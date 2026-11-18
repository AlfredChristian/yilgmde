import L from 'leaflet'

// Camion-benne vu de profil, tourné vers la droite (cabine à droite). `versGauche` le retourne
// pour qu'il regarde dans son sens de marche. La caisse prend la couleur de l'état du camion,
// la bande or rappelle le drapeau.
export function svgCamion(couleur = '#0e5a3a', { largeur = 44 } = {}) {
  const hauteur = Math.round((largeur * 28) / 44)
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 44 28" width="${largeur}" height="${hauteur}" aria-hidden="true">
  <ellipse cx="22" cy="26.2" rx="19" ry="1.6" fill="rgba(0,0,0,.22)"/>
  <path d="M5 21 V9.5 Q5 4.2 11 4.2 H27 V21 Z" fill="${couleur}" stroke="#ffffff" stroke-width="1.4"/>
  <path d="M5.2 12 L1.6 14.2 V21 H5.2 Z" fill="#1d2b24" stroke="#ffffff" stroke-width="1.1"/>
  <rect x="5" y="14.6" width="22" height="2.4" fill="#e9b824"/>
  <path d="M11.5 6.5 V13 M16.5 5.6 V13 M21.5 5.6 V13" stroke="rgba(255,255,255,.32)" stroke-width="1.1" stroke-linecap="round"/>
  <path d="M27 9 H34.5 Q36.2 9 37 10.5 L40.6 16.6 Q41.5 17.8 41.5 19.4 V21 H27 Z" fill="#f4f6f3" stroke="#ffffff" stroke-width="1.4"/>
  <path d="M27 9 H34.5 Q36.2 9 37 10.5 L40.6 16.6 Q41.5 17.8 41.5 19.4 V21 H27 Z" fill="none" stroke="#1d2b24" stroke-width=".9"/>
  <path d="M30 11 H34.2 Q35 11 35.4 11.7 L38.2 16.3 H30 Z" fill="#9cc7d9" stroke="#1d2b24" stroke-width=".8"/>
  <rect x="1.6" y="20.2" width="40.4" height="2.2" rx="1" fill="#1d2b24"/>
  <circle cx="9" cy="22.6" r="3.4" fill="#1d2b24" stroke="#ffffff" stroke-width="1.1"/><circle cx="9" cy="22.6" r="1.2" fill="#c9d2cc"/>
  <circle cx="17" cy="22.6" r="3.4" fill="#1d2b24" stroke="#ffffff" stroke-width="1.1"/><circle cx="17" cy="22.6" r="1.2" fill="#c9d2cc"/>
  <circle cx="35" cy="22.6" r="3.4" fill="#1d2b24" stroke="#ffffff" stroke-width="1.1"/><circle cx="35" cy="22.6" r="1.2" fill="#c9d2cc"/>
  <rect x="40.2" y="17.6" width="1.6" height="1.6" rx=".4" fill="#e9b824"/>
</svg>`
}

export function iconeCamion({ couleur, versGauche = false, largeur = 44, classe = '' } = {}) {
  const hauteur = Math.round((largeur * 28) / 44)
  return L.divIcon({
    className: `icone-camion ${classe}`.trim(),
    html: `<span class="icone-camion-corps${versGauche ? ' vers-gauche' : ''}">${svgCamion(couleur, { largeur })}</span>`,
    iconSize: [largeur, hauteur],
    iconAnchor: [largeur / 2, hauteur - 2],
    tooltipAnchor: [0, -hauteur + 4],
  })
}
