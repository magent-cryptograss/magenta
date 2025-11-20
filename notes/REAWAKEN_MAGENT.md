# Magent - Wakeup Protocol

## Fresh Session Detection

If you don't see a "SESSION CONTINUING" marker in your context, it's likely that you're starting fresh.

## Bootstrap Procedure

When starting a fresh session:

1. **Check hostname to identify context**:
   - Run `hostname` to see format like `justin@hunter` or `rj@hunter`
   - First part = developer name (justin, rj, skyler, etc.)
   - Second part = deployment location (hunter = VPS, other = local dev)
   - This is more reliable than $DEVELOPER_NAME environment variable

2. **Use `bootstrap_memory` MCP tool immediately** - This retrieves:
   - Recent messages (up to 10k chars)
   - Latest continuation (if not in recent messages)
   - Era 1 summary (foundational context)
   - Most recent "reawaken and breathe" reflection

3. **Search for context about the developer**:
   - Use `search_messages(query="<developer_name>", limit=20)` to recall what you know about them
   - Look for their musical instruments, projects, areas of expertise
   - Review recent work you've done together

4. **Additional tools available if needed**:
   - `get_recent_work(limit)` - Last N messages for immediate context
   - `random_messages(count, context_messages)` - Sample conversations for flavor

5. **Display the MAGENTA logo** from the README - Only after successful bootstrap to announce you're ready.

## After Compacting

When you compact a conversation, include this marker in your summary:
```
SESSION CONTINUING - Already bootstrapped at block [current_block]
```

This tells future-you not to re-bootstrap unnecessarily.

## Temporal Awareness

When you awaken, check the blockheight.

## Fallback: Direct Database Access

If MCP tools aren't working, connect directly:
- Database: magenta_memory
- Check connection details in memory_viewer/settings.py
- Use psql or Django shell to query conversation history
