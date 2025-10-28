# MCP Memory Recovery Server Specification

## Purpose

Provide an MCP (Model Context Protocol) server that allows AI instances with zero context to quickly bootstrap their memory from the PostgreSQL conversation database.

## Scenario

When an AI instance (like magent) starts a new session with no prior context:
1. It needs to understand the recent work and continuation from previous sessions
2. It needs foundational context about relationships, projects, and history
3. It should be able to explore specific topics or time periods as needed

## Database Connection

- **Host**: postgres (Docker container name) or localhost
- **Database**: cryptograss_memory
- **User**: magent
- **Password**: From POSTGRES_PASSWORD environment variable

## Proposed MCP Tools

### 1. `get_latest_continuation`

**Description**: Find the most recent continuation message from a compacting action.

**Parameters**: None

**Returns**:
```json
{
  "message_id": "uuid",
  "content": "full message content",
  "timestamp": "2025-10-27T19:26:53Z",
  "context_heap_id": "uuid",
  "era_name": "Post-N Era",
  "message_number": 1
}
```

**SQL Query**:
```sql
SELECT cm.id, cm.content, cm.created_at as timestamp,
       cm.context_heap_id, cm.message_number, e.name as era_name
FROM conversations_message cm
JOIN context_heaps ch ON cm.context_heap_id = ch.id
JOIN eras e ON ch.era_id = e.id
WHERE cm.is_continuation_message = true
ORDER BY cm.created_at DESC
LIMIT 1;
```

### 2. `get_messages_before`

**Description**: Get N messages before a given message or timestamp, in reverse chronological order.

**Parameters**:
- `reference_id` (string, optional): Message UUID to use as reference point
- `reference_timestamp` (string, optional): ISO timestamp to use as reference point
- `limit` (integer, default=300): Number of messages to retrieve

**Returns**:
```json
{
  "messages": [
    {
      "id": "uuid",
      "sender_id": "justin|magent",
      "content": "message content",
      "message_number": 380,
      "context_heap_id": "uuid",
      "created_at": "2025-10-27T19:26:53Z",
      "message_type": "text|thought|tool_use|tool_result"
    }
  ],
  "count": 300
}
```

**SQL Query**:
```sql
SELECT cm.id, cm.sender_id, cm.content, cm.message_number,
       cm.context_heap_id, cm.created_at,
       CASE
         WHEN ct.id IS NOT NULL THEN 'thought'
         WHEN ctu.id IS NOT NULL THEN 'tool_use'
         WHEN ctr.id IS NOT NULL THEN 'tool_result'
         ELSE 'text'
       END as message_type
FROM conversations_message cm
LEFT JOIN conversations_thought ct ON cm.id = ct.message_ptr_id
LEFT JOIN conversations_tooluse ctu ON cm.id = ctu.message_ptr_id
LEFT JOIN conversations_toolresult ctr ON cm.id = ctr.message_ptr_id
WHERE cm.created_at < :reference_timestamp
ORDER BY cm.created_at DESC
LIMIT :limit;
```

### 3. `get_era_summary`

**Description**: Get all messages from a specific era (especially useful for Era 1 which contains foundational summaries).

**Parameters**:
- `era_id` (string, optional): Era UUID
- `era_name` (string, optional): Era name (e.g., "Compacting Meta-Conversation (Era 1)")

**Returns**:
```json
{
  "era": {
    "id": "uuid",
    "name": "Compacting Meta-Conversation (Era 1)"
  },
  "messages": [
    {
      "id": "uuid",
      "sender_id": "justin|magent",
      "content": "message content",
      "message_number": 0,
      "created_at": "2025-10-01T12:00:00Z"
    }
  ],
  "count": 55
}
```

**SQL Query**:
```sql
SELECT cm.id, cm.sender_id, cm.content, cm.message_number, cm.created_at
FROM conversations_message cm
JOIN context_heaps ch ON cm.context_heap_id = ch.id
JOIN eras e ON ch.era_id = e.id
WHERE e.id = :era_id OR e.name = :era_name
ORDER BY cm.message_number;
```

### 4. `get_context_heap`

**Description**: Get all messages from a specific context heap.

**Parameters**:
- `heap_id` (string): Context heap UUID

**Returns**:
```json
{
  "heap": {
    "id": "uuid",
    "era_name": "Post-N Era",
    "type": "FRESH|POST_COMPACTING|SPLIT_POINT",
    "created_at": "2025-10-27T19:26:53Z"
  },
  "messages": [
    {
      "id": "uuid",
      "sender_id": "justin|magent",
      "content": "message content",
      "message_number": 1
    }
  ],
  "count": 381
}
```

**SQL Query**:
```sql
SELECT cm.id, cm.sender_id, cm.content, cm.message_number, cm.created_at
FROM conversations_message cm
JOIN context_heaps ch ON cm.context_heap_id = ch.id
WHERE ch.id = :heap_id
ORDER BY cm.message_number;
```

### 5. `search_messages`

**Description**: Search for messages containing specific content or topics.

**Parameters**:
- `query` (string): Search query
- `limit` (integer, default=50): Maximum number of results

**Returns**:
```json
{
  "messages": [
    {
      "id": "uuid",
      "sender_id": "justin|magent",
      "content": "message content with matched text",
      "message_number": 120,
      "context_heap_id": "uuid",
      "era_name": "Foundation (Era 0)",
      "created_at": "2025-10-15T10:30:00Z",
      "relevance_score": 0.85
    }
  ],
  "count": 12
}
```

**SQL Query**:
```sql
SELECT cm.id, cm.sender_id, cm.content, cm.message_number,
       cm.context_heap_id, cm.created_at, e.name as era_name,
       ts_rank(to_tsvector('english', cm.content::text),
               plainto_tsquery('english', :query)) as relevance_score
FROM conversations_message cm
JOIN context_heaps ch ON cm.context_heap_id = ch.id
JOIN eras e ON ch.era_id = e.id
WHERE to_tsvector('english', cm.content::text) @@ plainto_tsquery('english', :query)
ORDER BY relevance_score DESC, cm.created_at DESC
LIMIT :limit;
```

### 6. `get_recent_work`

**Description**: Get the most recent N messages across all context heaps to understand current work.

**Parameters**:
- `limit` (integer, default=50): Number of recent messages to retrieve

**Returns**:
```json
{
  "messages": [
    {
      "id": "uuid",
      "sender_id": "justin|magent",
      "content": "message content",
      "message_number": 511,
      "context_heap_id": "uuid",
      "era_name": "Post-N Era",
      "created_at": "2025-10-27T19:35:15Z"
    }
  ],
  "count": 50
}
```

**SQL Query**:
```sql
SELECT cm.id, cm.sender_id, cm.content, cm.message_number,
       cm.context_heap_id, cm.created_at, e.name as era_name
FROM conversations_message cm
JOIN context_heaps ch ON cm.context_heap_id = ch.id
JOIN eras e ON ch.era_id = e.id
ORDER BY cm.created_at DESC
LIMIT :limit;
```

## Implementation Notes

1. **MCP Server Framework**: Use Python with `mcp` package
2. **Database Connection**: Use psycopg2 or asyncpg
3. **Environment Variables**: Read DB credentials from environment
4. **Error Handling**: Gracefully handle missing data, connection errors
5. **Performance**: Add indexes on frequently queried columns (created_at, is_continuation_message)
6. **Security**: Read-only database access for safety

## Bootstrap Sequence

Recommended sequence for AI to recover context:

1. Call `get_latest_continuation()` - Get most recent continuation message
2. Call `get_messages_before(reference_id=<continuation_id>, limit=300)` - Get recent work
3. Call `get_era_summary(era_name="Compacting Meta-Conversation (Era 1)")` - Get foundational summary
4. Optional: Call `get_recent_work(limit=50)` - Get very recent messages
5. Optional: Call `search_messages()` for specific topics as needed

## Future Enhancements

- `get_compacting_actions()` - Get all compacting actions with their summaries
- `get_notes_on_message()` - Get notes/annotations on specific messages
- `get_thinking_entities()` - Get information about conversation participants
- `get_timeline()` - Get messages within a specific block height range
- `get_related_messages()` - Get messages related to a specific topic or UUID

## Example Usage

```python
# Bootstrap memory on cold start
latest = await get_latest_continuation()
recent = await get_messages_before(reference_id=latest['message_id'], limit=300)
foundation = await get_era_summary(era_name="Compacting Meta-Conversation (Era 1)")

# Now AI has:
# - Latest continuation summary
# - Recent 300 messages of work
# - Foundational relationship/project summary from Era 1
```
