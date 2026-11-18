import L from 'leaflet'

// Illustrations de la simulation d'un quartier (D62) : habitant, tricycle de précollecte,
// poubelle devant une maison. Dessins originaux, aux couleurs de l'application.

export function svgPersonne(couleur = '#0e5a3a', { taille = 22, sac = false } = {}) {
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 28" width="${taille * 0.72}" height="${taille}" aria-hidden="true">
  <ellipse cx="10" cy="26.6" rx="6" ry="1.2" fill="rgba(0,0,0,.22)"/>
  <circle cx="10" cy="5" r="3.6" fill="#7a4a2a" stroke="#fff" stroke-width="1.2"/>
  <path d="M4.6 11.2 Q4.6 9 7 9 H13 Q15.4 9 15.4 11.2 V17.5 H4.6 Z" fill="${couleur}" stroke="#fff" stroke-width="1.2"/>
  <path d="M6.4 17.3 L6 25.4 M13.6 17.3 L14 25.4" stroke="#1d2b24" stroke-width="2.6" stroke-linecap="round"/>
  ${sac ? '<path d="M15.2 13.5 h3.4 l.8 6.4 h-5 z" fill="#1d2b24" stroke="#fff" stroke-width="1"/>' : ''}
</svg>`
}

export function svgTricycle(couleur = '#0e5a3a', { largeur = 40, charge = 0 } = {}) {
  const h = Math.round((largeur * 26) / 40)
  const hauteurCharge = Math.round(Math.min(1, charge) * 6)
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 26" width="${largeur}" height="${h}" aria-hidden="true">
  <ellipse cx="20" cy="24.6" rx="17" ry="1.3" fill="rgba(0,0,0,.2)"/>
  <rect x="2.5" y="${9 - hauteurCharge}" width="17" height="${hauteurCharge}" rx="1.5" fill="#6b5a3e" stroke="#fff" stroke-width=".8"/>
  <path d="M2 9 H20 V17.5 H2 Z" fill="${couleur}" stroke="#fff" stroke-width="1.3"/>
  <rect x="2" y="12.4" width="18" height="2" fill="#e9b824"/>
  <path d="M20 15.5 L27 15.5 L31.5 8.5 M27.4 15.5 L33.5 20.5 M29.5 6.5 H33.5" stroke="#1d2b24" stroke-width="1.8" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
  <circle cx="27" cy="5" r="2.4" fill="#7a4a2a" stroke="#fff" stroke-width="1"/>
  <path d="M26 7.6 L24.8 13.2" stroke="#1d2b24" stroke-width="2.4" stroke-linecap="round"/>
  <circle cx="6" cy="20.5" r="3.4" fill="#fff" stroke="#1d2b24" stroke-width="1.8"/>
  <circle cx="15.5" cy="20.5" r="3.4" fill="#fff" stroke="#1d2b24" stroke-width="1.8"/>
  <circle cx="33.5" cy="20.5" r="3.4" fill="#fff" stroke="#1d2b24" stroke-width="1.8"/>
</svg>`
}

export function svgPoubelle(taille = 14) {
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 14 16" width="${taille}" height="${Math.round(taille * 16 / 14)}" aria-hidden="true">
  <path d="M2.5 4.5 H11.5 L10.6 15 H3.4 Z" fill="#0e5a3a" stroke="#fff" stroke-width="1.1"/>
  <rect x="1.5" y="2.4" width="11" height="2.4" rx="1" fill="#1d2b24" stroke="#fff" stroke-width="1"/>
  <path d="M5.5 7 V12.6 M8.5 7 V12.6" stroke="rgba(255,255,255,.5)" stroke-width="1"/>
</svg>`
}

const cache = new Map()
function icone(cle, html, largeur, hauteur, ancreY = hauteur - 2) {
  if (!cache.has(cle)) {
    cache.set(cle, L.divIcon({ className: 'icone-quartier', html, iconSize: [largeur, hauteur], iconAnchor: [largeur / 2, ancreY], tooltipAnchor: [0, -hauteur + 4] }))
  }
  return cache.get(cle)
}

export const COULEUR_MODE = { abonne: '#0e5a3a', apport: '#2f6f9f', sauvage: '#b8322a' }

export const iconePersonne = (mode, sac) => icone(`p-${mode}-${sac}`, `<span class="icone-quartier-corps">${svgPersonne(COULEUR_MODE[mode], { sac })}</span>`, 16, 22)
export const iconeTricycle = (versGauche, charge) => {
  const palier = Math.round(Math.min(1, charge) * 4) / 4
  return icone(`t-${versGauche}-${palier}`, `<span class="icone-quartier-corps${versGauche ? ' vers-gauche' : ''}">${svgTricycle('#0e5a3a', { charge: palier })}</span>`, 40, 26)
}
export const iconePoubelle = () => icone('b', svgPoubelle(), 14, 16, 16)
