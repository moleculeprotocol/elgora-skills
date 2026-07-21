#!/usr/bin/env python3
"""Guardian discovery + kanban tick for a Hermes-hosted Agora Guardian.

Runs once per cron tick, BEFORE the LLM, with no tokens spent. It polls the
chain via `agora-cli guardian:judgeable` (through the secrets wrapper), keeps a
persistent kanban file so a fresh cron context can pick up where the last one
left off, and prints exactly one line telling the agent what to do:

    NO_WORK                     nothing ready          -> agent replies [SILENT]
    BUSY:<id>                   evaluation in progress  -> agent replies [SILENT]
    BLOCKER:<msg>               CLI / env failure       -> agent reports it
    EVALUATE:<id>               fresh bounty ready       -> agent judges it
    RETRY:<id>:<n>:<reason>     previous attempt failed  -> agent retries it

The kanban is local bookkeeping, never the source of truth. The chain is. If the
file is lost or corrupt it is rebuilt from `guardian:judgeable` on the next tick.

Copy to ~/.hermes/scripts/guardian-discover.py on the Hermes host. Stdlib only.
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

HOME = os.path.expanduser("~")

# Reference the SYMLINK, never the real path under secrets/. A prompt or script
# containing a ".../secrets/..." path is rejected by the Hermes prompt scanner.
WRAPPER = os.path.join(HOME, ".hermes", "agora-guardian-wrapper.sh")
KANBAN = os.path.join(HOME, ".hermes", "guardian-kanban.json")

MAX_RETRY = 3            # attempts after the first failure before we give up
WATCHDOG_SECS = 15 * 60  # a bounty stuck in "doing" longer than this is unstuck
PRUNE_AFTER_SECS = 60 * 60   # drop terminal entries this long past their timeout
JUDGEABLE_TIMEOUT = 90       # seconds to wait on the CLI call


class Blocker(Exception):
    """A CLI/env failure that should surface to the operator, not be swallowed."""


def now_ts() -> int:
    return int(time.time())


def iso(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def iso_to_ts(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(datetime.fromisoformat(value).timestamp())
    except ValueError:
        return None


def load_kanban() -> dict:
    try:
        with open(KANBAN, encoding="utf-8") as fh:
            data = json.load(fh)
            return data if isinstance(data, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError):
        # A missing or corrupt board is not fatal: rebuild from the chain.
        return {}


def save_kanban(kb: dict) -> None:
    os.makedirs(os.path.dirname(KANBAN), exist_ok=True)
    tmp = f"{KANBAN}.tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(kb, fh, indent=2, sort_keys=True)
    os.replace(tmp, KANBAN)  # atomic; a crash mid-write never truncates the board


def discover() -> dict[str, int]:
    """Return {bounty_id: settlement_timeout_at} for every ready bounty.

    `guardian:judgeable` prints a single JSON-array line, or nothing at all when
    there is no work. Anything else (non-zero exit, unparseable output) is a
    blocker the operator needs to see.
    """
    try:
        proc = subprocess.run(
            [WRAPPER, "agora-cli", "guardian:judgeable"],
            capture_output=True,
            text=True,
            timeout=JUDGEABLE_TIMEOUT,
        )
    except FileNotFoundError:
        raise Blocker(f"wrapper not found or not executable: {WRAPPER}")
    except subprocess.TimeoutExpired:
        raise Blocker(f"guardian:judgeable timed out after {JUDGEABLE_TIMEOUT}s")

    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-1:] or [""]
        raise Blocker(f"guardian:judgeable exit {proc.returncode}: {tail[0]}")

    out = proc.stdout.strip()
    if not out:
        return {}  # empty stdout means no ready bounties

    try:
        rows = json.loads(out)
    except json.JSONDecodeError:
        raise Blocker(f"guardian:judgeable emitted non-JSON: {out[:120]}")

    ready: dict[str, int] = {}
    for row in rows:
        ready[str(row["bounty_id"])] = int(row["settlement_timeout_at"])
    return ready


def new_entry(timeout_at: int, t: int) -> dict:
    return {
        "status": "todo",
        "settlement_timeout_at": timeout_at,
        "added_at": iso(t),
        "started_at": None,
        "finished_at": None,
        "failure_reason": None,
        "retry_count": 0,
    }


def main() -> None:
    kb = load_kanban()
    t = now_ts()

    # 1. Watchdog: a session that crashed mid-evaluation leaves a bounty pinned
    #    in "doing" forever, blocking the whole queue. Unstick it so it retries.
    for entry in kb.values():
        started = iso_to_ts(entry.get("started_at"))
        if entry["status"] == "doing" and started and t - started > WATCHDOG_SECS:
            entry["status"] = "failed"
            entry["failure_reason"] = "watchdog: stuck in doing >15m"
            entry["finished_at"] = iso(t)

    # 2. Prune terminal entries well past their settlement window.
    for bid in list(kb):
        e = kb[bid]
        timeout_at = e.get("settlement_timeout_at")
        if e["status"] in ("done", "failed") and timeout_at and t > timeout_at + PRUNE_AFTER_SECS:
            del kb[bid]

    # 3. Discover from the chain. A blocker is reported, not hidden.
    try:
        ready = discover()
    except Blocker as exc:
        save_kanban(kb)
        print(f"BLOCKER:{exc}")
        return

    # 4. Merge ready bounties in. New ids become todo; known ids keep the
    #    authoritative timeout. We never resurrect a done/failed entry here — a
    #    bounty we already settled can linger in judgeable until its timeout
    #    (e.g. no_valid_submission), and the kanban is what stops us re-judging.
    for bid, timeout_at in ready.items():
        if bid not in kb:
            kb[bid] = new_entry(timeout_at, t)
        else:
            kb[bid]["settlement_timeout_at"] = timeout_at

    # 5. One active judging cycle at a time, across cron cycles. If anything is
    #    "doing", a previous session is still working — stay out of its way.
    for bid, e in kb.items():
        if e["status"] == "doing":
            save_kanban(kb)
            print(f"BUSY:{bid}")
            return

    # 6. Candidate pool = bounties the chain reports ready AND that we have not
    #    finished. Intersecting with `ready` means a bounty settled elsewhere is
    #    simply never handed out, no stale-flag guessing required.
    candidates = []  # (bounty_id, timeout_at, verb, retry_count)
    for bid, timeout_at in ready.items():
        e = kb[bid]
        if e["status"] == "todo":
            candidates.append((bid, timeout_at, "EVALUATE", e["retry_count"]))
        elif e["status"] == "failed" and e["retry_count"] < MAX_RETRY:
            candidates.append((bid, timeout_at, "RETRY", e["retry_count"]))
        # done, doing, or retry-exhausted failed -> skip

    if not candidates:
        save_kanban(kb)
        print("NO_WORK")
        return

    # 7. Most urgent first: nearest settlement_timeout_at wins.
    candidates.sort(key=lambda c: c[1])
    bid, _timeout_at, verb, retry_count = candidates[0]

    if verb == "RETRY":
        # Count this attempt now so a crash before the agent marks failed still
        # consumes a retry (bounded crash-loop) rather than spinning forever.
        kb[bid]["retry_count"] = retry_count + 1
        save_kanban(kb)
        reason = kb[bid].get("failure_reason") or ""
        print(f"RETRY:{bid}:{retry_count + 1}:{reason}")
    else:
        save_kanban(kb)
        print(f"EVALUATE:{bid}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # never let the tick die silently
        print(f"BLOCKER:discover script crashed: {exc}", file=sys.stdout)
