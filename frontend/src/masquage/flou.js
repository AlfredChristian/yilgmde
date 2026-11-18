// Floutage d'une zone, pixel par pixel, identique au serveur (D59). Sans dépendance au navigateur.

/** Pixelise puis floute la zone élargie de MARGE, comme le serveur (backend/masquage.py, `flouter`) :
 * moyenne par blocs de 1/5 de la zone, agrandissement sans lissage, puis flou gaussien. Irréversible,
 * et calculé pixel par pixel : rien de l'image d'origine ne transparaît sur les bords. */
export function flouterPixels(px, lw, lh) {
  const bloc = Math.max(4, Math.floor(Math.min(lw, lh) / 5))
  const sw = Math.max(1, Math.floor(lw / bloc)), sh = Math.max(1, Math.floor(lh / bloc))
  const moy = new Float32Array(sw * sh * 3)
  for (let j = 0; j < sh; j++) {
    const ya = Math.floor((j * lh) / sh), yb = Math.floor(((j + 1) * lh) / sh)
    for (let i = 0; i < sw; i++) {
      const xa = Math.floor((i * lw) / sw), xb = Math.floor(((i + 1) * lw) / sw)
      let r = 0, g = 0, b = 0
      for (let y = ya; y < yb; y++)
        for (let x = xa; x < xb; x++) { const k = (y * lw + x) * 4; r += px[k]; g += px[k + 1]; b += px[k + 2] }
      const n = (yb - ya) * (xb - xa), o = (j * sw + i) * 3
      moy[o] = r / n; moy[o + 1] = g / n; moy[o + 2] = b / n
    }
  }
  const plan = new Float32Array(lw * lh * 3)
  for (let y = 0; y < lh; y++) {
    const j = Math.min(sh - 1, Math.floor((y * sh) / lh))
    for (let x = 0; x < lw; x++) {
      const o = (j * sw + Math.min(sw - 1, Math.floor((x * sw) / lw))) * 3, k = (y * lw + x) * 3
      plan[k] = moy[o]; plan[k + 1] = moy[o + 1]; plan[k + 2] = moy[o + 2]
    }
  }
  // Flou gaussien séparable, noyau et sigma choisis comme OpenCV pour un noyau de (2 x bloc) | 1.
  const taille = Math.max(3, (bloc * 2) | 1), r = taille >> 1
  const sigma = 0.3 * ((taille - 1) * 0.5 - 1) + 0.8
  const noyau = Array.from({ length: taille }, (_, i) => Math.exp(-((i - r) ** 2) / (2 * sigma * sigma)))
  const somme = noyau.reduce((a, v) => a + v, 0)
  const passe = (src, horizontal) => {
    const out = new Float32Array(src.length)
    for (let y = 0; y < lh; y++)
      for (let x = 0; x < lw; x++)
        for (let c = 0; c < 3; c++) {
          let v = 0
          for (let t = -r; t <= r; t++) {
            const xx = horizontal ? Math.min(lw - 1, Math.max(0, x + t)) : x
            const yy = horizontal ? y : Math.min(lh - 1, Math.max(0, y + t))
            v += noyau[t + r] * src[(yy * lw + xx) * 3 + c]
          }
          out[(y * lw + x) * 3 + c] = v / somme
        }
    return out
  }
  const flou = passe(passe(plan, true), false)
  for (let k = 0; k < lw * lh; k++) {
    px[k * 4] = flou[k * 3]; px[k * 4 + 1] = flou[k * 3 + 1]; px[k * 4 + 2] = flou[k * 3 + 2]
  }
}
