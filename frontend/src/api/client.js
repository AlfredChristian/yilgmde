// Client d'acces aux donnees. Le composant ne sait pas si les donnees
// viennent du mock ou de l'API : tout passe par ce fichier.

// Attention : les variables Vite sont des chaines, pas des booleens.
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