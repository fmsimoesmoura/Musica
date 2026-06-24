// Stylized, recognizable brand marks for each service (not the providers' exact
// logo files). Brand names/marks are trademarks of their respective owners.

export function ProviderIcon({ name, size = 15 }: { name: string; size?: number }) {
  const common = { width: size, height: size, viewBox: "0 0 24 24", "aria-hidden": true } as const;

  if (name === "spotify") {
    return (
      <svg {...common}>
        <circle cx="12" cy="12" r="12" fill="#1DB954" />
        <path d="M6.4 9.6c3.5-1 7.8-.7 10.8 1.1" stroke="#0b0b0b" strokeWidth="1.7" fill="none" strokeLinecap="round" />
        <path d="M7 12.8c2.9-.8 6.2-.5 8.7 1" stroke="#0b0b0b" strokeWidth="1.5" fill="none" strokeLinecap="round" />
        <path d="M7.6 15.7c2.3-.6 4.8-.4 6.8.8" stroke="#0b0b0b" strokeWidth="1.3" fill="none" strokeLinecap="round" />
      </svg>
    );
  }

  if (name === "tidal") {
    // Overlapping diamonds, echoing TIDAL's geometric mark.
    return (
      <svg {...common}>
        <g fill="currentColor">
          <path d="M6 8l3-3 3 3-3 3z" />
          <path d="M12 8l3-3 3 3-3 3z" />
          <path d="M9 14l3-3 3 3-3 3z" />
        </g>
      </svg>
    );
  }

  if (name === "qobuz") {
    // Stylized Q.
    return (
      <svg {...common}>
        <circle cx="11" cy="11" r="6.4" fill="none" stroke="#2e7bd6" strokeWidth="2.4" />
        <path d="M14.6 14.6L19 19" stroke="#2e7bd6" strokeWidth="2.4" strokeLinecap="round" />
      </svg>
    );
  }

  return null;
}
