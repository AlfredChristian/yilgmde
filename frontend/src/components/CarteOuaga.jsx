import { useEffect, useMemo, useState } from 'react'
import { getDepotoirs } from '../api/client'

// Les 12 arrondissements de Ouagadougou (découpage INSD) et les dépotoirs vérifiés, en SVG :
// s'affiche sans connexion, sans fond de carte. Utilisée en ouverture de l'accueil.
const L = 560
const H = 480

export default function CarteOuaga() {
  const [arr, setArr] = useState(null)
  const [depotoirs, setDepotoirs] = useState([])

  useEffect(() => {
    fetch('/ouaga-arrondissements.json').then((r) => r.json()).then(setArr).catch(() => {})
    getDepotoirs().then((d) => setDepotoirs(d.features ?? [])).catch(() => {})
  }, [])

  const proj = useMemo(() => {
    if (!arr) return null
    const pts = arr.features.flatMap((f) => anneaux(f.geometry).flat())
    const lons = pts.map((p) => p[0])
    const lats = pts.map((p) => p[1])
    const [x0, x1, y0, y1] = [Math.min(...lons), Math.max(...lons), Math.min(...lats), Math.max(...lats)]
    const k = Math.cos((((y0 + y1) / 2) * Math.PI) / 180)
    const echelle = Math.min((L - 24) / ((x1 - x0) * k), (H - 24) / (y1 - y0))
    const dx = (L - (x1 - x0) * k * echelle) / 2
    const dy = (H - (y1 - y0) * echelle) / 2
    return ([lon, lat]) => [dx + (lon - x0) * k * echelle, dy + (y1 - lat) * echelle]
  }, [arr])

  if (!proj) return <div className="carte-ouaga carte-ouaga-vide" aria-hidden="true" />

  const actifs = depotoirs.filter((f) => f.properties.legalite !== 'officiel' && ['actif', 'intervention_planifiee'].includes(f.properties.statut))
  const traites = depotoirs.filter((f) => f.properties.legalite !== 'officiel' && ['eradique', 'sous_surveillance'].includes(f.properties.statut))
  const point = (f) => proj(f.geometry.coordinates)

  return (
    <figure className="carte-ouaga">
      <svg viewBox={`0 0 ${L} ${H}`} role="img"
        aria-label={`Carte des 12 arrondissements de Ouagadougou : ${actifs.length} dépotoirs à traiter et ${traites.length} déjà traités`}>
        {arr.features.map((f) => (
          <g key={f.properties.arrondissement}>
            {anneaux(f.geometry).map((anneau, i) => (
              <path key={i} className="carte-ouaga-arr" d={chemin(anneau, proj)} />
            ))}
          </g>
        ))}
        {arr.features.map((f) => {
          const [cx, cy] = centre(anneaux(f.geometry)[0].map(proj))
          return <text key={`t${f.properties.arrondissement}`} x={cx} y={cy} className="carte-ouaga-num">{f.properties.arrondissement}</text>
        })}
        {traites.map((f) => { const [x, y] = point(f); return <circle key={f.properties.id} cx={x} cy={y} r="3.2" className="carte-ouaga-traite" /> })}
        {actifs.map((f) => { const [x, y] = point(f); return <circle key={f.properties.id} cx={x} cy={y} r="3.6" className="carte-ouaga-actif" /> })}
      </svg>
      <figcaption className="carte-ouaga-legende">
        <span><i className="carte-ouaga-actif" /> {actifs.length} dépotoirs à traiter</span>
        <span><i className="carte-ouaga-traite" /> {traites.length} traités et surveillés</span>
        <span>12 arrondissements</span>
      </figcaption>
    </figure>
  )
}

function anneaux(g) {
  return g.type === 'Polygon' ? [g.coordinates[0]] : g.coordinates.map((p) => p[0])
}

function chemin(anneau, proj) {
  return anneau.map((p, i) => `${i ? 'L' : 'M'}${proj(p).map((v) => v.toFixed(1)).join(',')}`).join('') + 'Z'
}

// Centre de gravité d'un polygone (pour placer le numéro de l'arrondissement)
function centre(pts) {
  let a = 0, cx = 0, cy = 0
  for (let i = 0; i < pts.length - 1; i++) {
    const f = pts[i][0] * pts[i + 1][1] - pts[i + 1][0] * pts[i][1]
    a += f
    cx += (pts[i][0] + pts[i + 1][0]) * f
    cy += (pts[i][1] + pts[i + 1][1]) * f
  }
  return a ? [cx / (3 * a), cy / (3 * a)] : pts[0]
}
