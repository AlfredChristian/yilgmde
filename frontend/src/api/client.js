// Client d'acces aux donnees. Le composant ne sait pas si les donnees
// viennent du mock ou de l'API : tout passe par ce fichier.

// Attention : les variables Vite sont des chaines, pas des booleens.

import { ajouter, lister, retirer } from './fileAttente'

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
export async function postSignalement({ type_dechet, volume_estime, description, latitude, longitude, audio }) {
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
  form.append('longitude', String(longitude))
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
    throw new Error(typeof detail === 'string' ? detail : `Erreur ${res.status}`)
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

// Tente l'envoi ; sans reseau, met en file d'attente.
export async function signalerAvecFile(donnees) {
  try {
    return { envoye: true, reponse: await postSignalement(donnees) }
  } catch (err) {
    if (estHorsLigne(err)) {
      await ajouter(donnees)
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
      await postSignalement(item.donnees)
      await retirer(item.cle)
      envoyes += 1
    } catch (err) {
      if (estHorsLigne(err)) break // toujours pas de reseau : on arrete
      await retirer(item.cle) // refus du serveur : inutile de reessayer
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