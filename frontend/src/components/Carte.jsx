import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  MapContainer,
  CircleMarker,
  Popup,
  LayersControl,
  LayerGroup,
  useMap,
} from '../carte'
import FondDeCarte from './FondDeCarte'
import 'leaflet/dist/leaflet.css'
import { getDepotoirs, getSignalements } from '../api/client'
import { COULEURS_DEPOTOIR, COULEURS_SIGNALEMENT } from '../config/couleurs'
import Legende from './Legende'

// Centre de Ouagadougou [latitude, longitude]. [H] sera deplace dans la config.
const CENTRE = [12.3714, -1.5197]
const ZOOM = 13

// Couleur d'un signalement selon le resultat attendu de la verification.
function couleurSignalement(attendu = '') {
  if (attendu.startsWith('rejete')) return COULEURS_SIGNALEMENT.rejete
  if (attendu.startsWith('alerte')) return COULEURS_SIGNALEMENT.alerte
  return COULEURS_SIGNALEMENT.enAttente
}

// Depuis le suivi d'un signalement (/carte?depotoir=12) : la carte se centre sur ce dépotoir.
function Viser({ lat, lon }) {
  const map = useMap()
  useEffect(() => {
    map.flyTo([lat, lon], 17, { duration: 0.8 })
  }, [map, lat, lon])
  return null
}

export default function Carte() {
  const [parametres] = useSearchParams()
  const cible = Number(parametres.get('depotoir')) || null
  const [depotoirs, setDepotoirs] = useState([])
  const [signalements, setSignalements] = useState([])
  const [erreur, setErreur] = useState(null)

  useEffect(() => {
    getDepotoirs()
      .then((g) => setDepotoirs(g.features))
      .catch((e) => setErreur(e.message))
    getSignalements()
      .then((g) => setSignalements(g.features))
      .catch((e) => setErreur(e.message))
  }, [])

  return (
    <div style={{ position: 'relative', height: '100%', width: '100%' }}>
      {erreur && (
        <div style={{ position: 'absolute', zIndex: 1000, background: 'white', padding: 8 }}>
          Erreur : {erreur}
        </div>
      )}
      <MapContainer center={CENTRE} zoom={ZOOM} style={{ height: '100%', width: '100%' }}>
        {(() => {
          const f = cible && depotoirs.find((x) => x.properties.id === cible)
          return f ? <Viser lat={f.geometry.coordinates[1]} lon={f.geometry.coordinates[0]} /> : null
        })()}
        <FondDeCarte>
          <LayersControl.Overlay checked name="Dépotoirs vérifiés">
            <LayerGroup>
              {depotoirs.map((f) => {
                const [lon, lat] = f.geometry.coordinates
                const p = f.properties
                return (
                  <CircleMarker
                    key={p.id}
                    center={[lat, lon]}
                    radius={10}
                    pathOptions={{
                      color: (p.legalite === 'officiel' ? COULEURS_DEPOTOIR.officiel : COULEURS_DEPOTOIR[p.statut]) ?? '#555',
                      fillOpacity: 0.7,
                    }}
                  >
                    <Popup ouvert={p.id === cible}>
                      <strong>{p.legalite === 'officiel' ? 'Centre de collecte' : 'Dépotoir'} n°{p.id}</strong>
                      <br />
                      Statut : {p.statut}
                      <br />
                      Volume : {p.volume_estime}
                      <br />
                      Signalements : {p.nb_signalements}
                    </Popup>
                  </CircleMarker>
                )
              })}
            </LayerGroup>
          </LayersControl.Overlay>

          <LayersControl.Overlay name="Signalements (test)">
            <LayerGroup>
              {signalements.map((f) => {
                const [lon, lat] = f.geometry.coordinates
                const p = f.properties
                return (
                  <CircleMarker
                    key={p.id}
                    center={[lat, lon]}
                    radius={6}
                    pathOptions={{ color: couleurSignalement(p.attendu), fillOpacity: 0.9 }}
                  >
                    <Popup>
                      <strong>Signalement n°{p.id}</strong>
                      <br />
                      {p.description}
                      <br />
                      Type : {p.type_dechet} / Volume : {p.volume_estime}
                      <br />
                      Attendu : {p.attendu}
                    </Popup>
                  </CircleMarker>
                )
              })}
            </LayerGroup>
          </LayersControl.Overlay>
        </FondDeCarte>
      </MapContainer>
    <Legende />
  </div>
  )
}