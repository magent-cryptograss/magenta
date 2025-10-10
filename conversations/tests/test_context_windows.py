"""
Tests for ContextOpeningMessage and CompactingAction creation.

Tests the new polymorphic message structure where:
- ContextOpeningMessage IS the context window
- RegularMessage chains with parent and context_window
- CompactingAction marks when a context was closed
"""

import json
import tempfile
import uuid
from pathlib import Path
from django.test import TestCase
from conversations.models import (
    ThinkingEntity,
    ContextOpeningMessage,
    RegularMessage,
    CompactingAction
)


class ContextWindowTestCase(TestCase):
    """Test context window creation with new polymorphic structure."""

    def setUp(self):
        """Create thinking entities for tests."""
        self.justin = ThinkingEntity.objects.create(name='justin', is_biological_human=True)
        self.magent = ThinkingEntity.objects.create(name='magent', is_biological_human=False)

    def test_create_context_with_compacting_action(self):
        """Test creating a context window that ended with a compact event."""

        # First message opens the context
        opener = ContextOpeningMessage.objects.create(
            id='00000000-0000-0000-0000-000000000001',
            content="Let's build a memory system",
            sender=self.justin,
            timestamp=1726401600,
            session_id=uuid.uuid4(),
            source_file='test.jsonl'
        )
        opener.recipients.add(self.magent)

        # Chain of regular messages
        session_id = opener.session_id

        msg2 = RegularMessage.objects.create(
            id='00000000-0000-0000-0000-000000000002',
            content="Great idea! Let's start.",
            sender=self.magent,
            timestamp=1726401660,
            session_id=session_id,
            parent=opener,
            context_window=opener
        )
        msg2.recipients.add(self.justin)

        msg3 = RegularMessage.objects.create(
            id='00000000-0000-0000-0000-000000000003',
            content="Show me the code",
            sender=self.justin,
            timestamp=1726401720,
            session_id=session_id,
            parent=msg2,
            context_window=opener
        )
        msg3.recipients.add(self.magent)

        # Create CompactingAction to mark context as closed
        compacting = CompactingAction.objects.create(
            context_opening_message=opener,
            ending_message_id='00000000-0000-0000-0000-000000000003',
            summary='Discussion about memory systems',
            compact_trigger='manual',
            pre_compact_tokens=145000
        )

        # Verify structure
        self.assertEqual(opener.sender.name, 'justin')
        self.assertIn(self.magent, opener.recipients.all())
        self.assertEqual(opener.session_id, session_id)

        # Verify message chain
        self.assertEqual(msg2.parent, opener)
        self.assertEqual(msg2.context_window, opener)
        self.assertEqual(msg3.parent, msg2)
        self.assertEqual(msg3.context_window, opener)

        # Verify all messages in context
        context_messages = opener.messages.all()
        self.assertEqual(context_messages.count(), 2)  # msg2 and msg3
        context_message_ids = [str(msg.id) for msg in context_messages]
        self.assertIn(str(msg2.id), context_message_ids)
        self.assertIn(str(msg3.id), context_message_ids)

        # Verify compacting action
        self.assertEqual(opener.compacting_action.compact_trigger, 'manual')
        self.assertEqual(opener.compacting_action.pre_compact_tokens, 145000)
        self.assertEqual(opener.compacting_action.summary, 'Discussion about memory systems')

        print("✓ Context window with compacting test passed!")
        print(f"  Opener: {opener}")
        print(f"  Messages in context: {context_messages.count()}")
        print(f"  Compacting: {compacting}")

    def test_context_without_compacting(self):
        """Test creating a context window that just ended (no compact)."""

        opener = ContextOpeningMessage.objects.create(
            id='00000000-0000-0000-0000-000000000005',
            content="Quick question",
            sender=self.justin,
            timestamp=1726405200,
            session_id=uuid.uuid4()
        )
        opener.recipients.add(self.magent)

        msg2 = RegularMessage.objects.create(
            id='00000000-0000-0000-0000-000000000006',
            content="Sure, what is it?",
            sender=self.magent,
            timestamp=1726405260,
            session_id=opener.session_id,
            parent=opener,
            context_window=opener
        )
        msg2.recipients.add(self.justin)

        # Verify context works without compacting action
        self.assertEqual(opener.messages.count(), 1)
        self.assertFalse(hasattr(opener, 'compacting_action'))

        print("✓ Non-compacted context test passed!")
        print(f"  Opener: {opener}")
        print(f"  Has compacting action: {hasattr(opener, 'compacting_action')}")

    def test_multiple_recipients(self):
        """Test message with multiple recipients."""

        rj = ThinkingEntity.objects.create(name='rj', is_biological_human=True)

        opener = ContextOpeningMessage.objects.create(
            id='00000000-0000-0000-0000-000000000007',
            content="Hey team, let's collaborate",
            sender=self.justin,
            timestamp=1726408800,
            session_id=uuid.uuid4()
        )
        opener.recipients.add(self.magent, rj)

        # Verify multiple recipients
        self.assertEqual(opener.recipients.count(), 2)
        self.assertIn(self.magent, opener.recipients.all())
        self.assertIn(rj, opener.recipients.all())

        print("✓ Multiple recipients test passed!")
        print(f"  Recipients: {[r.name for r in opener.recipients.all()]}")


if __name__ == '__main__':
    import django
    django.setup()
    from django.test.utils import get_runner
    from django.conf import settings

    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(["conversations.tests.test_context_windows"])
