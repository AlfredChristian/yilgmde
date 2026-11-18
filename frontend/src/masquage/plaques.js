// Plaques par la forme, sur le téléphone (D59) : portage de `_plaques_par_forme` du serveur
// (backend/masquage.py). Un rectangle clair contenant une rangée de 4 à 12 caractères sombres
// de même hauteur, quel que soit le pays. Entrée : niveaux de gris (Uint8Array, largeur, hauteur).

// Minimum ou maximum glissant sur une fenêtre rectangulaire (bords ignorés, comme OpenCV).
function morpho(src, w, h, kw, kh, max) {
  const tmp = new Uint8Array(w * h), out = new Uint8Array(w * h)
  const ax = kw >> 1, ay = kh >> 1
  for (let y = 0; y < h; y++)
    for (let x = 0; x < w; x++) {
      let v = max ? 0 : 255
      const x0 = Math.max(0, x - ax), x1 = Math.min(w - 1, x - ax + kw - 1)
      for (let i = x0; i <= x1; i++) { const p = src[y * w + i]; if (max ? p > v : p < v) v = p }
      tmp[y * w + x] = v
    }
  for (let y = 0; y < h; y++)
    for (let x = 0; x < w; x++) {
      let v = max ? 0 : 255
      const y0 = Math.max(0, y - ay), y1 = Math.min(h - 1, y - ay + kh - 1)
      for (let j = y0; j <= y1; j++) { const p = tmp[j * w + x]; if (max ? p > v : p < v) v = p }
      out[y * w + x] = v
    }
  return out
}
const dilater = (s, w, h, kw, kh) => morpho(s, w, h, kw, kh, true)
const eroder = (s, w, h, kw, kh) => morpho(s, w, h, kw, kh, false)
const fermer = (s, w, h, kw, kh) => eroder(dilater(s, w, h, kw, kh), w, h, kw, kh)

const reflet = (i, n) => (i < 0 ? -i : i >= n ? 2 * n - i - 2 : i)   // bord « reflect 101 »

function sobelX(src, w, h) {
  const out = new Float32Array(w * h)
  for (let y = 0; y < h; y++) {
    const ym = reflet(y - 1, h) * w, y0 = y * w, yp = reflet(y + 1, h) * w
    for (let x = 0; x < w; x++) {
      const xm = reflet(x - 1, w), xp = reflet(x + 1, w)
      out[y0 + x] = Math.abs(src[ym + xp] - src[ym + xm] + 2 * (src[y0 + xp] - src[y0 + xm]) + src[yp + xp] - src[yp + xm])
    }
  }
  return out
}

function flou5(src, w, h) {
  const k = [1, 4, 6, 4, 1], tmp = new Float32Array(w * h), out = new Uint8Array(w * h)
  for (let y = 0; y < h; y++)
    for (let x = 0; x < w; x++) {
      let s = 0
      for (let i = -2; i <= 2; i++) s += k[i + 2] * src[y * w + reflet(x + i, w)]
      tmp[y * w + x] = s / 16
    }
  for (let y = 0; y < h; y++)
    for (let x = 0; x < w; x++) {
      let s = 0
      for (let i = -2; i <= 2; i++) s += k[i + 2] * tmp[reflet(y + i, h) * w + x]
      out[y * w + x] = Math.round(s / 16)
    }
  return out
}

function otsu(valeurs) {
  const hist = new Float64Array(256)
  for (const v of valeurs) hist[v]++
  const n = valeurs.length
  let somme = 0
  for (let i = 0; i < 256; i++) somme += i * hist[i]
  let sB = 0, wB = 0, meilleur = 0, seuil = 0
  for (let t = 0; t < 256; t++) {
    wB += hist[t]
    if (!wB) continue
    const wF = n - wB
    if (!wF) break
    sB += t * hist[t]
    const mB = sB / wB, mF = (somme - sB) / wF
    const v = wB * wF * (mB - mF) ** 2
    if (v > meilleur) { meilleur = v; seuil = t }
  }
  return seuil
}

// Composantes connexes (8 voisins) d'un masque : boîte englobante et surface de chacune.
function composantes(masque, w, h) {
  const etiq = new Int32Array(w * h), res = [], pile = []
  for (let d = 0; d < w * h; d++) {
    if (!masque[d] || etiq[d]) continue
    const c = { x0: w, y0: h, x1: 0, y1: 0, aire: 0 }
    etiq[d] = res.length + 1
    pile.push(d)
    while (pile.length) {
      const p = pile.pop(), x = p % w, y = (p - x) / w
      c.aire++
      if (x < c.x0) c.x0 = x
      if (x > c.x1) c.x1 = x
      if (y < c.y0) c.y0 = y
      if (y > c.y1) c.y1 = y
      for (let dy = -1; dy <= 1; dy++)
        for (let dx = -1; dx <= 1; dx++) {
          const nx = x + dx, ny = y + dy
          if (nx < 0 || ny < 0 || nx >= w || ny >= h) continue
          const q = ny * w + nx
          if (masque[q] && !etiq[q]) { etiq[q] = res.length + 1; pile.push(q) }
        }
    }
    res.push({ x: c.x0, y: c.y0, l: c.x1 - c.x0 + 1, h: c.y1 - c.y0 + 1, aire: c.aire })
  }
  return res
}

/** Zones [x, y, largeur, hauteur] des plaques trouvées par leur forme. */
export function plaquesParForme(gris, w, h) {
  const kx = Math.max(9, Math.floor(w / 45) | 1)
  const ferme = fermer(gris, w, h, kx, Math.max(5, Math.floor(kx / 3)))
  const noirSurClair = new Uint8Array(w * h)
  for (let i = 0; i < w * h; i++) noirSurClair[i] = ferme[i] - gris[i]
  const grad = sobelX(noirSurClair, w, h)
  let mn = Infinity, mx = -Infinity
  for (const v of grad) { if (v < mn) mn = v; if (v > mx) mx = v }
  const g8 = new Uint8Array(w * h)
  for (let i = 0; i < w * h; i++) g8[i] = mx > mn ? Math.round(((grad[i] - mn) * 255) / (mx - mn)) : 0
  const lisse = fermer(flou5(g8, w, h), w, h, kx * 2 + 1, Math.max(3, Math.floor(kx / 3)))
  const s = otsu(lisse)
  let masque = new Uint8Array(w * h)
  for (let i = 0; i < w * h; i++) masque[i] = lisse[i] > s ? 255 : 0
  masque = dilater(eroder(masque, w, h, 5, 5), w, h, 5, 5)

  const plaques = []
  for (const c of composantes(masque, w, h)) {
    const { x, y, l: cw, h: ch } = c
    if (ch < 8 || cw / ch < 2 || cw / ch > 10 || cw * ch < 0.0003 * w * h || cw * ch > 0.06 * w * h) continue
    const dy = Math.floor(ch * 0.5)
    const y0 = Math.max(0, y - dy), y1 = Math.min(h, y + ch + dy)
    const rw = cw, rh = y1 - y0
    const region = new Uint8Array(rw * rh)
    for (let j = 0; j < rh; j++) region.set(gris.subarray((y0 + j) * w + x, (y0 + j) * w + x + cw), j * rw)
    const t = otsu(region)
    const encre = new Uint8Array(rw * rh)
    let noir = 0
    for (let i = 0; i < region.length; i++) if (region[i] <= t) { encre[i] = 1; noir++ }
    if (noir / region.length > 0.6) continue
    const caracteres = composantes(encre, rw, rh).filter((k) => k.h >= 0.6 * ch && k.h <= 1.2 * ch && k.l <= 0.3 * cw && k.aire >= 6)
    if (caracteres.length < 4 || caracteres.length > 12) continue
    const hs = caracteres.map((k) => k.h)
    if (Math.max(...hs) <= 1.6 * Math.min(...hs)) plaques.push([x, y0, cw, rh])
  }
  return plaques
}
