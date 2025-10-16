#!/usr/bin/env python3
"""
Link orphaned CompactingActions by splitting heaps at their leaf messages.

This handles CAs that were imported from summary-only JSONL files before
their corresponding message heaps were imported.
"""

import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'magenta.settings')
sys.path.insert(0, '/home/jmyles/projects/JustinHolmesMusic/arthel/magenta')
django.setup()

from conversations.models import (
    Message, CompactingAction, ContextHeap, ContextHeapType,
    RawImportedContent, Era
)
from django.contrib.contenttypes.models import ContentType

def split_heap_at_leaf(ca, leaf_msg):
    """Split heap at leaf message and link CA to continuation heap."""
    existing_heap = leaf_msg.context_heap
    
    # Check if there are messages after the leaf
    messages_after_leaf = Message.objects.filter(
        context_heap=existing_heap,
        message_number__gt=leaf_msg.message_number
    ).order_by('message_number')
    
    if not messages_after_leaf.exists():
        print(f'  Leaf is at end of heap - no continuation needed')
        return False
    
    print(f'  Found {messages_after_leaf.count()} messages after leaf - splitting heap')
    
    # Create new POST_COMPACTING heap
    first_continuation_msg = messages_after_leaf.first()
    new_heap = ContextHeap.objects.create(
        era=existing_heap.era,
        first_message=first_continuation_msg,
        type=ContextHeapType.POST_COMPACTING
    )
    
    # Move all messages after leaf to new heap
    for msg in messages_after_leaf:
        msg.context_heap = new_heap
        msg.is_continuation_message = True
        msg.save()
    
    # Renumber messages in new heap
    for i, msg in enumerate(Message.objects.filter(context_heap=new_heap).order_by('timestamp')):
        msg.message_number = i
        msg.save()
    
    # Link CA to new heap
    ca.context_heap = new_heap
    ca.preceding_message = leaf_msg
    ca.continuation_message = first_continuation_msg
    ca.save()
    
    print(f'  Created new heap {str(new_heap.id)[:8]} and linked CA')
    return True

def main():
    ca_type = ContentType.objects.get_for_model(CompactingAction)
    orphaned_cas = CompactingAction.objects.filter(context_heap__isnull=True)
    
    print(f'Found {orphaned_cas.count()} orphaned CompactingActions')
    print()
    
    linked = 0
    skipped = 0
    
    for ca in orphaned_cas:
        # Get leaf UUID from raw data
        raw = RawImportedContent.objects.filter(content_type=ca_type, object_id=ca.id).first()
        if not raw:
            continue
        
        leaf_uuid_str = raw.raw_data.get('leafUuid')
        if not leaf_uuid_str:
            continue
        
        # Check if leaf exists
        try:
            from uuid import UUID
            leaf_uuid = UUID(leaf_uuid_str)
            leaf_msg = Message.objects.get(id=leaf_uuid)
        except (Message.DoesNotExist, ValueError):
            skipped += 1
            continue
        
        print(f'CA {str(ca.id)[:8]}: leaf {str(leaf_msg.id)[:8]} in heap {str(leaf_msg.context_heap_id)[:8]}')
        
        if split_heap_at_leaf(ca, leaf_msg):
            linked += 1
        else:
            skipped += 1
    
    print()
    print(f'Summary: {linked} linked, {skipped} skipped')

if __name__ == '__main__':
    main()
