import { useEffect, useMemo, useState } from 'react'
import { createPortal } from 'react-dom'
import { MapContainer, TileLayer, CircleMarker, Polyline, Tooltip, useMap } from 'react-leaflet'
import { getSuiviFlotte } from '../api/client'

// Suivi de la flotte (D51), en 2D sur la vraie carte, avec deux informations bien séparées :
// - AVANCEMENT RÉEL : les arrêts cochés par le chauffeur ou la brigade (GET /admin/suivi,
//   relu toutes les 15 s). Vert = fait, avec l'heure.
// - HORAIRE PRÉVU : où chaque camion devrait être à l'heure choisie, d'après la durée calculée
//   par le moteur, répartie sur les trajets au prorata des distances. Ce n'est pas du GPS.

const DEBUT_JOURNEE_MIN = 7 * 60 // [H] départ du dépôt à 7 h
const RAFRAICHISSEMENT_MS = 15000
const VITESSE_LECTURE = 6 // minutes de plan par tic de 250 ms

function distanceKm([la1, lo1], [la2, lo2]) {
  const r = Math.PI / 180
  const a = Math.sin(((la2 - la1) * r) / 2) ** 2 + Math.cos(la1 * r) * Math.cos(la2 * r) * Math.sin(((lo2 - lo1) * r) / 2) ** 2
  return 12742 * Math.asin(Math.sqrt(a))
}

const heure = (min) => `${String(Math.floor(min / 60) % 24).padStart(2, '0')}:${String(Math.round(min % 60)).padStart(2, '0')}`
const heureReelle = (iso) => (iso ? new Date(iso).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' }) : null)

const longueurKm = (geom) => geom.slice(1).reduce((s, p, i) => s + distanceKm(geom[i], p), 0)

// Horaire prévu d'un camion pour un jour : ses rotations bout à bout depuis le dépôt.
// Chaque segment est un trajet (dépôt → arrêt 1, …, dernier arrêt → dépôt) : [début, fin] en minutes
// et sa géométrie, celle des voies quand le plan a été calculé sur le réseau routier (D52).
function horaire(rotations, depot) {
  const segments = []
  let t = DEBUT_JOURNEE_MIN
  for (const rot of rotations) {
    const sites = [depot, ...rot.arrets.map((a) => [a.latitude, a.longitude]), depot]
    const geoms = rot.trace?.length === sites.length - 1 ? rot.trace : sites.slice(1).map((p, i) => [sites[i], p])
    const longueurs = geoms.map(longueurKm)
    const total = longueurs.reduce((s, l) => s + l, 0) || 1
    longueurs.forEach((l, i) => {
      const duree = (rot.duree_min * l) / total
      segments.push({ debut: t, fin: t + duree, geom: geoms[i], longueur: l, arret: rot.arrets[i] ?? null })
      t += duree
    })
  }
  return { segments, fin: t }
}

// Point situé à la fraction f (0–1) du trajet, en suivant sa géométrie.
function pointSurTrajet(geom, longueur, f) {
  let reste = f * longueur
  for (let i = 1; i < geom.length; i++) {
    const l = distanceKm(geom[i - 1], geom[i])
    if (reste <= l && l > 0) {
      const g = reste / l
      return [geom[i - 1][0] + (geom[i][0] - geom[i - 1][0]) * g, geom[i - 1][1] + (geom[i][1] - geom[i - 1][1]) * g]
    }
    reste -= l
  }
  return geom.at(-1)
}

function positionPrevue(plan, minute) {
  if (minute <= DEBUT_JOURNEE_MIN || !plan.segments.length) return { pos: plan.segments[0]?.geom[0], etat: 'Au dépôt' }
  if (minute >= plan.fin) return { pos: plan.segments.at(-1).geom.at(-1), etat: 'Rentré au dépôt' }
  const s = plan.segments.find((x) => minute < x.fin)
  const f = s.fin > s.debut ? (minute - s.debut) / (s.fin - s.debut) : 1
  return {
    pos: pointSurTrajet(s.geom, s.longueur, f),
    etat: s.arret ? `Vers le point n°${s.arret.cible_id}` : 'Retour au dépôt',
  }
}

function Recadrer({ positions }) {
  const map = useMap()
  const cle = positions.length
  useEffect(() => {
    // la carte apparait dans un panneau qui vient de s'ouvrir : recalculer sa taille d'abord
    const id = setTimeout(() => {
      map.invalidateSize()
      if (positions.length) map.fitBounds(positions, { padding: [24, 24] })
    }, 50)
    return () => clearTimeout(id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map, cle])
  return null
}

// Rendu dans <body> : un parent du plan (transform / overflow) empecherait sinon le plein ecran.
export default function SuiviFlotte(props) {
  return createPortal(<VueSuivi {...props} />, document.body)
}

function VueSuivi({ onRetourCarte }) {
  const [suivi, setSuivi] = useState(null)
  const [erreur, setErreur] = useState(null)
  const [jour, setJour] = useState(1)
  const [minute, setMinute] = useState(DEBUT_JOURNEE_MIN + 90)
  const [lecture, setLecture] = useState(false)
  const [majLe, setMajLe] = useState(null)

  // Avancement réel, relu régulièrement : un arrêt coché sur le téléphone apparaît ici.
  useEffect(() => {
    let actif = true
    const charger = () =>
      getSuiviFlotte()
        .then((s) => { if (actif) { setSuivi(s); setErreur(null); setMajLe(new Date()) } })
        .catch((e) => actif && setErreur(e.message))
    charger()
    const id = setInterval(charger, RAFRAICHISSEMENT_MS)
    return () => { actif = false; clearInterval(id) }
  }, [])

  const depotLat = suivi?.depot.latitude
  const depotLon = suivi?.depot.longitude
  const depot = useMemo(() => (depotLat == null ? null : [depotLat, depotLon]), [depotLat, depotLon])
  const duJour = useMemo(
    () => (suivi ? suivi.tournees.filter((t) => t.type === 'collecte' && t.jour === jour && t.arrets.length) : []),
    [suivi, jour],
  )
  const camions = useMemo(() => {
    const parCamion = new Map()
    for (const t of duJour) parCamion.set(t.camion_id, [...(parCamion.get(t.camion_id) ?? []), t])
    return [...parCamion.entries()].map(([id, rotations]) => {
      rotations.sort((a, b) => a.rotation - b.rotation)
      const faits = rotations.reduce((s, r) => s + r.arrets_effectues, 0)
      const total = rotations.reduce((s, r) => s + r.arrets_total, 0)
      const derniere = rotations.map((r) => r.derniere_activite).filter(Boolean).sort().at(-1) ?? null
      return { id, rotations, faits, total, derniere, agent: rotations.find((r) => r.affectee_nom)?.affectee_nom ?? null, plan: horaire(rotations, depot) }
    }).sort((a, b) => b.faits / (b.total || 1) - a.faits / (a.total || 1) || (b.agent ? 1 : 0) - (a.agent ? 1 : 0))
  }, [duJour, depot])
  const finJournee = Math.max(DEBUT_JOURNEE_MIN + 60, ...camions.map((c) => c.plan.fin))

  useEffect(() => {
    if (!lecture) return undefined
    const id = setInterval(() => setMinute((m) => (m + VITESSE_LECTURE > finJournee ? DEBUT_JOURNEE_MIN : m + VITESSE_LECTURE)), 250)
    return () => clearInterval(id)
  }, [lecture, finJournee])

  if (!suivi) {
    return <section className="flotte-ecran flotte-suivi suivi-plein-ecran"><p className="carte-texte">{erreur ?? 'Chargement du suivi…'}</p></section>
  }

  const r = suivi.resume
  const tousLesArrets = duJour.flatMap((t) => t.arrets)
  const faitsDuJour = tousLesArrets.filter((a) => a.statut === 'effectue').length
  const positions = [depot, ...tousLesArrets.map((a) => [a.latitude, a.longitude])]

  return (
    <section className="flotte-ecran flotte-suivi suivi-plein-ecran" role="dialog" aria-label="Suivi de la flotte">
      <div className="flotte-entete">
        <div>
          <h2 className="carte-titre">Suivi de la flotte</h2>
          <p className="flotte-sous-titre">
            <span className="flotte-live" /> Avancement réel relu toutes les 15 s
            {majLe && ` · dernière mise à jour ${majLe.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}`}
          </p>
        </div>
        <button className="flotte-retour" onClick={onRetourCarte}>Retour au plan</button>
      </div>

      <div className="suivi-chiffres">
        <p><strong>{r.arrets_effectues} / {r.arrets_total}</strong> arrêts effectués (tout le passage)</p>
        <p><strong>{faitsDuJour} / {tousLesArrets.length}</strong> le jour {jour}</p>
        <p><strong>{r.tournees_affectees}</strong> tournées affectées · <strong>{r.tournees_terminees}</strong> terminées</p>
      </div>

      <div className="suivi-commandes">
        <div className="suivi-jours" role="group" aria-label="Jour du passage">
          {suivi.jours.map((j) => (
            <button key={j} className={j === jour ? 'actif' : ''} aria-pressed={j === jour} onClick={() => setJour(j)}>Jour {j}</button>
          ))}
        </div>
        <button className="btn-contour" onClick={() => setLecture((l) => !l)}>{lecture ? '❚❚ Pause' : '▶ Rejouer la journée'}</button>
        <label className="suivi-heure">
          Horaire prévu : <strong>{heure(minute)}</strong>
          <input type="range" min={DEBUT_JOURNEE_MIN} max={Math.ceil(finJournee)} step={1} value={Math.min(minute, finJournee)}
            onChange={(e) => { setLecture(false); setMinute(Number(e.target.value)) }} />
        </label>
      </div>

      <div className="suivi-corps">
        <div className="suivi-carte">
          <MapContainer center={depot} zoom={13} style={{ height: '100%', width: '100%' }}>
            <TileLayer attribution="&copy; OpenStreetMap" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
            <Recadrer positions={positions} />
            {camions.map((c) => c.rotations.map((t) => (
              <Polyline key={`l${t.id}`} positions={t.trace ? t.trace.flat() : [depot, ...t.arrets.map((a) => [a.latitude, a.longitude]), depot]}
                pathOptions={{ color: t.affectee_a ? '#1b6b4a' : '#8fa89a', weight: t.affectee_a ? 3 : 1.5, opacity: t.affectee_a ? 0.9 : 0.55 }} />
            )))}
            {tousLesArrets.map((a) => (
              <CircleMarker key={`a${a.id}`} center={[a.latitude, a.longitude]} radius={a.statut === 'effectue' ? 6 : 4}
                pathOptions={a.statut === 'effectue'
                  ? { color: '#ffffff', weight: 2, fillColor: '#1f9d55', fillOpacity: 1 }
                  : { color: '#6b7c72', weight: 1.5, fillColor: '#ffffff', fillOpacity: 1 }}>
                <Tooltip>
                  Point n°{a.cible_id} · {a.statut === 'effectue' ? `fait à ${heureReelle(a.effectue_le) ?? '?'}` : 'à faire'}
                </Tooltip>
              </CircleMarker>
            ))}
            {camions.map((c) => {
              const { pos, etat } = positionPrevue(c.plan, minute)
              return pos ? (
                <CircleMarker key={`c${c.id}`} center={pos} radius={8}
                  pathOptions={{ color: '#ffffff', weight: 2, fillColor: c.agent ? '#e0a100' : '#52514e', fillOpacity: 1 }}>
                  <Tooltip>{c.id}{c.agent ? ` · ${c.agent}` : ''} · {etat} (prévu à {heure(minute)})</Tooltip>
                </CircleMarker>
              ) : null
            })}
            <CircleMarker center={depot} radius={9} pathOptions={{ color: '#ffffff', weight: 2, fillColor: '#0b3d2a', fillOpacity: 1 }}>
              <Tooltip permanent direction="top">Dépôt</Tooltip>
            </CircleMarker>
          </MapContainer>
        </div>

        <ol className="suivi-liste" aria-label={`Camions du jour ${jour}`}>
          {camions.map((c) => {
            const pct = c.total ? Math.round((100 * c.faits) / c.total) : 0
            return (
              <li key={c.id}>
                <div className="suivi-ligne">
                  <strong>{c.id}</strong>
                  <span>{c.faits}/{c.total} arrêts</span>
                </div>
                <div className="suivi-barre" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100} aria-label={`${c.id} : ${pct} %`}>
                  <span style={{ width: `${pct}%` }} />
                </div>
                <small>
                  {c.agent ?? 'Non affecté'} · {c.rotations.length} rotation{c.rotations.length > 1 ? 's' : ''} · fin prévue {heure(c.plan.fin)}
                  {c.derniere && ` · dernier arrêt coché à ${heureReelle(c.derniere)}`}
                </small>
              </li>
            )
          })}
        </ol>
      </div>

      <div className="flotte-legende">
        <span><i className="flotte-dot" style={{ background: '#1f9d55' }} /> Arrêt fait (coché sur le terrain)</span>
        <span><i className="flotte-dot" style={{ background: '#fff', border: '1.5px solid #6b7c72' }} /> Arrêt à faire</span>
        <span><i className="flotte-dot" style={{ background: '#e0a100' }} /> Camion affecté, position prévue</span>
        <span><i className="flotte-dot" style={{ background: '#52514e' }} /> Camion non affecté, position prévue</span>
      </div>
      <p className="flotte-note">
        Les positions des camions sont celles de l'horaire prévu par le plan (départ du dépôt à 7 h), pas un GPS.
        L'avancement réel vient des arrêts cochés par les chauffeurs ; un traceur GPS pourra remplacer l'horaire prévu.
      </p>
    </section>
  )
}
