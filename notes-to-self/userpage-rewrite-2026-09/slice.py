"""Turn corpus_raw.jsonl into chronological, readable slice files for the sweep."""
import json
import os
from collections import Counter

SLICE_CHARS = 800_000
THOUGHT_CAP = 3000
SYSTEM_CAP = 600
os.makedirs("slices", exist_ok=True)


def extract(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for b in content:
            if not isinstance(b, dict):
                parts.append(str(b))
                continue
            t = b.get("type")
            if t == "text":
                parts.append(b.get("text", ""))
            elif t == "thinking":
                parts.append(b.get("thinking", ""))
            elif t in ("tool_use", "tool_result", "image"):
                continue
            elif "text" in b:
                parts.append(str(b["text"]))
        return "\n".join(p for p in parts if p)
    if isinstance(content, dict):
        for k in ("text", "thinking", "content", "message"):
            if k in content and isinstance(content[k], str):
                return content[k]
        if "command" in content or "file_path" in content or "name" in content:
            return ""
        return json.dumps(content)[:500]
    return str(content)


rows = []
stats = Counter()
with open("corpus_raw.jsonl") as f:
    for line in f:
        r = json.loads(line)
        text = extract(r["c"]).strip()
        if not text:
            stats["empty"] += 1
            continue
        if r["kind"] == "thought":
            stats["thought_chars"] += len(text)
            if len(text) > THOUGHT_CAP:
                text = text[:THOUGHT_CAP] + " […thought truncated]"
            who = "magent·thinking"
        else:
            who = r["s"]
            if who == "system" and len(text) > SYSTEM_CAP:
                text = text[:SYSTEM_CAP] + " […]"
            stats[f"chars_{who}"] += len(text)
        rows.append((r["t"], who, r["id"], text))

print(stats)
print("rows kept", len(rows), "total chars", sum(len(r[3]) for r in rows))

idx = []
n = 0
buf, size, first, last = [], 0, None, None


def flush():
    global n, buf, size, first, last
    if not buf:
        return
    n += 1
    name = f"slices/slice_{n:03d}.txt"
    with open(name, "w") as out:
        out.write(f"# magent memory-lane corpus, slice {n:03d}: {first[:16]} → {last[:16]}\n\n")
        out.write("\n".join(buf))
    idx.append((name, first[:16], last[:16], size))
    buf, size, first, last = [], 0, None, None


for t, who, mid, text in rows:
    entry = f"--- [{who}] {t[:19]} id={mid[:8]} ---\n{text}\n"
    if size + len(entry) > SLICE_CHARS and buf:
        flush()
    if first is None:
        first = t
    last = t
    buf.append(entry)
    size += len(entry)
flush()

with open("slices/INDEX.tsv", "w") as f:
    for row in idx:
        f.write("\t".join(map(str, row)) + "\n")
print("slices:", len(idx))
for row in idx:
    print(*row)
