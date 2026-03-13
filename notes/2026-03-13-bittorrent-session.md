# BitTorrent Integration Session — 2026-03-13 (Block ~24,650,800)

## What we built

### Deterministic torrent generation (`torrent.py`)
- Pure Python implementation (no external library) of bencode + SHA-1 torrent creation
- **Deterministic infohash**: same files + same CID as torrent name = identical infohash every time
- Piece length computed deterministically from total file size (target ~1500 pieces, power-of-2 sizes)
- Files sorted alphabetically by path
- No non-deterministic fields in the info dict (timestamps, private flags, etc. excluded)
- WebSeeds: delivery-kid IPFS gateway (primary) + ipfs.io (fallback)
- Default public trackers (opentrackr, openbittorrent, etc.)
- Lives at `delivery-kid/pinning-service/app/services/torrent.py`

### Delivery-kid endpoint: `POST /enrich/torrent`
- Takes `{"cid": "Qm..."}`, fetches directory from local IPFS, generates deterministic torrent
- Returns `{infohash, trackers, file_count, total_size, piece_length}`
- Auth-gated (API key) — expensive operation (IPFS fetch + SHA-1 hashing of all bytes)
- Does NOT edit wiki pages — that's Blue Railroad's job
- Route: `delivery-kid/pinning-service/app/routes/enrich.py`

### Blue Railroad enrichment: `enrich-torrents` CLI command
- New module `blue_railroad_import/torrent_enrichment.py`
- Queries PickiPedia API (`action=releaselist&filter=missing-torrent`)
- For each release missing `bittorrent_infohash`, calls delivery-kid's `/enrich/torrent`
- Appends infohash + trackers to Release page YAML (string append, NOT yaml.dump round-trip — preserves existing formatting)
- Saves under Blue Railroad bot identity — clean Recent Changes
- 15 tests covering formatting preservation, idempotency, error handling, full flow
- 152/152 tests passing across the full blue-railroad-import suite

### Jenkins job: `pickipedia-enrich-torrents`
- Runs every 2 minutes (fast no-op when nothing needs enrichment)
- Uses `BLUERAILROAD_BOT_USERNAME`/`PASSWORD` for wiki edits
- Uses `DELIVERY_KID_API_KEY` for torrent generation
- Job definition: `maybelle/jobs/pickipedia-enrich-torrents.groovy`

## Architecture decisions

### Separation of concerns
- **Delivery-kid**: compute only (IPFS access + torrent math). No wiki credentials.
- **Blue Railroad bot**: orchestration + wiki edits. Consistent bot identity in Recent Changes.
- **Jenkins**: scheduling. Every 2 minutes, same cadence as the import job.

### Why not in the finalize pipeline
- Justin's insight: this should be a reconciliation loop, not coupled to finalize
- Handles existing releases AND new ones identically
- Idempotent — safe to run repeatedly

### Why delivery-kid doesn't edit wiki pages
- Justin wanted Blue Railroad Imports as the single bot identity in Recent Changes
- YAML formatting concern: round-tripping through yaml.dump would reformat all pages
- Solution: Blue Railroad appends fields surgically, delivery-kid just returns data

### YAML append strategy (important!)
- `append_torrent_fields()` parses YAML to check state, but writes by string append
- Existing formatting (key order, comments, whitespace, list indentation) is preserved
- Only change visible in wiki diff: two new fields at bottom of page
- Tested explicitly: `test_preserves_key_order`, `test_preserves_comments_and_whitespace`, etc.

### Webseed vs. dedicated BT seeder
- Currently using HTTP webseed (BEP 19) pointing at delivery-kid's IPFS gateway
- BT clients can download files immediately via HTTP — functionally works
- Not a "real" seed: doesn't announce to trackers, doesn't join swarm as a peer
- Decided: webseed is sufficient for now, add Transmission daemon later if swarm matters
- The swarm forms organically once anyone downloads (they become a peer)

## Cleanup
- **Removed `maybelle/pinning-service/`** — dead Node.js code, predecessor to delivery-kid
- **Removed stray `torrent.py` from blue-railroad-import** — delivery-kid owns torrent generation
- JS torrent implementation removed earlier with maybelle/pinning-service

## What's already built on PickiPedia (from previous sessions)
- `ReleaseContent.php`: `getBittorrentHash()`, `getBittorrentTrackers()`
- `ReleaseContentHandler.php`: `renderTorrentLink()` — magnet URI rendering
- `ApiReleaseList.php`: `missing-torrent` filter — queries releases needing torrents
- Release YAML schema: `bittorrent_infohash`, `bittorrent_trackers` fields

## Git state
- **maybelle-config** branch `multi-step-album-upload`
  - Deployed to production: enrich endpoint, Caddy route, Jenkins env var
  - Pending merge: cron schedule (2min), webseed change (delivery-kid gateway)
- **blue-railroad-import** `main` at `2ae78aa` — pushed, ready for Jenkins pickup
- **pickipedia** — production has magnet link rendering, Release YAML support

## Deployment status
- Delivery-kid: `/enrich/torrent` endpoint live (verified — returns 405 on GET)
- Jenkins: `pickipedia-enrich-torrents` job created, needs rebuild for `DELIVERY_KID_API_KEY` env var
- Blue-railroad-import: pushed to GitHub, Jenkins will install on next rebuild

## What's next
1. **Merge remaining commits** to production (2min cron + webseed) and redeploy
2. **Verify end-to-end**: trigger Jenkins job, confirm Release pages get infohash + trackers
3. **Test magnet link**: click a magnet link on a Release page, confirm download works via webseed
4. **Later**: Add Transmission daemon for proper BT seeding if swarm growth warrants it
5. **Test finalize progress UI end-to-end** — still untested with real delivery-kid SSE stream
6. **Issue #51** — Restrict ReleaseDraft namespace read access
