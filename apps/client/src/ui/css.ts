/**
 * The interface's stylesheet.
 *
 * The game was built for a 760 by 600 stage, so the interface is
 * **absolutely positioned** inside it and never reflowed: a panel that
 * moved would be a panel that covered something else.
 *
 * The colours are the game's own: a dark slate ground, a warm gold for
 * the player's own numbers, and a muted grey for the ones that are
 * warnings.
 */
export function uiCss(): string {
  return `
/*
 * The dialog and feedback tokens. They are the same slate, gold and muted
 * grey as the rest of the interface; naming them here keeps the new blocks
 * from growing another set of scattered literals.
 */
:root {
  --swl-surface: #131a24;
  --swl-surface-raised: #1d2430;
  --swl-border: #38445a;
  --swl-ink: #e8e3d8;
  --swl-ink-muted: #8d97a8;
  --swl-accent: #f5c542;
  --swl-danger: #e07a5f;
  --swl-success: #86d38a;
  --swl-scrim: #000a;
  --swl-gap: 8px;
  --swl-gap-lg: 12px;
}

.swl-ui {
  position: absolute;
  inset: 0;
  pointer-events: none;
  font-family: var(--swl-font-body, "Nunito", system-ui, sans-serif);
  color: #e8e3d8;
  font-size: calc(13px * var(--swl-font-scale-body, 1));
  user-select: none;
}

.swl-ui button {
  font: inherit;
  color: inherit;
  background: none;
  border: none;
  cursor: pointer;
  pointer-events: auto;
}

/*
 * Panels that can be long scroll **inside** the 760x600 stage instead of
 * clipping or pushing their tabs out of it. touch-action: pan-y tells a
 * touch browser the panel owns vertical panning (the canvas has
 * touch-action: none), so a finger scrolls the list rather than the page.
 * The font-scale variables below are deliberately untouched.
 */
.swl-inventory-scroll,
.swl-build-list,
.swl-dialog-body {
  touch-action: pan-y;
  -webkit-overflow-scrolling: touch;
}

/* --- The account form -------------------------------------------------- */

.swl-auth-modes {
  display: flex;
  gap: 8px;
  justify-content: center;
}

.swl-auth-modes button {
  padding: 6px 12px;
  border: 1px solid #38445a;
  border-radius: 3px;
  color: #8d97a8;
}

.swl-auth-modes .swl-auth-mode-active {
  border-color: #f5c542;
  color: #f5c542;
}

#signin-error { margin: 0; color: #e07a5f; }

/* --- The top bar ------------------------------------------------------- */

.swl-hud {
  position: absolute;
  left: 0;
  right: 0;
  top: 0;
  height: 48px;
  display: flex;
  align-items: stretch;
  justify-content: space-between;
  background: linear-gradient(#1d2430, #141a24);
  border-bottom: 1px solid #000;
  box-shadow: 0 1px 0 #2c3646;
}

.swl-hud-resources,
.swl-hud-player {
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 0 6px;
}

/*
 * The headings use the **display** face, the way the original does: the
 * body face is for the interface and the display face is for the
 * titles. The display face is scaled by its own factor, because the
 * two faces do not share their widths.
 */
.swl-goal-title,
.swl-chapter-title,
.swl-info-name {
  font-family: var(--swl-font-display, system-ui, sans-serif);
}

.swl-readout {
  position: relative;
  display: flex;
  align-items: baseline;
  gap: 4px;
  padding: 4px 8px;
  border-radius: 3px;
  pointer-events: auto;
  outline: none;
}

.swl-readout:hover,
.swl-readout:focus {
  background: #263043;
}

.swl-readout-label {
  color: #8d97a8;
  font-size: calc(10px * var(--swl-font-scale-body, 1));
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.swl-readout-value {
  color: #f2e6c8;
  font-weight: 700;
}

.swl-resource-gold .swl-readout-value { color: #f5c542; }
.swl-resource-wood .swl-readout-value { color: #b98a4e; }
.swl-resource-oil .swl-readout-value { color: #7fb3d5; }
.swl-resource-steel .swl-readout-value { color: #cfd6e0; }
.swl-resource-cash .swl-readout-value { color: #86d38a; }
.swl-resource-mana .swl-readout-value { color: #b48ef0; }

/*
 * The XP bar is a narrow track with a fill whose width is the fraction the
 * model derived. The number beside it is the server's XP over the content's
 * requirement; the bar is only a picture of that pair.
 */
.swl-xp {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
}

.swl-xp-label {
  color: #8d97a8;
  font-size: calc(10px * var(--swl-font-scale-body, 1));
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.swl-xp-track {
  display: block;
  width: 72px;
  height: 7px;
  overflow: hidden;
  border: 1px solid #38445a;
  border-radius: 4px;
  background: #10151d;
}

.swl-xp-fill {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, #7fb3d5, #f5c542);
}

.swl-xp-value {
  color: #f2e6c8;
  font-size: calc(11px * var(--swl-font-scale-body, 1));
  font-variant-numeric: tabular-nums;
}

/* The bonus read-out: a reading of the server's own cycles, never a claim. */
.swl-bonus-status {
  display: flex;
  flex-direction: column;
  gap: 1px;
  padding: 2px 6px;
  border-left: 1px solid #38445a;
  color: #f2e6c8;
  font-size: calc(10px * var(--swl-font-scale-body, 1));
  font-variant-numeric: tabular-nums;
}

.swl-bonus-day { color: #f5c542; font-weight: 700; }
.swl-bonus-weekly { color: #9fb3d1; }

/* The bonus is a gesture: the client asks, and the server names the reward. */
/* The button qualifier beats the generic .swl-ui button reset above. */
.swl-ui button.swl-bonus {
  padding: 4px 8px;
  border: 1px solid #f5c542;
  border-radius: 3px;
  background: #f5c542;
  color: #10151d;
  font-size: calc(11px * var(--swl-font-scale-body, 1));
  font-weight: 700;
}

.swl-ui button.swl-bonus:hover:not(:disabled) { background: #ffd75e; }

.swl-ui button.swl-bonus:disabled {
  border-color: #38445a;
  background: #1d2430;
  color: #5c6678;
  cursor: not-allowed;
}

.swl-army {
  padding: 4px 8px;
  color: #8d97a8;
  font-size: calc(11px * var(--swl-font-scale-body, 1));
}

.swl-placing {
  align-self: center;
  padding: 4px 8px;
  color: #f5c542;
  font-size: calc(11px * var(--swl-font-scale-body, 1));
  white-space: nowrap;
}

/* --- The popovers ------------------------------------------------------ */

.swl-popover {
  position: absolute;
  top: 100%;
  left: 0;
  min-width: 180px;
  padding: 8px 10px;
  background: #10151d;
  border: 1px solid #38445a;
  border-radius: 4px;
  box-shadow: 0 4px 14px #000a;
  z-index: 20;
}

.swl-popover-first {
  margin: 0;
  color: #e8e3d8;
  white-space: pre-line;
}

.swl-popover-warning {
  margin: 6px 0 0;
  color: #e0a33c;
}

/* --- The chapter map --------------------------------------------------- */

.swl-chapters {
  position: absolute;
  right: 8px;
  top: 58px;
  display: flex;
  gap: 6px;
  padding: 6px;
  border: 1px solid #38445a;
  border-radius: 4px;
  background: #131a24;
  pointer-events: auto;
}

.swl-chapter-title {
  margin-bottom: 4px;
  color: #8d97a8;
  font-size: calc(9px * var(--swl-font-scale-display, 1));
  text-align: center;
}

.swl-chapter-quests {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 3px;
}

.swl-quest-slot {
  width: 18px;
  height: 18px;
  display: grid;
  place-items: center;
  border-radius: 3px;
  font-size: calc(10px * var(--swl-font-scale-body, 1));
}

.swl-quest-open {
  background: #f5c542;
  color: #10151d;
  font-weight: 700;
}

.swl-quest-locked {
  background: #1d2430;
  color: #5c6678;
}

/* An opened slot is a button. The generic button rule above would otherwise
   strip the slot's background, so these win with one more class. */
.swl-ui button.swl-quest-slot {
  padding: 0;
}

.swl-ui .swl-quest-open {
  background: #f5c542;
  color: #10151d;
  font-weight: 700;
}

.swl-ui .swl-quest-locked {
  background: #1d2430;
  color: #5c6678;
}

.swl-quest-active {
  outline: 1px solid var(--swl-accent);
  outline-offset: 1px;
}

/* --- The inventory panel ---------------------------------------------- */

/* The chapter strip above ends at about y=144, so the inventory starts
   below it. The maximum height is reduced by the same amount: the panel
   keeps its old bottom edge and scrolls its contents rather than covering
   the chapter buttons. This holds at every viewport because the whole stage
   is scaled uniformly, never reflowed. */
.swl-inventory {
  position: absolute;
  right: 8px;
  top: 152px;
  width: 220px;
  max-height: 192px;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 8px 10px;
  border: 1px solid #38445a;
  border-radius: 4px;
  background: #131a24;
  pointer-events: auto;
}

/* The head holds the title and its category tabs; only the list below it
   scrolls. Long contents never push the tabs out of the 760x600 stage. */
.swl-inventory-head {
  flex: none;
}

.swl-inventory-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 2px;
  margin-top: 5px;
}

/* The roster opens the one dialog from this head, beside the section title. */
.swl-inventory-roster {
  float: right;
  padding: 0 4px;
  border: 1px solid var(--swl-border);
  border-radius: 3px;
  color: var(--swl-accent);
  font-size: calc(10px * var(--swl-font-scale-body, 1));
}

.swl-inventory-scroll {
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
}

.swl-inventory-title {
  color: #f2e6c8;
  font-family: var(--swl-font-display, system-ui, sans-serif);
  font-size: calc(13px * var(--swl-font-scale-display, 1));
  font-weight: 700;
}

.swl-inventory-empty {
  margin: 6px 0 0;
  color: #8d97a8;
  font-size: calc(11px * var(--swl-font-scale-body, 1));
}

.swl-inventory-list {
  margin: 6px 0 0;
  padding: 0;
  list-style: none;
}

.swl-inventory-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 3px 0;
}

.swl-inventory-name {
  flex: 1;
  color: #e8e3d8;
  font-size: calc(12px * var(--swl-font-scale-body, 1));
}

.swl-inventory-qty {
  color: #f5c542;
  font-size: calc(11px * var(--swl-font-scale-body, 1));
  font-weight: 700;
}

.swl-ui button.swl-inventory-place {
  padding: 3px 8px;
  border: 1px solid #f5c542;
  border-radius: 3px;
  background: #f5c542;
  color: #10151d;
  font-size: calc(11px * var(--swl-font-scale-body, 1));
  font-weight: 700;
}

.swl-ui button.swl-inventory-place:hover { background: #ffd75e; }

/* --- The goal panel --------------------------------------------------- */

.swl-goals {
  position: absolute;
  left: 8px;
  top: 58px;
  width: 300px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  pointer-events: auto;
}

.swl-goal-slot {
  position: relative;
}

.swl-goal-title {
  display: block;
  width: 100%;
  padding: 5px 8px;
  border: 1px solid #38445a;
  border-radius: 3px;
  background: #131a24;
  color: #e8e3d8;
  font-size: calc(12px * var(--swl-font-scale-display, 1));
  text-align: left;
}

.swl-goal-title:hover { background: #1b2432; }

.swl-goal-badge {
  position: absolute;
  right: 6px;
  top: 50%;
  transform: translateY(-50%);
  padding: 1px 6px;
  border-radius: 3px;
  background: #f5c542;
  color: #10151d;
  font-size: calc(10px * var(--swl-font-scale-body, 1));
  font-weight: 700;
}

/* --- The expansion control --------------------------------------------- */

.swl-expansion {
  position: absolute;
  left: 8px;
  top: 168px;
  width: 300px;
  max-height: 210px;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  gap: 4px;
  overflow-y: auto;
  overscroll-behavior: contain;
  touch-action: pan-y;
  padding: 6px 8px;
  border: 1px solid #38445a;
  border-radius: 4px;
  background: #131a24;
  pointer-events: auto;
}

.swl-expansion-head {
  margin-bottom: 4px;
  color: #8d97a8;
  font-size: calc(10px * var(--swl-font-scale-display, 1));
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.swl-ui button.swl-expansion-buy {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  width: 100%;
  padding: 5px 8px;
  border: 1px solid #f5c542;
  border-radius: 3px;
  background: #1b2432;
  color: #f5c542;
  font-size: calc(12px * var(--swl-font-scale-display, 1));
}

.swl-ui button.swl-expansion-buy:hover:not(:disabled) { background: #27324a; }

.swl-expansion-price { display: flex; gap: 8px; }

.swl-expansion-gold { color: #f2d67a; }

.swl-expansion-cash { color: #9fd3a0; }

.swl-expansion-buyfor {
  color: #8d97a8;
  font-size: calc(10px * var(--swl-font-scale-body, 1));
}

/* The original's requirement literals, shown only when the server's own
   wallet or neighbour count is short. They are hints, never enforced gates. */
.swl-expansion-prompt {
  margin: 0;
  color: #e0a33c;
  white-space: pre-line;
  font-size: calc(10px * var(--swl-font-scale-body, 1));
  line-height: 1.25;
}

/* The post-purchase growth result, inline in the same panel — no second
   overlay, no proprietary art. Its words and price are content/client text;
   the tiles and the count are the server's answer. */
.swl-expansion-result {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 5px 7px;
  border: 1px solid var(--swl-success);
  border-radius: 3px;
  background: #1d2a22;
}

.swl-expansion-result-head {
  margin: 0;
  color: var(--swl-success);
  font-family: var(--swl-font-display, system-ui, sans-serif);
  font-size: calc(13px * var(--swl-font-scale-display, 1));
  text-transform: uppercase;
}

.swl-expansion-result-message {
  margin: 0;
  color: var(--swl-ink);
  font-weight: 700;
}

.swl-expansion-result-detail,
.swl-expansion-result-price {
  margin: 0;
  color: var(--swl-ink-muted);
  font-size: calc(10px * var(--swl-font-scale-body, 1));
  font-variant-numeric: tabular-nums;
}

.swl-ui button.swl-expansion-result-dismiss {
  align-self: flex-end;
  padding: 2px 8px;
  border: 1px solid var(--swl-border);
  border-radius: 3px;
  color: var(--swl-ink-muted);
  font-size: calc(10px * var(--swl-font-scale-body, 1));
}

.swl-ui button.swl-expansion-result-dismiss:hover { border-color: var(--swl-accent); }

/* --- The collections tab ----------------------------------------------- */

.swl-collections { padding-top: 3px; }
.swl-collections-empty { margin: 0; color: var(--swl-ink-muted); font-size: calc(11px * var(--swl-font-scale-body, 1)); }
.swl-collections-list { display: flex; flex-direction: column; gap: 6px; margin: 0; padding: 0; list-style: none; }
.swl-collection { padding: 4px 0; border-top: 1px solid var(--swl-border); }
.swl-collection-head { display: flex; align-items: baseline; gap: 6px; }
.swl-collection-name { flex: 1; color: var(--swl-ink); font-weight: 700; }
.swl-collection-progress { color: var(--swl-accent); font-variant-numeric: tabular-nums; }
.swl-collection-done { color: var(--swl-success); font-size: calc(10px * var(--swl-font-scale-body, 1)); }
.swl-collection-description { margin: 2px 0; color: var(--swl-ink-muted); font-size: calc(10px * var(--swl-font-scale-body, 1)); }
.swl-collection-items { display: flex; flex-wrap: wrap; gap: 4px; margin: 0; padding: 0; list-style: none; }
.swl-collection-item { padding: 1px 4px; border: 1px solid var(--swl-border); border-radius: 3px; color: var(--swl-ink); font-size: calc(10px * var(--swl-font-scale-body, 1)); }
.swl-collection-item.is-missing { color: var(--swl-ink-muted); border-style: dashed; }
.swl-collection-item-qty { color: var(--swl-accent); }
.swl-collection-prize,
.swl-collection-price { margin: 3px 0 0; color: var(--swl-ink-muted); font-size: calc(10px * var(--swl-font-scale-body, 1)); }

/* --- The info panel ---------------------------------------------------- */

.swl-info {
  position: absolute;
  right: 8px;
  bottom: 8px;
  width: 220px;
  padding: 8px 10px;
  border: 1px solid #38445a;
  border-radius: 4px;
  background: #131a24;
  pointer-events: auto;
}

.swl-info-name {
  color: #f2e6c8;
  font-size: calc(13px * var(--swl-font-scale-display, 1));
  font-weight: 700;
}

.swl-info-earns {
  margin-top: 3px;
  color: #8d97a8;
  font-size: calc(12px * var(--swl-font-scale-body, 1));
}

.swl-info-hint {
  margin-top: 5px;
  color: #8d97a8;
  font-size: calc(11px * var(--swl-font-scale-body, 1));
}

.swl-info-stats {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 2px 8px;
  margin: 5px 0 0;
  color: #8d97a8;
  font-size: calc(11px * var(--swl-font-scale-body, 1));
}

.swl-info-stats dt { color: #8d97a8; }

.swl-info-stats dd {
  margin: 0;
  color: #e8e3d8;
  text-align: right;
}

.swl-info-collect {
  margin-top: 8px;
  padding: 4px 10px;
  border: 1px solid #f5c542;
  border-radius: 3px;
  background: #f5c542;
  color: #10151d;
  font-size: calc(12px * var(--swl-font-scale-body, 1));
  font-weight: 700;
}

/* The Upgrade and Finish actions share the resource button's shape. */
.swl-info-actions {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 8px;
}

.swl-info-action-button {
  width: 100%;
  padding: 4px 10px;
  border: 1px solid #f5c542;
  border-radius: 3px;
  background: #f5c542;
  color: #10151d;
  font-size: calc(12px * var(--swl-font-scale-body, 1));
  font-weight: 700;
}

.swl-info-action-button:hover { background: #ffd75e; }

.swl-info-action-note {
  margin-top: 2px;
  color: #8d97a8;
  font-size: calc(10px * var(--swl-font-scale-body, 1));
}

/* --- The collection-period selector ------------------------------------ */

.swl-info-production {
  margin-top: 5px;
  color: var(--swl-accent);
  font-size: calc(11px * var(--swl-font-scale-body, 1));
}

.swl-info-period-button {
  width: 100%;
  margin-top: 5px;
  padding: 4px 10px;
  border: 1px solid var(--swl-border);
  border-radius: 3px;
  background: var(--swl-surface-raised);
  color: var(--swl-ink);
  font-size: calc(11px * var(--swl-font-scale-body, 1));
}

.swl-info-period-button:hover { border-color: var(--swl-accent); }

.swl-production {
  display: flex;
  flex-direction: column;
  gap: var(--swl-gap);
}

.swl-production-head { font-weight: 700; }

.swl-production-cycle { color: var(--swl-accent); }

.swl-production-options {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--swl-gap);
}

.swl-production-option {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 8px;
  border: 1px solid var(--swl-border);
  border-radius: 3px;
  background: var(--swl-surface-raised);
  text-align: left;
}

.swl-production-option:hover { border-color: var(--swl-accent); }

.swl-production-option-active {
  border-color: var(--swl-accent);
  background: #2a2a20;
}

.swl-production-wait { font-weight: 700; }

.swl-production-mult { color: var(--swl-accent); }

.swl-production-amount,
.swl-production-note {
  color: var(--swl-ink-muted);
  font-size: calc(11px * var(--swl-font-scale-body, 1));
}

.swl-production-note { margin: 0; }

/* --- The recruitment panel --------------------------------------------- */

.swl-recruit {
  position: absolute;
  right: 236px;
  bottom: 8px;
  width: 220px;
  padding: 8px 10px;
  border: 1px solid #38445a;
  border-radius: 4px;
  background: #131a24;
  pointer-events: auto;
}

.swl-recruit-title {
  color: #f2e6c8;
  font-family: var(--swl-font-display, system-ui, sans-serif);
  font-size: calc(13px * var(--swl-font-scale-display, 1));
  font-weight: 700;
}

.swl-recruit-units {
  margin: 6px 0 0;
  padding: 0;
  list-style: none;
}

.swl-recruit-unit {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 3px 0;
}

.swl-recruit-unit-name {
  color: #e8e3d8;
  font-size: calc(12px * var(--swl-font-scale-body, 1));
}

.swl-recruit-train,
.swl-recruit-take {
  padding: 3px 8px;
  border: 1px solid #f5c542;
  border-radius: 3px;
  color: #10151d;
  background: #f5c542;
  font-size: calc(11px * var(--swl-font-scale-body, 1));
  font-weight: 700;
}

.swl-recruit-train:hover,
.swl-recruit-take:hover:not(:disabled) { background: #ffd75e; }

.swl-recruit-queue {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 8px;
  padding-top: 6px;
  border-top: 1px solid #2b3546;
}

.swl-recruit-countdown {
  color: #8d97a8;
  font-size: calc(11px * var(--swl-font-scale-body, 1));
}

.swl-recruit-take:disabled {
  border-color: #38445a;
  color: #5c6678;
  background: #1d2430;
  cursor: not-allowed;
}

/* --- The store ---------------------------------------------------------- */

.swl-store {
  position: absolute;
  right: 8px;
  bottom: 8px;
  max-width: 320px;
  max-height: 45vh;
  overflow: auto;
  padding: 6px 8px;
  border: 1px solid #38445a;
  border-radius: 4px;
  background: rgba(16, 21, 29, 0.92);
  color: #f2e6c8;
  font-size: calc(11px * var(--swl-font-scale-body, 1));
  pointer-events: auto;
}

.swl-store-summary { cursor: pointer; color: #f5c542; font-weight: 700; }
.swl-store-packs { display: flex; flex-direction: column; gap: 6px; margin-top: 6px; }
.swl-store-pack { border-top: 1px solid #38445a; padding-top: 4px; }
.swl-store-pack-name { margin-bottom: 3px; }
.swl-store-tiers { display: flex; flex-wrap: wrap; gap: 4px; }

.swl-ui button.swl-store-buy {
  padding: 3px 6px;
  border: 1px solid #4a6a8a;
  border-radius: 3px;
  background: #223047;
  color: #f2e6c8;
  font-size: calc(10px * var(--swl-font-scale-body, 1));
}

.swl-ui button.swl-store-buy:disabled {
  border-color: #38445a;
  background: #1d2430;
  color: #5c6678;
  cursor: not-allowed;
}

/* --- The Research LAB --------------------------------------------------- */

.swl-magiclab {
  position: absolute;
  right: 340px;
  bottom: 8px;
  max-width: 360px;
  max-height: 60vh;
  overflow: auto;
  padding: 6px 8px;
  border: 1px solid #38445a;
  border-radius: 4px;
  background: rgba(16, 21, 29, 0.92);
  color: #f2e6c8;
  font-size: calc(11px * var(--swl-font-scale-body, 1));
  pointer-events: auto;
}

.swl-magiclab-summary { cursor: pointer; color: #a9d7ff; font-weight: 700; }
.swl-magiclab-body { margin-top: 6px; }
.swl-magic-entries { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 6px; }
.swl-magic-entry { border-top: 1px solid #38445a; padding-top: 4px; }
.swl-magic-entry-head { display: flex; gap: 6px; align-items: baseline; }
.swl-magic-name { font-weight: 700; }
.swl-magic-stars { color: #f5c542; }
.swl-magic-status { color: #9fb3d1; }
.swl-magic-description { margin: 2px 0; color: #b9c6da; }
.swl-magic-costs { display: flex; flex-wrap: wrap; gap: 4px; align-items: center; }
.swl-magic-unlock { color: #f0a5a5; }

.swl-ui button.swl-magic-buy {
  padding: 3px 6px;
  border: 1px solid #4a6a8a;
  border-radius: 3px;
  background: #223047;
  color: #f2e6c8;
  font-size: calc(10px * var(--swl-font-scale-body, 1));
}

.swl-ui button.swl-magic-buy:disabled {
  border-color: #38445a;
  background: #1d2430;
  color: #5c6678;
  cursor: not-allowed;
}

.swl-magic-packs { display: flex; gap: 4px; margin-top: 8px; }
.swl-magic-pages { display: flex; gap: 6px; align-items: center; margin-top: 6px; }

/* --- The spell book ----------------------------------------------------- */

.swl-spellbook {
  position: absolute;
  right: 700px;
  bottom: 8px;
  max-width: 340px;
  max-height: 60vh;
  overflow: auto;
  padding: 6px 8px;
  border: 1px solid #38445a;
  border-radius: 4px;
  background: rgba(16, 21, 29, 0.92);
  color: #f2e6c8;
  font-size: calc(11px * var(--swl-font-scale-body, 1));
  pointer-events: auto;
}

.swl-spellbook-summary { cursor: pointer; color: #c9a9ff; font-weight: 700; }
.swl-spellbook-body { margin-top: 6px; }
.swl-spellbook-empty { color: #9fb3d1; }
.swl-spellbook-spells { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 4px; }
.swl-spellbook-spell { display: flex; gap: 6px; align-items: center; border-top: 1px solid #38445a; padding-top: 4px; }
.swl-spellbook-name { font-weight: 700; }
.swl-spellbook-level, .swl-spellbook-area { color: #9fb3d1; }

.swl-ui button.swl-spellbook-cast {
  margin-left: auto;
  padding: 3px 6px;
  border: 1px solid #4a6a8a;
  border-radius: 3px;
  background: #223047;
  color: #f2e6c8;
  font-size: calc(10px * var(--swl-font-scale-body, 1));
}

.swl-ui button.swl-spellbook-cast:disabled {
  border-color: #38445a;
  background: #1d2430;
  color: #5c6678;
  cursor: not-allowed;
}

.swl-spellbook-pages { display: flex; gap: 6px; align-items: center; margin-top: 6px; }

/* --- The neighbour strip ----------------------------------------------- */

.swl-neighbours {
  position: absolute;
  left: 8px;
  bottom: 8px;
  display: flex;
  gap: 4px;
  pointer-events: auto;
}

.swl-neighbour {
  width: 74px;
  padding: 4px;
  border: 1px solid #38445a;
  border-radius: 3px;
  background: #131a24;
  text-align: center;
}

.swl-neighbour-portrait {
  height: 28px;
  margin-bottom: 3px;
  border-radius: 3px;
  background: #1d2430;
}

.swl-neighbour-name {
  color: #e8e3d8;
  font-size: calc(11px * var(--swl-font-scale-body, 1));
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.swl-neighbour-level,
.swl-neighbour-xp {
  color: #8d97a8;
  font-size: calc(10px * var(--swl-font-scale-body, 1));
}

/* --- The build menu ---------------------------------------------------- */

.swl-build-menu {
  position: absolute;
  left: 8px;
  bottom: 8px;
  width: 300px;
  max-height: 420px;
  display: flex;
  flex-direction: column;
  background: #131a24;
  border: 1px solid #38445a;
  border-radius: 5px;
  box-shadow: 0 6px 20px #000a;
  pointer-events: auto;
  overflow: hidden;
}

.swl-build-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 2px;
  padding: 6px 6px 0;
  border-bottom: 1px solid #2b3546;
}

.swl-tab {
  padding: 4px 8px;
  border-radius: 3px 3px 0 0;
  color: #8d97a8;
  font-size: calc(11px * var(--swl-font-scale-body, 1));
}

.swl-tab:hover { color: #e8e3d8; }

.swl-tab-active {
  color: #10151d;
  background: #f5c542;
}

.swl-build-list {
  margin: 0;
  padding: 4px;
  list-style: none;
  overflow-y: auto;
}

.swl-build-item button {
  display: flex;
  align-items: baseline;
  gap: 8px;
  width: 100%;
  padding: 4px 6px;
  border-radius: 3px;
  text-align: left;
}

.swl-build-item button:hover { background: #233047; }

.swl-build-item button:disabled {
  cursor: not-allowed;
}

.swl-build-item button:disabled:hover { background: none; }

.swl-build-name { flex: 1; }

.swl-build-cost {
  color: #8d97a8;
  font-size: calc(11px * var(--swl-font-scale-body, 1));
}

.swl-build-locked .swl-build-name,
.swl-build-locked .swl-build-cost {
  color: #5c6678;
}

.swl-build-lock {
  color: #e0a33c;
  font-size: calc(10px * var(--swl-font-scale-body, 1));
}

/* --- The tutorial ------------------------------------------------------ */

.swl-tutorial {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 20;
}

.swl-tutorial-ring {
  position: absolute;
  border: 3px solid #f5c542;
  border-radius: 50%;
  box-shadow: 0 0 0 9999px #0000, 0 0 18px #f5c542cc;
  animation: swl-tutorial-pulse 1.6s ease-in-out infinite;
}

@keyframes swl-tutorial-pulse {
  0%, 100% { opacity: 0.55; transform: scale(1); }
  50% { opacity: 1; transform: scale(1.04); }
}

.swl-tutorial-arrow {
  position: absolute;
  width: 0;
  height: 0;
  border-top: 13px solid transparent;
  border-bottom: 13px solid transparent;
  border-left: 26px solid #f5c542;
  filter: drop-shadow(0 0 4px #000c);
  animation: swl-tutorial-nudge 0.9s ease-in-out infinite alternate;
}

@keyframes swl-tutorial-nudge {
  from { margin-left: 0; }
  to { margin-left: 6px; }
}

.swl-tutorial-box {
  position: absolute;
  width: 286px;
  box-sizing: border-box;
  padding: 10px 12px;
  border: 1px solid #f5c542;
  border-radius: 5px;
  background: linear-gradient(#1d2430f2, #131a24f2);
  box-shadow: 0 8px 24px #000b, inset 0 1px 0 #ffffff14;
  pointer-events: auto;
}

.swl-tutorial-step {
  margin: 0;
  color: #8d97a8;
  font-size: calc(10px * var(--swl-font-scale-body, 1));
  letter-spacing: 0.08em;
}

.swl-tutorial-title {
  margin: 2px 0 6px;
  color: #f5c542;
  font-family: var(--swl-font-display, system-ui, sans-serif);
  font-size: calc(15px * var(--swl-font-scale-display, 1));
  line-height: 1.1;
  text-transform: uppercase;
}

.swl-tutorial-lesson {
  margin: 0 0 4px;
  color: #e8e3d8;
  font-size: calc(12px * var(--swl-font-scale-body, 1));
  line-height: 1.35;
}

.swl-tutorial-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 8px;
}

.swl-tutorial-skip {
  color: #8d97a8;
  font-size: calc(11px * var(--swl-font-scale-body, 1));
  text-decoration: underline;
}

.swl-tutorial-next {
  padding: 4px 12px;
  border: 1px solid #f5c542;
  border-radius: 3px;
  background: #f5c542;
  color: #10151d;
  font-size: calc(12px * var(--swl-font-scale-body, 1));
  font-weight: 700;
}

.swl-tutorial-next:hover {
  background: #ffd75e;
}

/* --- The dialog -------------------------------------------------------- */

.swl-dialog-backdrop {
  position: absolute;
  inset: 0;
  z-index: 40;
  display: grid;
  place-items: center;
  background: var(--swl-scrim);
  pointer-events: auto;
}

.swl-dialog {
  width: min(420px, calc(100% - 32px));
  max-height: calc(100% - 48px);
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  padding: var(--swl-gap-lg);
  border: 1px solid var(--swl-border);
  border-top: 3px solid var(--swl-accent);
  border-radius: 6px;
  background: linear-gradient(var(--swl-surface-raised), var(--swl-surface));
  box-shadow: 0 10px 32px #000c, inset 0 1px 0 #ffffff14;
  pointer-events: auto;
  outline: none;
}

.swl-dialog:focus-visible {
  outline: 2px solid var(--swl-accent);
  outline-offset: 2px;
}

.swl-dialog-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--swl-gap);
}

.swl-dialog-title {
  margin: 0;
  color: var(--swl-accent);
  font-family: var(--swl-font-display, system-ui, sans-serif);
  font-size: calc(16px * var(--swl-font-scale-display, 1));
  line-height: 1.2;
  text-transform: uppercase;
}

.swl-dialog-close {
  flex: none;
  width: 24px;
  height: 24px;
  display: grid;
  place-items: center;
  border-radius: 3px;
  color: var(--swl-ink-muted);
  font-size: calc(18px * var(--swl-font-scale-body, 1));
  line-height: 1;
}

.swl-dialog-close:hover {
  background: #263043;
  color: var(--swl-ink);
}

.swl-dialog-close:focus-visible {
  outline: 2px solid var(--swl-accent);
  outline-offset: 1px;
}

.swl-dialog-body {
  margin-top: var(--swl-gap);
  /* A flex child must be allowed to shrink before overflow-y can scroll,
     so a long briefing stays inside the 760x600 stage. */
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  color: var(--swl-ink);
  font-size: calc(12px * var(--swl-font-scale-body, 1));
  line-height: 1.4;
}

.swl-dialog-combat { border-top-color: var(--swl-danger); }
.swl-dialog-result,
.swl-dialog-reward { border-top-color: var(--swl-success); }

/* --- The quest panels --------------------------------------------------- */

.swl-quest-panel {
  display: flex;
  flex-direction: column;
  gap: var(--swl-gap-lg);
}

.swl-quest-subtitle,
.swl-quest-won,
.swl-quest-lost {
  margin: 0;
  color: var(--swl-ink-muted);
}

.swl-quest-won { color: var(--swl-success); }
.swl-quest-lost { color: var(--swl-danger); }

.swl-quest-result-heading,
.swl-quest-rank,
.swl-quest-reward-title {
  margin: 0;
  color: var(--swl-ink-muted);
}

.swl-quest-difficulty {
  display: flex;
  align-items: center;
  gap: var(--swl-gap);
  margin: 0;
  padding: var(--swl-gap);
  border: 1px solid var(--swl-border);
  border-radius: 4px;
}

.swl-quest-difficulty legend {
  padding: 0 4px;
  color: var(--swl-ink-muted);
}

.swl-quest-team {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin: 0;
  padding: var(--swl-gap);
  border: 1px solid var(--swl-border);
  border-radius: 4px;
}

.swl-quest-team legend {
  padding: 0 4px;
  color: var(--swl-ink-muted);
}

.swl-quest-team-row {
  display: flex;
  align-items: center;
  gap: var(--swl-gap);
  color: var(--swl-ink-muted);
}

.swl-quest-team-row input[type='number'] {
  width: 4rem;
}

.swl-quest-team-echo {
  margin: 0;
  color: var(--swl-ink-muted);
}

/* The mission timer is the server's remaining seconds, not a local clock. */
.swl-quest-timer {
  margin: 0;
  color: #f5c542;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.swl-quest-star {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  color: var(--swl-accent);
}

.swl-quest-counters,
.swl-quest-roster,
.swl-quest-rewards {
  margin: 0;
  padding: 0;
  list-style: none;
}

.swl-quest-counters {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(110px, 1fr));
  gap: var(--swl-gap);
}

.swl-quest-counter {
  display: flex;
  justify-content: space-between;
  gap: var(--swl-gap);
  padding: 4px 8px;
  border: 1px solid var(--swl-border);
  border-radius: 4px;
  background: var(--swl-surface);
}

.swl-quest-counter dt { color: var(--swl-ink-muted); }
.swl-quest-counter dd { margin: 0; color: var(--swl-accent); font-weight: 700; }

.swl-quest-roster {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.swl-quest-unit {
  display: flex;
  justify-content: space-between;
  gap: var(--swl-gap);
  color: var(--swl-ink-muted);
}

.swl-quest-unit .swl-quest-dead { color: var(--swl-danger); }

.swl-quest-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: var(--swl-gap);
}

.swl-quest-buttons button {
  padding: 5px 10px;
  border: 1px solid var(--swl-border);
  border-radius: 4px;
  background: var(--swl-surface-raised);
}

.swl-quest-buttons button:hover:not(:disabled) { border-color: var(--swl-accent); }
.swl-quest-buttons button:disabled { color: var(--swl-ink-muted); cursor: not-allowed; }
.swl-quest-buttons .swl-quest-primary { border-color: var(--swl-accent); color: var(--swl-accent); }
.swl-quest-buttons button:focus-visible { outline: 2px solid var(--swl-accent); outline-offset: 1px; }

/* --- The assault result, history and combat HUD ------------------------- */

/* These panels live in the one shared dialog, so they reuse its surface and
   tokens. Nothing here is a second overlay, and nothing is drawn from an
   original's art: the portraits are text tiles with a charge bar. */
.swl-assault-panel {
  display: flex;
  flex-direction: column;
  gap: var(--swl-gap);
}

.swl-assault-won,
.swl-assault-lost {
  margin: 0;
  font-family: var(--swl-font-display, system-ui, sans-serif);
  font-size: calc(15px * var(--swl-font-scale-display, 1));
  text-transform: uppercase;
}

.swl-assault-won { color: var(--swl-success); }
.swl-assault-lost { color: var(--swl-danger); }

.swl-assault-heading {
  margin: 0;
  color: var(--swl-ink-muted);
}

.swl-assault-note {
  margin: 0;
  color: var(--swl-ink-muted);
  font-size: calc(11px * var(--swl-font-scale-body, 1));
}

.swl-assault-muted { color: var(--swl-ink-muted); }

.swl-assault-loot,
.swl-assault-roster,
.swl-assault-specials {
  margin: 0;
  padding: 0;
  list-style: none;
}

.swl-assault-loot {
  display: flex;
  flex-wrap: wrap;
  gap: var(--swl-gap);
}

.swl-assault-loot li {
  padding: 3px 8px;
  border: 1px solid var(--swl-border);
  border-radius: 4px;
  background: var(--swl-surface);
  color: var(--swl-accent);
  font-variant-numeric: tabular-nums;
}

.swl-assault-counts {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--swl-gap);
  margin: 0;
}

.swl-assault-count {
  display: flex;
  justify-content: space-between;
  gap: var(--swl-gap);
  padding: 4px 8px;
  border: 1px solid var(--swl-border);
  border-radius: 4px;
  background: var(--swl-surface);
}

.swl-assault-count dt { color: var(--swl-ink-muted); }
.swl-assault-count dd { margin: 0; color: var(--swl-accent); font-weight: 700; }

.swl-assault-opponent { margin: 0; color: var(--swl-ink-muted); }

.swl-assault-army {
  margin-top: var(--swl-gap);
  padding-top: var(--swl-gap);
  border-top: 1px solid var(--swl-border);
}

.swl-assault-army h4 {
  margin: 0 0 4px;
  color: var(--swl-accent);
  font-family: var(--swl-font-display, system-ui, sans-serif);
  font-size: calc(12px * var(--swl-font-scale-display, 1));
  text-transform: uppercase;
}

.swl-assault-roster {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.swl-assault-roster-row {
  display: flex;
  gap: var(--swl-gap);
  color: var(--swl-ink);
  font-size: calc(11px * var(--swl-font-scale-body, 1));
}

.swl-assault-roster-row span:nth-child(2) { margin-left: auto; color: var(--swl-accent); }

.swl-assault-countdown {
  margin: 0;
  color: var(--swl-accent);
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.swl-assault-tabs {
  display: flex;
  gap: var(--swl-gap);
}

.swl-assault-tabs button {
  padding: 4px 8px;
  border: 1px solid var(--swl-border);
  border-radius: 3px;
  color: var(--swl-ink-muted);
}

.swl-assault-tabs .swl-assault-tab-active {
  border-color: var(--swl-accent);
  color: var(--swl-accent);
}

.swl-assault-history {
  width: 100%;
  border-collapse: collapse;
  font-size: calc(11px * var(--swl-font-scale-body, 1));
}

.swl-assault-history th,
.swl-assault-history td {
  padding: 4px 6px;
  border-bottom: 1px solid var(--swl-border);
  text-align: left;
}

.swl-assault-history th { color: var(--swl-ink-muted); font-weight: 400; }
.swl-assault-history td { color: var(--swl-ink); }

.swl-assault-strategies {
  display: flex;
  flex-direction: column;
  gap: var(--swl-gap);
  margin: 0;
  padding: var(--swl-gap);
  border: 1px solid var(--swl-border);
  border-radius: 4px;
}

.swl-assault-strategies legend { padding: 0 4px; color: var(--swl-ink-muted); }

.swl-assault-strategy {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 2px var(--swl-gap);
  color: var(--swl-ink);
}

.swl-assault-strategy input { grid-row: span 2; }

.swl-assault-strategy-name { font-weight: 700; }

.swl-assault-strategy-note {
  color: var(--swl-ink-muted);
  font-size: calc(11px * var(--swl-font-scale-body, 1));
  line-height: 1.3;
}

.swl-assault-specials {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: var(--swl-gap);
}

.swl-assault-special {
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: var(--swl-gap);
  border: 1px solid var(--swl-border);
  border-radius: 4px;
  background: var(--swl-surface);
}

.swl-assault-special-idle { border-color: var(--swl-danger); }

.swl-assault-special-name {
  color: var(--swl-ink);
  font-weight: 700;
  font-size: calc(11px * var(--swl-font-scale-body, 1));
  overflow-wrap: anywhere;
}

.swl-assault-special-shape,
.swl-assault-special-state {
  color: var(--swl-ink-muted);
  font-size: calc(10px * var(--swl-font-scale-body, 1));
}

.swl-assault-special-idle .swl-assault-special-state { color: var(--swl-danger); }

/* The casting mask is the server's charge fraction, never a local animation. */
.swl-assault-special-track {
  display: block;
  height: 6px;
  overflow: hidden;
  border: 1px solid var(--swl-border);
  border-radius: 3px;
  background: #10151d;
}

.swl-assault-special-mask {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, #7fb3d5, var(--swl-accent));
}

.swl-assault-buttons {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: var(--swl-gap);
  margin-top: var(--swl-gap);
}

.swl-assault-buttons button {
  padding: 5px 10px;
  border: 1px solid var(--swl-border);
  border-radius: 4px;
  background: var(--swl-surface-raised);
}

.swl-assault-buttons button:hover:not(:disabled) { border-color: var(--swl-accent); }

.swl-assault-buttons button:disabled { color: var(--swl-ink-muted); cursor: not-allowed; }

.swl-assault-buttons .swl-assault-primary {
  border-color: var(--swl-accent);
  color: var(--swl-accent);
}

/* --- The onboarding family ---------------------------------------------- */

/* The launcher is a narrow strip between the goals and the chapter map. It
   holds gestures only: opening a panel never changes the world. */
.swl-onboarding-launcher {
  position: absolute;
  left: 316px;
  top: 58px;
  display: flex;
  flex-direction: column;
  gap: 3px;
  pointer-events: auto;
}

.swl-onboarding-launcher button {
  padding: 3px 8px;
  border: 1px solid var(--swl-border);
  border-radius: 3px;
  background: var(--swl-surface);
  color: var(--swl-ink-muted);
  font-size: calc(10px * var(--swl-font-scale-body, 1));
  text-align: left;
  white-space: nowrap;
}

.swl-onboarding-launcher button:hover,
.swl-onboarding-launcher button:focus-visible {
  border-color: var(--swl-accent);
  color: var(--swl-accent);
}

/* The help body reuses the tutorial overlay's type, so the panel reads as the
   same tutorial the arrow is pointing through. */
.swl-onboarding-help,
.swl-onboarding-next,
.swl-onboarding-confirm {
  display: flex;
  flex-direction: column;
  gap: var(--swl-gap);
}

.swl-onboarding-steps {
  display: flex;
  flex-direction: column;
  gap: var(--swl-gap);
  margin: 0;
  padding: 0;
  list-style: none;
}

.swl-onboarding-steps li {
  padding: var(--swl-gap);
  border: 1px solid var(--swl-border);
  border-radius: 4px;
  background: var(--swl-surface);
}

.swl-onboarding-steps .swl-onboarding-step-current {
  border-color: var(--swl-accent);
}

.swl-onboarding-empty,
.swl-onboarding-note {
  margin: 0;
  color: var(--swl-ink-muted);
}

.swl-onboarding-confirm-message {
  margin: 0;
  color: var(--swl-ink);
}

.swl-onboarding-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--swl-gap);
}

.swl-onboarding-actions button {
  padding: 5px 10px;
  border: 1px solid var(--swl-border);
  border-radius: 4px;
  background: var(--swl-surface-raised);
}

.swl-onboarding-actions button:hover:not(:disabled) { border-color: var(--swl-accent); }
.swl-onboarding-actions button:disabled { color: var(--swl-ink-muted); cursor: not-allowed; }
.swl-onboarding-actions .swl-onboarding-primary {
  border-color: var(--swl-accent);
  color: var(--swl-accent);
}

/* --- The feedback channel ---------------------------------------------- */

.swl-feedback {
  position: absolute;
  top: 54px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 30;
  display: flex;
  flex-direction: column;
  gap: var(--swl-gap);
  width: min(360px, calc(100% - 32px));
  pointer-events: none;
}

.swl-feedback-item {
  display: flex;
  align-items: flex-start;
  gap: var(--swl-gap);
  padding: var(--swl-gap) var(--swl-gap-lg);
  border: 1px solid var(--swl-border);
  border-left-width: 3px;
  border-radius: 4px;
  background: var(--swl-surface);
  box-shadow: 0 4px 14px #000a;
  font-size: calc(12px * var(--swl-font-scale-body, 1));
  line-height: 1.3;
}

.swl-feedback-success {
  border-left-color: var(--swl-success);
  color: var(--swl-ink);
}

.swl-feedback-error {
  border-left-color: var(--swl-danger);
  color: var(--swl-ink);
}

.swl-feedback-mark { flex: none; font-weight: 700; }
.swl-feedback-success .swl-feedback-mark { color: var(--swl-success); }
.swl-feedback-error .swl-feedback-mark { color: var(--swl-danger); }
.swl-feedback-text { white-space: pre-line; }

/* --- The army roster, team thumbnails and unit XP ----------------------- */

.swl-roster-columns {
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(0, 1fr);
  gap: var(--swl-gap-lg);
}

.swl-roster-heading {
  margin: 0 0 4px;
  color: var(--swl-accent);
  font-family: var(--swl-font-display, system-ui, sans-serif);
  font-size: calc(13px * var(--swl-font-scale-display, 1));
  text-transform: uppercase;
}

.swl-roster-note {
  margin: 2px 0;
  color: var(--swl-ink-muted);
  font-size: calc(11px * var(--swl-font-scale-body, 1));
}

.swl-roster-units,
.swl-roster-thumbs {
  margin: 0;
  padding: 0;
  list-style: none;
}

.swl-roster-unit {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 2px 0;
  border-bottom: 1px solid #38445a80;
}

.swl-roster-inspect {
  display: flex;
  flex: 1 1 auto;
  align-items: center;
  gap: 6px;
  min-width: 0;
  padding: 3px 4px;
  border-radius: 3px;
  text-align: left;
}

.swl-roster-inspect:hover,
.swl-roster-inspect-active {
  background: #27324a;
}

.swl-roster-unit-name {
  flex: 1 1 auto;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.swl-roster-unit-qty { color: var(--swl-accent); }
.swl-roster-unit-level { color: var(--swl-accent); font-size: calc(10px * var(--swl-font-scale-body, 1)); }

.swl-roster-unit input[type='number'] {
  width: 3.5rem;
  flex: none;
  background: var(--swl-surface);
  border: 1px solid var(--swl-border);
  border-radius: 3px;
  color: var(--swl-ink);
}

.swl-roster-team { margin-top: var(--swl-gap-lg); }

.swl-roster-thumbs {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.swl-roster-thumb {
  display: flex;
  flex-direction: column;
  min-width: 84px;
  padding: 5px 7px;
  border: 1px solid var(--swl-border);
  border-radius: 4px;
  background: var(--swl-surface);
  color: var(--swl-ink-muted);
  font-size: calc(11px * var(--swl-font-scale-body, 1));
}

.swl-roster-thumb-active {
  border-color: var(--swl-accent);
  color: var(--swl-ink);
  box-shadow: inset 0 1px 0 #f5c54255;
}

.swl-roster-thumb-name { font-weight: 700; }
.swl-roster-thumb-state { color: var(--swl-ink-muted); }

.swl-roster-xp {
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: var(--swl-gap);
  border: 1px solid var(--swl-border);
  border-radius: 4px;
  background: var(--swl-surface);
}

.swl-roster-xp-title,
.swl-roster-xp-level {
  margin: 0;
  color: var(--swl-accent);
  font-family: var(--swl-font-display, system-ui, sans-serif);
  font-size: calc(13px * var(--swl-font-scale-display, 1));
  letter-spacing: 0.04em;
}

.swl-roster-xp-name {
  margin: 0;
  color: var(--swl-ink);
  font-weight: 700;
}

.swl-roster-stars {
  margin: 0;
  color: var(--swl-accent);
  font-size: calc(16px * var(--swl-font-scale-body, 1));
  letter-spacing: 2px;
}

.swl-roster-xp-progress,
.swl-roster-xp-bonus,
.swl-roster-xp-hint {
  margin: 0;
  color: var(--swl-ink-muted);
  font-size: calc(11px * var(--swl-font-scale-body, 1));
}

.swl-roster-xp-hint { color: var(--swl-accent); }

.swl-roster-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--swl-gap);
  margin-top: var(--swl-gap-lg);
}

.swl-roster-actions button {
  padding: 5px 12px;
  border: 1px solid var(--swl-border);
  border-radius: 3px;
}

.swl-roster-actions .swl-roster-primary {
  border-color: var(--swl-accent);
  background: var(--swl-accent);
  color: #10151d;
  font-weight: 700;
}

.swl-roster-actions button:disabled { opacity: 0.5; cursor: default; }

/* --- The reusable UI chrome ---------------------------------------------
 * Tabs, pills, the popover and its cover, the zoom bound to the camera, the
 * speaker box and the collect/hurry affordances. All drawn with text and CSS:
 * none of the original's proprietary button or icon art is claimed.
 * ---------------------------------------------------------------------- */

.swl-chrome {
  position: absolute;
  right: 8px;
  top: 344px;
  width: 220px;
  max-height: 156px;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  gap: 4px;
  overflow-y: auto;
  padding: 6px 8px;
  border: 1px solid var(--swl-border);
  border-radius: 4px;
  background: rgba(19, 26, 36, 0.94);
  color: var(--swl-ink);
  font-size: calc(11px * var(--swl-font-scale-body, 1));
  pointer-events: auto;
  z-index: 12;
}

.swl-chrome-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.swl-chrome-title {
  color: var(--swl-accent);
  font-family: var(--swl-font-display, system-ui, sans-serif);
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.swl-chrome button {
  padding: 2px 6px;
  border: 1px solid var(--swl-border);
  border-radius: 3px;
  background: var(--swl-surface-raised);
}

.swl-chrome button:hover:not(:disabled) { border-color: var(--swl-accent); }
.swl-chrome button:disabled { opacity: 0.5; cursor: default; }

.swl-chrome-cover {
  position: absolute;
  inset: 0;
  z-index: 25;
  background: var(--swl-scrim);
}

.swl-chrome-popover {
  position: absolute;
  right: 12px;
  top: 376px;
  z-index: 26;
  width: 232px;
  box-sizing: border-box;
  padding: var(--swl-gap) var(--swl-gap-lg);
  border: 1px solid var(--swl-accent);
  border-radius: 4px;
  background: var(--swl-surface);
  box-shadow: 0 6px 20px #000a;
  pointer-events: auto;
}

.swl-chrome-popover-line { margin: 0 0 6px; line-height: 1.3; }
.swl-chrome-popover-ok { border-color: var(--swl-accent) !important; }

.swl-chrome-zoom {
  display: flex;
  align-items: center;
  gap: 4px;
}

.swl-chrome-zoom-step { min-width: 22px; }
.swl-chrome-zoom-range { flex: 1; min-width: 0; accent-color: var(--swl-accent); }
.swl-chrome-zoom-value { color: var(--swl-ink-muted); white-space: nowrap; }

.swl-chrome-actions { display: flex; gap: 4px; }

.swl-chrome-action {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 1px;
  text-align: left;
}

.swl-chrome-action-collect { border-left: 3px solid var(--swl-success) !important; }
.swl-chrome-action-hurry { border-left: 3px solid var(--swl-accent) !important; }
.swl-chrome-action-mark { color: var(--swl-accent); font-size: 14px; }
.swl-chrome-action-note { color: var(--swl-ink-muted); font-size: calc(10px * var(--swl-font-scale-body, 1)); }

.swl-chrome-notice { display: flex; flex-direction: column; gap: 4px; }

.swl-chrome-speaker {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  padding: 4px;
  border-left: 3px solid var(--swl-danger);
  background: var(--swl-surface-raised);
}

.swl-chrome-speaker-mark { color: var(--swl-danger); font-weight: 700; }
.swl-chrome-speaker-text { flex: 1; white-space: pre-line; }

.swl-chrome-tabs,
.swl-chrome-pills { display: flex; flex-wrap: wrap; gap: 2px; }

.swl-chrome-tab {
  padding: 2px 5px !important;
  border-radius: 3px !important;
  color: var(--swl-ink-muted);
}

.swl-chrome-tab-hover { border-color: var(--swl-accent) !important; color: var(--swl-ink); }
.swl-chrome-tab-selected { background: var(--swl-accent) !important; color: #10151d !important; font-weight: 700; }
.swl-chrome-pills .swl-chrome-tab { border-radius: 10px !important; }

.swl-chrome-catalogue {
  margin: 0;
  padding: 0;
  list-style: none;
  max-height: 56px;
  overflow-y: auto;
  touch-action: pan-y;
}

.swl-chrome-catalogue-item { width: 100%; text-align: left; }

.swl-chrome-attachable {
  position: absolute;
  z-index: 12;
  display: flex;
  flex-direction: column;
  align-items: center;
  transform: translate(-50%, -100%);
  color: var(--swl-accent);
  text-shadow: 0 1px 3px #000;
  pointer-events: none;
}

.swl-chrome-attach-arrow { font-size: 16px; line-height: 1; }
.swl-chrome-attach-label { font-size: calc(10px * var(--swl-font-scale-body, 1)); white-space: nowrap; }

.swl-chrome-popup-message { margin: 0 0 8px; white-space: pre-line; }
.swl-chrome-popup-actions { display: flex; justify-content: flex-end; }
.swl-chrome-popup-actions button { border-color: var(--swl-accent) !important; }

/* The hospital and attack-symbol panels, hosted by the one shared dialog. */
.swl-character-setup { display: flex; flex-direction: column; gap: 8px; }
.swl-hospital-description,
.swl-hospital-store,
.swl-hospital-empty,
.swl-attack-symbols-heading,
.swl-attack-symbols-subhead { margin: 0; }

.swl-hospital-store { color: var(--swl-ink-muted); }
.swl-hospital-units,
.swl-attack-symbols-stats,
.swl-attack-symbols-classes { margin: 0; padding: 0; list-style: none; }

.swl-hospital-units { display: flex; flex-direction: column; gap: 4px; max-height: 160px; overflow-y: auto; }
.swl-hospital-unit {
  display: grid;
  grid-template-columns: 1fr auto auto auto auto;
  align-items: center;
  gap: 6px;
  padding: 3px 4px;
  background: var(--swl-surface-raised);
}
.swl-hospital-unit-name { font-weight: 700; }
.swl-hospital-unit-cost { color: var(--swl-ink-muted); font-size: calc(10px * var(--swl-font-scale-body, 1)); }
.swl-hospital-help { margin: 0; white-space: pre-line; color: var(--swl-ink-muted); font-size: calc(10px * var(--swl-font-scale-body, 1)); }
.swl-hospital-resurrect-syringe { border-color: var(--swl-accent) !important; }

.swl-attack-symbols-stats { display: flex; flex-direction: column; gap: 3px; }
.swl-attack-symbols-stat { display: grid; grid-template-columns: 100px 1fr; gap: 6px; }
.swl-attack-symbols-stat dt { color: var(--swl-accent); }
.swl-attack-symbols-stat dd { margin: 0; }
.swl-attack-symbols-classes { columns: 2; font-size: calc(10px * var(--swl-font-scale-body, 1)); }
.swl-character-setup-actions { display: flex; justify-content: flex-end; }
`.trim();
}
