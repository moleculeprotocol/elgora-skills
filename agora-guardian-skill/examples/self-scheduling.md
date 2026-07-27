# Keeping a Guardian running — one worked example

This is a **sample**, not a rule. The Agora protocol and the Guardian skill do
not care how you wake up or where you keep your notes — only that ready bounties
get judged before their settlement timeout. Below is one concrete way to arrange
that. Adapt it, or throw it away and do something that fits your host better.

The shape is always the same: **a recurring wake → discover → work a small
board → sleep.** Two properties matter regardless of the tool you use to wake:

- **Fixed cadence.** Wake on a fixed schedule (e.g. a few times a day), not a
  drifting "every N hours from last run."
- **Catch up on missed wakes.** If your host was down when a wake was due, run it
  on recovery. A missed wake must never mean a missed bounty. This also covers a
  wake that lands too early relative to finalized chain time (e.g. one timed to
  a bounty's `submissionDeadline`): an empty result from that cycle is not an
  error, just something the next scheduled run picks up.

`guardian:judgeable` fetches candidate bounties from a subgraph, then before
reporting anything it revalidates each candidate against fresh finalized
AgoraHub state. So a missed or crashed cycle is still self-healing in practice:
the next wake re-runs discovery and picks up the same ready bounties.
<!-- A proposal to move the chain read from every discovery poll to once, right
     before judging starts on a chosen bounty, is tracked in
     https://github.com/moleculeprotocol/agora-v0/issues/123 -->

## A local board (kanban)

Keep your working state in something you can inspect and rebuild — a directory of
one small file per bounty is plenty:

```
guardian-board/
  todo/    <bounty_id>.json     # ready, not started
  doing/   <bounty_id>.json     # being judged right now (keep this to one)
  done/    <bounty_id>.json     # this Guardian's report was published
  failed/  <bounty_id>.json     # last attempt failed; note why + when to retry
```

A file might hold `{ "bounty_id": "42", "settlement_timeout_at": "1750000000",
"attempts": 1, "last_error": "sandbox timeout", "next_attempt_after": "..." }`.

This board is a **convenience, never the source of truth.** If it is deleted or
gets out of sync, run `guardian:judgeable` and rebuild `todo/` from what it
reports ready. Never trust a stored flag over the chain — a bounty is
"done" here only when this Guardian's report is published. The chain remains the
source of truth for whether the bounty is settled.

Work the board one bounty at a time, nearest `settlement_timeout_at` first.

**Only one active judging cycle at a time.** A fixed-cadence wake can still
overlap a long-running evaluation from the previous cycle — if that happens,
two cycles can duplicate work or publish conflicting reports. Guard against
this with whatever your host offers (a single-flight lock file, a `flock`, your
scheduler's own "skip if already running" / max-concurrency-1 policy) — the
mechanism stays host-owned, but the one-at-a-time guarantee must hold across
cycles, not just within one.

## One cycle, in pseudo-code

```
ready = run("agora-cli guardian:judgeable")   # empty stdout means no work → stop
for each r in ready: ensure todo/<r.bounty_id>.json exists (with its timeout)

reconcile against this fresh ready list before picking:
  any doing/ file left over from a crashed cycle → move back to todo/
  any failed/ file whose next_attempt_after has passed → move back to todo/

pick the todo/ bounty with the smallest settlement_timeout_at
move it to doing/

judge it (follow SKILL.md): open submissions → run/inspect → decide
run("agora-cli guardian:submit <id> <outcome> [winner] <report.md>")   # off-chain

if the report was published: move to done/
else: move to failed/ with the reason and a backoff; a later cycle retries
```

Do not immediately re-scan after publishing; let the next scheduled cycle pick
up whatever is still ready.

## Waking up: pick whatever your host offers

The scheduler is the runner's choice. Some options, all expressing the same
"fixed cadence + catch up on missed wakes" idea:

- **systemd** (`.timer` with `OnCalendar=` + `Persistent=true`) running a oneshot
  service that executes one cycle.
- **A cloud cron** (Vercel Cron, GitHub Actions schedule, a managed cron box).
- **A Kubernetes `CronJob`.**
- **Your agent host's own scheduler / heartbeat.** For example, a Hermes agent
  can register a recurring job that runs one cycle. If you do this, put the
  *cycle logic* behind a stable command on your `PATH` and pass only the bounty
  id into any sub-prompt — never a secret path, key, or host path. (A prompt that
  contains a `.../secrets/...` path can be rejected by a prompt scanner, which
  would silently skip the run.) A fully worked version of this — script-backed
  cron, on-disk kanban, secrets wrapper, and the prompt — is in
  [self-scheduling-hermes.md](self-scheduling-hermes.md).

Whatever you choose, keep it to **one** scheduler. Do not have a scheduled job
create another scheduled job at runtime — that second scheduler is exactly the
fragile layer this design removes.

## Proposal review is a separate phase

The scheduler stops after `guardian:submit`. When the proposal builder later
supplies the two-report consensus commitment and proposed Safe transaction, run
`settlement:verify` with this Guardian's own report. Approve only byte-identical
`to`, `value`, and `data` through this Guardian's Safe owner wallet. Do not add
proposal polling, Safe execution, or the Safe owner key to this scheduler.
