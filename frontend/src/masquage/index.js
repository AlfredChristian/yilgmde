// Masquage des visages et des plaques sur le téléphone, avant l'envoi (D59).
//
// La photo d'origine ne quitte jamais l'appareil : elle est réduite (1600 px au plus),
// les visages (YuNet) et les plaques (forme) sont pixelisés puis floutés, et l'image est
// ré-encodée en JPEG, ce qui retire aussi les métadonnées (position GPS, modèle du téléphone).
// Le serveur refait le même masquage en filet de sécurité.

import { flouterPixels } from './flou.js'

const COTE_MAX = 1600       // comme masquage.cote_max_px du serveur
const COTE_DETECTION = 640  // entrée du modèle YuNet
const MARGE = 0.25
const SEUIL_VISAGE = 0.6
const QUALITE = 0.85

let travailleur = null
let compteur = 0

function detecter(image) {
  if (!travailleur) travailleur = new Worker(new URL('./travailleur.js', import.meta.url), { type: 'module' })
  const id = ++compteur
  return new Promise((resolve, reject) => {
    const surMessage = ({ data }) => {
      if (data.id !== id) return
      travailleur.removeEventListener('message', surMessage)
      if (data.erreur) reject(new Error(data.erreur))
      else resolve(data)
    }
    travailleur.addEventListener('message', surMessage)
    travailleur.postMessage({ id, base: import.meta.env.BASE_URL, image, seuil: SEUIL_VISAGE })
  })
}

function toile(w, h) {
  const c = document.createElement('canvas')
  c.width = w
  c.height = h
  return c
}

/** Retire les zones entièrement contenues dans une autre. */
function fusionner(zones) {
  const garde = []
  for (const z of [...zones].sort((a, b) => b[2] * b[3] - a[2] * a[3])) {
    const [x, y, w, h] = z
    if (!garde.some(([gx, gy, gw, gh]) => x >= gx && y >= gy && x + w <= gx + gw && y + h <= gy + gh)) garde.push(z)
  }
  return garde
}

function flouter(ctx, [x, y, w, h], W, H) {
  const dx = Math.floor(w * MARGE), dy = Math.floor(h * MARGE)
  const x0 = Math.max(0, Math.floor(x - dx)), y0 = Math.max(0, Math.floor(y - dy))
  const x1 = Math.min(W, Math.ceil(x + w + dx)), y1 = Math.min(H, Math.ceil(y + h + dy))
  if (x1 <= x0 || y1 <= y0) return
  const zone = ctx.getImageData(x0, y0, x1 - x0, y1 - y0)
  flouterPixels(zone.data, x1 - x0, y1 - y0)
  ctx.putImageData(zone, x0, y0)
}

/**
 * Masque une photo. Renvoie { fichier (JPEG masqué), visages, plaques, ms }.
 * Lève une erreur si le téléphone ne sait pas le faire (le serveur masquera alors seul).
 */
export async function masquerPhoto(fichier) {
  const bitmap = await createImageBitmap(fichier, { imageOrientation: 'from-image' })
  const e = Math.min(1, COTE_MAX / Math.max(bitmap.width, bitmap.height))
  const W = Math.round(bitmap.width * e), H = Math.round(bitmap.height * e)
  const grande = toile(W, H)
  const ctx = grande.getContext('2d')
  ctx.drawImage(bitmap, 0, 0, W, H)
  bitmap.close?.()

  const d = Math.min(1, COTE_DETECTION / Math.max(W, H))
  const pw = Math.max(1, Math.round(W * d)), ph = Math.max(1, Math.round(H * d))
  const petite = toile(pw, ph)
  const pctx = petite.getContext('2d')
  pctx.drawImage(grande, 0, 0, pw, ph)
  const resultat = await detecter(pctx.getImageData(0, 0, pw, ph))

  const remettre = (zones) => fusionner(zones.map(([x, y, w, h]) => [x / d, y / d, w / d, h / d]))
  const visages = remettre(resultat.visages), plaques = remettre(resultat.plaques)
  for (const z of [...visages, ...plaques]) flouter(ctx, z, W, H)

  const blob = await new Promise((ok, ko) => grande.toBlob((b) => (b ? ok(b) : ko(new Error('ré-encodage impossible'))), 'image/jpeg', QUALITE))
  const nom = (fichier.name || 'photo').replace(/\.[^.]+$/, '') + '.jpg'
  return { fichier: new File([blob], nom, { type: 'image/jpeg' }), visages: visages.length, plaques: plaques.length, ms: resultat.ms }
}
