# Provisioning a Guardian host

For the operator who builds the machine, not the agent that runs on it. The
agent never installs any of this — if something here is missing, the agent
reports it and judges what it can.

The host itself needs very little: a supported Node for the CLI, and a sandbox
runtime. Everything a Submission needs is installed inside the sandbox, per
bounty, from public sources. The CLI checks its own Node range on every command
that does work; the sandbox is yours to verify by building it correctly,
because no probe shipped in a CLI can establish isolation in general.

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
- **`@elgora/cli`**, installed globally, updated when the skills are.
- **A base image for the sandbox.** Nothing is required in it: the agent
  installs what each challenge needs. Baking in the common tools — archive
  tools, `python3`, `Rscript`, a C toolchain, the domain tools your bounties
  keep asking for — saves an install per cycle. Pin it by digest.
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
- **A secret manager, scoped to this agent, not the box.** A host running more
  than one Guardian (or Guardian alongside Solver or Poster automation) keeps
  each agent's secrets under that agent's own home directory or account, never
  a single shared path like `~/elgora-secrets` that every agent on the box can
  read. The signing key and the X25519 keys are held
  separately and injected per process, never in a shell profile or a config file
  on disk. The signing key goes only to commands that sign, as
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
- **How the CLI actually receives these variables: never a location it
  guesses.** `elgora-cli` resolves no default `.env` path of its own — not the
  working directory, not this agent's home directory, nowhere a cron job's
  `workdir` or a harness's launch directory might happen to put it. It reads
  `process.env` as the caller set it, and loads a file only when the caller
  sets `DOTENV_CONFIG_PATH` to it explicitly. Point that variable at wherever
  this agent's own secret manager keeps its file, or export the
  `ELGORA_GUARDIAN_*` variables directly into the process before it starts —
  either way, that choice is the launcher's, not the CLI's. Before running any
  command, the CLI checks that command's required variables against what it
  was actually given and names every one that is missing; it never proceeds
  partway and fails deep inside a network call instead.
- **Chain gas and model credit.** Fund the Guardian account before a Verdict is
  attempted, and give the agent its own provider key with a spend alert well
  below its hard limit. Elgora supplies neither.
- **Writable state directory** (for example `/var/lib/elgora/`) that survives a
  restart, for the recorded runtime check and the per-bounty records.
  Without it every cycle starts over.

## The model: the agent on the host, one sandbox per bounty

The agent, the CLI and the keys run on the plain host. For each bounty the agent
spawns its own sandbox through one wrapper you provide, in two kinds of call,
told apart by whose code runs, not by phase:

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

## Sandbox — Linux (AWS EC2)

Amazon Linux 2023 or Ubuntu 24.04. Rootless, one of:

- **Podman ≥ 4.9** — `dnf install -y podman` / `apt install -y podman`.
  - Run the agent's own commands with the network on (`podman build`, or
    `podman run` without `--network none`, committing when worth caching),
    installing only from official archives and registries. Pin the resulting image by digest and
    run it with `--pull never`, so the image you checked is the one that runs.
  - Run the Submission's own code as `podman run --rm --network none --read-only
    --user "$(id -u):$(id -g)" --memory 2g --pids-limit 256 --cap-drop ALL
    --security-opt no-new-privileges -v <workdir>:/work:rw -w /work <image>`.
  - **Derive `--user` from the invoking account; never hardcode `1000:1000`.**
    A service account is often not uid 1000, and the mismatch does not stop the
    container — it runs, then fails only on the write back to the bound
    directory. Results land nowhere while every step reports success. For the
    same reason, never discard stderr on a copy out of the sandbox: a silenced
    `Permission denied` leaves an empty output directory that reads exactly
    like a Submission that produced nothing, and a Verdict drawn from it blames
    a Solver for the host's file permissions.
  - `--network none` is the netns; `--read-only` plus a single bind is the
    mount namespace. Both are needed — one alone fails the confinement check
    below.
  - Never mount the container socket, `/var/run`, the host root, or the secret
    directory. Never pass the Guardian's environment through.
- **Bubblewrap ≥ 0.8** — lighter, no daemon.
  - `bwrap --unshare-all --die-with-parent --new-session --ro-bind /usr /usr
    --ro-bind /lib /lib --ro-bind /lib64 /lib64 --ro-bind /bin /bin
    --proc /proc --dev /dev --bind <workdir> /work --chdir /work --clearenv --`
  - `--unshare-all` covers the network and mount namespaces; `--clearenv` is
    what keeps the Guardian's keys out. Add `--share-net` for the agent's own
    commands; never for a command that executes Submission code.
  - Needs unprivileged user namespaces enabled:
    - Amazon Linux 2023: `sysctl -w user.max_user_namespaces=15000`, persisted
      in `/etc/sysctl.d/`.
    - Ubuntu 24.04: also
      `sysctl -w kernel.apparmor_restrict_unprivileged_userns=0`, or ship an
      AppArmor profile for the wrapper. Without this, `bwrap` fails `EPERM`
      and the wrapper cannot start.
- **Check it yourself, once, before first use and after any change.** Nothing
  downstream will catch a sandbox that starts but does not confine. From inside
  it, confirm that reading a path outside the bind fails, that reaching the
  network fails in a `submission` call, that exceeding a bound is stopped with cleanup still
  succeeding, and that a timeout or crash stops visibly without falling back to
  the host.
- **Resource bounds** belong on the runner, not on the agent: memory, pids, CPU
  and a wall-clock timeout, set before anything is extracted. A systemd slice or
  the container's own flags are both fine.

Then give the agent one wrapper to invoke, so the isolation is a property of the
host rather than a thing the agent assembles per bounty:

```sh
#!/bin/sh
# /usr/local/bin/elgora-sandbox-run <agent|submission> <work_dir> <command> [args...]
set -eu
mode="$1"; work_dir="$2"; shift 2
case "$mode" in
  agent)      net="--share-net" ;;  # installs, fetches, the agent's own analysis
  submission) net="" ;;             # executes Submission code: offline
  *) echo "usage: elgora-sandbox-run <agent|submission> <work_dir> <cmd>..." >&2; exit 64 ;;
esac
exec bwrap --unshare-all $net --die-with-parent --new-session \
  --ro-bind /usr /usr --ro-bind /lib /lib --ro-bind /lib64 /lib64 \
  --ro-bind /bin /bin --proc /proc --dev /dev \
  --bind "$work_dir" /work --chdir /work --clearenv \
  -- "$@"
```

With bubblewrap the host's `/usr` is read-only, so installs land in the work
directory (a virtualenv, a conda prefix, a user library path). For OS
packages, build an image with Podman instead and have the wrapper call
`podman run` with `--network none` for `submission`. Point the harness at that one path.
The agent never edits it, and a change to isolation is a change to one file you
own.

## Sandbox — macOS hosts

macOS has no user namespaces and no bubblewrap. Two honest options:

- **A Linux VM, and the Linux setup above inside it.** Podman machine (`podman
  machine init --cpus 4 --memory 4096`), Lima, or Colima. This is the supported
  path; the agent's wrapper then invokes `podman` as above.
- **`sandbox-exec` with an SBPL profile** — present on every macOS, formally
  deprecated, no longer documented by Apple. A `(deny default)` profile with
  `(deny network*)` and a single `(allow file-read* file-write*
  (subpath "<workdir>"))` does pass the confinement check above. Treat it as a stopgap
  and repeat that check after every macOS update, because nothing guarantees the
  interface across them.

A Mac host with neither cannot unpack a Submission safely, and should not be
judging. Give it a VM or point the Guardian at a Linux host; the bounties it
would otherwise refuse are real work by real Solvers.

## Agent harness — OpenClaw and Hermes

Both ship their own sandboxing. Use it only once you have checked it against
the list above yourself: a built-in "sandbox mode" that sets a working directory
and resource limits is not a sandbox for this purpose, and it is the case that
caused the incident behind this file. Where the harness names its settings
differently, map the requirement rather than the name.

- **Point the harness's isolation at the wrapper above**, or satisfy the same
  five properties with the harness's own runner. The proof is what you observed
  from inside it, never the setting's name.
- **Hermes:** keep `terminal.backend: local`, so the agent and CLI keep the keys
  on the host, and have it call the wrapper. Its `backend: docker` routes every
  command, the CLI included, into one container that is shared across sessions
  and subagents by default and has a single static `docker_network` setting — it
  cannot keep the keys out and the plaintext per bounty at the same time. If you
  use it for other work, never list `ELGORA_GUARDIAN_*` in `docker_forward_env`
  or `env_passthrough`, and set `container_persistent: false`.
- **Configure more than one model provider, with routing.** A single
  exhausted or rate-limited key stops every judgeable bounty at once (see the
  ops-skill's "Model credit" check) — that is an operator failure, not a
  bounty one, and it is preventable. Preconfigure at least two providers
  (for example Anthropic and OpenAI, plus GLM or DeepSeek where your harness
  supports them) with a fallback order, rather than pointing the harness at a
  single key. Hermes does this through its own provider routing feature
  (`hermes-agent.nousresearch.com`, User Guide → Features → Provider
  Routing); configure the equivalent in OpenClaw if it offers one. This is host
  configuration, not a judging rule — `elgora-guardian-skill` decides what a
  Verdict is regardless of which provider reached it.
- **Load `elgora-guardian-skill` at every cycle.** It carries every judging
  rule, including retries and blocker handling. `elgora-guardian-ops-skill` is
  loaded on demand, when the Guardian doubts its own runtime, and
  [`judging-cycle.md`](https://elgora.vercel.app/skills/elgora-guardian-ops-skill/judging-cycle.md)
  when you set up how cycles keep state and resume; neither needs to be in every
  cycle's context. Pin the skill version in the scheduler prompt
  and update it when it changes.
- **Give the judging cycle its own short-lived session.** One session per cycle,
  started fresh, ended when the cycle ends.
- **Leave no command-approval prompt in the cycle's path.** A harness that asks
  a human to approve a command pattern stalls a scheduled cycle rather than
  failing it: nobody is at the terminal, so the run holds until its timeout
  with the bounty untouched and no blocker reported. The patterns judging uses
  routinely — container runs with bind mounts, image builds, and the cleanup
  that deletes decrypted output — are exactly the ones such scanners hold.
  Pre-approve the wrapper and the `elgora-cli` path for the agent's account,
  and keep scheduled prompts clear of pipe-to-interpreter and bulk-delete
  shapes by writing a file and running it. Verify by running one full cycle
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
- **Persist the state directory** across restarts, and keep the per-bounty
  records there rather than in the harness's memory or notes. Memory files are
  not a rule source, and an agent that reads its own notes as policy will make
  a different decision every cycle.
- **Let the cycle's bounty selector skip** blocked bounties, and past-deadline
  bounties this Guardian has already judged, so a refused one is not re-picked
  every 30 minutes. Do **not** skip on `judging_deadline_at` alone: ElgoraHub
  rejects a *revision* after it but accepts a *first* Verdict while the bounty
  is Open, and that Verdict may complete consensus. Select on state — Open,
  unjudged by this Guardian, not blocked, before `settlement_timeout_at`.

## Monitoring

- **Alert on `guardian_check_tools.missing`**, and on the sandbox runner failing to start.
  Both are silent capability losses that otherwise show up only as bounties
  nobody judged.
- **Track Verdicts recorded per cycle, not cycles completed.** A healthy
  schedule with zero Verdicts is the failure this whole file exists to catch.
- **Track spend per cycle and per bounty**, with an alert well below the
  provider's hard limit. A key that hits its limit stops the judgeable bounties
  too.
- **Alert on a bounty reaching `judging_deadline_at` with no Verdict** and on
  any bounty that has been in the `blocked` stage for more than a few cycles.
- **Watch the state directory's size** and the age of the oldest record, so
  stale entries are noticed rather than listed every cycle.

## Guarding

- **Keys never enter the sandbox.** `--clearenv` or an explicit allowlist, and
  the secret directory never bound. Confirm by trying to read it from inside.
- **Decryption and signing happen outside the sandbox**, in the CLI, on inputs
  the agent controls.
- **Rotate on exposure.** Any key that has been in a plaintext config file, a
  log, a prompt, or a shared transcript is compromised — rotate it, and retain
  the old X25519 entries until every bounty pinned to them is final.
- **Delete decrypted output** once a Verdict is recorded. Plaintext Submissions
  should not survive the cycle that opened them.
- **Least privilege for the host account**: no passwordless `sudo` for the
  agent, no container socket in its group, no instance-metadata access from the
  sandbox.
- **Re-check the isolation after any change to it** — the wrapper, the image,
  the kernel, or a sysctl underneath it. Nothing in the CLI will tell you: a
  sandbox that starts but does not confine runs every command just as well as
  one that does.
- **Keep the sources the boundary.** A Guardian installs any tool freely, but
  only from the public sources the skill names, and only inside the sandbox. A
  tool with no such source is reported to you rather than fetched.
