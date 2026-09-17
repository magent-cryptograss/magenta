# PickiPedia Blue Railroad Session - 2026-02-11

## What We Built Tonight

### Blue Railroad Token Gallery
- Created `Template:Blue Railroad Token Gallery` and `Template:Blue Railroad Gallery Item`
- Uses SMW `format=template` with `named args=yes` for proper rendering
- Shows: thumbnail, #n, song + exercise, owner (linked to user page if exists), blockheight
- Owner lookup: queries pages by `[[Ethereum Address::...]]`, links to user page with Display Name

### Token Template Improvements
- Added `|thumbnail=` parameter (CID-based filename)
- Added `|maybelle_pinned=yes/no` with display "✓ Pinned on [[Cryptograss:Maybelle|maybelle]]" or "⏳ Pending"
- Added `|contract_version=` display
- Burned token detection via `#switch` on owner address (zero/dead addresses)
- Categories: `[[Category:Blue Railroad Tokens]]` vs `[[Category:Burned Blue Railroad Tokens]]`

### Import Bot (blue-railroad-import) - PR #7
1. **CID normalization** - `py-cid` library converts Qm... (CIDv0) ↔ bafy... (CIDv1) so same content = same thumbnail filename
2. **Fallback gateway** - tries maybelle, falls back to ipfs.io for thumbnail downloads
3. **Preserve user content** - only updates template block, leaves user-added content intact
4. **Only update on changes** - checks owner + maybelle_pinned status, skips if unchanged
5. **Maybelle status check** - HEAD request to verify video is on maybelle gateway

### Pinning Service (maybelle-config) - needs push
- **Transcoding added**: All non-MP4 files transcoded to H.264
- Downscales to max 720p, never upscales
- MJPEG/MKV → H.264/MP4 gives massive compression (1.3GB → ~30MB)
- Skips small (<50MB) MP4s already optimized
- Uses CRF 23, preset medium, faststart for streaming

### Key Learnings
- CIDv0 (`Qm...`) and CIDv1 (`bafy...`) can represent same content - normalize before comparing!
- `py-cid` library: use `.encode("base32").decode("ascii")` for bafy format (not `str()` which gives zdj7...)
- MediaWiki duplicate detection checks deleted file archive too - need `php maintenance/deleteArchivedFiles.php --delete --force`
- mwclient `upload()` returns dict - must check `result['upload']['result']` for actual success
- Pinning service does async background pin - content may not be on maybelle immediately

## Pending
- Push maybelle-config transcoding changes
- Consider VP9 (royalty-free) instead of H.264
- User page: Justin's is `User:JMyles` with `[[Ethereum Address::0x4f84b3650Dbf651732a41647618E7fF94A633F09]]` and `[[Display Name::justinholmes.eth]]`

## Files Modified
- `blue-railroad-import/`: token_page.py, importer.py, thumbnail.py, wiki_client.py, pyproject.toml
- `maybelle-config/maybelle/pinning-service/server.js`
- PickiPedia templates: Blue Railroad Token, Blue Railroad Token Gallery, Blue Railroad Gallery Item, Blue Railroad Owner Link
