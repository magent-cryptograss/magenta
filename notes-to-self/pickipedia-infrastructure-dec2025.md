# PickiPedia Infrastructure Work - December 28, 2025

## Context
Working with Justin on hunter.cryptograss.live to fix PickiPedia 500 errors and set up proper infrastructure.

## Root Cause of 500 Errors
**MediaWiki 1.45.1 is incompatible with Semantic MediaWiki 6.0.1**

The error was:
```
TypeError: MediaWiki\Content\JsonContentHandler::__construct(): Argument #2 ($parsoidParserFactory) must be of type ?MediaWiki\Parser\Parsoid\ParsoidParserFactory, array given
```

SMW's SchemaContentHandler calls JsonContentHandler with the old API signature. MW 1.45 changed the constructor.

**Fix:** Downgraded to MediaWiki 1.43.6 LTS (SMW 6.0.1 supports MW 1.43-1.44)

Commit in pickipedia repo: `0c6eff4` - changes Jenkinsfile MEDIAWIKI_VERSION and TimedMediaHandler branch to REL1_43.

## Current Issue: DBQueryError on RecentChanges
After downgrade, RecentChanges throws DBQueryError. Haven't been able to see the actual error because NFSN's error logging is extremely difficult - PHP errors don't appear in any accessible logs.

## Solution: GlitchTip Error Tracking
Set up GlitchTip (open source Sentry alternative) on maybelle to get proper error tracking.

### GlitchTip Setup Status
- Branch: `glitchtip-setup` on magent-cryptograss/maybelle-config
- Services: postgres, redis, web, worker containers
- URL: https://glitchtip.maybelle.cryptograss.live
- Caddy route added to Caddyfile.maybelle.j2

### Issues Fixed During Setup
1. Port mapping: GlitchTip listens on 8080, not 8000 - fixed to `8800:8080`
2. Email config: Added `EMAIL_URL: "consolemail://"` to avoid SMTP connection errors
3. Registration: Set `ENABLE_OPEN_USER_REGISTRATION: "True"` for initial setup

### Secrets Needed in Vault
```yaml
glitchtip_secret_key: <regenerate - old ones exposed in chat>
glitchtip_postgres_password: <regenerate>
pickipedia_sentry_dsn: <get from GlitchTip after creating project>
```

## PickiPedia Changes Ready to Deploy
Branch: main on magent-cryptograss/pickipedia (commit `6c3d1e2`)

- Added sentry/sentry SDK to composer.json
- Added mediawiki/hit-counters extension
- LocalSettings.php: Sentry init code + HitCounters wfLoadExtension
- LocalSettings.local.php template updated to include $wgSentryDsn

## Todo List for Justin

1. ☐ Merge `glitchtip-setup` branch to maybelle production (latest commit: 967c6fb)
2. ☐ Redeploy maybelle
3. ☐ Create GlitchTip account at https://glitchtip.maybelle.cryptograss.live
   - Check `docker logs glitchtip-web` for email verification link
   - First user becomes admin
4. ☐ Create PickiPedia project in GlitchTip, copy the DSN
5. ☐ Add `pickipedia_sentry_dsn` to vault and redeploy maybelle
6. ☐ Merge pickipedia changes to production and trigger Jenkins build
7. ☐ Run on NFSN: `php maintenance/run.php update --quick` (for HitCounters tables)
8. ☐ Verify RecentChanges works - GlitchTip will show actual errors now
9. ☐ Set up GoAccess for NFSN access log analysis (lower priority)

## Additional Context
- NFSN access logging was turned on with weekly rotation
- Considered GoAccess for log analysis + HitCounters extension for per-page stats
- Deploy pause mechanism works: `/var/jenkins_home/.pickipedia-deploy-paused`

## Block Height
Working around Ethereum block 21,105,693 - 21,113,000
