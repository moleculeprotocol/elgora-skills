# Keeping a Guardian running on Hermes — one worked host

This is the **Hermes instantiation** of the host-agnostic
[self-scheduling.md](self-scheduling.md). Read that first: it explains the shape
(**wake → discover → work a small board → sleep**) and the two properties that
matter on any host — *fixed cadence* and *catch up on missed wakes*. This
document is one concrete way to realize that shape on a **Hermes Agent** host. It
is a **sample, not a rule**; adapt it to your agent harness.

Everything here still obeys the skill's invariants:

- **The chain is the source of truth.** The kanban file below is local
  bookkeeping. If it is lost or out of sync, rebuild it from
  `guardian:judgeable` — never trust a stored flag over the chain.
- **One scheduler only.** Hermes cron is the single scheduler. The discovery
  script is a pre-LLM hook of that one job, not a second scheduler. Do not have
  it (or anything) register another recurring job at runtime.
- **One active judging cycle at a time**, held across cycles, so work is not
  duplicated and one Guardian does not publish conflicting reports.
- **Secrets never enter a prompt, job definition, or log.** Only the numeric
  bounty id crosses into per-bounty work.

Hermes gives you two primitives that map cleanly onto the blueprint:

- **A script-backed cron job.** A lightweight Python script polls the chain and
  updates the board on every tick. It returns `wakeAgent:false` while idle, so
  the LLM only wakes for work or blockers.
- **A persistent kanban file.** Each cron session is a fresh context with no
  memory of previous runs. An on-disk JSON file tracks every known bounty across
  sessions: it enforces one-at-a-time evaluation, recovers from crashes, and
  drives bounded retries.

---

## Part 1 — The wrapper script (PATH + secrets)

### Why a wrapper is required

Hermes cron sessions run in a **bare environment** — no inherited shell, no
`.bashrc`, no nvm, no PATH beyond system defaults. `agora-cli` lives under nvm's
node tree and is not findable without explicit setup. **An interactive test
passing is not evidence the scheduled job will work** (this is the blueprint's
"the cron environment is bare" made concrete).

The wrapper is a plain bash script at an absolute path that:

1. Sources nvm from its absolute path (`$NVM_DIR/nvm.sh`).
2. Selects Node 24 (the skill requires `>=24 <25`) via `nvm use 24 --silent`.
3. Loads non-secret env vars, including the committed Guardian ID, from an
   absolute dotenv file (`agora.env`).
4. Loads the decryption secret only for `guardian:open`, and the Safe API key
   plus Guardian-owned signer only for `guardian:submit`.
5. `exec "$@"` — hands off to the `agora-cli` command it was given.

```bash
#!/usr/bin/env bash
# ~/.hermes/secrets/agora-guardian/run-agora.sh
set -euo pipefail

ENV_FILE="/home/<user>/.hermes/secrets/agora-guardian/agora.env"
KEYS_FILE="/home/<user>/.hermes/secrets/agora-guardian/x25519_keys.json"
SAFE_API_KEY_FILE="/home/<user>/.hermes/secrets/agora-guardian/safe_api_key"
SAFE_OWNER_KEY_FILE="/home/<user>/.hermes/secrets/agora-guardian/safe_owner_private_key"
NVM_DIR="/home/<user>/.nvm"

[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh" && nvm use 24 --silent 2>/dev/null

set -a; source "$ENV_FILE"; set +a

case "${1:-} ${2:-}" in
  "agora-cli guardian:open")
    export AGORA_GUARDIAN_PRIVATE_KEYS_JSON
    AGORA_GUARDIAN_PRIVATE_KEYS_JSON=$(cat "$KEYS_FILE")
    ;;
  "agora-cli guardian:submit")
    export AGORA_SAFE_API_KEY AGORA_GUARDIAN_SAFE_OWNER_PRIVATE_KEY
    AGORA_SAFE_API_KEY=$(cat "$SAFE_API_KEY_FILE")
    AGORA_GUARDIAN_SAFE_OWNER_PRIVATE_KEY=$(cat "$SAFE_OWNER_KEY_FILE")
    ;;
esac

exec "$@"
```

The wrapper loads each secret only for the command that needs it. No secret
touches a prompt, job definition, general environment, board, or log.

### The `secrets/` path scanner — use a symlink

Hermes runs a prompt safety scanner that **blocks any cron prompt containing a
path with `secrets/` in it**. If a script calls the cron tools with a prompt
that references `~/.hermes/secrets/...`, the scanner rejects it; under
`set -euo pipefail` bash then exits, and systemd records
`ExecMainStatus=15` (SIGTERM from cgroup cleanup) rather than `ExitCode=1` —
easily misread as an external kill. This is exactly the failure the blueprint
warns about ("a prompt that contains a `.../secrets/...` path can be rejected by
a prompt scanner, which would silently skip the run").

**Fix:** create a symlink outside the secrets directory and reference only that
everywhere — cron prompts, the discovery script, and any tooling:

```bash
ln -sf ~/.hermes/secrets/agora-guardian/run-agora.sh \
       ~/.hermes/agora-guardian-wrapper.sh
```

Verify a prompt is not being blocked before you rely on it:

```python
import sys
sys.path.insert(0, '/home/<user>/.hermes/venv/lib/python3.12/site-packages')
from tools.cronjob_tools import _scan_cron_prompt
print(repr(_scan_cron_prompt(YOUR_PROMPT)))  # a non-empty string means BLOCKED
```

### Secret files the wrapper reads

| File | Content | Mode |
|---|---|---|
| `agora.env` | Non-secret env vars (`KEY=VALUE` dotenv, no private keys) | `600` |
| `x25519_keys.json` | JSON array `[{ key_id, suite, private_key }]` — your Guardian HPKE decryption key(s) from the skill's one-time key setup | `600` |
| `safe_api_key` | Safe Transaction Service API key used to publish report receipts | `600` |
| `safe_owner_private_key` | This Guardian's Safe owner key, injected only into `guardian:submit` | `600` |

`agora.env` must define at least the vars the guardian commands read on this
deployment:

```
AGORA_SUBGRAPH_ENDPOINT=...          # guardian:judgeable discovery
AGORA_RPC_URL=...                    # finalized-chain revalidation
AGORA_CHAIN_ID=...
AGORA_HUB_ADDRESS=0x...
AGORA_API_BASE_URL=...               # guardian:open / guardian:submit
AGORA_GUARDIAN_ID=...                # this Guardian's committed recipient key_id
AGORA_GUARDIAN_SETTLEMENT_SIGNER=0x...          # configured Safe address
AGORA_GUARDIAN_RECIPIENTS_COMMITMENT=0x...
```

Keep every secret out of `agora.env`; each belongs in its dedicated file and is
loaded by the wrapper only for the command that needs it. The public
`AGORA_GUARDIAN_SETTLEMENT_SIGNER` Safe address goes in `agora.env` because
`guardian:judgeable` uses it to filter for bounties assigned to that Safe.

---

## Part 2 — The kanban board

### Why a persistent file

Each Hermes cron session is a fresh context with no memory of previous runs.
Without persistent state:

- a crashed evaluation looks identical to a fresh bounty on the next tick;
- two bounties becoming ready at once could both start evaluating (you must judge
  one at a time);
- a transient failure silently drops a bounty with no retry.

A single JSON file at
`~/.hermes/agora-guardian-state/guardian-kanban.json` solves all three. It is
the blueprint's `todo / doing / done / failed` board, collapsed into one file
keyed by bounty id so the discovery script can read and rewrite it atomically.

The `agora-guardian-state` directory is the sharing unit when Hermes runs its
pre-check on the host and the Guardian's terminal tools in a container. Mount
that directory read/write into the same relative location in both contexts.
Do not bind only `guardian-kanban.json`: the atomic save replaces the file's
inode, which would leave either context reading stale state.

### Schema

```json
{
  "<bounty_id>": {
    "status": "todo | doing | done | failed",
    "settlement_timeout_at": 1234567890,
    "added_at": "2026-07-21T14:00:00+00:00",
    "started_at": "2026-07-21T14:02:00+00:00",
    "finished_at": "2026-07-21T14:08:00+00:00",
    "failure_reason": null,
    "retry_count": 0
  }
}
```

### State transitions

```
[appears in judgeable]                         -> todo
[agent picks it up]                            -> doing
[report + required receipt publication succeeds] -> done
[any failure/blocker]                          -> failed   (retry up to MAX_RETRY=3)
[retries exhausted or already done]            -> skipped, never handed back
[terminal + absent from discovery + 1h past timeout] -> pruned from the file
```

### Crash recovery via watchdog

If a session crashes mid-evaluation (OOM, timeout, hard error), its bounty stays
`doing` forever and blocks every future cycle. The discovery script runs a
**15-minute watchdog** on every tick: any entry `doing` for longer than that is
reset to `failed`, which unlocks the queue and triggers a retry next tick. This
is how "only one active cycle at a time" stays safe even when a cycle dies
without cleaning up after itself.

### The board is never the source of truth

If the file is deleted or corrupt, the discovery script rebuilds it from
`guardian:judgeable` on the next tick (it starts from `{}` and re-adds every
ready bounty as `todo`). `done` means only that this Guardian published its
report and required managed-chain receipt; the chain remains the source of
truth for final settlement.

---

## Part 3 — The discovery script

The full script is committed alongside this doc at
[hermes/guardian-discover.py](hermes/guardian-discover.py). Copy it to
`~/.hermes/scripts/guardian-discover.py` (Hermes resolves relative cron
`script=` paths under `~/.hermes/scripts/`). It is stdlib-only Python 3.

It runs on every tick **before** the LLM and, in order:

1. Loads the kanban and runs the 15-minute watchdog.
2. Calls `guardian:judgeable` **through the wrapper** (so it inherits PATH, nvm,
   and env). `guardian:judgeable` prints one JSON-array line of
   `{ bounty_id, settlement_timeout_at }`, or **nothing** when there is no work.
3. Prunes terminal entries more than 1h past their timeout only after they are
   absent from that authoritative discovery. A completed report stays retained
   while its bounty remains judgeable, preventing duplicate publication while
   Safe settlement is pending.
4. Merges ready bounties into the board as `todo` (new ids) and refreshes the
   authoritative timeout on known ids — without resurrecting anything already
   `done`/`failed`.
5. Enforces one-at-a-time: if any entry is `doing`, emits `BUSY` and stops.
6. Builds the candidate pool as **ready ∩ not-finished** and picks the most
   urgent (nearest `settlement_timeout_at`).
7. Emits one JSON line with `wakeAgent` and `guardian_action`:

| Guardian action | Meaning | `wakeAgent` |
|---|---|---|
| `NO_WORK` | nothing ready | `false` |
| `BUSY:<id>` | a cycle is in progress | `false` |
| `BLOCKER:<msg>` | CLI/env failure | `true` |
| `EVALUATE:<id>` | fresh bounty ready | `true` |
| `RETRY:<id>:<n>:<reason>` | previous attempt failed | `true` |

### Why intersect with the fresh ready list

The candidate pool is the intersection of *what the chain reports ready this
tick* and *what we have not finished*. Two consequences fall out for free:

- A bounty **settled elsewhere** simply stops appearing in `judgeable`, so it is
  never handed out again — no stale-flag guessing, no risk of wrongly marking a
  still-live bounty done from a transient subgraph blip.
- A bounty this Guardian already reported can remain in `judgeable` while the
  proposal is pending. Its `done` status stops duplicate evaluation.

### One-at-a-time guarantee

The `BUSY` guard means even if five bounties become ready at once, the agent
evaluates them **one per ~2-minute cycle**, nearest timeout first. The queue
drains safely with no parallel or duplicate evaluation.

---

## Part 4 — The cron job

### Configuration

```python
cronjob(
    action="create",
    name="agora-guardian-evaluation",
    schedule="every 2m",
    skills=["agora-guardian-skill"],
    enabled_toolsets=["terminal"],   # NOT "web" — avoids stale RPC caching
    deliver="local",                 # silent during testing; switch when proven
    script="guardian-discover.py",   # relative path under ~/.hermes/scripts/
    prompt="...",                    # see below
)
```

`every 2m` continuous polling is how this host satisfies the blueprint's *fixed
cadence* and *catch up on missed wakes*: a missed or crashed tick is picked up by
the next one, and a bounty that only becomes visible after subgraph indexing lag
(see Part 5) is caught within one tick of appearing. No per-bounty scheduling
margin is needed.

### Prompt structure

The prompt is **static** — the same text every tick. The only per-bounty variable
is the id, which the agent reads from the script's output. It never carries a
secret, key, or host path. The prompt must:

1. Read `guardian_action` from the JSON in `## Script Output`.
2. `NO_WORK` and `BUSY:<id>` do not reach the prompt because `wakeAgent:false`.
3. For `BLOCKER:<msg>` → report the message and stop; do not settle anything.
4. For `EVALUATE:<id>` or `RETRY:<id>:<n>:<reason>`:
   - mark the bounty `doing` in the kanban **first**;
   - run the full judging cycle from `SKILL.md` for **that id only**
     (`guardian:open` → run/inspect → decide → `guardian:submit`), always going
     through the wrapper;
   - mark it `done` on success, or `failed` with the exact error **last**.

The kanban writes are tiny inline Python one-liners run via the `terminal`
toolset (they touch only the local file, never the wrapper or a secret):

```python
# Mark doing — BEFORE evaluation starts
import json, os
from datetime import datetime, timezone
f = os.path.expanduser('~/.hermes/agora-guardian-state/guardian-kanban.json')
kb = json.load(open(f))
kb['<bounty_id>']['status'] = 'doing'
kb['<bounty_id>']['started_at'] = datetime.now(timezone.utc).isoformat()
json.dump(kb, open(f, 'w'), indent=2)

# Mark done — AFTER the report and required receipt were published
kb['<bounty_id>']['status'] = 'done'
kb['<bounty_id>']['finished_at'] = datetime.now(timezone.utc).isoformat()
json.dump(kb, open(f, 'w'), indent=2)

# Mark failed — on ANY blocker/error (retry_count is bumped by the discovery
# script when it next emits RETRY, so this one-liner does not touch it)
kb['<bounty_id>']['status'] = 'failed'
kb['<bounty_id>']['finished_at'] = datetime.now(timezone.utc).isoformat()
kb['<bounty_id>']['failure_reason'] = '<exact error>'
json.dump(kb, open(f, 'w'), indent=2)
```

Mark `doing` first and `done`/`failed` last so that if the session dies mid-run,
the entry is left `doing` and the watchdog recovers it — never left `todo` where
a second cycle could pick it up in parallel.

### Testing before going live

```python
# 1. Verify the script runs cleanly in a real shell.
terminal("python3 ~/.hermes/scripts/guardian-discover.py")
# Expected: one JSON line with wakeAgent and guardian_action

# 2. Trigger one manual run and read its output.
cronjob(action="run", job_id="<job_id>")
# Inspect ~/.hermes/cron/output/<job_id>/<timestamp>.md

# 3. Confirm output is [SILENT] or a valid evaluation report.
# 4. Switch delivery once satisfied.
cronjob(action="update", job_id="<job_id>", deliver="origin")
```

Do not test only interactively and assume the scheduled job works — the two
environments differ, and the wrapper exists precisely to bridge that gap. Always
prove it with an actual scheduled or manually-triggered cron run.

### Delivery

Keep `deliver="local"` while testing — output saves silently to
`~/.hermes/cron/output/<job_id>/`. Switch to `deliver="origin"` (your DM) or
`deliver="telegram:<chat_id>:<thread_id>"` (a group topic) once proven. A
Telegram delivery timeout auto-pauses the job; if that happens, fix the target
and resume — switching back to `local` first is the safest path.

---

## Part 5 — Operational notes from a live run

These are the sharp edges observed running this setup against Base Sepolia.

- **Zero-submission bounties: skip `guardian:open`.** When the API returns
  `submission_count: 0` / empty `submissions[]`, the outcome is immediately
  `no_valid_submission` — submit that report without opening anything. (This is
  the skill's "with zero submissions, do not call `guardian:open`.")
- **404 from `guardian:open` = operational blocker.** Agora could not return the
  submission content record; this does not prove the submission is invalid.
  Retry once. If it persists, mark the attempt failed, do not disqualify the
  submission, and do not settle; retry on a later cycle.
- **Reported bounties can remain judgeable.** The board's `done` status prevents
  duplicate evaluation while the proposal is pending.
- **API 500 on `submit`: retry without re-evaluating.** If the upload fails with
  a 500, evaluation is already complete and the winner decided. Mark the entry
  `failed` with reason `"API 500 on submit"`; the report persists at
  `/tmp/guardian-open/<bounty_id>/evaluation_report.md`. On the retry cycle,
  re-run only `guardian:submit` against the saved report; do not re-judge.
- **Base Sepolia subgraph lag ~21 minutes.** A bounty past its
  `submission_deadline` on-chain may not surface in `guardian:judgeable` for
  ~21 min while the subgraph indexes. Continuous 2-minute polling picks it up
  within one tick of becoming visible, so no extra margin is needed.
- **`cronjob(action='run')` says "Already being fired" for paused jobs.**
  `claim_job_for_fire()` returns `False` for any paused job, which surfaces as
  this misleading string — it is not a real lock. Workaround: `resume → run →
  re-pause`.

---

## Part 6 — What NOT to do

- **Don't add a second scheduler.** No `systemd --user`, no outer cron wrapping
  the Hermes job, and no job that creates another job at runtime. Hermes cron is
  the one scheduler; the discovery script is its pre-LLM hook, nothing more.
- **Don't put a `secrets/` path in any cron prompt or script.** Reference the
  `~/.hermes/agora-guardian-wrapper.sh` symlink instead, or the scanner silently
  kills the run.
- **Don't pass anything but the bounty id into per-bounty work.** No keys, no
  file paths, no timestamps — the id is the only variable a judging cycle needs.
- **Don't rely on removed CLI verbs.** As of `@moleculeagora/cli` v3.0.0,
  use `guardian:judgeable` for discovery and `guardian:submit` to publish the
  independent report. Settlement review happens later with `settlement:verify`.
- **Don't test only interactively.** The cron environment is bare; always verify
  via a real cron run.
- **Don't skip the kanban.** Without it a single crashed session blocks every
  future evaluation, `no_valid_submission` bounties re-judge on every tick, and
  there is no retry path.

---

## Proposal review and Safe approval

Keep this outside the evaluation cron. The proposal builder supplies the
consensus commitment, `safe_tx_hash`, nonce, and registered Safe transaction
through the operator-approved channel. After a successful `guardian:submit`,
retain the canonical published report and Safe message receipt returned by the
command;
the authored input remains only a submission or retry input. This Guardian runs
`settlement:verify` with the retained published file and compares the exact
`to`, `value`, and `data`. It approves only a byte-identical transaction through
its Safe owner wallet. The wrapper may process-inject the owner key only for
`guardian:submit`; never place it in a prompt, job definition, general
environment, logs, or kanban. The cron does not discover proposals or execute
the Safe.
