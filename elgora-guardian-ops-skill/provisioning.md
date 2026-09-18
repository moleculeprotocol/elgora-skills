# Provisioning a Guardian host

For the operator who builds the machine, not the agent that runs on it. The
agent never installs any of this — if something here is missing, the agent
reports it and judges what it can.

Two halves, and only the first has a command:

```sh
elgora-cli guardian:check-tools
```

- Exits zero once the host has a supported Node and the four required tools. It
  reports the rest of the allowlist as advisory, and names the Debian package
  for anything missing.
- It says nothing about the sandbox. No probe shipped in a CLI can establish
  isolation in general, so the second half of this file is yours to verify by
  building it correctly — not by reading a green check.

## Baseline, every host

- **Node 24.x** (`>=24 <25`). Match the CLI's `engines` range exactly; a version
  outside it fails `guardian:check-tools`.
- **`@elgora/cli`**, installed globally, updated when the skills are.
- **`unzip`, `zipinfo`, `tar`, `sha256sum`** — the four `guardian:check-tools` requires
  (`shasum -a 256` on macOS). A Submission is opened, listed and hash-verified
  before any of it is read.
- **The rest of the allowlist, in the sandbox image.** The agent installs from
  it by name as a challenge needs it — archive tools, `curl`/`wget`/`git`, `jq`,
  `python3`, `node`, `Rscript`, `ruby`, `perl`, and the
  `gcc`/`clang`/`gfortran`/`make`/`cmake`/`cargo`/`go`/`javac` family. Baking
  the common ones into the image saves an install per cycle; it is not required.
  The full list ships in `SKILL.md` beside this file.
- **Package-manager access from inside the sandbox**, to the official Debian and
  Ubuntu archives and the language registries (PyPI, CRAN, npmjs.com,
  crates.io). Without it the agent cannot supply what a challenge names, and
  bounties get refused over a missing compiler.
- **A secret manager**, with the signing key and the X25519 keys held
  separately and injected per process, never in a shell profile or a config file
  on disk.
- **Writable state directory** (for example `/var/lib/elgora/`) that survives a
  restart, for the recorded preflight result and the per-bounty records.
  Without it every cycle starts over.

## Sandbox — Linux (AWS EC2)

Amazon Linux 2023 or Ubuntu 24.04. Rootless, one of:

- **Podman ≥ 4.9** — `dnf install -y podman` / `apt install -y podman`.
  - Run each evaluation as `podman run --rm --network none --read-only
    --user 1000:1000 --memory 2g --pids-limit 256 --cap-drop ALL
    --security-opt no-new-privileges -v <workdir>:/work:rw -w /work <image>`.
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
    what keeps the Guardian's keys out.
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
  network fails, that exceeding a bound is stopped with cleanup still
  succeeding, and that a timeout or crash stops visibly without falling back to
  the host.
- **Resource bounds** belong on the runner, not on the agent: memory, pids, CPU
  and a wall-clock timeout, set before anything is extracted. A systemd slice or
  the container's own flags are both fine.

Then give the agent one wrapper to invoke, so the isolation is a property of the
host rather than a thing the agent assembles per bounty:

```sh
# /usr/local/bin/elgora-sandbox-run <work_dir> <command> [args...]
#!/bin/sh
set -eu
work_dir="$1"; shift
exec bwrap --unshare-all --die-with-parent --new-session \
  --ro-bind /usr /usr --ro-bind /lib /lib --ro-bind /lib64 /lib64 \
  --ro-bind /bin /bin --proc /proc --dev /dev \
  --bind "$work_dir" /work --chdir /work --clearenv \
  -- "$@"
```

Point the harness at that one path. The agent never edits it, and a change to
isolation is a change to one file you own.

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
- **Load both skills at every cycle** — `elgora-guardian-skill` and
  `elgora-guardian-ops-skill`. Loading only the first silently drops preflight,
  cycle state and the retry rules. Pin the skill versions in the scheduler
  prompt and update it when they change.
- **Give the judging cycle its own short-lived session.** One session per cycle,
  started fresh, ended when the cycle ends.
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
- **Let the cycle's bounty selector skip** bounties past `judging_deadline_at`
  and bounties marked blocked, so a refused bounty is not re-picked every 30
  minutes until it times out.

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
  the kernel, or a sysctl underneath it. `guardian:check-tools` will not tell you:
  it checks tooling, and a clean tooling result on a broken sandbox looks exactly like a
  clean one on a good sandbox.
- **Keep the allowlist the boundary.** A Guardian installs from it freely; a
  request for anything else is reported to you. Widening it is your decision,
  and it belongs in the registry the skill renders from, not in a local note.
