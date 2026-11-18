import { useEffect, useMemo, useState } from 'react'
import { createPortal } from 'react-dom'
import { MapContainer, CircleMarker, Polyline, Tooltip, useMap } from '../carte'
import FondDeCarte from './FondDeCarte'
import { getSuiviDepotoirs } from '../api/client'
import './SuiviEradication.css'

// Suivi de l'éradication (D60) : chaque dépotoir à la position donnée dans ses signalements,
// avec ses étapes datées (signalé, validé, intervention de la brigade Laabal, éradiqué,
// surveillance). Le curseur montre la situation à une date ; « Rejouer » fait défiler les jours.

const JOUR = 86400000
const RAFRAICHISSEMENT_MS = 30000
const TICK_MS = 220

const ETATS = {
  signale: { texte: 'Signalé, en attente de validation', court: 'Signalé', couleur: '#e58a7f', rayon: 6 },
  valide: { texte: 'Validé, à traiter', court: 'À traiter', couleur: '#b8322a', rayon: 7 },
  intervention: { texte: 'Intervention de la brigade en cours', court: 'En intervention', couleur: '#e9b824', rayon: 8 },
  eradique: { texte: 'Éradiqué', court: 'Éradiqué', couleur: '#0e5a3a', rayon: 7 },
  surveillance: { texte: 'Éradiqué, sous surveillance', court: 'Sous surveillance', couleur: '#4f7a66', rayon: 6 },
}
const ORDRE = ['signale', 'valide', 'intervention', 'eradique', 'surveillance']
const FILTRES = [
  { cle: 'tous', texte: 'Tous' },
  { cle: 'a_traiter', texte: 'À traiter', etats: ['signale', 'valide'] },
  { cle: 'intervention', texte: 'En intervention', etats: ['intervention'] },
  { cle: 'eradique', texte: 'Éradiqués', etats: ['eradique', 'surveillance'] },
]

const temps = (iso) => (iso ? new Date(iso).getTime() : null)
const date = (iso, avecHeure = false) => (iso ? new Date(iso).toLocaleDateString('fr-FR', avecHeure
  ? { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' } : { day: 'numeric', month: 'short', year: 'numeric' }) : null)

/** État d'un dépotoir à l'instant t (null s'il n'était pas encore signalé). */
function etatA(d, t) {
  let etat = null
  for (const e of ORDRE) if (d.etapes[e] && temps(d.etapes[e]) <= t) etat = e
  return etat
}

function Cadrage({ points, choisi }) {
  const map = useMap()
  const cle = points.length
  useEffect(() => {
    const id = setTimeout(() => {
      map.invalidateSize()
      if (points.length) map.fitBounds(points, { padding: [24, 24] })
    }, 50)
    return () => clearTimeout(id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map, cle])
  useEffect(() => {
    if (choisi) map.flyTo([choisi.latitude, choisi.longitude], Math.max(map.getZoom(), 16), { duration: 0.6 })
  }, [map, choisi])
  return null
}

export default function SuiviEradication(props) {
  return createPortal(<VueEradication {...props} />, document.body)
}

function VueEradication({ onRetour }) {
  const [suivi, setSuivi] = useState(null)
  const [erreur, setErreur] = useState(null)
  const [majLe, setMajLe] = useState(null)
  const [maintenant, setMaintenant] = useState(() => Date.now())
  const [jour, setJour] = useState(null)        // index du jour affiché (null = aujourd'hui)
  const [lecture, setLecture] = useState(false)
  const [filtre, setFiltre] = useState('tous')
  const [choisiId, setChoisiId] = useState(null)

  useEffect(() => {
    let actif = true
    const charger = () => getSuiviDepotoirs()
      .then((s) => { if (actif) { setSuivi(s); setErreur(null); setMajLe(new Date()); setMaintenant(Date.now()) } })
      .catch((e) => actif && setErreur(e.message))
    charger()
    const id = setInterval(charger, RAFRAICHISSEMENT_MS)
    return () => { actif = false; clearInterval(id) }
  }, [])

  // Jours de la chronologie : du premier signalement à aujourd'hui.
  const debut = suivi?.debut
  const premierJour = useMemo(() => {
    if (!debut) return null
    const d = new Date(debut)
    d.setHours(0, 0, 0, 0)
    return d.getTime()
  }, [debut])
  const nbJours = premierJour == null ? 1 : Math.max(1, Math.ceil((maintenant - premierJour) / JOUR))
  const jourAffiche = jour ?? nbJours - 1
  const instant = premierJour == null ? maintenant : Math.min(maintenant, premierJour + (jourAffiche + 1) * JOUR - 1)
  const aujourdhui = jourAffiche >= nbJours - 1

  useEffect(() => {
    if (!lecture) return undefined
    const id = setInterval(() => setJour((j) => {
      const suivant = (j ?? nbJours - 1) + 1
      if (suivant >= nbJours) { setLecture(false); return null }
      return suivant
    }), TICK_MS)
    return () => clearInterval(id)
  }, [lecture, nbJours])

  const visibles = useMemo(() => {
    if (!suivi) return []
    return suivi.depotoirs
      .map((d) => ({ ...d, etat: etatA(d, instant) }))
      .filter((d) => d.etat)
  }, [suivi, instant])
  const etatsFiltre = FILTRES.find((f) => f.cle === filtre).etats
  const liste = useMemo(() => {
    const recent = (d) => Math.max(...ORDRE.map((e) => (d.etapes[e] && temps(d.etapes[e]) <= instant ? temps(d.etapes[e]) : 0)))
    return visibles.filter((d) => !etatsFiltre || etatsFiltre.includes(d.etat)).sort((a, b) => recent(b) - recent(a))
  }, [visibles, etatsFiltre, instant])
  const choisi = visibles.find((d) => d.id === choisiId) ?? null

  if (!suivi) {
    return <section className="flotte-ecran flotte-suivi suivi-plein-ecran"><p className="carte-texte">{erreur ?? 'Chargement du suivi…'}</p></section>
  }

  const compte = (etats) => visibles.filter((d) => etats.includes(d.etat)).length
  const eradiquesCeJour = visibles.filter((d) => d.etapes.eradique && instant - temps(d.etapes.eradique) < JOUR)
  const r = suivi.resume
  const positions = suivi.depotoirs.map((d) => [d.latitude, d.longitude])

  return (
    <section className="flotte-ecran flotte-suivi suivi-plein-ecran eradication" role="dialog" aria-label="Suivi de l’éradication des dépotoirs">
      <div className="flotte-entete">
        <div>
          <h2 className="carte-titre">Suivi de l’éradication</h2>
          <p className="flotte-sous-titre">
            <span className="flotte-live" /> Dépotoirs à la position donnée dans les signalements, relus toutes les 30 s
            {majLe && `. Dernière mise à jour ${majLe.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}`}
          </p>
        </div>
        <button className="flotte-retour" onClick={onRetour}>Retour au plan</button>
      </div>

      <div className="suivi-chiffres">
        <p><strong>{compte(['signale', 'valide'])}</strong> à traiter</p>
        <p><strong>{compte(['intervention'])}</strong> en intervention</p>
        <p><strong>{compte(['eradique', 'surveillance'])}</strong> éradiqués, dont {compte(['surveillance'])} sous surveillance</p>
        {r.delai_median_jours != null && <p>Délai médian du signalement à l’éradication : <strong>{String(r.delai_median_jours).replace('.', ',')} j</strong></p>}
      </div>

      <div className="suivi-commandes">
        <div className="suivi-jours" role="group" aria-label="Filtrer les dépotoirs">
          {FILTRES.map((f) => (
            <button key={f.cle} className={f.cle === filtre ? 'actif' : ''} aria-pressed={f.cle === filtre} onClick={() => setFiltre(f.cle)}>{f.texte}</button>
          ))}
        </div>
        <button className="btn-contour" onClick={() => {
          if (!lecture && aujourdhui) setJour(0)
          setLecture((l) => !l)
        }}>{lecture ? 'Mettre en pause' : 'Rejouer depuis le début'}</button>
        <label className="suivi-heure">
          Situation au <strong>{aujourdhui ? 'aujourd’hui' : date(new Date(instant).toISOString())}</strong>
          <input type="range" min={0} max={nbJours - 1} step={1} value={jourAffiche}
            onChange={(e) => { setLecture(false); const v = Number(e.target.value); setJour(v >= nbJours - 1 ? null : v) }}
            aria-valuetext={date(new Date(instant).toISOString())} />
        </label>
      </div>

      <div className="suivi-corps">
        <div className="suivi-carte">
          <MapContainer center={positions[0] ?? [12.37, -1.52]} zoom={12} style={{ height: '100%', width: '100%' }}>
            <FondDeCarte />
            <Cadrage points={positions} choisi={choisi} />
            {eradiquesCeJour.map((d) => (
              <CircleMarker key={`h${d.id}`} center={[d.latitude, d.longitude]} radius={16} interactive={false}
                pathOptions={{ stroke: false, fillColor: ETATS.eradique.couleur, fillOpacity: 0.18 }} />
            ))}
            {visibles.map((d) => {
              const e = ETATS[d.etat]
              const actif = d.id === choisiId
              const estompe = etatsFiltre && !etatsFiltre.includes(d.etat)
              return (
                <CircleMarker key={d.id} center={[d.latitude, d.longitude]} radius={actif ? e.rayon + 4 : e.rayon}
                  eventHandlers={{ click: () => setChoisiId(d.id) }}
                  pathOptions={{ color: '#ffffff', weight: actif ? 3 : 1.5, fillColor: e.couleur, fillOpacity: estompe ? 0.25 : 1, opacity: estompe ? 0.4 : 1 }}>
                  <Tooltip>Dépotoir n°{d.id}{d.zone_nom ? `, ${d.zone_nom}` : ''} : {e.court.toLowerCase()}</Tooltip>
                </CircleMarker>
              )
            })}
            {choisi && choisi.signalements.filter((s) => temps(s.cree_le) <= instant).map((s) => (
              <Polyline key={`l${s.id}`} positions={[[s.latitude, s.longitude], [choisi.latitude, choisi.longitude]]}
                pathOptions={{ color: '#1d2b24', weight: 1, dashArray: '3 3', opacity: 0.6 }} />
            ))}
            {choisi && choisi.signalements.filter((s) => temps(s.cree_le) <= instant).map((s) => (
              <CircleMarker key={`s${s.id}`} center={[s.latitude, s.longitude]} radius={4}
                pathOptions={{ color: '#1d2b24', weight: 1.5, fillColor: '#ffffff', fillOpacity: 1 }}>
                <Tooltip>Signalement n°{s.id}, reçu le {date(s.cree_le, true)}</Tooltip>
              </CircleMarker>
            ))}
          </MapContainer>
        </div>

        <ol className="suivi-liste eradication-liste" aria-label="Dépotoirs, du plus récemment modifié au plus ancien">
          {liste.length === 0 && <li className="eradication-vide">Aucun dépotoir dans ce filtre à cette date.</li>}
          {liste.map((d) => (
            <li key={d.id} className={d.id === choisiId ? 'choisi' : ''}>
              <button className="eradication-ligne" onClick={() => setChoisiId(d.id === choisiId ? null : d.id)} aria-expanded={d.id === choisiId}>
                <span className="suivi-ligne">
                  <strong>Dépotoir n°{d.id}</strong>
                  <span className="eradication-etat" style={{ '--c': ETATS[d.etat].couleur }}>{ETATS[d.etat].court}</span>
                </span>
                <small>{[d.zone_nom, `volume ${d.volume_estime}`, `${d.nb_signalements} signalement${d.nb_signalements > 1 ? 's' : ''}`].filter(Boolean).join(', ')}</small>
              </button>
              <ol className="eradication-etapes">
                {['signale', 'valide', 'intervention', 'eradique'].map((e) => {
                  const fait = d.etapes[e] && temps(d.etapes[e]) <= instant
                  return (
                    <li key={e} className={fait ? 'fait' : ''}>
                      <span>{{ signale: 'Signalé', valide: 'Validé', intervention: 'Intervention', eradique: 'Éradiqué' }[e]}</span>
                      <time>{fait ? date(d.etapes[e], true) : 'à venir'}</time>
                    </li>
                  )
                })}
              </ol>
              {d.id === choisiId && (
                <p className="eradication-detail">
                  {d.brigade ? `Brigade : ${d.brigade}. ` : ''}
                  {d.delai_eradication_jours != null && temps(d.etapes.eradique) <= instant ? `Éradiqué ${String(d.delai_eradication_jours).replace('.', ',')} jours après le premier signalement. ` : ''}
                  {d.etapes.surveillance && temps(d.etapes.surveillance) <= instant ? `Sous surveillance depuis le ${date(d.etapes.surveillance)}. ` : ''}
                  {d.dates_estimees ? 'Certaines dates sont estimées (dépotoir importé sans historique).' : ''}
                </p>
              )}
            </li>
          ))}
        </ol>
      </div>

      <div className="flotte-legende">
        {ORDRE.map((e) => <span key={e}><i className="flotte-dot" style={{ background: ETATS[e].couleur }} /> {ETATS[e].texte}</span>)}
        <span><i className="eradication-halo" /> Éradiqué dans les dernières 24 h</span>
        <span><i className="flotte-dot" style={{ background: '#fff', border: '1.5px solid #1d2b24' }} /> Position d’un signalement (dépotoir choisi)</span>
      </div>
    </section>
  )
}
