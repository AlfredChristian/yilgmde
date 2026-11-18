import { useEffect, useRef, useState } from 'react'
import { MapContainer, CircleMarker, Polyline, Polygon, Popup, Tooltip, useMap, useMapEvents } from 'react-leaflet'
import FondDeCarte from '../components/FondDeCarte'
import 'leaflet/dist/leaflet.css'
import { activerScenario, affecterTournee, comparerScenarios, creerScenario, getArrondissements, getParametres, getPlan, getScenarios, getSynthese, getUtilisateurs, majParametres, simulerScenario } from '../api/client'
import './Plan.css'
import SuiviFlotte from '../components/SuiviFlotte'
import SuiviEradication from '../components/SuiviEradication'
import Affectations from '../components/Affectations'
import LectureMarkdown from '../components/LectureMarkdown'

const CENTRE = [12.3714, -1.5197]
const COULEURS = ['#1b6b4a', '#f4b942', '#7b2cbf', '#0077b6', '#d62828']

// Champs traduits en parametres de scenario dans api/client.js (versApi).
const PARAMETRES = [
  { cle: 'arrondissement', libelle: 'Périmètre', type: 'arrondissement' },
  { cle: 'camions_en_panne', libelle: 'Camions en panne', type: 'nombre', min: 0 },
  { cle: 'saison_pluies', libelle: 'Saison des pluies', type: 'bool' },
  { cle: 'budget_xof', libelle: 'Budget mensuel (XOF)', type: 'nombre', min: 0, pas: 1000000 },
  { cle: 'evolution_population_pct', libelle: 'Évolution de la population (%)', type: 'nombre', min: -50, max: 100 },
  { cle: 'abonnement_pct', libelle: 'Ménages abonnés aux pré-collecteurs (%)', type: 'nombre', min: 0, max: 100 },
  { cle: 'frequence', libelle: 'Passages de collecte par semaine', type: 'nombre', min: 1, max: 7 },
  { cle: 'apport_volontaire_pct', libelle: 'Apport volontaire aux points (%)', type: 'nombre', min: 0, max: 100 },
]
const TOURNEES_AFFICHEES = 30
const fmt = (n) => Math.round(n).toLocaleString('fr-FR')
const fmtNombre = (n) => (n == null ? '-' : typeof n === 'number' ? n.toLocaleString('fr-FR', { maximumFractionDigits: 1 }) : n)
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

// Le meme nom d'indicateur peut venir du plan et de la simulation (cout_total_xof).
const LIBELLES_SIMULATION = { cout_total_xof: 'Coût simulé sur la période (XOF)' }

// Valeur affichée d'un indicateur : les kg en tonnes, les parts avec « % » ;
// un écart de parts se lit en points (« +4 pts »), pas en pourcentage.
function valeurIndicateur(cle, n, ecart = false) {
  if (n == null) return '-'
  if (cle.endsWith('_kg')) return fmt(n / 1000)
  return fmtNombre(n) + (cle.endsWith('_pct') ? (ecart ? ' pts' : ' %') : '')
}

// Champ numérique saisi librement : la valeur n'est appliquée (et le plan recalculé) qu'avec
// Entrée ou en quittant le champ. Les espaces sont acceptés (« 180 000 000 »).
function ChampNombre({ valeur, min, max, onValider }) {
  const [texte, setTexte] = useState(null)        // null : on affiche la valeur du plan
  const affiche = texte ?? fmt(valeur)
  const invalide = texte != null && !/^-?\d+$/.test(texte.replace(/[\s\u202f\u00a0]/g, ''))

  function valider() {
    if (texte == null) return
    const n = Number(texte.replace(/[\s\u202f\u00a0]/g, ''))
    setTexte(null)
    if (!Number.isFinite(n) || texte.trim() === '') return
    const borne = Math.min(max ?? n, Math.max(min, Math.round(n)))
    if (borne !== valeur) onValider(borne)
  }

  return (
    <input
      type="text"
      inputMode="numeric"
      className={invalide ? 'champ-invalide' : ''}
      value={affiche}
      onFocus={(e) => e.target.select()}
      onChange={(e) => setTexte(e.target.value)}
      onBlur={valider}
      onKeyDown={(e) => { if (e.key === 'Enter') e.currentTarget.blur(); if (e.key === 'Escape') { setTexte(null); e.currentTarget.blur() } }}
      aria-invalid={invalide}
    />
  )
}

// Tracé d'un nouveau quartier : chaque clic ajoute un coin.
function TraceQuartier({ actif, onPoint }) {
  const map = useMapEvents({ click: (e) => actif && onPoint([e.latlng.lat, e.latlng.lng]) })
  useEffect(() => {
    if (actif) map.doubleClickZoom.disable()
    else map.doubleClickZoom.enable()
    map.getContainer().style.cursor = actif ? 'crosshair' : ''
  }, [actif, map])
  return null
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
      <small>de {fmtNombre(min)} % à {fmtNombre(max)} %</small>
    </figure>
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
  const [flotteOuverte, setFlotteOuverte] = useState(false)
  const [eradicationOuverte, setEradicationOuverte] = useState(false)
  const [vue, setVue] = useState('carte')     // panneau de droite : 'carte', 'affectations' ou 'synthese'
  const [trace, setTrace] = useState(null)     // coins du quartier en cours de tracé, null hors tracé
  const [nouveauQuartier, setNouveauQuartier] = useState({ nom: '', population: '' })
  const [synthese, setSynthese] = useState(null)
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

  // Seule la réponse du dernier changement est affichée (un calcul plus ancien peut finir après).
  const dernierAppel = useRef(0)
  function changer(cle, valeur) {
    setParams((p) => ({ ...p, [cle]: valeur }))
    clearTimeout(delai.current)
    delai.current = setTimeout(async () => {
      const appel = ++dernierAppel.current
      setCalcul(true)
      setErreur(null)
      const debut = performance.now()
      try {
        const nouveau = await majParametres({ [cle]: valeur })
        if (appel !== dernierAppel.current) return
        setPlan(nouveau)
        setDernierMs(Math.round(performance.now() - debut))
      } catch (e) {
        if (appel === dernierAppel.current) setErreur(`Recalcul impossible : ${e.message}`)
      } finally {
        if (appel === dernierAppel.current) setCalcul(false)
      }
    }, 300)
  }

  // Nouveau quartier dessiné sur la carte (épreuve en direct) : ajout puis plan recalculé.
  async function modifierQuartiers(cle, valeur) {
    setCalcul(true)
    setErreur(null)
    try {
      setPlan(await majParametres({ [cle]: valeur }))
      setParams(await getParametres())
      return true
    } catch (e) {
      setErreur(`Quartier non pris en compte : ${e.message}`)
      return false
    } finally {
      setCalcul(false)
    }
  }

  async function ajouterQuartier() {
    const population = Number(String(nouveauQuartier.population).replace(/\s/g, ''))
    const anneau = [...trace, trace[0]].map(([lat, lon]) => [Number(lon.toFixed(6)), Number(lat.toFixed(6))])
    const feature = {
      type: 'Feature',
      properties: { nom: nouveauQuartier.nom.trim() || 'Nouveau quartier', population },
      geometry: { type: 'Polygon', coordinates: [anneau] },
    }
    if (await modifierQuartiers('ajouter_quartier', feature)) {
      setTrace(null)
      setNouveauQuartier({ nom: '', population: '' })
    }
  }

  async function ouvrirSynthese() {
    setVue('synthese')
    setSynthese(null)
    try {
      setSynthese(await getSynthese())
    } catch (e) {
      setSynthese(`Le plan de gestion n’a pas pu être chargé : ${e.message}`)
    }
  }

  function telechargerSynthese() {
    const lien = document.createElement('a')
    lien.href = URL.createObjectURL(new Blob([synthese], { type: 'text/markdown;charset=utf-8' }))
    lien.download = 'plan-de-gestion.md'
    lien.click()
    URL.revokeObjectURL(lien.href)
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

  // Utilisée par l'écran des affectations : lève l'erreur pour qu'il arrête la série.
  async function affecterSimple(tournee, utilisateurId) {
    setErreur(null)
    try {
      const resultat = await affecterTournee(tournee.id, Number(utilisateurId))
      setPlan((courant) => ({ ...courant, tournees: courant.tournees.map((t) => t.id === tournee.id ? { ...t, affectee_a: resultat.affectee_a } : t) }))
    } catch (e) {
      setErreur(`Affectation impossible : ${e.message}`)
      throw e
    }
  }

  return (
    <main className="plan-page">
      <aside className="plan-panneau">
        <h1>Plan de gestion</h1>

        <div className="plan-etat">
          {calcul ? <span className="statut statut-attente">Recalcul…</span>
            : <span className="statut statut-ok">À jour{dernierMs != null && `, calculé en ${dernierMs} ms`}</span>}
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
                  <ChampNombre
                    valeur={params[d.cle] ?? 0}
                    min={d.min ?? 0}
                    max={d.cle === 'camions_en_panne' ? params.nb_camions : d.max}
                    onValider={(v) => changer(d.cle, v)}
                  />
                )}
              </label>
            ))}
          </div>
        </section>

        {params.arrondissement > 0 && (
          <p className="plan-limite">
            <strong>Hypothèse :</strong> ce plan d’arrondissement peut mobiliser toute la flotte communale.
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
                <p>Dépotoirs actifs : <strong>de {resume.depotoirs_actifs_debut} à {resume.depotoirs_actifs_fin}</strong></p>
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
                <p className="carte-texte">Sur {comparaison.jours} jours avec la graine {comparaison.graine}. La première colonne est la référence.</p>
                <div className="plan-tableau-wrap">
                  <table>
                    <thead><tr><th>Indicateur</th>{comparaison.scenarios.map((s) => <th key={s.id}>{s.nom}</th>)}</tr></thead>
                    <tbody>{comparaison.indicateurs.map((ligne) => (
                      <tr key={`${ligne.source}-${ligne.indicateur}`}>
                        <th>{(ligne.source === 'simulation' && LIBELLES_SIMULATION[ligne.indicateur]) || LIBELLES_COMPARAISON[ligne.indicateur] || ligne.indicateur}</th>
                        {ligne.valeurs.map((valeur, i) => (
                          <td key={comparaison.scenarios[i].id} className={ligne.meilleur?.includes(comparaison.scenarios[i].id) ? 'plan-meilleur' : ''}>
                            {valeurIndicateur(ligne.indicateur, valeur)}{i > 0 && ligne.ecart_a_la_reference[i] != null && <small> ({ligne.ecart_a_la_reference[i] > 0 ? '+' : ''}{valeurIndicateur(ligne.indicateur, ligne.ecart_a_la_reference[i], true)})</small>}
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
            <p className="plan-chiffre">{ind.nb_points_regroupement} <small>points, {ind.camions_utilises.length} camions mobilisés</small></p>
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
                {t.type === 'intervention' ? `Laabal, brigade ${t.brigade}` : `${t.camion_id}${t.jour ? `, jour ${t.jour}` : ''}`}
                {', '}{t.distance_km} km, {Math.round(t.duree_min)} min
              </p>
            ))}
            {plan.tournees.length > TOURNEES_AFFICHEES && (
              <p className="carte-texte">… et {plan.tournees.length - TOURNEES_AFFICHEES} autres (voir la synthèse).</p>
            )}
          </div>
        </section>

        <section className="carte plan-bloc">
          <div>
            <h2 className="carte-titre">Nouveau quartier</h2>
            {trace === null ? (
              <>
                {params.quartiers?.length > 0 ? (
                  <ul className="plan-quartiers">
                    {params.quartiers.map((q, k) => (
                      <li key={k}>
                        <span><strong>{q.nom}</strong>{q.population != null && <small>{fmt(q.population)} habitants</small>}</span>
                        <button className="btn-contour danger" disabled={calcul} onClick={() => modifierQuartiers('retirer_quartier', k)}>Retirer</button>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="carte-texte">Ajoutez un quartier qui n’existe pas encore : le plan lui attribue des points de regroupement et des tournées.</p>
                )}
                <button className="btn-contour plein" disabled={calcul} onClick={() => { setVue('carte'); setFlotteOuverte(false); setTrace([]) }}>
                  Dessiner un quartier sur la carte
                </button>
              </>
            ) : (
              <div className="plan-trace">
                <p className="carte-texte">
                  Cliquez sur la carte pour placer les coins du quartier.
                  {trace.length < 3 ? ` Encore ${3 - trace.length} point${3 - trace.length > 1 ? 's' : ''} au minimum.` : ` ${trace.length} coins placés.`}
                </p>
                <label className="plan-select">
                  <span>Nom du quartier</span>
                  <input type="text" value={nouveauQuartier.nom} placeholder="Ex. : extension de Yagma" maxLength={80}
                    onChange={(e) => setNouveauQuartier((q) => ({ ...q, nom: e.target.value }))} />
                </label>
                <label className="plan-select">
                  <span>Population estimée</span>
                  <input type="text" inputMode="numeric" value={nouveauQuartier.population} placeholder="Ex. : 12 000"
                    onChange={(e) => setNouveauQuartier((q) => ({ ...q, population: e.target.value }))} />
                </label>
                <div className="plan-boutons">
                  <button className="btn-contour plein" disabled={calcul || trace.length < 3 || !(Number(String(nouveauQuartier.population).replace(/\s/g, '')) > 0)} onClick={ajouterQuartier}>
                    Ajouter le quartier
                  </button>
                  <button className="btn-contour" disabled={!trace.length} onClick={() => setTrace((t) => t.slice(0, -1))}>Retirer le dernier coin</button>
                  <button className="btn-contour" onClick={() => setTrace(null)}>Annuler</button>
                </div>
              </div>
            )}
          </div>
        </section>

        <section className="carte plan-bloc">
          <div>
            <h2 className="carte-titre">Plan de gestion</h2>
            <p className="carte-texte">Le document de synthèse du scénario de travail : points, tournées, coûts et recommandations.</p>
            <button className={`btn-contour${vue === 'synthese' ? ' plein' : ''}`} onClick={() => (vue === 'synthese' ? setVue('carte') : ouvrirSynthese())}>
              {vue === 'synthese' ? 'Revenir à la carte' : 'Lire le plan de gestion'}
            </button>
          </div>
        </section>

        <section className="carte plan-bloc">
          <div>
            <h2 className="carte-titre">Équipes et flotte</h2>
            <p className="carte-texte">
              {plan.tournees.filter((t) => t.affectee_a).length} tournées affectées sur {plan.tournees.length}.
            </p>
            <div className="plan-boutons">
              <button className={`btn-contour${vue === 'affectations' ? ' plein' : ''}`} onClick={() => setVue(vue === 'affectations' ? 'carte' : 'affectations')}>
                {vue === 'affectations' ? 'Revenir à la carte' : 'Affecter les tournées'}
              </button>
              <button className="btn-contour" onClick={() => setFlotteOuverte(true)}>Suivi de la flotte</button>
              <button className="btn-contour" onClick={() => setEradicationOuverte(true)}>Suivi de l’éradication</button>
            </div>
          </div>
        </section>
      </aside>

      <div className={`plan-carte ${flotteOuverte ? 'plan-carte-flotte' : ''}`}>
        {eradicationOuverte && <SuiviEradication onRetour={() => setEradicationOuverte(false)} />}
        {flotteOuverte ? <SuiviFlotte onRetourCarte={() => setFlotteOuverte(false)} /> : vue === 'affectations' ? (
          <Affectations tournees={plan.tournees} utilisateurs={utilisateurs} onAffecter={affecterSimple} onRetour={() => setVue('carte')} />
        ) : vue === 'synthese' ? (
          <section className="synthese">
            <header className="affectations-tete synthese-tete">
              <div className="plan-boutons">
                {synthese && <button className="btn-contour" onClick={telechargerSynthese}>Télécharger</button>}
                <button className="btn-contour" onClick={() => setVue('carte')}>Revenir à la carte</button>
              </div>
            </header>
            {synthese ? <LectureMarkdown texte={synthese} /> : <p className="carte-texte"><span className="role-spinner" /> Chargement du plan de gestion</p>}
          </section>
        ) : <MapContainer center={CENTRE} zoom={13} style={{ height: '100%', width: '100%' }}>
          <FondDeCarte />
          {plan.points_regroupement.map((p) => (
            <CircleMarker key={`p${p.id}`} center={[p.latitude, p.longitude]} radius={plan.points_regroupement.length > 300 ? 4 : 8}
              pathOptions={{ color: '#124a34', fillColor: '#f4b942', fillOpacity: 0.95 }}>
              <Popup><strong>Point de regroupement n°{p.id}</strong><br />{p.explication}</Popup>
            </CircleMarker>
          ))}
          {plan.tournees.map((t, i) => (
            <Polyline key={`t${t.id}`} positions={t.trace ? t.trace.flat() : t.arrets.map((a) => [a.latitude, a.longitude])}
              pathOptions={{ color: COULEURS[i % COULEURS.length], weight: 2 }} />
          ))}
          <Recadrer points={plan.points_regroupement} />
          <TraceQuartier actif={trace !== null} onPoint={(p) => setTrace((t) => [...t, p])} />
          {(params.quartiers ?? []).map((q, k) => q.geometrie?.type === 'Polygon' && (
            <Polygon key={`q${k}`} positions={q.geometrie.coordinates[0].map(([lon, lat]) => [lat, lon])}
              pathOptions={{ color: '#b8322a', weight: 2, dashArray: '6 4', fillOpacity: 0.08 }}>
              <Tooltip sticky>{q.nom}{q.population != null ? `, ${fmt(q.population)} habitants` : ''}</Tooltip>
            </Polygon>
          ))}
          {trace?.length > 0 && (
            <>
              <Polygon positions={trace} pathOptions={{ color: '#b8322a', weight: 2, fillOpacity: 0.12 }} />
              {trace.map((p, k) => <CircleMarker key={`c${k}`} center={p} radius={5} pathOptions={{ color: '#fff', weight: 2, fillColor: '#b8322a', fillOpacity: 1 }} />)}
            </>
          )}
        </MapContainer>}
      </div>
    </main>
  )
}