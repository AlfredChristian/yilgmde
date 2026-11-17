import { useEffect, useRef, useState } from 'react'
import { MapContainer, TileLayer, CircleMarker, Polyline, Popup } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import Icone from '../components/Icone'
import { getParametres, majParametres, getPlan } from '../api/client'
import './Plan.css'

const CENTRE = [12.3714, -1.5197]
const COULEURS = ['#1b6b4a', '#f4b942', '#7b2cbf', '#0077b6', '#d62828']

// [H] a aligner avec config/default.yaml
const PARAMETRES = [
  { cle: 'camions', libelle: 'Camions disponibles', type: 'nombre', min: 0, max: 10 },
  { cle: 'camions_en_panne', libelle: 'Camions en panne', type: 'nombre', min: 0, max: 10 },
  { cle: 'saison_pluies', libelle: 'Saison des pluies', type: 'bool' },
  { cle: 'menages_nouveau_quartier', libelle: 'Ménages du nouveau quartier', type: 'nombre', min: 0, max: 20000, pas: 500 },
  { cle: 'budget_xof', libelle: 'Budget (XOF)', type: 'nombre', min: 0, max: 5000000, pas: 50000 },
]

export default function Plan() {
  const [params, setParams] = useState(null)
  const [plan, setPlan] = useState(null)
  const [calcul, setCalcul] = useState(false)
  const [erreur, setErreur] = useState(null)
  const [dernierMs, setDernierMs] = useState(null)
  const delai = useRef(null)

  useEffect(() => {
    Promise.all([getParametres(), getPlan()])
      .then(([p, pl]) => { setParams(p.parametres ?? p); setPlan(pl) })
      .catch((e) => setErreur(e.message))
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
                {d.type === 'bool' ? (
                  <input type="checkbox" checked={!!params[d.cle]} onChange={(e) => changer(d.cle, e.target.checked)} />
                ) : (
                  <input
                    type="number" min={d.min} max={d.max} step={d.pas ?? 1}
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
            <p className="plan-chiffre">{ind.couverture_pct} % <small>couverture</small></p>
            <p className="plan-chiffre">{ind.cout_total_xof.toLocaleString('fr-FR')} <small>XOF de coût</small></p>
            {ind.hors_budget && <p className="mod-alerte">Budget dépassé</p>}
          </div>
        </section>

        <section className="carte plan-bloc">
          <div>
            <h2 className="carte-titre">Tournées ({plan.tournees.length})</h2>
            {plan.tournees.length === 0 && <p className="carte-texte">Aucun camion actif.</p>}
            {plan.tournees.map((t, i) => (
              <p key={t.id} className="plan-tournee">
                <span className="plan-pastille" style={{ background: COULEURS[i % COULEURS.length] }} />
                {t.camion_id} · {t.distance_km} km · {t.duree_min} min
              </p>
            ))}
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
            <CircleMarker key={`p${p.id}`} center={[p.latitude, p.longitude]} radius={12}
              pathOptions={{ color: '#124a34', fillColor: '#f4b942', fillOpacity: 0.95 }}>
              <Popup><strong>Point de regroupement n°{p.id}</strong><br />{p.explication}</Popup>
            </CircleMarker>
          ))}
          {plan.tournees.map((t, i) => (
            <Polyline key={`t${t.id}`} positions={t.arrets.map((a) => [a.latitude, a.longitude])}
              pathOptions={{ color: COULEURS[i % COULEURS.length], weight: 5 }} />
          ))}
        </MapContainer>
      </div>
    </main>
  )
}