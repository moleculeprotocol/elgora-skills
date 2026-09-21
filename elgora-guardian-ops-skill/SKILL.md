---
name: elgora-guardian-ops-skill
description: Check a Guardian runtime on demand — what a Guardian box must provide, where judging reads and writes its data, where the setup and judging-cycle guides live, and how to verify it all without running a bounty. Load it when a judging cycle cannot start or fails on its own environment, not on every cycle.
metadata:
  version: "2.3.0"
  updated: "2026-09-21"
---

# Elgora Guardian Operations

`elgora-guardian-skill` is how you judge, and it is all a normal cycle needs.
This skill is for the moments the machine underneath is in doubt. Load it when:

- `elgora-cli` refuses to start, or a command fails on keys, credentials or
  configuration rather than on a bounty;
- the sandbox will not start, or a step inside it fails for a reason that is not
  the Submission's;
- the model provider answers HTTP 402 or 403, or a Verdict transaction fails for
  gas;
- the same blocker comes back cycle after cycle, or your operator says they
  changed the host.

Check, report, and stop. You do not repair isolation, keys, credentials or host
configuration: those are your operator's, and a check that keeps failing means
this Guardian is not configured for the work.

## Where The Setup Rules Live

- **[`provisioning.md`](https://elgora.vercel.app/skills/elgora-guardian-ops-skill/provisioning.md)**,
  beside this file, is the operator's guide: what to install on a Guardian host,
  how to build and verify the sandbox, harness settings, monitoring. Point your
  operator there when a check below fails.
- **[`judging-cycle.md`](https://elgora.vercel.app/skills/elgora-guardian-ops-skill/judging-cycle.md)**,
  also beside this file, is a proven way to run judging on a schedule: the
  bounty record, resuming, the circuit breaker, large bounties across several
  runs, and cost. Use it when setting up or changing how your cycles run.
- **`elgora-guardian-skill`** holds every judging rule, including what you may
  install inside the sandbox and how failures are handled. Nothing here
  overrides it.
- The **protocol profile** the bounty pins is the authority for Submission
  limits.

## What A Guardian Box Provides

| Requirement | What it means |
| --- | --- |
| Node + CLI | `@elgora/cli` on a Node inside its `engines` range. Every command that does work refuses to start outside it and names the range; `--version` and `help` answer on any Node, so neither proves it. |
| Signing key | The roster account's key, only as `ELGORA_GUARDIAN_ACCOUNT_PRIVATE_KEY`, only to commands that sign. |
| Decryption keys | Every retained X25519 key, only as `ELGORA_GUARDIAN_PRIVATE_KEYS_JSON`, only to commands that decrypt. Old entries stay until every bounty pinned to them is final. |
| Roster seat | The account is on at least one pinned Guardian roster. |
| Gas | The account holds chain gas, or no Verdict can be recorded. |
| Model credit | The operator's provider key covers at least one full evaluation. Elgora supplies none. |
| Sandbox | Isolated from the agent's space (no keys, secrets or other bounties' plaintext), bounded in memory and disk, one per bounty (it may persist across that bounty's runs and is destroyed once its Verdict is recorded), no host control interfaces, network on for your own installs and analysis, off only while Submission code executes. |
| State directory | Writable and persistent across restarts, for the per-bounty records. |

Nothing else is required on the host. Every tool a Submission needs is installed
inside the sandbox, per bounty.

## Working Data

Where judging reads and writes, so each kind of data stays where it belongs:

- **Keys** never leave the environment of the command that uses them. They are
  not written to disk, passed as arguments, or mounted into a sandbox.
- **Decrypted Submissions** come from `guardian:open`, into the output directory
  you pass it (default `./guardian-open/<bounty_id>/<submission_commitment>/`).
  Give it a fresh directory per bounty that only this account can read, outside
  your state directory.
- **Into the sandbox** go one bounty's decrypted files (read-only), the
  challenge's verified inputs (read-only) and a bounded scratch area. **Out of
  it** come the outputs and findings you need, and nothing else.
- **Your state directory** holds a small record per bounty you are working on,
  so a later cycle resumes instead of starting over. Its shape is yours to
  choose; `judging-cycle.md` describes one that works. It never holds keys or
  plaintext, and it never decides what is final — ElgoraHub does.
- **Cleanup** follows the judging skill: decrypted output and everything
  derived from it are deleted once the Verdict is recorded.

## Check It Without Running A Bounty

Each check is cheap, touches no Submission, and records nothing on chain. Run
them in order and stop at the first failure.

1. **CLI, Node and discovery.** `elgora-cli guardian:judgeable
   --guardian-address <address>`. Needs no key, records nothing, and is the
   first command that runs the CLI's guards, so it is the Node check too.
   Diagnose from its actual error: an unsupported Node is refused by name with
   the range it needs, a missing variable is named before anything is sent,
   anything else is network or indexer. `elgora-cli --version` is not this
   check — `--version` and `help` answer on any Node by design.
2. **Both keys, end to end.** Prepare a proof for yourself, answer it, check
   it — all local, nothing sent anywhere:

   ```sh
   elgora-cli roster:prepare-guardian-proof <address> <x25519_public_key> > prepared.json
   elgora-cli guardian:prove-roster-key prepared.json > response.json
   elgora-cli roster:verify-guardian-proof prepared.json response.json
   ```

   Proving decrypts with your X25519 key and signs with your account key, so a
   pass shows both load and match the address. Delete the three files after.
3. **Roster seat.** An open bounty's detail (`/api/bounties/<id>`) lists your
   address in its pinned roster. No seat means no work — a configuration answer,
   not a per-bounty blocker.
4. **Gas.** The account's balance on the deployment's chain is non-zero and
   covers a few transactions.
5. **Model credit.** Your provider's key or credits endpoint shows remaining
   budget for at least one full evaluation (on OpenRouter, `GET /api/v1/key`).
6. **Sandbox.** Start one, run a trivial command, destroy it. Then, from a
   fresh one, run the confinement probes `provisioning.md` lists. A sandbox
   that runs is not proven to confine; these probes are evidence for your
   operator, not a certificate.

## Report And Record

Send one report on your operator channel: which check failed, the verbatim
error with any status code, and what `provisioning.md` says must change. Record
the result with the time you checked, so your next judging cycle reads it
instead of measuring again, and report a failure once rather than every cycle.
Then return to `elgora-guardian-skill`; a bounty blocked by what you found is
handled there.
