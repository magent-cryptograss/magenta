"""
Conversation models for memory archive.

Structure:
- Era - groups related context heaps (e.g., "Era 0", "Era 1")
  - ContextHeap - a single context heap within an era
    - Message - messages accumulate in heaps until compacting

Message hierarchy (polymorphic):
- Message (concrete base) - common fields including content
  - Thought - signed thinking message
  - ToolUse - tool calls with parameters
  - ToolResult - tool execution results
"""

from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
import uuid


# ============================================================================
# Thinking Entity Model
# ============================================================================

class ThinkingEntity(models.Model):
    """
    A thinking entity - human or AI.

    Most details about an entity come from inward-pointing relationships
    from other models (messages sent, messages received, etc).
    """

    name = models.CharField(max_length=50, unique=True, primary_key=True)
    is_biological_human = models.BooleanField(default=True)

    class Meta:
        db_table = 'thinking_entities'
        verbose_name_plural = 'thinking entities'

    def __str__(self):
        return self.name


# ============================================================================
# Era and Context Heap Models
# ============================================================================

class Era(models.Model):
    """
    A named era in conversation history.

    Sometimes, this represents a time when previous context was lost or otherwise not used.
    In others, it is significant change in the runtime environment of the client(s) being used by the agent(s).
    In still others, it represents a significant "life event" or inflection point for the agents' understanding and story.

    Eras group related context heaps together.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'eras'
        ordering = ['created_at']

    def earliest_blockheight(self):
        """Returns the earliest blockheight from all messages in this era."""
        from django.db.models import Min
        result = Message.objects.filter(
            context_heap__era=self,
            eth_blockheight__isnull=False
        ).aggregate(earliest=Min('eth_blockheight'))
        return result['earliest']

    def latest_blockheight(self):
        """Returns the latest blockheight from all messages in this era."""
        from django.db.models import Max
        result = Message.objects.filter(
            context_heap__era=self,
            eth_blockheight__isnull=False
        ).aggregate(latest=Max('eth_blockheight'))
        return result['latest']

    def __str__(self):
        return self.name


class ContextHeapType(models.TextChoices):
    """Types of context heaps based on why they were created."""
    FRESH = 'fresh', 'Fresh conversation'
    POST_COMPACTING = 'post_compacting', 'After compacting'
    SPLIT_POINT = 'split_point', 'Context split'


class ContextHeap(models.Model):
    """
    This is the short-term memory of an AI ThinkingEntity.

    The 'heap' of context (in some circles, this is called a "Context Window") represents the
    conversational knowledge to which an LLM can have ready-access at any given prompt.

    Heaps are occasionally "compacted" in order to preserve the conversational and work flow.
    The CompactingActions represent the end of a heap and also usually the beginning of another.

    The 'type' field indicates why this context heap was created:
    - FRESH: Beginning of a new conversation
    - POST_COMPACTING: Started after a context compacting operation
    - SPLIT_POINT: Created due to export splits or model changes

    For SPLIT_POINT heaps, first_message points to the message in the parent heap
    where the split occurred (i.e., first_message.context_heap != self).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    era = models.ForeignKey(Era, models.CASCADE, related_name='context_heaps')
    first_message = models.ForeignKey(
        'Message',
        models.CASCADE,
        related_name='opened_heaps'
    )
    type = models.CharField(
        max_length=20,
        choices=ContextHeapType.choices,
        default=ContextHeapType.FRESH
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'context_heaps'
        ordering = ['created_at']

    def __str__(self):
        return f"{self.era.name} - {self.get_type_display()} - Heap starting at msg #{self.first_message.message_number}"

    def parent_heap(self):
        """For SPLIT_POINT heaps, return the heap they split from."""
        if self.type != ContextHeapType.SPLIT_POINT:
            return None
        return self.first_message.context_heap  # Will be different from self

    def earliest_blockheight(self):
        """Returns the earliest blockheight from messages in this heap."""
        result = self.messages.filter(eth_blockheight__isnull=False).aggregate(
            earliest=models.Min('eth_blockheight')
        )
        return result['earliest']

    def latest_blockheight(self):
        """Returns the latest blockheight from messages in this heap."""
        result = self.messages.filter(eth_blockheight__isnull=False).aggregate(
            latest=models.Max('eth_blockheight')
        )
        return result['latest']


# ============================================================================
# Message Models (Polymorphic)
# ============================================================================

class Message(models.Model):
    """
    Base class for all message types.

    All messages have content (JSONField to handle both text and structured data).
    All messages belong to a context heap.
    Messages can optionally have a parent for threading.
    """

    # Identity (from client)
    id = models.UUIDField(primary_key=True)
    message_number = models.IntegerField(null=True, blank=True)

    # Content - all messages have content
    content = models.JSONField()

    # Context - all messages belong to a heap
    context_heap = models.ForeignKey('ContextHeap', models.CASCADE, related_name='messages', null=True, blank=True)

    # Threading - optional parent for message chains
    parent = models.ForeignKey('self', models.CASCADE, related_name='children', null=True, blank=True)

    # Participants
    sender = models.ForeignKey(ThinkingEntity, models.CASCADE, related_name='sent_messages')
    recipients = models.ManyToManyField(ThinkingEntity, related_name='received_messages')

    # Session context
    session_id = models.UUIDField(null=True, blank=True)

    # Temporal tracking
    timestamp = models.BigIntegerField(null=True, blank=True)
    eth_blockheight = models.BigIntegerField(null=True, blank=True)
    eth_block_offset = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    # Metadata
    model_backend = models.CharField(max_length=100, null=True, blank=True)
    stop_reason = models.CharField(max_length=50, null=True, blank=True)
    source_file = models.CharField(max_length=255, null=True, blank=True)
    missing_from_markdown = models.BooleanField(default=False)

    # Usage tracking
    input_tokens = models.IntegerField(null=True, blank=True)
    output_tokens = models.IntegerField(null=True, blank=True)
    cache_creation_input_tokens = models.IntegerField(null=True, blank=True)
    cache_read_input_tokens = models.IntegerField(null=True, blank=True)

    # Flags
    is_sidechain = models.BooleanField(default=False)
    is_synthetic_error = models.BooleanField(default=False)  # Claude Code synthetic error response
    is_retry = models.BooleanField(default=False)  # User retry due to timeout/error
    is_continuation_message = models.BooleanField(default=False)  # System-injected summary at start of post-compact session

    # Environment context
    cwd = models.TextField(null=True, blank=True)
    git_branch = models.CharField(max_length=255, null=True, blank=True)
    client_version = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['session_id', 'timestamp']),
            models.Index(fields=['sender']),
        ]
        unique_together = [['context_heap', 'message_number']]

    def __str__(self):
        recipient_names = ','.join(r.name for r in self.recipients.all()) if self.pk else '?'
        return f"{self.sender}→{recipient_names} at {self.timestamp}"

    @property
    def has_children(self):
        """Check if this message has any children."""
        return hasattr(self, 'children') and self.children.exists()

    def get_descendants(self):
        """Recursively get all descendants of this message."""
        if not hasattr(self, 'children'):
            return []
        descendants = []
        for child in self.children.all():
            descendants.append(child)
            descendants.extend(child.get_descendants())
        return descendants


class Thought(Message):
    """
    Thinking message - represents the interal monologue of an AI ThinkingEntity.

    These are apparently sometimes signed (perhaps cryptographically?) by the vendor of LLM clients.
    """

    signature = models.TextField()

    def __str__(self):
        preview = str(self.content)[:50] + '...' if len(str(self.content)) > 50 else str(self.content)
        return f"[Thought] {preview}"


class ToolUse(Message):
    """
    Tool call message.

    Records when the assistant calls a tool with specific parameters.
    Links to ToolResult via tool_id.
    """

    tool_name = models.CharField(max_length=100)
    tool_id = models.CharField(max_length=100, unique=True)  # "toolu_01Eu..."

    def __str__(self):
        return f"[ToolUse] {self.tool_name} ({self.tool_id})"

    def get_result(self):
        """Get the corresponding ToolResult message."""
        try:
            return ToolResult.objects.get(tool_use_id=self.tool_id)
        except ToolResult.DoesNotExist:
            return None


class ToolResult(Message):
    """
    Tool execution result.

    Links back to the ToolUse message via tool_use_id.
    Content contains output/stdout/stderr as JSON.
    """

    tool_use_id = models.CharField(max_length=100, db_index=True)  # Links to ToolUse.tool_id
    is_error = models.BooleanField(default=False)

    def __str__(self):
        status = "ERROR" if self.is_error else "OK"
        preview = str(self.content)[:50] + '...' if len(str(self.content)) > 50 else str(self.content)
        return f"[ToolResult] {status}: {preview}"

    def get_tool_use(self):
        """Get the corresponding ToolUse message."""
        try:
            return ToolUse.objects.get(tool_id=self.tool_use_id)
        except ToolUse.DoesNotExist:
            return None


# ============================================================================
# Compacting Action
# ============================================================================

class CompactingAction(models.Model):
    """
    Records when a context heap was closed via compacting.

    Points to the ContextHeap that was closed.
    Not all context heaps have a CompactingAction - some end naturally.

    context_heap can be null during import when we find summaries before
    we've imported the context heap they belong to.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    context_heap = models.OneToOneField(
        ContextHeap,
        models.CASCADE,
        null=True,
        blank=True,
        related_name='compacting_action'
    )
    ending_message_id = models.UUIDField(null=True, blank=True)  # Last message before compact
    compact_boundary_message_id = models.UUIDField(null=True, blank=True)
    continuation_message = models.ForeignKey(
        Message,
        models.SET_NULL,
        null=True,
        blank=True,
        related_name='continuation_for_compacting_action'
    )  # The system-injected summary message at start of next heap
    summary = models.TextField(null=True, blank=True)
    compact_trigger = models.CharField(max_length=50, null=True, blank=True)
    pre_compact_tokens = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'compacting_actions'

    def __str__(self):
        trigger = self.compact_trigger or 'unknown'
        tokens = f"{self.pre_compact_tokens:,}" if self.pre_compact_tokens else '?'
        heap = f"heap {str(self.context_heap_id)[:8]}" if self.context_heap_id else "orphaned"
        return f"Compact ({trigger}, {tokens} tokens, {heap})"


# ============================================================================
# Supporting Models
# ============================================================================

class Topic(models.Model):
    """A topic that can be tagged on messages."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    category = models.CharField(max_length=50, default='misc')
    description = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'topics'
        ordering = ['name']

    def __str__(self):
        return self.name


class MessageTopic(models.Model):
    """Many-to-many relationship between messages and topics with relevance."""

    message_id = models.UUIDField()
    topic = models.ForeignKey(Topic, models.CASCADE)
    relevance = models.IntegerField(default=5, help_text="1-10 scale")

    class Meta:
        db_table = 'message_topics'
        unique_together = ['message_id', 'topic']

    def __str__(self):
        return f"{self.message_id}: {self.topic.name} ({self.relevance})"


class Note(models.Model):
    """
    Notes about various objects (messages, context windows, eras).

    Notes are authored by thinking entities (humans or AI) and can be attached to
    any model using generic foreign keys.

    Examples: import metadata, editorial comments, corrections, context about
    incomplete conversations, compacting decisions.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Generic foreign key to attach notes to any model
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.UUIDField()
    about = GenericForeignKey('content_type', 'object_id')

    # Who wrote this note
    from_entity = models.ForeignKey(ThinkingEntity, models.CASCADE, related_name='authored_notes')

    content = models.TextField()
    eth_blockheight = models.BigIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notes'
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
        ]
        ordering = ['created_at']

    def __str__(self):
        preview = self.content[:50] + '...' if len(self.content) > 50 else self.content
        return f"Note by {self.from_entity}: {preview}"


class ConversationFile(models.Model):
    """Tracks which messages came from which conversation files."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    filename = models.CharField(max_length=255)
    file_path = models.TextField(null=True, blank=True)
    beginning_message_id = models.UUIDField(null=True, blank=True)
    ending_message_id = models.UUIDField(null=True, blank=True)
    checksum = models.CharField(max_length=64, null=True, blank=True)
    message_count = models.IntegerField(null=True, blank=True)
    imported_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'conversation_files'
        ordering = ['-imported_at']

    def __str__(self):
        return f"{self.filename} ({self.message_count} messages)"


class RawImportedContent(models.Model):
    """
    Stores raw imported data for debugging purposes.

    Can be attached to any model (Message, CompactingAction, etc.)
    to preserve the original import format for troubleshooting.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Generic foreign key to attach to any object
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.UUIDField()
    about = GenericForeignKey('content_type', 'object_id')

    # The raw data as imported
    raw_data = models.JSONField()

    # Import metadata
    source_file = models.ForeignKey(ConversationFile, models.SET_NULL, null=True, blank=True, related_name='raw_imports')
    imported_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'raw_imported_content'
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
        ]

    def __str__(self):
        return f"Raw data for {self.content_type} {str(self.object_id)[:8]}"
