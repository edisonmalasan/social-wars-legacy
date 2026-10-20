/**
 * Server authority over combat.
 *
 * The original game resolves combat **on the client**: the client rolls the
 * damage, applies it, and tells the server what happened. The server trusts
 * it. That is the single most exploitable thing about the original design,
 * and it is what roadmap finding F3 and non-negotiable 3 exist to prevent.
 *
 * So the clone does the opposite: **the server issues the seed and runs the
 * roll.** The client never sends a damage number, and even if it does, the
 * server ignores it.
 *
 * The API is shaped to make that structural rather than a matter of
 * discipline: `resolveServerCombat` takes a seed and the two combatants, and
 * returns the outcome. There is no parameter for a client-claimed result,
 * because there is nowhere to put one.
 */
import { Random, hashSeed } from './random.ts';
import { resolveDamage, type CombatStats, type CombatContext } from './combat.ts';

/** A combatant, as the server sees it. */
export interface Combatant extends CombatStats {
  id: string;
  itemId: number;
  /** The unit's current health. */
  health: number;
  /** The unit's maximum life. */
  maxLife: number;
  /** The unit's position, in tiles. */
  x: number;
  y: number;
  /** The unit's random attack phase, 0-4. Units only; buildings fire in lockstep. */
  phase?: number;
}

/** What the server needs to resolve one attack. */
export interface ServerCombatInput {
  /**
   * The server-issued seed.
   *
   * It must be **server-issued**: the client may not choose it, or it can
   * grind for a favourable roll. A battle id is the natural seed, because it
   * is already unique, already server-issued, and already known to both sides.
   */
  seed: string;
  /** The attacker. */
  attacker: Combatant;
  /** The defender. */
  defender: Combatant;
  /** Per-attack tunables, if any. */
  context?: CombatContext;
  /** How many units the hit is spread across. */
  numTargets?: number;
  /** The defender's fighting-type properties, for the counter check. */
  defenderProperties?: Record<string, unknown>;
}

/** What the server decided. */
export interface ServerCombatOutcome {
  /** The seed the decision was made with. */
  seed: string;
  /** The damage the server rolled. */
  damage: number;
  /** Whether it was a critical hit. */
  crit: boolean;
  /** The variance the roll used. */
  variance: number;
  /** The defender's health after the hit. */
  defenderHealthAfter: number;
  /** Whether the hit killed. */
  killed: boolean;
  /** The counter multiplier that applied. */
  counterMultiplier: number;
  /** Every stage of the pipeline, for the golden-master diff. */
  stages: { name: string; value: number }[];
}

/**
 * Resolve one attack, server-side.
 *
 * The randomness comes from a `Random` seeded **only** by the server-issued
 * seed. Nothing the client sends can reach it, so the same seed and the same
 * inputs always produce the same outcome — on any machine, in any process.
 */
export function resolveServerCombat(input: ServerCombatInput): ServerCombatOutcome {
  const random = new Random(hashSeed(input.seed));

  // The damage class divides the attack by the number of units the hit
  // caught, BEFORE the damage pipeline runs:
  //
  //   SimpleDamage.apply:  _loc2_.recibirAtaque(this.damage / numTargets, attacker)
  //
  // so the division happens here, on the way into the pipeline.
  const numTargets = Math.max(1, input.numTargets ?? 1);
  const attacker: Combatant = {
    ...input.attacker,
    attack: input.attacker.attack / numTargets,
  };

  const result = resolveDamage(attacker, input.defender, random, input.context ?? {});

  const healthAfter = Math.max(0, input.defender.health - result.damage);
  return {
    seed: input.seed,
    damage: result.damage,
    crit: result.crit,
    variance: result.variance,
    defenderHealthAfter: healthAfter,
    killed: healthAfter <= 0,
    counterMultiplier: result.counterMultiplier,
    stages: result.stages,
  };
}

/**
 * What the client claimed, for the server to check against its own answer.
 *
 * This exists only so the server can *log* a mismatch. Nothing in the
 * resolution path reads it.
 */
export interface ClientClaim {
  /** The damage the client says it dealt. */
  damage: number;
  /** The seed the client says it used, if it sent one. */
  seed?: string;
}

/** The verdict on a client's claim. */
export interface ClaimVerdict {
  /** Does the claim match the server's own answer? */
  matches: boolean;
  /** The damage the server rolled. */
  serverDamage: number;
  /** The damage the client claimed. */
  clientDamage: number;
  /** The difference. */
  difference: number;
}

/**
 * Compare a client's claim with the server's answer.
 *
 * The claim is **never** used to decide anything. It is only compared, so
 * the server can count how many players are sending nonsense.
 */
export function checkClientClaim(
  claim: ClientClaim,
  outcome: ServerCombatOutcome,
): ClaimVerdict {
  const difference = claim.damage - outcome.damage;
  return {
    matches: difference === 0,
    serverDamage: outcome.damage,
    clientDamage: claim.damage,
    difference,
  };
}

/**
 * The seed a battle should use.
 *
 * A battle id is the right seed: it is server-issued, unique, and known to
 * both sides, so the client can *replay* the same battle and see the same
 * result — which is what makes the outcome auditable rather than arbitrary.
 */
export function battleSeed(battleId: string, attempt = 0): string {
  return attempt === 0 ? battleId : `${battleId}#${attempt}`;
}
