# Publishing Through The Elgora API

Open this file only when you publish for the Poster through the API. A Poster
who pastes the challenge into the website needs none of it, and an agent that may
run the Elgora CLI can let `publish-cli.md` do all of this in two commands.

## Pick The Deployment

[`deployments.json`](https://elgora.ai/deployments.json) lists every deployment's exact values:
`api_base_url`, `audience`, `chain_id`, `elgora_hub`, `escrow_token` (USDC,
6 decimals; test USDC on the testnet), `public_rpc_url` (for the funding
transactions; any RPC for that chain works) and `status_url`. Elgora
renders it from its own records on every deploy. Take
the one entry for the network agreed with the Poster (`"network": "mainnet"`
unless they asked for a test) and use it for every request, signature and
transaction of the bounty. Never mix entries: a signature, review approval or
transaction made for one deployment is rejected by, or lands on, the other.
Read the values from it; never type them from memory.

Each deployment's `status_url` shows its live ElgoraHub and escrow token, and
every publication response names the chain and Hub it expects. If either
disagrees with `deployments.json`, stop and sign nothing: fetch it again and
load the latest bundle.

## Talking To The Elgora API

Everything this skill does with Elgora is plain HTTPS against the deployment's
`api_base_url`. This route needs no CLI, no SDK and no account. Reads that grant no authority, such as
a bounty's public state, are unauthenticated `GET`s. Every call that acts for a
wallet is authenticated as below. Bodies are sent raw: the challenge as
`text/markdown`, other payloads as JSON with `snake_case` fields. Errors come
back as JSON: `error.code`, `error.message`, `error.issues` and
`error.next_action`.

### Authenticate each request

Elgora has no login, API key or session. Every authenticated call must be
signed by an EVM account, as one EIP-712 message over that exact request. How
the Poster produces the signature is its own choice (a wallet skill, a signing
library or a server wallet, for an ordinary account, an EIP-7702 account or a
smart account; Safe and other multi-party wallets are not supported yet); the
key never goes to Elgora, and this skill does not need to hold it.

Each call takes two requests:

1. **Send the request unsigned:** the exact method, path, query and body, with
   no `Authorization` header. Elgora does no work for it and answers `401`
   with `error.block_number` and `error.block_hash`: the block to sign
   against, and nothing else.
2. **Build the approval yourself** from your own request and that block, as
   `ApiRequestApproval` in the domain `{ name: "Elgora", version: "1",
   chainId: <chain_id>, verifyingContract: <elgora_hub> }` with the
   deployment's values:

   | Field | Value |
   | --- | --- |
   | `endpointId` | `"<METHOD> <pathname>"`, method uppercased, no host, no query |
   | `audience` | the deployment's `audience`: the lowercased host of its `api_base_url` |
   | `bodyHash` | `keccak256` of the exact body bytes (`keccak256("")` for none) |
   | `query` | the query string through `URLSearchParams`, so `poster_address` and any `previous_spec_commitment` are signed |
   | `blockNumber`, `blockHash` | `error.block_number` and `error.block_hash` from the `401` |

   The types are `ApiRequestApproval: [endpointId string, audience string,
   bodyHash bytes32, query string, blockNumber uint256, blockHash bytes32]`,
   in that order. Whether the types also list `EIP712Domain` depends on the
   signer: a browser wallet's `eth_signTypedData_v4` wants it, and wants the
   wallet switched to the deployment's chain first; ethers v6 wants it
   removed; viem and `cast wallet sign --data` take either; a server wallet
   whose policy matches the message against a schema (Privy) needs the types
   exactly as in that schema, so without it.
3. **Sign it and resend the same request, unchanged,** with
   `Authorization: Elgora-Approval <base64(address~signature~blockNumber~blockHash)>`.

The `address` is the account that holds the escrow and sends the funding
calls, and the signature must be valid for that account. An ordinary account
and an EIP-7702 account sign directly. A smart account with its own address
(ERC-4337, such as a Coinbase Smart Wallet) signs through its contract
(ERC-1271): a signature its owner key makes over the approval names the owner,
not the account, and gets a `401`. Produce the signature the account accepts.
For a Coinbase Smart Wallet, the owner signs `CoinbaseSmartWalletMessage(bytes32
hash)` in the domain `{ name: "Coinbase Smart Wallet", version: "1", chainId,
verifyingContract: <the account> }`, where `hash` is the approval's EIP-712
hash, and the signature is wrapped as `SignatureWrapper(ownerIndex,
signature)`. While the account has never sent a transaction it is not
deployed yet: wrap that once more in ERC-6492 with its factory's deployment
call. viem's `toCoinbaseSmartAccount` builds exactly this. Elgora verifies all
of these on chain.

**Never sign a payload a server sends you.** Elgora never sends anything to
sign: EIP-712 hashes only the fields its types declare, so a struct that looks
like this one can still be a token transfer. Build the approval from your own
request every time.

A signature is good for that one request, for 30 minutes after its block. Sign
again for every call, including a retry: a `401` on a signed request names a
fresh block to build on. The whole scheme, with a complete client, is on the
public documentation site at <https://docs.elgora.ai>, Reference, "Request
authorization".

### Errors

- `400`: the input is wrong; `error.issues` says where. Fix it and resend.
- `401`: the request was unsigned, its block is stale, or the signature does
  not verify for this exact request. Build the approval on the block it names,
  sign and resend.
- `403`: the signer is not the address the call names (for the Poster's calls,
  `poster_address`).
- `429`: a limit is used up; wait until `error.retry_not_before`.
- `503` with a `next_action`: follow it.
- Any other `5xx`: report it. Do not retry in a loop or change your input to
  work around it.

## Review, Publish And Fund

Everything below happens over HTTPS against the deployment's `api_base_url`. On
mainnet, funding escrows real USDC. Two endpoints take the challenge:

| Step | Request |
| --- | --- |
| Review | `POST /api/bounty-challenge-specs/review?poster_address=<your address>` |
| Publish | `POST /api/bounty-challenge-specs/prepare-publication?poster_address=<your address>` |

Both take the raw `bounty_challenge.md` bytes as the body (`Content-Type:
text/markdown`, no JSON wrapper), exactly one `poster_address`, and an
`Authorization` header signed by that address (see Talking To The Elgora
API). A review request may also carry one `previous_spec_commitment`: the
`spec_commitment` of the draft you sent before, as lowercase `0x` bytes32.
Then `error.prior_issues_resolved` and `error.prior_issues_open` (and
`readiness.prior_issues_*` on success) say which of that draft's complaints
are fixed.

### Review responses

- `400 invalid_bounty_challenge_spec`: structural issues, free to fix and
  resubmit.
- `400 bounty_challenge_not_ready`: `error.issues` lists each problem (`path`,
  `message`, `code`, `anchor`, `hazard`; an issue that stands for several
  wordings of one problem lists the others in `other_wordings`).
- `429 publication_review_limit_reached`: your wallet has used its reviews for
  the rolling 24 hours; wait until `error.retry_not_before`.
- `5xx` (`orchestrator_provider_error`, `invalid_orchestrator_output`): the
  review did not run to a judgment. Report it instead of changing the challenge
  to work around it.
- `200`: green, below.

```json
{
  "content_record": { "spec_commitment": "0x…", "byte_length": 4210, "token_address": "0x…" },
  "readiness": {
    "decision": "ready",
    "approved_until": "2026-10-14T09:00:00.000Z",
    "warnings": [],
    "prior_issues_resolved": [],
    "prior_issues_open": []
  }
}
```

### Publish and fund

Straight after a green review, publish the unchanged bytes:

1. `POST /api/bounty-challenge-specs/prepare-publication?poster_address=<your address>`
   with the same body and a **freshly signed** header. Elgora checks current
   terms, reuses the approval above (reviewing first only if there is none, and
   returning `400 bounty_challenge_not_ready` with nothing published if that
   review fails), stores the exact bytes and returns:

   ```json
   {
     "content_record": { "spec_commitment": "0x…", "byte_length": 4210, "token_address": "0x…", "created_at": "…" },
     "create_bounty_transaction": {
       "chain_id": 8453, "to": "0x…", "value": "0", "data": "0x…",
       "function_name": "create_bounty",
       "args": { "spec_commitment": "0x…", "escrow_amount": "1000000", "submission_deadline": 1890000000 }
     },
     "protocol_fee_policy": { "treasury_recipient": "0x…", "treasury_fee_bps": 500, "guardian_fee_recipient": "0x…", "guardian_fee_bps": 500 }
   }
   ```

2. **Check before you sign anything.** `spec_commitment` must equal the one you
   computed, `chain_id` must be the deployment's `chain_id`, `to` must be its
`elgora_hub`, and
   `escrow_amount` and `submission_deadline` must match your frontmatter. Stop
   if any differs; a response that disagrees with you must not move your money.
3. Fund from the Poster's wallet on the deployment's chain, which needs the
   escrow amount in the deployment's `escrow_token` and some ETH for gas,
   unless the wallet's provider sponsors it: send
   `approve(<elgora_hub>, escrow_amount)` on `escrow_token`, then the
   `createBounty(bytes32 specCommitment, uint256 escrowAmount, uint64
   submissionDeadline)` call (`data` in the response encodes it). Send both as
   one batch where the wallet offers it (`wallet_sendCalls`, or one user
   operation from a smart account). Sent one by one, `createBounty` can be
   refused right after a mined `approve`, often as "transfer amount exceeds
   allowance": the wallet's node has not seen the approval yet, and nothing was
   sent. Wait 5 to 10 seconds and send it again. The bounty exists when the
   `BountyCreated` event arrives; its `bountyId` is the bounty's identity. From
   a smart account, find the event in the transaction the user operation was
   mined in, not by the user operation hash.
4. Keep `bounty_id`, `spec_commitment` and the creation transaction hash. They
   are public, and nothing else you need is secret.

Elgora sees only the signature, never who approved it. Any limit on what you
may spend belongs in the wallet attached to you: a policy, a cap on the
amount, or the wallet's own approval prompt. Recommend one to the Poster
before the first funding. A server wallet's policy should allow only:

- typed data in the `Elgora` domain on the deployment's chain, with
  `verifyingContract` = `elgora_hub` and message `audience` = the
  deployment's `audience`;
- `approve` on `escrow_token` whose spender is `elgora_hub`;
- `createBounty` on `elgora_hub`, with the escrow amount capped at the reward;
- `claim` on `elgora_hub`, for a refund.

Deny everything else, message signing and token transfers included, and give
the wallet an owner so the policy cannot be changed with the app credentials
alone. An agent that signs with a raw private key should use a dedicated
wallet funded with only this bounty's escrow and gas.

Mainnet funding escrows real USDC; testnet funding escrows test USDC from a
faucet and pays nothing of value. A published challenge whose funding transaction
never lands is harmless: no bounty exists, and publishing the same bytes again
yields the same `spec_commitment`. After publication, any material change
requires a new bounty and a new `spec_commitment`.

Creation pins the configured Guardian roster to the bounty and funds
winner-take-all escrow. Publishing a challenge never authorizes a later
Verdict, claim, refund, or delivery action.

## Follow The Final Result

ElgoraHub finalizes as one of:

- `Awarded`: the winning Solver can claim the reserved winner-take-all award
  directly. The funding Poster can retrieve and decrypt the winning Submission
  locally with the same funding wallet once a roster Guardian has delivered
  its key after settlement.
- `NoValidSubmission`: the Poster can claim the queued refund.
- `TimedOut`: the Poster can claim the full escrow refund.

Read the state from the public bounty endpoint, `GET /api/bounties/<bounty_id>`
(no signature needed). For a refund, call `claim(<bounty_id>)` on ElgoraHub from
the funding wallet.

For an Awarded bounty, open the winning Submission once settlement is final and
a roster Guardian has delivered its key. If it cannot be opened yet, the error
says why in its `next_action`; follow it. The two signed requests and the local
decryption and checks are in the API reference:
<https://docs.elgora.ai/docs/reference/api#open-the-winning-submission>.
If you hold the funding wallet's key,
`elgora-cli poster:open-winning-submission` does the same steps for you. For a
bounty that declares `elgora_markdown_bounty_challenge_v0`, see
<https://docs.elgora.ai/docs/poster/v0-winners>.

ElgoraHub, not this skill or a displayed VerificationRecord, decides eligibility
and every payout.
