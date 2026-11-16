// Client d'acces aux donnees. Le composant ne sait pas si les donnees
// viennent du mock ou de l'API : tout passe par ce fichier.

// Attention : les variables Vite sont des chaines, pas des booleens.
const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true'
const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

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
