import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { COMMAND_NAMES, type CommandName } from './index.ts';
import {
  COMMAND_FAMILIES,
  COMMAND_TABLE,
  ERROR_CODES,
  HTTP_STATUS,
  MAX_COMMANDS_PER_REQUEST,
  PROTOCOL_VERSION,
  RESULT_KINDS,
  failureResponse,
  getCommandSpec,
  isSupportedVersion,
  maxArgs,
  minArgs,
  parseRequestBody,
  responseStatus,
  successResponse,
  validateCommandArguments,
  validateRequest,
} from './commands.ts';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(HERE, '../../..');
const CATALOGUE = path.join(REPO_ROOT, 're/docs/03-commands-quests-economy.md');
const COST_TABLE = path.join(REPO_ROOT, 'packages/rules/src/commandcost.ts');

/* -------------------------------------------------------------------------
 * The ground truth, read from the repository
 * ---------------------------------------------------------------------- */

/** One row of the command catalogue in re/docs/03 §1. */
interface CatalogueRow {
  /** The wire name the client sends. */
  readonly wire: string;
  /** The AS3 class. */
  readonly asClass: string;
  /** The arguments cell. */
  readonly args: string;
  /** The resource-delta cell. */
  readonly delta: string;
  /** Whether the upstream server handles it. */
  readonly server: string;
}

/** The rows of the command catalogue. */
function catalogueRows(): CatalogueRow[] {
  const text = readFileSync(CATALOGUE, 'utf8');
  // Only the catalogue itself: the document has other tables further down.
  const start = text.indexOf('# 1. THE COMMAND CATALOGUE');
  const end = text.indexOf('### 1.1');
  assert.ok(start > 0 && end > start, 'the command catalogue section moved');
  const rows: CatalogueRow[] = [];
  for (const line of text.slice(start, end).split('\n')) {
    if (!/^\| \d+ \|/.test(line)) continue;
    const cells = line.split('|').map((cell) => cell.trim());
    // | # | wire | class | args | delta | server |
    assert.equal(cells.length, 8, `unexpected catalogue row: ${line}`);
    rows.push({
      wire: (cells[2] ?? '').replace(/`/g, ''),
      asClass: (cells[3] ?? '').replace(/`/g, ''),
      args: cells[4] ?? '',
      delta: cells[5] ?? '',
      server: cells[6] ?? '',
    });
  }
  return rows;
}

/** How many arguments the catalogue lists for a row. */
function catalogueArgCount(row: CatalogueRow): number {
  return (row.args.match(/`\d+:/g) ?? []).length;
}

/**
 * Whether the catalogue says the command spends resources.
 *
 * The delta column writes a spend as a negative amount, with a U+2212 MINUS
 * SIGN. A grant is a plus.
 */
function catalogueSpends(row: CatalogueRow): boolean {
  return row.delta.includes('\u2212');
}

/** The commands the rules cost table prices. */
function pricedCommands(): Set<string> {
  const text = readFileSync(COST_TABLE, 'utf8');
  const block = text.match(/export const PRICED_COMMANDS = \[([\s\S]*?)\] as const;/);
  assert.ok(block !== null, 'the cost table no longer has a PRICED_COMMANDS list');
  return new Set(
    (block[1] ?? '')
      .split(',')
      .map((entry) => entry.trim().replace(/^'|'$/g, ''))
      .filter((entry) => entry.length > 0),
  );
}

/* -------------------------------------------------------------------------
 * A valid argument list for every command
 * ---------------------------------------------------------------------- */

/**
 * The commands the native protocol refuses, and why.
 *
 * `flash_debug` and `set_variables` are forbidden outright.
 * recoverable argument shape. `fast_forward` is administrative, which the
 * command-level validator does not know about — the role does.
 */
const REFUSED: Readonly<Record<string, string>> = {
  flash_debug: 'forbidden-command',
  set_variables: 'forbidden-command',
};

/** The commands a player session may not use. */
const REFUSED_AS_PLAYER: Readonly<Record<string, string>> = {
  ...REFUSED,
  // These six are only ever queued by the client's debug panel
  // (GUI/AdminPanel.as), so a player session may not use them.
  fast_forward: 'forbidden-command',
  load_map: 'forbidden-command',
  reset: 'forbidden-command',
  save_map: 'forbidden-command',
  system_receive_si_help: 'forbidden-command',
  system_reset_quest: 'forbidden-command',
};

/** A valid argument list for every command in the vocabulary. */
const VALID_ARGS: Readonly<Record<CommandName, readonly unknown[]>> = {
  accept_collect_help: [1, 'x'],
  activate: [1, 0],
  activate_item_click: [1, '{}'],
  add_click: [1],
  add_inventory_item: [1, 1],
  add_xp_unit: [1, 1, 1],
  admin_set_quest_rank: ['x', '1'],
  apply_rewards_ranking: ['{}'],
  assist_neighbor: ['x', '{}'],
  assist_receive: [1],
  attack_player: ['x'],
  batch_remove: ['{}'],
  buy: [1, 1, 1, 1, 1, 1, 0, 'b'],
  buy_magic: [1, 'g'],
  buy_mana_new: [1, 'c'],
  buy_offer_pack: [1, '{}'],
  buy_powerups: [1],
  buy_premium_account: [0],
  buy_resources: ['g', 1, 'c'],
  buy_si_help: [1],
  buy_stored_item_cash: [1],
  clean_attacks: [],
  clean_received_assists: ['x'],
  clear_message: [],
  collect: [1],
  collect_mission: [1],
  complete_collection: [1, 0],
  complete_goal: [1],
  complete_tutorial: [1],
  cross_promotion_finished: ['x'],
  darts_new_free: [],
  darts_reset: [1],
  darts_shoot_balloon: [0, 0],
  end_attack: ['x', true],
  end_quest: ['x', 1],
  exchange_cash: [],
  expand: [1],
  fast_forward: [1],
  finish_building: [1, 1],
  finish_robotic_help: ['{}'],
  finish_si: [1, 1],
  flash_debug: [1, 1, 1, 1, 1, 1, 1],
  kill: [1, 'x'],
  kill_iid: [1, 'x'],
  level_up: [1],
  load_map: ['x'],
  modify_energy: [],
  modify_position_universe: [1, 1],
  move: [1, 1, 1, 1, 'x'],
  next_research_item: [1],
  next_research_step: [1, true],
  orient: [1, 1],
  ping: [],
  place_gift: [1, 1, 1, 1, 1],
  place_stored_item: [1, 1, 1, 1, 1, 1, 0, 1, 1, 1],
  pop_queue_unit: [1],
  pop_unit: [1, 1, 1, 1, 1, 1, 1],
  premium_upgrade: [1, 1, 1, 1],
  push_queue_unit: [1],
  push_queue_unit2: [1, 1],
  push_unit: [1, 1],
  remove_inventory_item: [1, 1],
  research_buy_step_cash: [1, 1],
  reset: [],
  reset_collect: [1],
  reset_position_univers: [],
  reset_research_item: [1],
  reset_world_change: [],
  resurrect_hero: [1, 1, 1, 1, 0],
  rt_open_graph_unit: [1],
  save_map: ['x'],
  sell: [1, 'x'],
  sell_gift: [1],
  sell_stored_item: [1],
  set_goals: [1, '{}'],
  set_help_map: ['x'],
  set_quest_var: ['x', '{}'],
  set_resource_allies: ['g', 1],
  set_strategy: [1],
  set_variables: [],
  soulmixer_speedup: [1],
  spy_player: ['x'],
  store_add_items: [[]],
  store_item: [1],
  system_receive_mana: [1],
  system_receive_si_help: [1, 'x'],
  system_reset_quest: [],
  trade_resource: ['w', 0, 1],
  unit_collections_completed: [1],
  upgrade: [1],
  use_magic: [1],
  weekly_reward: [],
  win_alliance_daily_bonus: [],
  win_daily_bonus: [1, 1],
};

function request(commands: readonly unknown[]): Record<string, unknown> {
  return {
    v: PROTOCOL_VERSION,
    id: 'req-1',
    token: 'session-token',
    commands,
  };
}

function command(name: string, args: readonly unknown[]): Record<string, unknown> {
  return { map: 0, name, args };
}

/* -------------------------------------------------------------------------
 * The command table
 * ---------------------------------------------------------------------- */

describe('the command table', () => {
  it('has exactly the commands COMMAND_NAMES has', () => {
    const inNames = [...COMMAND_NAMES].sort();
    const inTable = Object.keys(COMMAND_TABLE).sort();
    assert.deepEqual(inTable, inNames);
    assert.equal(inTable.length, COMMAND_NAMES.length);
  });

  it('gives every command a spec under its own name', () => {
    for (const name of COMMAND_NAMES) {
      const spec = getCommandSpec(name);
      assert.ok(spec !== undefined, `${name} has no spec`);
      assert.equal(spec.name, name);
      assert.equal(spec.summary.length > 0, true, `${name} has no summary`);
      assert.equal((COMMAND_FAMILIES as readonly string[]).includes(spec.family), true);
      assert.equal((RESULT_KINDS as readonly string[]).includes(spec.result), true);
      assert.equal(typeof spec.costsResources, 'boolean', `${name}`);
      assert.equal(typeof spec.mutatesWorld, 'boolean', `${name}`);
      assert.equal(typeof spec.idempotent, 'boolean', `${name}`);
      assert.equal(typeof spec.shapeKnown, 'boolean', `${name}`);
    }
  });

  it('names every argument and gives it a known type', () => {
    const types = ['int', 'uint', 'number', 'string', 'boolean', 'json', 'array'];
    for (const name of COMMAND_NAMES) {
      const spec = getCommandSpec(name)!;
      for (const arg of spec.args) {
        assert.equal(arg.name.length > 0, true, `${name} has an unnamed argument`);
        assert.equal(types.includes(arg.type), true, `${name}.${arg.name} has type ${arg.type}`);
        assert.equal(
          arg.optional === undefined || typeof arg.optional === 'boolean',
          true,
          `${name}.${arg.name}`,
        );
      }
      // The optional arguments are always at the end, so that the arity is a
      // prefix of the list.
      const firstOptional = spec.args.findIndex((arg) => arg.optional === true);
      if (firstOptional >= 0) {
        assert.equal(
          spec.args.slice(firstOptional).every((arg) => arg.optional === true),
          true,
          `${name} has a required argument after an optional one`,
        );
      }
    }
  });

  it('has a valid argument list for every command', () => {
    assert.deepEqual(Object.keys(VALID_ARGS).sort(), [...COMMAND_NAMES].sort());
    for (const name of COMMAND_NAMES) {
      const spec = getCommandSpec(name)!;
      const args = VALID_ARGS[name];
      assert.ok(args !== undefined, `${name} has no valid argument list`);
      assert.equal(
        args.length >= minArgs(spec) && args.length <= maxArgs(spec),
        true,
        `${name} takes ${minArgs(spec)}..${maxArgs(spec)} arguments, the fixture has ${args.length}`,
      );
    }
  });

  it('agrees with the command catalogue on the argument count', () => {
    // The native protocol deliberately differs from the legacy argument list
    // for these six commands; each difference is explained in the table.
    const DIVERGENT = new Set([
      'buy_magic', // the payment resource was only in the client-declared delta
      'buy_mana_new', // the amount and the payment resource were only in the delta
      'end_quest', // the native form carries no claimed outcome
      'finish_si', // the client never pushes the third argument
      'trade_resource', // the traded amount was only in the client-declared delta
      'weekly_reward', // the server owns the reward
      'buy_resources', // the whole payload was in the client-declared delta
    ]);

    const rows = catalogueRows();
    for (const name of COMMAND_NAMES) {
      const spec = getCommandSpec(name)!;
      const wire = spec.legacyWireName ?? name;
      const row = rows.find((candidate) => candidate.wire === wire);
      if (row === undefined) {
        // Every command the client can send has a catalogue row, so a
        // missing one means the catalogue or the list is wrong.
        assert.fail(`${name} has no row in the catalogue`);
      }
      if (DIVERGENT.has(name)) continue;
      assert.equal(
        catalogueArgCount(row),
        maxArgs(spec),
        `${name}: the catalogue lists ${catalogueArgCount(row)} arguments, the table has ${maxArgs(spec)}`,
      );
      // A command whose catalogue entry has a conditional argument may have
      // a lower minimum; one without must have a fixed arity.
      const conditional = /only (if|for|when)/.test(row.args);
      if (!conditional) {
        assert.equal(
          minArgs(spec),
          maxArgs(spec),
          `${name}: the catalogue fixes the argument count, so the table must too`,
        );
      }
    }
  });

  it('agrees with the command catalogue on which commands spend resources', () => {
    const rows = catalogueRows();
    for (const name of COMMAND_NAMES) {
      const spec = getCommandSpec(name)!;
      const wire = spec.legacyWireName ?? name;
      const row = rows.find((candidate) => candidate.wire === wire);
      if (row === undefined) continue;
      if (!catalogueSpends(row)) continue;
      assert.equal(
        spec.costsResources,
        true,
        `${name} spends resources in the catalogue but is not marked as costing`,
      );
    }
  });

  it('agrees with the rules cost table about which commands have a cost', () => {
    const priced = pricedCommands();
    // The two priced commands that do not spend: one pays the player, and
    // one is a grant whose price belongs to a different command.
    const NOT_A_SPEND = new Set(['sell_stored_item', 'level_up']);
    for (const name of COMMAND_NAMES) {
      const spec = getCommandSpec(name)!;
      if (!priced.has(name)) continue;
      if (NOT_A_SPEND.has(name)) continue;
      assert.equal(
        spec.costsResources,
        true,
        `${name} is priced by the cost table but is not marked as costing`,
      );
    }
  });

  it('refuses the wallet-overwriting commands', () => {
    // Non-negotiable 6: flash_debug overwrites the whole wallet from client
    // arguments, so it must not exist in the new server.
    assert.equal(getCommandSpec('flash_debug')!.forbidden, true);
    // set_variables carries nothing but a client-declared resource delta,
    // which is the same defect under another name.
    assert.equal(getCommandSpec('set_variables')!.forbidden, true);
    assert.equal(
      getCommandSpec('set_variables')!.notes?.includes('client-declared resource delta'),
      true,
    );
  });

  it('reads the whole command catalogue', () => {
    // The catalogue documents 94 wire names. If the parser stops seeing one,
    // the cross-checks above would pass vacuously.
    assert.equal(catalogueRows().length, 94);
  });

  it('marks the commands whose argument shape is unknown', () => {
    const unknown = COMMAND_NAMES.filter((name) => !getCommandSpec(name)!.shapeKnown);
    assert.deepEqual(unknown, []);
  });

  it('records the legacy wire name that differs', () => {
    const differing = COMMAND_NAMES.filter(
      (name) => getCommandSpec(name)!.legacyWireName !== undefined,
    );
    assert.deepEqual(differing, []);
    // The client's name is the plural one, and it is the name the protocol
    // uses, so no command needs a legacy alias.
    assert.ok(getCommandSpec('unit_collections_completed'));
  });

  it('never lets a combat command carry a claimed outcome', () => {
    // Finding F5: the server re-simulates, so the native form of the combat
    // commands has nowhere to put the client's claim.
    for (const name of ['end_attack', 'end_quest'] as const) {
      const spec = getCommandSpec(name)!;
      assert.equal(
        spec.args.some((arg) => arg.type === 'json'),
        false,
        `${name} still carries a JSON blob`,
      );
    }
  });
});

/* -------------------------------------------------------------------------
 * The version
 * ---------------------------------------------------------------------- */

describe('the protocol version', () => {
  it('speaks version 1', () => {
    assert.equal(PROTOCOL_VERSION, 1);
    assert.equal(isSupportedVersion(PROTOCOL_VERSION), true);
  });

  it('accepts the whole supported range', () => {
    for (let version = 1; version <= 1; version += 1) {
      assert.equal(isSupportedVersion(version), true);
    }
  });

  it('refuses a version it does not speak', () => {
    assert.equal(isSupportedVersion(0), false);
    assert.equal(isSupportedVersion(2), false);
    assert.equal(isSupportedVersion(-1), false);
    assert.equal(isSupportedVersion(1.5), false);
  });

  it('refuses a request whose version it does not speak', () => {
    const result = validateRequest({ ...request([]), v: 99 });
    assert.equal(result.ok, false);
    assert.equal(result.errors[0]!.code, 'unsupported-protocol-version');
    assert.equal(result.errors[0]!.status, 400);
  });

  it('refuses a request whose version is not a number', () => {
    for (const version of ['1', null, undefined, 1.5, {}]) {
      const result = validateRequest({ ...request([]), v: version });
      assert.equal(result.ok, false, `version ${String(version)} was accepted`);
      assert.equal(result.errors[0]!.code, 'unsupported-protocol-version');
    }
  });

  it('checks the version before anything else', () => {
    // A body that is wrong in every other way still reports the version
    // first, so the client knows to upgrade before it fixes the rest.
    const result = validateRequest({ v: 99, id: '', token: '', commands: 'nope' });
    assert.equal(result.errors.length, 1);
    assert.equal(result.errors[0]!.code, 'unsupported-protocol-version');
  });
});

/* -------------------------------------------------------------------------
 * The request envelope
 * ---------------------------------------------------------------------- */

describe('the request envelope', () => {
  it('accepts a well-formed request', () => {
    const result = validateRequest(request([command('ping', [])]));
    assert.equal(result.ok, true);
    assert.deepEqual(result.errors, []);
    assert.ok(result.request !== null);
    assert.equal(result.request!.v, PROTOCOL_VERSION);
    assert.equal(result.request!.id, 'req-1');
    assert.equal(result.request!.token, 'session-token');
    assert.equal(result.request!.commands.length, 1);
    assert.equal(result.request!.commands[0]!.name, 'ping');
  });

  it('never takes an identity from the body', () => {
    // Upstream took the player identity from the request (USERID). The
    // native envelope has four fields, and none of them is a player id.
    const result = validateRequest({
      ...request([command('ping', [])]),
      USERID: 'php-session-id',
      user_id: 'php-session-id',
    });
    assert.equal(result.ok, true);
    assert.deepEqual(Object.keys(result.request!).sort(), ['commands', 'id', 'token', 'v']);
    assert.equal(JSON.stringify(result.request).includes('php-session-id'), false);
  });

  it('carries no client-declared resource vector', () => {
    const result = validateRequest({
      ...request([command('buy', [9001, 12, 3, 4, 1, 0, 0, 'b'])]),
      resources: [0, 0, 1000000, 0, 0, 0, 0, 0],
    });
    assert.equal(result.ok, true);
    assert.equal(Object.keys(result.request!).includes('resources'), false);
  });

  it('leaves no room for a resource delta in the arguments', () => {
    // A ninth argument to `buy` would be the place to smuggle a delta.
    const result = validateRequest(
      request([command('buy', [9001, 12, 3, 4, 1, 0, 0, 'b', 0, 0, 1000000, 0, 0, 0, 0, 0])]),
    );
    assert.equal(result.ok, false);
    assert.equal(result.errors[0]!.code, 'invalid-argument-count');
  });

  it('requires a session token', () => {
    for (const token of [undefined, '', 42, null]) {
      const body = request([]);
      delete body['token'];
      if (token !== undefined) body['token'] = token;
      const result = validateRequest(body);
      assert.equal(result.ok, false, `token ${String(token)} was accepted`);
      assert.equal(result.errors[0]!.code, 'missing-session-token');
      assert.equal(result.errors[0]!.status, 401);
    }
  });

  it('requires a request id', () => {
    for (const id of [undefined, '', 42]) {
      const body = request([]);
      delete body['id'];
      if (id !== undefined) body['id'] = id;
      const result = validateRequest(body);
      assert.equal(result.ok, false, `id ${String(id)} was accepted`);
      assert.equal(result.errors[0]!.code, 'malformed-request');
    }
  });

  it('refuses a body that is not an object', () => {
    for (const body of [null, undefined, 42, 'hello', [], true]) {
      const result = validateRequest(body);
      assert.equal(result.ok, false, `${String(body)} was accepted`);
      assert.equal(result.errors[0]!.code, 'malformed-request');
      assert.equal(result.request, null);
    }
  });

  it('refuses a request without a command array', () => {
    const result = validateRequest({ v: PROTOCOL_VERSION, id: 'r', token: 't' });
    assert.equal(result.ok, false);
    assert.equal(result.errors[0]!.code, 'malformed-request');
  });

  it('refuses a body that is not JSON, without throwing', () => {
    const result = parseRequestBody('{not json');
    assert.equal(result.ok, false);
    assert.equal(result.errors[0]!.code, 'malformed-request');
    assert.equal(result.errors[0]!.status, 400);
  });

  it('parses a JSON body and validates it', () => {
    const result = parseRequestBody(JSON.stringify(request([command('ping', [])])));
    assert.equal(result.ok, true);
    assert.equal(result.request!.commands[0]!.name, 'ping');
  });

  it('limits how many commands one request may carry', () => {
    const many = Array.from({ length: MAX_COMMANDS_PER_REQUEST + 1 }, () =>
      command('ping', []),
    );
    const result = validateRequest(request(many));
    assert.equal(result.ok, false);
    assert.equal(result.errors[0]!.code, 'malformed-request');
    assert.equal(result.errors[0]!.message.includes(String(MAX_COMMANDS_PER_REQUEST)), true);

    const exact = Array.from({ length: MAX_COMMANDS_PER_REQUEST }, () => command('ping', []));
    assert.equal(validateRequest(request(exact)).ok, true);
  });

  it('refuses a command that is not an object', () => {
    const result = validateRequest(request(['ping', 42, null]));
    assert.equal(result.ok, false);
    assert.equal(result.errors.length, 3);
    assert.equal(result.errors[0]!.code, 'malformed-request');
    assert.equal(result.errors[0]!.commandIndex, 0);
  });

  it('refuses a command without a map id', () => {
    const result = validateRequest(request([{ name: 'ping', args: [] }]));
    assert.equal(result.ok, false);
    assert.equal(result.errors[0]!.code, 'invalid-argument');
    assert.equal(result.errors[0]!.argumentIndex, 0);
  });

  it('refuses a negative map id', () => {
    const result = validateRequest(request([{ map: -1, name: 'ping', args: [] }]));
    assert.equal(result.ok, false);
    assert.equal(result.errors[0]!.code, 'invalid-argument');
  });
});

/* -------------------------------------------------------------------------
 * The command validator
 * ---------------------------------------------------------------------- */

describe('the command validator', () => {
  it('accepts a valid argument list for every command in the vocabulary', () => {
    for (const name of COMMAND_NAMES) {
      const errors = validateCommandArguments(name, VALID_ARGS[name]);
      const expected = REFUSED[name];
      if (expected === undefined) {
        assert.deepEqual(errors, [], `${name} rejected its own valid arguments`);
      } else {
        assert.equal(errors.length, 1, `${name} produced ${errors.length} errors`);
        assert.equal(errors[0]!.code, expected, `${name} was refused for the wrong reason`);
      }
    }
  });

  it('accepts every command of the vocabulary in a request', () => {
    const body = request(
      COMMAND_NAMES.map((name) => command(name, VALID_ARGS[name])),
    );
    const result = validateRequest(body);
    const expectedErrors = Object.keys(REFUSED_AS_PLAYER).length;
    assert.equal(
      result.errors.length,
      expectedErrors,
      JSON.stringify(result.errors, null, 2),
    );
    assert.equal(result.ok, false);
    for (const error of result.errors) {
      assert.equal(REFUSED_AS_PLAYER[error.command!], error.code);
    }
  });

  it('accepts every command of the vocabulary for an administrator', () => {
    const body = request(
      COMMAND_NAMES.map((name) => command(name, VALID_ARGS[name])),
    );
    const result = validateRequest(body, { role: 'admin' });
    // Only the forbidden commands and the shapeless one are still refused.
    assert.equal(
      result.errors.length,
      Object.keys(REFUSED).length,
      JSON.stringify(result.errors, null, 2),
    );
  });

  it('refuses an unknown command', () => {
    const result = validateRequest(request([command('teleport', [])]));
    assert.equal(result.ok, false);
    assert.equal(result.errors[0]!.code, 'unknown-command');
    assert.equal(result.errors[0]!.status, 400);
    assert.equal(result.errors[0]!.command, 'teleport');
  });

  it('refuses flash_debug', () => {
    const result = validateRequest(request([command('flash_debug', [1, 2, 3, 4, 5, 6, 7])]));
    assert.equal(result.ok, false);
    assert.equal(result.errors[0]!.code, 'forbidden-command');
    assert.equal(result.errors[0]!.status, 403);
  });

  it('refuses set_variables', () => {
    const result = validateRequest(request([command('set_variables', [])]));
    assert.equal(result.ok, false);
    assert.equal(result.errors[0]!.code, 'forbidden-command');
  });

  it('refuses a command that is not in the vocabulary', () => {
    // There is no command with an unknown argument shape any more: all 94
    // have a catalogue row. A name outside the vocabulary is refused as
    // unknown.
    const result = validateRequest(request([command('build', [])]));
    assert.equal(result.ok, false);
    assert.equal(result.errors[0]!.code, 'unknown-command');
    assert.equal(result.errors[0]!.status, 400);
  });

  it('refuses an administrative command for a player', () => {
    const result = validateRequest(request([command('fast_forward', [3600])]));
    assert.equal(result.ok, false);
    assert.equal(result.errors[0]!.code, 'forbidden-command');
    assert.equal(result.errors[0]!.status, 403);
  });

  it('accepts an administrative command for an administrator', () => {
    const result = validateRequest(request([command('fast_forward', [3600])]), {
      role: 'admin',
    });
    assert.equal(result.ok, true, JSON.stringify(result.errors, null, 2));
  });

  it('refuses a command with too few arguments', () => {
    const result = validateRequest(request([command('buy', [9001, 12])]));
    assert.equal(result.ok, false);
    assert.equal(result.errors[0]!.code, 'invalid-argument-count');
    assert.equal(result.errors[0]!.expected, '8..8 arguments');
  });

  it('refuses a command with too many arguments', () => {
    const result = validateRequest(request([command('ping', ['extra'])]));
    assert.equal(result.ok, false);
    assert.equal(result.errors[0]!.code, 'invalid-argument-count');
  });

  it('refuses an argument of the wrong type', () => {
    const result = validateRequest(request([command('collect', ['seven'])]));
    assert.equal(result.ok, false);
    assert.equal(result.errors[0]!.code, 'invalid-argument');
    assert.equal(result.errors[0]!.argumentIndex, 0);
    assert.equal(result.errors[0]!.expected, 'an integer');
    assert.equal(result.errors[0]!.status, 400);
  });

  it('refuses a negative unsigned argument', () => {
    const result = validateRequest(request([command('add_xp_unit', [1, -5])]));
    assert.equal(result.ok, false);
    assert.equal(result.errors[0]!.code, 'invalid-argument');
    assert.equal(result.errors[0]!.expected, 'a non-negative integer');
  });

  it('refuses a value outside a closed set', () => {
    const result = validateRequest(request([command('darts_shoot_balloon', [99, 0])]));
    assert.equal(result.ok, false);
    assert.equal(result.errors[0]!.code, 'invalid-argument');
    assert.equal(result.errors[0]!.expected?.includes('one of'), true);
  });

  it('refuses a string that is not JSON where JSON is required', () => {
    const result = validateRequest(request([command('set_quest_var', ['spawned', 'not json'])]));
    assert.equal(result.ok, false);
    assert.equal(result.errors[0]!.code, 'invalid-argument');
    assert.equal(result.errors[0]!.argumentIndex, 1);
  });

  it('accepts a decoded JSON value as well as an encoded one', () => {
    const encoded = validateRequest(request([command('set_quest_var', ['spawned', 'true'])]));
    assert.equal(encoded.ok, true, JSON.stringify(encoded.errors, null, 2));
    const decoded = validateRequest(request([command('set_quest_var', ['spawned', true])]));
    assert.equal(decoded.ok, true, JSON.stringify(decoded.errors, null, 2));
  });

  it('reports every mistake at once', () => {
    const result = validateRequest(
      request([
        command('nonsense', []),
        command('collect', ['seven', 'eight']),
        command('flash_debug', [1, 2, 3, 4, 5, 6, 7]),
      ]),
    );
    assert.equal(result.ok, false);
    assert.equal(result.errors.length, 3);
    assert.deepEqual(
      result.errors.map((error) => error.commandIndex),
      [0, 1, 2],
    );
  });

  it('never throws, whatever it is given', () => {
    const garbage: unknown[] = [
      null,
      undefined,
      0,
      '',
      'ping',
      [],
      [1, 2, 3],
      { v: 'x' },
      { v: 1, id: {}, token: [], commands: {} },
      { v: 1, id: 'a', token: 'b', commands: [{ map: {}, name: 7, args: 'x' }] },
      { v: 1, id: 'a', token: 'b', commands: [{}] },
    ];
    for (const body of garbage) {
      const result = validateRequest(body);
      assert.equal(result.ok, false);
      assert.equal(result.errors.length > 0, true);
      for (const error of result.errors) {
        assert.equal((ERROR_CODES as readonly string[]).includes(error.code), true);
        assert.equal(error.status >= 400 && error.status < 500, true);
      }
    }
  });

  it('never throws on a bad argument list', () => {
    // An argument list that is not an array at all is a malformed request.
    for (const args of [null, undefined, 7, 'x', {}]) {
      const result = validateRequest(request([command('collect', args as readonly unknown[])]));
      assert.equal(result.ok, false);
      assert.equal(result.errors[0]!.code, 'malformed-request');
    }
    // An argument list that is an array of the wrong things is a bad
    // argument.
    for (const args of [[null], [undefined], ['seven']]) {
      const result = validateRequest(request([command('collect', args as readonly unknown[])]));
      assert.equal(result.ok, false);
      assert.equal(result.errors[0]!.code, 'invalid-argument');
    }
  });
});

/* -------------------------------------------------------------------------
 * The response envelope
 * ---------------------------------------------------------------------- */

describe('the response envelope', () => {
  it('echoes the request id', () => {
    const response = successResponse('req-1', []);
    assert.equal(response.id, 'req-1');
    assert.equal(response.v, PROTOCOL_VERSION);
  });

  it('is ok when every command succeeded', () => {
    const response = successResponse('req-1', [
      { index: 0, ok: true, result: { kind: 'none' } },
    ]);
    assert.equal(response.ok, true);
    assert.equal(response.errors.length, 0);
    assert.equal(responseStatus(response), 200);
  });

  it('is not ok when a command failed', () => {
    const response = failureResponse('req-1', [
      {
        code: 'unknown-command',
        message: 'there is no command named "teleport"',
        status: 400,
      },
    ]);
    assert.equal(response.ok, false);
    assert.equal(responseStatus(response), 400);
  });

  it('answers with the status of the worst error', () => {
    const response = failureResponse('req-1', [
      { code: 'malformed-request', message: 'x', status: 400 },
      { code: 'forbidden-command', message: 'x', status: 403 },
    ]);
    assert.equal(responseStatus(response), 403);
  });

  it('never answers with a 5xx', () => {
    for (const code of ERROR_CODES) {
      assert.equal(HTTP_STATUS[code] >= 400, true, code);
      assert.equal(HTTP_STATUS[code] < 500, true, code);
    }
  });
});
