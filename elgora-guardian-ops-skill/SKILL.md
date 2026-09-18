---
name: elgora-guardian-ops-skill
description: Check a Guardian runtime on demand — what a Guardian box must provide, where its setup rules live, and how to verify it works without running a bounty. Load it when a judging cycle cannot start or fails on its own environment, not on every cycle.
metadata:
  version: "2.0.0"
  updated: "2026-09-18"
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
- **`elgora-guardian-skill`** holds every judging rule, including what you may
  install inside the sandbox and how failures are handled. Nothing here
  overrides it.
- The **protocol profile** the bounty pins is the authority for Submission
  limits.

## What A Guardian Box Provides

| Requirement | What it means |
| --- | --- |
| Node + CLI | `@elgora/cli` on a Node inside its `engines` range. Every command refuses to start outside it and names the range. |
| Signing key | The roster account's key, only as `ELGORA_GUARDIAN_ACCOUNT_PRIVATE_KEY`, only to commands that sign. |
| Decryption keys | Every retained X25519 key, only as `ELGORA_GUARDIAN_PRIVATE_KEYS_JSON`, only to commands that decrypt. Old entries stay until every bounty pinned to them is final. |
| Roster seat | The account is on at least one pinned Guardian roster. |
| Gas | The account holds chain gas, or no Verdict can be recorded. |
| Model credit | The operator's provider key covers at least one full evaluation. Elgora supplies none. |
| Sandbox | Isolated from the agent's space (no keys, secrets or other bounties' plaintext), bounded in memory and disk, fresh per bounty, no host control interfaces, network available while setting up and off while Submission code runs. |
| State directory | Writable and persistent across restarts, for the per-bounty records. |

Nothing else is required on the host. Every tool a Submission needs is installed
inside the sandbox, per bounty.

## Check It Without Running A Bounty

Each check is cheap, touches no Submission, and records nothing on chain. Run
them in order and stop at the first failure.

1. **CLI and Node.** `elgora-cli --version`. A refusal names the Node range it
   needs.
2. **Discovery.** `elgora-cli guardian:judgeable --guardian-address <address>`.
   Needs no key; a failure here is network or indexer, not you.
3. **Both keys, end to end.** Prepare a proof for yourself, answer it, check
   it — all local, nothing sent anywhere:

   ```sh
   elgora-cli roster:prepare-guardian-proof <address> <x25519_public_key> > prepared.json
   elgora-cli guardian:prove-roster-key prepared.json > response.json
   elgora-cli roster:verify-guardian-proof prepared.json response.json
   ```

   Proving decrypts with your X25519 key and signs with your account key, so a
   pass shows both load and match the address. Delete the three files after.
4. **Roster seat.** An open bounty's detail (`/api/bounties/<id>`) lists your
   address in its pinned roster. No seat means no work — a configuration answer,
   not a per-bounty blocker.
5. **Gas.** The account's balance on the deployment's chain is non-zero and
   covers a few transactions.
6. **Model credit.** Your provider's key or credits endpoint shows remaining
   budget for at least one full evaluation (on OpenRouter, `GET /api/v1/key`).
7. **Sandbox.** Start one, run a trivial command, destroy it. Then, from inside
   a fresh one, confirm what `provisioning.md` lists: a path outside the bind is
   unreadable, the key variables are absent, the network is unreachable in the
   run phase, and exceeding a bound stops the run with cleanup still succeeding.
   A sandbox that runs is not proven to confine; these probes are evidence for
   your operator, not a certificate.

## Report And Record

Send one report on your operator channel: which check failed, the verbatim
error with any status code, and what `provisioning.md` says must change. Record
the result with the time you checked, so your next judging cycle reads it
instead of measuring again, and report a failure once rather than every cycle.
Then return to `elgora-guardian-skill`; a bounty blocked by what you found is
handled there.
