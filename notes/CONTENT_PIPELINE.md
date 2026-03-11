# Content Pipeline: PickiPedia → delivery-kid

## Architecture
Wiki login is the auth layer. Browser uploads directly to delivery-kid — no bytes through PHP/Nginx.

1. User logs into wiki, goes to Special:UploadContent (requires `upload-to-delivery-kid` right, granted to sysop)
2. PHP generates HMAC-SHA256 token from shared API key: `HMAC(api_key, "upload:{username}:{timestamp}")`
3. JS sends files directly to delivery-kid with token headers (X-Upload-Token, X-Upload-User, X-Upload-Timestamp)
4. delivery-kid verifies HMAC + timestamp freshness, accepts upload
5. Three-step UI: drag-drop upload → review/metadata → finalize (SSE progress streaming)

## Auth Methods on delivery-kid
1. HMAC upload token (browser → delivery-kid, wiki-issued)
2. API key (server-to-server, X-API-Key header)
3. Wallet signature (existing cryptograss.live flow)

## API Key Deployment Chain
Vault (`delivery_kid_api_key`) flows to:
- delivery-kid: ansible → container env → FastAPI settings
- Production pickipedia: maybelle ansible → Jenkins secrets → LocalSettings.local.php
- Dev pickipedia (hunter): hunter ansible → arthel env → container_startup.py → docker-compose env → wiki container → getenv()

## Key Files
- `pickipedia/extensions/PickiPediaReleases/src/SpecialUploadContent.php`
- `pickipedia/extensions/PickiPediaReleases/resources/ext.pickipediaReleases.upload.js`
- `pickipedia/extensions/PickiPediaReleases/extension.json`
- `maybelle-config/delivery-kid/pinning-service/app/auth.py`

## Status (March 2026)
Code committed and pushed to forks. Waiting on merge to production and deploy of both repos.
Leaked API key needs rotation.
