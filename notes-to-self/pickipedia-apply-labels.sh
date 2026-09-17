#!/bin/bash
# PickiPedia issue-labeling plan — magent, block ~25,865,700
# Requires an account with TRIAGE (or push) on cryptograss/pickipedia.
# The magent-cryptograss token is pull-only, so this WILL 404/deny under it.
set -euo pipefail
R=cryptograss/pickipedia

# --- 1. labels (idempotent; ignore "already exists") ---
gh label create security        -R $R -c d93f0b -d "Security / trust-model / access-control" 2>/dev/null || true
gh label create podcast-firehose -R $R -c 1d76db -d "Podcast aggregation + firehose pipeline" 2>/dev/null || true
gh label create verification    -R $R -c 5319e7 -d "Bot/AI edit verification workflow" 2>/dev/null || true
gh label create smw             -R $R -c 0e8a16 -d "Semantic MediaWiki properties/queries" 2>/dev/null || true
gh label create invites         -R $R -c fbca04 -d "Account-creation / invite flow" 2>/dev/null || true
gh label create infra           -R $R -c c5def5 -d "Deploy / container / build infrastructure" 2>/dev/null || true

# --- 2. assignments ---
gh issue edit 102 -R $R --add-label security,podcast-firehose
gh issue edit 101 -R $R --add-label security,podcast-firehose
gh issue edit 100 -R $R --add-label security,invites,bug
gh issue edit 97  -R $R --add-label security,podcast-firehose
gh issue edit 87  -R $R --add-label smw,bug
gh issue edit 85  -R $R --add-label verification,bug
gh issue edit 70  -R $R --add-label enhancement
gh issue edit 60  -R $R --add-label enhancement
gh issue edit 59  -R $R --add-label invites,bug
gh issue edit 51  -R $R --add-label security,enhancement
gh issue edit 36  -R $R --add-label enhancement
gh issue edit 20  -R $R --add-label bug,infra
gh issue edit 19  -R $R --add-label verification,enhancement
gh issue edit 18  -R $R --add-label enhancement
gh issue edit 17  -R $R --add-label smw,enhancement
gh issue edit 16  -R $R --add-label smw,verification,enhancement
gh issue edit 15  -R $R --add-label verification,enhancement
gh issue edit 13  -R $R --add-label infra,bug
gh issue edit 12  -R $R --add-label bug
gh issue edit 11  -R $R --add-label verification,enhancement
gh issue edit 3   -R $R --add-label bug
gh issue edit 2   -R $R --add-label smw
gh issue edit 1   -R $R --add-label infra,enhancement,documentation
echo "done"
