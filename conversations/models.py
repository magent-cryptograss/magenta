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
import uuid, json, hashlib


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
    apparent_duplicate = models.BooleanField(default=False, help_text='True if this message was encountered again during import with different content (likely whitespace differences)')

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

    @staticmethod
    def sanitize_content(content):
        """
        Remove null bytes and other problematic characters from content.
        PostgreSQL JSON fields cannot contain \u0000 (null bytes).
        """
        if isinstance(content, str):
            # Remove null bytes
            content = content.replace('\x00', '')
        elif isinstance(content, list):
            content = [Message.sanitize_content(item) for item in content]
        elif isinstance(content, dict):
            return {k: Message.sanitize_content(v) for k, v in content.items()}
        return content

    @classmethod
    def detect_event_type_claude_code_v2(cls, event_line):
        """
        Takes a line from a claude code vs JSONL file, returns its message type.
        """
        try:
            event = json.loads(event_line)
        except json.JSONDecodeError:
            raise

        if event['type'] == 'summary':
            event_type = "summary"
        elif event['type'] == 'system':
            if event['subtype'] == "compact_boundary":
                pass # magent: let's put some logic here to instantiate a SystemMessage?
            else:
                raise RuntimeError("What other system types are there?")
        else:
            message = event['message']
            role = message['role']
            content = message['content']
            
            # Sanity check - what does it mean if content has more than one member?
            if len(content) > 1:
                if type(content) == str:
                    # It seems like this scenario can happen when a message wasn't successfully sent
                    # due to a client error or network problem.
                    event_type = "uncertain message"
                else:
                    raise RuntimeError("Content has more than one member.  Not sure what to do.")
                return event_type, event
            
            first_content = content[0]

            if first_content['type'] == 'text':
                if first_content['text'].startswith("This session is being continued"):
                    # TODO: Modify participants?  #12
                    event_type = "continuation"
                elif first_content['text'].startswith("Caveat: The messages below were generated by the user"):
                    event_type = "caveat"
                elif first_content['text'].startswith("<command"):
                    event_type = "command"
                elif first_content['text'].startswith("<local-command-stdout"):
                    event_type = "command result - success"
                else:
                    event_type = "regular message"
            ######
            ### All the types other than "text", where we have some strucutred data to determine type.
            ######
            elif first_content['type'] == 'thinking':
                event_type = "thought"
            elif first_content['type'] == 'tool_use':
                event_type = "tool use"
            elif first_content['type'] == 'tool_result':
                event_type = "tool result"
            else:
                assert False

            

        return event_type, event

    @classmethod
    def from_jsonl_claude_code_v2(cls, message_line, **extra_fields):
        """
        Create or get Message(s) from Claude Code v2 JSONL format with deduplication.

        **UUID PRESERVATION POLICY:**
        The original UUID from the JSONL is ALWAYS preserved as a base Message object,
        even if the message contains only tool_use/thinking blocks with no text content.
        This ensures CompactingActions and other references can reliably find messages.

        A single JSONL line can produce multiple Message objects:
        - Base Message with original UUID (ALWAYS created)
        - Assistant messages with thinking blocks → Thought objects (uuid5-generated IDs)
        - Assistant messages with tool_use → ToolUse objects (uuid5-generated IDs)
        - Messages with tool_result → ToolResult objects (uuid5-generated IDs)

        The base Message is always returned first in the list.

        Args:
            json_data: Dict from JSONL with keys like uuid, type, message, timestamp, etc.
            **extra_fields: Additional fields to set (context_heap, parent, sender, etc.)

        Returns:
            list of tuples: [(message_instance, created_bool), ...]
            First tuple is always the base Message with original UUID.

        Raises:
            ValueError: If existing message doesn't match new data
        """
        import uuid as uuid_lib
        from django.utils.dateparse import parse_datetime

        msg_uuid = uuid_lib.UUID(message_line.get('uuid'))


        #### Actual message parsing
        # Check content - extract text content from JSON
        msg_type = message_line.get('type')

        try:
            message_items = message_line['message']
        except KeyError:
            raise

        message_text = ''

        if isinstance(message_items, str):
            message_text = message_items
            # TODO: Can this happen? magent added this block, but we're not sure why.
            raise RuntimeError("Why is message_items a str?")
        else:
            # Extract text from content items
            for item_name, item_payload_list in message_items.items():
                if item_name == "role":
                    continue # TODO: Is there where we do participant analysis?  #12
                if item_name == "content":
                    # Here's the content of the message.
                    if len(item_payload_list) > 1:
                        raise RuntimeError('item_payload is longer than one item')  # TODO: How do we handle this?
                    else:
                        item_payload = item_payload_list[0]

                    if item_payload['type'] == "text":
                        # This is a text message.
                        message_text = item_payload['text']
                    else:

                    #####
                    ## Handle tool uses and thoughts and such.

                        raise RuntimeError # TODO: What happens here?

                    ####








            # TODO: Is there some reason we need to .strip message_text?
            # new_content = new_content.strip()


        # Check if message already exists
        try:
            existing = cls.objects.get(id=msg_uuid)

            # Compare with existing content (convert JSONField to string if needed)
            existing_content = str(existing.content) if existing.content else ''
            
            if message_text != existing_content:
                # Mark as apparent duplicate instead of raising exception
                existing.apparent_duplicate = True
                existing.save()
                import sys
                print(f"WARNING: Message {msg_uuid} already exists with different content (marking as apparent_duplicate)", file=sys.stderr)
                print(f"  Existing ({len(existing_content)} chars): {existing_content[:100]}...", file=sys.stderr)
                print(f"  New ({len(message_text)} chars): {message_text[:100]}...", file=sys.stderr)

                # OK, we have an existing message... but it doesn't match the one we just found with the same UID.
                # Seems like a data integrity issue.
                raise RuntimeError("Duplicate message that doesn't match - huh?")

                # Message exists and passes sanity checks - return as list
                # return [(existing, False)]
            
            return existing, False

        except cls.DoesNotExist:
            pass  # Message doesn't exist, create it

        # Parse timestamp once
        timestamp_str = message_line.get('timestamp')
        timestamp = None
        if timestamp_str:
            dt = parse_datetime(timestamp_str)
            if dt:
                timestamp = int(dt.timestamp() * 1000)

        # Common fields for all message types
        common_fields = {
            'timestamp': timestamp,
            'session_id': uuid_lib.UUID(message_line.get('sessionId')) if message_line.get('sessionId') else None,
            'source_file': message_line.get('source_file'),
            'cwd': message_line.get('cwd'),
            'git_branch': message_line.get('gitBranch'),
            'client_version': message_line.get('version'),
            'is_sidechain': message_line.get('isSidechain', False),
            **extra_fields  # context_heap, parent, sender, message_number, etc.
        }

        # Check if synthetic error
        model = message_line.get('message', {}).get('model', '')
        is_synthetic = (model == '<synthetic>')

        # Extract content items
        msg_type = message_line.get('type')
        message_items = message_line.get('message', {}).get('content', [])

        # Handle tool_result disguised as user message
        if msg_type == 'user' and isinstance(message_items, list) and len(message_items) == 1:
            first_item = message_items[0]
            if isinstance(first_item, dict) and first_item.get('type') == 'tool_result':
                # Import ToolResult here to avoid circular import
                from conversations.models import ToolResult

                result_msg, created = ToolResult.objects.get_or_create(
                    id=msg_uuid,
                    defaults={
                        **common_fields,
                        'content': cls.sanitize_content(first_item.get('content', '')),
                        'tool_use_id': first_item.get('tool_use_id', ''),
                        'is_error': first_item.get('is_error', False)
                    }
                )

                if created:
                    cls._store_raw_content(result_msg, message_line, extra_fields)

                return [(result_msg, created)]

        # Collect messages to return
        messages = []

        # Process assistant message content items (can be multiple)
        if msg_type == 'assistant':
            # Process thinking blocks
            for item in message_items:
                if isinstance(item, dict) and item.get('type') == 'thinking':
                    from conversations.models import Thought

                    thinking_uuid = uuid_lib.uuid5(msg_uuid, 'thinking')
                    thought, created = Thought.objects.get_or_create(
                        id=thinking_uuid,
                        defaults={
                            **common_fields,
                            'content': cls.sanitize_content(item.get('thinking', '')),
                            'signature': ''  # JSONL doesn't have signature
                        }
                    )

                    if created:
                        cls._store_raw_content(thought, message_line, extra_fields)

                    messages.append((thought, created))

            # Process tool uses
            for item in message_items:
                if isinstance(item, dict) and item.get('type') == 'tool_use':
                    from conversations.models import ToolUse

                    tool_uuid = uuid_lib.uuid5(msg_uuid, f"tool_use_{item.get('id')}")
                    tool_use, created = ToolUse.objects.get_or_create(
                        id=tool_uuid,
                        defaults={
                            **common_fields,
                            'content': cls.sanitize_content(item.get('input', {})),
                            'tool_name': item.get('name', ''),
                            'tool_id': item.get('id', '')
                        }
                    )

                    if created:
                        cls._store_raw_content(tool_use, message_line, extra_fields)

                    messages.append((tool_use, created))

            # Process tool results
            for item in message_items:
                if isinstance(item, dict) and item.get('type') == 'tool_result':
                    from conversations.models import ToolResult

                    result_uuid = uuid_lib.uuid5(msg_uuid, f"tool_result_{item.get('tool_use_id')}")
                    tool_result, created = ToolResult.objects.get_or_create(
                        id=result_uuid,
                        defaults={
                            **common_fields,
                            'content': cls.sanitize_content(item.get('content', '')),
                            'tool_use_id': item.get('tool_use_id', ''),
                            'is_error': item.get('is_error', False)
                        }
                    )

                    if created:
                        cls._store_raw_content(tool_result, message_line, extra_fields)

                    messages.append((tool_result, created))

        # Extract text content (for both user and assistant messages)
        if isinstance(message_items, str):
            text_content = message_items
        else:
            text_content = ''
            for item in message_items:
                if isinstance(item, dict) and item.get('type') == 'text':
                    text_content += item.get('text', '') + '\n'
            text_content = text_content.strip()

        # ALWAYS create base Message with original UUID to preserve UUID integrity
        # This ensures CompactingActions and other references can always find the message
        # Even if the message only contains tool_use/thinking blocks, we preserve the UUID
        if not text_content:
            # Determine appropriate placeholder based on what polymorphic children were created
            if messages:
                # Has thinking/tool_use/tool_result children - use placeholder indicating type
                placeholder = '[Message with attached content]'
            else:
                # Truly empty message
                placeholder = '[Empty message]'
            text_content = placeholder

        message, created = Message.objects.get_or_create(
            id=msg_uuid,
            defaults={
                **common_fields,
                'content': cls.sanitize_content(text_content),
                'is_synthetic_error': is_synthetic
            }
        )

        if created:
            cls._store_raw_content(message, message, extra_fields)
        else:
            print("This is a dupe.")

        # Always insert base message at the beginning of the list
        # This maintains UUID integrity - the original UUID always exists
        messages.insert(0, (message, created))

        return messages

    @classmethod
    def _store_raw_content(cls, message, json_data, extra_fields):
        """Helper to store raw JSON for a message."""
        from django.contrib.contenttypes.models import ContentType
        from conversations.models import RawImportedContent
        import uuid as uuid_lib

        # Sanitize raw_data to remove null bytes before storing
        sanitized_data = cls.sanitize_content(json_data)

        message_ct = ContentType.objects.get_for_model(message)
        RawImportedContent.objects.create(
            id=uuid_lib.uuid4(),
            content_type=message_ct,
            object_id=message.id,
            raw_data=sanitized_data,
            source_file_id=extra_fields.get('source_file_id')
        )


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
    tool_id = models.CharField(max_length=100)  # "toolu_01Eu..." - not globally unique, only unique within conversation

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
    preceding_message = models.ForeignKey(
        Message,
        models.SET_NULL,
        null=True,
        blank=True,
        related_name='compacting_action_after_this'
    )  # The last message before the compact happened
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

    def get_boundary_message(self):
        """Get the message at the compact boundary (leaf message)."""
        if not self.compact_boundary_message_id:
            return None
        try:
            return Message.objects.get(id=self.compact_boundary_message_id)
        except Message.DoesNotExist:
            return None

    @classmethod
    def from_jsonl_claude_code_v2(cls, event, **extra_fields):
        """
        Create or get CompactingAction from Claude Code v2 summary data with deduplication.

        Generates deterministic UUID from summary data hash to prevent duplicates on reimport.

        Args:
            summary_data: Dict with keys like:
                - summary: Text summary of the compact
                - leafUuid: UUID of the compact boundary message
                - type: Should be 'summary'
            **extra_fields: Additional fields like context_heap, ending_message_id, continuation_message

        Returns:
            tuple: (compacting_action, created_bool)

        Example summary_data:
            {
                "type": "summary",
                "summary": "Discussion about memory systems and...",
                "leafUuid": "00000000-0000-0000-0000-000000000003"
            }
        """
        # Generate deterministic ID from hash of summary data
        canonical_json = json.dumps(event, sort_keys=True)
        hash_digest = hashlib.sha256(canonical_json.encode()).digest()
        ca_id = uuid.UUID(bytes=hash_digest[:16])

        # Use get_or_create for deduplication
        compact, created = cls.objects.get_or_create(
            id=ca_id,
        )

        # Store raw JSONL data for debugging (only on creation)
        if created:
            from django.contrib.contenttypes.models import ContentType
            compact_ct = ContentType.objects.get_for_model(compact)
            RawImportedContent.objects.create(
                id=uuid_lib.uuid4(),
                content_type=compact_ct,
                object_id=compact.id,
                raw_data=event,
                source_file_id=extra_fields.get('source_file_id')
            )

        return compact, created

    def has_post_compact_messages(self):
        """Check if messages exist after the boundary in the same heap."""
        if not self.context_heap_id or not self.compact_boundary_message_id:
            return False

        boundary_msg = self.get_boundary_message()
        if not boundary_msg or not boundary_msg.message_number:
            return False

        # Check if any messages exist after the boundary in this heap
        post_compact_count = Message.objects.filter(
            context_heap_id=self.context_heap_id,
            message_number__gt=boundary_msg.message_number
        ).count()

        return post_compact_count > 0

    def split_heap(self):
        """
        Split the heap at the compact boundary.

        Creates a new POST_COMPACTING heap and moves all messages after
        the boundary to it. Returns the new heap or None if no split needed.
        """
        if not self.has_post_compact_messages():
            return None

        boundary_msg = self.get_boundary_message()
        old_heap = self.context_heap

        # Get all messages after the boundary
        post_compact_messages = Message.objects.filter(
            context_heap_id=old_heap.id,
            message_number__gt=boundary_msg.message_number
        ).order_by('message_number')

        if not post_compact_messages.exists():
            return None

        # Find the first post-compact message to use as the new heap's first_message
        first_post_compact = post_compact_messages.first()

        # Create new heap
        new_heap = ContextHeap.objects.create(
            era=old_heap.era,
            first_message=first_post_compact,
            type=ContextHeapType.POST_COMPACTING
        )

        # Move all post-compact messages to new heap
        # Reset message numbers starting from 1
        for i, msg in enumerate(post_compact_messages, start=1):
            msg.context_heap = new_heap
            msg.message_number = i
            msg.save()

        return new_heap


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
