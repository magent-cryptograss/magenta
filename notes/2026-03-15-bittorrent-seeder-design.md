# BitTorrent Seeder Design — 2026-03-15

## Problem
Magnet links don't work because there are no peers with the torrent metadata.
Webseeds can only be used *after* the client has metadata (piece hashes, file list).
With no existing peers or .torrent file available, clients stay stuck at "downloading metadata" forever.

## Solution: Integrated libtorrent seeder in delivery-kid

### Architecture
A libtorrent session running inside the FastAPI process on delivery-kid.
When a torrent is generated, content is kept in a seeding directory and
the torrent is loaded into the session. delivery-kid becomes the first
(and potentially only) seeder.

### Components

1. **`app/services/seeder.py`** — libtorrent session manager
   - Singleton session started via FastAPI lifespan
   - Seeding directory: `/staging/seeding/{cid}/` (on Hetzner Storage Box)
   - Each CID dir contains: content files + `torrent.dat` (the .torrent bytes)
   - On startup: scan seeding dir, load all saved torrents
   - Methods:
     - `add_torrent(cid, torrent_bytes, data_dir)` — move content to seeding dir, load into session
     - `get_torrent_file(infohash) -> bytes` — serve .torrent file
     - `status() -> dict` — seeding stats (num torrents, peers, upload rate)
   - Listens on ports 6881-6891 for peer connections

2. **Modify `app/routes/enrich.py`**
   - After generating torrent, move content to seeding dir instead of deleting
   - Save .torrent bytes alongside content
   - Add torrent to seeder session
   - Return `torrent_url` in response (e.g. `https://delivery-kid.cryptograss.live/torrent/{infohash}.torrent`)

3. **New endpoint: `GET /torrent/{infohash}.torrent`**
   - Serves the .torrent file directly
   - Clients can get metadata + webseed info from this file
   - No need for peers/DHT to bootstrap

4. **Docker config changes** (ansible playbook)
   - Expose ports 6881-6891 TCP+UDP for BitTorrent swarm
   - libtorrent pip dependency in Dockerfile

5. **Caddy config**
   - Add `/torrent/*` route to pinning service

6. **PickiPedia Release page**
   - Add .torrent download link alongside magnet link
   - Store `bittorrent_torrent_url` in Release YAML
   - PHP renderer shows `[torrent]` link

### Why libtorrent over Transmission/qBittorrent
- Already in the same Python process — no extra daemon
- We generate torrent bytes programmatically — can load directly into session
- Total control over behavior
- Less infrastructure to manage
- pip install, no system packages needed
- Already tested libtorrent works (used it for debugging today)

### Considerations
- Storage: seeding dir will grow as releases accumulate. ~640MB per video,
  but these files are also in IPFS blocks on the same storage box (duplication).
  Could use symlinks or hardlinks to IPFS block store, but IPFS stores blocks
  as shards, not whole files. So some duplication is unavoidable.
- The storage box is CIFS-mounted, which can be slow for random reads.
  Piece hashing during initial load might be slow. Could skip verification
  on startup since we generated the content ourselves.
- Memory: libtorrent session is lightweight even with hundreds of torrents.
- Port exposure: need 4001 (IPFS) + 6881+ (BT) — check firewall.

### Deployment sequence
1. Add libtorrent to Dockerfile
2. Build seeder.py service
3. Modify enrich.py to use seeder
4. Add /torrent/ endpoint and Caddy route
5. Expose BT ports in Docker and firewall
6. Deploy delivery-kid
7. Clear and regenerate all torrent metadata (includes torrent_url)
8. Update PHP renderer to show .torrent link
9. Deploy pickipedia

### Status
- IPFS gateway confirmed working (HTTP 200, serves files, supports Range requests)
- libtorrent installed and tested on hunter
- Caddy /webseed/ rewrite confirmed working for multi-file torrents
- Single-file direct IPFS gateway URL confirmed working
- 28 releases have infohashes but no peers/seeders
- Webseeds stored in YAML (pending deploy of latest blue-railroad-import)
