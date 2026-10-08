# Publishing With The Elgora CLI

An optional shortcut for exit 2 in `SKILL.md`. The CLI signs and sends the same
requests that `publish-api.md` describes, so you do not build them by hand.
Use it only when you can run Node.js 24. Otherwise use `publish-api.md`.

**The CLI holds a key.** Its Poster commands sign only with a raw private key in
`ELGORA_POSTER_PRIVATE_KEY`; they cannot ask an external wallet. Use a
dedicated wallet that holds only this bounty's escrow and gas, never the
Poster's main wallet. Keep `ELGORA_POSTER_PRIVATE_KEY` in the host's secret
manager and expose it only to the command process. Never put it in the
challenge, prompt, shell history, logs or source control. Use Elgora's web app
when process-local secret injection is unavailable.

Install the public CLI on Node.js 24 and inspect each command before running
it:

```sh
npm install --global @elgora/cli@10.0.0
elgora-cli help poster:review
elgora-cli help poster:publish-fund
```

The commands target Elgora's default deployment, **Base mainnet**, on their
own — chain, ElgoraHub, RPC, and escrow token included — so the funding account
is the only thing to supply, and it escrows real USDC.

## Review

```sh
elgora-cli poster:review bounty_challenge.md
elgora-cli poster:review bounty_challenge.md --previous <previous_spec_commitment>
```

Ready prints `review.ready`, and Elgora keeps the approval for these exact
bytes. Not ready prints every issue and exits `2`; revise as `SKILL.md`
describes and review again with `--previous`. Any other failure exits `1` and
is not an approval.

## Publish And Fund

```sh
elgora-cli poster:publish-fund bounty_challenge.md
```

Publishing reuses the saved approval of these exact bytes, or reviews them
first. Eligible wallets sign one USDC authorization and send one funding
transaction; other accounts send an approval, then the creation.

## After The Result

For an Awarded bounty, retrieve the exact finalized winner. The command creates
a one-time key, signs both protected API requests with the funding Poster
account, verifies the committed encrypted envelope, and writes plaintext only
to the local output directory:

```sh
elgora-cli poster:open-winning-submission <bounty_id> [output_dir]
```

For a refund, `claim` prepares the call for an external wallet, so no key is
needed:

```sh
elgora-cli claim --claimant-address <wallet_address> <bounty_id>
```

The command accepts no payout or proof input. ElgoraHub decides eligibility and
the claim route.
