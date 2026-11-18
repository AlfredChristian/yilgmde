import { LayersControl, TileLayer } from '../carte'

// Fond de toutes les cartes : le plan (OpenStreetMap) par défaut et une vue satellite,
// au choix avec le petit carré en haut à droite. Le choix se fait carte par carte.
// Des couches en plus (enfants) rejoignent le même carré : une seule commande par carte.
export default function FondDeCarte({ children }) {
  return (
    <LayersControl position="topright">
      <LayersControl.BaseLayer checked name="Plan">
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
          maxZoom={19}
        />
      </LayersControl.BaseLayer>
      <LayersControl.BaseLayer name="Satellite">
        <TileLayer
          attribution="Imagerie &copy; Esri, Maxar, Earthstar Geographics"
          url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
          maxZoom={19}
        />
      </LayersControl.BaseLayer>
      {children}
    </LayersControl>
  )
}
