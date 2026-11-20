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

.swl-inventory {
  position: absolute;
  right: 8px;
  top: 104px;
  width: 220px;
  max-height: 240px;
  box-sizing: border-box;
  overflow-y: auto;
  padding: 8px 10px;
  border: 1px solid #38445a;
  border-radius: 4px;
  background: #131a24;
  pointer-events: auto;
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
  overflow-y: auto;
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
`.trim();
}
