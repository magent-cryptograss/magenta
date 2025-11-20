"""
Tests for CompactingAction.from_jsonl_claude_code_v2() classmethod.
"""

import uuid
from django.test import TestCase
from conversations.models import (
    CompactingAction, ThinkingEntity, Era, ContextHeap, ContextHeapType, Message
)


class CompactingActionFromJsonlTests(TestCase):
    """Test CompactingAction.from_jsonl_claude_code_v2() deduplication and instantiation."""

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

    def test_creates_new_compacting_action(self):
        """Creating a new CompactingAction returns (action, True)."""
        summary_data = {
            'type': 'summary',
            'summary': 'Discussion about memory systems and database design',
            'leafUuid': str(uuid.uuid4())
        }

        compact, created = CompactingAction.from_jsonl_claude_code_v2(
            summary_data,
            context_heap=self.heap
        )

        self.assertTrue(created)
        self.assertEqual(compact.summary, 'Discussion about memory systems and database design')
        self.assertEqual(compact.compact_trigger, 'user_initiated')
        self.assertEqual(compact.pre_compact_tokens, 0)
        self.assertEqual(compact.context_heap, self.heap)
        self.assertIsNotNone(compact.compact_boundary_message_id)

    def test_generates_deterministic_id(self):
        """Same summary data generates same UUID."""
        summary_data = {
            'type': 'summary',
            'summary': 'Test summary',
            'leafUuid': '00000000-0000-0000-0000-000000000001'
        }

        compact1, created1 = CompactingAction.from_jsonl_claude_code_v2(summary_data)
        compact2, created2 = CompactingAction.from_jsonl_claude_code_v2(summary_data)

        self.assertTrue(created1)
        self.assertFalse(created2)
        self.assertEqual(compact1.id, compact2.id)

    def test_different_summaries_get_different_ids(self):
        """Different summary data generates different UUIDs."""
        summary_data_1 = {
            'type': 'summary',
            'summary': 'First summary',
            'leafUuid': '00000000-0000-0000-0000-000000000001'
        }

        summary_data_2 = {
            'type': 'summary',
            'summary': 'Second summary',
            'leafUuid': '00000000-0000-0000-0000-000000000002'
        }

        compact1, _ = CompactingAction.from_jsonl_claude_code_v2(summary_data_1)
        compact2, _ = CompactingAction.from_jsonl_claude_code_v2(summary_data_2)

        self.assertNotEqual(compact1.id, compact2.id)

    def test_allows_orphaned_compacting_action(self):
        """Can create CompactingAction without context_heap (orphaned)."""
        summary_data = {
            'type': 'summary',
            'summary': 'Orphaned compact',
            'leafUuid': str(uuid.uuid4())
        }

        compact, created = CompactingAction.from_jsonl_claude_code_v2(summary_data)

        self.assertTrue(created)
        self.assertIsNone(compact.context_heap)
        self.assertEqual(compact.summary, 'Orphaned compact')

    def test_accepts_extra_fields(self):
        """Extra fields like ending_message_id are set correctly."""
        ending_msg_id = uuid.uuid4()
        summary_data = {
            'type': 'summary',
            'summary': 'Test',
            'leafUuid': str(uuid.uuid4())
        }

        compact, created = CompactingAction.from_jsonl_claude_code_v2(
            summary_data,
            context_heap=self.heap,
            ending_message_id=ending_msg_id
        )

        self.assertTrue(created)
        self.assertEqual(compact.ending_message_id, ending_msg_id)
        self.assertEqual(compact.context_heap, self.heap)

    def test_handles_missing_leaf_uuid(self):
        """Handles summary data without leafUuid."""
        summary_data = {
            'type': 'summary',
            'summary': 'Summary without leaf UUID'
        }

        compact, created = CompactingAction.from_jsonl_claude_code_v2(summary_data)

        self.assertTrue(created)
        self.assertIsNone(compact.compact_boundary_message_id)

    def test_deduplication_preserves_original(self):
        """Calling with same summary twice returns original, doesn't update."""
        summary_data = {
            'type': 'summary',
            'summary': 'Original summary',
            'leafUuid': str(uuid.uuid4())
        }

        # Create first time
        compact1, created1 = CompactingAction.from_jsonl_claude_code_v2(
            summary_data,
            context_heap=self.heap
        )
        self.assertTrue(created1)
        self.assertEqual(compact1.context_heap, self.heap)

        # Try to create again with different context_heap (should preserve original)
        era2 = Era.objects.create(name='Era 2')
        first_msg2 = Message.objects.create(
            id=uuid.uuid4(),
            message_number=0,
            content='First message',
            sender=self.justin
        )
        first_msg2.recipients.add(self.magent)
        heap2 = ContextHeap.objects.create(
            era=era2,
            first_message=first_msg2,
            type=ContextHeapType.FRESH
        )

        compact2, created2 = CompactingAction.from_jsonl_claude_code_v2(
            summary_data,
            context_heap=heap2  # Different heap
        )

        self.assertFalse(created2)
        self.assertEqual(compact1.id, compact2.id)
        self.assertEqual(compact2.context_heap, self.heap)  # Keeps original heap

    def test_stores_raw_imported_content(self):
        """Stores raw summary data in RawImportedContent."""
        from django.contrib.contenttypes.models import ContentType
        from conversations.models import RawImportedContent

        summary_data = {
            'type': 'summary',
            'summary': 'Test summary for raw content',
            'leafUuid': str(uuid.uuid4())
        }

        compact, created = CompactingAction.from_jsonl_claude_code_v2(summary_data)

        self.assertTrue(created)

        # Check RawImportedContent was created
        compact_ct = ContentType.objects.get_for_model(compact)
        raw_content = RawImportedContent.objects.get(
            content_type=compact_ct,
            object_id=compact.id
        )

        # Verify raw_data structure matches original summary
        self.assertEqual(raw_content.raw_data, summary_data)
        self.assertEqual(raw_content.raw_data['type'], 'summary')
        self.assertEqual(raw_content.raw_data['summary'], 'Test summary for raw content')
        self.assertEqual(raw_content.raw_data['leafUuid'], summary_data['leafUuid'])

    def test_does_not_store_raw_content_for_existing_ca(self):
        """Does not create duplicate RawImportedContent on dedupe."""
        from django.contrib.contenttypes.models import ContentType
        from conversations.models import RawImportedContent

        summary_data = {
            'type': 'summary',
            'summary': 'Dedupe test',
            'leafUuid': str(uuid.uuid4())
        }

        # Create first time
        compact1, created1 = CompactingAction.from_jsonl_claude_code_v2(summary_data)
        self.assertTrue(created1)

        # Try to create again (should dedupe)
        compact2, created2 = CompactingAction.from_jsonl_claude_code_v2(summary_data)
        self.assertFalse(created2)

        # Should only have ONE RawImportedContent
        compact_ct = ContentType.objects.get_for_model(compact1)
        raw_count = RawImportedContent.objects.filter(
            content_type=compact_ct,
            object_id=compact1.id
        ).count()

        self.assertEqual(raw_count, 1)
