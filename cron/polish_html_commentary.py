#!/usr/bin/env python3
import argparse
import html
import json
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from openai import OpenAI

LED_RE = re.compile(r'(<p class="lede">)(.*?)(</p>)', re.DOTALL | re.IGNORECASE)


def est_today():
    return datetime.now(ZoneInfo("America/New_York")).date().isoformat()


def target_files(site_root: Path, date_str: str):
    candidates = [
        site_root / f"{date_str}.html",
        site_root / f"{date_str}-plus-money.html",
        site_root / f"{date_str}-run-line.html",
        site_root / f"{date_str}-run-totals.html",
    ]
    return [p for p in candidates if p.exists()]


def extract_ledes(text: str):
    items = []
    for i, m in enumerate(LED_RE.finditer(text), 1):
        raw_inner = m.group(2)
        # HTML lede content is plain text in practice; normalize defensively.
        clean = re.sub(r"<[^>]+>", "", raw_inner)
        clean = html.unescape(clean).strip()
        items.append({
            "index": i,
            "start": m.start(),
            "end": m.end(),
            "text": clean,
        })
    return items


def call_rewriter(batch, model_name):
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        env_paths = [
            Path("/Users/asmith/.openclaw/workspace/baseball/.env"),
            Path("/Users/asmith/.openclaw/workspace/baseball/.env.local"),
        ]
        for p in env_paths:
            if not p.exists():
                continue
            for line in p.read_text(encoding="utf-8").splitlines():
                t = line.strip()
                if t.startswith("OPENAI_API_KEY="):
                    api_key = t.split("=", 1)[1].strip().strip('"').strip("'")
                    break
            if api_key:
                break
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    client = OpenAI(api_key=api_key)

    system_prompt = (
        "You are a grizzled MLB betting analyst and veteran beat writer. Rewrite commentary so it pops: sharper voice, tighter rhythm, "
        "clear edge, no fluff, still factual. Keep each rewrite to one paragraph and preserve factual meaning. "
        "Do not invent facts, numbers, players, injuries, weather, line movement, or outcomes."
    )

    user_prompt = (
        "For each item below: in the voice of a grizzled MLB analyst, make this commentary better and make it pop. "
        "Keep it punchy and publication-ready while preserving all factual meaning. "
        "Return STRICT JSON only as an array of objects with fields: id, commentary.\n\n"
        f"Input:\n{json.dumps(batch, ensure_ascii=False)}"
    )

    resp = client.chat.completions.create(
        model=model_name,
        temperature=0.5,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    raw = (resp.choices[0].message.content or "").strip()

    # Parse loose JSON payload.
    try:
        parsed = json.loads(raw)
    except Exception:
        start = raw.find("[")
        end = raw.rfind("]")
        if start >= 0 and end > start:
            parsed = json.loads(raw[start : end + 1])
        else:
            raise RuntimeError("LLM returned non-JSON payload")

    if not isinstance(parsed, list):
        raise RuntimeError("LLM payload must be a JSON array")

    out = {}
    for item in parsed:
        if not isinstance(item, dict):
            continue
        i = item.get("id")
        txt = str(item.get("commentary", "")).strip()
        if i is None or not txt:
            continue
        out[str(i)] = txt
    return out


def apply_rewrites(original_html: str, ledes, rewrites):
    if not ledes:
        return original_html, 0

    parts = []
    last = 0
    changed = 0

    for item in ledes:
        # Recompute match from original text slices via indices captured from regex pass.
        m = LED_RE.search(original_html, item["start"], item["end"])
        if not m:
            continue
        parts.append(original_html[last : m.start()])

        rid = str(item["index"])
        new_text = rewrites.get(rid)
        if new_text:
            escaped = html.escape(new_text, quote=False)
            parts.append(f'{m.group(1)}{escaped}{m.group(3)}')
            if escaped.strip() != m.group(2).strip():
                changed += 1
        else:
            parts.append(m.group(0))

        last = m.end()

    parts.append(original_html[last:])
    return "".join(parts), changed


def git_commit_push(site_root: Path, files, date_str: str):
    rels = [str(p.relative_to(site_root)) for p in files]

    add = subprocess.run(["git", "add", *rels], cwd=str(site_root), capture_output=True, text=True)
    if add.returncode != 0:
        raise RuntimeError(add.stderr.strip() or add.stdout.strip() or "git add failed")

    status = subprocess.run(["git", "status", "--porcelain"], cwd=str(site_root), capture_output=True, text=True)
    if status.returncode != 0:
        raise RuntimeError(status.stderr.strip() or status.stdout.strip() or "git status failed")
    if not status.stdout.strip():
        return False

    msg = f"Polish MLB commentary voice {date_str}"
    commit = subprocess.run(["git", "commit", "-m", msg], cwd=str(site_root), capture_output=True, text=True)
    if commit.returncode != 0:
        raise RuntimeError(commit.stderr.strip() or commit.stdout.strip() or "git commit failed")

    push = subprocess.run(["git", "push", "origin", "main"], cwd=str(site_root), capture_output=True, text=True)
    if push.returncode != 0:
        raise RuntimeError(push.stderr.strip() or push.stdout.strip() or "git push failed")
    return True


def main():
    parser = argparse.ArgumentParser(description="Polish published MLB HTML commentary using ChatGPT voice pass")
    parser.add_argument("--date", default="", help="Target date YYYY-MM-DD (default: today ET)")
    parser.add_argument("--site-root", default="/Users/asmith/.openclaw/workspace/sportzballz.io")
    parser.add_argument("--model", default=os.environ.get("OPENAI_COMMENTARY_MODEL", "gpt-4o-mini"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    date_str = args.date.strip() or est_today()
    site_root = Path(args.site_root)
    files = target_files(site_root, date_str)
    if not files:
        print(f"No target HTML files found for {date_str}")
        return 0

    payload = []
    per_file = {}

    for p in files:
        raw = p.read_text(encoding="utf-8")
        ledes = extract_ledes(raw)
        if not ledes:
            continue
        per_file[p] = {"raw": raw, "ledes": ledes}
        for item in ledes:
            payload.append({
                "id": str(item["index"]),
                "file": p.name,
                "commentary": item["text"],
            })

    if not payload:
        print("No lede commentary blocks found to polish")
        return 0

    # Batch by file for safer id mapping and smaller payloads.
    changed_files = []
    for p, info in per_file.items():
        batch = [
            {"id": str(item["index"]), "commentary": item["text"]}
            for item in info["ledes"]
        ]
        rewrites = call_rewriter(batch, args.model)
        updated_html, changed = apply_rewrites(info["raw"], info["ledes"], rewrites)
        if changed > 0:
            if not args.dry_run:
                p.write_text(updated_html, encoding="utf-8")
            changed_files.append(p)
            print(f"{p.name}: polished {changed} commentary blocks")
        else:
            print(f"{p.name}: no meaningful commentary changes")

    if not changed_files:
        print("No file changes to publish")
        return 0

    if args.dry_run:
        print("Dry run enabled; skipping git publish")
        return 0

    pushed = git_commit_push(site_root, changed_files, date_str)
    if pushed:
        print(f"Published polished commentary for {date_str}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
