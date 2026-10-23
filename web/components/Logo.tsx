// Robot del bot en SVG (nitido a cualquier tamano). Mismos colores que el avatar del perfil.
export default function Logo({ size = 36 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" role="img" aria-label="Bot Facebook">
      <defs>
        <linearGradient id="lg-bg" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#3b2a9c" />
          <stop offset="1" stopColor="#0f1640" />
        </linearGradient>
        <linearGradient id="lg-head" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#9be6ff" />
          <stop offset="1" stopColor="#3a9bff" />
        </linearGradient>
      </defs>
      <rect width="100" height="100" rx="24" fill="url(#lg-bg)" />
      <line x1="50" y1="14" x2="50" y2="26" stroke="#c9d4ff" strokeWidth="3" strokeLinecap="round" />
      <circle cx="50" cy="12" r="4.5" fill="#ff5f7e" />
      <rect x="20" y="42" width="6" height="16" rx="3" fill="#2c6bd6" />
      <rect x="74" y="42" width="6" height="16" rx="3" fill="#2c6bd6" />
      <rect x="24" y="26" width="52" height="42" rx="14" fill="url(#lg-head)" />
      <rect x="30" y="33" width="40" height="28" rx="10" fill="#0f1640" />
      <circle cx="42" cy="45" r="5.5" fill="#7fffd4" />
      <circle cx="58" cy="45" r="5.5" fill="#7fffd4" />
      <path d="M42 54 Q50 60 58 54" stroke="#7fffd4" strokeWidth="2.6" fill="none" strokeLinecap="round" />
      <path d="M26 92 Q26 74 42 72 H58 Q74 74 74 92 Z" fill="#3a9bff" />
    </svg>
  );
}
