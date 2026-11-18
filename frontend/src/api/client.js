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

// Renvoie un GeoJSON FeatureCollection de signalements de test (mock seulement).
// Avec l'API, les signalements bruts ne sont jamais publics (D11) : couche vide.
// Le jeu ouvert anonymise est a `${API_URL}/donnees/signalements.geojson` (D40).
export function getSignalements() {
  if (!USE_MOCK) return Promise.resolve({ type: 'FeatureCollection', features: [] })
  return getJson('/mock/signalements_exemple.geojson')
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
export async function postSignalement({ type_dechet, volume_estime, description, latitude, longitude, photo, audio, id_client, capture_le }) {
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

  if (id_client) form.append('id_client', id_client)
  if (capture_le) form.append('capture_le', capture_le)
  if (photo) form.append('photo', photo, photo.name || 'photo.jpg')
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
    // 422 de validation : FastAPI renvoie une liste [{ msg, ... }] ; on garde les messages lisibles.
    const message = typeof detail === 'string' ? detail
      : Array.isArray(detail) ? detail.map((d) => String(d.msg ?? '').replace(/^Value error, /, '')).filter(Boolean).join(' ; ')
      : ''
    const erreur = new Error(message || `Erreur ${res.status}`)
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
  if (res.status === 429) {
    const minutes = Math.ceil(Number(res.headers.get('Retry-After') ?? 900) / 60)
    throw new Error(`Trop d'essais : réessayez dans ${minutes} min`)
  }
  if (!res.ok) throw new Error(`Erreur ${res.status}`)
  const data = await res.json()
  // Le nom n'est pas dans la reponse de connexion : on le lit sur /auth/moi.
  let nom = email.trim()
  try {
    const moi = await fetch(`${API_URL}/auth/moi`, { headers: { Authorization: `Bearer ${data.access_token}` } })
    if (moi.ok) nom = (await moi.json()).nom ?? nom
  } catch {
    // nom par defaut : l'e-mail
  }
  return { ...data, nom }
}

// Appel authentifie (en-tete Bearer) pour les routes /admin, /chauffeur, /laabal.
// Corps FormData (photo) : pas de Content-Type, le navigateur ajoute la frontiere multipart.
// Les erreurs portent le statut HTTP et le message du serveur (champ `detail`).
export async function appelAuth(chemin, options = {}) {
  const s = lireSession()
  const multipart = options.body instanceof FormData
  const res = await fetch(`${API_URL}${chemin}`, {
    ...options,
    headers: {
      ...(multipart ? {} : { 'Content-Type': 'application/json' }),
      ...(options.headers ?? {}),
      Authorization: `Bearer ${s?.token ?? ''}`,
    },
  })
  if (res.status === 401) {
    ecrireSession(null) // session expiree
    window.location.assign('/connexion')
  }
  if (!res.ok) {
    let detail = null
    try {
      detail = (await res.json()).detail
    } catch {
      // reponse sans JSON
    }
    const e = new Error(typeof detail === 'string' ? detail : `Erreur ${res.status}`)
    e.statut = res.status
    throw e
  }
  return res.json()
}

// Fichier protege (photo, note vocale) : les balises <img>/<audio> n'envoient pas
// le jeton, on le telecharge donc avec l'en-tete et on renvoie une URL locale.
async function urlProtegee(chemin) {
  if (!chemin) return null
  const s = lireSession()
  const res = await fetch(`${API_URL}${chemin}`, { headers: { Authorization: `Bearer ${s?.token ?? ''}` } })
  return res.ok ? URL.createObjectURL(await res.blob()) : null
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
  // La file reste légère : photo et note vocale ne sont téléchargées que dans la fiche.
  const liste = await appelAuth('/admin/signalements?statut=en_attente_revue')
  return liste.map((s) => ({ ...s, a_photo: Boolean(s.photo_url), a_audio: Boolean(s.note_vocale_url) }))
}

// Fiche complète d'un signalement (D54) : description, quartier, appareil, voisinage, médias.
export async function getSignalementDetail(id) {
  if (USE_MOCK) {
    const s = MOCK_FILE.find((x) => x.id === id)
    if (!s) throw new Error('signalement introuvable')
    return { ...s, description: id === 13 ? 'Tas au bord de la voie, devant l’école' : null, secteur: 'Secteur 12', arrondissement: 3,
      contributeur: { score_confiance: 0.6, nb_signalements: 3, verifies: 2, rejetes: 0, bloque: false },
      depotoirs_proches: id === 13 ? [{ id: 3, distance_m: 40, latitude: 12.3716, longitude: -1.5195, statut: 'actif', legalite: 'illegal', volume_estime: 'moyen', nb_signalements: 4 }] : [],
      signalements_proches: id === 13 ? [{ id: 12, distance_m: 3, latitude: 12.3714, longitude: -1.5197, statut: 'en_attente_revue', type_dechet: 'menager', volume_estime: 'moyen', cree_le: '2026-11-17T09:30:00Z' }] : [] }
  }
  const s = await appelAuth(`/admin/signalements/${id}`)
  return { ...s, photo_url: await urlProtegee(s.photo_url), audio_url: await urlProtegee(s.note_vocale_url) }
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
let MOCK_PARAMS = { arrondissement: 0, camions_en_panne: 0, saison_pluies: false, budget_xof: 500000, nb_camions: 3, evolution_population_pct: 0, abonnement_pct: 30, frequence: 2, apport_volontaire_pct: 60, quartiers: [] }
let MOCK_SCENARIOS = [
  { id: 1, nom: 'base', parametres: {}, actif: true },
  { id: 2, nom: 'pluies', parametres: { scenario: { saison: 'pluies' } }, actif: false },
]
let PROCHAIN_MOCK_SCENARIO_ID = 3

// Plan simule a partir des parametres (mock uniquement).
function planMock(p) {
  const actifs = Math.max(p.nb_camions - p.camions_en_panne, 0)
  const facteur = p.saison_pluies ? 1.4 : 1
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
      // memes noms que l'API (D41)
      capacite_collecte_pct: Math.max(0, Math.min(100, 100 - p.camions_en_panne * 18)),
      part_captee_estimee_pct: p.saison_pluies ? 55.2 : 60.2,
      nb_points_regroupement: 2,
      camions_utilises: tournees.map((t) => t.camion_id),
      cout_mensuel_estime_xof: cout * 8,
      budget_mensuel_xof: p.budget_xof,
      budget_depasse: cout * 8 > p.budget_xof,
      camions_flotte: ['camion_1', 'camion_2', 'camion_3'],
    },
  }
}

// Avec l'API, le formulaire travaille sur le scenario actif. Ses parametres sont des
// surcharges de la config (docs/api-contract.md) ; on les traduit dans les deux sens.
let SCENARIO_ID = null
let FLOTTE = [] // ids de tous les camions, lus dans le dernier plan (indicateurs.camions_flotte)

async function scenarioActif() {
  if (SCENARIO_ID == null) {
    const liste = await appelAuth('/scenarios')
    SCENARIO_ID = (liste.find((sc) => sc.actif) ?? liste[0]).id
  }
  return SCENARIO_ID
}

function retenirFlotte(plan) {
  if (plan?.indicateurs?.camions_flotte) FLOTTE = plan.indicateurs.camions_flotte
  return plan
}

// Surcharges du scenario -> champs du formulaire (Plan.jsx).
function versFormulaire(p, plan) {
  const ind = plan.indicateurs
  return {
    arrondissement: p.perimetre?.arrondissements?.[0] ?? 0, // 0 = toute la commune
    saison_pluies: (p.scenario?.saison ?? p.saison) === 'pluies',
    camions_en_panne: (p.camions ?? []).filter((c) => c.disponible === false).length,
    // budget de la commune : celui du perimetre divise par sa part (D39)
    budget_xof: Math.round(ind.budget_mensuel_xof / (ind.perimetre?.part_budget ?? 1)),
    nb_camions: FLOTTE.length,
    // leviers de l'énoncé (D56) : valeurs en vigueur renvoyées par le plan
    evolution_population_pct: ind.leviers?.evolution_population_pct ?? 0,
    abonnement_pct: Math.round((ind.leviers?.taux_abonnement_precollecteurs ?? 0) * 100),
    frequence: ind.leviers?.frequence_passages_par_semaine ?? 2,
    apport_volontaire_pct: Math.round((ind.leviers?.prob_apport_volontaire ?? 0) * 100),
    quartiers: (p.zones_ajoutees ?? []).map((z) => {
      const f = typeof z === 'string' ? JSON.parse(z) : z
      const props = f.properties ?? {}
      return { nom: props.nom ?? 'Nouveau quartier', population: props.population ?? null, geometrie: f.type === 'Feature' ? f.geometry : f }
    }),
  }
}

// Champ du formulaire -> surcharge envoyee a PUT /scenarios/{id}/parametres.
function versApi(cle, valeur) {
  switch (cle) {
    case 'arrondissement':
      return { perimetre: { arrondissements: valeur ? [valeur] : [] } }
    case 'saison_pluies':
      return { scenario: { saison: valeur ? 'pluies' : 'seche' } }
    case 'camions_en_panne': // les N premiers camions de la flotte sont en panne
      // Jamais de liste vide : elle remplacerait toute la flotte de la config.
      if (!FLOTTE.length) throw new Error('flotte inconnue : rechargez la page')
      return { camions: FLOTTE.map((id, i) => ({ id, disponible: i >= valeur })) }
    case 'budget_xof':
      return { mairie: { budget_mensuel_xof: valeur } }
    case 'evolution_population_pct':
      return { population: { evolution_pct: valeur } }
    case 'abonnement_pct':
      return { population: { taux_abonnement_precollecteurs: valeur / 100 } }
    case 'frequence':
      return { collecte: { frequence_passages_par_semaine: valeur } }
    case 'apport_volontaire_pct':
      return { simulation: { prob_apport_volontaire: valeur / 100 } }
    case 'ajouter_quartier':   // valeur : Feature GeoJSON { properties: { nom, population } }
      return { zones_ajoutees: [valeur] }
    case 'retirer_quartier':   // valeur : position dans la liste des quartiers ajoutés
      return { retirer_zones: [valeur] }
    default:
      return { [cle]: valeur }
  }
}

export async function getParametres() {
  if (USE_MOCK) return { ...MOCK_PARAMS }
  const id = await scenarioActif()
  const [scenario, plan] = await Promise.all([appelAuth(`/scenarios/${id}`), getPlan()])
  return versFormulaire(scenario.parametres ?? {}, plan)
}

// Modification partielle des parametres ; renvoie le plan recalcule.
export async function majParametres(partiel) {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 250))
    MOCK_PARAMS = { ...MOCK_PARAMS, ...partiel }
    return planMock(MOCK_PARAMS)
  }
  const id = await scenarioActif()
  const [[cle, valeur]] = Object.entries(partiel)
  const plan = await appelAuth(`/scenarios/${id}/parametres`, {
    method: 'PUT',
    body: JSON.stringify(versApi(cle, valeur)),
  })
  return retenirFlotte(plan)
}

// Plan de gestion lisible (texte Markdown) du scénario de travail.
export async function getSynthese() {
  if (USE_MOCK) return '# Plan de gestion\n\nLa synthèse est disponible avec l’API.'
  const id = await scenarioActif()
  const s = lireSession()
  const res = await fetch(`${API_URL}/scenarios/${id}/plan/synthese`, { headers: { Authorization: `Bearer ${s?.token ?? ''}` } })
  if (!res.ok) throw new Error(`Erreur ${res.status}`)
  return res.text()
}

// Le même plan de gestion en PDF (D65), pour le téléchargement.
export async function getSynthesePdf() {
  if (USE_MOCK) throw new Error('Le PDF est disponible avec l’API.')
  const id = await scenarioActif()
  const s = lireSession()
  const res = await fetch(`${API_URL}/scenarios/${id}/plan/synthese.pdf`, { headers: { Authorization: `Bearer ${s?.token ?? ''}` } })
  if (!res.ok) throw new Error(`Erreur ${res.status}`)
  return res.blob()
}

export async function getPlan() {
  if (USE_MOCK) return planMock(MOCK_PARAMS)
  const id = await scenarioActif()
  return retenirFlotte(await appelAuth(`/scenarios/${id}/plan`))
}

// Liste, activation, simulation et comparaison des scénarios (tableau de bord D6).
// Le scénario actif reste celui que le formulaire de plan modifie.
export async function getScenarios() {
  if (USE_MOCK) return MOCK_SCENARIOS.map((scenario) => ({ ...scenario }))
  return appelAuth('/scenarios')
}

export async function activerScenario(id) {
  if (USE_MOCK) {
    MOCK_SCENARIOS = MOCK_SCENARIOS.map((scenario) => ({ ...scenario, actif: scenario.id === id }))
    return MOCK_SCENARIOS.find((scenario) => scenario.id === id)
  }
  const scenario = await appelAuth(`/scenarios/${id}/activer`, { method: 'POST' })
  SCENARIO_ID = scenario.id
  return scenario
}

// activer = true : la copie devient le scenario de travail (celui que le formulaire modifie).
export async function creerScenario(nom, baseSur, activer = false) {
  if (USE_MOCK) {
    const base = MOCK_SCENARIOS.find((scenario) => scenario.id === baseSur)
    const scenario = { id: PROCHAIN_MOCK_SCENARIO_ID++, nom, parametres: { ...(base?.parametres ?? {}) }, actif: activer }
    MOCK_SCENARIOS = [...MOCK_SCENARIOS.map((sc) => (activer ? { ...sc, actif: false } : sc)), scenario]
    return scenario
  }
  const scenario = await appelAuth('/scenarios', {
    method: 'POST',
    body: JSON.stringify({ nom, base_sur: baseSur, parametres: {}, activer }),
  })
  if (activer) SCENARIO_ID = scenario.id
  return scenario
}

function simulationMock(jours, graine) {
  const plan = planMock(MOCK_PARAMS)
  const capacite = plan.indicateurs.capacite_collecte_pct
  const partCaptee = Math.min(100, Math.max(0, 62 + (capacite - 70) * 0.28 - (MOCK_PARAMS.saison_pluies ? 8 : 0)))
  const indicateurs = Array.from({ length: jours }, (_, i) => ({
    jour: i + 1,
    part_captee_pct: Math.round((partCaptee + Math.sin((i + 1) * 0.7 + graine) * 3) * 10) / 10,
    depotoirs_actifs: Math.max(0, 4 + Math.round(i / 8) + MOCK_PARAMS.camions_en_panne),
    dechets_sauvages_kg: Math.round((100 - partCaptee) * 85 * (i + 1)),
    collecte_suspendue: plan.indicateurs.budget_depasse,
  }))
  const dernier = indicateurs[indicateurs.length - 1]
  return {
    scenario_id: 1,
    plan_id: 1,
    graine,
    indicateurs,
    resume: {
      jours,
      part_captee_moyenne_pct: Math.round(indicateurs.reduce((s, i) => s + i.part_captee_pct, 0) / jours * 10) / 10,
      depotoirs_actifs_debut: indicateurs[0].depotoirs_actifs,
      depotoirs_actifs_fin: dernier.depotoirs_actifs,
      dechets_sauvages_kg: dernier.dechets_sauvages_kg,
      passages_collecte: Math.floor(jours / 3),
      passages_suspendus_budget: plan.indicateurs.budget_depasse ? Math.floor(jours / 3) : 0,
      cout_total_xof: Math.round(plan.indicateurs.cout_mensuel_estime_xof * jours / 30),
      budget_restant_xof: Math.max(0, plan.indicateurs.budget_mensuel_xof - plan.indicateurs.cout_mensuel_estime_xof),
    },
  }
}

export async function simulerScenario(jours, graine) {
  if (USE_MOCK) return simulationMock(jours, graine)
  const id = await scenarioActif()
  return appelAuth(`/scenarios/${id}/simuler`, { method: 'POST', body: JSON.stringify({ jours, graine }) })
}

export async function comparerScenarios(ids, jours, graine) {
  if (USE_MOCK) {
    const simulation = simulationMock(jours, graine)
    const valeurs = [simulation.resume.part_captee_moyenne_pct, simulation.resume.part_captee_moyenne_pct - 8]
    return {
      jours,
      graine,
      scenarios: ids.map((id, i) => ({ id, nom: MOCK_SCENARIOS.find((scenario) => scenario.id === id)?.nom ?? `scénario ${i + 1}` })),
      indicateurs: [
        { source: 'plan', indicateur: 'capacite_collecte_pct', valeurs: [100, 82], ecart_a_la_reference: [0, -18], sens: 'plus', meilleur: [ids[0]] },
        { source: 'simulation', indicateur: 'part_captee_moyenne_pct', valeurs, ecart_a_la_reference: [0, -8], sens: 'plus', meilleur: [ids[0]] },
        { source: 'simulation', indicateur: 'depotoirs_actifs_fin', valeurs: [simulation.resume.depotoirs_actifs_fin, simulation.resume.depotoirs_actifs_fin + 3], ecart_a_la_reference: [0, 3], sens: 'moins', meilleur: [ids[0]] },
        { source: 'simulation', indicateur: 'dechets_sauvages_kg', valeurs: [simulation.resume.dechets_sauvages_kg, simulation.resume.dechets_sauvages_kg + 22000], ecart_a_la_reference: [0, 22000], sens: 'moins', meilleur: [ids[0]] },
      ],
    }
  }
  return appelAuth(`/scenarios/comparer?ids=${ids.join(',')}&jours=${jours}&graine=${graine}`)
}

// Liste des arrondissements pour le choix du perimetre (livrable 3).
export async function getArrondissements() {
  if (USE_MOCK) return []
  return getJson(`${API_URL}/arrondissements`)
}

// ---- Suivi de la flotte (admin, D51) ----
// Avancement reel du plan courant : arrets coches (avec l'heure) et agent affecte.
export async function getSuiviFlotte() {
  if (USE_MOCK) {
    const plan = planMock(MOCK_PARAMS)
    const tournees = plan.tournees.map((t, i) => ({
      ...t, type: 'collecte', jour: 1, rotation: 1, affectee_a: i === 0 ? 11 : null, affectee_nom: i === 0 ? 'Issa chauffeur' : null,
      arrets: t.arrets.map((a, k) => ({ ...a, id: i * 100 + k, cible_id: a.ordre, statut: i === 0 && k === 0 ? 'effectue' : 'a_faire',
        effectue_le: i === 0 && k === 0 ? new Date().toISOString() : null })),
    })).map((t) => ({ ...t, arrets_total: t.arrets.length, arrets_effectues: t.arrets.filter((a) => a.statut === 'effectue').length,
      derniere_activite: t.arrets.find((a) => a.effectue_le)?.effectue_le ?? null }))
    return {
      plan_id: 1, depot: { latitude: 12.43, longitude: -1.47 }, jours: [1], tournees,
      resume: { arrets_total: tournees.reduce((s, t) => s + t.arrets_total, 0), arrets_effectues: 1, tournees_affectees: 1, tournees_terminees: 0 },
    }
  }
  return appelAuth('/admin/suivi')
}

// Suivi de l'éradication des dépotoirs (admin, D60) : signalé, validé, intervention, éradiqué.
export async function getSuiviDepotoirs() {
  if (USE_MOCK) {
    const jour = 86400000, maintenant = Date.now()
    const iso = (t) => (t == null ? null : new Date(t).toISOString())
    const statuts = ['actif', 'actif', 'intervention_planifiee', 'eradique', 'eradique', 'sous_surveillance']
    const depotoirs = Array.from({ length: 36 }, (_, i) => {
      const statut = statuts[i % statuts.length]
      const lat = 12.33 + ((i * 37) % 100) / 1000, lon = -1.56 + ((i * 53) % 110) / 1000
      const signale = maintenant - (40 - i) * jour
      const valide = signale + 5 * 3600000
      const intervention = statut === 'actif' ? null : valide + 2 * jour
      const eradique = ['eradique', 'sous_surveillance'].includes(statut) ? intervention + jour : null
      return {
        id: i + 1, latitude: lat, longitude: lon, zone_nom: `Secteur ${(i % 12) + 1}`, volume_estime: ['petit', 'moyen', 'gros'][i % 3],
        statut, nb_signalements: 1 + (i % 3), nb_reapparitions: 0, brigade: intervention ? 'Awa Laabal' : null,
        etapes: { signale: iso(signale), valide: iso(valide), intervention: iso(intervention), eradique: iso(eradique),
          surveillance: statut === 'sous_surveillance' ? iso(eradique + 3 * jour) : null },
        dates_estimees: false, photo_intervention: Boolean(eradique),
        delai_eradication_jours: eradique ? Math.round(((eradique - signale) / jour) * 10) / 10 : null,
        signalements: Array.from({ length: 1 + (i % 3) }, (_, k) => ({ id: i * 10 + k, latitude: lat + k * 0.0004, longitude: lon - k * 0.0003, cree_le: iso(signale + k * jour) })),
      }
    })
    const n = (s) => depotoirs.filter((d) => d.statut === s).length
    return {
      debut: depotoirs[0].etapes.signale, fin: iso(maintenant),
      resume: { depotoirs: depotoirs.length, a_traiter: n('actif'), en_intervention: n('intervention_planifiee'),
        eradiques: n('eradique') + n('sous_surveillance'), sous_surveillance: n('sous_surveillance'), delai_median_jours: 2.2 },
      depotoirs,
    }
  }
  return appelAuth('/admin/suivi-depotoirs')
}

// Simulation d'un quartier (admin, D62).
export async function getSecteursQuartier() {
  if (USE_MOCK) return [{ id: 1, nom: 'Secteur 1', population: 42000, points: 6 }]
  return appelAuth('/admin/simulation-quartier/secteurs')
}

export async function getSimulationQuartier(zoneId, pointId = null, graine = 1) {
  if (!USE_MOCK) {
    const q = new URLSearchParams({ zone_id: zoneId, graine })
    if (pointId != null) q.set('point_id', pointId)
    return appelAuth(`/admin/simulation-quartier?${q}`)
  }
  // Démonstration hors serveur : un petit quartier en grille, trajets en ligne droite.
  let x = graine * 9301 + 49297
  const hasard = () => ((x = (x * 9301 + 49297) % 233280) / 233280)
  const c = [12.371, -1.52], d = 0.004
  const points = [{ id: 1, latitude: c[0], longitude: c[1], vide_min: null, dans_le_secteur: true }, { id: 2, latitude: c[0] + 0.0025, longitude: c[1] - 0.002, vide_min: null, dans_le_secteur: true }]
  const sauvage = { id: 'v1', latitude: c[0] - 0.0032, longitude: c[1] + 0.003, existant: false, depotoir_id: null }
  const maisons = Array.from({ length: 60 }, (_, i) => {
    const la = c[0] + (hasard() - 0.5) * d * 2, lo = c[1] + (hasard() - 0.5) * d * 2
    const r = hasard(), mode = r < 0.3 ? 'abonne' : r < 0.7 ? 'apport' : 'sauvage'
    const p = Math.abs(la - points[0].latitude) + Math.abs(lo - points[0].longitude) < Math.abs(la - points[1].latitude) + Math.abs(lo - points[1].longitude) ? points[0] : points[1]
    return { id: i + 1, latitude: la, longitude: lo, mode, point_id: p.id, sortie_min: 360 + hasard() * 90, ...(mode === 'sauvage' ? { sauvage_id: 'v1' } : {}) }
  })
  const seg = (a, b, t0, v) => { const l = Math.hypot(a[0] - b[0], a[1] - b[1]) * 111000; return { t0, t1: t0 + Math.max(0.5, l / v), trace: [a, b] } }
  const pietons = maisons.filter((m) => m.mode !== 'abonne').map((m) => {
    const cible = m.mode === 'apport' ? points.find((p) => p.id === m.point_id) : sauvage
    const t0 = Math.max(m.sortie_min, 390 + hasard() * 150)
    const aller = seg([m.latitude, m.longitude], [cible.latitude, cible.longitude], t0, 67)
    const depose = { t0: aller.t1, t1: aller.t1 + 1, trace: [[cible.latitude, cible.longitude]] }
    m.depart_min = t0; m.depot_min = depose.t0
    return { maison_id: m.id, mode: m.mode, segments: [aller, depose, seg([cible.latitude, cible.longitude], [m.latitude, m.longitude], depose.t1, 67)] }
  })
  const tricycles = points.map((p, k) => {
    const groupe = maisons.filter((m) => m.mode === 'abonne' && m.point_id === p.id)
    let t = 420 + 4 * k, ici = [p.latitude, p.longitude]
    const segments = [], arrets = []
    for (const m of groupe) {
      const s1 = seg(ici, [m.latitude, m.longitude], t, 133); segments.push(s1); t = Math.max(s1.t1, m.sortie_min) + 1.5
      segments.push({ t0: s1.t1, t1: t, trace: [[m.latitude, m.longitude]] }); m.collecte_min = t; arrets.push({ maison_id: m.id, t }); ici = [m.latitude, m.longitude]
    }
    const s2 = seg(ici, [p.latitude, p.longitude], t, 133); segments.push(s2)
    segments.push({ t0: s2.t1, t1: s2.t1 + 6, trace: [[p.latitude, p.longitude]] })
    return { id: k + 1, point_id: p.id, segments, arrets, vidage_min: s2.t1 + 6, poubelles: groupe.length }
  })
  const camions = points.map((p) => {
    const arrivee = Math.max(...tricycles.filter((x) => x.point_id === p.id).map((x) => x.vidage_min), ...pietons.filter((x) => x.mode === 'apport' && maisons[x.maison_id - 1].point_id === p.id).map((x) => x.segments[1].t0)) + 30
    p.vide_min = arrivee + 6
    const loin = [p.latitude + 0.01, p.longitude + 0.012]
    return { point_id: p.id, vide_min: arrivee + 6, segments: [{ t0: arrivee - 6, t1: arrivee, trace: [loin, [p.latitude, p.longitude]] }, { t0: arrivee, t1: arrivee + 6, trace: [[p.latitude, p.longitude]] }, { t0: arrivee + 6, t1: arrivee + 12, trace: [[p.latitude, p.longitude], loin] }] }
  })
  const n = (mode) => maisons.filter((m) => m.mode === mode).length
  const cercle = { type: 'Polygon', coordinates: [Array.from({ length: 33 }, (_, k) => [c[1] + 0.0047 * Math.cos((k / 32) * 2 * Math.PI), c[0] + 0.0045 * Math.sin((k / 32) * 2 * Math.PI)])] }
  return {
    zone: { id: zoneId, nom: 'Secteur 1', population: 900, geometrie: cercle }, secteur: { id: zoneId, nom: 'Secteur 1', population: 42000, geometrie: cercle },
    centre: { point_id: 1, latitude: c[0], longitude: c[1], rayon_m: 450 }, points_du_secteur: points, graine,
    horaire: { debut: 345, fin: Math.ceil(Math.max(...camions.map((x) => x.segments[2].t1), ...pietons.map((x) => x.segments[2].t1)) + 10) },
    echelle: { maisons: maisons.length, batiments_du_quartier: 2400, menages_par_maison: 6, kg_par_maison: 21.6 },
    regles: { taux_abonnement: 0.3, prob_apport: 0.6, distance_max_a_pied_m: 300, sur_les_voies: false },
    maisons, points, sauvages: [sauvage], tricycles, pietons, camions,
    resume: { abonnes: n('abonne'), apport_volontaire: n('apport'), depot_sauvage: n('sauvage'), kg_precollectes: n('abonne') * 21.6, kg_apportes: n('apport') * 21.6, kg_sauvages: n('sauvage') * 21.6, tricycles: tricycles.length },
  }
}

// ---- Comptes (admin, D49) ----
let MOCK_UTILISATEURS = [
  { id: 1, nom: 'Administrateur', email: 'admin@test', role: 'admin', actif: true },
  { id: 11, nom: 'Issa chauffeur', email: 'chauffeur@test', role: 'chauffeur', actif: true },
  { id: 12, nom: 'Awa Laabal', email: 'laabal@test', role: 'laabal', actif: true },
]

export async function getUtilisateurs() {
  if (USE_MOCK) return MOCK_UTILISATEURS.map((u) => ({ ...u }))
  return appelAuth('/admin/utilisateurs')
}

// { nom, email, mot_de_passe, role } ; erreur 409 si l'e-mail existe deja.
export async function creerUtilisateur(compte) {
  if (USE_MOCK) {
    if (MOCK_UTILISATEURS.some((u) => u.email === compte.email.trim().toLowerCase())) throw new Error('un compte existe déjà avec cet email')
    const cree = { id: Math.max(...MOCK_UTILISATEURS.map((u) => u.id)) + 1, nom: compte.nom, email: compte.email.trim().toLowerCase(), role: compte.role, actif: true }
    MOCK_UTILISATEURS = [...MOCK_UTILISATEURS, cree]
    return cree
  }
  return appelAuth('/admin/utilisateurs', { method: 'POST', body: JSON.stringify(compte) })
}

// changements : { nom?, role?, actif? }. Le serveur refuse (409) qu'un admin se desactive
// ou se retire son role, ou qu'il ne reste plus d'admin actif.
export async function modifierUtilisateur(id, changements) {
  if (USE_MOCK) {
    MOCK_UTILISATEURS = MOCK_UTILISATEURS.map((u) => (u.id === id ? { ...u, ...changements } : u))
    return MOCK_UTILISATEURS.find((u) => u.id === id)
  }
  return appelAuth(`/admin/utilisateurs/${id}`, { method: 'PATCH', body: JSON.stringify(changements) })
}

export async function reinitialiserMotDePasse(id, motDePasse) {
  if (USE_MOCK) return MOCK_UTILISATEURS.find((u) => u.id === id)
  return appelAuth(`/admin/utilisateurs/${id}/mot-de-passe`, { method: 'POST', body: JSON.stringify({ mot_de_passe: motDePasse }) })
}

export async function affecterTournee(tourneeId, utilisateurId) {
  if (USE_MOCK) return { id: tourneeId, affectee_a: utilisateurId }
  return appelAuth(`/admin/tournees/${tourneeId}/affecter`, {
    method: 'POST', body: JSON.stringify({ utilisateur_id: utilisateurId }),
  })
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

// Toutes les rotations affectees au chauffeur, mises bout a bout dans une seule liste.
// Renvoie null si aucune tournee ne lui est affectee.
export async function getTournee() {
  if (USE_MOCK) return JSON.parse(JSON.stringify(MOCK_TOURNEE))
  const { tournees } = await appelAuth('/chauffeur/tournee')
  if (!tournees.length) return null
  let ordre = 0
  return {
    id: tournees[0].id,
    camion_id: [...new Set(tournees.map((t) => t.camion_id))].join(', '),
    distance_km: Math.round(tournees.reduce((s, t) => s + t.distance_km, 0) * 10) / 10,
    duree_min: Math.round(tournees.reduce((s, t) => s + t.duree_min, 0)),
    // tracé sur les voies (D52) : toutes les rotations bout à bout, dépôt compris
    trace: tournees.every((t) => t.trace) ? tournees.flatMap((t) => t.trace.flat()) : null,
    arrets: tournees.flatMap((t) =>
      t.arrets.map((a) => ({
        ...a,
        ordre: ++ordre,
        rotation: t.rotation ?? 1,
        nom: `Point de regroupement n°${a.cible_id}`,
      })),
    ),
  }
}

// Le serveur ne sait que cocher un arret (pas d'annulation).
export async function marquerArret(arret) {
  if (USE_MOCK) {
    MOCK_TOURNEE.arrets = MOCK_TOURNEE.arrets.map((a) => (a.ordre === arret.ordre ? { ...a, statut: 'effectue' } : a))
    return { ok: true }
  }
  return appelAuth(`/chauffeur/arrets/${arret.id}/effectue`, { method: 'POST' })
}

// ---- Laabal ----
let MOCK_LAABAL = [
  { id: 1, latitude: 12.3714, longitude: -1.5197, volume_estime: 'moyen', legalite: 'illegal', statut: 'actif' },
  { id: 2, latitude: 12.365, longitude: -1.53, volume_estime: 'gros', legalite: 'illegal', statut: 'actif' },
  { id: 4, latitude: 12.39, longitude: -1.51, volume_estime: 'petit', legalite: 'illegal', statut: 'intervention_planifiee' },
]

// Depotoirs illegaux a traiter, du plus prioritaire au moins prioritaire (avec la raison).
export async function getDepotoirsLaabal() {
  if (USE_MOCK) return MOCK_LAABAL.map((d) => ({ ...d }))
  const liste = await appelAuth('/laabal/depotoirs-a-traiter')
  return liste.map((d) => ({ ...d, legalite: 'illegal' }))
}

// action : 'intervention_planifiee' (intervention en cours), 'eradique' ou 'sous_surveillance'.
// Cycle cote serveur (B5) : actif -> intervention_planifiee -> eradique -> sous_surveillance.
// Trajet de la brigade, de sa base au dépotoir et retour, sur les voies (D61), pour l'animation.
export async function getItineraireLaabal(id) {
  if (USE_MOCK) {
    const d = MOCK_LAABAL.find((x) => x.id === id)
    const base = [12.43, -1.47], site = [d.latitude, d.longitude]
    const coude = [base[0], site[1]]
    return { depotoir_id: id, base: { latitude: base[0], longitude: base[1] }, aller: [base, coude, site], retour: [site, coude, base],
      distance_aller_m: 9000, distance_retour_m: 9000, sur_les_voies: false }
  }
  return appelAuth(`/laabal/depotoirs/${id}/itineraire`)
}

export async function changerStatutDepotoir(id, action, photo = null) {
  if (USE_MOCK) {
    MOCK_LAABAL = MOCK_LAABAL.map((d) => (d.id === id ? { ...d, statut: action } : d))
    return { ok: true }
  }
  if (action === 'sous_surveillance') {
    return appelAuth(`/laabal/depotoirs/${id}/surveillance`, { method: 'POST' })
  }
  const form = new FormData()
  form.append('statut', action === 'eradique' ? 'eradique' : 'en_cours')
  if (photo) form.append('photo', photo)
  return appelAuth(`/laabal/depotoirs/${id}/intervention`, { method: 'POST', body: form })
}