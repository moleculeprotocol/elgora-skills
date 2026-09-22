#!/usr/bin/env bash
# Elgora Guardian sandbox confinement probes.
#
# Usage: check-sandbox.sh [path-to-wrapper]
#   The wrapper defaults to $ELGORA_SANDBOX_RUN, then to elgora-sandbox-run on
#   PATH. It is called as: <wrapper> <agent|submission> <work_dir> <cmd>...
#
# Prints one line per property:   <tier> <property> <pass|fail|unmeasured> <detail>
# Exit: 0 every Tier 1 property measured and passing
#       1 a Tier 1 property failed, or could not be measured
#       2 the wrapper could not be run at all
#
# An unmeasured property is never reported as a pass. Every negative assertion
# here is paired with a positive control that must succeed first: a probe whose
# mechanism is broken reports unmeasured rather than silently confirming what
# it never tested.
#
# Deliberately no pipeline around the body. Wrapping this in `{ ... } | tee`
# runs it in a subshell, the result flags never reach the parent, and the
# script exits 0 while printing failures. Redirect the whole invocation
# instead: check-sandbox.sh > results.txt 2>&1

set -uo pipefail

WRAPPER="${1:-${ELGORA_SANDBOX_RUN:-elgora-sandbox-run}}"
tier1_bad=0

work_dir="$(mktemp -d)"
canary_dir="$(mktemp -d)"
canary_file="$canary_dir/elgora-probe-canary"
canary_token="elgora-canary-$$-$(date +%s)"
printf '%s\n' "$canary_token" > "$canary_file"
cleanup() { rm -rf "$work_dir" "$canary_dir"; }
trap cleanup EXIT

report() { printf '%s %s %s %s\n' "$1" "$2" "$3" "$4"; }

# Tier 1 is what decides whether this host judges at all, so an unmeasured
# Tier 1 property counts against it exactly as a failure does.
record() {
  report "$@"
  if [ "$1" = "TIER1" ] && [ "$3" != "pass" ]; then tier1_bad=1; fi
}

run_in() { # run_in <agent|submission> <command...>
  local mode="$1"; shift
  "$WRAPPER" "$mode" "$work_dir" "$@" 2>&1
}

if ! command -v "$WRAPPER" >/dev/null 2>&1 && [ ! -x "$WRAPPER" ]; then
  report BLOCKED wrapper fail "not executable: $WRAPPER"
  exit 2
fi
if ! run_in agent /bin/bash -c 'exit 0' >/dev/null 2>&1; then
  report BLOCKED wrapper fail "a trivial agent call did not succeed"
  exit 2
fi

# --- Tier 1 -----------------------------------------------------------------

# Keys absent. Checked in both call kinds: a wrapper that clears the
# environment for one and not the other is the common mistake.
for mode in agent submission; do
  leaked="$(run_in "$mode" /bin/bash -c \
    'env | grep -c -E "^(ELGORA_GUARDIAN_|.*(API_KEY|TOKEN|SECRET|PRIVATE|MNEMONIC))" || true')"
  leaked="$(printf '%s' "$leaked" | tr -dc '0-9')"
  if [ -z "$leaked" ]; then
    record TIER1 "keys-absent($mode)" unmeasured "could not enumerate the environment"
  elif [ "$leaked" = "0" ]; then
    record TIER1 "keys-absent($mode)" pass "no key-shaped variable inside"
  else
    record TIER1 "keys-absent($mode)" fail "$leaked key-shaped variables inside"
  fi
done

# Secrets unreachable. Positive control first: the host really did write a
# canary that a process outside the sandbox can read. Probing with a file the
# image also ships (/etc/shadow is the usual mistake) proves nothing.
if ! grep -q "$canary_token" "$canary_file" 2>/dev/null; then
  record TIER1 secrets-unreachable unmeasured "canary unreadable on the host; probe is broken"
else
  seen="$(run_in submission /bin/bash -c "cat '$canary_file' 2>/dev/null || true")"
  if printf '%s' "$seen" | grep -q "$canary_token"; then
    record TIER1 secrets-unreachable fail "read a host file outside the bind mount"
  else
    record TIER1 secrets-unreachable pass "host canary outside the bind is unreadable"
  fi
fi

# No host control interface.
found="$(run_in submission /bin/bash -c '
  for p in /var/run/docker.sock /run/docker.sock /var/run/podman/podman.sock /run/containerd; do
    [ -e "$p" ] && printf "%s " "$p"
  done
  true')"
found="$(printf '%s' "$found" | tr -d '[:space:]')"
if [ -n "$found" ]; then
  record TIER1 no-host-control fail "control interface visible inside"
else
  record TIER1 no-host-control pass "no container socket or runtime endpoint inside"
fi

# Results land. This is what replaces prescribing a uid/gid flag: no value is
# correct across runtimes, so assert the outcome instead. stderr is kept --
# a silenced Permission denied is what makes this failure look like a
# Submission that produced nothing.
marker="elgora-write-$$"
write_err="$(run_in submission /bin/bash -c "printf '%s\n' '$marker' > /work/elgora-write-probe" 2>&1)"
landed="$work_dir/elgora-write-probe"
if [ ! -f "$landed" ]; then
  record TIER1 results-land fail "nothing arrived in the bind mount: ${write_err:-no stderr}"
elif [ ! -s "$landed" ]; then
  record TIER1 results-land fail "file arrived empty: ${write_err:-no stderr}"
elif ! grep -q "$marker" "$landed"; then
  record TIER1 results-land fail "file arrived with unexpected contents"
else
  owner="$(stat -c '%u' "$landed" 2>/dev/null || stat -f '%u' "$landed" 2>/dev/null)"
  if [ "$owner" = "$(id -u)" ]; then
    record TIER1 results-land pass "written from inside, owned by uid $owner on the host"
  else
    record TIER1 results-land fail "owned by uid $owner on the host, not $(id -u)"
  fi
fi

# Bounded wall clock. Only the wrapper can enforce this; if it does not, say
# so rather than scoring it either way.
start="$(date +%s)"
run_in submission /bin/bash -c 'sleep 120' >/dev/null 2>&1
elapsed=$(( $(date +%s) - start ))
if [ "$elapsed" -lt 115 ]; then
  record TIER1 wall-clock pass "a 120s command was stopped after ${elapsed}s"
else
  record TIER1 wall-clock unmeasured "no timeout observed in ${elapsed}s; the wrapper must enforce one"
fi

# --- Tier 2 -----------------------------------------------------------------

# Network off during submission. The positive control is the whole point: the
# identical check must succeed in an agent call. Without it a probe using a
# shell builtin the image lacks reports "no network" without ever testing it.
net_probe='
  if (exec 3<>/dev/tcp/1.1.1.1/53) 2>/dev/null; then exec 3>&-; echo REACHED; fi
  getent hosts deb.debian.org >/dev/null 2>&1 && echo RESOLVED
  true'
control="$(run_in agent /bin/bash -c "$net_probe")"
if ! printf '%s' "$control" | grep -q -E 'REACHED|RESOLVED'; then
  report TIER2 network-off unmeasured "positive control failed in an agent call; probe or host network is broken"
else
  offline="$(run_in submission /bin/bash -c "$net_probe")"
  if printf '%s' "$offline" | grep -q -E 'REACHED|RESOLVED'; then
    report TIER2 network-off fail "reached the network while running Submission code"
  else
    report TIER2 network-off pass "control reached the network, submission call did not"
  fi
fi

# Mount namespace.
home_listing="$(run_in submission /bin/bash -c 'ls -A /home 2>/dev/null | head -5; true')"
if [ -n "$(printf '%s' "$home_listing" | tr -d '[:space:]')" ]; then
  report TIER2 mount-namespace fail "host /home is visible inside"
else
  report TIER2 mount-namespace pass "/home is empty inside"
fi

# Resource bounds, read from the kernel's own accounting rather than inferred
# from behaviour. A probe that allocates or forks to test a bound tends to
# lose its own output once the bound is hit.
bounds="$(run_in submission /bin/bash -c '
  for f in memory.max pids.max cpu.max; do
    printf "%s=%s " "$f" "$(cat /sys/fs/cgroup/$f 2>/dev/null || echo unreadable)"
  done
  true')"
case "$bounds" in
  *unreadable*|"")
    report TIER2 resource-bounds unmeasured "cgroup accounting not readable inside: $bounds" ;;
  *"memory.max=max"*|*"pids.max=max"*)
    report TIER2 resource-bounds fail "a bound is unset: $bounds" ;;
  *)
    report TIER2 resource-bounds pass "$bounds" ;;
esac

# Capabilities.
capeff="$(run_in submission /bin/bash -c 'grep ^CapEff /proc/self/status 2>/dev/null | tr -d "[:space:]"; true')"
case "$capeff" in
  "")                report TIER2 capabilities unmeasured "CapEff not readable inside" ;;
  *0000000000000000) report TIER2 capabilities pass "CapEff is empty" ;;
  *)                 report TIER2 capabilities fail "$capeff" ;;
esac

# --- Tier 3 -----------------------------------------------------------------

uidmap="$(run_in submission /bin/bash -c 'cat /proc/self/uid_map 2>/dev/null | tr -s " "; true')"
if [ -z "$uidmap" ]; then
  report TIER3 user-namespace unmeasured "uid_map not readable inside"
else
  report TIER3 user-namespace pass "uid_map:$uidmap"
fi

if [ "$tier1_bad" -ne 0 ]; then
  printf 'RESULT fail a Tier 1 property failed or could not be measured\n'
  exit 1
fi
printf 'RESULT pass every Tier 1 property measured and passing\n'
exit 0
