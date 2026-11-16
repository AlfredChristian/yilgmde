const FORMES = {
  menu: <path d="M3 6h18M3 12h18M3 18h18" />,
  carte: (
    <>
      <path d="M12 21s7-6.2 7-11a7 7 0 1 0-14 0c0 4.8 7 11 7 11z" />
      <circle cx="12" cy="10" r="2.5" />
    </>
  ),
  alerte: (
    <>
      <path d="M12 3l10 18H2L12 3z" />
      <path d="M12 10v5M12 18v.5" />
    </>
  ),
  suivi: (
    <>
      <circle cx="11" cy="11" r="7" />
      <path d="M16 16l5 5" />
    </>
  ),
  mairie: <path d="M3 21h18M5 21V10l7-6 7 6v11M9 21v-6h6v6" />,
  camion: (
    <>
      <path d="M2 6h11v10H2zM13 9h4l4 4v3h-8" />
      <circle cx="6.5" cy="17.5" r="1.8" />
      <circle cx="16.5" cy="17.5" r="1.8" />
    </>
  ),
  bouclier: (
    <>
      <path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6l8-3z" />
      <path d="M8.5 12l2.5 2.5 4.5-5" />
    </>
  ),
  itineraire: (
    <>
      <circle cx="6" cy="18" r="2" />
      <circle cx="18" cy="6" r="2" />
      <path d="M8 18h7a3 3 0 0 0 0-6H9a3 3 0 0 1 0-6h7" />
    </>
  ),
    micro: (
    <>
      <rect x="9" y="3" width="6" height="12" rx="3" />
      <path d="M5 11a7 7 0 0 0 14 0M12 18v3" />
    </>
  ),
    tas_petit: <path d="M4 19h16M8 19c0-3 2-4 4-4s4 1 4 4" />,
  tas_moyen: <path d="M3 19h18M5 19c0-4 3-7 7-7s7 3 7 7" />,
  tas_gros: (
    <>
      <path d="M2 19h22M3 19c0-6 4-12 9-12s9 6 9 12" />
      <path d="M9 11l1 1M14 9l1 1M12 14l1 1" />
    </>
  ),
  sac: (
    <>
      <path d="M8 6h8l2 4v9a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2v-9l2-4z" />
      <path d="M10 6c0-2 1-3 2-3s2 1 2 3" />
    </>
  ),
  gravats: (
    <>
      <rect x="3" y="13" width="8" height="5" />
      <rect x="13" y="13" width="8" height="5" />
      <rect x="8" y="7" width="8" height="5" />
    </>
  ),
  bouteille: (
    <>
      <path d="M10 3h4v3l2 3v11a1 1 0 0 1-1 1H9a1 1 0 0 1-1-1V9l2-3V3z" />
      <path d="M8 13h8" />
    </>
  ),
}

export default function Icone({ nom, taille = 24 }) {
  return (
    <svg
      width={taille}
      height={taille}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {FORMES[nom]}
    </svg>
  )
}