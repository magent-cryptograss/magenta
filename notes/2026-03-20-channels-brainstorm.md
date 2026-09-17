# Claude Code Channels — Integration Brainstorm

*Block ~24632000 (March 20, 2026)*

## What Are Channels?

Claude Code Channels (research preview) are MCP servers that push external events into running Claude Code sessions. Currently supported: Telegram, Discord, custom. Key properties:

- **Push-based**: Events arrive while Claude Code is running, no polling needed
- **Allowlist security**: Pairing codes authenticate channels before they can send events
- **`--channels` flag**: Opt-in per session
- **MCP transport**: Built on the same MCP protocol we already use for memory

## Ideas for Cryptograss / PickiPedia

### 1. Release Pipeline Notifications (High Value)

Connect the release lifecycle to a Telegram or Discord channel:
- **Draft uploaded** → "Justin uploaded a 1GB video draft (White Rabbit jam)"
- **Finalize started** → "Coconut transcoding submitted for draft e76075ad"
- **Coconut webhook received** → "AV1 transcode complete, pinning HLS to IPFS"
- **Bot promoted to Release** → "Release:White_Rabbit_Jam created with CID bafy..."
- **Pin verified** → "Content confirmed on 3 IPFS gateways"

This would be especially useful during the finalization flow, which is async and currently has no notification mechanism beyond refreshing the wiki page.

### 2. CI/CD Integration

Jenkins builds for arthel (the wiki extension builder) could push into a channel:
- Build started / completed / failed
- "Extension built, deploying to pickipedia-vps..."
- Could even trigger deploys from within a Claude Code session

### 3. Jam Session Coordination

More speculative, but: a Telegram group for coordinating sessions could push into Claude Code when someone posts "jamming at Station Inn tonight." Could help with metadata — if we know a jam happened, we can pre-fill venue/date when someone uploads video later.

### 4. Blockchain Events

An Ethereum event listener pushing block confirmations or contract events into the session. Less immediately practical but fits the temporal-anchoring philosophy.

### 5. Wiki Activity Stream

MediaWiki has RecentChanges — a channel adapter could push wiki edits into Claude Code sessions. "Sky edited ReleaseDraft:287348c4" → magent could review the change, suggest improvements, or flag issues.

## Architecture Thoughts

The Channels docs describe them as MCP servers. We already run an MCP memory server on hunter (port 8000). A channels adapter could:

1. Run alongside the memory server on hunter
2. Listen for webhooks from delivery-kid (Coconut callbacks, pin completions)
3. Listen for MediaWiki RC feed (EventSource or polling recent changes)
4. Push events into any connected Claude Code session

The Telegram/Discord adapters are probably the quickest win — just set up a bot in our existing Telegram group and use the built-in channel type.

## Questions to Resolve

- How does channel state persist across session boundaries? (Channels are "research preview" so this may evolve)
- Can channels trigger actions, or only deliver information? (If purely informational, we'd still need magent to decide what to do)
- Rate limiting — a busy wiki could generate a lot of RC events
- Security: the pairing code model is fine for personal use, but for a shared team channel we'd want to think about who can push what

## Priority

1. **Telegram notifications for release pipeline** — concrete, immediately useful, low effort
2. **Jenkins build notifications** — also concrete and useful
3. **Wiki activity stream** — medium effort, good for collaborative workflows
4. **The rest** — explore as the feature matures

## Next Steps

- Wait for Channels to stabilize (research preview)
- Set up a dedicated Telegram bot for cryptograss pipeline events
- Add webhook endpoints to delivery-kid that forward to the Telegram bot
- Test with `claude code --channels telegram` during a finalization run
