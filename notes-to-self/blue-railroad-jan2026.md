# Blue Railroad Train - Development Notes (January 2026)

## Current Status

The Blue Railroad submission system is partially working on PickiPedia production:
- Template exists: `Template:Blue Railroad Submission`
- Form exists: `Form:Blue Railroad Submission`
- PageForms extension is now installed and working
- Anonymous editing enabled
- `Special:VerifyBotEdits` deployed for bulk verification of bot edits

## Form URL
https://pickipedia.xyz/wiki/Special:FormEdit/Blue_Railroad_Submission

## Outstanding Work

### 1. Multiple Participants per Video
The form currently has single squatter + wallet. Need to support multiple participants since one video can show multiple people doing the exercise together.

**Change from:**
- squatter (single)
- wallet_address (single)

**Change to:**
- participants (repeatable field):
  - name
  - wallet_address

PageForms supports this with `multiple` attribute or `holds template`.

### 2. Block Height Auto-fill
Currently shows placeholder with external link to etherscan. Should:
- Auto-fill with the wiki's build-time block from `$wgPickipediaBuildInfo['blockheight']`
- This is available in PHP, need to inject into form somehow

### 3. Datetime to Block Converter
Add optional datetime picker that converts to approximate Ethereum block:
- Ethereum mainnet: ~12 seconds per block
- Formula: `target_block = current_block - ((now - target_time) / 12)`
- Could be JavaScript in the form or a wiki gadget

### 4. Instagram Video Import
**yt-dlp works!** Tested successfully on hunter:
```bash
~/yt-dlp-venv/bin/yt-dlp "https://www.instagram.com/p/DTKHo-JDGlc/"
```

Downloaded 48MB video from Justin's Instagram without needing login.

**Integration plan:**
- Add tool to pickipedia-mcp that:
  1. Takes Instagram URL
  2. Downloads via yt-dlp (installed at `~/yt-dlp-venv/bin/yt-dlp`)
  3. Uploads to wiki via MediaWiki API
  4. Returns `File:BlueRailroad-{shortcode}.mp4` for form use

Alternative: Add "Instagram URL" field to form, process server-side.

### 5. Recorder Field
Keep but make clearly optional, no wallet address needed.

## Exercise Types (from Manzanita album)
- **Blue Railroad Train** - Squats
- **Nine Pound Hammer** - Pushups
- **Ginseng Sullivan** - Army Crawls

## Badge Tiers (Zero-utility NFTs)
- Depot Pass
- Conductor's Ticket
- Engineer's Emblem
- Brakeman's Badge

## Related Files
- `/home/magent/workspace/pickipedia/extensions/PickiPediaVerification/` - verification extension with Special:VerifyBotEdits
- Template and Form are on the wiki itself, not in repo

## yt-dlp Location
Installed in venv on hunter:
```
~/yt-dlp-venv/bin/yt-dlp
```
Version: 2025.12.08
