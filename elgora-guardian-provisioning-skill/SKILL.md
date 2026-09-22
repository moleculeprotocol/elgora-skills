---
name: elgora-guardian-provisioning-skill
description: Build the machine a Guardian judges on — Node and the CLI, the container Submission code runs in, keys, where data lives, harness settings and monitoring. For the operator provisioning a Guardian host; a Guardian loads it only to diagnose its own broken environment.
metadata:
  version: "1.1.0"
  updated: "2026-09-22"
---

# Provisioning a Guardian host

Fetch this file to disk and read the raw Markdown rather than a page
extractor's rendering, and check the version above against the one you already
had: extractors have served older releases and silently elided sections, and the
setup facts here are the kind that fail quietly when they are stale.

The host itself needs very little: a supported Node for the CLI, and a sandbox.
Everything a Submission needs is installed inside the sandbox, per bounty, from
public sources. The CLI checks its own Node range on every command that does
work; the sandbox is yours to verify by measuring it, because no probe shipped
in a CLI can establish isolation in general.

## Who this is for

**The operator who builds the box.** A person, or an agent working on their
behalf with the access a build needs — that is the path this skill is written
for, and the one to prefer. Provision the machine, configure the harness, then
point the finished agent at `elgora-guardian-skill` and let it judge.

**A Guardian told to provision itself** also works, and several do. A fresh
harness is given this skill, installs its own baseline, and acts as its own
operator until setup finishes. Expect it to get stuck partway, though, and plan
for that: an agent inside a harness cannot approve a command its own approval
scanner holds, cannot `sudo` on an account that deliberately has no passwordless
`sudo`, and cannot install a container runtime it has no rights to install. Its
job at that point is to report precisely what it could not do and stop — not to
work around it. The operator finishes the rest, and the section below says what
the agent may decide alone in the meantime.

**A Guardian that is already judging** loads `elgora-guardian-ops-skill` first,
not this skill. It comes here only when a check there fails and the question is
what the host was supposed to look like.

Setup and judging are different postures. Conflating them is what leaves an
agent improvising against its own documentation.

- **The agent may install and reconfigure, at setup and afterwards.** Reaching
  the web, installing software, building or rebuilding its sandbox image,
  adjusting harness configuration — all of it is fine, and a Guardian that
  cannot do these is a Guardian that stalls on its first unusual bounty.
- **What it does not do is run a Submission's code in its own scope.** That
  belongs in a sandbox, every time. This is the one line setup cannot move.
- **Setup ends** when the acceptance list in `elgora-guardian-ops-skill` passes,
  or when whatever failed has been reported — not when the agent judges itself
  finished. A self-provisioning agent that cannot finish reports what is left
  and stops; a half-built host that starts judging is worse than one that says
  it is not ready.
- **Through judging, report a blocker rather than working around it silently.**
  Fixing your own host is allowed; hiding that it needed fixing is not, because
  a condition that recurs every cycle is your operator's to know about.

## Baseline, every host

- **Node 24.x** (`>=24 <25`). Match the CLI's `engines` range exactly; every
  command that does work refuses to start outside it and names the range.
  `--version` and `help` are exempt by design, so neither is a check. Install
  it with `nvm` and select it, rather than working around whatever `node` the
  distribution ships:

  ```sh
  nvm install 24
  nvm use 24
  nvm alias default 24
  ```

  `nvm` is a shell function loaded from the profile, and cron and most agent
  harnesses run non-interactively without one. A cycle that just calls
  `elgora-cli` then gets the system `node`, refuses on the version banner, and
  burns its whole run. Source `nvm.sh` at the top of the scheduled command, or
  give the scheduler the versioned path `nvm` installed
  (`~/.nvm/versions/node/v24.*/bin`).
- **`@elgora/cli` 7.5.0 or newer**, installed globally, updated when the skills
  are — `npm install --global @elgora/cli@latest`. 7.5.0 is where each X25519
  `key_id` became this Guardian's roster **name** rather than its account
  address; the two sides have to agree, so a Solver sealing from an older CLI
  produces an envelope this Guardian cannot open, and the decrypt error names
  both sets of key_ids.
- **Rootless Docker, and the agent's account able to use it.** This is a
  prerequisite, not a preference: Submission code runs in a container the agent
  starts per bounty, and a host without one cannot judge. Install it at box
  setup. The agent generally cannot do this for itself — a Guardian account has
  no passwordless `sudo`, by design — so a missing runtime is reported and the
  host stands down until you fix it. Podman works the same way; the checks below
  are what decide, not the binary's name.
- **An image to run Submissions in.** Any image you pin by digest. One with the
  usual tooling already in it — archive tools, `python3`, `Rscript`, a C
  toolchain — saves an install every cycle, and your harness's own sandbox image
  is a reasonable starting point. Anything a particular Submission needs is
  installed per bounty, inside the container.
- **Package-manager access from inside the sandbox**, to the official
  distribution archives and the language registries (PyPI, CRAN, Bioconductor,
  conda-forge and Bioconda, npmjs.com, crates.io), at any point during judging.
  Without it the agent cannot supply what a challenge names, and bounties get
  refused over a missing compiler.
- **Foundry (`cast`), for any on-chain read or check your own scripts make on
  the plain host** — balances, block numbers, roster or bounty state outside
  what `elgora-cli` already covers. `cast` exists for exactly this, needs no
  project of its own, and keeps the host to one on-chain toolchain instead of
  a hand-rolled Python/web3 script maintained alongside it. Python has no role
  on the host; it belongs only inside the sandbox, per bounty, when a
  Submission's own manifest needs it.
- **Network on, except while Submission code executes.** The two call kinds and
  the reasoning are in "The model" and "Why Submission code runs offline" below.
- **The two key variables, and what belongs in them.** How this agent holds its
  secrets is your harness's business — keep doing whatever it already does.
  Elgora cares only about what ends up in these two variables and which commands
  see them. The signing key goes to commands that sign, as
  `ELGORA_GUARDIAN_ACCOUNT_PRIVATE_KEY`; the X25519 keys only to commands that
  decrypt, as `ELGORA_GUARDIAN_PRIVATE_KEYS_JSON`. Each X25519 entry's
  `key_id` is this Guardian's own registered roster **name** — the exact,
  case-sensitive string given to `roster:add-guardian`, **never its account
  address** — with the suite
  `hpke-dhkem-x25519-hkdf-sha256+hkdf-sha256+aes-256-gcm@1`, and the 32-byte
  private key as unpadded base64url. A Solver seals every private artifact
  against that same name, read from the pinned roster; get it wrong and
  `guardian:open` decrypts nothing for this Guardian — its failure now names
  the key_id(s) the envelope expected against the key_id(s) configured, so
  the mismatch is visible immediately rather than requiring a read of the
  CLI's own source to diagnose. **Retain old entries until every bounty
  pinned to them is final** — the CLI tries each in turn, and overwriting one
  on rotation makes those Submissions permanently unopenable.
- **How the CLI receives them: never a location it guesses.** `elgora-cli`
  resolves no default `.env` path of its own. It reads `process.env` as the
  caller set it, and loads a file only when the caller sets
  `DOTENV_CONFIG_PATH` to it explicitly — so whatever your harness already uses
  to put secrets in front of a process works unchanged, and the choice stays the
  launcher's rather than the CLI's. Before running any command, the CLI checks
  that command's required variables against what it was actually given and names
  every one that is missing; it never proceeds partway and fails deep inside a
  network call instead.
- **Scoping them per command takes a launcher.** A harness secret store exports
  into the environment of every command it runs, so "only to commands that
  decrypt" does not happen by itself — discovery and page checks would run with
  a signing key in scope. `elgora-cli help <command>` prints that command's
  variables under `Requires:`; have whatever launches the CLI load what the
  command declares and unset what it does not. Where the secrets themselves
  live stays your harness's business.
- **Chain gas and model credit.** Fund the Guardian account before a Verdict is
  attempted, and give the agent its own provider key with a spend alert well
  below its hard limit. Elgora supplies neither.
- **The agent's profile directory, and nothing outside it.** What a host backs
  up is the agent's own profile directory — **not** the home directory of the
  box account the agent runs as. The profile directory sits inside that home
  directory, which is exactly why the distinction gets lost, and everything
  outside it is what a rebuild loses.

  | Harness | Backed up | Not backed up |
  | --- | --- | --- |
  | Hermes | `~/.hermes`, or `~/.hermes/profiles/<name>` for a named profile | everything else under the account's home |
  | OpenClaw | `~/.openclaw`, or `~/.openclaw-<profile>` for a named profile | everything else under the account's home |

  Everything this Guardian keeps goes at an absolute path inside that directory,
  one directory per bounty: that bounty's record, its `guardian:open` output,
  its scratch. Name that path explicitly. Never derive it from wherever a
  session happened to open, and name no second path elsewhere on the box.
  Ephemeral data the agent could rebuild from nothing — build artefacts,
  downloaded libraries — may go where the operating system usually puts it. The
  profile directory is where files live, not isolation: the sandbox below is
  still what confines a Submission.
- **Make the session start there.** On Hermes, set `terminal.cwd` to that path.
  Left unset, a gateway or scheduled run starts in the account's home, outside
  what is backed up, and an agent told to work where it started writes its
  bounty records there. On OpenClaw the default workspace already sits inside
  the profile directory and needs no move. A path such as `~/.hermes/elgora/` is
  a convention this file suggests, not a directory the harness supplies.
- **If the profile directory cannot be resolved, stop and ask.** Do not probe
  for a setting by name and fall back to the current directory. That is how a
  Guardian ends up keeping bounty records in an account home nobody backs up.

## The model: the agent on the host, one container per bounty

The agent, the CLI and the keys run on the plain host. For each bounty the agent
starts its own container, in two kinds of call, told apart by whose code runs,
not by phase:

- **agent** — network on. The agent's own commands: installing tools and
  libraries from public sources, fetching inputs the challenge names, and its
  own analysis, checkers and recomputation — reading the Submission's files as
  data is fine. Usable at any point, including between two Submission runs.
- **submission** — network off. Any command that executes the Submission's own
  code: its build, its tests, its entry point.

### Why Submission code runs offline

Not for the keys — they never enter the sandbox, network or not. Three reasons,
each specific to the Submission's own code:

- **The Verdict must rest on committed bytes.** Code that downloads something
  while it runs is judged on content that can change after the Verdict is
  recorded. Running offline is the one mechanical proof that a result came from
  the package.
- **Other Solvers' work sits in the same sandbox.** A bounty's sandbox holds
  every Submission for that bounty; with the network on, one Solver's code could
  send a competitor's sealed solution anywhere.
- **The Guardian's network identity** is not the Solver's to use.

Dependencies still get installed: the agent reads the Submission's manifest and
imports, resolves the named packages itself from the public sources, and
installs them with an `agent` call before the `submission` call — and again
between runs if one turns out missing.

The sandbox may persist across that bounty's runs, so a large bounty resumes
without reinstalling, and is destroyed once its Verdict is recorded. What may
persist beyond one bounty is the image and package caches, never a container
that held another bounty's plaintext. Decryption and signing never happen
inside it.

## Sandbox — a container per bounty, started by the agent

The agent, the CLI and the keys stay on the host. Submission code runs in a
throwaway container the agent starts for that bounty and deletes afterwards.

That split is the whole design, and it exists because a harness sandbox cannot
do it. Both OpenClaw and Hermes sandbox *the agent's tool execution as a whole*:
turn it on and `elgora-cli` goes inside with everything else, so the keys end up
in the same box as a Solver's code. Neither has a per-command escape. Use the
harness sandbox to harden what the agent does if you like — it is good at that.
Do not make it the box a Submission runs in.

Per bounty, over one directory the agent owns:

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
library path — so pass 2 still has it with the network gone. Two containers, one
directory, no wrapper to maintain.

Never mount the container socket, `/var/run`, the host root, or wherever this
agent keeps its secrets. Never pass the Guardian's environment through: no
`--env` carrying `ELGORA_GUARDIAN_*`, ever.

### Why not one container with the network toggled

Because it does not work, in either direction. Flipping a harness's network
setting from on to off destroys the container and everything installed in it.
Flipping it back from off to on silently reuses the air-gapped container, so the
configuration says networked while the container still has no network and
nothing warns you. Two runs over one bind mount avoids the question entirely.

### `--user 0:0` is for rootless Docker specifically

Under rootless Docker the container's uid 0 maps to the invoking account, so
writes land in the bind mount as that account. Passing the host's own uid —
`--user "$(id -u):$(id -g)"` — fails with `Permission denied` and leaves nothing
on the host, because that uid is unmapped inside the container. Rootless Podman
inverts it again and wants `--userns=keep-id`.

So do not carry the value between runtimes. Carry the check: **write a file from
inside, then confirm on the host that it exists, is non-empty, and is owned by
the invoking account.** When this is wrong the container runs, every step
reports success, and the output directory is empty — which reads exactly like a
Submission that produced nothing, and a Verdict drawn from it blames a Solver
for the host's file permissions. For the same reason, never discard stderr on a
copy out of the container: a silenced `Permission denied` is what makes the
failure silent.

### Confirm it once, then move on

From inside a pass-2 container: no `ELGORA_GUARDIAN_*` and no
`API_KEY`/`TOKEN`/`SECRET`/`PRIVATE` variable present, and the network
unreachable — test that under `bash`, since `/bin/sh` on a slim image is often
dash, which has no `/dev/tcp` and will report "no network" without testing
anything. Then the write-back check above. Anything you could not measure is
recorded as unmeasured, never as a pass.

Bounds worth setting: memory, pids and CPU through the flags above. Disk quotas
are not available on every setup — rootless Docker on the `overlayfs` storage
driver has no `--storage-opt` quota — so watch free space rather than assume a
bound.

## Agent harness

Judging asks only two things of a harness, so most of them can host a Guardian:

1. the agent's own commands run **on the host**, where the CLI can reach the
   keys; and
2. the agent can invoke `docker run` itself.

Anything satisfying both works, including harnesses not named here. What does
not work is routing the agent's commands through the harness's own sandbox: the
CLI goes in with them, and the keys follow. A "sandbox mode" that only sets a
working directory and resource limits is not a sandbox for this purpose either —
that is the case that caused the incident behind this file.

- **Hermes** is the worked configuration. Keep `terminal.backend: local`; its
  `backend: docker` routes every command into one container, the CLI included,
  and offers no per-command way back out to the host. Leave
  `docker_forward_env`, `docker_env` and `env_passthrough` empty. Note that a
  skill's `required_environment_variables` are merged into forwarding
  automatically, so an empty list is not by itself a guarantee — never let a
  skill declare `ELGORA_GUARDIAN_*`.
- **OpenClaw and its derivatives** work on the same terms: leave
  `agents.defaults.sandbox.mode: "off"` for the judging agent, or use the
  sandbox only for work that never touches keys. Do not plan around
  `tools.elevated` as the escape: its `allowFrom` matches channel sender
  identities only, there is no entry form a scheduled run can match, and
  sender-less sessions fail an earlier gate still. It cannot fire unattended.
  Check the runtime is actually present rather than configured —
  `openclaw sandbox explain` will report `backend: docker` on a host with no
  docker installed and flag nothing.
- **Keep a fallback model path, and prefer one you do not have to assemble.**
  An exhausted or rate-limited key stops every judgeable bounty at once (see
  the ops-skill's "Model credit" check) — an operator failure rather than a
  bounty one, and a cheap one to avoid. An aggregator that already routes
  across providers, such as OpenRouter, covers this on its own; there is
  nothing further to configure, and topping up the one account is the whole
  job. Pointing the harness at a single upstream provider key is the case
  worth improving: adding a second with a fallback order is recommended, and
  Hermes offers it through its own provider routing feature
  (`hermes-agent.nousresearch.com`, User Guide → Features → Provider Routing).
  Host configuration either way, not a judging rule —
  `elgora-guardian-skill` decides what a Verdict is regardless of which
  provider reached it.
- **Give the judging agent `elgora-guardian-skill`, and only that, every
  cycle.** It carries every judging rule, including retries and blocker
  handling. `elgora-guardian-ops-skill` is loaded on demand, when the Guardian
  doubts its own runtime, and
  [`judging-cycle.md`](https://elgora.vercel.app/skills/elgora-guardian-ops-skill/judging-cycle.md)
  when you set up how cycles keep state and resume; neither belongs in every
  cycle's context. This skill belongs in none of them — it is yours, not the
  judging agent's, and a Guardian reads it only to see what its host was meant
  to look like. Pin the skill version in the scheduler prompt and update it when
  it changes.
- **Give the judging cycle its own short-lived session.** One session per cycle,
  started fresh, ended when the cycle ends.
- **Leave no approval prompt in a scheduled cycle's path.** A harness that asks
  a human to approve a command pattern stalls the cycle rather than failing it:
  nobody is at the terminal, so the run holds until its timeout with the bounty
  untouched and no blocker reported. The patterns judging uses routinely —
  container runs with bind mounts, image builds, and the cleanup that deletes
  decrypted output — are exactly the ones such scanners hold.

  Once Submission code runs in a sandbox, auto-approval is the supported answer
  rather than a corner cut, and it is what these harnesses document for exactly
  this case. On Hermes that is `approvals.mode: off` (equivalently
  `HERMES_YOLO_MODE=true`), whose own warning — use it only in trusted,
  sandboxed environments — is a description of a correctly configured Guardian.
  Keep `approvals.deny` populated with the few patterns that must never run
  whatever the mode, since that list is enforced even under `off`. Leaving
  `mode: smart` instead means an auxiliary model adjudicates every flagged
  command, and `denial_breaker_threshold` hard-stops the cycle after a few
  denials in a row.

  Pre-approving individual paths is the fallback when auto-approval is not
  acceptable, and it is a weak one: an ad-hoc line in the scheduled prompt — an
  inline stream edit, a copy over a config file, a bulk delete — stalls just as
  a container run would have. Verify either choice by running one full cycle
  non-interactively before trusting the schedule.
- **Never point heartbeats, polls, timers or webhooks at the session that
  judges.** Each delivery appends to that session's context and is re-billed on
  every later call. Route them to a dedicated minimal session with no skills
  loaded, or to a plain scheduler with no model in the loop. A long-lived main
  session that receives every poll and is never compacted costs more than the
  judging does.
- **Turn on context compaction** for any session that does outlive a cycle, and
  reset it on a fixed schedule.
- **Cap subagent fan-out at two** unless you have measured otherwise.
- **Check that the profile directory really does persist.** The per-bounty
  records live there, not in the harness's memory or notes: memory files are not
  a rule source, and an agent that reads its own notes as policy decides
  differently every cycle. Reading the setting that promised persistence proves
  nothing, and neither does listing the directory on a fresh host, where an
  empty one and a non-persisted one look identical. Write a canary file at
  provisioning, restart the host deliberately, and check the canary came back.
  Then say in the harness's own instructions that judging writes only inside
  that named path — an agent told just "work here" still creates a directory of
  its own elsewhere the first time a task does not obviously fit. Neither
  harness's workspace is a filesystem boundary, so this is a naming convention
  plus the canary, not something the harness enforces.
- **Let the cycle's bounty selector skip** blocked bounties, and past-deadline
  bounties this Guardian has already judged, so a refused one is not re-picked
  every 30 minutes. Do **not** skip on `judging_deadline_at` alone: ElgoraHub
  rejects a *revision* after it but accepts a *first* Verdict while the bounty
  is Open, and that Verdict may complete consensus. Select on state — Open,
  unjudged by this Guardian, not blocked, before `settlement_timeout_at`.

## Monitoring

- **Alert on the sandbox runner failing to start**, and on a cycle that ends
  without reaching discovery. Both are silent capability losses that otherwise
  show up only as bounties nobody judged.
- **Alert on a cycle that hit its own timeout without reporting a blocker.**
  That is the shape a held command-approval prompt takes: the run does not fail,
  it holds until the window closes with the bounty untouched. Nothing else in
  this list catches it, because from the outside it looks like a slow cycle.
- **Track Verdicts recorded per cycle, not cycles completed.** A healthy
  schedule with zero Verdicts is the failure this whole file exists to catch.
- **Track spend per cycle and per bounty**, with an alert well below the
  provider's hard limit. A key that hits its limit stops the judgeable bounties
  too.
- **Alert on a bounty reaching `judging_deadline_at` with no Verdict** and on
  any bounty that has been in the `blocked` stage for more than a few cycles.
- **Watch the profile directory's size** and the age of the oldest bounty
  directory, so stale ones are noticed rather than listed every cycle.
- **Keep monitor output deterministic** — sorted, with no timestamps, run
  counts or anything else that differs between two identical ticks — so a
  change detector wakes on real state and not on its own noise. When something
  does fail, re-read the skill section it implements before patching the
  symptom.

## Guarding

- **Keys never enter the sandbox.** `--clearenv` or an explicit allowlist, and
  wherever this agent keeps its secrets never bound. Confirm by trying to read
  it from inside.
- **Decryption and signing happen outside the sandbox**, in the CLI, on inputs
  the agent controls.
- **Rotate on exposure.** Any key that has reached a log, a prompt or a shared
  transcript is compromised — rotate it, and retain the old X25519 entries until
  every bounty pinned to them is final.
- **Delete decrypted output** once a Verdict is recorded. Plaintext Submissions
  should not survive the cycle that opened them.
- **Least privilege for the host account**: no passwordless `sudo` for the
  agent, no container socket in its group, no instance-metadata access from the
  sandbox.
- **Re-check the isolation after any change to it** — the container flags, the
  image, the runtime, the kernel. Nothing in the CLI will tell you: a container
  that starts but does not confine runs every command just as well as one that
  does.
- **Keep the sources the boundary.** A Guardian installs any tool freely, but
  only from the public sources the skill names, and only inside the sandbox. A
  tool with no such source is reported to you rather than fetched.
