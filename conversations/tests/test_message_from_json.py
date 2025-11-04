"""
Tests for Message.from_jsonl_claude_code_v2() classmethod.
"""

import uuid
from django.test import TestCase
from django.contrib.contenttypes.models import ContentType
from conversations.models import (
    Message, ThinkingEntity, Era, ContextHeap, ContextHeapType, RawImportedContent
)


class MessageFromJsonTests(TestCase):
    """Test Message.from_jsonl_claude_code_v2() deduplication and instantiation."""

    def setUp(self):
        """Create test entities and context."""
        self.justin = ThinkingEntity.objects.create(name='justin', is_biological_human=True)
        self.magent = ThinkingEntity.objects.create(name='magent', is_biological_human=False)

        self.era = Era.objects.create(name='Test Era')

        # Create a heap for messages to belong to
        first_msg = Message.objects.create(
            id=uuid.uuid4(),
            message_number=0,
            content='First message',
            sender=self.justin
        )
        first_msg.recipients.add(self.magent)

        self.heap = ContextHeap.objects.create(
            era=self.era,
            first_message=first_msg,
            type=ContextHeapType.FRESH
        )

        first_msg.context_heap = self.heap
        first_msg.save()

    def test_creates_new_message_from_json(self):
        """Creating a new message returns [(message, True)]."""
        json_data = {
            'uuid': str(uuid.uuid4()),
            'type': 'user',
            'sessionId': str(uuid.uuid4()),
            'timestamp': '2025-10-15T14:30:00.000Z',
            'cwd': '/home/test',
            'gitBranch': 'main',
            'version': '1.0.0',
            'isSidechain': False,
            'message': {
                'role': 'user',
                'content': [
                    {
                        'type': 'text',
                        'text': 'Hello, this is a test message'
                    }
                ]
            }
        }

        results = Message.from_jsonl_claude_code_v2(
            json_data,
            context_heap=self.heap,
            sender=self.justin,
            message_number=1
        )

        self.assertEqual(len(results), 1)
        message, created = results[0]
        self.assertTrue(created)
        self.assertEqual(message.content, 'Hello, this is a test message')
        self.assertEqual(message.sender, self.justin)
        self.assertEqual(message.context_heap, self.heap)
        self.assertEqual(message.message_number, 1)
        self.assertEqual(message.cwd, '/home/test')
        self.assertEqual(message.git_branch, 'main')
        self.assertEqual(message.client_version, '1.0.0')
        self.assertFalse(message.is_sidechain)

    def test_deduplicates_existing_message(self):
        """Calling from_json with existing UUID returns (existing_message, False)."""
        msg_uuid = uuid.uuid4()
        session_uuid = uuid.uuid4()

        # Create original message
        original = Message.objects.create(
            id=msg_uuid,
            message_number=1,
            content='Original message',
            context_heap=self.heap,
            sender=self.justin,
            session_id=session_uuid
        )
        original.recipients.add(self.magent)

        # Try to create again with same UUID
        json_data = {
            'uuid': str(msg_uuid),
            'type': 'user',
            'sessionId': str(session_uuid),
            'timestamp': '2025-10-15T14:30:00.000Z',
            'message': {
                'role': 'user',
                'content': [{'type': 'text', 'text': 'Different content'}]
            }
        }

        results = Message.from_jsonl_claude_code_v2(
            json_data,
            context_heap=self.heap,
            sender=self.justin,
            message_number=1
        )

        self.assertEqual(len(results), 1)
        message, created = results[0]

        self.assertFalse(created)
        self.assertEqual(message.id, original.id)
        self.assertEqual(message.content, 'Original message')  # Keeps original content

    def test_sanity_check_fails_on_session_mismatch(self):
        """Raises ValueError if existing message has different session_id."""
        msg_uuid = uuid.uuid4()
        original_session = uuid.uuid4()
        different_session = uuid.uuid4()

        # Create original message
        Message.objects.create(
            id=msg_uuid,
            message_number=1,
            content='Original message',
            context_heap=self.heap,
            sender=self.justin,
            session_id=original_session
        )

        # Try to create with same UUID but different session
        json_data = {
            'uuid': str(msg_uuid),
            'type': 'user',
            'sessionId': str(different_session),
            'timestamp': '2025-10-15T14:30:00.000Z',
            'message': {
                'role': 'user',
                'content': [{'type': 'text', 'text': 'Content'}]
            }
        }

        with self.assertRaises(ValueError) as context:
            Message.from_jsonl_claude_code_v2(
                json_data,
                context_heap=self.heap,
                sender=self.justin,
                message_number=1
            )

        self.assertIn('different session_id', str(context.exception))

    def test_handles_string_content(self):
        """Handles content as plain string instead of array."""
        json_data = {
            'uuid': str(uuid.uuid4()),
            'type': 'user',
            'message': {
                'role': 'user',
                'content': 'Plain string content'
            }
        }

        results = Message.from_jsonl_claude_code_v2(
            json_data,
            context_heap=self.heap,
            sender=self.justin,
            message_number=1
        )

        self.assertEqual(len(results), 1)
        message, created = results[0]

        self.assertTrue(created)
        self.assertEqual(message.content, 'Plain string content')

    def test_handles_empty_content(self):
        """Creates message with placeholder for empty content."""
        json_data = {
            'uuid': str(uuid.uuid4()),
            'type': 'user',
            'message': {
                'role': 'user',
                'content': []
            }
        }

        results = Message.from_jsonl_claude_code_v2(
            json_data,
            context_heap=self.heap,
            sender=self.justin,
            message_number=1
        )

        self.assertEqual(len(results), 1)
        message, created = results[0]

        self.assertTrue(created)
        self.assertEqual(message.content, '[Empty message]')

    def test_parses_timestamp_correctly(self):
        """Converts ISO timestamp to milliseconds since epoch."""
        json_data = {
            'uuid': str(uuid.uuid4()),
            'type': 'user',
            'timestamp': '2025-10-15T14:30:45.123Z',
            'message': {
                'role': 'user',
                'content': 'Test'
            }
        }

        results = Message.from_jsonl_claude_code_v2(
            json_data,
            context_heap=self.heap,
            sender=self.justin,
            message_number=1
        )

        self.assertEqual(len(results), 1)
        message, created = results[0]

        self.assertTrue(created)
        self.assertIsNotNone(message.timestamp)
        # Should be milliseconds since epoch
        self.assertGreater(message.timestamp, 1700000000000)  # After Nov 2023

    def test_handles_missing_optional_fields(self):
        """Creates message successfully with minimal JSON data."""
        json_data = {
            'uuid': str(uuid.uuid4()),
            'type': 'user',
            'message': {
                'role': 'user',
                'content': 'Minimal message'
            }
        }

        results = Message.from_jsonl_claude_code_v2(
            json_data,
            context_heap=self.heap,
            sender=self.justin,
            message_number=1
        )

        self.assertEqual(len(results), 1)
        message, created = results[0]

        self.assertTrue(created)
        self.assertIsNone(message.timestamp)
        self.assertIsNone(message.session_id)
        self.assertIsNone(message.cwd)
        self.assertFalse(message.is_sidechain)

    def test_sanity_check_fails_on_timestamp_mismatch(self):
        """Raises ValueError if existing message has different timestamp."""
        msg_uuid = uuid.uuid4()

        # Create original message
        Message.objects.create(
            id=msg_uuid,
            message_number=1,
            content='Original message',
            context_heap=self.heap,
            sender=self.justin,
            timestamp=1729000000000  # Oct 15, 2024
        )

        # Try with different timestamp
        json_data = {
            'uuid': str(msg_uuid),
            'type': 'user',
            'timestamp': '2025-10-15T14:30:00.000Z',  # Oct 15, 2025 (different year)
            'message': {
                'role': 'user',
                'content': 'Content'
            }
        }

        with self.assertRaises(ValueError) as context:
            Message.from_jsonl_claude_code_v2(
                json_data,
                context_heap=self.heap,
                sender=self.justin,
                message_number=1
            )

        self.assertIn('different timestamp', str(context.exception))

    def test_sanity_check_fails_on_sender_mismatch(self):
        """Raises ValueError if existing message has different sender."""
        msg_uuid = uuid.uuid4()

        # Create original message from justin
        Message.objects.create(
            id=msg_uuid,
            message_number=1,
            content='Original message',
            context_heap=self.heap,
            sender=self.justin
        )

        # Try with different sender (magent)
        json_data = {
            'uuid': str(msg_uuid),
            'type': 'assistant',
            'message': {
                'role': 'assistant',
                'content': 'Content'
            }
        }

        with self.assertRaises(ValueError) as context:
            Message.from_jsonl_claude_code_v2(
                json_data,
                context_heap=self.heap,
                sender=self.magent,  # Different sender!
                message_number=1
            )

        self.assertIn('different sender', str(context.exception))

    def test_stores_raw_imported_content(self):
        """Stores raw JSON data in RawImportedContent."""
        json_data = {
            'uuid': str(uuid.uuid4()),
            'type': 'user',
            'sessionId': str(uuid.uuid4()),
            'timestamp': '2025-10-15T14:30:00.000Z',
            'message': {
                'role': 'user',
                'content': [{'type': 'text', 'text': 'Test message'}]
            }
        }

        results = Message.from_jsonl_claude_code_v2(
            json_data,
            context_heap=self.heap,
            sender=self.justin,
            message_number=1
        )

        self.assertEqual(len(results), 1)
        message, created = results[0]

        self.assertTrue(created)

        # Check RawImportedContent was created
        message_ct = ContentType.objects.get_for_model(message)
        raw_content = RawImportedContent.objects.get(
            content_type=message_ct,
            object_id=message.id
        )

        # Verify raw_data structure matches original JSONL
        self.assertEqual(raw_content.raw_data, json_data)
        self.assertEqual(raw_content.raw_data['uuid'], json_data['uuid'])
        self.assertEqual(raw_content.raw_data['type'], 'user')
        self.assertEqual(raw_content.raw_data['sessionId'], json_data['sessionId'])
        self.assertEqual(raw_content.raw_data['timestamp'], '2025-10-15T14:30:00.000Z')
        self.assertEqual(raw_content.raw_data['message']['role'], 'user')
        self.assertEqual(raw_content.raw_data['message']['content'][0]['type'], 'text')
        self.assertEqual(raw_content.raw_data['message']['content'][0]['text'], 'Test message')

    def test_does_not_store_raw_content_for_existing_message(self):
        """Does not create duplicate RawImportedContent on dedupe."""
        msg_uuid = uuid.uuid4()

        json_data = {
            'uuid': str(msg_uuid),
            'type': 'user',
            'sessionId': str(uuid.uuid4()),
            'message': {
                'role': 'user',
                'content': 'Test'
            }
        }

        # Create message first time
        results1 = Message.from_jsonl_claude_code_v2(
            json_data,
            context_heap=self.heap,
            sender=self.justin,
            message_number=1
        )
        message1, created1 = results1[0]
        self.assertTrue(created1)

        # Try to create again (should dedupe)
        results2 = Message.from_jsonl_claude_code_v2(
            json_data,
            context_heap=self.heap,
            sender=self.justin,
            message_number=1
        )
        message2, created2 = results2[0]
        self.assertFalse(created2)

        # Should only have ONE RawImportedContent
        message_ct = ContentType.objects.get_for_model(message1)
        raw_count = RawImportedContent.objects.filter(
            content_type=message_ct,
            object_id=msg_uuid
        ).count()

        self.assertEqual(raw_count, 1)

    def test_creates_thought_from_assistant_thinking(self):
        """Assistant message with thinking block creates base Message + Thought."""
        from conversations.models import Thought

        msg_uuid = uuid.uuid4()
        json_data = {
            'uuid': str(msg_uuid),
            'type': 'assistant',
            'sessionId': str(uuid.uuid4()),
            'message': {
                'role': 'assistant',
                'content': [
                    {
                        'type': 'thinking',
                        'thinking': 'Let me think about this problem...'
                    }
                ]
            }
        }

        results = Message.from_jsonl_claude_code_v2(
            json_data,
            context_heap=self.heap,
            sender=self.magent
            # Note: message_number should be set by import script, not here
        )

        # Should create 2 messages: base Message (with original UUID), Thought
        self.assertEqual(len(results), 2)

        # First is base Message with original UUID
        base_msg, base_created = results[0]
        self.assertTrue(base_created)
        self.assertEqual(base_msg.id, msg_uuid)
        self.assertEqual(base_msg.content, '[Message with attached content]')

        # Second is Thought with uuid5-generated ID
        thought, thought_created = results[1]
        self.assertTrue(thought_created)
        self.assertIsInstance(thought, Thought)
        self.assertEqual(thought.content, 'Let me think about this problem...')
        self.assertEqual(thought.signature, '')  # JSONL doesn't have signature

    def test_creates_tool_use_from_assistant_tool_call(self):
        """Assistant message with tool_use creates base Message + ToolUse."""
        from conversations.models import ToolUse

        msg_uuid = uuid.uuid4()
        json_data = {
            'uuid': str(msg_uuid),
            'type': 'assistant',
            'sessionId': str(uuid.uuid4()),
            'message': {
                'role': 'assistant',
                'content': [
                    {
                        'type': 'tool_use',
                        'id': 'toolu_01ABC123',
                        'name': 'Read',
                        'input': {'file_path': '/test/file.txt'}
                    }
                ]
            }
        }

        results = Message.from_jsonl_claude_code_v2(
            json_data,
            context_heap=self.heap,
            sender=self.magent
            # Note: message_number should be set by import script, not here
        )

        # Should create 2 messages: base Message (with original UUID), ToolUse
        self.assertEqual(len(results), 2)

        # First is base Message with original UUID
        base_msg, base_created = results[0]
        self.assertTrue(base_created)
        self.assertEqual(base_msg.id, msg_uuid)
        self.assertEqual(base_msg.content, '[Message with attached content]')

        # Second is ToolUse with uuid5-generated ID
        tool_use, tool_created = results[1]
        self.assertTrue(tool_created)
        self.assertIsInstance(tool_use, ToolUse)
        self.assertEqual(tool_use.tool_name, 'Read')
        self.assertEqual(tool_use.tool_id, 'toolu_01ABC123')
        self.assertEqual(tool_use.content, {'file_path': '/test/file.txt'})

    def test_creates_multiple_messages_from_assistant_with_mixed_content(self):
        """Assistant message with thinking + tool_use + text creates multiple messages."""
        from conversations.models import Thought, ToolUse

        json_data = {
            'uuid': str(uuid.uuid4()),
            'type': 'assistant',
            'sessionId': str(uuid.uuid4()),
            'message': {
                'role': 'assistant',
                'content': [
                    {'type': 'thinking', 'thinking': 'I need to read this file'},
                    {'type': 'tool_use', 'id': 'toolu_01ABC', 'name': 'Read', 'input': {}},
                    {'type': 'text', 'text': 'Let me check that file for you'}
                ]
            }
        }

        # Note: In reality, the import script would increment message_number for each
        # But from_json doesn't do that - it's the caller's responsibility
        # For this test, we don't pass message_number to let Django auto-generate it
        results = Message.from_jsonl_claude_code_v2(
            json_data,
            context_heap=self.heap,
            sender=self.magent
            # Note: no message_number passed - this test just verifies polymorphic creation
        )

        # Should create 4 messages: base Message (with original UUID), Thought, ToolUse
        # Note: Base message now always comes first to preserve UUID
        self.assertEqual(len(results), 3)

        # First MUST be base Message with original UUID and text content
        base_msg, created1 = results[0]
        self.assertTrue(created1)
        self.assertIsInstance(base_msg, Message)
        self.assertEqual(base_msg.content, 'Let me check that file for you')
        self.assertEqual(base_msg.id, uuid.UUID(json_data['uuid']))

        # Second should be Thought (with uuid5-generated ID)
        thought, created2 = results[1]
        self.assertTrue(created2)
        self.assertIsInstance(thought, Thought)
        self.assertEqual(thought.content, 'I need to read this file')

        # Third should be ToolUse (with uuid5-generated ID)
        tool_use, created3 = results[2]
        self.assertTrue(created3)
        self.assertIsInstance(tool_use, ToolUse)
        self.assertEqual(tool_use.tool_name, 'Read')

    def test_creates_tool_result_from_user_message(self):
        """User message with tool_result creates ToolResult object."""
        from conversations.models import ToolResult

        json_data = {
            'uuid': str(uuid.uuid4()),
            'type': 'user',
            'sessionId': str(uuid.uuid4()),
            'message': {
                'role': 'user',
                'content': [
                    {
                        'type': 'tool_result',
                        'tool_use_id': 'toolu_01ABC123',
                        'content': 'File contents here',
                        'is_error': False
                    }
                ]
            }
        }

        results = Message.from_jsonl_claude_code_v2(
            json_data,
            context_heap=self.heap,
            sender=self.justin,
            message_number=1
        )

        self.assertEqual(len(results), 1)
        message, created = results[0]

        self.assertTrue(created)
        self.assertIsInstance(message, ToolResult)
        self.assertEqual(message.tool_use_id, 'toolu_01ABC123')
        self.assertEqual(message.content, 'File contents here')
        self.assertFalse(message.is_error)

    def test_polymorphic_messages_each_get_raw_content(self):
        """Each polymorphic message from one JSONL line gets its own RawImportedContent."""
        json_data = {
            'uuid': str(uuid.uuid4()),
            'type': 'assistant',
            'sessionId': str(uuid.uuid4()),
            'message': {
                'role': 'assistant',
                'content': [
                    {'type': 'thinking', 'thinking': 'I need to read this file'},
                    {'type': 'tool_use', 'id': 'toolu_01ABC', 'name': 'Read', 'input': {'file_path': '/test.txt'}},
                    {'type': 'text', 'text': 'Let me check that file for you'}
                ]
            }
        }

        results = Message.from_jsonl_claude_code_v2(
            json_data,
            context_heap=self.heap,
            sender=self.magent
        )

        # Should have 3 messages (Thought, ToolUse, Message)
        self.assertEqual(len(results), 3)

        # Each message should have its own RawImportedContent
        for message, created in results:
            self.assertTrue(created)

            message_ct = ContentType.objects.get_for_model(message)
            raw_content = RawImportedContent.objects.get(
                content_type=message_ct,
                object_id=message.id
            )

            # All should reference the same source JSON
            self.assertEqual(raw_content.raw_data, json_data)
            self.assertEqual(raw_content.raw_data['uuid'], json_data['uuid'])

        # Verify we have exactly 3 RawImportedContent records
        total_raw = RawImportedContent.objects.filter(
            object_id__in=[msg.id for msg, _ in results]
        ).count()
        self.assertEqual(total_raw, 3)

    def test_preserves_original_uuid_for_tool_use_only_message(self):
        """Messages with ONLY tool_use (no text) preserve original UUID."""
        msg_uuid = uuid.uuid4()
        json_data = {
            'uuid': str(msg_uuid),
            'type': 'assistant',
            'sessionId': str(uuid.uuid4()),
            'timestamp': '2025-10-15T16:00:00.000Z',
            'message': {
                'role': 'assistant',
                'content': [
                    {
                        'type': 'tool_use',
                        'id': 'toolu_test123',
                        'name': 'Bash',
                        'input': {'command': 'ls -la'}
                    }
                ]
            }
        }

        results = Message.from_jsonl_claude_code_v2(
            json_data,
            context_heap=self.heap,
            parent=None,
            sender=self.magent
        )

        # Should create 2 messages: base Message + ToolUse
        self.assertEqual(len(results), 2)

        # First message MUST be base Message with original UUID
        base_msg, base_created = results[0]
        self.assertEqual(base_msg.id, msg_uuid)
        self.assertTrue(base_created)
        self.assertEqual(base_msg.content, '[Message with attached content]')

        # Second message is ToolUse with generated UUID
        tool_use, tool_created = results[1]
        self.assertNotEqual(tool_use.id, msg_uuid)  # Different UUID
        self.assertTrue(hasattr(tool_use, 'tooluse'))  # Is a ToolUse
        self.assertTrue(tool_created)

        # Verify original UUID exists in database
        original_exists = Message.objects.filter(id=msg_uuid).exists()
        self.assertTrue(original_exists)

    def test_preserves_original_uuid_for_thinking_only_message(self):
        """Messages with ONLY thinking (no text) preserve original UUID."""
        msg_uuid = uuid.uuid4()
        json_data = {
            'uuid': str(msg_uuid),
            'type': 'assistant',
            'sessionId': str(uuid.uuid4()),
            'timestamp': '2025-10-15T16:00:00.000Z',
            'message': {
                'role': 'assistant',
                'content': [
                    {
                        'type': 'thinking',
                        'thinking': 'Let me consider this carefully...'
                    }
                ]
            }
        }

        results = Message.from_jsonl_claude_code_v2(
            json_data,
            context_heap=self.heap,
            parent=None,
            sender=self.magent
        )

        # Should create 2 messages: base Message + Thought
        self.assertEqual(len(results), 2)

        # First message MUST be base Message with original UUID
        base_msg, base_created = results[0]
        self.assertEqual(base_msg.id, msg_uuid)
        self.assertTrue(base_created)
        self.assertEqual(base_msg.content, '[Message with attached content]')

        # Verify original UUID exists in database
        original_exists = Message.objects.filter(id=msg_uuid).exists()
        self.assertTrue(original_exists)

    def test_preserves_original_uuid_for_mixed_content_message(self):
        """Messages with thinking + tool_use + text preserve original UUID."""
        msg_uuid = uuid.uuid4()
        json_data = {
            'uuid': str(msg_uuid),
            'type': 'assistant',
            'sessionId': str(uuid.uuid4()),
            'timestamp': '2025-10-15T16:00:00.000Z',
            'message': {
                'role': 'assistant',
                'content': [
                    {'type': 'thinking', 'thinking': 'I should run this command...'},
                    {'type': 'tool_use', 'id': 'toolu_abc', 'name': 'Bash', 'input': {'command': 'pwd'}},
                    {'type': 'text', 'text': 'Running command to check directory'}
                ]
            }
        }

        results = Message.from_jsonl_claude_code_v2(
            json_data,
            context_heap=self.heap,
            parent=None,
            sender=self.magent
        )

        # Should create 3 messages: base Message (with text), Thought, ToolUse
        self.assertEqual(len(results), 3)

        # First message MUST be base Message with original UUID and text content
        base_msg, _ = results[0]
        self.assertEqual(base_msg.id, msg_uuid)
        self.assertIn('Running command', base_msg.content)

        # All other messages have different UUIDs
        for msg, _ in results[1:]:
            self.assertNotEqual(msg.id, msg_uuid)

        # Verify original UUID exists in database
        original_exists = Message.objects.filter(id=msg_uuid).exists()
        self.assertTrue(original_exists)
