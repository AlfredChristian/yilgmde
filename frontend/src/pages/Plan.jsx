import { useEffect, useRef, useState } from 'react'
import { MapContainer, TileLayer, CircleMarker, Polyline, Popup, useMap } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import { activerScenario, affecterTournee, comparerScenarios, creerScenario, getArrondissements, getParametres, getPlan, getScenarios, getUtilisateurs, majParametres, simulerScenario } from '../api/client'
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
const fmtNombre = (n) => (n == null ? '—' : typeof n === 'number' ? n.toLocaleString('fr-FR', { maximumFractionDigits: 1 }) : n)
const LIBELLES_COMPARAISON = {
  capacite_collecte_pct: 'Capacité de collecte',
  part_captee_estimee_pct: 'Part captée estimée',
  nb_points_regroupement: 'Points de regroupement',
  distance_totale_km: 'Distance totale (km)',
  cout_total_xof: 'Coût d’un passage (XOF)',
  cout_mensuel_estime_xof: 'Coût mensuel estimé (XOF)',
  part_captee_moyenne_pct: 'Part captée moyenne',
  nouveaux_depotoirs: 'Nouveaux dépotoirs',
  depotoirs_actifs_fin: 'Dépotoirs actifs en fin de période',
  dechets_sauvages_kg: 'Déchets sauvages cumulés (t)',
  passages_suspendus_budget: 'Passages suspendus par le budget',
}

// Valeur affichée d'un indicateur : les kg en tonnes, les parts avec « % ».
function valeurIndicateur(cle, n) {
  if (n == null) return '—'
  if (cle.endsWith('_kg')) return fmt(n / 1000)
  return fmtNombre(n) + (cle.endsWith('_pct') ? ' %' : '')
}

// Recadre la carte sur les points du plan quand le perimetre change.
function Recadrer({ points }) {
  const map = useMap()
  useEffect(() => {
    if (points.length) map.fitBounds(points.map((p) => [p.latitude, p.longitude]), { padding: [20, 20] })
  }, [map, points])
  return null
}

function Courbe({ indicateurs }) {
  if (!indicateurs?.length) return null
  const largeur = 320
  const hauteur = 108
  const valeurs = indicateurs.map((i) => i.part_captee_pct)
  const min = Math.min(...valeurs)
  const max = Math.max(...valeurs)
  const amplitude = max - min || 1
  const points = valeurs.map((v, i) => `${(i / Math.max(valeurs.length - 1, 1)) * largeur},${hauteur - ((v - min) / amplitude) * (hauteur - 16) - 8}`).join(' ')
  return (
    <figure className="plan-courbe">
      <figcaption>Part captée jour par jour</figcaption>
      <svg viewBox={`0 0 ${largeur} ${hauteur}`} role="img" aria-label="Évolution quotidienne de la part captée">
        <line x1="0" x2={largeur} y1={hauteur - 8} y2={hauteur - 8} />
        <polyline points={points} />
      </svg>
      <small>min. {fmtNombre(min)} % · max. {fmtNombre(max)} %</small>
    </figure>
  )
}

function FlotteSimulation({ tournees, onRetourCarte }) {
  const [temps, setTemps] = useState(38)
  const collectes = tournees.filter((t) => t.type === 'collecte').slice(0, 8)

  useEffect(() => {
    const intervalle = setInterval(() => setTemps((valeur) => (valeur + 1) % 100), 1800)
    return () => clearInterval(intervalle)
  }, [])

  if (!collectes.length) {
    return (
      <section className="flotte-ecran flotte-ecran-vide">
        <div>
          <div className="flotte-entete"><div><h2 className="carte-titre">Suivi de la flotte</h2><p className="flotte-sous-titre">Simulation de déplacement des véhicules</p></div><span className="flotte-badge">Simulation locale</span></div>
          <div className="flotte-vide-contenu"><p className="carte-texte">Aucun camion n'est mobilisé dans le plan actuel. Les véhicules apparaîtront ici dès qu'une tournée de collecte sera calculée.</p><button className="btn-contour" onClick={onRetourCarte}>Retour à la carte</button></div>
        </div>
      </section>
    )
  }

  return (
    <section className="flotte-ecran">
      <div>
        <div className="flotte-entete">
          <div><h2 className="carte-titre">Suivi de la flotte</h2><p className="flotte-sous-titre"><span className="flotte-live" /> Déplacement simulé, mise à jour automatique</p></div>
          <div className="flotte-entete-actions"><span className="flotte-badge">Simulation locale</span><button className="flotte-retour" onClick={onRetourCarte}>Retour à la carte</button></div>
        </div>
        <div className="flotte-scene" aria-label="Simulation isométrique des camions">
          <div className="flotte-route flotte-route-a" />
          <div className="flotte-route flotte-route-b" />
          <div className="flotte-route flotte-route-c" />
          <div className="flotte-zone flotte-zone-a">ZONE 09</div>
          <div className="flotte-zone flotte-zone-b">ZONE 12</div>
          {collectes.map((tournee, index) => {
            const progress = (temps + index * 13) % 100
            const statut = progress > 82 ? 'Retour dépôt' : progress > 55 ? 'Collecte en cours' : 'En route'
            return (
              <div key={tournee.id} className="flotte-camion" style={{ left: `${12 + progress * 0.72}%`, top: `${18 + progress * 0.45}%` }}>
                <span className="flotte-camion-ombre" />
                <span className="flotte-camion-corps"><span className="flotte-camion-cabine" /><span className="flotte-camion-roue roue-a" /><span className="flotte-camion-roue roue-b" /></span>
                <span className="flotte-camion-label">{tournee.camion_id}<small>{statut}</small></span>
              </div>
            )
          })}
        </div>
        <div className="flotte-legende"><span><i className="flotte-dot flotte-dot-vert" /> En route</span><span><i className="flotte-dot flotte-dot-jaune" /> Collecte en cours</span><span><i className="flotte-dot flotte-dot-gris" /> Retour dépôt</span></div>
        <p className="flotte-note">Cette vue simule la position des véhicules. Elle sera alimentée par GPS lorsque les capteurs seront connectés.</p>
      </div>
    </section>
  )
}

export default function Plan() {
  const [params, setParams] = useState(null)
  const [plan, setPlan] = useState(null)
  const [calcul, setCalcul] = useState(false)
  const [erreur, setErreur] = useState(null)
  const [dernierMs, setDernierMs] = useState(null)
  const [arrondissements, setArrondissements] = useState([])
  const [scenarios, setScenarios] = useState([])
  const [simulation, setSimulation] = useState(null)
  const [simulationEnCours, setSimulationEnCours] = useState(false)
  const [comparaison, setComparaison] = useState(null)
  const [comparaisonEnCours, setComparaisonEnCours] = useState(false)
  const [jours, setJours] = useState(30)
  const [graine, setGraine] = useState(42)
  const [scenarioCompare, setScenarioCompare] = useState('')
  const [nomVariante, setNomVariante] = useState('')
  const [utilisateurs, setUtilisateurs] = useState([])
  const [affectations, setAffectations] = useState({})
  const [flotteOuverte, setFlotteOuverte] = useState(false)
  const [affectationEnCours, setAffectationEnCours] = useState(null)
  const delai = useRef(null)

  useEffect(() => {
    Promise.all([getParametres(), getPlan(), getScenarios(), getUtilisateurs()])
      .then(([p, pl, sc, usagers]) => {
        setParams(p)
        setPlan(pl)
        setScenarios(sc)
        setUtilisateurs(usagers.filter((u) => u.actif))
        setScenarioCompare(String(sc.find((s) => !s.actif)?.id ?? ''))
      })
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

  async function rafraichirScenario() {
    const [p, pl, sc] = await Promise.all([getParametres(), getPlan(), getScenarios()])
    setParams(p)
    setPlan(pl)
    setScenarios(sc)
    setSimulation(null)
    setComparaison(null)
  }

  async function choisirScenario(id) {
    if (!id) return
    setCalcul(true)
    setErreur(null)
    try {
      await activerScenario(Number(id))
      await rafraichirScenario()
    } catch (e) {
      setErreur(`Changement de scénario impossible : ${e.message}`)
    } finally {
      setCalcul(false)
    }
  }

  async function dupliquerScenario() {
    const actif = scenarios.find((s) => s.actif)
    if (!actif) return
    setCalcul(true)
    setErreur(null)
    try {
      // La variante devient le scénario de travail : les réglages suivants ne touchent plus la référence,
      // qui est présélectionnée pour la comparaison.
      const nom = nomVariante.trim() || `variante ${scenarios.length + 1}`
      await creerScenario(nom, actif.id, true)
      setNomVariante('')
      await rafraichirScenario()
      setScenarioCompare(String(actif.id))
    } catch (e) {
      setErreur(`Création du scénario impossible : ${e.message}`)
    } finally {
      setCalcul(false)
    }
  }

  async function lancerSimulation() {
    setSimulationEnCours(true)
    setErreur(null)
    try {
      setSimulation(await simulerScenario(jours, graine))
    } catch (e) {
      setErreur(`Simulation impossible : ${e.message}`)
    } finally {
      setSimulationEnCours(false)
    }
  }

  async function lancerComparaison() {
    const actif = scenarios.find((s) => s.actif)
    if (!actif || !scenarioCompare || Number(scenarioCompare) === actif.id) return
    setComparaisonEnCours(true)
    setErreur(null)
    try {
      setComparaison(await comparerScenarios([actif.id, Number(scenarioCompare)], jours, graine))
    } catch (e) {
      setErreur(`Comparaison impossible : ${e.message}`)
    } finally {
      setComparaisonEnCours(false)
    }
  }

  if (!params || !plan) return <main className="plan-page"><p>{erreur ?? 'Chargement…'}</p></main>
  const ind = plan.indicateurs
  const actif = scenarios.find((s) => s.actif)
  const resume = simulation?.resume
  const chauffeurs = utilisateurs.filter((u) => u.role === 'chauffeur')
  const brigades = utilisateurs.filter((u) => u.role === 'laabal')

  async function affecter(tournee, utilisateurId) {
    if (!utilisateurId) return
    setAffectationEnCours(tournee.id)
    setErreur(null)
    try {
      const resultat = await affecterTournee(tournee.id, Number(utilisateurId))
      setPlan((courant) => ({ ...courant, tournees: courant.tournees.map((t) => t.id === tournee.id ? { ...t, affectee_a: resultat.affectee_a } : t) }))
      setAffectations((courant) => ({ ...courant, [tournee.id]: '' }))
    } catch (e) {
      setErreur(`Affectation impossible : ${e.message}`)
    } finally {
      setAffectationEnCours(null)
    }
  }

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

        {params.arrondissement > 0 && (
          <p className="plan-limite">
            <strong>Hypothèse de démonstration :</strong> ce plan d’arrondissement peut mobiliser toute la flotte communale.
            L’affectation durable d’une part de flotte par arrondissement reste à modéliser.
          </p>
        )}

        <section className="carte plan-bloc">
          <div>
            <h2 className="carte-titre">Scénarios</h2>
            <label className="plan-select">
              <span>Scénario de travail</span>
              <select value={actif?.id ?? ''} onChange={(e) => choisirScenario(e.target.value)} disabled={calcul}>
                {scenarios.map((s) => <option key={s.id} value={s.id}>{s.nom}</option>)}
              </select>
            </label>
            <label className="plan-select">
              <span>Nom de la variante</span>
              <input type="text" value={nomVariante} placeholder="ex. pluies, panne, sensibilisation" maxLength={100}
                onChange={(e) => setNomVariante(e.target.value)} />
            </label>
            <button className="btn-contour plan-bouton" onClick={dupliquerScenario} disabled={calcul || !actif}>
              Créer une variante et la modifier
            </button>
            <p className="carte-texte">La variante copie les paramètres actuels et devient le scénario de travail : la référence reste intacte pour la comparaison.</p>
          </div>
        </section>

        <section className="carte plan-bloc">
          <div>
            <h2 className="carte-titre">Simulation</h2>
            <div className="plan-reglages">
              <label>Jours<input type="number" min="1" max="365" value={jours} onChange={(e) => setJours(Number(e.target.value))} /></label>
              <label>Graine<input type="number" value={graine} onChange={(e) => setGraine(Number(e.target.value))} /></label>
            </div>
            <button className="btn-contour plein plan-bouton" onClick={lancerSimulation} disabled={simulationEnCours}>
              {simulationEnCours ? 'Simulation en cours…' : `Simuler ${jours} jours`}
            </button>
            {resume && (
              <div className="plan-resultat">
                <p><strong>{fmtNombre(resume.part_captee_moyenne_pct)} %</strong> part captée moyenne</p>
                <p><strong>{fmt(resume.dechets_sauvages_kg / 1000)} t</strong> de déchets sauvages</p>
                {resume.nouveaux_depotoirs != null && <p><strong>{resume.nouveaux_depotoirs}</strong> nouveaux dépotoirs</p>}
                <p><strong>{resume.depotoirs_actifs_debut} → {resume.depotoirs_actifs_fin}</strong> dépotoirs actifs</p>
                <p><strong>{fmtNombre(resume.cout_total_xof)} XOF</strong> de coût simulé</p>
                <Courbe indicateurs={simulation.indicateurs} />
              </div>
            )}
          </div>
        </section>

        <section className="carte plan-bloc">
          <div>
            <h2 className="carte-titre">Comparer</h2>
            <label className="plan-select">
              <span>Comparer le scénario actif avec</span>
              <select value={scenarioCompare} onChange={(e) => setScenarioCompare(e.target.value)}>
                <option value="">Choisir une variante</option>
                {scenarios.filter((s) => !s.actif).map((s) => <option key={s.id} value={s.id}>{s.nom}</option>)}
              </select>
            </label>
            <button className="btn-contour plan-bouton" onClick={lancerComparaison} disabled={comparaisonEnCours || !scenarioCompare}>
              {comparaisonEnCours ? 'Comparaison en cours…' : 'Comparer à graine identique'}
            </button>
            {comparaison && (
              <div className="plan-comparaison">
                <p className="carte-texte">{comparaison.jours} jours · graine {comparaison.graine} · la première colonne est la référence.</p>
                <div className="plan-tableau-wrap">
                  <table>
                    <thead><tr><th>Indicateur</th>{comparaison.scenarios.map((s) => <th key={s.id}>{s.nom}</th>)}</tr></thead>
                    <tbody>{comparaison.indicateurs.map((ligne) => (
                      <tr key={`${ligne.source}-${ligne.indicateur}`}>
                        <th>{LIBELLES_COMPARAISON[ligne.indicateur] ?? ligne.indicateur}</th>
                        {ligne.valeurs.map((valeur, i) => (
                          <td key={comparaison.scenarios[i].id} className={ligne.meilleur?.includes(comparaison.scenarios[i].id) ? 'plan-meilleur' : ''}>
                            {valeurIndicateur(ligne.indicateur, valeur)}{i > 0 && ligne.ecart_a_la_reference[i] != null && <small> ({ligne.ecart_a_la_reference[i] > 0 ? '+' : ''}{valeurIndicateur(ligne.indicateur, ligne.ecart_a_la_reference[i])})</small>}
                          </td>
                        ))}
                      </tr>
                    ))}</tbody>
                  </table>
                </div>
              </div>
            )}
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

        <section className="carte plan-bloc">
          <div>
            <div className="plan-section-entete"><h2 className="carte-titre">Affecter les tournées</h2><button className="btn-contour plan-flotte-bouton" onClick={() => setFlotteOuverte(true)}>Voir la flotte en grand</button></div>
            {plan.tournees.length === 0 && <p className="carte-texte">Aucune tournée à affecter.</p>}
            {plan.tournees.map((tournee) => {
              const candidats = tournee.type === 'collecte' ? chauffeurs : brigades
              const affecte = utilisateurs.find((u) => u.id === tournee.affectee_a)
              return (
                <div className="plan-affectation" key={tournee.id}>
                  <strong>{tournee.type === 'collecte' ? `${tournee.camion_id} · jour ${tournee.jour ?? 1}` : `Laabal · brigade ${tournee.brigade ?? 1}`}</strong>
                  <small>{affecte ? `Affectée à ${affecte.nom}` : 'Non affectée'}</small>
                  <div>
                    <select value={affectations[tournee.id] ?? ''} onChange={(e) => setAffectations((courant) => ({ ...courant, [tournee.id]: e.target.value }))}>
                      <option value="">{candidats.length ? 'Choisir un agent' : `Aucun ${tournee.type === 'collecte' ? 'chauffeur' : 'agent Laabal'} actif`}</option>
                      {candidats.map((u) => <option key={u.id} value={u.id}>{u.nom}</option>)}
                    </select>
                    <button className="btn-contour" disabled={affectationEnCours === tournee.id || !affectations[tournee.id]} onClick={() => affecter(tournee, affectations[tournee.id])}>
                      {affectationEnCours === tournee.id ? 'Affectation…' : 'Affecter'}
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        </section>
      </aside>

      <div className={`plan-carte ${flotteOuverte ? 'plan-carte-flotte' : ''}`}>
        {flotteOuverte ? <FlotteSimulation tournees={plan.tournees} onRetourCarte={() => setFlotteOuverte(false)} /> : <MapContainer center={CENTRE} zoom={13} style={{ height: '100%', width: '100%' }}>
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
        </MapContainer>}
      </div>
    </main>
  )
}