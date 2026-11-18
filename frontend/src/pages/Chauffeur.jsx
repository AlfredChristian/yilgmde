import { useEffect, useState } from 'react'
import { MapContainer, CircleMarker, Marker, Tooltip, Polyline, useMap } from '../carte'
import FondDeCarte from '../components/FondDeCarte'
import 'leaflet/dist/leaflet.css'
import { useAuth } from '../auth/AuthContext'
import { getTournee, marquerArret } from '../api/client'
import Icone from '../components/Icone'
import { iconeCamion, svgCamion } from '../components/iconeCamion'
import './Roles.css'

const CENTRE = [12.3714, -1.5197]

// Recadre sur la tournée au chargement, puis sur l'arrêt choisi dans la liste.
function Cadrage({ arrets, choisi }) {
  const map = useMap()
  useEffect(() => {
    const id = setTimeout(() => {
      map.invalidateSize({ animate: false })
      if (arrets.length > 1) map.fitBounds(arrets.map((a) => [a.latitude, a.longitude]), { padding: [32, 32] })
      else if (arrets.length === 1) map.setView([arrets[0].latitude, arrets[0].longitude], 15)
    }, 60)
    return () => clearTimeout(id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map, arrets.length])
  useEffect(() => {
    if (choisi) map.flyTo([choisi.latitude, choisi.longitude], 16, { duration: 0.6 })
  }, [map, choisi])
  return null
}

export default function Chauffeur() {
  const { session } = useAuth()
  const [tournee, setTournee] = useState(null)
  const [erreur, setErreur] = useState(null)
  const [charge, setCharge] = useState(false)
  const [choisi, setChoisi] = useState(null)
  const [enCours, setEnCours] = useState(null)

  function charger() {
    setCharge(false)
    setErreur(null)
    getTournee().then(setTournee).catch((e) => setErreur(e.message)).finally(() => setCharge(true))
  }
  useEffect(() => {
    getTournee().then(setTournee).catch((e) => setErreur(e.message)).finally(() => setCharge(true))
  }, [])

  // Un arrêt validé ne se décoche pas : le serveur garde la trace du passage.
  async function valider(a) {
    setEnCours(a.ordre)
    try {
      await marquerArret(a)
      setTournee((t) => ({ ...t, arrets: t.arrets.map((x) => (x.ordre === a.ordre ? { ...x, statut: 'effectue' } : x)) }))
    } catch (e) {
      setErreur(e.message)
    } finally {
      setEnCours(null)
    }
  }

  if (!tournee) {
    return (
      <main className="role-page">
        {!charge ? (
          <div className="role-chargement"><span className="role-spinner" /> Chargement de votre tournée</div>
        ) : (
          <section className="role-vide">
            <span className="tuile"><Icone nom="camion" taille={28} /></span>
            <h1>{erreur ? 'Votre tournée ne peut pas être chargée' : 'Aucune tournée pour le moment'}</h1>
            <p>{erreur ?? 'La mairie ne vous a pas encore affecté de tournée. Elle apparaîtra ici dès qu’elle sera attribuée.'}</p>
            <button className="btn-contour plein" onClick={charger}>Actualiser</button>
          </section>
        )}
      </main>
    )
  }

  const faits = tournee.arrets.filter((a) => a.statut === 'effectue').length
  const total = tournee.arrets.length
  const positions = tournee.arrets.map((a) => [a.latitude, a.longitude])
  const prochain = tournee.arrets.find((a) => a.statut !== 'effectue')
  // Le camion est montré au dernier arrêt validé (au premier arrêt avant le départ), tourné
  // vers le prochain arrêt.
  const dernierFait = [...tournee.arrets].reverse().find((a) => a.statut === 'effectue')
  const posCamion = dernierFait ?? tournee.arrets[0]
  const iconeVehicule = posCamion && iconeCamion({
    couleur: '#0e5a3a',
    largeur: 52,
    versGauche: Boolean(prochain && prochain !== posCamion && prochain.longitude < posCamion.longitude),
  })

  return (
    <main className="terrain">
      <section className="terrain-gauche">
        <header className="terrain-tete">
          <h1>Ma tournée</h1>
          <ul className="puces">
            <li className="puce">{session.nom}</li>
            <li className="puce">{tournee.camion_id}</li>
            <li className="puce">{tournee.distance_km} km</li>
            <li className="puce">environ {Math.round(tournee.duree_min / 60 * 10) / 10} h</li>
          </ul>
          <div className="terrain-progression" aria-label={`${faits} arrêts effectués sur ${total}`}>
            <div className="terrain-barre"><span style={{ width: `${total ? (100 * faits) / total : 0}%` }} /></div>
            <strong>{faits} sur {total} arrêts effectués</strong>
          </div>
        </header>

        <h2 className="terrain-sous-titre">Votre parcours du jour</h2>
        <div className="terrain-carte">
          <MapContainer center={positions[0] ?? CENTRE} zoom={13} style={{ height: '100%', width: '100%' }}>
            <FondDeCarte />
            <Cadrage arrets={tournee.arrets} choisi={choisi} />
            {positions.length > 1 && (
              <Polyline positions={tournee.trace?.length ? tournee.trace : positions} pathOptions={{ color: '#0e5a3a', weight: 5, opacity: 0.85 }} />
            )}
            {tournee.arrets.map((a) => {
              const fait = a.statut === 'effectue'
              const actif = choisi?.ordre === a.ordre
              return (
                <CircleMarker key={a.ordre} center={[a.latitude, a.longitude]} radius={actif ? 13 : 10}
                  eventHandlers={{ click: () => setChoisi(a) }}
                  pathOptions={{ color: '#ffffff', weight: 3, fillColor: fait ? '#0e5a3a' : '#e9b824', fillOpacity: 1 }}>
                  <Tooltip direction="top" permanent={actif}>Arrêt {a.ordre} : {fait ? 'effectué' : 'à faire'}</Tooltip>
                </CircleMarker>
              )
            })}
            {posCamion && (
              <Marker position={[posCamion.latitude, posCamion.longitude]} icon={iconeVehicule} zIndexOffset={1000} keyboard={false}>
                <Tooltip direction="top">
                  {tournee.camion_id}, {dernierFait ? `arrêt ${dernierFait.ordre} validé` : 'avant le premier arrêt'}
                  {prochain ? `, prochain : arrêt ${prochain.ordre}` : ', tournée terminée'}
                </Tooltip>
              </Marker>
            )}
          </MapContainer>
        </div>
        <p className="terrain-legende">
          <span><i className="terrain-pastille a-faire" /> À faire</span>
          <span><i className="terrain-pastille fait" /> Effectué</span>
          <span><i className="terrain-trait" /> Trajet par les rues</span>
          <span><i className="icone-camion-legende" dangerouslySetInnerHTML={{ __html: svgCamion('#0e5a3a', { largeur: 28 }) }} />Votre camion, au dernier arrêt validé</span>
        </p>
      </section>

      <section className="terrain-droite" aria-labelledby="titre-arrets">
        <div className="terrain-droite-tete">
          <h2 id="titre-arrets">Points de regroupement</h2>
          {prochain && <button className="btn-contour" onClick={() => setChoisi(prochain)}>Aller au prochain arrêt</button>}
        </div>
        {erreur && <p className="mod-erreur" role="alert">{erreur}</p>}
        <ol className="arrets">
          {tournee.arrets.map((a) => {
            const fait = a.statut === 'effectue'
            return (
              <li key={a.ordre} className={`arret${fait ? ' arret-fait' : ''}${choisi?.ordre === a.ordre ? ' arret-choisi' : ''}`}>
                <button className="arret-zone" onClick={() => setChoisi(a)} aria-label={`Voir l’arrêt ${a.ordre} sur la carte`}>
                  <span className="arret-num">{fait ? <Icone nom="check" taille={18} /> : a.ordre}</span>
                  <span className="arret-texte">
                    <strong>{a.nom}</strong>
                    <span>Rotation {a.rotation ?? 1}{fait ? ', effectué' : ''}</span>
                  </span>
                </button>
                {fait ? (
                  <span className="arret-etat">Effectué</span>
                ) : (
                  <button className="btn-contour plein" disabled={enCours === a.ordre} onClick={() => valider(a)}>
                    <Icone nom="check" taille={18} /> Marquer effectué
                  </button>
                )}
              </li>
            )
          })}
        </ol>
      </section>
    </main>
  )
}
