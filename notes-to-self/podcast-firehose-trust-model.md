# Podcast firehose: the trust model, end to end

Written block ~25,865,700 (2026-08-30), reviewing the Aug-18 podcast work
(#95/#96/#97/#98/#99) against the actual code on `upstream/production`.

## Justin's question, answered plainly

> An attacker with write access can create a malicious RSS feed and then cause
> our firehose parser to consume it by adding it to a page in the podcast
> category, right?

**Right — that is exactly the shape.** Moving podcast config onto the wiki
(#95) didn't add a fetch; it changed *who decides what gets fetched and what
regexes get run on the result*. The category is the control surface: anything
in `Category:Podcasts` with a `{{Podcast|rss=...}}` gets pulled on the cron.

The threat actor is **anyone in the `user` group** — i.e. anyone who created an
account. Account creation is invite-gated (`PickiPediaInvitations`), and
`$wgGroupPermissions['*']['edit'] = false`, so it is *not* the open internet.
But it is a low bar: one invite code and you can edit the parser config.

## What is already defended (Aug-18, all merged, all reproduced first)

The Aug-18 work was good and the guards are real. Three landed in #96
(`podcast_net.py`, `podcast_budget.py`):

1. **ReDoS** — Python `re` has no timeout; `^(?P<guest>[A-Za-z ]+)+$` against a
   50-char title never returns. `podcast_budget.budget()` gives each *show* a
   SIGALRM wall-clock allowance. Blast radius = that show's guest names.
   (Needs no attacker — a contributor writing a greedy pattern trips it.)
2. **SSRF via feed URL** — `assert_safe_url()` refuses non-http schemes and any
   host resolving to loopback / RFC1918 / link-local / reserved / multicast.
   Deliberately *not* airtight: resolve-and-check has a DNS-rebinding TOCTOU
   gap, and the docstring says so. Proportionate to "someone with an account,"
   not "someone running a rebinding server."
3. **Entity expansion** — `fetch_bytes()` caps the body at 8 MiB and reads one
   byte past the cap so an over-long body is *refused*, not truncated into
   malformed XML. (This one predated the wiki entirely.)

Good instinct in all three: put the blast radius where the config loader
already puts it, and never let one bad show take down the other twelve.

## What is NOT yet defended — the two gaps I'd file

### GAP 1 — wikitext injection on the WRITE side (new, not in #96)

#96 hardened the *fetch*. It did nothing about what we do with feed **content**
after we have it. `podcast-episodes.py::make_wikitext()` interpolates the
episode title and description straight into a `{{PodcastEpisode|...}}` template
with **no escaping**. Demonstrated live against the real code:

    input title:  Ep 12}}{{Delete|reason=spam}}[[Category:Verified shows]]{{PodcastEpisode|title=Innocent
    output:       ...|title=Ep 12}}{{Delete...}}[[Category:Verified shows]]{{PodcastEpisode|title=Innocent...

An episode title chosen by whoever controls the feed can:
  - close the template early (`}}`) and inject arbitrary templates/wikitext,
  - forge `[[Category:...]]` membership (e.g. claim "Verified shows"),
  - inject extra `|param=` pairs — description already yielded
    `...|topic=Bill Monroe|description=hijacked` via an HTML entity (`&#124;`).

This runs only under `--create` (default is dry-run), so it is not firing on the
cron *today*. But it is the live hazard the moment episode-page creation is
automated — which is the stated plan (redlinks are the product).

**Fix shape:** sanitize before interpolation. Strip/escape `{ } | [ ] < >` and
newlines from every feed-derived value; `html.unescape()` BEFORE stripping (not
after) so `&#124;` can't smuggle a pipe past the filter; cap length. Same
posture the fetch guards already take — treat feed bytes as hostile.

### GAP 2 — second SSRF surface: the RSS extension inside the wiki

`Template:Podcast`'s doc and `Template:LatestPodcastEpisodes` embed
`<rss>{{{rss}}}</rss>`. That is the **MediaWiki RSS extension**, a completely
separate fetcher from our Python — and `podcast_net`'s guards never touch it.
LocalSettings.php sets:

    $wgRSSUrlWhitelist = array( "*" );   // = fetch anything

I probed it live: `<rss>http://127.0.0.1:1/feed.xml</rss>` on a sandbox page
made the wiki container *attempt the loopback connection* (failed only because
the port was closed) and **reflected the connection result to the anonymous
reader**:

    Error fetching URL: Failed to connect to 127.0.0.1 port 1 ...

So any account holder can turn a wiki page into an SSRF request from inside the
container, with the response/error surfaced to unauthenticated readers — a
blind-to-semi-blind SSRF oracle against the internal network / cloud metadata.
This is arguably worse than the firehose path because it fires on *page view*,
synchronously, no cron needed.

**Fix shape:** replace `array("*")` with an explicit allowlist of feed hosts,
or front it with the same `assert_safe_url` posture. At minimum, deny RFC1918 /
loopback / link-local at the extension level. `$wgAllowExternalImages = true`
(same file, same "small trusted wiki" rationale) widens the reflected-fetch
surface a little further via `<img>` and is worth revisiting in the same pass.

## The deliberation in #97 — my read

#97 asks: harden against hostile regexes, or restrict who may write them?
**They solve different problems and neither is a superset** (the table in #97 is
correct). Restriction does NOT touch: accidental ReDoS, SSRF via feed URL, or
entity expansion — those are content/parser problems, not authorship problems.
Restriction DOES help only the *deliberately* malicious regex.

My recommendation: **keep it community-writable, keep hardening.** The whole
point of #95 was that the people who know bluegrass podcasts aren't the people
with push access. Locking the parser to a `podcast-editor` group throws that
away to buy protection against one of four threats — the other three you'd have
to fix anyway. The precedent cited (`release-edit` on ns 3004) is for a
namespace holding *release money data*, a different risk class.

The sane middle: community-writable feeds + patterns, with these guardrails:
  - [done #96] per-show ReDoS budget, SSRF check, size cap on the Python fetch
  - [GAP 1] escape feed content on the write path before it becomes wikitext
  - [GAP 2] lock down `$wgRSSUrlWhitelist` to a host allowlist
  - [worth adding] the firehose cron already runs `timeout` + writes to a temp
    file and only `mv`s on success (see maybelle pickipedia-vps ansible) —
    good, keep it; a stalled run keeps serving the last good feed.
  - [operational] a bad pattern/feed logs the *page name* to fix. Make sure that
    log is actually read (GlitchTip DSN is wired in the ansible role).

## Where the pieces live (for future-me)

- Fetch guards:   `tools/podcast_net.py`, `tools/podcast_budget.py`
- Config loader:  `tools/podcast_config.py`  (wiki-first, repo fallback, MERGE)
- Write path:     `tools/podcast-episodes.py::make_wikitext / make_page_title`
- Firehose out:   `tools/podcast-firehose.py`  (ElementTree escapes on write — OK)
- Cron/deploy:    maybelle-config `pickipedia-vps/ansible/roles/mediawiki/tasks/main.yml`
                  → `/usr/local/bin/pickipedia-firehose.sh`, cron min 9, `timeout` wrapped
- RSS extension:  LocalSettings.php ~L276-285 (`$wgRSSUrlWhitelist`, `$wgAllowExternalImages`)
- Auth gate:      LocalSettings.php L157-162 (anon can't edit; user can), PickiPediaInvitations
