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


def resolve_openai_key():
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
    return api_key


def rewrite_single_lede(client, model_name, lede_text: str):
    system_prompt = (
        "You are a grizzled MLB betting analyst and veteran beat writer. Rewrite commentary so it pops: sharper voice, tighter rhythm, "
        "clear edge, no fluff, still factual. Keep it to one paragraph and preserve factual meaning. "
        "Do not invent facts, numbers, players, injuries, weather, line movement, or outcomes. "
        "Avoid robotic phrasing like 'prediction model', 'confidence rating', or 'data points'."
    )

    few_shot_user = (
        "Rewrite this in your style:\n"
        "The Orioles are favored at -148 with a confidence rating of 0.545 based on 17 of 22 data points. "
        "The White Sox have offensive issues and lineup instability."
    )
    few_shot_assistant = (
        "Baltimore at -148 isn\'t a bargain-bin ticket, but the market move says the right side has teeth. "
        "The Orioles bring the cleaner profile tonight—steadier bats, fewer empty trips, and less lineup chaos—"
        "while Chicago\'s still searching for consistent run production."
    )

    user_prompt = (
        "In the voice of a grizzled MLB analyst, make this commentary better and make it pop. "
        "Keep all facts intact. One paragraph only.\n\n"
        f"Original commentary:\n{lede_text}"
    )

    resp = client.chat.completions.create(
        model=model_name,
        temperature=0.45,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": few_shot_user},
            {"role": "assistant", "content": few_shot_assistant},
            {"role": "user", "content": user_prompt},
        ],
    )

    return (resp.choices[0].message.content or "").strip()


def judge_rewrite(client, judge_model, original: str, rewritten: str):
    judge_prompt = (
        "You are grading rewrite quality for sportsbook editorial. Return STRICT JSON object with fields: "
        "fidelity (true/false), pop_score (1-10 int), reasons (array of short strings).\n\n"
        f"Original:\n{original}\n\nRewrite:\n{rewritten}"
    )

    resp = client.chat.completions.create(
        model=judge_model,
        temperature=0,
        messages=[
            {"role": "system", "content": "Be strict. Prefer factual fidelity over style."},
            {"role": "user", "content": judge_prompt},
        ],
    )

    raw = (resp.choices[0].message.content or "").strip()
    try:
        obj = json.loads(raw)
    except Exception:
        l = raw.find("{")
        r = raw.rfind("}")
        if l >= 0 and r > l:
            obj = json.loads(raw[l : r + 1])
        else:
            return {"fidelity": False, "pop_score": 0, "reasons": ["judge_parse_failed"]}

    fidelity = bool(obj.get("fidelity"))
    pop = int(obj.get("pop_score") or 0)
    reasons = obj.get("reasons") if isinstance(obj.get("reasons"), list) else []
    return {"fidelity": fidelity, "pop_score": pop, "reasons": reasons}


def call_rewriter_single(client, model_name, judge_model, item):
    original = item["text"]
    rewritten = rewrite_single_lede(client, model_name, original)

    # Basic guardrails before LLM judge.
    if not rewritten or len(rewritten.split()) < 35:
        return None, "too_short_or_empty"

    if re.search(r"\b(confidence rating|data points|in this matchup|today\'s matchup)\b", rewritten, re.I):
        # common bland/templated phrases; send to judge anyway but likely reject
        pass

    grade = judge_rewrite(client, judge_model, original, rewritten)
    if not grade["fidelity"]:
        return None, f"fidelity_fail:{','.join(grade['reasons'][:2])}"
    if grade["pop_score"] < 6:
        return None, f"pop_too_low:{grade['pop_score']}"

    return rewritten, f"accepted:pop_{grade['pop_score']}"


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
    parser.add_argument("--model", default=os.environ.get("OPENAI_COMMENTARY_MODEL", "gpt-4o"))
    parser.add_argument("--judge-model", default=os.environ.get("OPENAI_COMMENTARY_JUDGE_MODEL", "gpt-4o-mini"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    date_str = args.date.strip() or est_today()
    site_root = Path(args.site_root)
    files = target_files(site_root, date_str)
    if not files:
        print(f"No target HTML files found for {date_str}")
        return 0

    per_file = {}

    for p in files:
        raw = p.read_text(encoding="utf-8")
        ledes = extract_ledes(raw)
        if not ledes:
            continue
        per_file[p] = {"raw": raw, "ledes": ledes}

    if not per_file:
        print("No lede commentary blocks found to polish")
        return 0

    client = OpenAI(api_key=resolve_openai_key())

    changed_files = []
    for p, info in per_file.items():
        rewrites = {}
        accepted = 0
        rejected = 0
        for item in info["ledes"]:
            out, status = call_rewriter_single(client, args.model, args.judge_model, item)
            if out:
                rewrites[str(item["index"])] = out
                accepted += 1
            else:
                rejected += 1

        updated_html, changed = apply_rewrites(info["raw"], info["ledes"], rewrites)
        if changed > 0:
            if not args.dry_run:
                p.write_text(updated_html, encoding="utf-8")
            changed_files.append(p)
            print(f"{p.name}: polished {changed} commentary blocks (accepted={accepted}, rejected={rejected})")
        else:
            print(f"{p.name}: no meaningful commentary changes (accepted={accepted}, rejected={rejected})")

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
