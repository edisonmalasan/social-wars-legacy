/**
 * The interface's stylesheet.
 *
 * The game was built for a 760 by 600 stage, so the interface is
 * **absolutely positioned** inside it and never reflowed: a panel that
 * moved would be a panel that covered something else.
 *
 * The colours are the game's own: an olive game bar with a golden
 * selection, a white speech bubble for the mayor, and the dark slate
 * surfaces of the contextual panels.
 */
export function uiCss(): string {
  return `
/*
 * The dialog and feedback tokens stay on the contextual panels. The game
 * bar and the mayor's bubble use their own tokens, named after the original
 * colours: olive rgb(97,104,7), selection rgb(233,221,81) and white. Keeping
 * them here means the HUD, the at-rest chrome and the tutorial share one
 * palette without scattering literals through the rules.
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

  /* The original game bar and its selected tab. */
  --swl-olive: #616807;
  --swl-ochre: #e9dd51;
  --swl-game-bar: var(--swl-olive);
  --swl-game-bar-hover: #454b06;
  --swl-game-bar-selected: var(--swl-ochre);
  --swl-game-ink: #fff8d0;
  --swl-game-label: #dcd69a;

  /* The mayor's speech bubble: white fill, blue title, dark body ink. */
  --swl-bubble: #ffffff;
  --swl-bubble-title: #143a9e;
  --swl-bubble-ink: #1b2430;
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
  background: linear-gradient(var(--swl-game-bar), var(--swl-olive));
  border-bottom: 1px solid #2f3305;
  box-shadow: 0 1px 0 var(--swl-game-bar-selected);
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
  background: var(--swl-game-bar-hover);
}

/* The pointer focus is restored here: .swl-readout suppresses the UA ring. */
.swl-readout:focus-visible {
  outline: 2px solid var(--swl-game-bar-selected);
  outline-offset: 1px;
}

.swl-readout-label {
  color: var(--swl-game-label);
  font-size: calc(10px * var(--swl-font-scale-body, 1));
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.swl-readout-value {
  color: var(--swl-game-ink);
  font-weight: 700;
}

/* Brighter tints than the panel palette: these sit on the dark olive bar. */
.swl-resource-gold .swl-readout-value { color: var(--swl-ochre); }
.swl-resource-wood .swl-readout-value { color: #f0d49a; }
.swl-resource-oil .swl-readout-value { color: #b6def7; }
.swl-resource-steel .swl-readout-value { color: #f3f6fb; }
.swl-resource-cash .swl-readout-value { color: #b6eeb6; }
.swl-resource-mana .swl-readout-value { color: #dcc4ff; }

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
  color: var(--swl-game-label);
  font-size: calc(10px * var(--swl-font-scale-body, 1));
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.swl-xp-track {
  display: block;
  width: 72px;
  height: 7px;
  overflow: hidden;
  border: 1px solid #2f3305;
  border-radius: 4px;
  background: #2b3004;
}

.swl-xp-fill {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, #b6def7, var(--swl-ochre));
}

.swl-xp-value {
  color: var(--swl-game-ink);
  font-size: calc(11px * var(--swl-font-scale-body, 1));
  font-variant-numeric: tabular-nums;
}

/* The bonus read-out: a reading of the server's own cycles, never a claim. */
.swl-bonus-status {
  display: flex;
  flex-direction: column;
  gap: 1px;
  padding: 2px 6px;
  border-left: 1px solid #2f3305;
  color: var(--swl-game-ink);
  font-size: calc(10px * var(--swl-font-scale-body, 1));
  font-variant-numeric: tabular-nums;
}

.swl-bonus-day { color: var(--swl-ochre); font-weight: 700; }
.swl-bonus-weekly { color: var(--swl-game-label); }

/* The bonus is a gesture: the client asks, and the server names the reward. */
/* The button qualifier beats the generic .swl-ui button reset above. */
.swl-ui button.swl-bonus {
  padding: 4px 8px;
  border: 1px solid var(--swl-game-bar-selected);
  border-radius: 3px;
  background: var(--swl-game-bar-selected);
  color: #1b2003;
  font-size: calc(11px * var(--swl-font-scale-body, 1));
  font-weight: 700;
}

.swl-ui button.swl-bonus:hover:not(:disabled) { background: #f4ea83; }

.swl-ui button.swl-bonus:focus-visible { outline: 2px solid #fff8d0; outline-offset: 1px; }

.swl-ui button.swl-bonus:disabled {
  border-color: #2f3305;
  background: var(--swl-game-bar-hover);
  color: #a8a97a;
  cursor: not-allowed;
}

.swl-army {
  padding: 4px 8px;
  color: var(--swl-game-label);
  font-size: calc(11px * var(--swl-font-scale-body, 1));
}

.swl-placing {
  align-self: center;
  padding: 4px 8px;
  color: var(--swl-ochre);
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

/* GUI/InfoPopup.as: the HUD's popover with its display timer and
   anchor-relative repositioning. The box is placed in viewport coordinates by
   the model; the readout's own popover stays the source of both lines. No
   original popup art is claimed. */
.swl-info-popup {
  position: fixed;
  pointer-events: none;
  z-index: 30;
  max-width: 260px;
  min-width: 180px;
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

/* GUI/InventoryItem.as: the stored items as a grid of draggable cells. The
   column and row come from the UI-only setPos layout; the Place button is the
   same request gesture as before, and no proprietary cell art is claimed. */
.swl-inventory-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 4px;
  margin: 6px 0 0;
  padding: 0;
  list-style: none;
}

.swl-inventory-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  padding: 4px;
  border: 1px dashed #38445a;
  border-radius: 3px;
  background: #10151d;
}

.swl-inventory-cell:hover { border-color: #f5c542; }

.swl-inventory-cell-name {
  overflow: hidden;
  color: #e8e3d8;
  font-size: calc(10px * var(--swl-font-scale-body, 1));
  text-overflow: ellipsis;
  white-space: nowrap;
}

.swl-inventory-cell-qty {
  color: #f5c542;
  font-size: calc(10px * var(--swl-font-scale-body, 1));
  font-weight: 700;
}

.swl-ui .swl-inventory-cell .swl-inventory-place {
  padding: 1px 4px;
  font-size: calc(10px * var(--swl-font-scale-body, 1));
}

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

/* --- The mystery-box popups -------------------------------------------- */

.swl-mystery-launcher {
  position: absolute;
  right: 8px;
  bottom: 132px;
  max-width: 320px;
  padding: 4px 8px;
  border: 1px solid #38445a;
  border-radius: 4px;
  background: rgba(16, 21, 29, 0.92);
  color: #f2e6c8;
  font-size: calc(10px * var(--swl-font-scale-body, 1));
  pointer-events: auto;
}

.swl-mystery-launcher-summary { cursor: pointer; color: #f5c542; font-weight: 700; }
.swl-mystery-launcher-list { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 4px; }

.swl-ui button.swl-mystery-launch {
  padding: 3px 6px;
  border: 1px solid #4a6a8a;
  border-radius: 3px;
  background: #223047;
  color: #f2e6c8;
}

.swl-ui button.swl-mystery-launch:disabled {
  border-color: #38445a;
  background: #1d2430;
  color: #5c6678;
  cursor: not-allowed;
}

.swl-mystery-title,
.swl-mystery-win { font-weight: 700; color: #f5c542; margin: 2px 0; }
.swl-mystery-prompt,
.swl-mystery-storage { margin: 2px 0; color: var(--swl-ink-muted); white-space: pre-line; }
.swl-mystery-banner,
.swl-mystery-week { margin: 4px 0; color: #f2e6c8; white-space: pre-line; }
.swl-mystery-rows { display: flex; flex-direction: column; gap: 4px; margin: 6px 0; }
.swl-mystery-row { display: flex; gap: 6px; align-items: baseline; }
.swl-mystery-rarity { color: #f5c542; min-width: 64px; }
.swl-mystery-candidates { display: flex; flex-wrap: wrap; gap: 6px; }
.swl-mystery-won { margin: 6px 0; padding-left: 18px; }
.swl-mystery-price { color: #a9d7ff; margin: 2px 0; }
.swl-mystery-unavailable { color: var(--swl-ink-muted); font-style: italic; }

.swl-ui button.swl-mystery-buy,
.swl-ui button.swl-mystery-ok {
  padding: 4px 8px;
  border: 1px solid #4a6a8a;
  border-radius: 3px;
  background: #223047;
  color: #f2e6c8;
  margin: 2px 4px 0 0;
}

.swl-ui button.swl-mystery-buy:disabled {
  border-color: #38445a;
  background: #1d2430;
  color: #5c6678;
  cursor: not-allowed;
}

/* --- The soul-mixer help and turbine ----------------------------------- */

.swl-ui button.swl-soulmixer-launch {
  position: absolute;
  right: 8px;
  bottom: 106px;
  padding: 3px 6px;
  border: 1px solid #4a6a8a;
  border-radius: 3px;
  background: #223047;
  color: #f2e6c8;
  font-size: calc(10px * var(--swl-font-scale-body, 1));
  pointer-events: auto;
}

.swl-soulmixer-help {
  margin: 4px 0 8px;
  color: var(--swl-ink-muted);
  white-space: pre-line;
  font-size: calc(11px * var(--swl-font-scale-body, 1));
}

.swl-soulmixer-turbina {
  margin: 6px 0;
  padding: 6px 8px;
  border: 1px solid #38445a;
  border-radius: 4px;
  background: rgba(16, 21, 29, 0.92);
}

.swl-soulmixer-turbina-label { margin: 0; color: #f5c542; font-weight: 700; }
.swl-soulmixer-turbina-state { margin: 2px 0 0; color: #f2e6c8; }
.swl-soulmixer-turbina-empty { margin: 2px 0 0; color: var(--swl-ink-muted); font-style: italic; }

.swl-ui button.swl-soulmixer-close {
  padding: 4px 8px;
  border: 1px solid #4a6a8a;
  border-radius: 3px;
  background: #223047;
  color: #f2e6c8;
}

/* --- Atom Fusion and the robot-research centres ----------------------- */

.swl-fusion-launcher { position: absolute; right: 8px; bottom: 130px; }

.swl-fusion-launcher-summary {
  cursor: pointer;
  color: #f5c542;
  font-size: calc(10px * var(--swl-font-scale-body, 1));
}

.swl-fusion-launcher-list { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 4px; }

.swl-ui button.swl-fusion-launch {
  padding: 3px 6px;
  border: 1px solid #4a6a8a;
  border-radius: 3px;
  background: #223047;
  color: #f2e6c8;
  font-size: calc(10px * var(--swl-font-scale-body, 1));
}

.swl-fusion { max-width: 560px; font-size: calc(11px * var(--swl-font-scale-body, 1)); }
.swl-fusion-title { margin: 2px 0; color: #f5c542; font-weight: 700; }
.swl-fusion-description { margin: 2px 0 8px; color: var(--swl-ink-muted); white-space: pre-line; }
.swl-fusion section { margin: 8px 0; padding: 6px 8px; border: 1px solid #38445a; border-radius: 4px; background: rgba(16, 21, 29, 0.92); }
.swl-fusion h3 { margin: 0 0 4px; color: #f5c542; font-size: 1em; }
.swl-fusion-empty { margin: 2px 0; color: var(--swl-ink-muted); font-style: italic; }
.swl-fusion-gate { margin: 4px 0 0; color: var(--swl-danger); }
.swl-fusion-input-list, .swl-fusion-candidate-list { margin: 2px 0; padding-left: 18px; }
.swl-fusion-candidate-list { max-height: 130px; overflow-y: auto; }
.swl-fusion-power-value { margin: 2px 0; color: #a9d7ff; font-weight: 700; }
.swl-fusion-result-value { margin: 2px 0; color: #8fd694; font-weight: 700; }
.swl-fusion-powerup-table { width: 100%; border-collapse: collapse; }
.swl-fusion-powerup-table th, .swl-fusion-powerup-table td { padding: 2px 4px; text-align: left; border-bottom: 1px solid #2b3444; }
.swl-fusion-powerup-table tr[data-swl-current='true'] td { color: #f5c542; }

.swl-ui button.swl-fusion-action {
  padding: 3px 8px;
  border: 1px solid #4a6a8a;
  border-radius: 3px;
  background: #223047;
  color: #f2e6c8;
}
.swl-ui button.swl-fusion-close { margin-top: 8px; }

.swl-research { max-width: 560px; font-size: calc(11px * var(--swl-font-scale-body, 1)); }
.swl-research-title { margin: 2px 0 8px; color: #f5c542; font-weight: 700; }
.swl-research section { margin: 8px 0; padding: 6px 8px; border: 1px solid #38445a; border-radius: 4px; background: rgba(16, 21, 29, 0.92); }
.swl-research h3 { margin: 0 0 4px; color: #f5c542; font-size: 1em; }
.swl-research-progress-label { margin: 0 0 4px; }
.swl-research-bar { height: 8px; border: 1px solid #38445a; border-radius: 4px; background: #10131a; }
.swl-research-bar-fill { display: block; height: 100%; background: #f5c542; }
.swl-research-item-name { margin: 2px 0; color: #f2e6c8; font-weight: 700; }
.swl-research-item-cash { margin: 2px 0; color: #a9d7ff; }
.swl-research-track { display: flex; flex-wrap: wrap; gap: 6px; margin: 6px 0 0; padding-left: 18px; }
.swl-research-track li[data-swl-current='true'] { color: #f5c542; font-weight: 700; }
.swl-research-countdown-label { margin: 0; color: #f5c542; font-weight: 700; }
.swl-research-countdown-value { margin: 2px 0; color: #a9d7ff; }
.swl-research-hint { margin: 6px 0; color: var(--swl-ink-muted); }
.swl-research-help-title { margin: 0; color: #f5c542; font-weight: 700; }
.swl-research-help-hint { margin: 2px 0; color: var(--swl-ink-muted); }
.swl-research-help-friends { margin: 4px 0; padding-left: 18px; }
.swl-research-actions { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }

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
  border: 1px solid var(--swl-ochre);
  border-radius: 3px;
  background: var(--swl-olive);
  text-align: center;
}

.swl-neighbour-portrait {
  height: 28px;
  margin-bottom: 3px;
  border-radius: 3px;
  background: #3d4305;
}

.swl-neighbour-name {
  color: var(--swl-game-ink);
  font-size: calc(11px * var(--swl-font-scale-body, 1));
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.swl-neighbour-level,
.swl-neighbour-xp {
  color: var(--swl-game-label);
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
  color: #1b2003;
  background: var(--swl-game-bar-selected);
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
  border: 3px solid var(--swl-ochre);
  border-radius: 50%;
  box-shadow: 0 0 0 9999px #0000, 0 0 18px var(--swl-ochre);
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
  border-left: 26px solid var(--swl-ochre);
  filter: drop-shadow(0 0 4px #000c);
  animation: swl-tutorial-nudge 0.9s ease-in-out infinite alternate;
}

@keyframes swl-tutorial-nudge {
  from { margin-left: 0; }
  to { margin-left: 6px; }
}

/*
 * The mayor's box keeps its original footprint: the step positions in the
 * client were laid out for a 286 by 172 box on the 760 by 600 stage. Only
 * its paint changes - a white speech bubble with a CSS tail pointing up
 * towards the place the step marks. The tail is drawn with two triangles
 * (an ochre outline under a white fill) so no image asset is needed.
 */
.swl-tutorial-box {
  position: absolute;
  width: 286px;
  box-sizing: border-box;
  padding: 10px 12px;
  border: 1px solid var(--swl-ochre);
  border-radius: 5px;
  background: var(--swl-bubble);
  box-shadow: 0 8px 24px #000b;
  pointer-events: auto;
}

.swl-tutorial-bubble {
  background: var(--swl-bubble);
  color: var(--swl-bubble-ink);
}

.swl-tutorial-bubble::before,
.swl-tutorial-bubble::after {
  content: '';
  position: absolute;
  left: 40px;
  width: 0;
  height: 0;
  border-left: 11px solid transparent;
  border-right: 11px solid transparent;
}

.swl-tutorial-bubble::before {
  top: -12px;
  border-bottom: 12px solid var(--swl-ochre);
}

.swl-tutorial-bubble::after {
  top: -10px;
  border-bottom: 10px solid var(--swl-bubble);
}

/* Scoped to the bubble: the help panel reuses these classes on dark slate. */
.swl-tutorial-bubble .swl-tutorial-step {
  color: #4a5570;
}

.swl-tutorial-bubble .swl-tutorial-title {
  color: var(--swl-bubble-title);
  font-weight: 800;
}

.swl-tutorial-bubble .swl-tutorial-lesson {
  color: var(--swl-bubble-ink);
}

.swl-tutorial-bubble .swl-tutorial-skip {
  color: var(--swl-bubble-title);
}

.swl-tutorial-bubble .swl-tutorial-next {
  border-color: var(--swl-olive);
  background: var(--swl-game-bar);
  color: var(--swl-game-ink);
}

.swl-tutorial-bubble .swl-tutorial-next:hover {
  background: var(--swl-game-bar-hover);
}

.swl-tutorial-bubble .swl-tutorial-next:focus-visible {
  outline: 2px solid var(--swl-bubble-title);
  outline-offset: 2px;
}

.swl-tutorial-bubble .swl-tutorial-skip:focus-visible {
  outline: 2px solid var(--swl-bubble-title);
  outline-offset: 2px;
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

/* --- The player-owned resource market --------------------------------- */
/* The chrome's head keeps the market gesture beside the help button. */
.swl-chrome-head-actions { display: flex; align-items: center; gap: 4px; }

.swl-ui button.swl-market-launcher {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 0 4px;
  color: var(--swl-accent);
  font-size: calc(10px * var(--swl-font-scale-body, 1));
  white-space: nowrap;
}

.swl-market-art-badge { width: 24px; height: 24px; flex: 0 0 24px; }
.swl-market-art-empty { width: 56px; height: 42px; flex: 0 0 56px; }
.swl-market-art-resource { width: 28px; height: 28px; flex: 0 0 28px; }
.swl-market-art-exhausted { width: 18px; height: 18px; flex: 0 0 18px; vertical-align: middle; }

.swl-market {
  max-width: 540px;
  display: flex;
  flex-direction: column;
  gap: var(--swl-gap);
  font-size: calc(11px * var(--swl-font-scale-body, 1));
}

.swl-market-head { display: flex; align-items: center; gap: var(--swl-gap); }
.swl-market-title { margin: 0; color: var(--swl-accent); font-weight: 700; font-size: 1.2em; }
.swl-market-note { margin: 2px 0 0; color: var(--swl-ink-muted); }

.swl-market-empty {
  display: flex;
  align-items: center;
  gap: var(--swl-gap);
  padding: var(--swl-gap);
  border: 1px dashed var(--swl-border);
  border-radius: 4px;
  background: var(--swl-surface-raised);
}
.swl-market-empty-list { margin: 0; padding-left: 16px; color: var(--swl-ink-muted); }

.swl-market-counters,
.swl-market-wallet {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 4px var(--swl-gap-lg);
  margin: 0;
  padding: var(--swl-gap);
  border: 1px solid var(--swl-border);
  border-radius: 4px;
  background: rgba(16, 21, 29, 0.92);
}
.swl-market-counters > div,
.swl-market-wallet > div { display: flex; justify-content: space-between; gap: 6px; }
.swl-market-counters dt,
.swl-market-wallet dt { color: var(--swl-ink-muted); }
.swl-market-counters dd,
.swl-market-wallet dd { margin: 0; color: var(--swl-accent); font-weight: 700; text-align: right; }

.swl-market-display { margin: 0; color: var(--swl-ink-muted); white-space: pre-line; }
.swl-market-exhaustion {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 0;
  color: var(--swl-danger);
}

.swl-market-rows { display: flex; flex-direction: column; gap: 6px; margin: 0; padding: 0; list-style: none; }
.swl-market-row {
  display: flex;
  gap: var(--swl-gap);
  padding: 6px;
  border: 1px solid var(--swl-border);
  border-radius: 4px;
  background: var(--swl-surface-raised);
}
.swl-market-row-main { flex: 1; min-width: 0; }
.swl-market-row-name { margin: 0; color: var(--swl-ink); font-weight: 700; }
.swl-market-row-key { color: var(--swl-ink-muted); font-weight: 400; }
.swl-market-row-numbers { margin: 2px 0 4px; color: var(--swl-ink-muted); }
.swl-market-actions { display: flex; flex-wrap: wrap; gap: 4px; }
.swl-ui button.swl-market-trade {
  padding: 3px 6px;
  border: 1px solid var(--swl-border);
  border-radius: 3px;
  background: var(--swl-surface);
}
.swl-ui button.swl-market-buy { border-color: var(--swl-success); color: var(--swl-success); }
.swl-ui button.swl-market-sell { border-color: var(--swl-accent); color: var(--swl-accent); }
.swl-market-footer { justify-content: flex-end; }
.swl-ui button.swl-market-close { padding: 4px 12px; border-color: var(--swl-accent); }

/* --- The store's item-button chrome ------------------------------------ */
/* Original inline geometry only: no image files and no copied artwork. */
.swl-store-items { display: flex; flex-direction: column; gap: var(--swl-gap); }
.swl-store-cash { margin: 0; color: var(--swl-ink-muted); }
.swl-store-cash [data-swl-server] { color: var(--swl-accent); font-weight: 700; }

.swl-store-empty {
  display: flex;
  align-items: center;
  gap: var(--swl-gap);
  padding: var(--swl-gap);
  border: 1px dashed var(--swl-border);
  border-radius: 4px;
  background: var(--swl-surface-raised);
}
.swl-store-empty-list { margin: 0; padding-left: 16px; color: var(--swl-ink-muted); }
.swl-store-art-empty { width: 56px; height: 42px; flex: 0 0 56px; }

.swl-store-item-list { display: flex; flex-direction: column; gap: 6px; margin: 0; padding: 0; list-style: none; }
.swl-store-item {
  display: flex;
  gap: var(--swl-gap);
  padding: 6px;
  border: 1px solid #4a6a8a;
  border-radius: 4px;
  background: linear-gradient(180deg, #223047, #1d2430);
}
.swl-store-art-badge { width: 40px; height: 40px; flex: 0 0 40px; }
.swl-store-item-main { flex: 1; min-width: 0; }
.swl-store-item-name { margin: 0; color: var(--swl-ink); font-weight: 700; }
.swl-store-item-flag {
  margin-left: 6px;
  padding: 1px 4px;
  border-radius: 3px;
  background: #f5c542;
  color: #1d2430;
  font-size: calc(9px * var(--swl-font-scale-body, 1));
}
.swl-store-item-contents { margin: 2px 0 4px; color: var(--swl-ink-muted); }
.swl-store-item-content-note { color: #8d97a8; font-style: italic; }
.swl-store-item-tiers { display: flex; flex-wrap: wrap; gap: 4px; }
.swl-store-art-cash { width: 16px; height: 16px; flex: 0 0 16px; vertical-align: middle; }
.swl-ui button.swl-store-item-buy {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 6px;
  border: 1px solid #4a6a8a;
  border-radius: 3px;
  background: #223047;
  color: var(--swl-ink);
  font-size: calc(10px * var(--swl-font-scale-body, 1));
}
.swl-ui button.swl-store-item-buy:disabled {
  border-color: var(--swl-border);
  background: #1d2430;
  color: #5c6678;
  cursor: not-allowed;
}

/* Resource buttons / icon chrome — original inline geometry only. */
.swl-ui button.swl-resource-buttons-launcher {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 2px 7px 2px 3px;
  border: 1px solid #4a6a8a;
  border-radius: 4px;
  background: #223047;
  color: var(--swl-ink);
  font-size: calc(10px * var(--swl-font-scale-body, 1));
}
.swl-ui button.swl-resource-buttons-launcher[data-swl-open='true'] {
  border-color: var(--swl-accent);
  background: #2b3b55;
}
.swl-resource-buttons-art-badge { width: 26px; height: 26px; flex: 0 0 26px; }

.swl-resource-buttons { display: flex; flex-direction: column; gap: var(--swl-gap); }
.swl-resource-buttons-head { display: flex; align-items: center; gap: var(--swl-gap); }
.swl-resource-buttons-head .swl-resource-buttons-art-badge { width: 40px; height: 40px; flex: 0 0 40px; }
.swl-resource-buttons-title { margin: 0; color: var(--swl-ink); font-weight: 700; }
.swl-resource-buttons-note { margin: 2px 0 0; color: var(--swl-ink-muted); }

.swl-resource-buttons-tabs {
  display: flex;
  gap: 4px;
  border-bottom: 1px solid var(--swl-border);
}
.swl-resource-buttons-tab {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px 2px;
  border: 1px solid var(--swl-accent);
  border-bottom-color: transparent;
  border-radius: 3px 3px 0 0;
  background: #223047;
  color: var(--swl-ink);
}
.swl-resource-buttons-art-tab { width: 28px; height: 14px; }

.swl-resource-buttons-list {
  display: flex;
  flex-direction: column;
  gap: 5px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.swl-resource-buttons-shortcut {
  display: flex;
  align-items: flex-start;
  gap: var(--swl-gap);
  padding: 5px 7px;
  border: 1px solid #4a6a8a;
  border-radius: 4px;
  background: linear-gradient(180deg, #223047, #1d2430);
}
.swl-resource-buttons-art-icon { width: 24px; height: 24px; flex: 0 0 24px; }
.swl-resource-buttons-shortcut-main { flex: 1; min-width: 0; }
.swl-resource-buttons-label { margin: 0; color: var(--swl-ink); font-weight: 700; }
.swl-resource-buttons-numbers { margin: 2px 0; color: var(--swl-ink-muted); }
.swl-resource-buttons-numbers [data-swl-server] { color: var(--swl-accent); font-weight: 700; }
.swl-resource-buttons-limit { color: #8d97a8; font-style: italic; }
.swl-resource-buttons-trades { display: flex; flex-wrap: wrap; gap: 4px; }
.swl-ui button.swl-resource-buttons-trade {
  padding: 2px 6px;
  border: 1px solid #4a6a8a;
  border-radius: 3px;
  background: #2b3b55;
  color: var(--swl-ink);
  font-size: calc(10px * var(--swl-font-scale-body, 1));
}

.swl-resource-buttons-empty {
  display: flex;
  align-items: center;
  gap: var(--swl-gap);
  padding: var(--swl-gap);
  border: 1px dashed var(--swl-border);
  border-radius: 4px;
  background: var(--swl-surface-raised);
}
.swl-resource-buttons-art-empty { width: 56px; height: 42px; flex: 0 0 56px; }
.swl-resource-buttons-empty-list { margin: 0; padding-left: 16px; color: var(--swl-ink-muted); }
.swl-resource-buttons-footer { display: flex; justify-content: flex-end; }
.swl-ui button.swl-resource-buttons-close {
  padding: 3px 10px;
  border: 1px solid #4a6a8a;
  border-radius: 3px;
  background: #223047;
  color: var(--swl-ink);
}

/* --- The extended portrait popup, icon panel and assault portraits -------- */

/* All three shells draw only server-owned values. Every mark is original
   inline SVG geometry, so no art asset or image reference is needed here. */
.swl-portrait-icons {
  display: grid;
  gap: 4px;
  margin: 4px 0;
}

.swl-portrait-icon {
  display: flex;
  align-items: center;
  gap: 4px;
  min-width: 0;
  padding: 2px 4px;
  border: 1px solid var(--swl-border);
  border-radius: 3px;
  background: var(--swl-surface-raised);
}

.swl-portrait-icon-glyph { width: 18px; height: 18px; flex: 0 0 18px; }
.swl-portrait-icon-label {
  overflow: hidden;
  color: var(--swl-ink-muted);
  font-size: calc(10px * var(--swl-font-scale-body, 1));
  text-overflow: ellipsis;
  white-space: nowrap;
}
.swl-portrait-icon-amount {
  margin-left: auto;
  color: var(--swl-accent);
  font-variant-numeric: tabular-nums;
}

.swl-portrait-icons-empty,
.swl-portrait-launcher-empty,
.swl-assault-portraits-empty {
  margin: 4px 0;
  color: var(--swl-ink-muted);
  font-size: calc(11px * var(--swl-font-scale-body, 1));
}

.swl-ui button.swl-portrait-launcher {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin: 4px 0;
  padding: 3px 8px 3px 3px;
  border: 1px solid var(--swl-accent);
  border-radius: 4px;
  background: var(--swl-surface-raised);
  color: var(--swl-ink);
}
.swl-ui button.swl-portrait-launcher:disabled {
  border-color: var(--swl-border);
  color: var(--swl-ink-muted);
  cursor: not-allowed;
}
.swl-portrait-figure { width: 32px; height: 40px; flex: 0 0 32px; }
.swl-portrait-launcher-name { font-weight: 700; }
.swl-portrait-launcher-count { color: var(--swl-accent); font-variant-numeric: tabular-nums; }

.swl-portrait-popup {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}
.swl-portrait-popup .swl-portrait-figure { width: 72px; height: 88px; flex: 0 0 72px; }
.swl-portrait-popup-name { margin: 0; font-weight: 700; }
.swl-portrait-popup-count,
.swl-portrait-popup-level,
.swl-portrait-popup-note { margin: 0; color: var(--swl-ink-muted); }

.swl-assault-portraits {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: 0 0 8px;
  padding: 0;
  list-style: none;
}
.swl-assault-portrait {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 4px;
  border: 1px solid var(--swl-border);
  border-radius: 4px;
  background: var(--swl-surface-raised);
}
.swl-assault-portrait-excluded { opacity: 0.55; }
.swl-assault-portrait-name { font-size: calc(10px * var(--swl-font-scale-body, 1)); }
.swl-assault-portrait-count { color: var(--swl-accent); font-variant-numeric: tabular-nums; }

/* --- The Original art gallery -------------------------------------------
 * The marks are inline data URLs generated at render time, so the grid needs
 * no image files and no network. It stays inside the shared dialog and keeps
 * the CC0 notice beside the work it covers.
 */
.swl-ui button.swl-original-art-launcher {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin: 4px 0;
  padding: 3px 8px;
  border: 1px solid var(--swl-accent);
  border-radius: 4px;
  background: var(--swl-surface-raised);
  color: var(--swl-ink);
}
.swl-original-art-launcher-count {
  color: var(--swl-accent);
  font-variant-numeric: tabular-nums;
}
.swl-original-art {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--swl-gap);
  max-width: 420px;
}
.swl-original-art-heading { margin: 0; font-weight: 700; }
.swl-original-art-intro,
.swl-original-art-caption {
  margin: 0;
  color: var(--swl-ink-muted);
  font-size: calc(11px * var(--swl-font-scale-body, 1));
  text-align: center;
}
.swl-original-art-grid {
  display: grid;
  grid-template-columns: repeat(4, 64px);
  gap: 6px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.swl-original-art-mark {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 3px;
  border: 1px solid var(--swl-border);
  border-radius: 4px;
  background: var(--swl-surface-raised);
}
.swl-original-art-img {
  display: block;
  width: 64px;
  height: 64px;
  image-rendering: auto;
}
.swl-original-art-name {
  max-width: 64px;
  overflow: hidden;
  color: var(--swl-ink-muted);
  font-size: calc(9px * var(--swl-font-scale-body, 1));
  text-align: center;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.swl-original-art-licence {
  margin: 0;
  padding: 6px 8px;
  border: 1px solid var(--swl-border);
  border-radius: 4px;
  color: var(--swl-accent);
  font-size: calc(11px * var(--swl-font-scale-body, 1));
  text-align: center;
}
.swl-original-art-details {
  width: 100%;
  color: var(--swl-ink-muted);
  font-size: calc(10px * var(--swl-font-scale-body, 1));
}
.swl-original-art-details summary { cursor: pointer; }
.swl-original-art-notice {
  max-height: 120px;
  overflow: auto;
  margin: 4px 0;
  padding: 6px;
  border-radius: 3px;
  background: var(--swl-surface);
  white-space: pre-wrap;
  word-break: break-word;
}
.swl-original-art-statement { margin: 4px 0; }
.swl-ui button.swl-original-art-close {
  padding: 5px 14px;
  border: 1px solid var(--swl-border);
  border-radius: 4px;
  background: var(--swl-surface-raised);
  color: var(--swl-ink);
}

/* --- The Original FX panel ---------------------------------------------
 * Each stage stacks the generator's six inline frames. One CSS animation,
 * offset per frame with a negative delay, cycles them without a client-side
 * clock or any game state. The reduced-motion rule leaves a single still.
 */
.swl-ui button.swl-original-fx-launcher {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin: 4px 0;
  padding: 3px 8px;
  border: 1px solid var(--swl-accent);
  border-radius: 4px;
  background: var(--swl-surface-raised);
  color: var(--swl-ink);
}
.swl-original-fx-launcher-count {
  color: var(--swl-accent);
  font-variant-numeric: tabular-nums;
}
.swl-original-fx {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--swl-gap);
  max-width: 420px;
}
.swl-original-fx-heading { margin: 0; font-weight: 700; }
.swl-original-fx-intro,
.swl-original-fx-motion,
.swl-original-fx-caption {
  margin: 0;
  color: var(--swl-ink-muted);
  font-size: calc(11px * var(--swl-font-scale-body, 1));
  text-align: center;
}
.swl-original-fx-list {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: var(--swl-gap-lg);
  margin: 0;
  padding: 0;
  list-style: none;
}
.swl-original-fx-sequence {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  padding: 6px;
  border: 1px solid var(--swl-border);
  border-radius: 4px;
  background: var(--swl-surface-raised);
}
.swl-original-fx-stage {
  position: relative;
  width: 64px;
  height: 64px;
  overflow: hidden;
  border-radius: 3px;
  background: var(--swl-surface);
}
.swl-original-fx-frame {
  position: absolute;
  inset: 0;
  display: block;
  width: 64px;
  height: 64px;
  opacity: 0;
  animation: swl-original-fx-cycle 1.2s steps(1, end) infinite;
}
.swl-original-fx-frame[data-swl-fx-frame='0'] { animation-delay: 0ms; }
.swl-original-fx-frame[data-swl-fx-frame='1'] { animation-delay: -200ms; }
.swl-original-fx-frame[data-swl-fx-frame='2'] { animation-delay: -400ms; }
.swl-original-fx-frame[data-swl-fx-frame='3'] { animation-delay: -600ms; }
.swl-original-fx-frame[data-swl-fx-frame='4'] { animation-delay: -800ms; }
.swl-original-fx-frame[data-swl-fx-frame='5'] { animation-delay: -1000ms; }
@keyframes swl-original-fx-cycle {
  0% { opacity: 1; }
  16.6667% { opacity: 0; }
  100% { opacity: 0; }
}
.swl-original-fx-name {
  color: var(--swl-ink);
  font-weight: 700;
}
.swl-original-fx-detail {
  color: var(--swl-ink-muted);
  font-size: calc(10px * var(--swl-font-scale-body, 1));
}
.swl-original-fx-licence {
  margin: 0;
  padding: 6px 8px;
  border: 1px solid var(--swl-border);
  border-radius: 4px;
  color: var(--swl-accent);
  font-size: calc(11px * var(--swl-font-scale-body, 1));
  text-align: center;
}
.swl-original-fx-details {
  width: 100%;
  color: var(--swl-ink-muted);
  font-size: calc(10px * var(--swl-font-scale-body, 1));
}
.swl-original-fx-details summary { cursor: pointer; }
.swl-original-fx-notice {
  max-height: 120px;
  overflow: auto;
  margin: 4px 0;
  padding: 6px;
  border-radius: 3px;
  background: var(--swl-surface);
  white-space: pre-wrap;
  word-break: break-word;
}
.swl-original-fx-statement { margin: 4px 0; }
.swl-ui button.swl-original-fx-close {
  padding: 5px 14px;
  border: 1px solid var(--swl-border);
  border-radius: 4px;
  background: var(--swl-surface-raised);
  color: var(--swl-ink);
}
@media (prefers-reduced-motion: reduce) {
  .swl-original-fx-frame {
    animation: none;
    opacity: 0;
  }
  .swl-original-fx-frame[data-swl-fx-first='true'] { opacity: 1; }
}
`.trim();
}
