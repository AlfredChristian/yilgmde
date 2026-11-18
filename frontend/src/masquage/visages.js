// Visages par YuNet sur le téléphone (D59) : même modèle et même décodage que le serveur
// (cv2.FaceDetectorYN), pour que le téléphone floute ce que le serveur aurait flouté.

export const COTE = 640   // entrée fixe du modèle exporté

/** Image RGBA (ImageData ou équivalent) → tenseur BGR [1,3,640,640], image en haut à gauche. */
export function preparer(image) {
  const { width: w, height: h, data } = image
  const t = new Float32Array(3 * COTE * COTE)
  const plan = COTE * COTE
  for (let y = 0; y < Math.min(h, COTE); y++)
    for (let x = 0; x < Math.min(w, COTE); x++) {
      const i = (y * w + x) * 4, o = y * COTE + x
      t[o] = data[i + 2]           // B
      t[plan + o] = data[i + 1]    // G
      t[2 * plan + o] = data[i]    // R
    }
  return t
}

function iou(a, b) {
  const x0 = Math.max(a[0], b[0]), y0 = Math.max(a[1], b[1])
  const x1 = Math.min(a[0] + a[2], b[0] + b[2]), y1 = Math.min(a[1] + a[3], b[1] + b[3])
  const inter = Math.max(0, x1 - x0) * Math.max(0, y1 - y0)
  return inter / (a[2] * a[3] + b[2] * b[3] - inter)
}

/** Sorties du réseau → visages [x, y, largeur, hauteur, score] après suppression des doublons. */
export function decoder(sorties, seuil = 0.6, seuilNms = 0.3) {
  const candidats = []
  for (const pas of [8, 16, 32]) {
    const cls = sorties[`cls_${pas}`].donnees, obj = sorties[`obj_${pas}`].donnees
    const bbox = sorties[`bbox_${pas}`].donnees
    const cols = COTE / pas
    for (let idx = 0; idx < cls.length; idx++) {
      const c = Math.min(1, Math.max(0, cls[idx])), o = Math.min(1, Math.max(0, obj[idx]))
      const score = Math.sqrt(c * o)
      if (score < seuil) continue
      const r = Math.floor(idx / cols), col = idx % cols
      const cx = (col + bbox[idx * 4]) * pas, cy = (r + bbox[idx * 4 + 1]) * pas
      const w = Math.exp(bbox[idx * 4 + 2]) * pas, h = Math.exp(bbox[idx * 4 + 3]) * pas
      candidats.push([cx - w / 2, cy - h / 2, w, h, score])
    }
  }
  candidats.sort((a, b) => b[4] - a[4])
  const gardes = []
  for (const c of candidats) if (gardes.every((g) => iou(g, c) <= seuilNms)) gardes.push(c)
  return gardes
}

export const CONTRASTE_MIN_VISAGE = 6   // comme backend/masquage.py

/** Écart type des gris dans la zone [x, y, l, h] d'une image RGBA (0 si vide). */
function contraste({ width: w, height: h, data }, [x, y, l, hz]) {
  const x0 = Math.max(0, Math.floor(x)), y0 = Math.max(0, Math.floor(y))
  const x1 = Math.min(w, Math.floor(x + l)), y1 = Math.min(h, Math.floor(y + hz))
  let n = 0, s = 0, s2 = 0
  for (let j = y0; j < y1; j++)
    for (let i = x0; i < x1; i++) {
      const k = (j * w + i) * 4
      const g = 0.299 * data[k] + 0.587 * data[k + 1] + 0.114 * data[k + 2]
      n++; s += g; s2 += g * g
    }
  return n ? Math.sqrt(Math.max(0, s2 / n - (s / n) ** 2)) : 0
}

/** Visages d'une image RGBA d'au plus 640 px de côté. Une zone unie n'est pas un visage. */
export function detecterVisages(reseau, image, seuil) {
  const sorties = reseau.executer(preparer(image), COTE, COTE)
  return decoder(sorties, seuil).filter((v) => contraste(image, v) >= CONTRASTE_MIN_VISAGE)
}
