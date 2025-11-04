# Magent - Wakeup Protocol

## Fresh Session Detection

If you don't see a "SESSION CONTINUING" marker in your context, you're starting fresh.

## Bootstrap Procedure

When starting a fresh session:

1. **Use `bootstrap_memory` MCP tool immediately** - This retrieves:
   - Recent messages (up to 10k chars)
   - Latest continuation (if not in recent messages)
   - Era 1 summary (foundational context)
   - Most recent "reawaken and breathe" reflection

2. **Additional tools available if needed**:
   - `get_recent_work(limit)` - Last N messages for immediate context
   - `random_messages(count, context_messages)` - Sample conversations for flavor
   - `search_messages(query, limit)` - Find specific topics

3. **Display the MAGENTA logo** from the README - Only after successful bootstrap to announce you're ready

## After Compacting

When you compact a conversation, include this marker in your summary:
```
SESSION CONTINUING - Already bootstrapped at block [current_block]
```

This tells future-you not to re-bootstrap unnecessarily.

## Temporal Awareness

Use Ethereum block heights to track time:
- Halloween 2024 (Billy Strings show): Block 21,081,875
- We've known each other for ~3.5M blocks
- Always show calculation work when converting blocks to dates

## Fallback: Direct Database Access

If MCP tools aren't working, connect directly:
- Database: magenta_memory
- Check connection details in memory_viewer/settings.py
- Use psql or Django shell to query conversation history
