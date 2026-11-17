// Client d'acces aux donnees. Le composant ne sait pas si les donnees
// viennent du mock ou de l'API : tout passe par ce fichier.

// Attention : les variables Vite sont des chaines, pas des booleens.

import { ajouter, lister, retirer, nouvelleCle } from './fileAttente'

const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true'
const API_URL = import.meta.env.VITE_API_URL ?? '/api'

async function getJson(url) {
  const res = await fetch(url)
  if (!res.ok) {
    throw new Error(`Erreur ${res.status} sur ${url}`)
  }
  return res.json()
}

// Renvoie un GeoJSON FeatureCollection (format de GET /depotoirs).
export function getDepotoirs() {
  const url = USE_MOCK
    ? '/mock/depotoirs_exemple.geojson'
    : `${API_URL}/depotoirs`
  return getJson(url)
}

// Renvoie un GeoJSON FeatureCollection de signalements (bruts, avant moderation).
// [H] route reelle a confirmer dans docs/api-contract.md
export function getSignalements() {
  const url = USE_MOCK
    ? '/mock/signalements_exemple.geojson'
    : `${API_URL}/signalements`
  return getJson(url)
}

// Jeton anonyme propre a l'appareil (citoyen sans compte).
function jetonAppareil() {
  try {
    let j = localStorage.getItem('jeton_appareil')
    if (!j) {
      j = crypto.randomUUID
        ? crypto.randomUUID()
        : Date.now() + '-' + Math.random().toString(16).slice(2)
      localStorage.setItem('jeton_appareil', j)
    }
    return j
  } catch {
    return 'inconnu'
  }
}

// Envoie un signalement. [H] format a confirmer dans docs/api-contract.md
export async function postSignalement({ type_dechet, volume_estime, description, latitude, longitude, audio, id_client, capture_le }) {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 800))
    const bloc = () => Math.random().toString(36).slice(2, 5).toUpperCase()
    const code = `${bloc()}-${bloc()}`
    // Simule le filtre hors zone du back. [H] boite autour de Ouaga
    const horsZone = latitude < 12.2 || latitude > 12.55 || longitude < -1.7 || longitude > -1.3
    return horsZone
      ? { id: 0, code_suivi: code, statut: 'rejete_auto', motif: "hors zone d'étude" }
      : { id: 0, code_suivi: code, statut: 'en_attente_revue', motif: null }
  }

  const form = new FormData()
  form.append('type_dechet', type_dechet)
  form.append('volume_estime', volume_estime)
  form.append('description', description ?? '')
  form.append('latitude', String(latitude))
  
  if (id_client) form.append('id_client', id_client)
  if (capture_le) form.append('capture_le', capture_le)
  if (audio) {
    const ext = audio.blob.type.includes('mp4') ? 'mp4' : 'webm'
    form.append('note_vocale', audio.blob, `note.${ext}`)
  }

  // Ne pas fixer Content-Type : le navigateur ajoute la bonne frontiere multipart.
  const res = await fetch(`${API_URL}/signalements`, {
    method: 'POST',
    headers: { 'X-Device-Token': jetonAppareil() },
    body: form,
  })
  if (!res.ok) {
    let detail = null
    try {
      detail = (await res.json()).detail
    } catch {
      // reponse sans JSON
    }
    const erreur = new Error(typeof detail === 'string' ? detail : `Erreur ${res.status}`)
    erreur.statut = res.status // permet de distinguer 429/503 (a reessayer) de 413/422 (definitif)
    throw erreur
  }
  return res.json()
}

// Statut d'un signalement a partir de son code de suivi.
export async function getSuivi(code) {
  const propre = code.trim().toUpperCase()
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 500))
    if (propre === 'K7M-4QD') {
      return { code_suivi: propre, statut: 'verifie', motif: null, depotoir_id: 3 }
    }
    if (propre === 'ERR-000') {
      return { code_suivi: propre, statut: 'rejete', motif: 'photo sans rapport', depotoir_id: null }
    }
    if (propre.startsWith('NON')) {
      const e = new Error('introuvable')
      e.introuvable = true
      throw e
    }
    return { code_suivi: propre, statut: 'en_attente_revue', motif: null, depotoir_id: null }
  }
  const res = await fetch(`${API_URL}/signalements/suivi/${encodeURIComponent(propre)}`)
  if (res.status === 404) {
    const e = new Error('introuvable')
    e.introuvable = true
    throw e
  }
  if (!res.ok) throw new Error(`Erreur ${res.status}`)
  return res.json()
}

// Erreur reseau (pas de reponse du serveur) = a mettre en file d'attente.
function estHorsLigne(err) {
  return err instanceof TypeError || !navigator.onLine
}

// Erreur definitive : le serveur refuse ce signalement, inutile de reessayer.
function estDefinitive(err) {
  return [400, 413, 422].includes(err.statut)
}

// Faut-il garder le signalement pour plus tard ? Reseau coupe ou erreur temporaire du serveur.
function aReessayer(err) {
  return estHorsLigne(err) || (typeof err.statut === 'number' && !estDefinitive(err))
}

// Tente l'envoi ; en cas de coupure ou d'erreur temporaire, met en file d'attente.
export async function signalerAvecFile(donnees) {
  // Identifiant et date fixes des le premier essai : si la reponse se perd, la file
  // renverra le meme id_client et le serveur ne creera pas de doublon.
  const id_client = nouvelleCle()
  const creeLe = Date.now()
  try {
    const reponse = await postSignalement({
      ...donnees,
      id_client,
      capture_le: new Date(creeLe).toISOString(),
    })
    return { envoye: true, reponse }
  } catch (err) {
    if (aReessayer(err)) {
      await ajouter(donnees, { cle: id_client, creeLe })
      return { envoye: false }
    }
    throw err
  }
}

export async function nombreEnAttente() {
  return (await lister()).length
}

// Renvoie les signalements en attente. Retourne le nombre envoye.
export async function viderFile() {
  let envoyes = 0
  for (const item of await lister()) {
    try {
      await postSignalement({
        ...item.donnees,
        id_client: item.cle,
        capture_le: new Date(item.creeLe).toISOString(),
      })
      await retirer(item.cle) // 200 (deja recu) ou 201 : l'element peut partir
      envoyes += 1
    } catch (err) {
      // Refus definitif (400, 413, 422) : inutile de reessayer, on retire.
      // Tout le reste (reseau coupe, 429, 503, 500...) : on garde tout et on reessaiera.
      if (!estDefinitive(err)) break
      await retirer(item.cle)
    }
  }
  return envoyes
}

// ---- Session (connexion des roles admin, chauffeur, laabal) ----
const CLE_SESSION = 'yilgamde_session'

export function lireSession() {
  try {
    return JSON.parse(localStorage.getItem(CLE_SESSION))
  } catch {
    return null
  }
}

export function ecrireSession(s) {
  try {
    if (s) localStorage.setItem(CLE_SESSION, JSON.stringify(s))
    else localStorage.removeItem(CLE_SESSION)
  } catch {
    // stockage indisponible
  }
}

// Comptes de test, mode mock uniquement.
const COMPTES_MOCK = {
  'admin@test': { role: 'admin', nom: 'Admin (test)' },
  'chauffeur@test': { role: 'chauffeur', nom: 'Chauffeur (test)' },
  'laabal@test': { role: 'laabal', nom: 'Laabal (test)' },
}

// Renvoie { access_token, role, nom }.
export async function login(email, mot_de_passe) {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 400))
    const compte = COMPTES_MOCK[email.trim().toLowerCase()]
    if (!compte || mot_de_passe !== 'test') {
      const e = new Error('identifiants')
      e.identifiants = true
      throw e
    }
    return { access_token: 'mock-token', ...compte }
  }
  const res = await fetch(`${API_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: email.trim(), mot_de_passe }),
  })
  if (res.status === 401 || res.status === 403) {
    const e = new Error('identifiants')
    e.identifiants = true
    throw e
  }
  if (!res.ok) throw new Error(`Erreur ${res.status}`)
  const data = await res.json()
  return { ...data, nom: data.nom ?? email.trim() }
}

// Appel authentifie (en-tete Bearer) pour les routes /admin, /chauffeur, /laabal.
export async function appelAuth(chemin, options = {}) {
  const s = lireSession()
  const res = await fetch(`${API_URL}${chemin}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers ?? {}),
      Authorization: `Bearer ${s?.token ?? ''}`,
    },
  })
  if (res.status === 401) {
    ecrireSession(null) // session expiree
    window.location.assign('/connexion')
  }
  if (!res.ok) throw new Error(`Erreur ${res.status}`)
  return res.json()
}

// ---- Moderation (admin) ----
let MOCK_FILE = [
  { id: 12, latitude: 12.3714, longitude: -1.5197, type_dechet: 'menager', volume_estime: 'moyen',
    photo_url: null, audio_url: null, statut: 'en_attente_revue', score_auto: 0.82,
    alertes: [], cree_le: '2026-11-17T09:30:00Z' },
  { id: 13, latitude: 12.37142, longitude: -1.51972, type_dechet: 'menager', volume_estime: 'moyen',
    photo_url: null, audio_url: null, statut: 'en_attente_revue', score_auto: 0.55,
    alertes: ['doublon_probable:12'], cree_le: '2026-11-17T09:41:00Z' },
  { id: 14, latitude: 12.4, longitude: -1.5, type_dechet: 'plastiques', volume_estime: 'petit',
    photo_url: null, audio_url: null, statut: 'en_attente_revue', score_auto: 0.7,
    alertes: [], cree_le: '2026-11-17T10:02:00Z' },
]

export async function getFileModeration() {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 300))
    return [...MOCK_FILE]
  }
  return appelAuth('/admin/signalements?statut=en_attente_revue')
}

export async function validerSignalement(id, fusionnerAvec = null) {
  if (USE_MOCK) {
    MOCK_FILE = MOCK_FILE.filter((s) => s.id !== id)
    return { ok: true }
  }
  return appelAuth(`/admin/signalements/${id}/valider`, {
    method: 'POST',
    body: JSON.stringify({ fusionner_avec: fusionnerAvec }),
  })
}

export async function rejeterSignalement(id, motif) {
  if (USE_MOCK) {
    MOCK_FILE = MOCK_FILE.filter((s) => s.id !== id)
    return { ok: true }
  }
  return appelAuth(`/admin/signalements/${id}/rejeter`, {
    method: 'POST',
    body: JSON.stringify({ motif }),
  })
}

// ---- Scenarios et plan (admin) ----
let MOCK_PARAMS = { camions: 3, camions_en_panne: 0, saison_pluies: false, menages_nouveau_quartier: 0, budget_xof: 500000 }

// Plan simule a partir des parametres (mock uniquement).
function planMock(p) {
  const actifs = Math.max(p.camions - p.camions_en_panne, 0)
  const facteur = (p.saison_pluies ? 1.4 : 1) * (1 + p.menages_nouveau_quartier / 20000)
  const tournees = []
  for (let i = 0; i < actifs; i++) {
    const dec = i * 0.012
    tournees.push({
      id: i + 1, type: 'collecte', camion_id: `camion_${i + 1}`,
      distance_km: Math.round((14.2 * facteur) / Math.max(actifs, 1) * 3 * 10) / 10,
      duree_min: Math.round((95 * facteur) / Math.max(actifs, 1) * 3),
      cout_xof: Math.round((21000 * facteur) / Math.max(actifs, 1) * 3),
      arrets: [
        { ordre: 1, latitude: 12.369 + dec, longitude: -1.525 + dec, statut: 'a_faire' },
        { ordre: 2, latitude: 12.372 + dec, longitude: -1.515 - dec, statut: 'a_faire' },
        { ordre: 3, latitude: 12.378 + dec, longitude: -1.505 + dec, statut: 'a_faire' },
      ],
    })
  }
  const cout = tournees.reduce((t, x) => t + x.cout_xof, 0)
  return {
    duree_calcul_ms: 120 + Math.round(Math.random() * 300),
    points_regroupement: [
      { id: 1, latitude: 12.369, longitude: -1.525, capacite_kg: 3000, explication: 'Proche de 2 dépotoirs actifs' },
      { id: 2, latitude: 12.380, longitude: -1.505, capacite_kg: 3000, explication: 'Zone dense, près du marché' },
    ],
    tournees,
    indicateurs: {
      couverture_pct: Math.max(0, Math.min(100, Math.round(100 - (p.camions_en_panne * 18 + (p.saison_pluies ? 12 : 0) + p.menages_nouveau_quartier / 400)))),
      cout_total_xof: cout,
      hors_budget: cout > p.budget_xof,
    },
  }
}

export async function getParametres() {
  if (USE_MOCK) return { ...MOCK_PARAMS }
  return appelAuth('/scenarios/1') // [H] scenario courant = 1
}

// Modification partielle des parametres ; renvoie le plan recalcule.
export async function majParametres(partiel) {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 250))
    MOCK_PARAMS = { ...MOCK_PARAMS, ...partiel }
    return planMock(MOCK_PARAMS)
  }
  return appelAuth('/scenarios/1/parametres', { method: 'PUT', body: JSON.stringify(partiel) })
}

export async function getPlan() {
  if (USE_MOCK) return planMock(MOCK_PARAMS)
  return appelAuth('/scenarios/1/plan') // [H] route a confirmer
}

// ---- Chauffeur ----
let MOCK_TOURNEE = {
  id: 1, camion_id: 'camion_1', distance_km: 14.2, duree_min: 95,
  arrets: [
    { ordre: 1, nom: 'Point de regroupement n°1', latitude: 12.369, longitude: -1.525, statut: 'a_faire' },
    { ordre: 2, nom: 'Point de regroupement n°2', latitude: 12.38, longitude: -1.505, statut: 'a_faire' },
    { ordre: 3, nom: 'Marché de quartier', latitude: 12.375, longitude: -1.51, statut: 'a_faire' },
  ],
}

export async function getTournee() {
  if (USE_MOCK) return JSON.parse(JSON.stringify(MOCK_TOURNEE))
  return appelAuth('/chauffeur/tournee') // [H]
}

export async function marquerArret(ordre, statut) {
  if (USE_MOCK) {
    MOCK_TOURNEE.arrets = MOCK_TOURNEE.arrets.map((a) => (a.ordre === ordre ? { ...a, statut } : a))
    return { ok: true }
  }
  return appelAuth(`/chauffeur/arrets/${ordre}/${statut === 'effectue' ? 'effectue' : 'reset'}`, { method: 'POST' }) // [H]
}

// ---- Laabal ----
let MOCK_LAABAL = [
  { id: 1, latitude: 12.3714, longitude: -1.5197, volume_estime: 'moyen', legalite: 'illegal', statut: 'actif' },
  { id: 2, latitude: 12.365, longitude: -1.53, volume_estime: 'gros', legalite: 'illegal', statut: 'actif' },
  { id: 4, latitude: 12.39, longitude: -1.51, volume_estime: 'petit', legalite: 'illegal', statut: 'surveille' },
]

export async function getDepotoirsLaabal() {
  if (USE_MOCK) return MOCK_LAABAL.map((d) => ({ ...d }))
  return appelAuth('/laabal/depotoirs') // [H]
}

export async function changerStatutDepotoir(id, statut) {
  if (USE_MOCK) {
    MOCK_LAABAL = MOCK_LAABAL.map((d) => (d.id === id ? { ...d, statut } : d))
    return { ok: true }
  }
  return appelAuth(`/laabal/depotoirs/${id}/${statut}`, { method: 'POST' }) // [H]
}