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

/* --- The top bar ------------------------------------------------------- */

.swl-hud {
  position: absolute;
  left: 0;
  right: 0;
  top: 0;
  height: 34px;
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
  top: 44px;
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
  font-size: calc(9px * var(--swl-font-scale-body, 1));
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

/* --- The goal panel --------------------------------------------------- */

.swl-goals {
  position: absolute;
  left: 8px;
  top: 44px;
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
  font-size: calc(12px * var(--swl-font-scale-body, 1));
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
  font-size: calc(13px * var(--swl-font-scale-body, 1));
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
`.trim();
}
