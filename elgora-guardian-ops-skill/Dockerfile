# Elgora Guardian sandbox image -- a suggestion, not a requirement.
#
# Your harness ships its own sandbox image; try that first. This one covers
# what challenges usually ask for, so a Guardian using it pays fewer per-cycle
# installs. Build it, extend it, or build something else entirely. Everything a
# particular Submission needs is still installed per bounty, inside the
# sandbox, from the public sources the judging skill names.
#
#   docker build -t elgora-sandbox:1 - < Dockerfile
#   docker image inspect elgora-sandbox:1 --format '{{index .RepoDigests 0}}'
#
# Record that digest and run the wrapper against it with --pull never, so the
# image you checked is the image that runs. Builds on amd64 and arm64.
#
# LABEL version below is the manifest entry; bump it with any change here.

FROM debian:12-slim

LABEL org.elgora.sandbox.version="1.0.0"

ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8

RUN apt-get update \
  && apt-get install --yes --no-install-recommends \
    bash \
    bzip2 \
    build-essential \
    ca-certificates \
    coreutils \
    curl \
    git \
    gzip \
    jq \
    procps \
    python3 \
    python3-venv \
    python3-pip \
    r-base-core \
    tar \
    unzip \
    xz-utils \
    zip \
    zstd \
  && rm -rf /var/lib/apt/lists/*

# bash, not sh: the network probes in check-sandbox.sh use /dev/tcp, which
# dash does not implement. A probe running under dash reports "no network"
# whether or not the sandbox has one.
SHELL ["/bin/bash", "-c"]

WORKDIR /work
