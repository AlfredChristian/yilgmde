// Composants de carte React écrits directement sur Leaflet (licence BSD-2), D65.
//
// Ils remplacent react-leaflet, dont la licence (Hippocratic 2.1) n'est pas reconnue open
// source par l'OSI. Mêmes noms et mêmes propriétés que react-leaflet pour ce que l'application
// utilise : MapContainer, TileLayer, LayersControl (BaseLayer, Overlay), LayerGroup, Marker,
// CircleMarker, Circle, Polyline, Polygon, Tooltip, Popup, useMap, useMapEvents. Une seule
// propriété en plus : `<Popup ouvert>` ouvre la bulle (utilisé par la carte publique).

import { createContext, useContext, useEffect, useLayoutEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

const CarteContexte = createContext(null)       // la carte Leaflet
const ConteneurContexte = createContext(null)   // où ajouter une couche : { ajouter, retirer }
const CoucheContexte = createContext(null)      // la couche à laquelle accrocher une bulle
const ControleContexte = createContext(null)    // le sélecteur de fonds et de couches

export function useMap() {
  const map = useContext(CarteContexte)
  if (!map) throw new Error('useMap doit être utilisé dans <MapContainer>')
  return map
}

/** Écoute des événements de la carte ; les gestionnaires peuvent changer à chaque rendu. */
export function useMapEvents(gestionnaires) {
  const map = useMap()
  const courant = useRef(gestionnaires)
  useEffect(() => { courant.current = gestionnaires })
  useEffect(() => {
    const relais = Object.fromEntries(Object.keys(courant.current).map((nom) => [nom, (e) => courant.current[nom]?.(e)]))
    map.on(relais)
    return () => { map.off(relais) }
    // Les noms d'événements sont fixés au premier rendu, comme dans react-leaflet.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map])
  return map
}

export function MapContainer({ center, zoom, style, className, children, ...options }) {
  const div = useRef(null)
  const [map, setMap] = useState(null)
  useLayoutEffect(() => {
    const m = L.map(div.current, { center, zoom, ...options })
    setMap(m)
    return () => { m.remove(); setMap(null) }
    // La vue initiale ne compte qu'à la création ; ensuite on passe par useMap().
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
  const conteneur = map && { ajouter: (c) => c.addTo(map), retirer: (c) => c.remove() }
  return (
    <div ref={div} style={style} className={className}>
      {map && (
        <CarteContexte.Provider value={map}>
          <ConteneurContexte.Provider value={conteneur}>{children}</ConteneurContexte.Provider>
        </CarteContexte.Provider>
      )}
    </div>
  )
}

// Les setState dans les effets ci-dessous gardent l'objet Leaflet créé (système externe) :
// c'est l'usage prévu des effets, l'avertissement « set-state-in-effect » ne s'applique pas.
// Crée la couche une fois, l'ajoute à son conteneur, la retire au démontage, et rejoue
// `maj` quand les propriétés changent. Les gestionnaires d'événements suivent le dernier rendu.
function useCouche(creer, maj, deps, eventHandlers, auFond = false) {
  const conteneur = useContext(ConteneurContexte)
  const [couche, setCouche] = useState(null)
  const gestionnaires = useRef(eventHandlers)
  useEffect(() => { gestionnaires.current = eventHandlers })
  useEffect(() => {
    const c = creer()
    const noms = Object.keys(gestionnaires.current ?? {})
    const relais = Object.fromEntries(noms.map((nom) => [nom, (e) => gestionnaires.current?.[nom]?.(e)]))
    c.on(relais)
    conteneur.ajouter(c)
    // Lignes et zones sous les points, quel que soit l'ordre d'arrivée (sinon un trajet
    // dessiné après coup cacherait les points et prendrait leurs survols).
    if (auFond && c._map) c.bringToBack()
    setCouche(c)
    return () => { c.off(relais); conteneur.retirer(c) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conteneur])
  useEffect(() => { if (couche) maj(couche) }, [couche, ...deps]) // eslint-disable-line react-hooks/exhaustive-deps
  return couche
}

function AvecBulles({ couche, children }) {
  return couche ? <CoucheContexte.Provider value={couche}>{children}</CoucheContexte.Provider> : null
}

export function TileLayer({ url, ...options }) {
  useCouche(() => L.tileLayer(url, options), (c) => c.setUrl(url), [url])
  return null
}

// Groupe de couches : ses enfants s'y ajoutent ; le groupe s'ajoute à son propre conteneur.
function useGroupe() {
  const groupe = useCouche(() => L.layerGroup(), () => {}, [])
  return groupe && { groupe, conteneur: { ajouter: (c) => groupe.addLayer(c), retirer: (c) => groupe.removeLayer(c) } }
}

export function LayerGroup({ children }) {
  const g = useGroupe()
  return g ? <ConteneurContexte.Provider value={g.conteneur}>{children}</ConteneurContexte.Provider> : null
}

export function LayersControl({ position = 'topright', children }) {
  const map = useMap()
  const [controle, setControle] = useState(null)
  useEffect(() => {
    const c = L.control.layers(undefined, undefined, { position }).addTo(map)
    setControle(c)
    return () => { c.remove() }
  }, [map, position])
  return controle ? <ControleContexte.Provider value={controle}>{children}</ControleContexte.Provider> : null
}

function CoucheDuControle({ name, checked = false, children, fond }) {
  const map = useMap()
  const controle = useContext(ControleContexte)
  const [groupe] = useState(() => L.layerGroup())
  useEffect(() => {
    if (fond) controle.addBaseLayer(groupe, name)
    else controle.addOverlay(groupe, name)
    if (checked) groupe.addTo(map)
    return () => { controle.removeLayer(groupe); groupe.remove() }
    // `checked` ne vaut qu'au départ : ensuite c'est l'utilisateur qui choisit.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [controle, groupe, name, map, fond])
  const conteneur = { ajouter: (c) => groupe.addLayer(c), retirer: (c) => groupe.removeLayer(c) }
  return <ConteneurContexte.Provider value={conteneur}>{children}</ConteneurContexte.Provider>
}
LayersControl.BaseLayer = function BaseLayer(props) { return <CoucheDuControle {...props} fond /> }
LayersControl.Overlay = function Overlay(props) { return <CoucheDuControle {...props} fond={false} /> }

export function CircleMarker({ center, radius = 10, pathOptions, eventHandlers, interactive = true, children }) {
  const couche = useCouche(
    () => L.circleMarker(center, { radius, interactive, ...pathOptions }),
    (c) => { c.setLatLng(center); c.setRadius(radius); c.setStyle({ ...pathOptions }) },
    [center[0], center[1], radius, JSON.stringify(pathOptions)],
    eventHandlers,
  )
  return <AvecBulles couche={couche}>{children}</AvecBulles>
}

export function Circle({ center, radius, pathOptions, eventHandlers, interactive = true, children }) {
  const couche = useCouche(
    () => L.circle(center, { radius, interactive, ...pathOptions }),
    (c) => { c.setLatLng(center); c.setRadius(radius); c.setStyle({ ...pathOptions }) },
    [center[0], center[1], radius, JSON.stringify(pathOptions)],
    eventHandlers,
  )
  return <AvecBulles couche={couche}>{children}</AvecBulles>
}

export function Marker({ position, icon, zIndexOffset = 0, keyboard = true, interactive = true, draggable = false, eventHandlers, children }) {
  const couche = useCouche(
    () => L.marker(position, { ...(icon ? { icon } : {}), zIndexOffset, keyboard, interactive, draggable }),
    (c) => { c.setLatLng(position); if (icon) c.setIcon(icon); c.setZIndexOffset(zIndexOffset) },
    [position[0], position[1], icon, zIndexOffset],
    eventHandlers,
  )
  return <AvecBulles couche={couche}>{children}</AvecBulles>
}

function useTrace(Classe, positions, pathOptions, eventHandlers, interactive) {
  return useCouche(
    () => new Classe(positions, { interactive, ...pathOptions }),
    (c) => { c.setLatLngs(positions); c.setStyle({ ...pathOptions }) },
    [positions, JSON.stringify(pathOptions)],
    eventHandlers,
    true,
  )
}

export function Polyline({ positions, pathOptions, eventHandlers, interactive = true, children }) {
  const couche = useTrace(L.Polyline, positions, pathOptions, eventHandlers, interactive)
  return <AvecBulles couche={couche}>{children}</AvecBulles>
}

export function Polygon({ positions, pathOptions, eventHandlers, interactive = true, children }) {
  const couche = useTrace(L.Polygon, positions, pathOptions, eventHandlers, interactive)
  return <AvecBulles couche={couche}>{children}</AvecBulles>
}

// Bulle (Tooltip ou Popup) dont le contenu est rendu par React dans un élément du DOM.
function useBulle(fabrique, lier, delier, deps) {
  const couche = useContext(CoucheContexte)
  const [element] = useState(() => document.createElement('div'))
  const [bulle, setBulle] = useState(null)
  useEffect(() => {
    if (!couche) return undefined
    const b = fabrique().setContent(element)
    lier(couche, b)
    setBulle(b)
    return () => { delier(couche) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [couche, element, ...deps])
  return { element, bulle, couche }
}

export function Tooltip({ direction = 'auto', permanent = false, sticky = false, children }) {
  const { element, bulle } = useBulle(
    () => L.tooltip({ direction, permanent, sticky }),
    (c, b) => c.bindTooltip(b),
    (c) => c.unbindTooltip(),
    [direction, permanent, sticky],
  )
  useEffect(() => { bulle?.update?.() })
  return createPortal(children, element)
}

export function Popup({ ouvert = false, children }) {
  const { element, bulle, couche } = useBulle(() => L.popup(), (c, b) => c.bindPopup(b), (c) => c.unbindPopup(), [])
  useEffect(() => { bulle?.update?.() })
  useEffect(() => { if (ouvert && couche && bulle) couche.openPopup() }, [ouvert, couche, bulle])
  return createPortal(children, element)
}
