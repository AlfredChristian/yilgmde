import { useEffect, useRef, useState } from 'react'
import { MapContainer, TileLayer, CircleMarker, Polyline, Popup, useMap } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import Icone from '../components/Icone'
import { getParametres, majParametres, getPlan, getArrondissements } from '../api/client'
import './Plan.css'

const CENTRE = [12.3714, -1.5197]
const COULEURS = ['#1b6b4a', '#f4b942', '#7b2cbf', '#0077b6', '#d62828']

// Champs traduits en parametres de scenario dans api/client.js (versApi).
const PARAMETRES = [
  { cle: 'arrondissement', libelle: 'Périmètre', type: 'arrondissement' },
  { cle: 'camions_en_panne', libelle: 'Camions en panne', type: 'nombre', min: 0 },
  { cle: 'saison_pluies', libelle: 'Saison des pluies', type: 'bool' },
  { cle: 'budget_xof', libelle: 'Budget mensuel de la commune (XOF)', type: 'nombre', min: 0, pas: 1000000 },
]
const TOURNEES_AFFICHEES = 30
const fmt = (n) => Math.round(n).toLocaleString('fr-FR')

// Recadre la carte sur les points du plan quand le perimetre change.
function Recadrer({ points }) {
  const map = useMap()
  useEffect(() => {
    if (points.length) map.fitBounds(points.map((p) => [p.latitude, p.longitude]), { padding: [20, 20] })
  }, [map, points])
  return null
}

export default function Plan() {
  const [params, setParams] = useState(null)
  const [plan, setPlan] = useState(null)
  const [calcul, setCalcul] = useState(false)
  const [erreur, setErreur] = useState(null)
  const [dernierMs, setDernierMs] = useState(null)
  const [arrondissements, setArrondissements] = useState([])
  const delai = useRef(null)

  useEffect(() => {
    Promise.all([getParametres(), getPlan()])
      .then(([p, pl]) => { setParams(p); setPlan(pl) })
      .catch((e) => setErreur(e.message))
    getArrondissements().then(setArrondissements).catch(() => {})
  }, [])

  function changer(cle, valeur) {
    setParams((p) => ({ ...p, [cle]: valeur }))
    clearTimeout(delai.current)
    delai.current = setTimeout(async () => {
      setCalcul(true)
      setErreur(null)
      const debut = performance.now()
      try {
        const nouveau = await majParametres({ [cle]: valeur })
        setPlan(nouveau)
        setDernierMs(Math.round(performance.now() - debut))
      } catch (e) {
        setErreur(`Recalcul impossible : ${e.message}`)
      } finally {
        setCalcul(false)
      }
    }, 300)
  }

  if (!params || !plan) return <main className="plan-page"><p>{erreur ?? 'Chargement…'}</p></main>
  const ind = plan.indicateurs

  return (
    <main className="plan-page">
      <aside className="plan-panneau">
        <h1>Plan de gestion</h1>

        <div className="plan-etat">
          {calcul ? <span className="statut statut-attente">Recalcul…</span>
            : <span className="statut statut-ok">À jour{dernierMs != null && ` · ${dernierMs} ms`}</span>}
        </div>
        {erreur && <p className="mod-erreur">{erreur}</p>}

        <section className="carte plan-bloc">
          <div>
            <h2 className="carte-titre">Paramètres</h2>
            {PARAMETRES.map((d) => (
              <label key={d.cle} className="plan-champ">
                <span>{d.libelle}</span>
                {d.type === 'arrondissement' ? (
                  <select value={params.arrondissement} onChange={(e) => changer(d.cle, Number(e.target.value))}>
                    <option value={0}>Toute la commune</option>
                    {arrondissements.map((a) => (
                      <option key={a.arrondissement} value={a.arrondissement}>
                        Arrondissement {a.arrondissement} ({fmt(a.population)} hab.)
                      </option>
                    ))}
                  </select>
                ) : d.type === 'bool' ? (
                  <input type="checkbox" checked={!!params[d.cle]} onChange={(e) => changer(d.cle, e.target.checked)} />
                ) : (
                  <input
                    type="number" min={d.min} max={d.cle === 'camions_en_panne' ? params.nb_camions : d.max} step={d.pas ?? 1}
                    value={params[d.cle] ?? 0}
                    onChange={(e) => changer(d.cle, Number(e.target.value))}
                  />
                )}
              </label>
            ))}
          </div>
        </section>

        <section className="carte plan-bloc">
          <div>
            <h2 className="carte-titre">Indicateurs</h2>
            <p className="plan-chiffre" title="Part du stock des points que les camions peuvent vider à chaque passage">
              {ind.capacite_collecte_pct.toLocaleString('fr-FR')} % <small>capacité de collecte</small>
            </p>
            <p className="plan-chiffre" title="Part des déchets produits qui arrive aux points (pré-collecte + apport volontaire)">
              {ind.part_captee_estimee_pct.toLocaleString('fr-FR')} % <small>part captée estimée</small>
            </p>
            <p className="plan-chiffre">{ind.nb_points_regroupement} <small>points · {ind.camions_utilises.length} camions mobilisés</small></p>
            <p className="plan-chiffre">
              {fmt(ind.cout_mensuel_estime_xof)} <small>XOF/mois sur {fmt(ind.budget_mensuel_xof)} de budget</small>
            </p>
            {ind.budget_depasse && <p className="mod-alerte">Budget dépassé</p>}
          </div>
        </section>

        <section className="carte plan-bloc">
          <div>
            <h2 className="carte-titre">Tournées ({plan.tournees.length})</h2>
            {plan.tournees.length === 0 && <p className="carte-texte">Aucun camion actif.</p>}
            {plan.tournees.slice(0, TOURNEES_AFFICHEES).map((t, i) => (
              <p key={t.id} className="plan-tournee">
                <span className="plan-pastille" style={{ background: COULEURS[i % COULEURS.length] }} />
                {t.type === 'intervention' ? `Laabal, brigade ${t.brigade}` : `${t.camion_id}${t.jour ? ` · jour ${t.jour}` : ''}`}
                {' · '}{t.distance_km} km · {Math.round(t.duree_min)} min
              </p>
            ))}
            {plan.tournees.length > TOURNEES_AFFICHEES && (
              <p className="carte-texte">… et {plan.tournees.length - TOURNEES_AFFICHEES} autres (voir la synthèse).</p>
            )}
          </div>
        </section>
      </aside>

      <div className="plan-carte">
        <MapContainer center={CENTRE} zoom={13} style={{ height: '100%', width: '100%' }}>
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          {plan.points_regroupement.map((p) => (
            <CircleMarker key={`p${p.id}`} center={[p.latitude, p.longitude]} radius={plan.points_regroupement.length > 300 ? 4 : 8}
              pathOptions={{ color: '#124a34', fillColor: '#f4b942', fillOpacity: 0.95 }}>
              <Popup><strong>Point de regroupement n°{p.id}</strong><br />{p.explication}</Popup>
            </CircleMarker>
          ))}
          {plan.tournees.map((t, i) => (
            <Polyline key={`t${t.id}`} positions={t.arrets.map((a) => [a.latitude, a.longitude])}
              pathOptions={{ color: COULEURS[i % COULEURS.length], weight: 2 }} />
          ))}
          <Recadrer points={plan.points_regroupement} />
        </MapContainer>
      </div>
    </main>
  )
}