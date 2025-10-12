#!/usr/bin/env python3
"""
Django management command to import single Claude Code JSONL file.

Usage:
    python manage.py import_claude_code_jsonl --file 097637c9-33b2-4806-bdcf-01540304de61.jsonl --era-id <uuid>
"""

import json
import uuid as uuid_lib
from pathlib import Path
from datetime import datetime
from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_datetime
from conversations.models import (
    Era, ContextWindow, ContextWindowType,
    Message, Thought, ToolUse, ToolResult, ThinkingEntity
)
from conversations.utils.retry_detection import RetryDetector


class Command(BaseCommand):
    help = 'Import single Claude Code JSONL conversation file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            required=True,
            help='JSONL file to import',
        )
        parser.add_argument(
            '--era-id',
            type=str,
            required=True,
            help='UUID of the Era to import into',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview without importing',
        )

    def handle(self, *args, **options):
        filepath = Path(options['file'])
        era_id = options['era_id']
        dry_run = options['dry_run']

        if not filepath.exists():
            self.stdout.write(self.style.ERROR(f'File not found: {filepath}'))
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
        lines = []
        with open(filepath) as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    # Skip summary lines
                    if data.get('type') != 'summary':
                        lines.append(data)
                except json.JSONDecodeError:
                    pass

        self.stdout.write(f'Found {len(lines)} messages')

        if dry_run:
            self.stdout.write('\nFirst 5 messages:')
            for i, msg_data in enumerate(lines[:5]):
                msg_type = msg_data.get('type')
                timestamp = msg_data.get('timestamp', 'no-timestamp')
                content = msg_data.get('message', {}).get('content', [])
                
                preview = ''
                if msg_type == 'user' and content:
                    preview = content[0].get('text', '')[:60]
                elif msg_type == 'assistant' and content:
                    for item in content:
                        if item.get('type') == 'text':
                            preview = item.get('text', '')[:60]
                            break
                
                self.stdout.write(f'  {i}. [{msg_type}] {timestamp} - {preview}...')
            return

        # Create context window
        filename = filepath.name
        first_msg_data = lines[0]

        # Determine first message details
        if first_msg_data.get('type') == 'user':
            first_sender = justin
            first_recipient = magent
            content_items = first_msg_data.get('message', {}).get('content', [])
            if isinstance(content_items, str):
                first_content = content_items
            else:
                first_content = ' '.join(
                    item.get('text', '') for item in content_items if isinstance(item, dict) and item.get('type') == 'text'
                )
        else:
            first_sender = magent
            first_recipient = justin
            content_items = first_msg_data.get('message', {}).get('content', [])
            first_content = ''
            if isinstance(content_items, str):
                first_content = content_items
            else:
                for item in content_items:
                    if isinstance(item, dict) and item.get('type') == 'text':
                        first_content = item.get('text', '')
                        break
            if not first_content:
                first_content = '[Assistant message]'

        # Create first message
        first_uuid = uuid_lib.UUID(first_msg_data.get('uuid'))
        timestamp_str = first_msg_data.get('timestamp')
        timestamp = None
        if timestamp_str:
            dt = parse_datetime(timestamp_str)
            if dt:
                timestamp = int(dt.timestamp() * 1000)

        first_msg = Message.objects.create(
            id=first_uuid,
            message_number=0,
            content=first_content,
            context_window=None,  # Set after creating window
            parent=None,
            sender=first_sender,
            timestamp=timestamp,
            session_id=uuid_lib.UUID(first_msg_data.get('sessionId')) if first_msg_data.get('sessionId') else None,
            source_file=filename,
            cwd=first_msg_data.get('cwd'),
            git_branch=first_msg_data.get('gitBranch'),
            client_version=first_msg_data.get('version')
        )
        first_msg.recipients.add(first_recipient)

        # Create context window
        context_window = ContextWindow.objects.create(
            era=era,
            first_message=first_msg,
            type=ContextWindowType.FRESH
        )

        # Update first message
        first_msg.context_window = context_window
        first_msg.save()

        self.stdout.write(self.style.SUCCESS(f'Created context window {context_window.id}'))

        # Process remaining messages
        message_num = 1
        parent = first_msg

        for msg_data in lines[1:]:
            msg_type = msg_data.get('type')
            msg_uuid = uuid_lib.UUID(msg_data.get('uuid'))
            
            timestamp_str = msg_data.get('timestamp')
            timestamp = None
            if timestamp_str:
                dt = parse_datetime(timestamp_str)
                if dt:
                    timestamp = int(dt.timestamp() * 1000)

            session_id = uuid_lib.UUID(msg_data.get('sessionId')) if msg_data.get('sessionId') else None

            # Common fields
            common = {
                'context_window': context_window,
                'parent': parent,
                'timestamp': timestamp,
                'session_id': session_id,
                'source_file': filename,
                'cwd': msg_data.get('cwd'),
                'git_branch': msg_data.get('gitBranch'),
                'client_version': msg_data.get('version')
            }

            if msg_type == 'user':
                content_items = msg_data.get('message', {}).get('content', [])

                # Check if this is actually a tool_result disguised as user message
                if isinstance(content_items, list) and len(content_items) == 1:
                    first_item = content_items[0]
                    if isinstance(first_item, dict) and first_item.get('type') == 'tool_result':
                        # This is a tool result, not a user message
                        result_msg = ToolResult.objects.create(
                            id=msg_uuid,
                            message_number=message_num,
                            content=first_item.get('content', ''),
                            sender=justin,  # Tool results come from user side
                            tool_use_id=first_item.get('tool_use_id', ''),
                            is_error=False,  # Assume not error unless specified
                            **common
                        )
                        result_msg.recipients.add(magent)
                        parent = result_msg
                        message_num += 1
                        continue

                # Regular user message
                if isinstance(content_items, str):
                    content = content_items
                else:
                    content = ' '.join(
                        item.get('text', '') for item in content_items if isinstance(item, dict) and item.get('type') == 'text'
                    )

                msg = Message.objects.create(
                    id=msg_uuid,
                    message_number=message_num,
                    content=content,
                    sender=justin,
                    **common
                )
                msg.recipients.add(magent)
                parent = msg
                message_num += 1

            elif msg_type == 'assistant':
                content_items = msg_data.get('message', {}).get('content', [])

                # Check if this is a synthetic error response
                model = msg_data.get('message', {}).get('model', '')
                is_synthetic = (model == '<synthetic>')

                # Process thinking blocks
                for item in content_items:
                    if item.get('type') == 'thinking':
                        thinking_uuid = uuid_lib.uuid5(msg_uuid, 'thinking')
                        thinking_msg = Thought.objects.create(
                            id=thinking_uuid,
                            message_number=message_num,
                            content=item.get('thinking', ''),
                            sender=magent,
                            signature='',  # JSONL doesn't have signature
                            **common
                        )
                        thinking_msg.recipients.add(justin)
                        parent = thinking_msg
                        message_num += 1

                # Process tool uses
                for item in content_items:
                    if item.get('type') == 'tool_use':
                        tool_uuid = uuid_lib.uuid5(msg_uuid, f"tool_use_{item.get('id')}")
                        tool_msg = ToolUse.objects.create(
                            id=tool_uuid,
                            message_number=message_num,
                            content=item.get('input', {}),
                            sender=magent,
                            tool_name=item.get('name', ''),
                            tool_id=item.get('id', ''),
                            **common
                        )
                        tool_msg.recipients.add(justin)
                        parent = tool_msg
                        message_num += 1

                # Process tool results
                for item in content_items:
                    if item.get('type') == 'tool_result':
                        result_uuid = uuid_lib.uuid5(msg_uuid, f"tool_result_{item.get('tool_use_id')}")
                        result_msg = ToolResult.objects.create(
                            id=result_uuid,
                            message_number=message_num,
                            content=item.get('content', ''),
                            sender=justin,  # Tool results come from user side
                            tool_use_id=item.get('tool_use_id', ''),
                            is_error=item.get('is_error', False),
                            **common
                        )
                        result_msg.recipients.add(magent)
                        parent = result_msg
                        message_num += 1

                # Process text content
                text_content = ''
                if isinstance(content_items, str):
                    text_content = content_items
                else:
                    for item in content_items:
                        if isinstance(item, dict) and item.get('type') == 'text':
                            text_content += item.get('text', '') + '\n'

                if text_content.strip():
                    text_msg = Message.objects.create(
                        id=msg_uuid,
                        message_number=message_num,
                        content=text_content.strip(),
                        sender=magent,
                        is_synthetic_error=is_synthetic,
                        model_backend=model if model != '<synthetic>' else None,
                        **common
                    )
                    text_msg.recipients.add(justin)
                    parent = text_msg
                    message_num += 1

        # Detect retries using RetryDetector
        self.stdout.write('Detecting retries...')
        all_messages = Message.objects.filter(
            context_window=context_window
        ).select_related('sender').order_by('message_number')

        detector = RetryDetector()
        retry_count = 0

        for msg in all_messages:
            is_retry = detector.is_retry(
                sender=msg.sender.name,
                content=str(msg.content),
                is_synthetic_error=msg.is_synthetic_error
            )

            if is_retry:
                msg.is_retry = True
                msg.save()
                retry_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'Imported {message_num} messages into {era.name}, window {context_window.id}'
        ))
        if retry_count > 0:
            self.stdout.write(self.style.WARNING(f'Marked {retry_count} messages as retries'))
