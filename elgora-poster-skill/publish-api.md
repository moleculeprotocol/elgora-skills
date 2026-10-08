# Publishing Through The Elgora API

Open this file only when you publish for the Poster. A Poster who pastes the
page into the website needs none of it.

## Talking To The Elgora API

Everything this skill does with Elgora is plain HTTPS against
`https://elgora.ai` (Base mainnet). There is
no CLI to install, no SDK and no account. Reads that grant no authority, such as
a bounty's public state, are unauthenticated `GET`s. Every call that acts for a
wallet is authenticated as below. Bodies are sent raw: the challenge as
`text/markdown`, other payloads as JSON with `snake_case` fields. Errors come
back as JSON: `error.code`, `error.message`, `error.issues` and
`error.next_action`.

### Authenticate each request

Elgora has no login, API key or session. Every authenticated call must be
signed by an EVM account, as one EIP-712 message over that exact request. How
the Poster produces the signature is its own choice (a wallet skill, a signing
library, a hardware wallet, a Safe); the key never goes to Elgora, and this skill
does not need to hold it.

What must be signed, as `ApiRequestApproval` in the domain `{ name: "Elgora",
version: "1", chainId: 8453, verifyingContract:
0x8f80d1183cd983b01b0c9ac6777cc732ec9800de }`:

| Field | Value |
| --- | --- |
| `endpointId` | `"<METHOD> <pathname>"`, method uppercased, no host, no query |
| `audience` | the lowercased host, `elgora.ai` |
| `bodyHash` | `keccak256` of the exact body bytes (`keccak256("")` for none) |
| `query` | the query string through `URLSearchParams`, so `poster_address` and any `previous_spec_commitment` are signed |
| `blockNumber`, `blockHash` | a recent Base block, three behind the tip |

Take the block from any public Base RPC: read the head with
`eth_blockNumber`, then the block three behind it with `eth_getBlockByNumber`
(its `number` and `hash`). Elgora's own default is the first of these.

| | Mainnet (Base, `8453`) |
| --- | --- |
| Public RPC | `https://mainnet.base.org` |
| Alternative | `https://base-rpc.publicnode.com` |

Public endpoints are rate limited; use your own provider if they throttle you.
The block must be on the chain the request targets, or the signature is
rejected.

Present it on every request as
`Authorization: Elgora-Approval <base64(address~signature~blockNumber~blockHash)>`.
Such a credential is self-issued, good for one request and accepted for five
minutes after its block. Sign again for every call, including a retry. The whole
scheme, with a complete client, is on the public documentation site at
<https://docs.elgora.ai>, Reference, "Request authorization".

### Errors

- `400`: the input is wrong; `error.issues` says where. Fix it and resend.
- `401`: a stale block or a signature that does not verify. Take a fresh block,
  sign again and retry.
- `403`: the signer is not the address the call names (for the Poster's calls,
  `poster_address`).
- `429`: a limit is used up; wait until `error.retry_not_before`.
- `5xx`: report it. Do not retry in a loop or change your input to work around
  it.

## Review, Publish And Fund

Everything below happens over HTTPS against `https://elgora.ai`, on Base
mainnet, and funding escrows real USDC. Two endpoints take the page:

| Step | Request |
| --- | --- |
| Review | `POST /api/bounty-challenge-specs/review?poster_address=<your address>` |
| Publish | `POST /api/bounty-challenge-specs/prepare-publication?poster_address=<your address>` |

Both take the raw `bounty_challenge.md` bytes as the body (`Content-Type:
text/markdown`, no JSON wrapper), exactly one `poster_address`, and an
`Authorization` header signed by that address (see Talking To The Elgora
API). A review request may also carry
one `previous_spec_commitment` (below).

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
   computed, `chain_id` must be 8453, `to` must be the ElgoraHub above, and
   `escrow_amount` and `submission_deadline` must match your frontmatter. Stop
   if any differs; a response that disagrees with you must not move your money.
3. Fund from the Poster's wallet, which needs the escrow amount in USDC
   (`0x833589fcd6edb6e08f4c7c32d4f71b54bda02913`, 6 decimals) and some ETH for
   gas: send `approve(<ElgoraHub>, escrow_amount)` on the USDC contract, then the
   `createBounty(bytes32 specCommitment, uint256 escrowAmount, uint64
   submissionDeadline)` call (`data` in the response encodes it). The bounty
   exists when the `BountyCreated` event arrives; its `bountyId` is the bounty's
   identity.
4. Keep `bounty_id`, `spec_commitment` and the creation transaction hash. They
   are public, and nothing else you need is secret.

Mainnet funding escrows real USDC. A published page whose funding transaction
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
  locally with the same funding wallet after delivery is available.
- `NoValidSubmission`: the Poster can claim the queued refund.
- `TimedOut`: the Poster can claim the full escrow refund.

Read the state from the public bounty endpoint, `GET /api/bounties/<bounty_id>`
(no signature needed). For a refund, call `claim(<bounty_id>)` on ElgoraHub from
the funding wallet. For an Awarded bounty, retrieve the exact finalized winner with
`POST /api/bounties/<bounty_id>/delivery/retrieve` (signed as above, body
`{ "poster_ephemeral_public_key": … }` with a fresh X25519 public key), which
returns the content key rewrapped to your key; fetch the encrypted Submission and
decrypt it locally, so plaintext never leaves the Poster's machine. The exact
steps are under How it works, "Delivering the winning work", at
<https://docs.elgora.ai>. ElgoraHub, not
this skill or a displayed VerificationRecord, decides eligibility and every
payout.
