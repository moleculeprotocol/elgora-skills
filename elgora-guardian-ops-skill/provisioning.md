# Provisioning a Guardian host

For the operator who builds the machine, not the agent that runs on it. The
agent never installs any of this — if something here is missing, the agent
reports it and judges what it can.

Verify every step with one command. It is the acceptance test for this whole
file, and the only thing the agent reads:

```sh
elgora-cli preflight --cache /var/lib/elgora/preflight.json --max-age 21600
```

- `modes.inspect: true` — the host can open, vet, read and recompute. This is
  enough to judge most bounties.
- `modes.execute_untrusted: true` — the sandbox was **proven** to confine.
  Required only for challenges whose criteria need the Solver's own code to run.
- `skipped` or `inconclusive` never counts as confinement. Fix it or accept that
  the host judges in `inspect` mode only.

## Baseline, every host

- **Node 24.x** (`>=24 <25`). Match the CLI's `engines` range exactly; a version
  outside it fails preflight.
- **`@elgora/cli`**, installed globally, updated when the skills are.
- **An archive lister** — any one of `unzip`, `zipinfo`, `bsdtar`, `7z`,
  `busybox`, or Python 3 with `zipfile`. Install one; do not install all.
- **`tar`** and **`sha256sum`** (or `shasum -a 256` on macOS).
- **A secret manager**, with the signing key and the X25519 keys held
  separately and injected per process, never in a shell profile or a config file
  on disk.
- **Writable state directory** (for example `/var/lib/elgora/`) that survives a
  restart, for the preflight cache and the per-bounty records. Without it every
  cycle starts over.

## Sandbox — Linux (AWS EC2)

Amazon Linux 2023 or Ubuntu 24.04. Rootless, one of:

- **Podman ≥ 4.9** — `dnf install -y podman` / `apt install -y podman`.
  - Run each evaluation as `podman run --rm --network none --read-only
    --user 1000:1000 --memory 2g --pids-limit 256 --cap-drop ALL
    --security-opt no-new-privileges -v <workdir>:/work:rw -w /work <image>`.
  - `--network none` is the netns; `--read-only` plus a single bind is the
    mount namespace. Both are needed — one alone fails preflight.
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
      and preflight reports `sandbox_runs: fail`.
- **Put a network client in the sandbox image** — `curl`, `wget`, or `python3`.
  Without one, preflight cannot attempt a connection and reports
  `network_blocked: inconclusive`, which does not unlock execution.
- **Resource bounds** belong on the runner, not on the agent: memory, pids, CPU
  and a wall-clock timeout, set before anything is extracted. A systemd slice or
  the container's own flags are both fine.

Then export the wrapper for the agent, using `{workdir}` where the work
directory is bound, and naming its path inside the sandbox if it differs:

```sh
export ELGORA_GUARDIAN_SANDBOX_COMMAND="bwrap --unshare-all --die-with-parent --ro-bind /usr /usr --ro-bind /lib /lib --ro-bind /lib64 /lib64 --ro-bind /bin /bin --proc /proc --dev /dev --bind {workdir} /work --chdir /work --clearenv --"
export ELGORA_GUARDIAN_SANDBOX_WORKDIR=/work
```

## Sandbox — macOS hosts

macOS has no user namespaces and no bubblewrap. Two honest options:

- **A Linux VM, and the Linux setup above inside it.** Podman machine (`podman
  machine init --cpus 4 --memory 4096`), Lima, or Colima. This is the supported
  path; the agent's wrapper then invokes `podman` as above.
- **`sandbox-exec` with an SBPL profile** — present on every macOS, formally
  deprecated, no longer documented by Apple. A `(deny default)` profile with
  `(deny network*)` and a single `(allow file-read* file-write*
  (subpath "<workdir>"))` does satisfy preflight. Treat it as a stopgap and
  re-run preflight after every macOS update, because nothing guarantees the
  interface across them.

Do not run execution bounties on a Mac host with neither. `inspect` mode still
works and still judges most bounties — that is the correct outcome, not a
degraded one.

## Agent harness — OpenClaw and Hermes

Both ship their own sandboxing. Use it if, and only if, `elgora-cli preflight`
confirms it confines; a built-in "sandbox mode" that sets a working directory
and resource limits is not a sandbox for this purpose. Where the harness names
its settings differently, map the requirement rather than the name.

- **Point the harness's isolation at the wrapper above**, or set
  `ELGORA_GUARDIAN_SANDBOX_COMMAND` to the harness's own runner and let
  preflight decide. Either way the proof is the preflight output, not the
  setting's name.
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

- **Alert on `preflight.blocked`**, and on `execute_untrusted` flipping from
  true to false. The second is a silent capability loss that otherwise shows up
  only as bounties nobody judged.
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
  the secret directory never bound. Confirm with `sandbox_filesystem_confined`
  in preflight.
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
- **Re-run preflight after any change to isolation.** The cached result
  invalidates itself when the wrapper command changes, but not when the kernel,
  the image, or a sysctl underneath it does — so re-run it after those by hand.
