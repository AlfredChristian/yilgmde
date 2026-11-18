// Petit moteur d'inférence pour YuNet, en JavaScript pur (masquage sur le téléphone, D59).
//
// Le modèle n'utilise que : Conv (pleine, 1x1, par canal), Relu, MaxPool, Resize (plus proche
// voisin), Add, Transpose, Reshape, Sigmoid. Les écrire ici évite un moteur ONNX de 4 Mo :
// le modèle complet pèse 235 Ko et fonctionne hors ligne. Graphe et poids sont produits par
// scripts/exporter_yunet_web.py ; le résultat est vérifié contre onnxruntime (scripts/verifier_masquage_web.py).

function tenseur(forme, donnees) {
  return { forme, donnees: donnees || new Float32Array(forme.reduce((a, b) => a * b, 1)) }
}

function conv(x, w, b, attrs) {
  const [, C, H, W] = x.forme
  const [M, Cg, kh, kw] = w.forme
  const g = attrs.group || 1
  const [pt, pl, pb, pr] = attrs.pads || [0, 0, 0, 0]
  const [sh, sw] = attrs.strides || [1, 1]
  const Ho = Math.floor((H + pt + pb - kh) / sh) + 1
  const Wo = Math.floor((W + pl + pr - kw) / sw) + 1
  const y = tenseur([1, M, Ho, Wo])
  const X = x.donnees, K = w.donnees, Y = y.donnees, B = b ? b.donnees : null
  const HWo = Ho * Wo, HW = H * W
  const Mg = M / g

  if (kh === 1 && kw === 1 && sh === 1 && sw === 1 && pt + pl + pb + pr === 0 && g === 1) {
    // 1x1 : chaque sortie est une combinaison des canaux d'entrée. Quatre sorties à la fois,
    // pour ne lire chaque canal d'entrée qu'une fois par bloc.
    for (let m0 = 0; m0 < M; m0 += 4) {
      const n = Math.min(4, M - m0)
      for (let q = 0; q < n; q++) Y.fill(B ? B[m0 + q] : 0, (m0 + q) * HWo, (m0 + q + 1) * HWo)
      const o0 = m0 * HWo, o1 = o0 + HWo, o2 = o1 + HWo, o3 = o2 + HWo
      for (let c = 0; c < C; c++) {
        const i = c * HW
        const k0 = K[m0 * C + c]
        if (n === 4) {
          const k1 = K[(m0 + 1) * C + c], k2 = K[(m0 + 2) * C + c], k3 = K[(m0 + 3) * C + c]
          for (let p = 0; p < HW; p++) {
            const v = X[i + p]
            Y[o0 + p] += k0 * v; Y[o1 + p] += k1 * v; Y[o2 + p] += k2 * v; Y[o3 + p] += k3 * v
          }
        } else {
          for (let q = 0; q < n; q++) {
            const k = K[(m0 + q) * C + c], o = (m0 + q) * HWo
            for (let p = 0; p < HW; p++) Y[o + p] += k * X[i + p]
          }
        }
      }
    }
    return y
  }

  // Cas général (3x3 pleine ou par canal) : entrée recopiée avec ses bords à zéro, ce qui
  // évite tout test de bord dans la boucle intérieure.
  const Hp = H + pt + pb, Wp = W + pl + pr
  let P = X
  if (pt + pl + pb + pr > 0) {
    P = new Float32Array(C * Hp * Wp)
    for (let c = 0; c < C; c++)
      for (let yi = 0; yi < H; yi++) P.set(X.subarray(c * HW + yi * W, c * HW + yi * W + W), (c * Hp + yi + pt) * Wp + pl)
  }
  for (let m = 0; m < M; m++) {
    const grp = Math.floor(m / Mg)
    const o = m * HWo
    Y.fill(B ? B[m] : 0, o, o + HWo)
    for (let cg = 0; cg < Cg; cg++) {
      const base = (grp * Cg + cg) * Hp * Wp
      const kb = (m * Cg + cg) * kh * kw
      for (let i = 0; i < kh; i++)
        for (let j = 0; j < kw; j++) {
          const k = K[kb + i * kw + j]
          if (k === 0) continue
          for (let yo = 0; yo < Ho; yo++) {
            const src = base + (yo * sh + i) * Wp + j
            const dst = o + yo * Wo
            for (let xo = 0; xo < Wo; xo++) Y[dst + xo] += k * P[src + xo * sw]
          }
        }
    }
  }
  return y
}

function maxpool(x, attrs) {
  const [, C, H, W] = x.forme
  const [kh, kw] = attrs.kernel_shape, [sh, sw] = attrs.strides
  const Ho = Math.floor((H - kh) / sh) + 1, Wo = Math.floor((W - kw) / sw) + 1
  const y = tenseur([1, C, Ho, Wo])
  for (let c = 0; c < C; c++)
    for (let yo = 0; yo < Ho; yo++)
      for (let xo = 0; xo < Wo; xo++) {
        let m = -Infinity
        for (let i = 0; i < kh; i++)
          for (let j = 0; j < kw; j++) {
            const v = x.donnees[(c * H + yo * sh + i) * W + xo * sw + j]
            if (v > m) m = v
          }
        y.donnees[(c * Ho + yo) * Wo + xo] = m
      }
  return y
}

function agrandir(x, echelles) {
  // Resize « nearest », coordonnées asymétriques, arrondi inférieur (seul mode du modèle).
  const [, C, H, W] = x.forme
  const Ho = Math.floor(H * echelles[2]), Wo = Math.floor(W * echelles[3])
  const y = tenseur([1, C, Ho, Wo])
  for (let c = 0; c < C; c++)
    for (let yo = 0; yo < Ho; yo++) {
      const yi = Math.min(H - 1, Math.floor(yo / echelles[2]))
      for (let xo = 0; xo < Wo; xo++) {
        const xi = Math.min(W - 1, Math.floor(xo / echelles[3]))
        y.donnees[(c * Ho + yo) * Wo + xo] = x.donnees[(c * H + yi) * W + xi]
      }
    }
  return y
}

function transposer(x, perm) {
  const f = x.forme
  const forme = perm.map((p) => f[p])
  const pasE = f.map((_, i) => f.slice(i + 1).reduce((a, b) => a * b, 1))
  const y = tenseur(forme)
  const n = y.donnees.length
  const idx = new Array(forme.length).fill(0)
  for (let k = 0; k < n; k++) {
    let src = 0
    for (let d = 0; d < forme.length; d++) src += idx[d] * pasE[perm[d]]
    y.donnees[k] = x.donnees[src]
    for (let d = forme.length - 1; d >= 0; d--) {
      if (++idx[d] < forme[d]) break
      idx[d] = 0
    }
  }
  return y
}

function remodeler(x, cible) {
  const total = x.donnees.length
  const forme = cible.map((v, i) => (v === 0 ? x.forme[i] : v))
  const connu = forme.filter((v) => v !== -1).reduce((a, b) => a * b, 1)
  return { forme: forme.map((v) => (v === -1 ? total / connu : v)), donnees: x.donnees }
}

export class Reseau {
  constructor(graphe, binaire) {
    this.graphe = graphe
    const tout = new Float32Array(binaire)
    this.poids = {}
    for (const [nom, p] of Object.entries(graphe.poids)) this.poids[nom] = tenseur(p.forme, tout.subarray(p.debut, p.debut + p.taille))
  }

  /** `entree` : Float32Array [1, 3, H, W] (BGR, valeurs 0-255). Renvoie les sorties par nom. */
  executer(entree, H, W) {
    const v = { [this.graphe.entree]: tenseur([1, 3, H, W], entree), ...this.poids }
    const cst = this.graphe.constantes
    for (const n of this.graphe.noeuds) {
      const [a, b, c] = n.entrees
      let r
      switch (n.op) {
        case 'Conv': r = conv(v[a], v[b], c ? v[c] : null, n.attrs); break
        case 'Relu': {
          const x = v[a].donnees, y = new Float32Array(x.length)
          for (let i = 0; i < x.length; i++) y[i] = x[i] > 0 ? x[i] : 0
          r = tenseur(v[a].forme, y)
          break
        }
        case 'Sigmoid': r = tenseur(v[a].forme, v[a].donnees.map((t) => 1 / (1 + Math.exp(-t)))); break
        case 'MaxPool': r = maxpool(v[a], n.attrs); break
        case 'Resize': r = agrandir(v[a], cst[n.entrees[2]]); break
        case 'Add': {
          const x = v[a].donnees, y = v[b].donnees
          if (x.length !== y.length) throw new Error('Add : formes différentes')
          r = tenseur(v[a].forme, x.map((t, i) => t + y[i]))
          break
        }
        case 'Transpose': r = transposer(v[a], n.attrs.perm); break
        case 'Reshape': r = remodeler(v[a], cst[b]); break
        default: throw new Error(`opération non prise en charge : ${n.op}`)
      }
      v[n.sorties[0]] = r
    }
    return Object.fromEntries(this.graphe.sorties.map((s) => [s, v[s]]))
  }
}
