#!/usr/bin/env python3
"""Deterministic, monitoring-only heartbeat for an Agora Guardian."""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass
from typing import Any, Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


GET_BOUNTY_SELECTOR = "ee8c4bbf"
OPEN_BOUNTY_STATUS = 0
QUICKNET_GENESIS_TIME = 1_692_803_367
QUICKNET_PERIOD_SECONDS = 3

GUARDIAN_HEARTBEAT_QUERY = """
query GuardianHeartbeatCandidates(
  $guardianSettlementSigner: Bytes!
  $guardianRecipientsCommitment: Bytes!
  $now: BigInt!
) {
  bounties(
    where: {
      status: Open
      guardianSettlementSigner: $guardianSettlementSigner
      guardianRecipientsCommitment: $guardianRecipientsCommitment
      submissionDeadline_lte: $now
      settlementTimeoutAt_gt: $now
    }
    orderBy: bountyId
    orderDirection: asc
  ) {
    bountyId
    status
    submissionDeadline
    settlementTimeoutAt
    guardianSettlementSigner
    guardianRecipientsCommitment
  }
}
""".strip()


class HeartbeatError(Exception):
    """A concise, operator-visible heartbeat failure."""


@dataclass(frozen=True)
class Config:
    chain_id: int
    hub_address: str
    rpc_url: str
    subgraph_url: str
    settlement_signer: str
    recipient_commitments: tuple[str, ...]
    timelock_reveal_delay_seconds: int


@dataclass(frozen=True)
class Candidate:
    bounty_id: int
    submission_deadline: int
    settlement_timeout_at: int
    settlement_signer: str
    recipient_commitment: str


JsonPost = Callable[[str, dict[str, Any]], dict[str, Any]]


def _required(env: Mapping[str, str], name: str) -> str:
    value = env.get(name, "").strip()
    if not value:
        raise HeartbeatError(f"missing required configuration: {name}")
    return value


def _parse_uint(value: str, name: str) -> int:
    if not value.isdigit():
        raise HeartbeatError(f"invalid unsigned integer configuration: {name}")
    return int(value)


def _parse_address(value: str, name: str) -> str:
    if not re.fullmatch(r"0x[0-9a-fA-F]{40}", value):
        raise HeartbeatError(f"invalid address configuration: {name}")
    return value.lower()


def _parse_commitment(value: str, name: str) -> str:
    if not re.fullmatch(r"0x[0-9a-fA-F]{64}", value):
        raise HeartbeatError(f"invalid bytes32 configuration: {name}")
    return value.lower()


def _parse_url(value: str, name: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HeartbeatError(f"invalid HTTP URL configuration: {name}")
    return value


def load_config(env: Mapping[str, str]) -> Config:
    current_commitment = _parse_commitment(
        _required(env, "AGORA_GUARDIAN_RECIPIENTS_COMMITMENT"),
        "AGORA_GUARDIAN_RECIPIENTS_COMMITMENT",
    )
    retained_raw = env.get(
        "AGORA_GUARDIAN_RETAINED_RECIPIENTS_COMMITMENTS", ""
    )
    commitments = [current_commitment]
    for raw_commitment in retained_raw.split(","):
        if not raw_commitment.strip():
            continue
        commitment = _parse_commitment(
            raw_commitment.strip(),
            "AGORA_GUARDIAN_RETAINED_RECIPIENTS_COMMITMENTS",
        )
        if commitment not in commitments:
            commitments.append(commitment)

    delay = _parse_uint(
        env.get("AGORA_TIMELOCK_REVEAL_DELAY_SECONDS", "0").strip(),
        "AGORA_TIMELOCK_REVEAL_DELAY_SECONDS",
    )
    chain_id = _parse_uint(
        _required(env, "AGORA_CHAIN_ID"),
        "AGORA_CHAIN_ID",
    )
    if chain_id == 0:
        raise HeartbeatError("AGORA_CHAIN_ID must be greater than zero")

    return Config(
        chain_id=chain_id,
        hub_address=_parse_address(
            _required(env, "AGORA_HUB_ADDRESS"), "AGORA_HUB_ADDRESS"
        ),
        rpc_url=_parse_url(_required(env, "AGORA_RPC_URL"), "AGORA_RPC_URL"),
        subgraph_url=_parse_url(
            _required(env, "AGORA_SUBGRAPH_ENDPOINT"),
            "AGORA_SUBGRAPH_ENDPOINT",
        ),
        settlement_signer=_parse_address(
            _required(env, "AGORA_GUARDIAN_SETTLEMENT_SIGNER"),
            "AGORA_GUARDIAN_SETTLEMENT_SIGNER",
        ),
        recipient_commitments=tuple(commitments),
        timelock_reveal_delay_seconds=delay,
    )


def post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    request = Request(
        url,
        data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        headers={
            "Accept": "application/json",
            "Cache-Control": "no-cache, no-store",
            "Content-Type": "application/json",
            "Pragma": "no-cache",
            "User-Agent": "agora-guardian-heartbeat/1",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=20) as response:
            decoded = json.loads(response.read())
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, UnicodeError):
        raise HeartbeatError("HTTP provider request failed") from None
    if not isinstance(decoded, dict):
        raise HeartbeatError("HTTP provider returned a malformed response")
    return decoded


def _rpc(
    config: Config,
    method: str,
    params: list[Any],
    http_post: JsonPost,
) -> Any:
    response = http_post(
        config.rpc_url,
        {"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
    )
    if response.get("error") is not None or "result" not in response:
        raise HeartbeatError(f"RPC method failed: {method}")
    return response["result"]


def _hex_uint(value: Any, field: str) -> int:
    if not isinstance(value, str) or not re.fullmatch(r"0x[0-9a-fA-F]+", value):
        raise HeartbeatError(f"RPC returned malformed {field}")
    return int(value, 16)


def _decimal_uint(value: Any, field: str) -> int:
    if not isinstance(value, str) or not value.isdigit():
        raise HeartbeatError(f"subgraph returned malformed {field}")
    return int(value)


def _finalized_timestamp(config: Config, http_post: JsonPost) -> int:
    chain_id = _hex_uint(_rpc(config, "eth_chainId", [], http_post), "chain id")
    if chain_id != config.chain_id:
        raise HeartbeatError(
            f"wrong RPC chain: expected {config.chain_id}, received {chain_id}"
        )

    block = _rpc(
        config,
        "eth_getBlockByNumber",
        ["finalized", False],
        http_post,
    )
    if not isinstance(block, dict):
        raise HeartbeatError("RPC returned malformed finalized block")
    _hex_uint(block.get("number"), "finalized block number")
    return _hex_uint(block.get("timestamp"), "finalized block timestamp")


def _subgraph_candidates(
    config: Config,
    commitment: str,
    now: int,
    http_post: JsonPost,
) -> list[Candidate]:
    response = http_post(
        config.subgraph_url,
        {
            "query": GUARDIAN_HEARTBEAT_QUERY,
            "variables": {
                "guardianSettlementSigner": config.settlement_signer,
                "guardianRecipientsCommitment": commitment,
                "now": str(now),
            },
        },
    )
    if response.get("errors"):
        raise HeartbeatError("subgraph query failed")
    data = response.get("data")
    bounties = data.get("bounties") if isinstance(data, dict) else None
    if not isinstance(bounties, list):
        raise HeartbeatError("subgraph returned malformed bounty data")

    candidates: list[Candidate] = []
    for record in bounties:
        if not isinstance(record, dict):
            raise HeartbeatError("subgraph returned malformed bounty record")
        bounty_id = _decimal_uint(record.get("bountyId"), "bountyId")
        deadline = _decimal_uint(
            record.get("submissionDeadline"), "submissionDeadline"
        )
        timeout = _decimal_uint(
            record.get("settlementTimeoutAt"), "settlementTimeoutAt"
        )
        signer = _parse_address(
            str(record.get("guardianSettlementSigner", "")),
            "subgraph guardianSettlementSigner",
        )
        record_commitment = _parse_commitment(
            str(record.get("guardianRecipientsCommitment", "")),
            "subgraph guardianRecipientsCommitment",
        )
        if (
            record.get("status") != "Open"
            or signer != config.settlement_signer
            or record_commitment != commitment
            or not deadline <= now < timeout
        ):
            raise HeartbeatError("subgraph returned a bounty outside the query filter")
        candidates.append(
            Candidate(
                bounty_id=bounty_id,
                submission_deadline=deadline,
                settlement_timeout_at=timeout,
                settlement_signer=signer,
                recipient_commitment=record_commitment,
            )
        )
    return candidates


def _abi_word_uint(word: str, field: str) -> int:
    if not re.fullmatch(r"[0-9a-fA-F]{64}", word):
        raise HeartbeatError(f"AgoraHub returned malformed {field}")
    return int(word, 16)


def _abi_word_address(word: str, field: str) -> str:
    if not re.fullmatch(r"0{24}[0-9a-fA-F]{40}", word):
        raise HeartbeatError(f"AgoraHub returned malformed {field}")
    return f"0x{word[-40:]}".lower()


def _finalized_bounty(
    config: Config,
    bounty_id: int,
    http_post: JsonPost,
) -> tuple[int, int, int, str]:
    calldata = f"0x{GET_BOUNTY_SELECTOR}{bounty_id:064x}"
    encoded = _rpc(
        config,
        "eth_call",
        [{"to": config.hub_address, "data": calldata}, "finalized"],
        http_post,
    )
    if not isinstance(encoded, str) or not re.fullmatch(
        r"0x[0-9a-fA-F]{640}", encoded
    ):
        raise HeartbeatError("AgoraHub returned malformed getBounty data")
    words = [encoded[index : index + 64] for index in range(2, len(encoded), 64)]

    _abi_word_address(words[0], "poster")
    status = _abi_word_uint(words[1], "status")
    deadline = _abi_word_uint(words[2], "submissionDeadline")
    timeout = _abi_word_uint(words[3], "settlementTimeoutAt")
    signer = _abi_word_address(words[4], "guardianSettlementSigner")
    _abi_word_address(words[5], "treasuryRecipient")
    _abi_word_address(words[6], "guardianFeeRecipient")
    _abi_word_uint(words[7], "treasuryFeeBps")
    _abi_word_uint(words[8], "guardianFeeBps")
    _abi_word_uint(words[9], "escrowAmount")
    return status, deadline, timeout, signer


def _timelock_release_at(deadline: int, reveal_delay: int) -> int:
    not_before = deadline + reveal_delay
    if not_before <= QUICKNET_GENESIS_TIME:
        return QUICKNET_GENESIS_TIME
    elapsed = not_before - QUICKNET_GENESIS_TIME
    rounds = (elapsed + QUICKNET_PERIOD_SECONDS - 1) // QUICKNET_PERIOD_SECONDS
    return QUICKNET_GENESIS_TIME + rounds * QUICKNET_PERIOD_SECONDS


def run_heartbeat(config: Config, http_post: JsonPost = post_json) -> list[dict[str, str]]:
    now = _finalized_timestamp(config, http_post)
    candidates_by_id: dict[int, Candidate] = {}
    for commitment in config.recipient_commitments:
        for candidate in _subgraph_candidates(config, commitment, now, http_post):
            existing = candidates_by_id.get(candidate.bounty_id)
            if existing is not None and existing != candidate:
                raise HeartbeatError("subgraph returned conflicting bounty records")
            candidates_by_id[candidate.bounty_id] = candidate

    actionable: list[dict[str, str]] = []
    for bounty_id in sorted(candidates_by_id):
        status, deadline, timeout, signer = _finalized_bounty(
            config, bounty_id, http_post
        )
        if (
            status == OPEN_BOUNTY_STATUS
            and signer == config.settlement_signer
            and deadline <= now < timeout
            and now
            >= _timelock_release_at(
                deadline, config.timelock_reveal_delay_seconds
            )
        ):
            actionable.append(
                {"bounty_id": str(bounty_id), "next_action": "evaluation_ready"}
            )
    return actionable


def main() -> int:
    try:
        config = load_config(os.environ)
        actionable = run_heartbeat(config)
    except HeartbeatError as error:
        sys.stderr.write(f"agora guardian heartbeat failed: {error}\n")
        return 1

    if actionable:
        sys.stdout.write(json.dumps(actionable, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
