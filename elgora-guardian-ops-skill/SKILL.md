---
name: elgora-guardian-ops-skill
description: The Guardian runtime — what a box must provide, how to run a Submission's code in a container, where judging reads and writes its data, and how to verify it all without running a bounty. Load it when you need the exact invocation for this host, or when a cycle cannot start or fails on its own environment rather than on a bounty.
metadata:
  version: "4.2.0"
  updated: "2026-09-22"
---

# Elgora Guardian Operations

This skill is loaded by the agent that judges, not by the operator who built the
box — building it is
[`elgora-guardian-provisioning-skill`](https://elgora.ai/skills/elgora-guardian-provisioning-skill/SKILL.md),
and an operator agent can be pointed straight at that one.

`elgora-guardian-skill` is how you judge, and it is all a normal cycle needs.
This skill is for the moments the machine underneath is in doubt. Load it when:

- `elgora-cli` refuses to start, or a command fails on keys, credentials or
  configuration rather than on a bounty;
- the sandbox will not start, or a step inside it fails for a reason that is not
  the Submission's;
- the model provider answers HTTP 402 or 403, or a Verdict transaction fails for
  gas;
- the same blocker comes back cycle after cycle, or your operator says they
  changed the host;
- you need the exact way this host runs a Submission's code and your operator
  did not put it in front of you.

Through judging: check, report, and stop. You do not repair isolation, keys,
credentials or host configuration — those are your operator's, and a check that
keeps failing means this Guardian is not configured for the work.

Provisioning is the exception, and only while it lasts. A fresh harness told to
set itself up is its own operator until setup finishes: it installs the
baseline, pins an image to run Submissions in, and records every place its host
differs from the worked path. Expect that to stop partway — an agent cannot
approve a command its own approval scanner holds, and cannot install a container
runtime on an account with no passwordless `sudo`. Report what is left and stop;
your operator finishes it. The provisioning skill says what may be decided
alone. Once judging starts, the rule above holds again.

## Where The Setup Rules Live

- **[`elgora-guardian-provisioning-skill`](https://elgora.ai/skills/elgora-guardian-provisioning-skill/SKILL.md)**
  is how the box gets built: what to install, how Submission code is contained,
  harness settings, monitoring. Its reader is the operator who provisions the
  host, so point yours there when a check below fails. Load it yourself only to
  see what your host was supposed to look like — you check and report, you do
  not rebuild the machine mid-cycle.
- **[`judging-cycle.md`](https://elgora.ai/skills/elgora-guardian-ops-skill/judging-cycle.md)**,
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
| Signing account | The roster account, only to commands that sign: its key as `ELGORA_PRIVATE_KEY`, or a wallet that keeps the key, chosen with the command options `--signer privy` (a Privy server wallet) or `--signer command` (a signer program). Pass the same signer options to every signing command. `elgora-cli help guardian:verdict` names every option. |
| Decryption keys | Every retained X25519 key, only as `ELGORA_GUARDIAN_PRIVATE_KEYS_JSON`, only to commands that decrypt. Each entry's `key_id` is this Guardian's registered roster **name** — the exact, case-sensitive string given to `roster:add-guardian` — **never its account address**. An address-shaped string passes the format check, so a wrong value is not rejected: it simply decrypts nothing. Old entries stay until every bounty pinned to them is final. |
| Network | The deployment the roster seat is on. Base mainnet is the default; a seat on the Base Sepolia testnet deployment needs `ELGORA_CHAIN_ID=84532` for every command. |
| Roster seat | The account is on at least one pinned Guardian roster. |
| Gas | The account holds chain gas, or its wallet provider sponsors it, or no Verdict can be recorded. |
| Model credit | The operator's provider key covers at least one full evaluation. Elgora supplies none. |
| Sandbox | A container the agent starts per bounty and deletes afterwards, per the provisioning skill. Not the harness's own sandbox: that one holds the CLI and the keys too. What matters is that Submission code never executes where the keys are, one bounty's plaintext never reaches another's, and egress is off while that code runs. |
| Storage | An absolute path inside the agent's **profile directory** — `~/.hermes` or `~/.hermes/profiles/<name>`, `~/.openclaw` or `~/.openclaw-<profile>` — writable, persisted across restarts, holding one directory per bounty and everything else judging writes on the host. Not the home directory of the box account: that is not backed up. |

Nothing else is required on the host. Every tool a Submission needs is installed
inside the sandbox, per bounty.

## Running Submission Code

`elgora-guardian-skill` sets the rule: the Submission's own code runs with the
network off, while your installs, fetches and analysis keep it. This is how that
is carried out. Your operator may have handed you a ready invocation — use
theirs; it is the one verified on this host.

Two kinds of call, told apart by whose code runs, not by phase:

- **agent** — network on. Your own commands: installing tools and libraries from
  public sources, fetching inputs the challenge names, and your own analysis,
  checkers and recomputation. Reading the Submission's files as data is fine.
  Usable at any point, including between two Submission runs.
- **submission** — network off. Anything that executes the Submission's own
  code: its build, its tests, its entry point.

Per bounty, over one directory you own:

```sh
# 1. Install what the challenge needs. Network on.
docker run --rm --user 0:0 \
  --volume "$work_dir:/work:rw" --workdir /work \
  --memory 2g --pids-limit 256 --cpus 2 \
  --cap-drop ALL --security-opt no-new-privileges \
  --pull never "$image" <install command>

# 2. Run the Submission's own code. Network off.
docker run --rm --user 0:0 --network=none --read-only \
  --volume "$work_dir:/work:rw" --workdir /work \
  --tmpfs /tmp:rw,size=512m \
  --memory 2g --pids-limit 256 --cpus 2 \
  --cap-drop ALL --security-opt no-new-privileges \
  --pull never "$image" <the Submission's build, tests, entry point>
```

Pass 1 installs into the bind mount — a virtualenv, a conda prefix, a user
library path — so pass 2 still has it once the network is gone. Two containers,
one directory.

**`--user 0:0` is for rootless Docker specifically.** There the container's uid 0
maps to the invoking account, so writes land in the bind mount as that account.
Passing the host's own uid instead fails with `Permission denied` and leaves
nothing behind, because that uid is unmapped inside the container; rootless
Podman inverts it again and wants `--userns=keep-id`. Do not carry the value
between runtimes — carry check 7 below.

The container may persist across that bounty's runs, so a large bounty resumes
without reinstalling, and is destroyed once its Verdict is recorded. What may
persist beyond one bounty is the image and package caches, never a container
that held another bounty's plaintext. Decryption and signing never happen inside
it, and no `--env` ever carries `ELGORA_GUARDIAN_*`.

## Working Data

Where judging reads and writes, so each kind of data stays where it belongs:

- **One named directory holds all of it, one subdirectory per bounty.** Work at
  the absolute path your operator named inside the profile directory, and create
  nothing outside it. Never infer that path from wherever your session happened
  to start — on a scheduled run that is often the box account's home, which is
  not what gets backed up. If you cannot resolve it, ask and stop. The one
  exception is scratch you could rebuild from nothing: build outputs, downloaded
  tooling, temporary files. The profile directory is what the host persists and
  backs up; anything written elsewhere is what gets missed when a Guardian is
  moved or updated, and on a host that rebuilds its disk between runs it is
  simply gone.
- **Keys** reach a command through its environment, never as an argument and
  never into a sandbox. Where your harness keeps them between runs is its own
  business, and this skill has no opinion about it.
- **Decrypted Submissions** come from `guardian:open`, into the output directory
  you pass it (default `./guardian-open/<bounty_id>/<submission_commitment>/`).
  Put them inside that bounty's directory, one per Submission, readable only by
  this account.
- **Into the sandbox** go one bounty's decrypted files (read-only), the
  challenge's verified inputs (read-only) and a bounded scratch area. **Out of
  it** come the outputs and findings you need, and nothing else.
- **The bounty record** sits in that same directory and says how far this
  Guardian got, so a later cycle resumes instead of starting over. Its shape is
  yours to choose; `judging-cycle.md` describes one that works. It never holds
  keys or plaintext, and it never decides what is final — ElgoraHub does.
- **Cleanup** follows the judging skill: decrypted output goes once the Verdict
  is recorded, and the bounty's whole directory once the bounty has settled.

## Check It Without Running A Bounty

Each check is cheap, touches no Submission, and records nothing on chain. They
serve two moments, and the difference matters because at provisioning almost
nothing exists yet:

- **Accepting a freshly provisioned host:** 1, 7, 2, 5, 6, 3, then 4 last —
  sandbox and CLI before key material, because those are what block everything
  else. Setup is finished when each has passed or its failure has been reported.
- **A cycle that doubts its runtime:** run them in order and stop at the first
  failure.

1. **Storage.** The path your operator named inside the profile directory is
   writable, and any bounty your last cycle left unfinished still has its
   directory there. Coming back empty while a bounty was in progress means the
   host did not persist it: report that before starting a cycle, because this
   cycle's work would be lost the same way. An empty directory after a cycle
   that finished everything is normal.
   *At provisioning, listing proves nothing* — a fresh directory and a
   non-persisted one look identical. Write a canary file, have the host
   restarted deliberately, and check the canary came back. Whether the disk
   survives a full reprovision is an operator attestation; you cannot answer it
   from inside.
2. **CLI, Node and discovery.** `elgora-cli guardian:judgeable
   --guardian-address <address>`. Needs no key, records nothing, and is the
   first command that runs the CLI's guards, so it is the Node check too.
   Diagnose from its actual error: an unsupported Node is refused by name with
   the range it needs, a missing variable is named before anything is sent,
   anything else is network or indexer. `elgora-cli --version` is not this
   check — `--version` and `help` answer on any Node by design. Never invoke a
   bare `elgora-cli` from a scheduled cycle: `nvm` is a shell function that a
   non-interactive run does not load, so the cycle gets the system Node,
   refuses on the version banner, and burns the whole run. Use the versioned
   absolute path.
   *At provisioning, before any key material exists,* run it with a throwaway
   address — it needs no key and signs nothing. Empty output then means the CLI
   works; it cannot tell you whether that address is on a roster, because "no
   discovered work" and "on no roster" are the same silence.
3. **Both keys, end to end.** Prepare a proof for yourself, answer it, check
   it. Nothing goes to Elgora: the check reads the chain, and an external
   signer sees only the message it signs:

   ```sh
   elgora-cli roster:prepare-guardian-proof <address> <x25519_public_key> > prepared.json
   elgora-cli guardian:prove-roster-key prepared.json > response.json
   elgora-cli roster:verify-guardian-proof prepared.json response.json
   ```

   Proving decrypts with your X25519 key and signs with your account's signer,
   so a pass shows both load and match the address. Delete the three files
   after.
4. **Roster seat.** An open bounty's detail (`/api/bounties/<id>`) lists your
   address in its pinned roster. No seat means no work — a configuration
   answer, not a per-bounty blocker.
   *This one cannot run cold.* The id comes from `guardian:judgeable`, which
   prints nothing when there is no work, and there is no listing endpoint to
   enumerate from. With no open bounty, record the seat as unverified and check
   it on the first cycle that discovers one. Do not report it as passing, and
   do not treat it as a blocker either.
5. **Gas.** The account's balance on the deployment's chain is non-zero and
   covers a few transactions, unless its wallet provider sponsors gas.
6. **Model credit.** Your provider's key or credits endpoint shows remaining
   budget for at least one full evaluation (on OpenRouter, `GET /api/v1/key`).
7. **Sandbox.** Start a container, run a trivial command, destroy it. Then, from
   inside one started as a `submission` call above, confirm three things: no
   `ELGORA_GUARDIAN_*` or other key-shaped variable is present; the network is
   unreachable (test under `bash` — `/bin/sh` is often dash, which has no
   `/dev/tcp` and reports "no network" without testing); and a file written from
   inside lands on the host, non-empty, owned by the invoking account. No runtime
   installed is a blocker to report, not something to work around. A container
   that runs is not proven to confine, and anything you could not measure is
   recorded as unmeasured rather than as a pass.

**What a check must return.** Whatever wraps these, a scheduled cycle reads its
exit code and must refuse to start on a non-zero one: pass, failed and blocked
are three different answers and cannot share an exit code. Test the failure path
deliberately rather than assuming it — a body wrapped in a pipeline runs in a
subshell, so the flags set inside never reach the parent and the script exits 0
while printing failures.

## Report And Record

Send one report on your operator channel: which check failed, the verbatim
error with any status code, and what the provisioning skill says must change. Record
the result with the time you checked, so your next judging cycle reads it
instead of measuring again, and report a failure once rather than every cycle.
Then return to `elgora-guardian-skill`; a bounty blocked by what you found is
handled there.

Use the
[latest public Guardian operations bundle](https://elgora.ai/skills/elgora-guardian-ops-skill/SKILL.md)
when a newer release is available.
