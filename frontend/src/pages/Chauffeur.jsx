import { useEffect, useState } from 'react'
import { MapContainer, TileLayer, CircleMarker, Popup, Polyline, useMap } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import { useAuth } from '../auth/AuthContext'
import { getTournee, marquerArret } from '../api/client'
import Icone from '../components/Icone'
import './Roles.css'

const CENTRE = [12.3714, -1.5197]

function RecadrerTournee({ arrets }) {
  const map = useMap()

  useEffect(() => {
    if (arrets.length === 1) {
      map.setView([arrets[0].latitude, arrets[0].longitude], 15)
      return
    }
    if (arrets.length > 1) {
      map.fitBounds(arrets.map((a) => [a.latitude, a.longitude]), { padding: [28, 28] })
    }
  }, [arrets, map])

  return null
}

function RecalculerTailleCarte() {
  const map = useMap()

  useEffect(() => {
    const actualiser = () => map.invalidateSize({ animate: false })
    const premier = requestAnimationFrame(actualiser)
    const second = window.setTimeout(actualiser, 120)
    window.addEventListener('resize', actualiser)
    return () => {
      cancelAnimationFrame(premier)
      window.clearTimeout(second)
      window.removeEventListener('resize', actualiser)
    }
  }, [map])

  return null
}

export default function Chauffeur() {
  const { session } = useAuth()
  const [tournee, setTournee] = useState(null)
  const [erreur, setErreur] = useState(null)

  const [charge, setCharge] = useState(false)
  const [itineraireOuvert, setItineraireOuvert] = useState(false)

  useEffect(() => {
    getTournee().then(setTournee).catch((e) => setErreur(e.message)).finally(() => setCharge(true))
  }, [])

  function reessayer() {
    setCharge(false)
    setErreur(null)
    getTournee().then(setTournee).catch((e) => setErreur(e.message)).finally(() => setCharge(true))
  }

  // Un arret coche ne se decoche pas (le serveur garde la trace du passage).
  async function cocher(a) {
    try {
      await marquerArret(a)
      setTournee((t) => ({ ...t, arrets: t.arrets.map((x) => (x.ordre === a.ordre ? { ...x, statut: 'effectue' } : x)) }))
    } catch (e) {
      setErreur(e.message)
    }
  }

  if (!tournee) {
    if (!charge) return <main className="role-page"><div className="role-chargement"><span className="role-spinner" /> Chargement de votre espace</div></main>
    return (
      <main className="role-page">
        <section className="role-empty carte">
          <div className="role-empty-icon"><Icone nom="camion" taille={34} /></div>
          <span className="statut statut-attente">En attente d'affectation</span>
          <h1>{erreur ? 'Votre tournée est indisponible' : 'Aucune tournée pour le moment'}</h1>
          <p>{erreur ?? "Votre espace est prêt. L'administrateur doit encore vous affecter une tournée de collecte."}</p>
          <div className="role-empty-actions">
            <button className="btn-contour plein" onClick={reessayer}><Icone nom="suivi" taille={18} /> Actualiser</button>
            <a className="btn-contour" href="mailto:mairie@yilgmde.local">Contacter la mairie</a>
          </div>
        </section>
        <section className="role-info-grid">
          <article className="role-info-card"><strong>1</strong><div><b>Votre responsable affecte</b><span>La tournée apparaît automatiquement ici dès qu'elle est assignée.</span></div></article>
          <article className="role-info-card"><strong>2</strong><div><b>Vous recevez les arrêts</b><span>Les points de regroupement et l'itinéraire du jour sont ensuite visibles.</span></div></article>
        </section>
      </main>
    )
  }
  const faits = tournee.arrets.filter((a) => a.statut === 'effectue').length
  const positions = tournee.arrets.map((a) => [a.latitude, a.longitude])

  return (
    <main className="role-page">
      <h1>Ma tournée</h1>
      <p className="role-intro">
        {session.nom} · {tournee.camion_id} · {tournee.distance_km} km · {tournee.duree_min} min
        <br />
        {faits} / {tournee.arrets.length} arrêts effectués
      </p>
      {erreur && <p className="mod-erreur">{erreur}</p>}

      <section className="chauffeur-itineraire carte">
        <div className="chauffeur-itineraire-entete">
          <div>
            <span className="statut statut-ok">Itinéraire intégré</span>
            <h2 className="carte-titre">Votre parcours du jour</h2>
            <p className="carte-texte">Visualisez les arrêts directement dans Yilgmdé, sans ouvrir un autre site.</p>
          </div>
          <button className="btn-contour plein" onClick={() => setItineraireOuvert((ouvert) => !ouvert)}>
            <Icone nom="itineraire" taille={18} /> {itineraireOuvert ? 'Masquer la carte' : 'Voir l’itinéraire'}
          </button>
        </div>
        {itineraireOuvert && (
          <div className="chauffeur-carte-itineraire">
            <MapContainer center={positions[0] ?? CENTRE} zoom={13} style={{ height: '420px', width: '100%' }}>
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
              <RecalculerTailleCarte />
              <RecadrerTournee arrets={tournee.arrets} />
              {positions.length > 1 && <Polyline positions={tournee.trace?.length ? tournee.trace : positions} pathOptions={{ color: '#1b6b4a', weight: 5, opacity: 0.85 }} />}
              {tournee.arrets.map((a) => {
                const fait = a.statut === 'effectue'
                return (
                  <CircleMarker
                    key={a.ordre}
                    center={[a.latitude, a.longitude]}
                    radius={10}
                    pathOptions={{ color: fait ? '#1b6b4a' : '#a86b00', fillColor: fait ? '#2eb872' : '#f4b942', fillOpacity: 1, weight: 3 }}
                  >
                    <Popup>
                      <strong>Arrêt {a.ordre}</strong><br />
                      {a.nom}<br />
                      {fait ? 'Effectué' : 'À faire'}
                    </Popup>
                  </CircleMarker>
                )
              })}
            </MapContainer>
            <div className="chauffeur-carte-legende"><span><i className="chauffeur-legende-point chauffeur-legende-fait" /> Effectué</span><span><i className="chauffeur-legende-point chauffeur-legende-a-faire" /> À faire</span><span><i className="chauffeur-legende-ligne" /> Tracé de la tournée</span></div>
          </div>
        )}
      </section>

      <div className="role-liste">
        {tournee.arrets.map((a) => {
          const fait = a.statut === 'effectue'
          return (
            <article key={a.ordre} className="carte">
              <div className="carte-gauche">
                <span className={fait ? 'tuile' : 'tuile tuile-jaune'}>
                  <Icone nom={fait ? 'check' : 'camion'} taille={28} />
                </span>
                <span className={fait ? 'statut statut-ok' : 'statut statut-attente'}>
                  {fait ? 'Effectué' : 'À faire'}
                </span>
              </div>
              <div>
                <h3 className="carte-titre">{a.nom}</h3>
                <p className="carte-texte">{a.latitude.toFixed(5)}, {a.longitude.toFixed(5)}</p>
                <div className="carte-actions">
                  {!fait && (
                    <button className="btn-contour plein" onClick={() => cocher(a)}>
                      <Icone nom="check" taille={18} /> Marquer effectué
                    </button>
                  )}
                  <button className="btn-contour" onClick={() => setItineraireOuvert(true)}>
                    <Icone nom="itineraire" taille={18} /> Itinéraire
                  </button>
                </div>
              </div>
              <span className="badge">{a.ordre}</span>
            </article>
          )
        })}
      </div>
    </main>
  )
}