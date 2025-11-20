"""
Memory service - handles querying conversation history.

All methods are synchronous Django ORM queries.
Called via sync_to_async from MCP tools.
"""

from conversations.models import Message, Era, ContextHeap
from django.db.models import Q
import random


class MemoryService:
    """Service for querying conversation memory"""

    @staticmethod
    def get_latest_continuation():
        """Get the most recent continuation message"""
        return Message.objects.filter(
            is_continuation_message=True
        ).order_by('-created_at').first()

    @staticmethod
    def get_message_by_id(message_id):
        """Get a specific message by its UUID"""
        try:
            return Message.objects.get(id=message_id)
        except Message.DoesNotExist:
            return None

    @staticmethod
    def get_messages_before(reference_id=None, reference_timestamp=None, limit=300):
        """Get N messages before a reference point"""
        if reference_id:
            ref_msg = Message.objects.get(id=reference_id)
            messages = Message.objects.filter(
                created_at__lt=ref_msg.created_at
            ).order_by('-created_at')[:limit]
        elif reference_timestamp:
            messages = Message.objects.filter(
                created_at__lt=reference_timestamp
            ).order_by('-created_at')[:limit]
        else:
            messages = Message.objects.order_by('-created_at')[:limit]

        return list(messages)

    @staticmethod
    def get_era_summary(era_name="Compacting Meta-Conversation (Era 1)"):
        """Get messages from a specific era"""
        try:
            era = Era.objects.get(name=era_name)
            heaps = ContextHeap.objects.filter(era=era)
            messages = Message.objects.filter(
                context_heap__in=heaps
            ).order_by('message_number')[:100]
            return {
                'era': era,
                'messages': list(messages)
            }
        except Era.DoesNotExist:
            return None

    @staticmethod
    def get_context_heap(heap_id):
        """Get all messages from a specific context heap"""
        try:
            heap = ContextHeap.objects.get(id=heap_id)
            messages = Message.objects.filter(
                context_heap=heap
            ).order_by('message_number')
            return {
                'heap': heap,
                'messages': list(messages)
            }
        except ContextHeap.DoesNotExist:
            return None

    @staticmethod
    def search_messages(query, limit=50):
        """Full-text search for messages"""
        # PostgreSQL full-text search
        from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector

        search_vector = SearchVector('content')
        search_query = SearchQuery(query)

        messages = Message.objects.annotate(
            rank=SearchRank(search_vector, search_query)
        ).filter(
            rank__gt=0
        ).order_by('-rank', '-created_at')[:limit]

        return list(messages)

    @staticmethod
    def get_recent_work(limit=50):
        """Get most recent messages"""
        messages = Message.objects.order_by('-created_at')[:limit]
        return list(messages)

    @staticmethod
    def get_random_messages_with_context(count=4, context_messages=4):
        """Get random messages with following context"""
        total = Message.objects.count()
        if total == 0:
            return []

        # Get random message IDs
        all_ids = list(Message.objects.values_list('id', flat=True))
        random_ids = random.sample(all_ids, min(count, len(all_ids)))

        results = []
        for msg_id in random_ids:
            random_msg = Message.objects.get(id=msg_id)

            # Get this message plus N following messages
            following = list(Message.objects.filter(
                created_at__gte=random_msg.created_at
            ).order_by('created_at')[:(context_messages + 1)])

            results.append({
                'starting_message': random_msg,
                'context': following
            })

        return results

    @staticmethod
    def get_recent_messages_by_chars(max_chars=10000):
        """Get recent messages up to a character limit"""
        messages = []
        total_chars = 0

        for msg in Message.objects.order_by('-created_at'):
            content_str = str(msg.content)
            if total_chars + len(content_str) > max_chars:
                break
            messages.append(msg)
            total_chars += len(content_str)

        return messages, total_chars

    @staticmethod
    def get_awakening_reflection():
        """Get most recent 'reawaken and breathe' message"""
        # TODO: Query by topic once topic tagging is working
        # For now, search for messages from magent containing "reawaken" or "breathe"
        return Message.objects.filter(
            Q(sender_id='magent') &
            (Q(content__icontains='reawaken') | Q(content__icontains='breathe'))
        ).order_by('-created_at').first()
