# PickiPedia Session Notes - December 29, 2025

## What We Accomplished

### Infrastructure Fixes
- Fixed SMW/MW version incompatibility (downgraded to MW 1.43.6 LTS for SMW 6.0.1)
- Set up GlitchTip for error tracking on maybelle
- Fixed Sentry PHP SDK integration:
  - Downgraded to sentry/sentry ^3.0 for PHP 8.2/8.3 compatibility
  - Added php-http/curl-client and guzzlehttp/psr7 for HTTP transport
  - Added proper error/exception handlers (set_exception_handler, set_error_handler, register_shutdown_function) - commit 8d81754
- Fixed HitCounters extension (use dev-REL1_43 branch)
- Added RSS extension for embedding podcast feeds
- Added `--ignore-platform-reqs` to composer in Jenkinsfile
- Added `BUILD_CACHE_VERSION` env var to force cache invalidation when adding extensions
- Added `--exclude='.git'` to rsync to reduce deploy size
- Added `--exclude='stats/'` to rsync for GoAccess reports
- Set up GoAccess for access log analytics at /stats/

### Templates Created
- Template:Band - bands with semantic properties (origin, scene, genre, members)
- Template:Scene - geographic music communities
- Template:Venue - music venues with calendar URLs for future scraping
- Template:Show - individual performances with date, venue, bands
- Template:Podcast - podcast infobox (RSS embed must be added manually on page due to extension limitation)

### Known Issues
- RSS extension doesn't support template variable substitution - must embed `<rss>` tag directly on pages, not via template
- Sentry wasn't catching errors until we added custom error handlers - now should work (needs verification after deploy)
- Some 500 errors still not showing in GlitchTip - the new error handlers in commit 8d81754 should fix this

### Pending Items
- Verify Sentry error handlers are working after deploy
- maybelle-config glitchtip-setup branch has rsync exclusions - needs merge to production
- GoAccess cron job set up on NFSN, outputting to /stats/index.html

## Issues Created
- magent-cryptograss/rabbithole#1 - Include podcasts option for picker guest episodes
- cryptograss/pickipedia#11 - Color-coding for AI-edited content pending patrol

## Next Up: AI Edit Color-Coding
Brainstorming simpler alternatives to FlaggedRevs:
- CSS styling based on last editor being in "bot" user group
- Semantic property approach with [[review_status::pending]]
- Custom extension that hooks into RecentChanges display

The key question: how to automatically detect AI vs human edits and display them differently until patrolled.

## Repo Locations
- pickipedia: cryptograss/pickipedia (upstream), magent-cryptograss/pickipedia (fork)
- maybelle-config: cryptograss/maybelle-config (upstream), magent-cryptograss/maybelle-config (fork)
- rabbithole: magent-cryptograss/rabbithole

## Current Ethereum Block
~24,114,000 (approximate as of session)
