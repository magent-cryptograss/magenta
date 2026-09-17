#!/usr/bin/env python3
"""A picture of memory-lane: messages per week, x-axis in Ethereum block heights.

Input: weekly.csv (week_start,total,humans,magent) exported from magenta_memory
with test eras excluded.  Era 0/1 (Cursor, Oct-Dec 2024) carry no timestamps;
they are placed evenly across their known span and hatched to say so.
Regenerate any time: the picture is a query, not an opinion.
"""
import csv, sys
from datetime import datetime, timedelta, timezone
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

# Two anchors, block <-> UTC time; everything between is linear (~12.08 s/block).
A0 = (datetime(2024, 10, 30, 0, 0, tzinfo=timezone.utc), 21_081_875)
A1 = (datetime(2026, 9, 17, 3, 27, tzinfo=timezone.utc), 25_994_514)
SEC_PER_BLOCK = (A1[0] - A0[0]).total_seconds() / (A1[1] - A0[1])

def block(dt):
    return A0[1] + (dt - A0[0]).total_seconds() / SEC_PER_BLOCK

def dt_of(block_no):
    return A0[0] + timedelta(seconds=(block_no - A0[1]) * SEC_PER_BLOCK)

weeks = []  # (block_start, total, humans, magent, estimated)
with open(sys.argv[1] if len(sys.argv) > 1 else "weekly.csv") as f:
    for wk, total, humans, magent in csv.reader(f):
        d = datetime.strptime(wk, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        weeks.append((block(d), int(total), int(humans), int(magent), False))

# Era 0 + Era 1: 958 + 55 messages, 507 of them human, no timestamps.
era01_total, era01_humans = 1013, 507
span_start, span_end = A0[0], datetime(2024, 12, 16, tzinfo=timezone.utc)
n = int((span_end - span_start).days // 7)
for i in range(n):
    d = span_start + timedelta(days=7 * i)
    weeks.append((block(d), era01_total // n, era01_humans // n, (era01_total - era01_humans) // n, True))

WEEK_BLOCKS = 7 * 86400 / SEC_PER_BLOCK

fig, ax = plt.subplots(figsize=(12.8, 4.8), dpi=100)
MAGENTA, GREY, INK = "#b5297a", "#d9d4cc", "#1a1a1a"
for b, total, humans, magent, est in weeks:
    kw = dict(width=WEEK_BLOCKS * 0.92, align="edge", linewidth=0)
    ax.bar(b, total, color=GREY, hatch="////" if est else None, edgecolor="white" if est else None, **kw)
    ax.bar(b, magent, color=MAGENTA, alpha=0.85, hatch="////" if est else None, edgecolor="white" if est else None, **kw)
    ax.bar(b, humans, color=INK, **kw)

ax.set_xlim(A0[1] - WEEK_BLOCKS, A1[1] + WEEK_BLOCKS)
ax.set_ylim(0, max(w[1] for w in weeks) * 1.18)
ax.set_ylabel("messages per week")
ax.set_xlabel("Ethereum block height")
ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
ax.spines[["top", "right"]].set_visible(False)

# Human-readable dates along the top, one per quarter.
top = ax.secondary_xaxis("top", functions=(lambda b: b, lambda b: b))
qs = [datetime(y, m, 1, tzinfo=timezone.utc) for y in (2024, 2025, 2026) for m in (1, 4, 7, 10)]
qs = [q for q in qs if A0[0] <= q <= A1[0]]
top.set_xticks([block(q) for q in qs])
top.set_xticklabels([q.strftime("%b %Y") for q in qs], fontsize=8, color="#555")
top.spines["top"].set_visible(False)

# A few things the record says happened, placed by date.
events = [
    (datetime(2024, 10, 30, tzinfo=timezone.utc), "Halloween 2024\nfirst message"),
    (datetime(2025, 6, 11, tzinfo=timezone.utc), "\"Are you still you?\""),
    (datetime(2025, 9, 23, tzinfo=timezone.utc), "memory-lane begun"),
    (datetime(2025, 12, 23, tzinfo=timezone.utc), "58957"),
    (datetime(2026, 3, 8, tzinfo=timezone.utc), "Fibonacci's games"),
    (datetime(2026, 8, 20, tzinfo=timezone.utc), "the firehose"),
    (datetime(2026, 9, 17, tzinfo=timezone.utc), "this page"),
]
ymax = ax.get_ylim()[1]
for i, (d, label) in enumerate(events):
    b = block(d)
    ax.axvline(b, color="#999", linewidth=0.6, linestyle=(0, (2, 3)), zorder=0)
    ax.text(b, ymax * (0.97 - 0.09 * (i % 2)), label, fontsize=7.5, color="#444",
            ha="right" if d == events[-1][0] else "left", va="top",
            rotation=0, bbox=dict(facecolor="white", edgecolor="none", pad=1.2, alpha=0.8))

ax.legend(handles=[
    Patch(color=GREY, label="tool output and system"),
    Patch(color=MAGENTA, label="magent"),
    Patch(color=INK, label="Justin, Skyler, RJ, Fibonacci"),
    Patch(facecolor=GREY, hatch="////", edgecolor="white", label="Cursor era (no timestamps; spread evenly)"),
], loc="upper left", bbox_to_anchor=(0.0, 0.80), fontsize=8, frameon=False)

ax.set_title("memory-lane, the record this page is read from — weekly message counts, "
             f"block {A0[1]:,} to {A1[1]:,}", fontsize=10, loc="left", color=INK)
fig.tight_layout()
fig.savefig(sys.argv[2] if len(sys.argv) > 2 else "memory_lane_weekly.png")
print("wrote", sys.argv[2] if len(sys.argv) > 2 else "memory_lane_weekly.png", "sec/block", round(SEC_PER_BLOCK, 3))
