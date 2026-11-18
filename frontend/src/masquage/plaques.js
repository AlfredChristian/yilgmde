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
function composantes(masque, w, h, etiq = new Int32Array(w * h)) {
  const res = [], pile = []
  for (let d = 0; d < w * h; d++) {
    if (!masque[d] || etiq[d]) continue
    const c = { x0: w, y0: h, x1: 0, y1: 0, aire: 0, sx: 0, sy: 0 }
    etiq[d] = res.length + 1
    pile.push(d)
    while (pile.length) {
      const p = pile.pop(), x = p % w, y = (p - x) / w
      c.aire++
      c.sx += x
      c.sy += y
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
    res.push({ x: c.x0, y: c.y0, l: c.x1 - c.x0 + 1, h: c.y1 - c.y0 + 1, aire: c.aire, cx: c.sx / c.aire, cy: c.sy / c.aire })
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

// Moyenne sur une fenêtre k x k, bords « reflect 101 », arrondie (comme cv2.blur).
function moyenne(src, w, h, k) {
  const r = k >> 1, tmp = new Float32Array(w * h), out = new Uint8Array(w * h)
  for (let y = 0; y < h; y++) {
    let s = 0
    for (let i = -r; i <= r; i++) s += src[y * w + reflet(i, w)]
    for (let x = 0; x < w; x++) {
      tmp[y * w + x] = s
      s += src[y * w + reflet(x + r + 1, w)] - src[y * w + reflet(x - r, w)]
    }
  }
  for (let x = 0; x < w; x++) {
    let s = 0
    for (let i = -r; i <= r; i++) s += tmp[reflet(i, h) * w + x]
    for (let y = 0; y < h; y++) {
      out[y * w + x] = Math.round(s / (k * k))
      s += tmp[reflet(y + r + 1, h) * w + x] - tmp[reflet(y - r, h) * w + x]
    }
  }
  return out
}

// Enveloppe convexe (chaîne monotone) de points [x, y].
function enveloppe(points) {
  const p = [...points].sort((a, b) => a[0] - b[0] || a[1] - b[1])
  if (p.length < 3) return p
  const croix = (o, a, b) => (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
  const bas = [], haut = []
  for (const q of p) {
    while (bas.length >= 2 && croix(bas[bas.length - 2], bas[bas.length - 1], q) <= 0) bas.pop()
    bas.push(q)
  }
  for (let i = p.length - 1; i >= 0; i--) {
    const q = p[i]
    while (haut.length >= 2 && croix(haut[haut.length - 2], haut[haut.length - 1], q) <= 0) haut.pop()
    haut.push(q)
  }
  return bas.slice(0, -1).concat(haut.slice(0, -1))
}

function dansEnveloppe(env, x, y) {
  if (env.length < 3) return false
  for (let i = 0; i < env.length; i++) {
    const a = env[i], b = env[(i + 1) % env.length]
    if ((b[0] - a[0]) * (y - a[1]) - (b[1] - a[1]) * (x - a[0]) < 0) return false
  }
  return true
}

// Masque des pixels jaunes (teinte 20 à 40 sur 180, saturation >= 40, valeur >= 80), avec la
// conversion HSV 8 bits d'OpenCV.
function masqueJaune(rgba, w, h) {
  const out = new Uint8Array(w * h)
  for (let i = 0; i < w * h; i++) {
    const r = rgba[i * 4], g = rgba[i * 4 + 1], b = rgba[i * 4 + 2]
    const v = Math.max(r, g, b), mn = Math.min(r, g, b), d = v - mn
    if (v < 80 || d === 0) continue
    if (Math.round((d * 255) / v) < 40) continue
    let t = v === r ? (60 * (g - b)) / d : v === g ? 120 + (60 * (b - r)) / d : 240 + (60 * (r - g)) / d
    if (t < 0) t += 360
    const teinte = Math.round(t / 2)
    if (teinte >= 20 && teinte <= 40) out[i] = 1
  }
  return out
}

// Zones du masque (fond de plaque supposé) à peu près rectangulaires, portant 4 à 16 caractères
// sombres sur une ou deux lignes. Portage de `_plaques_dans_masque` (backend/masquage.py).
function plaquesDansMasque(gris, masque, w, h) {
  const m = Math.max(3, Math.floor(w / 100) | 1)
  const clair = fermer(masque, w, h, m, m)
  const etiq = new Int32Array(w * h)
  const plaques = []
  composantes(clair, w, h, etiq).forEach((c, n) => {
    const { x, y, l: cw, h: ch, aire } = c
    if (!(aire >= 0.0005 * w * h && aire <= 0.08 * w * h && cw / ch >= 0.8 && cw / ch <= 5 && aire >= 0.5 * cw * ch && ch >= 12)) return
    // Seul l'intérieur de la plaque compte (une plaque penchée laisse des coins sombres dans sa boîte).
    const pts = []
    for (let j = 0; j < ch; j++) for (let i = 0; i < cw; i++) if (etiq[(y + j) * w + x + i] === n + 1) pts.push([i, j])
    const env = enveloppe(pts)
    let coque = new Uint8Array(cw * ch)
    for (let j = 0; j < ch; j++) for (let i = 0; i < cw; i++) coque[j * cw + i] = dansEnveloppe(env, i, j) ? 1 : 0
    coque = eroder(coque, cw, ch, 5, 5)
    const dedans = []
    for (let j = 0; j < ch; j++) for (let i = 0; i < cw; i++) if (coque[j * cw + i]) dedans.push(gris[(y + j) * w + x + i])
    if (dedans.length < 20) return
    const t = otsu(dedans)
    const encre = new Uint8Array(cw * ch)
    for (let j = 0; j < ch; j++) for (let i = 0; i < cw; i++) encre[j * cw + i] = coque[j * cw + i] && gris[(y + j) * w + x + i] <= t ? 1 : 0
    const caracteres = composantes(encre, cw, ch)
      .filter((q) => q.h >= 0.15 * ch && q.h <= 0.85 * ch && q.l <= 0.35 * cw && q.aire >= 6)
      .sort((a, b) => a.cy - b.cy)
    const rangees = []
    for (const q of caracteres) {
      const r = rangees.find((r) => Math.abs(q.cy - r.y) <= 0.5 * r.h && q.h / r.h >= 0.6 && q.h / r.h <= 1.6)
      if (r) r.n++
      else rangees.push({ y: q.cy, h: q.h, n: 1 })
    }
    const bonnes = rangees.filter((r) => r.n >= 3)
    const total = bonnes.reduce((a, r) => a + r.n, 0)
    if (bonnes.length >= 1 && bonnes.length <= 2 && total >= 4 && total <= 16) plaques.push([x, y, cw, ch])
  })
  return plaques
}

/**
 * Plaques vues par leur fond (D59) : plus clair que son entourage (plaque blanche, ou jaune sous
 * le flash) ou jaune (plaques de moto burkinabè, qui sans flash ont la luminosité de la latérite
 * mais pas sa couleur). Portage de `_plaques_fond_clair` (backend/masquage.py).
 */
export function plaquesFondClair(gris, w, h, rgba = null) {
  const k = Math.max(15, Math.floor(w / 20) | 1)
  const fond = moyenne(gris, w, h, k * 3)
  const clair = new Uint8Array(w * h)
  for (let i = 0; i < w * h; i++) clair[i] = gris[i] - fond[i] > 25 && gris[i] > 110 ? 1 : 0
  const masques = [clair]
  // Points jaunes isolés (grain du sol, herbe sèche) retirés : ils relieraient la plaque au décor.
  if (rgba) masques.push(dilater(eroder(masqueJaune(rgba, w, h), w, h, 3, 3), w, h, 3, 3))
  const plaques = []
  for (const masque of masques)
    for (const z of plaquesDansMasque(gris, masque, w, h))
      if (!plaques.some((p) => p.every((v, i) => v === z[i]))) plaques.push(z)
  return plaques
}
