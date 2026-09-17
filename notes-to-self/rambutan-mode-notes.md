# RambutanMode Extension Notes - January 2026

## What It Does
MediaWiki extension that adds "Rambutan" as a middle name/alias to person and band articles when user has mode enabled.

## Key Files
- **Repo:** https://github.com/cryptograss/RambutanMode
- **Extension location:** pickipedia/extensions/RambutanMode (git submodule)

## Parser Functions
- `{{#rambutan:Tony Rice}}` → `Tony "Rambutan" Rice` (two names) or `Name (also known by the stage name "Rambutan")` (3+ names)
- `{{#rambutanband:Band Name}}` → `Band Name (formerly known as Rambutan)`

## Key Bug Fixed
The toggle wasn't appearing because `needsToken()` returned `'csrf'` for ALL actions including the read-only `status` check. Fixed by making token requirement conditional - only `enable`/`disable` need CSRF tokens, not `status`.

## Architecture Notes
- Parser functions run at page parse time, so output depends on viewing user's preference
- This means pages using these functions will show different content to different users
- Toggle state stored in user options: `rambutanmode` (0/1) and `rambutanmode-enabled-at` (timestamp)
- Auto-expires at midnight Florida time (America/New_York) - checked by comparing enabled-at timestamp to today's midnight

## For Adding to More Pages
Pages need to explicitly use the parser functions. Example on Cory Walker page shows the pattern:
```wikitext
'''{{#rambutan:Cory Walker}}''' is best known as...
He plays in {{#rambutanband:[[East Nash Something]]}}.
```

## Future Enhancement Ideas (discussed but not implemented)
- Could hook into link rendering to auto-transform links to pages in Category:Musicians
- But this has caching implications - would need client-side JS approach
- Template wrappers like `{{Person|Name}}` and `{{Band|Name}}` would be cleaner

## Deployment
- Added as git submodule to pickipedia
- Jenkinsfile updated with "Initialize Submodules" stage
- PR #30: https://github.com/cryptograss/pickipedia/pull/30
