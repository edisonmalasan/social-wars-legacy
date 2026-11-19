# 20. The social services are server-only, and out of scope for the web client

**Status:** accepted

## Context

The server implements the original's social layer in full. `packages/server/src/alliance.ts`
covers all **11 alliance variants** and the **17 exact error codes** recovered from the
client; `packages/server/src/marketplace.ts` covers the auction and unit-betting
subsystem; `packages/server/src/socialstore.ts` holds the neighbour, profile, visit and
gifting state. `apps/server/src/social.ts` serves all of it over HTTP. The reverse
engineering that established those contracts is in
`re/docs/15-social-layer-contracts.md`.

The web client has no code that calls any of those endpoints. The **neighbour strip**
is the only social surface it draws (`packages/client/src/neighbours.ts`,
`apps/client/src/ui/neighbours.tsx`). The screen inventory nevertheless marked the
alliance and auction-house screens `implemented`, with notes that pointed at the
**server** modules: a server model is not a client screen. The roadmap's G4 item
allows the features to be "functional, or visibly out of scope", so the honest
position has to be recorded and checked rather than left as a misleading tick.

Three things the original relied on do not exist for this project:

- **No Facebook identity.** Friends, invitations, gifting, alliance membership and
  visiting were tied to a Facebook account. The clone authenticates its own players
  with credentials and revocable session tokens; it has no social graph to import.
- **No real-money settlement.** The original's bid and purchase flows assumed a
  live payment provider. The preservation project must not take payments, and the
  live premium-capture item is externally blocked for exactly that reason.
- **No live third-party service.** The alliance and auction endpoints pointed at a
  running Zynga service. Those services are gone: the upstream server answers `{}`
  for every alliance variant, so there is nothing to integrate with.

## Decision

**The server keeps and serves the alliance, auction and social-store services; the
web client intentionally does not surface them.** No alliance-centre, auction-house,
bidder, neighbour-profile or visit popup is built. The neighbour strip — the ordered
list of other players with their hurry-up state — is the one social surface that
remains, because it is drawn from the clone's own `/api/neighbours` endpoint.

This is a **client-scope** decision only. The commands, rules models, HTTP routes and
error codes stay; a future client with a social identity and a settlement service
could call them without re-implementing the rules. The roadmap's G4 social item is
closed with this record as the reason.

The decision is recorded where it can be checked: every alliance and marketplace
screen in `re/data/ui-screens.json` is `dropped` with a `Dropped: ` reason naming this
record (or `planned` where an in-game UI is still promised), and
`packages/client/src/screens.test.ts` refuses to let any of them be marked
`implemented` again without a real client model.

## Alternatives

- **Build the client screens against the server's endpoints.** It would look like
  parity, but the screens would have no Facebook identity to invite, no payment
  provider to bid with and no live alliance service to list. They would be empty
  shells presented as working features.
- **Point the client at the original's third-party endpoints.** Those services no
  longer exist, and routing player data to a dead external host would be a privacy
  and reliability problem even if one did.
- **Delete the server's social services as well.** That would lose the recovered
  contracts — the 11 variants, the 17 error codes, the auction flow — which are the
  preservation value of this work. Keeping them costs nothing at runtime and leaves
  the door open.
- **Leave the screens marked `implemented` because the server has models.** That is
  the current, incorrect state: it claims a client surface exists when it does not,
  and it would let the roadmap tick a box by mistake.
- **Drop the neighbour strip too.** It works against the clone's own server and is
  already checked by its own tests. Removing it would discard real functionality to
  make the scope statement tidier.

## Consequences

- The client bundle carries **no alliance, auction, visit or gifting UI**, and no
  client code calls the social HTTP routes. The server still serves them.
- The screen inventory's `dropped` decisions for those screens carry a real reason
  and a pointer here; the checked test fails if one is quietly relabelled
  `implemented`.
- The neighbour strip remains, with the server's ordering and hurry-up rules; the
  original's Facebook photo is deliberately not reproduced.
- Friend, gift and premium **purchase** screens that still promise an in-game UI are
  left `planned`, not dropped: premium and its purchase command are in scope for the
  client elsewhere, and dropping them here would hide wanted work. The already
  dropped real-money and hired-friend screens keep their existing reasons.
- A player cannot join an alliance or bid in an auction through this client. That is
  a visible, recorded limitation, not an unfinished feature.
