#!/usr/bin/env python3
"""
Django management command to import Claude Code JSONL backups.

Handles all four message types: TextMessage, Thought, ToolUse, ToolResult
"""

import json
import uuid as uuid_lib
from pathlib import Path
from datetime import datetime
from django.core.management.base import BaseCommand
from conversations.models import TextMessage, Thought, ToolUse, ToolResult
from constant_sorrow.constants import (
    IMPORTED,
    ALREADY_EXISTS,
    ALREADY_ATTEMPTED,
    PARENT_MISSING,
    IMPORT_ERROR
)


class Command(BaseCommand):
    help = 'Import messages from Claude Code JSONL backup files'

    def add_arguments(self, parser):
        parser.add_argument('backup_dir', type=str, help='Directory containing JSONL backup files')
        parser.add_argument('--dry-run', action='store_true', help='Preview without importing')

    def handle(self, *args, **options):
        backup_dir = Path(options['backup_dir'])
        dry_run = options['dry_run']

        if not backup_dir.exists():
            self.stdout.write(self.style.ERROR(f'Directory not found: {backup_dir}'))
            return

        # Collect and deduplicate messages
        self.stdout.write('Collecting messages from JSONL files...')
        messages_by_uuid = self.collect_messages(backup_dir)

        # Sort by timestamp
        messages = sorted(messages_by_uuid.values(), key=lambda m: m['timestamp'])

        # Count message types
        type_counts = {}
        for m in messages:
            mtype = m.get('message_type', 'unknown')
            type_counts[mtype] = type_counts.get(mtype, 0) + 1

        self.stdout.write(f'\nFound {len(messages)} unique messages (deduplicated)')
        for mtype, count in sorted(type_counts.items()):
            self.stdout.write(f'  {count:4d} {mtype} messages')

        if dry_run:
            self.stdout.write(self.style.WARNING('\n*** DRY RUN - No data will be imported ***\n'))
            self.stdout.write('First 10 messages:')
            for i, msg in enumerate(messages[:10]):
                dt = datetime.fromtimestamp(msg['timestamp'])
                mtype = msg.get('message_type', 'unknown').upper()
                sender = msg.get('sender', '?')
                recipient = msg.get('recipient', '?')
                content_preview = str(msg.get('content', msg.get('tool_name', '?')))[:60]
                self.stdout.write(f'  {i+1}. {dt} [{sender}→{recipient}] [{mtype}] {content_preview}...')
            return

        # Import messages with parent-first recursion
        self.stdout.write('\nImporting messages (parent-first order)...')

        # Build lookup dict
        self.msg_by_uuid = {m['uuid']: m for m in messages}
        self.attempted = set()  # Track what we've tried to import

        stats = {
            IMPORTED: 0,
            ALREADY_EXISTS: 0,
            ALREADY_ATTEMPTED: 0,
            PARENT_MISSING: 0,
            IMPORT_ERROR: 0
        }

        for msg in messages:
            result = self.import_with_parents(msg)
            stats[result] = stats.get(result, 0) + 1

            total = sum(stats.values())
            if total % 100 == 0:
                self.stdout.write(f'  Processed {total}/{len(messages)}...')

        self.stdout.write(self.style.SUCCESS(
            f'\n✓ Import complete:'
        ))
        for result, count in stats.items():
            if count > 0:
                self.stdout.write(f'  {count:4d} {result}')

    def parse_timestamp(self, iso_timestamp):
        """Convert ISO timestamp to Unix timestamp (seconds)."""
        dt = datetime.fromisoformat(iso_timestamp.replace('Z', '+00:00'))
        return int(dt.timestamp())

    def extract_text_from_content(self, content_list):
        """Extract text from content array."""
        text_parts = []
        for item in content_list:
            if isinstance(item, dict) and item.get('type') == 'text':
                text_parts.append(item.get('text', ''))
        return '\n'.join(text_parts) if text_parts else ''

    def extract_thinking_from_content(self, content_list):
        """Extract thinking text and signature from content array."""
        for item in content_list:
            if isinstance(item, dict) and item.get('type') == 'thinking':
                return item.get('thinking', ''), item.get('signature', '')
        return None, None

    def extract_tool_messages(self, content_list):
        """Extract tool_use and tool_result messages from content array."""
        tool_messages = []
        for item in content_list:
            if isinstance(item, dict):
                if item.get('type') == 'tool_use':
                    tool_messages.append({
                        'message_type': 'tool_use',
                        'tool_name': item.get('name'),
                        'tool_id': item.get('id'),
                        'tool_input': item.get('input', {}),
                    })
                elif item.get('type') == 'tool_result':
                    tool_messages.append({
                        'message_type': 'tool_result',
                        'tool_use_id': item.get('tool_use_id'),
                        'output': str(item.get('content', '')),
                        'is_error': item.get('is_error', False),
                    })
        return tool_messages

    def process_message(self, msg):
        """Process a single JSONL message and return list of message dicts."""
        msg_type = msg.get('type')
        if msg_type not in ['user', 'assistant']:
            return []

        uuid = msg.get('uuid')
        if not uuid:
            return []

        timestamp_str = msg.get('timestamp')
        if not timestamp_str:
            return []

        timestamp = self.parse_timestamp(timestamp_str)

        message_obj = msg.get('message', {})
        content = message_obj.get('content', [])

        if not isinstance(content, list):
            return []

        # Extract metadata
        session_id = msg.get('sessionId')
        parent_uuid = msg.get('parentUuid')
        message_id = message_obj.get('id')
        model = message_obj.get('model')
        stop_reason = message_obj.get('stop_reason')

        usage = message_obj.get('usage', {})
        input_tokens = usage.get('input_tokens')
        output_tokens = usage.get('output_tokens')
        cache_creation = usage.get('cache_creation_input_tokens')
        cache_read = usage.get('cache_read_input_tokens')

        # Common metadata for all message types
        common_metadata = {
            'session_id': session_id,
            'timestamp': timestamp,
            'model_backend': model,
            'source_file': f'{session_id}.jsonl' if session_id else 'unknown.jsonl',
            'message_id': message_id,
            'stop_reason': stop_reason,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'cache_creation_input_tokens': cache_creation,
            'cache_read_input_tokens': cache_read,
        }

        # Determine sender/recipient
        if msg_type == 'user':
            sender = 'justin'
            recipient = 'magent'
        else:  # assistant
            sender = 'magent'
            recipient = 'magent'  # Will be overridden for TextMessage

        results = []
        current_parent = parent_uuid

        # 1. Extract and create Thought message (if exists)
        thinking_content, signature = self.extract_thinking_from_content(content)
        if thinking_content:
            results.append({
                'message_type': 'thought',
                'uuid': uuid,
                'parent_id': current_parent,
                'sender': 'magent',
                'recipient': 'magent',
                'content': thinking_content,
                'signature': signature,
                **common_metadata
            })
            # Next messages will parent to this thinking message
            current_parent = uuid
            # Generate new UUID for subsequent messages
            uuid = str(uuid_lib.uuid5(uuid_lib.UUID(uuid), 'response'))

        # 2. Extract and create ToolUse/ToolResult messages
        tool_messages = self.extract_tool_messages(content)
        for tool_msg in tool_messages:
            tool_uuid = str(uuid_lib.uuid5(uuid_lib.UUID(uuid), f"tool_{tool_msg['message_type']}_{len(results)}"))

            tool_data = {
                'uuid': tool_uuid,
                'parent_id': current_parent,
                'sender': 'magent' if tool_msg['message_type'] == 'tool_use' else 'system',
                'recipient': 'system' if tool_msg['message_type'] == 'tool_use' else 'magent',
                **common_metadata
            }
            tool_data.update(tool_msg)
            results.append(tool_data)

            # Chain tool messages together
            current_parent = tool_uuid

        # 3. Create TextMessage (if text content exists)
        text_content = self.extract_text_from_content(content)
        if text_content:
            is_summary = text_content.startswith('This session is being continued from a previous conversation')

            results.append({
                'message_type': 'text',
                'uuid': uuid,
                'parent_id': current_parent,
                'sender': sender,
                'recipient': 'justin' if sender == 'magent' else 'magent',
                'content': text_content,
                'notes': 'session-summary' if is_summary else None,
                **common_metadata
            })

        return results

    def collect_messages(self, backup_dir):
        """Collect all messages from JSONL files with deduplication."""
        messages_by_uuid = {}

        jsonl_files = sorted(backup_dir.glob('*.jsonl'))
        self.stdout.write(f'Found {len(jsonl_files)} JSONL files')

        for filepath in jsonl_files:
            with open(filepath, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    try:
                        msg = json.loads(line)
                        processed = self.process_message(msg)

                        for msg_data in processed:
                            msg_uuid = msg_data['uuid']

                            # Keep earliest occurrence if duplicate
                            if msg_uuid not in messages_by_uuid:
                                messages_by_uuid[msg_uuid] = msg_data
                            elif msg_data['timestamp'] < messages_by_uuid[msg_uuid]['timestamp']:
                                messages_by_uuid[msg_uuid] = msg_data

                    except json.JSONDecodeError as e:
                        self.stdout.write(self.style.WARNING(
                            f'  Error parsing {filepath.name} line {line_num}: {e}'
                        ))
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(
                            f'  Error processing {filepath.name} line {line_num}: {e}'
                        ))

        return messages_by_uuid

    def import_with_parents(self, msg_data):
        """Recursively import a message after importing its parent."""
        msg_uuid = msg_data['uuid']

        # Already attempted?
        if msg_uuid in self.attempted:
            return ALREADY_ATTEMPTED

        self.attempted.add(msg_uuid)

        # Check if parent exists and needs importing
        parent_id = msg_data.get('parent_id')
        if parent_id:
            # Check if parent exists in database
            from conversations.models import Message
            if not Message.objects.filter(id=parent_id).exists():
                # Parent not in DB - try to import it first
                parent_data = self.msg_by_uuid.get(parent_id)
                if parent_data:
                    self.import_with_parents(parent_data)
                else:
                    # Parent not in our dataset - orphan this message by setting parent to None
                    msg_data['parent_id'] = None

        # Now import this message
        return self.import_message(msg_data)

    def import_message(self, msg_data):
        """Import a single message using Django ORM."""
        message_type = msg_data.get('message_type')
        msg_uuid = msg_data['uuid']

        # Check if already exists
        if message_type == 'text':
            if TextMessage.objects.filter(id=msg_uuid).exists():
                return ALREADY_EXISTS
        elif message_type == 'thought':
            if Thought.objects.filter(id=msg_uuid).exists():
                return ALREADY_EXISTS
        elif message_type == 'tool_use':
            if ToolUse.objects.filter(id=msg_uuid).exists():
                return ALREADY_EXISTS
        elif message_type == 'tool_result':
            if ToolResult.objects.filter(id=msg_uuid).exists():
                return ALREADY_EXISTS

        # Create the appropriate model instance
        try:
            if message_type == 'text':
                TextMessage.objects.create(
                    id=msg_uuid,
                    parent_id=msg_data.get('parent_id'),
                    sender=msg_data['sender'],
                    recipient=msg_data['recipient'],
                    content=msg_data['content'],
                    session_id=msg_data.get('session_id'),
                    message_id=msg_data.get('message_id'),
                    timestamp=msg_data.get('timestamp'),
                    model_backend=msg_data.get('model_backend'),
                    stop_reason=msg_data.get('stop_reason'),
                    source_file=msg_data.get('source_file'),
                    notes=msg_data.get('notes'),
                    input_tokens=msg_data.get('input_tokens'),
                    output_tokens=msg_data.get('output_tokens'),
                    cache_creation_input_tokens=msg_data.get('cache_creation_input_tokens'),
                    cache_read_input_tokens=msg_data.get('cache_read_input_tokens'),
                )
            elif message_type == 'thought':
                Thought.objects.create(
                    id=msg_uuid,
                    parent_id=msg_data.get('parent_id'),
                    sender=msg_data['sender'],
                    recipient=msg_data['recipient'],
                    content=msg_data['content'],
                    signature=msg_data.get('signature', ''),
                    session_id=msg_data.get('session_id'),
                    message_id=msg_data.get('message_id'),
                    timestamp=msg_data.get('timestamp'),
                    model_backend=msg_data.get('model_backend'),
                    stop_reason=msg_data.get('stop_reason'),
                    source_file=msg_data.get('source_file'),
                    notes=msg_data.get('notes'),
                    input_tokens=msg_data.get('input_tokens'),
                    output_tokens=msg_data.get('output_tokens'),
                    cache_creation_input_tokens=msg_data.get('cache_creation_input_tokens'),
                    cache_read_input_tokens=msg_data.get('cache_read_input_tokens'),
                )
            elif message_type == 'tool_use':
                ToolUse.objects.create(
                    id=msg_uuid,
                    parent_id=msg_data.get('parent_id'),
                    sender=msg_data['sender'],
                    recipient=msg_data['recipient'],
                    tool_name=msg_data['tool_name'],
                    tool_id=msg_data['tool_id'],
                    tool_input=msg_data['tool_input'],
                    session_id=msg_data.get('session_id'),
                    message_id=msg_data.get('message_id'),
                    timestamp=msg_data.get('timestamp'),
                    model_backend=msg_data.get('model_backend'),
                    stop_reason=msg_data.get('stop_reason'),
                    source_file=msg_data.get('source_file'),
                    input_tokens=msg_data.get('input_tokens'),
                    output_tokens=msg_data.get('output_tokens'),
                    cache_creation_input_tokens=msg_data.get('cache_creation_input_tokens'),
                    cache_read_input_tokens=msg_data.get('cache_read_input_tokens'),
                )
            elif message_type == 'tool_result':
                ToolResult.objects.create(
                    id=msg_uuid,
                    parent_id=msg_data.get('parent_id'),
                    sender=msg_data['sender'],
                    recipient=msg_data['recipient'],
                    tool_use_id=msg_data['tool_use_id'],
                    output=msg_data['output'],
                    is_error=msg_data.get('is_error', False),
                    session_id=msg_data.get('session_id'),
                    message_id=msg_data.get('message_id'),
                    timestamp=msg_data.get('timestamp'),
                    model_backend=msg_data.get('model_backend'),
                    stop_reason=msg_data.get('stop_reason'),
                    source_file=msg_data.get('source_file'),
                    input_tokens=msg_data.get('input_tokens'),
                    output_tokens=msg_data.get('output_tokens'),
                    cache_creation_input_tokens=msg_data.get('cache_creation_input_tokens'),
                    cache_read_input_tokens=msg_data.get('cache_read_input_tokens'),
                )
            return IMPORTED
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  Error importing {msg_uuid}: {e}'))
            return IMPORT_ERROR
