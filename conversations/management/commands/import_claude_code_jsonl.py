#!/usr/bin/env python3
"""
Django management command to import single Claude Code JSONL file.

Usage:
    python manage.py import_claude_code_jsonl --file 097637c9-33b2-4806-bdcf-01540304de61.jsonl --era-id <uuid>
"""

import json
import uuid as uuid_lib
import re
from pathlib import Path
from datetime import datetime
from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from conversations.models import (
    Era, ContextHeap, ContextHeapType,
    Message, Thought, ToolUse, ToolResult, ThinkingEntity,
    CompactingAction, Summary
)
from conversations.utils.retry_detection import RetryDetector
from importers_and_parsers.claude_code_v2 import import_line_from_claude_code_v2


class Command(BaseCommand):
    help = 'Import Claude Code JSONL conversation files (single file or directory)'

    # Store stats here so outer loop can access them
    last_import_stats = None

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            help='Single JSONL file to import',
        )
        parser.add_argument(
            '--directory',
            type=str,
            help='Directory containing JSONL files to import',
        )
        parser.add_argument(
            '--era-id',
            type=str,
            help='UUID of the Era to import into',
        )
        parser.add_argument(
            '--era-name',
            type=str,
            help='Name of the Era to import into (alternative to --era-id)',
        )
        parser.add_argument(
            '--recreate-era',
            action='store_true',
            help='Delete and recreate the era if it exists (only works with --era-name)',
        )
        parser.add_argument(
            '--clean-orphans',
            action='store_true',
            help='Delete orphaned messages and all CompactingActions before import',
        )

    def handle_directory(self, jsonl_files, era_id):
        """Import all JSONL files in directory and process watchlist at the end."""
        total_files = len(jsonl_files)
        errors = 0

        # Aggregated statistics
        all_heap_sizes = []
        total_heaps_created_loop_beginning = 0
        total_heaps_created_no_parent = 0
        total_heaps_created_compacting = 0
        total_heaps_closed = 0
        total_heaps_already_compacted = 0
        total_tiny_heaps = 0

        # Tracking
        self.watchlist = set()
        self.heaps_marked_for_multiple_compaction = []

        self.stdout.write(f'\nFound {total_files} JSONL files to import\n')

        # Import each file
        for i, filepath in enumerate(jsonl_files, 1):
            self.stdout.write(f'[{i}/{total_files}] Importing {filepath.name}...')

            try:
                # Call handle for single file (it will update last_import_stats)
                self.handle(file=str(filepath), era_id=era_id, _single_file_mode=True)

                # Collect statistics
                stats = Command.last_import_stats
                if stats:
                    total_heaps_created_loop_beginning += stats['heaps_created_because_loop_is_beginning']
                    total_heaps_created_no_parent += stats['heaps_created_because_no_parent']
                    total_heaps_created_compacting += stats['heaps_created_because_compacting']
                    total_heaps_closed += stats['heaps_closed']
                    total_heaps_already_compacted += stats['heaps_already_compacted']
                    total_tiny_heaps += stats['tiny_heaps']
                    all_heap_sizes.extend(stats['heap_sizes'])

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'ERROR importing {filepath.name}: {e}'))
                errors += 1
                raise

            orphaned_cas = CompactingAction.objects.filter(context_heap__isnull=True)

            if len(orphaned_cas) != len(self.watchlist):
                for ca in orphaned_cas:
                    if ca.looking_for_ending_message not in self.watchlist:
                        raise RuntimeError("Seems like we failed to start looking for an orphan's heap")

        # Process watchlist at the very end
        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('DIRECTORY IMPORT COMPLETE'))
        self.stdout.write(self.style.SUCCESS('='*60))

        # Get final counts
        era = Era.objects.get(id=era_id)
        ending_messages = Message.objects.filter(context_heap__era=era).count()
        orphaned_cas = CompactingAction.objects.filter(context_heap__isnull=True).count()
        linked_cas = CompactingAction.objects.filter(context_heap__isnull=False).count()

        self.stdout.write(f'\nTotal messages: {ending_messages:,}')
        self.stdout.write(f'Files with errors: {errors}')
        self.stdout.write(f'\nCompactingActions linked: {linked_cas}')
        self.stdout.write(f'CompactingActions orphaned: {orphaned_cas}')

        # Display watchlist
        self.stdout.write(f'\nWATCHLIST (orphaned ending messages): {len(self.watchlist)}')
        
        #################################################################
        ######### Cleanup and recovery efforts
        #################################################################

        self.found_at_the_last_minute = []
        if self.watchlist:
            self.stdout.write('  Message IDs on watchlist:')
            for uuid in self.watchlist:
                try:
                    heap_we_can_finally_close = Message.objects.get(id=uuid).context_heap
                except Message.DoesNotExist:
                    continue
                # self.stdout.write(f'    {str(uuid)[:8]}... (exists={exists})')
        

                #######
                # We found a message that matches the message that a CompactingAction reported as its last.
                # That means we've found the end of this heap, and we can mark the CompactingAction as having ended this heap.
                orphan_no_more = CompactingAction.objects.get(ending_message_id=uuid)

                try:
                    heap_we_can_finally_close.compacting_action
                    # Maybe we made two compacting actions - one from a summary and one from a boundary?
                    self.heaps_marked_for_multiple_compaction.append(heap_we_can_finally_close)
                    self.stdout.write(self.style.ERROR((
                    "This heap is already marked compacted.  Something is wrong.  Leaving this CompactingAction orphaned."
                    )))
                except ContextHeap.compacting_action.RelatedObjectDoesNotExist:
                    pass # This is good - there is no related compacting action.

                    orphan_no_more.context_heap = heap_we_can_finally_close
                    orphan_no_more.save()
                    self.found_at_the_last_minute.append(heap_we_can_finally_close)

        for context_heap in self.heaps_marked_for_multiple_compaction:
            
            #### Assess the possible enders and their CAs.
            possible_enders = []
            compacting_actions = []
            for message in context_heap.messages.all():
                try:
                    compacting_action = CompactingAction.objects.get(ending_message_id=message.id)
                    possible_enders.append((compacting_action, message))
                except CompactingAction.DoesNotExist:
                    continue
            assert True

        #####################################################
        #######################################################

        self.stdout.write(f'\nFound at the last minute: {len(self.found_at_the_last_minute)}')

        # Display heap statistics
        total_heaps_created = total_heaps_created_loop_beginning + total_heaps_created_no_parent + total_heaps_created_compacting
        self.stdout.write(f'\nHEAP STATISTICS:')
        self.stdout.write(f'  Total heaps created: {total_heaps_created}')
        self.stdout.write(f'    - Loop beginning: {total_heaps_created_loop_beginning}')
        self.stdout.write(f'    - No parent: {total_heaps_created_no_parent}')
        self.stdout.write(f'    - After compacting: {total_heaps_created_compacting}')
        self.stdout.write(f'  Total heaps closed: {total_heaps_closed}')
        self.stdout.write(f'  Heaps already compacted (errors): {total_heaps_already_compacted}')
        self.stdout.write(f'  Tiny heaps (≤1 message): {total_tiny_heaps}')

        if all_heap_sizes:
            self.stdout.write(f'\n  Heap size distribution:')
            self.stdout.write(f'    Min: {min(all_heap_sizes)} messages')
            self.stdout.write(f'    Max: {max(all_heap_sizes)} messages')
            self.stdout.write(f'    Average: {sum(all_heap_sizes)/len(all_heap_sizes):.1f} messages')
            self.stdout.write(f'    Median: {sorted(all_heap_sizes)[len(all_heap_sizes)//2]} messages')

        self.stdout.write(self.style.SUCCESS('='*60 + '\n'))

    def handle(self, *args, **options):
        _single_file_mode = options.get('_single_file_mode', False)

        # Validate arguments
        if not options.get('era_id') and not options.get('era_name'):
            self.stdout.write(self.style.ERROR('Must specify either --era-id or --era-name'))
            return

        if options.get('recreate_era') and not options.get('era_name'):
            self.stdout.write(self.style.ERROR('--recreate-era only works with --era-name'))
            return

        # Handle era creation/lookup
        if options.get('era_name'):
            era_name = options['era_name']

            # Delete era if recreate flag is set
            if options.get('recreate_era'):
                try:
                    old_era = Era.objects.get(name=era_name)
                    self.stdout.write(self.style.WARNING(f'Deleting existing era: {era_name}'))
                    old_era.delete()
                except Era.DoesNotExist:
                    pass

            # Clean orphans if flag is set
            if options.get('clean_orphans'):
                orphan_count = Message.objects.filter(context_heap=None).count()
                ca_count = CompactingAction.objects.all().count()
                self.stdout.write(self.style.WARNING(f'Deleting {orphan_count} orphaned messages and {ca_count} CompactingActions'))
                Message.objects.filter(context_heap=None).delete()
                CompactingAction.objects.all().delete()

            # Get or create era
            era, created = Era.objects.get_or_create(name=era_name)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created new era: {era_name} ({era.id})'))
            else:
                self.stdout.write(f'Using existing era: {era_name} ({era.id})')

            era_id = str(era.id)
        else:
            era_id = options['era_id']

        # Determine mode: single file or directory
        if options.get('directory') and not _single_file_mode:
            directory = Path(options['directory'])
            if not directory.exists():
                self.stdout.write(self.style.ERROR(f'Directory not found: {directory}'))
                return

            # Get all JSONL files
            jsonl_files = sorted(directory.glob("*.jsonl"))
            if not jsonl_files:
                self.stdout.write(self.style.ERROR(f'No JSONL files found in {directory}'))
                return

            return self.handle_directory(jsonl_files, era_id)

        elif options.get('file'):
            filepath = Path(options['file'])
            if not filepath.exists():
                self.stdout.write(self.style.ERROR(f'File not found: {filepath}'))
                return
        else:
            self.stdout.write(self.style.ERROR('Must specify either --file or --directory'))
            return

        # Get era
        try:
            era = Era.objects.get(id=era_id)
        except Era.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Era not found: {era_id}'))
            return

        # Get entities
        justin = ThinkingEntity.objects.get(name='justin')
        magent = ThinkingEntity.objects.get(name='magent')

        # Parse JSONL
        self.stdout.write(f'Parsing {filepath.name}...')
        events = []
        summary_data_by_leaf = {}
        previous_event = None
        filename = filepath.name
        last_compact, last_compact_created = (None, None)
        heap = None  # Ideally, this is just a bulwark value that is never kept past the heap logic below.
        need_new_heap = ContextHeapType.FRESH  # Flag to create heap on next message

        # Statistics tracking
        heaps_created_because_loop_is_beginning = []
        log_bucket = heaps_created_because_loop_is_beginning
        heaps_created_because_no_parent = []
        heaps_created_because_compacting = []
        heaps_closed = []
        heaps_already_compacted = 0

        with open(filepath) as f:
            for counter, line in enumerate(f):
                event, created, orphans_reunited = import_line_from_claude_code_v2(line, era, filename)

                if isinstance(event, Summary):
                    # Don't love this - is there no good way to duck type this later?
                    continue

                ##### Heap, boundary, and continuation (ie, collection-level) handling

                # If we flagged that we need a new heap and this is any kind of Message, create it now
                if isinstance(event, Message):
                    if event.has_no_parent_wants_no_parent():
                            need_new_heap = ContextHeapType.FRESH
                            log_bucket = heaps_created_because_no_parent
                    if need_new_heap:
                        heap = ContextHeap.objects.create(era=era, type=need_new_heap)
                        log_bucket.append(heap)
                        self.stdout.write(self.style.SUCCESS(
                            f'Created {need_new_heap} heap {str(heap.id)[:8]} for {event.__class__.__name__} {str(event.id)[:8]} after CompactingAction'
                        ))
                        need_new_heap = False

                if not event.context_heap:
                    if heap and isinstance(event, Message):
                        heap.add_event(event)
                    elif hasattr(event, "is_continuation_message") and event.is_continuation_message:
                        # TODO: Are we leaving the previous heap unclosed (ie, with no matching CompactingAction)?
                        heap = ContextHeap.objects.create(era=era, type=ContextHeapType.POST_COMPACTING)
                        heaps_created_because_no_parent.append(heap)
                        heap.add_event(event)
                    elif hasattr(event, "parent") and event.parent is None:
                        # Seems like a freshy?
                        heap = ContextHeap.objects.create(era=era)
                        heaps_created_because_no_parent.append(heap)
                        heap.add_event(event)
                    elif hasattr(event, "parent") and event.parent.context_heap:
                        event.context_heap = event.parent.context_heap
                else:
                    if created:
                        if not isinstance(event, CompactingAction):
                            assert False # How did the event already get assigned a heap?
                    else:
                        assert True # OK, so this already had a heap in the db.
                
                if heap is None and event.context_heap:
                    if created:
                        if not isinstance(event, CompactingAction):
                            # ...how do we have a heap if we didn't have one before?
                            assert False
                    else:
                        # This event had a heap in the db; let's pick up where we left off.
                        heap = event.context_heap
                
                if event.id in self.watchlist:
                    # We found a message that matches the message that a CompactingAction reported as its last.
                    # That means we've found the end of this heap, and we can mark the CompactingAction as having ended this heap.
                    orphan_no_more = CompactingAction.objects.get(looking_for_ending_message=event.id)
                    
                    if not event.context_heap:
                        raise ValueError("Can't reunite a CompactingAction using a message with no context heap.")

                    heap_we_can_finally_close = event.context_heap

                    try:
                        heap_we_can_finally_close.compacting_action
                        # Maybe we made two compacting actions - one from a summary and one from a boundary?
                        self.heaps_marked_for_multiple_compaction.append(heap_we_can_finally_close)
                        self.stdout.write(self.style.ERROR((
                        "This heap is already marked compacted.  Something is wrong.  Leaving this CompactingAction orphaned."
                        )))
                    except ContextHeap.compacting_action.RelatedObjectDoesNotExist:
                        pass # This is good - there is no related compacting action.

                        orphan_no_more.context_heap = heap_we_can_finally_close
                        orphan_no_more.save()
                        heaps_closed.append(heap_we_can_finally_close)

                    self.watchlist.remove(event.id)

                    if heap == heap_we_can_finally_close:
                        # TODO: Is this always POST_COMPACTING?  Maybe not?
                        heap = ContextHeap.objects.create(
                            era=era,
                            type=ContextHeapType.POST_COMPACTING
                        )
                        heaps_created_because_no_parent.append(heap)
                    else:
                        # TODO: Does this need special logic?
                        self.stdout.write(self.style.WARNING((
                            "The heap we're being asked to close isn't the heap we're on.  Not sure what to do."
                            )))

                if event.__class__ == CompactingAction:
                    compacting_action = event
                    last_compact, last_compact_created = event, created
                    try:
                        # TODO: Can't we do this with our get_or_create custom manager method?
                        ending_message = Message.objects.get(id=compacting_action.ending_message_id)
                        compacting_action.ending_message = ending_message
                        compacting_action.context_heap = ending_message.context_heap
                        compacting_action.save()
                    except Message.DoesNotExist:
                        if not compacting_action.context_heap:
                            # This is an orphan (we don't know what heap this is summarizing)
                            if created and self.watchlist is not None:
                                if compacting_action.looking_for_ending_message in self.watchlist:
                                    # Uhhh, we just made a compacting action looking for a message that's already on the watchlist?
                                    # ...but this is not newly created?
                                    assert False
                                else:
                                    self.watchlist.add(compacting_action.looking_for_ending_message)
                            # self.stdout.write(self.style.WARNING(
                            # f'Creating orphaned CompactingAction for boundary {str(boundary_uuid)[:8]}'
                            # ))

                    # Flag that we need a new heap when we encounter the next message
                    need_new_heap = ContextHeapType.POST_COMPACTING
                    log_bucket = heaps_created_because_compacting
                    if event.context_heap:
                        message_count = event.context_heap.messages.count()
                        self.stdout.write(self.style.SUCCESS(
                            f'CompactingAction {str(event.id)[:8]} ended heap {str(event.context_heap_id)[:8]} with {message_count} messages - will create new heap on next message'
                        ))
                    else:
                        self.stdout.write(self.style.WARNING(
                            f'CompactingAction {str(event.id)[:8]} has no context_heap (ending_message_id: {str(event.ending_message_id)[:8]}) - will create new heap on next message'
                        ))
                
                if event.__class__ == Message and event.is_continuation_message and last_compact is not None: # TODO: Awkward line; let's state this more tersely.
                    if last_compact.continuation_message:
                        if last_compact.continuation_message == event:
                            # The continuation message is already set to this one.  We're fine.
                            _success_message = f'Continuation message {str(event.id)[:8]} already linked to CompactingAction {str(last_compact.id)[:8]}'
                            self.stdout.write(self.style.SUCCESS(_success_message))
                        else:
                            self.stdout.write(self.style.ERROR(
                                f'CompactingAction {str(last_compact.id)[:8]} already has continuation {str(last_compact.continuation_message.id)[:8]}, '
                                f'but found different continuation {str(event.id)[:8]}'
                            ))
                            timestamp_of_existing = last_compact.continuation_message.timestamp
                            timestamp_of_new_continuation = event.timestamp

                            # Calculate time differences
                            ending_message = None
                            timestamp_of_ending_message = None
                            try:
                                ending_message = Message.objects.get(id=last_compact.ending_message_id)
                                timestamp_of_ending_message = ending_message.timestamp
                            except Message.DoesNotExist:
                                pass

                            # Show human-readable deltas
                            if timestamp_of_ending_message:
                                # Delta between leaf (ending) and existing continuation
                                delta_existing_ms = timestamp_of_existing - timestamp_of_ending_message
                                delta_existing_sec = delta_existing_ms / 1000
                                delta_existing_min = delta_existing_sec / 60

                                # Delta between leaf (ending) and new continuation
                                delta_new_ms = timestamp_of_new_continuation - timestamp_of_ending_message
                                delta_new_sec = delta_new_ms / 1000
                                delta_new_min = delta_new_sec / 60

                                self.stdout.write(self.style.WARNING(
                                    f'\n=== DUPLICATE CONTINUATION DETECTED ===\n'
                                    f'CompactingAction: {str(last_compact.id)[:8]}\n'
                                    f'Leaf message (ending): {str(last_compact.ending_message_id)[:8]}\n'
                                    f'Existing continuation: {str(last_compact.continuation_message.id)[:8]}\n'
                                    f'  Time after leaf: {delta_existing_sec:.1f}s ({delta_existing_min:.2f} min)\n'
                                    f'New continuation: {str(event.id)[:8]}\n'
                                    f'  Time after leaf: {delta_new_sec:.1f}s ({delta_new_min:.2f} min)\n'
                                ))

                            self.stdout.write(self.style.ERROR(f'Finding multiple continuation messages for this compacting action, but that is not currently possible.'))
                    else:
                        # The last compacting action has no continuation message; this is the one.
                        last_compact.continuation_message = event
                        last_compact.save()
                        self.stdout.write(self.style.SUCCESS(
                            f'Linked continuation message {str(event.id)[:8]} to CompactingAction {str(last_compact.id)[:8]}'
                        ))

        # Print summary statistics
        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('IMPORT SUMMARY'))
        self.stdout.write(self.style.SUCCESS('='*60))

        # Combine all heap creation reasons
        all_created_heaps = heaps_created_because_loop_is_beginning + heaps_created_because_no_parent + heaps_created_because_compacting

        self.stdout.write(f'\nHeaps created (total): {len(all_created_heaps)}')
        self.stdout.write(f'  - Loop beginning: {len(heaps_created_because_loop_is_beginning)}')
        self.stdout.write(f'  - No parent: {len(heaps_created_because_no_parent)}')
        self.stdout.write(f'  - After compacting: {len(heaps_created_because_compacting)}')
        self.stdout.write(f'\nHeaps closed: {len(heaps_closed)}')
        self.stdout.write(f'Heaps already compacted (errors): {heaps_already_compacted}')

        # Get message counts for all heaps created during this import
        self.stdout.write(f'\nMessage counts per heap created:')
        heap_sizes = []
        for heap in all_created_heaps:
            msg_count = heap.messages.count()
            heap_sizes.append(msg_count)
            heap_type = heap.get_type_display()
            self.stdout.write(f'  Heap {str(heap.id)[:8]} ({heap_type}): {msg_count} messages')

        if heap_sizes:
            self.stdout.write(f'\nHeap size statistics:')
            self.stdout.write(f'  Min: {min(heap_sizes)} messages')
            self.stdout.write(f'  Max: {max(heap_sizes)} messages')
            self.stdout.write(f'  Average: {sum(heap_sizes)/len(heap_sizes):.1f} messages')

            # Count tiny heaps (0-1 messages)
            tiny_heaps = [s for s in heap_sizes if s <= 1]
            if tiny_heaps:
                self.stdout.write(self.style.WARNING(
                    f'  WARNING: {len(tiny_heaps)} heaps with ≤1 message'
                ))

        self.stdout.write(self.style.SUCCESS('='*60 + '\n'))

        # Store statistics in class attribute for outer loop to access
        Command.last_import_stats = {
            'heaps_created_because_no_parent': len(heaps_created_because_no_parent),
            'heaps_created_because_loop_is_beginning': len(heaps_created_because_loop_is_beginning),
            'heaps_created_because_compacting': len(heaps_created_because_compacting),
            'heaps_closed': len(heaps_closed),
            'heaps_already_compacted': heaps_already_compacted,
            'heap_sizes': heap_sizes,
            'tiny_heaps': len([s for s in heap_sizes if s <= 1]) if heap_sizes else 0,
            'watchlist': list(self.watchlist),  # Convert set to list for serialization
        }
