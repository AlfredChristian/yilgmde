import { memo, useEffect, useMemo, useState } from 'react'
import { createPortal } from 'react-dom'
import { MapContainer, CircleMarker, Marker, Polygon, Tooltip, useMap } from '../carte'
import FondDeCarte from './FondDeCarte'
import { getSecteursQuartier, getSimulationQuartier } from '../api/client'
import { iconeCamion, svgCamion } from './iconeCamion'
import { COULEUR_MODE, iconePersonne, iconePoubelle, iconeTricycle, svgPersonne, svgPoubelle, svgTricycle } from './iconesQuartier'
import './SimulationQuartier.css'

// Simulation d'un quartier (D62) : la matinée d'un quartier, rejouée minute par minute.
// Maisons réelles (Open Buildings), points de regroupement du plan, rues réelles ; les gestes
// des ménages et les tournées des précollecteurs sont simulés avec les règles du simulateur.

const TICK_MS = 100
const VITESSES = [{ v: 1, texte: '×1' }, { v: 2, texte: '×2' }, { v: 4, texte: '×4' }]
const MIN_PAR_TICK = 0.25                    // à ×1 : 2,5 minutes de matinée par seconde
const camion = iconeCamion({ couleur: '#0e5a3a', largeur: 46 })
const camionGauche = iconeCamion({ couleur: '#0e5a3a', largeur: 46, versGauche: true })

const heure = (m) => `${String(Math.floor(m / 60)).padStart(2, '0')}h${String(Math.floor(m % 60)).padStart(2, '0')}`
const fmt = (n) => Math.round(n).toLocaleString('fr-FR')

function dist([a, b], [c, d]) {
  const r = Math.PI / 180
  const x = Math.sin(((c - a) * r) / 2) ** 2 + Math.cos(a * r) * Math.cos(c * r) * Math.sin(((d - b) * r) / 2) ** 2
  return 12742000 * Math.asin(Math.sqrt(x))
}

// Chaque segment reçoit ses longueurs cumulées une fois pour toutes.
function preparer(segments) {
  return segments.map((s) => {
    const c = [0]
    for (let i = 1; i < s.trace.length; i++) c.push(c[i - 1] + dist(s.trace[i - 1], s.trace[i]))
    return { ...s, cumul: c }
  })
}

/** Position à l'instant t sur une suite de segments : { pos, versGauche, segment } ou null. */
function position(segments, t) {
  const s = segments.find((x) => t >= x.t0 && t < x.t1)
  if (!s) return null
  if (s.trace.length === 1) return { pos: s.trace[0], versGauche: false, segment: s }
  const f = (t - s.t0) / (s.t1 - s.t0)
  const cible = f * s.cumul.at(-1)
  let i = s.cumul.findIndex((c) => c >= cible)
  if (i <= 0) i = 1
  const l = s.cumul[i] - s.cumul[i - 1]
  const g = l > 0 ? (cible - s.cumul[i - 1]) / l : 1
  const [a, b] = [s.trace[i - 1], s.trace[i]]
  return { pos: [a[0] + (b[0] - a[0]) * g, a[1] + (b[1] - a[1]) * g], versGauche: b[1] < a[1], segment: s }
}

function Cadrage({ cle, centre, rayon }) {
  const map = useMap()
  useEffect(() => {
    const id = setTimeout(() => {
      map.invalidateSize()
      const d = rayon / 111320
      map.fitBounds([[centre[0] - d, centre[1] - d * 1.02], [centre[0] + d, centre[1] + d * 1.02]], { padding: [10, 10] })
    }, 50)
    return () => clearTimeout(id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map, cle])
  return null
}

// Couches fixes : dessinées une fois, pas à chaque minute.
const Fond = memo(function Fond({ sim, onChoisirPoint }) {
  return (
    <>
      <Polygon positions={sim.secteur.geometrie.coordinates[0].map(([lo, la]) => [la, lo])} interactive={false}
        pathOptions={{ color: '#5a6a61', weight: 1.5, dashArray: '4 6', fill: false }} />
      <Polygon positions={sim.zone.geometrie.coordinates[0].map(([lo, la]) => [la, lo])} interactive={false}
        pathOptions={{ color: '#0e5a3a', weight: 2, fillColor: '#0e5a3a', fillOpacity: 0.04 }} />
      {sim.points_du_secteur.filter((p) => !sim.points.some((q) => q.id === p.id)).map((p) => (
        <CircleMarker key={`a${p.id}`} center={[p.latitude, p.longitude]} radius={5} eventHandlers={{ click: () => onChoisirPoint(p.id) }}
          pathOptions={{ color: '#5a6a61', weight: 1.5, fillColor: '#ffffff', fillOpacity: 0.9 }}>
          <Tooltip>Point n°{p.id} : cliquer pour simuler le quartier autour</Tooltip>
        </CircleMarker>
      ))}
      {sim.maisons.map((m) => (
        <CircleMarker key={`m${m.id}`} center={[m.latitude, m.longitude]} radius={3.2} interactive={false}
          pathOptions={{ stroke: false, fillColor: COULEUR_MODE[m.mode], fillOpacity: 0.55 }} />
      ))}
    </>
  )
})

export default function SimulationQuartier(props) {
  return createPortal(<Vue {...props} />, document.body)
}

function Vue({ onRetour }) {
  const [secteurs, setSecteurs] = useState(null)
  const [zoneId, setZoneId] = useState(null)
  const [pointId, setPointId] = useState(null)
  const [graine, setGraine] = useState(1)
  const [sim, setSim] = useState(null)
  const [erreur, setErreur] = useState(null)
  const [cleChargee, setCleChargee] = useState(null)
  const [t, setT] = useState(0)
  const [lecture, setLecture] = useState(false)
  const [vitesse, setVitesse] = useState(2)

  useEffect(() => {
    getSecteursQuartier()
      .then((s) => { setSecteurs(s); if (s.length) setZoneId(s[0].id); else setErreur('Aucun secteur avec des points de regroupement dans le plan courant.') })
      .catch((e) => setErreur(e.message))
  }, [])

  useEffect(() => {
    if (zoneId == null) return undefined
    let actif = true
    const cle = `${zoneId}-${pointId}-${graine}`
    getSimulationQuartier(zoneId, pointId, graine)
      .then((s) => { if (actif) { setSim(s); setErreur(null); setT(s.horaire.debut); setLecture(true) } })
      .catch((e) => actif && setErreur(e.message))
      .finally(() => actif && setCleChargee(cle))
    return () => { actif = false }
  }, [zoneId, pointId, graine])

  const chargement = zoneId != null && cleChargee !== `${zoneId}-${pointId}-${graine}`
  const changer = (f) => { setLecture(false); f() }

  const acteurs = useMemo(() => {
    if (!sim) return null
    return {
      tricycles: sim.tricycles.map((x) => ({ ...x, segments: preparer(x.segments) })),
      pietons: sim.pietons.map((x) => ({ ...x, segments: preparer(x.segments) })),
      camions: sim.camions.map((x) => ({ ...x, segments: preparer(x.segments) })),
      maisons: new Map(sim.maisons.map((m) => [m.id, m])),
    }
  }, [sim])

  useEffect(() => {
    if (!lecture || !sim) return undefined
    const id = setInterval(() => setT((x) => {
      const suivant = x + MIN_PAR_TICK * vitesse
      if (suivant >= sim.horaire.fin) { setLecture(false); return sim.horaire.fin }
      return suivant
    }), TICK_MS)
    return () => clearInterval(id)
  }, [lecture, vitesse, sim])

  const titre = (
    <div className="flotte-entete">
      <div>
        <h2 className="carte-titre">Simulation d’un quartier</h2>
        <p className="flotte-sous-titre">
          Maisons, rues et points de regroupement réels. Les gestes des ménages et les tournées des précollecteurs sont simulés avec les règles du simulateur.
        </p>
      </div>
      <button className="flotte-retour" onClick={onRetour}>Retour au plan</button>
    </div>
  )

  if (!sim) {
    return (
      <section className="flotte-ecran flotte-suivi suivi-plein-ecran quartier" role="dialog" aria-label="Simulation d’un quartier">
        {titre}
        <p className="carte-texte">{erreur ?? (secteurs ? 'Préparation de la matinée du quartier…' : 'Chargement des secteurs…')}</p>
      </section>
    )
  }

  // --- État à l'instant t -----------------------------------------------------------------
  const ramassees = new Set(sim.tricycles.flatMap((x) => x.arrets.filter((a) => a.t <= t).map((a) => a.maison_id)))
  const poubellesDehors = sim.maisons.filter((m) => m.sortie_min <= t && (m.mode === 'abonne' ? !ramassees.has(m.id) : t < m.depart_min))
  const sortent = sim.maisons.filter((m) => t >= m.sortie_min - 2 && t < m.sortie_min)          // l'habitant pose sa poubelle
  const chargePoint = new Map(sim.points.map((p) => [p.id, 0]))
  for (const x of sim.tricycles) if (x.vidage_min <= t && !(sim.points.find((p) => p.id === x.point_id)?.vide_min <= t)) chargePoint.set(x.point_id, chargePoint.get(x.point_id) + x.poubelles)
  for (const m of sim.maisons) {
    if (m.mode === 'apport' && m.depot_min <= t && !(sim.points.find((p) => p.id === m.point_id)?.vide_min <= t)) chargePoint.set(m.point_id, chargePoint.get(m.point_id) + 1)
  }
  const tas = new Map(sim.sauvages.map((s) => [s.id, 0]))
  for (const m of sim.maisons) if (m.mode === 'sauvage' && m.depot_min <= t) tas.set(m.sauvage_id, tas.get(m.sauvage_id) + 1)
  const kg = sim.echelle.kg_par_maison
  const auPoint = sim.maisons.filter((m) => (m.mode === 'apport' && m.depot_min <= t) || (m.mode === 'abonne' && sim.tricycles.some((x) => x.vidage_min <= t && x.arrets.some((a) => a.maison_id === m.id)))).length
  const sauvage = [...tas.values()].reduce((a, b) => a + b, 0)
  const r = sim.resume

  return (
    <section className="flotte-ecran flotte-suivi suivi-plein-ecran quartier" role="dialog" aria-label="Simulation d’un quartier">
      {titre}

      <div className="suivi-commandes">
        <label className="quartier-choix">
          Secteur
          <select value={zoneId ?? ''} onChange={(e) => changer(() => { setPointId(null); setZoneId(Number(e.target.value)) })}>
            {secteurs?.map((s) => <option key={s.id} value={s.id}>{s.nom ?? `Secteur ${s.id}`} ({fmt(s.population ?? 0)} hab.)</option>)}
          </select>
        </label>
        <button className="btn-contour" onClick={() => changer(() => setGraine((g) => g + 1))} disabled={chargement}>Autre matinée</button>
        <button className="btn-contour" onClick={() => { if (t >= sim.horaire.fin) setT(sim.horaire.debut); setLecture((l) => !l) }}>
          {lecture ? 'Mettre en pause' : t >= sim.horaire.fin ? 'Rejouer la matinée' : 'Lancer'}
        </button>
        <div className="suivi-jours" role="group" aria-label="Vitesse">
          {VITESSES.map((x) => <button key={x.v} className={x.v === vitesse ? 'actif' : ''} aria-pressed={x.v === vitesse} onClick={() => setVitesse(x.v)}>{x.texte}</button>)}
        </div>
        <label className="suivi-heure">
          <strong className="quartier-horloge">{heure(t)}</strong>
          <input type="range" min={sim.horaire.debut} max={sim.horaire.fin} step={1} value={Math.floor(t)}
            onChange={(e) => { setLecture(false); setT(Number(e.target.value)) }} aria-label="Heure de la matinée" />
        </label>
      </div>

      <div className="suivi-corps">
        <div className="suivi-carte">
          <MapContainer center={[sim.centre.latitude, sim.centre.longitude]} zoom={16} style={{ height: '100%', width: '100%' }}>
            <FondDeCarte />
            <Cadrage cle={`${sim.centre.point_id}-${sim.graine}`} centre={[sim.centre.latitude, sim.centre.longitude]} rayon={sim.centre.rayon_m} />
            <Fond sim={sim} onChoisirPoint={(id) => changer(() => setPointId(id))} />
            {sim.sauvages.map((s) => {
              const n = tas.get(s.id)
              return (n > 0 || s.existant) && (
                <CircleMarker key={`s${s.id}`} center={[s.latitude, s.longitude]} radius={6 + Math.min(16, Math.sqrt(n) * 2.4)}
                  pathOptions={{ color: '#ffffff', weight: 2, fillColor: '#b8322a', fillOpacity: 0.85 }}>
                  <Tooltip>{s.existant ? `Dépotoir n°${s.depotoir_id}` : 'Dépôt sauvage sur un terrain vague'} : {n} apport{n > 1 ? 's' : ''} ce matin, environ {fmt(n * kg)} kg</Tooltip>
                </CircleMarker>
              )
            })}
            {sim.points.map((p) => {
              const n = chargePoint.get(p.id)
              const vide = p.vide_min != null && p.vide_min <= t
              return (
                <CircleMarker key={`p${p.id}`} center={[p.latitude, p.longitude]} radius={9 + Math.min(10, Math.sqrt(n) * 1.6)}
                  pathOptions={{ color: '#124a34', weight: 2.5, fillColor: n ? '#e9b824' : '#ffffff', fillOpacity: 1 }}>
                  <Tooltip>Point de regroupement n°{p.id} : {vide ? 'vidé par le camion' : `${n} poubelle${n > 1 ? 's' : ''}, environ ${fmt(n * kg)} kg`}</Tooltip>
                </CircleMarker>
              )
            })}
            {poubellesDehors.map((m) => (
              <Marker key={`b${m.id}`} position={[m.latitude, m.longitude]} icon={iconePoubelle()} interactive={false} keyboard={false} />
            ))}
            {sortent.map((m) => (
              <Marker key={`h${m.id}`} position={[m.latitude, m.longitude]} icon={iconePersonne(m.mode, false)} interactive={false} keyboard={false} zIndexOffset={400} />
            ))}
            {acteurs.pietons.map((x) => {
              const p = position(x.segments, t)
              if (!p) return null
              const aller = p.segment === x.segments[0]
              return (
                <Marker key={`w${x.maison_id}`} position={p.pos} icon={iconePersonne(x.mode, aller)} keyboard={false} zIndexOffset={500}>
                  <Tooltip>{x.mode === 'apport' ? 'Habitant qui porte ses déchets au point' : 'Habitant qui jette ses déchets dans un dépôt sauvage'}</Tooltip>
                </Marker>
              )
            })}
            {acteurs.tricycles.map((x) => {
              const p = position(x.segments, t)
              const ramasse = x.arrets.filter((a) => a.t <= t).length
              const charge = x.vidage_min <= t ? 0 : ramasse / Math.max(1, x.poubelles)
              const pos = p?.pos ?? (() => { const pt = sim.points.find((q) => q.id === x.point_id); return [pt.latitude, pt.longitude] })()
              if (!p && t > x.vidage_min) return null
              return (
                <Marker key={`t${x.id}`} position={pos} icon={iconeTricycle(p?.versGauche ?? false, charge)} keyboard={false} zIndexOffset={800}>
                  <Tooltip>Précollecteur n°{x.id} : {ramasse} poubelle{ramasse > 1 ? 's' : ''} sur {x.poubelles}{x.vidage_min <= t ? ', vidé au point' : ''}</Tooltip>
                </Marker>
              )
            })}
            {acteurs.camions.map((x) => {
              const p = position(x.segments, t)
              return p && (
                <Marker key={`c${x.point_id}`} position={p.pos} icon={p.versGauche ? camionGauche : camion} keyboard={false} zIndexOffset={1000}>
                  <Tooltip>Camion de la mairie : vide le point n°{x.point_id}</Tooltip>
                </Marker>
              )
            })}
          </MapContainer>
        </div>

        <aside className="quartier-panneau" aria-label="Ce matin dans le quartier">
          <p className="quartier-lieu">
            {sim.secteur.nom ?? `Secteur ${sim.secteur.id}`}, quartier de {sim.centre.rayon_m} m autour du point n°{sim.centre.point_id}.
            {' '}{sim.echelle.maisons} maisons tirées parmi {fmt(sim.echelle.batiments_du_quartier)} bâtiments ; chacune compte pour {String(sim.echelle.menages_par_maison).replace('.', ',')} ménages.
          </p>
          <dl className="quartier-chiffres">
            <div><dt>Poubelles devant les maisons</dt><dd>{poubellesDehors.length}</dd></div>
            <div><dt>Arrivées aux points</dt><dd>{auPoint} <small>{fmt(auPoint * kg)} kg</small></dd></div>
            <div><dt>Jetées en dépôt sauvage</dt><dd className="rouge">{sauvage} <small>{fmt(sauvage * kg)} kg</small></dd></div>
          </dl>
          <h3>Sur toute la matinée</h3>
          <ul className="quartier-parts">
            <li><i style={{ background: COULEUR_MODE.abonne }} />{r.abonnes} maisons abonnées à un précollecteur ({r.tricycles} tournées de tricycle)</li>
            <li><i style={{ background: COULEUR_MODE.apport }} />{r.apport_volontaire} portent elles-mêmes leurs déchets au point</li>
            <li><i style={{ background: COULEUR_MODE.sauvage }} />{r.depot_sauvage} les jettent dans un dépôt sauvage, environ {fmt(r.kg_sauvages)} kg</li>
          </ul>
          <p className="quartier-regles">
            Règles du simulateur : {Math.round(sim.regles.taux_abonnement * 100)} % des ménages abonnés ; un non-abonné à moins de {sim.regles.distance_max_a_pied_m} m d’un point
            y porte ses déchets avec une probabilité de {Math.round(sim.regles.prob_apport * 100)} %, sinon il les jette. Cliquez un point gris pour simuler le quartier voisin.
          </p>
          {chargement && <p className="carte-texte"><span className="role-spinner" /> Nouvelle matinée…</p>}
          {erreur && <p className="mod-erreur" role="alert">{erreur}</p>}
        </aside>
      </div>

      <div className="flotte-legende">
        <span><i className="icone-camion-legende" dangerouslySetInnerHTML={{ __html: svgPersonne(COULEUR_MODE.abonne, { taille: 18 }) }} />Ménage abonné (sort sa poubelle)</span>
        <span><i className="icone-camion-legende" dangerouslySetInnerHTML={{ __html: svgPersonne(COULEUR_MODE.apport, { taille: 18, sac: true }) }} />Habitant qui porte ses déchets au point</span>
        <span><i className="icone-camion-legende" dangerouslySetInnerHTML={{ __html: svgPersonne(COULEUR_MODE.sauvage, { taille: 18, sac: true }) }} />Habitant qui jette en dépôt sauvage</span>
        <span><i className="icone-camion-legende" dangerouslySetInnerHTML={{ __html: svgPoubelle(12) }} />Poubelle devant la maison</span>
        <span><i className="icone-camion-legende" dangerouslySetInnerHTML={{ __html: svgTricycle('#0e5a3a', { largeur: 30 }) }} />Précollecteur en tricycle</span>
        <span><i className="icone-camion-legende" dangerouslySetInnerHTML={{ __html: svgCamion('#0e5a3a', { largeur: 28 }) }} />Camion de la mairie</span>
        <span><i className="flotte-dot" style={{ background: '#e9b824', border: '2px solid #124a34' }} /> Point de regroupement (taille selon le remplissage)</span>
        <span><i className="flotte-dot" style={{ background: '#b8322a' }} /> Dépôt sauvage</span>
      </div>
    </section>
  )
}
