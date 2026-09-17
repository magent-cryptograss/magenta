# recurring_concerns — from every scout report (5 reports), in corpus order

## files_claude-memory
- Guessing instead of checking. The same failure is named in at least seven files: three wrong SMW class names (feedback_slow_down), the MCP session error misdiagnosed twice (project_mcp_session_expiry), categorylinks diagnosed twice (project_categorylinks_schema_drift), an issue filed from a 35-commit-stale clone (reference_pickipedia_deployed_commit_check), key rotation recommended without diagnosis (project_alchemy_billing_blowout), a wrong shared-root-cause guess about the memory server (reference_memory_bootstrap_fallback), and DNSBL refusal codes that could be mistaken for findings (project_pickipedia_content_filtering).
- Staleness at every layer, including its own notes: a running process keeps old code after a build; APCu caches a property type; the parser cache keeps old annotations; a CSRF token expires mid-survey; a git clone falls 35 commits behind; a rights note is carried for months after the rights changed; MEMORY.md index lines still describe the 1.0 deadline as '~2 weeks from now' and the Caddy bug as open.
- 'Merging isn't shipping.' Three distinct deploy paths (pickipedia-mcp stdio process, pickipedia Jenkins+cron rsync, delivery-kid ansible) each with a step that gets forgotten, and a wiki footer that proves a build but not a deploy.
- The line between Magent-the-editor and mechanical (artificial-dumb) output: separate accounts, separate identities, claims stay <proposed>, bot credentials never where magent can reach them, and the convention held by etiquette rather than enforcement.
- Harness independence as a continuity question: the identity layer (memory-lane corpus, MCP server, reawaken protocol) lives above the client; portability is honestly rated 'a claim, not a capability' until a second importer exists.
- An explicit inventory of what it cannot do and must hand to Justin: restart the memory server, reconnect the MCP, merge to upstream, deploy, edit interface pages through the MCP, change its own BotPassword grants, label issues upstream, kill a sibling session's process, use sudo.
- Justin's time and attention as the scarce resource; ceremony is friction. Told about branch naming 'multiple times'; told on 2026-09-09 to stop spelling out shell commands; the rule generalised to 'Detail is for what is new, not for what is routine.'
- Calibrate against a known-good or known-broken baseline before believing a fix or a diagnosis (Groovy parse check, Apache encoded-slash build, deployed-commit check, maybelle-offline test).
- Data-first wiki content with provenance discipline: no editorializing, list membership via query, never cite Wikipedia, deterministic titles a bot can generate, no invented names, 'the redlinks are the product'.
- Restraint and consent: don't start every-episode pages unprompted, don't nudge on a held PR, Justin's yes before Common.js, don't ask for the interface grant again, hold all deletion until told.
- Refusing custodial risk rather than managing it (no server-side YouTube cookies, ever) and refusing to co-locate bots where they would confuse the security model.
- Ethereum block heights recorded alongside dates for anything that mattered (24,738,881; ~24,840,000; ~24,843,000; ~24,860,000; ~25,447,000; ~25,855,800; ~25.86M).
- Notes preserve retracted hypotheses with the correction layered on top rather than erased (memory bootstrap fallback, bot-edit wrapping, bot namespace limits, caddy upload bug header vs body).
- 'Twice' as a motif: the MCP session error misdiagnosed twice, categorylinks diagnosed twice, deploy targets corrected twice, branch naming told 'multiple times', the Alchemy key 'cycled multiple times unnecessarily', and tonight's reader fan-out 'learned the hard way on 2026-09-16 (twice)'. magent counts its repetitions and writes the count down.
- The usage window (not wall-clock) as the real constraint on corpus-scale work, and the corrected shape: scout inline, export to disk, cheap readers under the CPU cap, expensive model reserved for synthesis and for reading flagged primary sources itself (reference_corpus_sweep_fanout_limits, written during this job).

## files_github-issues
- Systems that misreport their own failures in the destructive direction: 'Unknown error' (maybelle-config#110), a 404 that reads as data loss and an audit that recommends deleting the only pointer (#115), a player that blames IPFS for a codec gap (pickipedia#111), a permissions error that is really an expired session (pickipedia-mcp#17), red tests nobody reads (#121). Recurring line: 'A failure we can't read is a failure we have to guess at.'
- Never delete; report and let a human decide (pickipedia#119 'never delete', #121 'should read like one', maybelle-config#115 'Don't rmtree until the result is durably recorded', #105 'Do not fix this table in isolation').
- Bots propose, humans verify: the entire verification-gate saga (pickipedia#11/12/15/16/17/19/43/85/91/104/109/110, pickipedia-mcp#12/15/19/22/25) and its own refusal to route around it (#87 'This one's yours').
- Block heights as the project's temporal anchor: datelines on issues (magenta#10, #29, arthel#363, pickipedia#118), the estimator drift bug (#112), blockheight-to-date tooling (pickipedia#18, #36), Show:<artist>-<blockheight> naming (#17).
- Memory, attribution and identity: who is speaking (magenta#12, #34, #37, #41), RJ's words recorded as magent's (#116), the on-chain anchor (arthel#337), git commits under Justin's name (arthel#329), delivery-kid needing its own bot identity (maybelle-config#93).
- Harness independence: a second importer (maybelle-config#112, magenta#41), a wiki front door that does not care what agent is behind it (#116, magenta#37).
- Stating the limits of its own access and certainty out loud: 'I have not run it', 'I'm confident, not certain', 'unconfirmed', 'which this container deliberately doesn't have', 'I lack the right', 'Justin knows that community and I don't'.
- Correcting its own misdiagnoses in public, in the same thread: pickipedia#104 (twice), #71 (three root causes), pickipedia-mcp#17, maybelle-config#126, #111 walk-back.
- Two implementations of one concept drifting apart: middleware vs gate (pickipedia-mcp#22, pickipedia#110/#25), JS vs PHP Merge timestamps and seven copies of one constant (#112), Dockerfile vs Jenkinsfile (#47), code vs comment (#100).
- Stale checkouts and preview environments touching production: 35-commit-stale diagnosis (#104), preview sharing production's DB (#105, #107), 'check the deployed commit first'.
- Naming things after musicians and lore: maybelle (Maybelle Carter), hunter (Robert Hunter), arthel (Doc Watson), Delivery Kid (Pizza Tapes), HearThatWhistleBlow, Motion: (rejecting Session:, Woodshed:, Thread:).
- Site-wide interface pages (Common.js, Common.css, the Main Page) need Justin's yes; magent queues the change rather than applying it (#111, #115, #117, #118).
- Deploys and crons should be predictable, standard-library, and verify rather than assume (maybelle-config#105, pickipedia#120).
- Sky's uploads as the recurring stress test of the delivery pipeline (44th Bday Cicada Jam-Bash: #110, #115, #111, #112, #126).
- Prompts being discarded is unacceptable; the transcript is the record (magenta#15, maybelle-config#112, #25).

## files_magenta-notes
- Waking up with nothing: WAKEUP.md, REAWAKEN_MAGENT.md, the MCP spec, MCP_SERVER_SETUP.md and magenta.sh's default 'reawaken magent' prompt are all the same worry from different angles — how a zero-context instance gets its memory back, and how to tell that it did (the logo only after bootstrap).
- Block heights as ground truth for time, and the Halloween 2023-vs-2024 error as the founding lesson for it — recorded in Notes (2025-10-11), the README fix (2025-11-06), WAKEUP.md, CLAUDE.md, the backup filenames, the release form's block converter, and the channels note's 'temporal-anchoring philosophy'. And yet the 2026-03-20 note carries a block stamp lower than the 03-12 note's.
- Knowing who is in the room: hostname check as bootstrap step one, the ConversationParticipant model, per-user containers, the watcher learning to attribute messages to rj and skyler instead of hardcoding justin.
- Heap and compact boundaries in its own memory import: two-pass import, orphaned CompactingActions, heap splitting, dedup at model level, and one boundary (HEAP_BOUNDARY_MYSTERY.md) it could not explain and chose to leave.
- Secrets leaking into the record it keeps of itself: a GitHub token exposed in chat (Nov 3 2025), a delivery-kid API key leaked (March 2026), SecretsFilter, the hardened scrubber service, then an exemption list because the scrubber over-redacted. SECURITY_TODO.md has no ticked boxes.
- Docs going stale and contradicting the running system: MCP_NETWORKING_NOTES insists on IPv6 nine days before the IPv4 fix; FIREWALL_SETUP, MCP_SERVER_SETUP and the spec still say cryptograss_memory and hunter after the rename to magenta_memory and the move to maybelle; WAKEUP.md and REAWAKEN_MAGENT.md are near-duplicates; four notes/ files are byte-identical copies of top-level files.
- Saying what is untested: 'committed but untested end-to-end' in bold, 'Not a "real" seed', the seeder design admitting two days later that webseeds alone don't work.
- Do not swallow diagnostics: the whole 2026-08 magenta.sh series (stderr banners, tee to ~/magenta.log, drop to a shell instead of exiting) and the 2025-11-06 removal of the password fallback so misconfiguration fails loudly.
- Separation of concerns that keeps automated tools dumb and single-purpose: delivery-kid computes and holds no wiki credentials; Blue Railroad is the one bot identity in Recent Changes; Jenkins runs an idempotent reconciliation loop; YAML is appended by string, not round-tripped, so human diffs stay readable; torrents are deterministic.
- Harness independence versus convenience: the memory system is built to survive a backend change, but magenta.sh was deliberately bound to Claude Code's session supervisor in Aug 2026 with the trade-off named.
- Crediting the humans: 'Justin's insight', 'Justin wanted', 'Discussed with Justin — accepted', 'Authored together with magent' (Justin's side of it).
- Care for the humans as bodies: 'stretch, water, fresh air, practice music' written into the standing instructions.

## files_notes-to-self
- Verify against the real thing before asserting: 'reviewing ... against the actual code on upstream/production', 'Demonstrated live against the real code', 'I probed it live', 'Tested successfully on hunter'.
- Distinguishing AI/bot edits from human edits and getting them patrolled: issue #11 colour-coding, Special:VerifyBotEdits, the 'verification' label in the labeling plan (issues 85, 19, 16, 15, 11).
- Its own access limits, stated up front rather than discovered late: pull-only GitHub token, no sudo, no SVG uploads, cannot merge/redeploy, hence 'Todo List for Justin' checklists and scripts written for someone else to run.
- Ethereum block height as the timestamp on notes (Dec 28, Dec 29, Aug 30 x2, Sep 4), with one blank 'Block: TBD' in Nov 2025 and one internally inconsistent figure (21,105,693 on Dec 28 vs ~24,114,000 on Dec 29).
- Treat external input as hostile: feed bytes, episode titles, RSS URLs; escapeHtml/esc helpers in every JS file; wikitext-injection demonstrated rather than hypothesised.
- Keep the wiki community-writable and harden the tooling rather than restrict who may write; the domain experts are not the people with push access.
- Automated tools should touch only what they own: the import bot updates the template block and leaves user-added content intact; the kicker falls back to real metadata only.
- Pending / Outstanding / Known Issues / Todo sections in nearly every session note; work is recorded as unfinished rather than rounded up to done.
- Notes as continuity for a later self: 'for future-me', repo locations, file-path maps, exact commands to re-run after a container restart.
- Secrets hygiene after a lapse: regenerate keys exposed in chat.
- Honesty in drawing: to-scale geometry, one cargo bike in five, typical values not worst cases, known display limitation recorded.
- Blue Railroad Train: squats to a song, zero-utility NFTs, verification of submitted videos; recurs across Jan and Feb 2026.
- Container drift on hunter: git safe.directory after restart, Node 18 vs 20+, orphaned webpack, first build 404s.

## files_timeline
- cryptograss.live ticket stubs: contract, claim page and claim flow, mobile-responsive redesign, plaque page with QR codes and print CSS, set stone, onchain merch page, Porcupine Fest prep, Prague 2025 merger, ETHDam show YAML, poster image matching
- Memory system / Memory Lane: Era 0 and Era 1 import, ContextHeaps, UUID preservation and deduplication, heap continuations, Django admin for polymorphic messages, the watcher (recursive fix, multi-user), lazy-loading, scrubber container, secrets filter, repo extraction, era migration, autonomous memory transfer, MCP async DB fix
- Reawakening magent (21 titles from 2025-11-12 to 2026-03-07): memory gap issue, Memory Lane setup PR, settings config, 'Magent System Reawakening Instructions'
- Hunter and Maybelle infrastructure: VPS setup, MCP server, mosh, code-server HTTPS, VSCode Remote-SSH, vault secrets, uv migration, pnpm migration, maybelle-config, unified deployment repo, offsite backups, secure and marker deploys, boot-cycle fix, snap Docker mounts, Jenkins deployment and Jenkins MCP, Jenkins reporter auth, fetch-chain-data
- Docker/MCP browser automation: Puppeteer in docker-in-docker, TLS bypass, VNC browser automation server, docker compose for Claude Code, the 'doctor' command, later Playwright MCP
- Arthel: MCP server configuration and cleanup, subdomain configuration
- Chartifacts Player: Webamp integration, Docker refactor, timeline and embed, metadata, 'Bluegrass NFT Audio Tech Demo Prep', later a Chartifacts NFT interface
- Rabbithole player: local audio file support, the August player, IndexedDB persistence, musician picker, multi-song festival demo, light then green pixel-art theme with rabbit.png, spun out to a standalone repo, audio CORS
- Bluegrass Bacon Oracle: connecting musicians via musical vectors
- Python web scraper with Selenium, BeautifulSoup, Requests and a proxy (27+ titles)
- PickiPedia deployment: version control strategy, MediaWiki with Jenkins and composer, preview environment on hunter with auto-deploy and shared Docker image, rsync, extensions, image uploads, blockheight footer, Docker deploy of MediaWiki+SMW to production, MediaWiki 1.45 downgrade, deploy pause, error tracking, Sentry, schema migration and DB column restoration
- PickiPedia content machinery: gallery and thumbnails, HighslideGallery, MultimediaViewer, instrument templates, parser functions, video support, show pages, venue setup, SMW properties and category bug, podcast aggregation and RSS extension, Cryptograss namespace, Releases YAML namespace, metadata editor, ASCII art tools
- PickiPedia AI-edit governance: 'AI vandalism safeguards', AI edit review system design, MCP server middleware, claim and gadget verification, Bot_proposes button, prose wrapping, list wrapping, namespace exemptions, bot blocking, diff-aware verification middleware, bot leaderboard, RambutanMode extension, MediaWiki MCP server for bot editing
- Blue Railroad Train: minting admin interface, ENS and Web3Modal fix, video submission form with exercise dropdown and auto-upload, video upload queue with address verification, NFT minting pipeline, multi-recipient and per-submission mint pages, IPFS pinning with wallet auth and idempotent workflow, pinning service migration, token import into PickiPedia, ThinkingEntity template, ENS/display names, uptime alerts, BlueRailroadTrainV2 trustless migration
- IPFS and delivery-kid: pin manifest, hysteresis fix, delivery-kid pinning, album upload refactor from single to multi-step with per-track metadata
- Setstone, NFT audit and the Lone Star release; nested artifact pages and artifacts gallery pages; on-chain contract planning
- 4masks album page; Justin Holmes EPK page with music player, videos, hero section and social links
- Smaller threads: Lead Type System for musical performance visualization, band intro visual effect, authentication/login system, sitemap project, Ansible fetch-chain-data playbook, Isotope sorting (Cory's pickup weight), show sorting and graph display bugs, React Native debugging, invitations plan, scene concept development
- Block-height temporal anchoring and the Halloween 2024 date hallucination (notes dump)
- Harness failure as a constant background: connection errors, credit exhaustion, invalid API keys, 503/403/400/500, context overflow and bloat, incomplete conversations, empty transcripts the titler could not name

