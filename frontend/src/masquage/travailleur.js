// Détection en arrière-plan (Web Worker) : l'écran reste fluide pendant les 1 à 3 secondes de calcul.
import { Reseau } from './reseau.js'
import { detecterVisages } from './visages.js'
import { plaquesParForme } from './plaques.js'

let reseau = null

async function charger(base) {
  if (reseau) return reseau
  const [graphe, poids] = await Promise.all([
    fetch(`${base}modeles/yunet.json`).then((r) => { if (!r.ok) throw new Error('modèle introuvable'); return r.json() }),
    fetch(`${base}modeles/yunet.bin`).then((r) => { if (!r.ok) throw new Error('modèle introuvable'); return r.arrayBuffer() }),
  ])
  reseau = new Reseau(graphe, poids)
  return reseau
}

self.onmessage = async ({ data }) => {
  const { id, base, image, seuil } = data
  try {
    const r = await charger(base)
    const debut = performance.now()
    const visages = detecterVisages(r, image, seuil)
    const { width: w, height: h, data: px } = image
    const gris = new Uint8Array(w * h)
    for (let i = 0; i < w * h; i++) gris[i] = Math.round(0.299 * px[i * 4] + 0.587 * px[i * 4 + 1] + 0.114 * px[i * 4 + 2])
    const plaques = plaquesParForme(gris, w, h)
    self.postMessage({ id, visages: visages.map((v) => v.slice(0, 4)), plaques, ms: performance.now() - debut })
  } catch (err) {
    self.postMessage({ id, erreur: String(err?.message || err) })
  }
}
