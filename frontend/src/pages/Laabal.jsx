import { useEffect, useRef, useState } from 'react'
import { MapContainer, CircleMarker, Marker, Tooltip, useMap } from '../carte'
import FondDeCarte from '../components/FondDeCarte'
import 'leaflet/dist/leaflet.css'
import { useAuth } from '../auth/AuthContext'
import { getDepotoirsLaabal, changerStatutDepotoir, getItineraireLaabal } from '../api/client'
import CamionEnRoute from '../components/CamionEnRoute'
import { iconeCamion } from '../components/iconeCamion'
import Icone from '../components/Icone'
import './Roles.css'

const CENTRE = [12.3714, -1.5197]

const STATUTS = {
  actif: { texte: 'À traiter', couleur: '#b8322a' },
  intervention_planifiee: { texte: 'Intervention en cours', couleur: '#e9b824' },
  eradique: { texte: 'Éradiqué', couleur: '#0e5a3a' },
  sous_surveillance: { texte: 'Sous surveillance', couleur: '#5a6a61' },
}

// Durée d'un trajet animé : proportionnelle à la distance, entre 3 et 7 secondes.
const dureeTrajet = (m) => Math.min(7000, Math.max(3000, (m / 1000) * 400))
const TRAVAIL_MS = 1800
const camionGare = iconeCamion({ couleur: '#0e5a3a', largeur: 46, audessus: true })

// Pendant un trajet animé, la carte cadre le trajet entier.
function CadrageTrajet({ trace }) {
  const map = useMap()
  useEffect(() => {
    if (trace?.length) map.flyToBounds(trace, { padding: [40, 40], duration: 0.6, maxZoom: 16 })
  }, [map, trace])
  return null
}

function Cadrage({ points, choisi }) {
  const map = useMap()
  useEffect(() => {
    const id = setTimeout(() => {
      map.invalidateSize({ animate: false })
      if (points.length > 1) map.fitBounds(points.map((d) => [d.latitude, d.longitude]), { padding: [32, 32] })
      else if (points.length === 1) map.setView([points[0].latitude, points[0].longitude], 15)
    }, 60)
    return () => clearTimeout(id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map, points.length])
  useEffect(() => {
    if (choisi) map.flyTo([choisi.latitude, choisi.longitude], 16, { duration: 0.6 })
  }, [map, choisi])
  return null
}

export default function Laabal() {
  const { session } = useAuth()
  const [liste, setListe] = useState(null)
  const [erreur, setErreur] = useState(null)
  const [choisi, setChoisi] = useState(null)
  const [enCours, setEnCours] = useState(null)
  // Trajet animé de la brigade (D61) : { id, phase: 'aller' | 'travail' | 'retour', trace, duree }
  const [mission, setMission] = useState(null)
  const finTrajet = useRef(null)
  const depart = useRef(null)

  useEffect(() => {
    getDepotoirsLaabal().then(setListe).catch((e) => setErreur(e.message))
  }, [])

  const fixer = (id, statut) => setListe((l) => l.map((x) => (x.id === id ? { ...x, statut } : x)))
  const attendre = (ms) => new Promise((ok) => setTimeout(ok, ms))
  // Lance un trajet animé et attend l'arrivée du camion.
  const rouler = (id, phase, trace, distance) => new Promise((ok) => {
    finTrajet.current = ok
    setMission({ id, phase, trace, duree: dureeTrajet(distance) })
  })

  async function itineraire(d) {
    try {
      return await getItineraireLaabal(d.id)
    } catch {
      return null   // sans trajet, le statut change sans animation
    }
  }

  // Intervention : le camion part de la base, arrive sur place, puis le dépotoir passe en jaune.
  // Éradication : travail sur place, le camion repart, le dépotoir passe en vert.
  async function changer(d, statut) {
    setEnCours(d.id)
    setErreur(null)
    setChoisi(d)
    try {
      if (statut === 'sous_surveillance') {
        await changerStatutDepotoir(d.id, statut)
        fixer(d.id, statut)
        return
      }
      const it = await itineraire(d)
      const appel = changerStatutDepotoir(d.id, statut)
      if (it && d.statut === 'actif') await rouler(d.id, 'aller', it.aller, it.distance_aller_m)
      if (statut === 'intervention_planifiee') {
        await appel
        fixer(d.id, statut)
        setMission(null)
        return
      }
      setMission(it ? { id: d.id, phase: 'travail' } : null)
      if (it) await attendre(TRAVAIL_MS)
      await appel
      if (!it) { fixer(d.id, statut); return }
      depart.current = () => fixer(d.id, statut)       // vert dès que le camion a quitté le site
      await rouler(d.id, 'retour', it.retour, it.distance_retour_m)
      fixer(d.id, statut)
      setMission(null)
    } catch (e) {
      setErreur(e.message)
      setMission(null)
    } finally {
      setEnCours(null)
      depart.current = null
    }
  }

  if (!liste) {
    return (
      <main className="role-page">
        <div className="role-chargement"><span className="role-spinner" /> {erreur ?? 'Chargement des dépotoirs à traiter'}</div>
      </main>
    )
  }

  if (liste.length === 0) {
    return (
      <main className="role-page">
        <section className="role-vide">
          <span className="tuile"><Icone nom="bouclier" taille={28} /></span>
          <h1>Aucun dépotoir à traiter</h1>
          <p>Les nouveaux dépotoirs vérifiés par la mairie apparaîtront ici, par ordre de priorité.</p>
        </section>
      </main>
    )
  }

  const restants = liste.filter((d) => d.statut === 'actif' || d.statut === 'intervention_planifiee').length

  return (
    <main className="terrain">
      <section className="terrain-gauche">
        <header className="terrain-tete">
          <h1>Mes interventions</h1>
          <ul className="puces">
            <li className="puce">{session.nom}</li>
            <li className="puce">{restants} à traiter</li>
            <li className="puce">{liste.length - restants} traités</li>
          </ul>
        </header>
        <h2 className="terrain-sous-titre">Dépotoirs sur la carte</h2>
        <div className="terrain-carte">
          <MapContainer center={liste[0] ? [liste[0].latitude, liste[0].longitude] : CENTRE} zoom={13} style={{ height: '100%', width: '100%' }}>
            <FondDeCarte />
            <Cadrage points={liste} choisi={choisi} />
            {mission?.trace && <CadrageTrajet trace={mission.trace} />}
            {mission?.trace && (
              <CamionEnRoute key={`${mission.id}-${mission.phase}`} trace={mission.trace} duree={mission.duree}
                libelle={mission.phase === 'aller' ? `En route vers le dépotoir n°${mission.id}` : 'Retour à la base'}
                onProgres={(f) => { if (f > 0.04 && depart.current) { depart.current(); depart.current = null } }}
                onFin={() => finTrajet.current?.()} />
            )}
            {liste.filter((d) => (d.statut === 'intervention_planifiee' && mission?.id !== d.id) || (mission?.phase === 'travail' && mission.id === d.id)).map((d) => (
              <Marker key={`g${d.id}-${mission?.phase === 'travail' && mission.id === d.id ? 'travail' : 'gare'}`} position={[d.latitude, d.longitude]} icon={camionGare} zIndexOffset={1500} keyboard={false}>
                <Tooltip direction="top" permanent={mission?.phase === 'travail' && mission.id === d.id}>
                  {mission?.phase === 'travail' && mission.id === d.id ? 'Éradication en cours' : `Brigade sur place, dépotoir n°${d.id}`}
                </Tooltip>
              </Marker>
            ))}
            {liste.map((d, i) => {
              const s = STATUTS[d.statut] ?? STATUTS.actif
              const actif = choisi?.id === d.id
              return (
                <CircleMarker key={d.id} center={[d.latitude, d.longitude]} radius={actif ? 13 : 10}
                  eventHandlers={{ click: () => setChoisi(d) }}
                  pathOptions={{ color: '#ffffff', weight: 3, fillColor: s.couleur, fillOpacity: 1 }}>
                  <Tooltip direction="top" permanent={actif}>Priorité {i + 1} : dépotoir n°{d.id}, {s.texte.toLowerCase()}</Tooltip>
                </CircleMarker>
              )
            })}
          </MapContainer>
        </div>
        <p className="terrain-legende">
          {Object.entries(STATUTS).map(([cle, s]) => (
            <span key={cle}><i className="terrain-pastille" style={{ background: s.couleur }} /> {s.texte}</span>
          ))}
          <span><i className="icone-camion-legende" dangerouslySetInnerHTML={{ __html: camionGare.options.html }} />Camion de la brigade</span>
        </p>
      </section>

      <section className="terrain-droite" aria-labelledby="titre-depotoirs">
        <div className="terrain-droite-tete">
          <h2 id="titre-depotoirs">Par ordre de priorité</h2>
        </div>
        {erreur && <p className="mod-erreur" role="alert">{erreur}</p>}
        <ol className="arrets">
          {liste.map((d, i) => {
            const s = STATUTS[d.statut] ?? STATUTS.actif
            const termine = d.statut === 'eradique' || d.statut === 'sous_surveillance'
            return (
              <li key={d.id} className={`arret arret-colonne${termine ? ' arret-fait' : ''}${choisi?.id === d.id ? ' arret-choisi' : ''}`}>
                <button className="arret-zone" onClick={() => setChoisi(d)} aria-label={`Voir le dépotoir n°${d.id} sur la carte`}>
                  <span className="arret-num">{termine ? <Icone nom="check" taille={18} /> : i + 1}</span>
                  <span className="arret-texte">
                    <strong>Dépotoir n°{d.id}</strong>
                    <span>{d.raison ? `${d.raison.charAt(0).toUpperCase()}${d.raison.slice(1)}` : `Volume ${d.volume_estime}`}</span>
                    <span className="arret-statut" style={{ color: s.couleur }}>{s.texte}</span>
                  </span>
                </button>
                <div className="carte-actions">
                  {d.statut === 'actif' && (
                    <button className="btn-contour" disabled={enCours !== null} onClick={() => changer(d, 'intervention_planifiee')}>
                      Commencer l’intervention
                    </button>
                  )}
                  {(d.statut === 'actif' || d.statut === 'intervention_planifiee') && (
                    <button className="btn-contour plein" disabled={enCours !== null} onClick={() => changer(d, 'eradique')}>
                      <Icone nom="check" taille={18} /> Marquer éradiqué
                    </button>
                  )}
                  {d.statut === 'eradique' && (
                    <button className="btn-contour" disabled={enCours !== null} onClick={() => changer(d, 'sous_surveillance')}>
                      Placer sous surveillance
                    </button>
                  )}
                </div>
              </li>
            )
          })}
        </ol>
      </section>
    </main>
  )
}
