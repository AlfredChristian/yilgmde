import { useEffect, useState } from 'react'
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import { getDepotoirs } from '../api/client'

// Centre de Ouagadougou [latitude, longitude]. [H] sera deplace dans la config.
const CENTRE = [12.3714, -1.5197]
const ZOOM = 13

// Couleur selon le statut du depotoir.
const COULEURS = {
  actif: '#d62828',
  eradique: '#2a9d8f',
}

export default function Carte() {
  const [depotoirs, setDepotoirs] = useState([])
  const [erreur, setErreur] = useState(null)

  useEffect(() => {
    getDepotoirs()
      .then((geojson) => setDepotoirs(geojson.features))
      .catch((e) => setErreur(e.message))
  }, [])

  return (
    <>
      {erreur && (
        <div style={{ position: 'absolute', zIndex: 1000, background: 'white', padding: 8 }}>
          Erreur : {erreur}
        </div>
      )}
      <MapContainer
        center={CENTRE}
        zoom={ZOOM}
        style={{ height: '100vh', width: '100%' }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {depotoirs.map((f) => {
          const [lon, lat] = f.geometry.coordinates
          const p = f.properties
          return (
            <CircleMarker
              key={p.id}
              center={[lat, lon]}
              radius={10}
              pathOptions={{ color: COULEURS[p.statut] ?? '#555', fillOpacity: 0.7 }}
            >
              <Popup>
                <strong>Dépotoir n°{p.id}</strong>
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
      </MapContainer>
    </>
  )
}