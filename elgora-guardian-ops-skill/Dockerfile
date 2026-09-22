# Elgora Guardian sandbox image.
#
# Build this as-is. The contents are a protocol-level choice, not a per-host
# one: they decide which bounties judge without a per-cycle install, so a
# Guardian that drops a tool here refuses work another Guardian accepts.
# Everything a particular Submission needs is still installed per bounty,
# inside the sandbox, from the public sources the judging skill names.
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
