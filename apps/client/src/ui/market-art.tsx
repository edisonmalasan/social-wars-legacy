/**
 * Original geometry for the player-owned resource market.
 *
 * Every shape here is drawn from scratch in inline SVG: a coin with a rising
 * three-bar ledger, a slatted crate for an empty state, three resource marks
 * and an hourglass. Nothing is copied, traced or extracted from the vendored
 * client, its SWF, an atlas or any Zynga artwork, and there are no image files
 * or new dependencies. The marks are decorative (`aria-hidden`); the panel's
 * text carries the meaning.
 */

/** The market's badge: a coin holding a small three-bar trade ledger. */
export function MarketBadge({ className }: { className?: string }): React.JSX.Element {
  return (
    <svg
      className={className}
      viewBox="0 0 48 48"
      width="48"
      height="48"
      aria-hidden="true"
      focusable="false"
    >
      <circle cx="24" cy="24" r="21" fill="#1d2430" stroke="#f5c542" strokeWidth="3" />
      <circle cx="24" cy="24" r="16" fill="none" stroke="#38445a" strokeWidth="1" />
      <path d="M14 31h20" stroke="#8d97a8" strokeWidth="2" strokeLinecap="round" />
      <rect x="16" y="24" width="4" height="7" fill="#86d38a" />
      <rect x="22" y="19" width="4" height="12" fill="#f5c542" />
      <rect x="28" y="14" width="4" height="17" fill="#a9d7ff" />
      <path
        d="M15 16l8-6 5 4 6-6"
        fill="none"
        stroke="#e8e3d8"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path d="M29 8h5v5" fill="none" stroke="#e8e3d8" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

/** An open, empty crate: the explicit empty-state mark. */
export function MarketEmptyArt({ className }: { className?: string }): React.JSX.Element {
  return (
    <svg
      className={className}
      viewBox="0 0 64 48"
      width="64"
      height="48"
      aria-hidden="true"
      focusable="false"
    >
      <path
        d="M8 18l24-9 24 9-24 9z"
        fill="#1d2430"
        stroke="#8d97a8"
        strokeWidth="2"
        strokeLinejoin="round"
      />
      <path
        d="M8 18v18l24 9V27zM56 18v18l-24 9V27z"
        fill="none"
        stroke="#8d97a8"
        strokeWidth="2"
        strokeLinejoin="round"
      />
      <path d="M32 27v18" stroke="#38445a" strokeWidth="2" />
      <path
        d="M20 14h24"
        stroke="#f5c542"
        strokeWidth="2"
        strokeDasharray="3 4"
        strokeLinecap="round"
      />
    </svg>
  );
}

/** A distinct, original mark for each of the three tradeable wire keys. */
export function MarketResourceMark({
  resource,
  className,
}: {
  resource: string;
  className?: string;
}): React.JSX.Element {
  if (resource === 'w') {
    // Three stacked, rounded timbers seen end-on.
    return (
      <svg
        className={className}
        viewBox="0 0 32 32"
        width="32"
        height="32"
        aria-hidden="true"
        focusable="false"
      >
        <rect x="5" y="8" width="22" height="6" rx="2" fill="#a9793e" stroke="#e8e3d8" strokeWidth="1" />
        <rect x="5" y="15" width="22" height="6" rx="2" fill="#bc8a49" stroke="#e8e3d8" strokeWidth="1" />
        <rect x="5" y="22" width="22" height="6" rx="2" fill="#a9793e" stroke="#e8e3d8" strokeWidth="1" />
        <circle cx="9" cy="11" r="1.3" fill="#6f4a22" />
        <circle cx="9" cy="18" r="1.3" fill="#6f4a22" />
        <circle cx="9" cy="25" r="1.3" fill="#6f4a22" />
      </svg>
    );
  }
  if (resource === 'o') {
    // A droplet with a single highlight, not any game icon.
    return (
      <svg
        className={className}
        viewBox="0 0 32 32"
        width="32"
        height="32"
        aria-hidden="true"
        focusable="false"
      >
        <path
          d="M16 3c4 7 9 12 9 18a9 9 0 0 1-18 0c0-6 5-11 9-18z"
          fill="#3c6f86"
          stroke="#a9d7ff"
          strokeWidth="2"
          strokeLinejoin="round"
        />
        <path d="M12 20c0 3 2 5 4 5" fill="none" stroke="#e8e3d8" strokeWidth="2" strokeLinecap="round" />
      </svg>
    );
  }
  // 's': a faceted ingot drawn as two trapezoids.
  return (
    <svg
      className={className}
      viewBox="0 0 32 32"
      width="32"
      height="32"
      aria-hidden="true"
      focusable="false"
    >
      <path d="M9 12h14l4 6H5z" fill="#8894a6" stroke="#e8e3d8" strokeWidth="1" />
      <path d="M5 18h22l-3 7H8z" fill="#5d687a" stroke="#e8e3d8" strokeWidth="1" />
      <path d="M11 14h10" stroke="#d7deea" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

/** The 24-hour wait, drawn as an hourglass beside the exhaustion caption. */
export function MarketExhaustedArt({
  className,
}: {
  className?: string;
}): React.JSX.Element {
  return (
    <svg
      className={className}
      viewBox="0 0 32 32"
      width="32"
      height="32"
      aria-hidden="true"
      focusable="false"
    >
      <path
        d="M7 4h18M7 28h18M9 4c0 7 7 8 7 12s-7 5-7 12M23 4c0 7-7 8-7 12s7 5 7 12"
        fill="none"
        stroke="#e07a5f"
        strokeWidth="2"
        strokeLinecap="round"
      />
      <path d="M12 24l4-6 4 6z" fill="#f5c542" />
    </svg>
  );
}
