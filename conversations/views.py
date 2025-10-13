from django.shortcuts import render
from django.http import JsonResponse
from .models import (
    Message,
    Thought,
    ToolUse,
    ToolResult
)


def memory_lane(request):
    """Main memory viewer/editor page."""
    return render(request, 'conversations/memory_lane.html')


def all_messages(request):
    """Messages grouped by Era and ContextWindow."""
    # Get all context windows with their eras
    from .models import ContextWindow, Era, Note, CompactingAction
    from django.contrib.contenttypes.models import ContentType

    eras = Era.objects.prefetch_related(
        'context_windows__messages__sender',
        'context_windows__messages__recipients'
    ).order_by('created_at')

    data = {
        'eras': [],
        'orphaned_compacting_actions': []
    }

    # Get content types for lookups
    message_ct = ContentType.objects.get(app_label='conversations', model='message')
    window_ct = ContentType.objects.get(app_label='conversations', model='contextwindow')
    era_ct = ContentType.objects.get(app_label='conversations', model='era')

    for era in eras:
        # Get notes for this era
        era_notes = Note.objects.filter(
            content_type=era_ct,
            object_id=era.id
        ).order_by('created_at')

        era_data = {
            'id': str(era.id),
            'name': era.name,
            'created_at': era.created_at.isoformat(),
            'earliest_blockheight': era.earliest_blockheight(),
            'latest_blockheight': era.latest_blockheight(),
            'context_windows': [],
            'notes': [{
                'id': str(note.id),
                'from_entity': note.from_entity.name,
                'content': note.content,
                'eth_blockheight': note.eth_blockheight,
                'created_at': note.created_at.isoformat()
            } for note in era_notes]
        }

        # Get all windows for this era
        all_windows = list(era.context_windows.all().order_by('created_at'))

        # Build hierarchy: find root windows (non-split) and their children (splits)
        def serialize_window(window):
            # Get notes for this window
            window_notes = Note.objects.filter(
                content_type=window_ct,
                object_id=window.id
            ).order_by('created_at')

            # Check for compacting action
            compacting_action = None
            if hasattr(window, 'compacting_action') and window.compacting_action:
                ca = window.compacting_action
                compacting_action = {
                    'id': str(ca.id),
                    'summary': ca.summary,
                    'compact_boundary_message_id': str(ca.compact_boundary_message_id) if ca.compact_boundary_message_id else None,
                    'compact_trigger': ca.compact_trigger
                }

            window_data = {
                'id': str(window.id),
                'type': window.type,
                'type_display': window.get_type_display(),
                'first_message_id': str(window.first_message_id),
                'created_at': window.created_at.isoformat(),
                'earliest_blockheight': window.earliest_blockheight(),
                'latest_blockheight': window.latest_blockheight(),
                'messages': [],
                'child_windows': [],
                'compacting_action': compacting_action,
                'notes': [{
                    'id': str(note.id),
                    'from_entity': note.from_entity.name,
                    'content': note.content,
                    'eth_blockheight': note.eth_blockheight,
                    'created_at': note.created_at.isoformat()
                } for note in window_notes]
            }

            # Build lookup of CompactingActions by their leaf message UUID
            # This includes both linked CAs (for this window or others) and orphaned ones
            all_compacting_actions = CompactingAction.objects.all()
            compacting_action_by_leaf_uuid = {
                action.compact_boundary_message_id: action
                for action in all_compacting_actions
                if action.compact_boundary_message_id
            }

            # Get messages for this window
            messages = window.messages.select_related('thought', 'tooluse', 'toolresult').order_by('message_number')
            for msg in messages:
                # Get the actual polymorphic instance
                if hasattr(msg, 'thought'):
                    actual_msg = msg.thought
                elif hasattr(msg, 'tooluse'):
                    actual_msg = msg.tooluse
                elif hasattr(msg, 'toolresult'):
                    actual_msg = msg.toolresult
                else:
                    actual_msg = msg

                # Get notes for this message
                msg_notes = Note.objects.filter(
                    content_type=message_ct,
                    object_id=msg.id
                ).order_by('created_at')

                msg_dict = {
                    'id': str(actual_msg.id),
                    'message_number': actual_msg.message_number,
                    'message_type': actual_msg.__class__.__name__,
                    'sender': msg.sender.name,
                    'recipients': [r.name for r in msg.recipients.all()],
                    'content': msg.content,  # JSONField - keep as dict/str, JsonResponse will serialize properly
                    'timestamp': msg.timestamp,
                    'eth_blockheight': msg.eth_blockheight,
                    'eth_block_offset': msg.eth_block_offset,
                    'created_at': msg.created_at.isoformat(),
                    'session_id': str(msg.session_id) if msg.session_id else None,
                    'source_file': msg.source_file,
                    'missing_from_markdown': msg.missing_from_markdown,
                    'cwd': msg.cwd,
                    'git_branch': msg.git_branch,
                    'client_version': msg.client_version,
                    'parent_id': str(msg.parent_id) if msg.parent_id else None,
                    'is_synthetic_error': msg.is_synthetic_error,
                    'is_retry': msg.is_retry,
                    'notes': [{
                        'id': str(note.id),
                        'from_entity': note.from_entity.name,
                        'content': note.content,
                        'eth_blockheight': note.eth_blockheight,
                        'created_at': note.created_at.isoformat()
                    } for note in msg_notes]
                }

                # Add type-specific fields
                if hasattr(msg, 'tooluse'):
                    msg_dict['tool_name'] = msg.tooluse.tool_name
                    msg_dict['tool_id'] = msg.tooluse.tool_id
                elif hasattr(msg, 'toolresult'):
                    msg_dict['tool_use_id'] = msg.toolresult.tool_use_id
                    msg_dict['is_error'] = msg.toolresult.is_error
                    # Look up parent ToolUse to get tool name
                    if msg.parent and hasattr(msg.parent, 'tooluse'):
                        msg_dict['tool_name'] = msg.parent.tooluse.tool_name
                elif hasattr(msg, 'thought'):
                    msg_dict['signature'] = msg.thought.signature

                window_data['messages'].append(msg_dict)

                # Check if this message is the leaf of a CompactingAction
                if msg.id in compacting_action_by_leaf_uuid:
                    compacting_action = compacting_action_by_leaf_uuid[msg.id]
                    # Add a pseudo-message representing the compacting action
                    window_data['messages'].append({
                        'id': str(compacting_action.id),
                        'message_type': 'CompactingAction',
                        'summary': compacting_action.summary,
                        'compact_trigger': compacting_action.compact_trigger,
                        'pre_compact_tokens': compacting_action.pre_compact_tokens,
                        'compact_boundary_message_id': str(compacting_action.compact_boundary_message_id),
                        'is_orphaned': compacting_action.context_window_id is None,
                        'linked_window_id': str(compacting_action.context_window_id) if compacting_action.context_window_id else None
                    })

            # Find child split windows
            for potential_child in all_windows:
                if potential_child.type == 'split_point':
                    parent_window = potential_child.parent_window()
                    if parent_window and parent_window.id == window.id:
                        window_data['child_windows'].append(serialize_window(potential_child))

            return window_data

        # Serialize root windows (non-split windows)
        for window in all_windows:
            if window.type != 'split_point':
                era_data['context_windows'].append(serialize_window(window))

        data['eras'].append(era_data)

    # Get orphaned compacting actions (not linked to any context window)
    orphaned = CompactingAction.objects.filter(context_window__isnull=True).order_by('created_at')
    for compact in orphaned:
        data['orphaned_compacting_actions'].append({
            'id': str(compact.id),
            'summary': compact.summary,
            'compact_boundary_message_id': str(compact.compact_boundary_message_id) if compact.compact_boundary_message_id else None,
            'compact_trigger': compact.compact_trigger,
            'created_at': compact.created_at.isoformat()
        })

    return JsonResponse(data, safe=False)


def api_messages(request):
    """API endpoint for fetching messages with filtering."""
    # Get filter parameters
    search = request.GET.get('search', '').lower()
    person = request.GET.get('person', '')
    show_thinking = request.GET.get('show_thinking', 'true') == 'true'
    message_types = request.GET.get('types', 'context_opening,regular,thought,tool_use,tool_result').split(',')
    limit = int(request.GET.get('limit', 100))

    # Start with all messages from base table
    messages = Message.objects.all()

    # Apply filters
    if person:
        # Filter by sender or recipients (M2M)
        messages = messages.filter(sender__name=person) | messages.filter(recipients__name=person)

    # Filter by message type
    if not show_thinking:
        # Exclude Thought messages
        messages = messages.exclude(thought__isnull=False)

    # Order by timestamp (or created_at if timestamp is null)
    messages = messages.order_by('-timestamp', '-created_at')[:limit]

    # Serialize messages with polymorphic content
    data = []
    for msg in messages.prefetch_related('recipients'):
        # Determine message type and get content
        message_type = None
        content = None
        extra = {}

        # Check which subclass this is
        if hasattr(msg, 'thought'):
            message_type = 'thought'
            content = str(msg.thought.content)
            extra['signature'] = msg.thought.signature
            extra['parent_uuid'] = str(msg.parent.id) if msg.parent else None
            extra['context_window'] = str(msg.context_window.id) if msg.context_window else None
        elif hasattr(msg, 'tooluse'):
            message_type = 'tool_use'
            content = f"[Tool: {msg.tooluse.tool_name}]"
            extra['tool_name'] = msg.tooluse.tool_name
            extra['tool_id'] = msg.tooluse.tool_id
            extra['parent_uuid'] = str(msg.parent.id) if msg.parent else None
            extra['context_window'] = str(msg.context_window.id) if msg.context_window else None
        elif hasattr(msg, 'toolresult'):
            message_type = 'tool_result'
            result_content = str(msg.toolresult.content)
            content = result_content[:100] + '...' if len(result_content) > 100 else result_content
            extra['is_error'] = msg.toolresult.is_error
            extra['tool_use_id'] = msg.toolresult.tool_use_id
            extra['parent_uuid'] = str(msg.parent.id) if msg.parent else None
            extra['context_window'] = str(msg.context_window.id) if msg.context_window else None
        else:
            message_type = 'message'
            content = str(msg.content)
            extra['parent_uuid'] = str(msg.parent.id) if msg.parent else None
            extra['context_window'] = str(msg.context_window.id) if msg.context_window else None

        # Filter by message type
        if message_type and message_type not in message_types:
            continue

        # Filter by search text
        if search and content and search not in content.lower():
            continue

        # Get recipients
        recipient_names = [r.name for r in msg.recipients.all()]

        data.append({
            'id': str(msg.id),
            'message_type': message_type,
            'sender': msg.sender.name,
            'recipients': recipient_names,
            'content': content,
            'timestamp': msg.timestamp,
            'session_id': str(msg.session_id) if msg.session_id else None,
            **extra
        })

    return JsonResponse(data, safe=False)
