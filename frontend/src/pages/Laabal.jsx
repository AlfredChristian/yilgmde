import { useEffect, useState } from 'react'
import { MapContainer, TileLayer, CircleMarker, Tooltip, useMap } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import { useAuth } from '../auth/AuthContext'
import { getDepotoirsLaabal, changerStatutDepotoir } from '../api/client'
import Icone from '../components/Icone'
import './Roles.css'

const CENTRE = [12.3714, -1.5197]

const STATUTS = {
  actif: { texte: 'À traiter', couleur: '#b8322a' },
  intervention_planifiee: { texte: 'Intervention en cours', couleur: '#e9b824' },
  eradique: { texte: 'Éradiqué', couleur: '#0e5a3a' },
  sous_surveillance: { texte: 'Sous surveillance', couleur: '#5a6a61' },
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

  useEffect(() => {
    getDepotoirsLaabal().then(setListe).catch((e) => setErreur(e.message))
  }, [])

  async function changer(d, statut) {
    setEnCours(d.id)
    try {
      await changerStatutDepotoir(d.id, statut)
      setListe((l) => l.map((x) => (x.id === d.id ? { ...x, statut } : x)))
    } catch (e) {
      setErreur(e.message)
    } finally {
      setEnCours(null)
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
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
              url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            <Cadrage points={liste} choisi={choisi} />
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
                    <button className="btn-contour" disabled={enCours === d.id} onClick={() => changer(d, 'intervention_planifiee')}>
                      Commencer l’intervention
                    </button>
                  )}
                  {(d.statut === 'actif' || d.statut === 'intervention_planifiee') && (
                    <button className="btn-contour plein" disabled={enCours === d.id} onClick={() => changer(d, 'eradique')}>
                      <Icone nom="check" taille={18} /> Marquer éradiqué
                    </button>
                  )}
                  {d.statut === 'eradique' && (
                    <button className="btn-contour" disabled={enCours === d.id} onClick={() => changer(d, 'sous_surveillance')}>
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
