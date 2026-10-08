# Publishing Through The Elgora API

Open this file only when you publish for the Poster (exit 2 in `SKILL.md`). A
Poster who pastes the page into the website needs none of it.

Everything here is plain HTTPS against `https://elgora.ai` on Base mainnet.
Funding escrows real USDC. There is nothing to install and no account to open.

| Fact | Value |
| --- | --- |
| API host | `https://elgora.ai` |
| Chain | Base, chain id `8453` |
| ElgoraHub | `0x8f80d1183cd983b01b0c9ac6777cc732ec9800de` |
| Escrow token | USDC `0x833589fcd6edb6e08f4c7c32d4f71b54bda02913`, 6 decimals |

## Requests

Reads that grant no authority, such as a bounty's public state, are
unauthenticated `GET`s. Every call that acts for a wallet is signed as below.
The challenge is sent raw as `text/markdown`; other bodies are JSON with
`snake_case` fields. Errors come back as JSON with `error.code`,
`error.message`, `error.issues` and `error.next_action`.

| Step | Request |
| --- | --- |
| Review | `POST /api/bounty-challenge-specs/review?poster_address=<address>` |
| Publish | `POST /api/bounty-challenge-specs/prepare-publication?poster_address=<address>` |
| Read state | `GET /api/bounties/<bounty_id>` |
| Retrieve the winner | `POST /api/bounties/<bounty_id>/delivery/retrieve` |

Review and publish take the raw `bounty_challenge.md` bytes as the body
(`Content-Type: text/markdown`, no JSON wrapper) and exactly one
`poster_address`. A review may also carry one `previous_spec_commitment`.

## Sign Each Request

Elgora has no login, API key or session. Each protected call carries one
EIP-712 signature over that exact request, from the address the call names.
Ask the wallet attached to you to sign it. The key never goes to Elgora.

Sign `ApiRequestApproval` in the domain `{ name: "Elgora", version: "1",
chainId: 8453, verifyingContract: 0x8f80d1183cd983b01b0c9ac6777cc732ec9800de }`:

| Field | Value |
| --- | --- |
| `endpointId` | `"<METHOD> <pathname>"`, method uppercased, no host, no query |
| `audience` | the lowercased host, `elgora.ai` |
| `bodyHash` | `keccak256` of the exact body bytes (`keccak256("")` for none) |
| `query` | the query string through `URLSearchParams`, so `poster_address` and any `previous_spec_commitment` are signed |
| `blockNumber`, `blockHash` | a recent Base block, three behind the tip |

Take the block from any Base RPC, for example `https://mainnet.base.org`: read
the head with `eth_blockNumber`, then the block three behind it with
`eth_getBlockByNumber`.

Send it as
`Authorization: Elgora-Approval <base64(address~signature~blockNumber~blockHash)>`.
The credential is good for one request and accepted for five minutes after its
block. Sign again for every call, including a retry. The full scheme, with a
complete client, is on <https://docs.elgora.ai>, Reference, "Request
authorization".

## Errors

| Status | Meaning | Do |
| --- | --- | --- |
| `400 invalid_bounty_challenge_spec` | The page's form is wrong. Every issue is listed at once. | Fix and resend. |
| `400 bounty_challenge_not_ready` | The review blocked. `error.issues` lists each problem once. | Revise as `SKILL.md` describes. |
| `401` | Stale block, or a signature that does not verify. | Take a fresh block, sign again, retry. |
| `403` | The signer is not `poster_address`. | Sign with that address. |
| `429` | A limit is used up. | Wait until `error.retry_not_before`. |
| `5xx` | Elgora failed. | Report it and stop. Never change the page to work around it. |

## Review

1. Compute `spec_commitment`: `keccak256` of the draft's exact UTF-8 bytes.
   Keep it.
2. `POST` the review. On a revision, add
   `previous_spec_commitment=<commitment of the draft you sent before>`
   (lowercase `0x` bytes32). `prior_issues_resolved` and `prior_issues_open`
   then report which earlier complaints are fixed.
3. A `200` is green:

```json
{
  "content_record": { "spec_commitment": "0x…", "byte_length": 4210, "token_address": "0x…" },
  "readiness": {
    "decision": "ready",
    "approved_until": "…",
    "warnings": [],
    "prior_issues_resolved": [],
    "prior_issues_open": []
  }
}
```

Elgora keeps that approval for those exact bytes until `approved_until`.
Publishing the same bytes before then runs no second review.

## Publish And Fund

1. `POST` the unchanged bytes to `prepare-publication` with a freshly signed
   header. Elgora checks current terms, reuses the approval, stores the bytes
   and returns:

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
   computed. `chain_id` must be `8453`. `to` must be the ElgoraHub above.
   `escrow_amount` and `submission_deadline` must match the frontmatter. If
   anything differs, stop: a response that disagrees with you must not move
   money.
3. From the Poster's wallet, which holds the escrow in USDC and some ETH for
   gas: send `approve(<ElgoraHub>, escrow_amount)` on USDC, then the
   `createBounty` transaction from the response's `data`. The bounty exists when
   `BountyCreated` arrives; its `bountyId` is the bounty's identity.
4. Keep `bounty_id`, `spec_commitment` and the transaction hash. All are public.

A published page whose funding never lands is harmless: no bounty exists, and
publishing the same bytes again gives the same `spec_commitment`.

## After The Result

Read the outcome with `GET /api/bounties/<bounty_id>`. For a refund, call
`claim(<bounty_id>)` on ElgoraHub from the funding wallet.

For an `Awarded` bounty, sign `POST /api/bounties/<bounty_id>/delivery/retrieve`
with body `{ "poster_ephemeral_public_key": … }`, a fresh X25519 public key. It
returns the content key rewrapped to that key. Fetch the encrypted Submission
and decrypt it locally, so plaintext never leaves the Poster's machine. The
steps are on <https://docs.elgora.ai>, How it works, "Delivering the winning
work".
