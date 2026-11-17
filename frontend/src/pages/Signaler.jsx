import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { MapContainer, TileLayer, Marker, useMap, useMapEvents } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import Icone from '../components/Icone'
import EnregistreurVocal from '../components/EnregistreurVocal'
import { postSignalement } from '../api/client'
import './Signaler.css'

const CENTRE = [12.3714, -1.5197] // [H] a deplacer dans la config

// Icone maison : evite les images par defaut de Leaflet, cassees avec Vite.
const ICONE = L.divIcon({ className: 'pin', iconSize: [22, 22], iconAnchor: [11, 11] })

const TYPES = [
  { valeur: 'menager', libelle: 'Ordures ménagères', icone: 'sac' },
  { valeur: 'gravats', libelle: 'Gravats', icone: 'gravats' },
  { valeur: 'plastiques', libelle: 'Plastiques', icone: 'bouteille' },
] // [H] a completer selon le contrat d'API

const VOLUMES = [
  { valeur: 'petit', libelle: 'Petit', icone: 'tas_petit' },
  { valeur: 'moyen', libelle: 'Moyen', icone: 'tas_moyen' },
  { valeur: 'gros', libelle: 'Gros', icone: 'tas_gros' },
]

function ClicCarte({ onChoix }) {
  useMapEvents({ click: (e) => onChoix([e.latlng.lat, e.latlng.lng]) })
  return null
}

function Recentrer({ position }) {
  const map = useMap()
  useEffect(() => {
    if (position) map.flyTo(position, Math.max(map.getZoom(), 16))
  }, [position, map])
  return null
}

export default function Signaler() {
  const [position, setPosition] = useState(null)
  const [type, setType] = useState('menager')
  const [volume, setVolume] = useState('moyen')
  const [description, setDescription] = useState('')
  const [audio, setAudio] = useState(null)
  const [message, setMessage] = useState(null)
  const [envoiEnCours, setEnvoiEnCours] = useState(false)
  const [confirmation, setConfirmation] = useState(null)

  function utiliserMaPosition() {
    if (!navigator.geolocation) {
      setMessage("La géolocalisation n'est pas disponible sur cet appareil.")
      return
    }
    setMessage('Recherche de votre position…')
    navigator.geolocation.getCurrentPosition(
      (p) => {
        setPosition([p.coords.latitude, p.coords.longitude])
        setMessage(null)
      },
      () => setMessage('Position refusée ou indisponible. Placez le point sur la carte.'),
      { enableHighAccuracy: true, timeout: 10000 },
    )
  }

  async function valider(e) {
    e.preventDefault()
    if (!position) {
      setMessage('Placez le dépotoir sur la carte avant de signaler.')
      return
    }
    setMessage(null)
    setEnvoiEnCours(true)
    try {
      const reponse = await postSignalement({
        type_dechet: type,
        volume_estime: volume,
        description,
        latitude: Number(position[0].toFixed(6)),
        longitude: Number(position[1].toFixed(6)),
        audio,
      })
      setConfirmation(reponse)
    } catch (err) {
      setMessage(`Envoi impossible : ${err.message}. Vous pouvez réessayer.`)
    } finally {
      setEnvoiEnCours(false)
    }
  }

  function nouveau() {
    setConfirmation(null)
    setPosition(null)
    setDescription('')
    setAudio(null)
    setType('menager')
    setVolume('moyen')
  }

if (confirmation) {
    const rejete = confirmation.statut === 'rejete_auto'
    return (
      <main className="signaler">
        <section className={rejete ? 'confirmation confirmation-rejet' : 'confirmation'}>
          <h1>{rejete ? 'Signalement non retenu' : 'Merci, signalement envoyé'}</h1>
          {rejete && <p>Motif : {confirmation.motif}</p>}
          <p>Gardez ce code pour suivre votre signalement :</p>
          <p className="confirmation-code">{confirmation.code_suivi}</p>
          {!rejete && (
            <p className="signaler-aide">
              Votre signalement sera vérifié avant d'apparaître sur la carte.
            </p>
          )}
          <div className="confirmation-actions">
            <button type="button" className="btn btn-vert" onClick={nouveau}>
              Faire un autre signalement
            </button>
            <Link to="/suivi" className="btn btn-vert">Suivre mon signalement</Link>
            <Link to="/" className="btn btn-jaune">Retour à l'accueil</Link>
          </div>
        </section>
      </main>
    )
  }

  return (
    <main className="signaler">
      <h1 className="signaler-titre">Signaler un dépotoir</h1>
      <p className="signaler-intro">
        Aucun compte nécessaire. Placez le point à l'endroit exact du dépotoir.
      </p>

      <form onSubmit={valider} className="signaler-form">
        <section>
          <h2>1. Où est-il ?</h2>
          <button type="button" className="btn btn-vert" onClick={utiliserMaPosition}>
            Utiliser ma position
          </button>
          <div className="signaler-carte">
            <MapContainer center={CENTRE} zoom={13} style={{ height: '100%', width: '100%' }}>
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
              <ClicCarte onChoix={setPosition} />
              <Recentrer position={position} />
              {position && (
                <Marker
                  position={position}
                  icon={ICONE}
                  draggable
                  eventHandlers={{
                    dragend: (e) => {
                      const { lat, lng } = e.target.getLatLng()
                      setPosition([lat, lng])
                    },
                  }}
                />
              )}
            </MapContainer>
          </div>
          <p className="signaler-aide">
            {position
              ? `Position : ${position[0].toFixed(5)}, ${position[1].toFixed(5)} (glissez le point pour ajuster)`
              : 'Touchez la carte pour placer le point.'}
          </p>
        </section>

        <section>
          <h2>2. De quoi s'agit-il ?</h2>

          <fieldset>
            <legend>Type de déchet</legend>
            <div className="choix choix-icones">
              {TYPES.map((t) => (
                <label key={t.valeur} className={type === t.valeur ? 'choix-actif' : ''}>
                  <input
                    type="radio"
                    name="type"
                    value={t.valeur}
                    checked={type === t.valeur}
                    onChange={() => setType(t.valeur)}
                  />
                  <Icone nom={t.icone} taille={40} />
                  {t.libelle}
                </label>
              ))}
            </div>
          </fieldset>

          <fieldset>
            <legend>Volume estimé</legend>
            <div className="choix choix-icones">
              {VOLUMES.map((v) => (
                <label key={v.valeur} className={volume === v.valeur ? 'choix-actif' : ''}>
                  <input
                    type="radio"
                    name="volume"
                    value={v.valeur}
                    checked={volume === v.valeur}
                    onChange={() => setVolume(v.valeur)}
                  />
                  <Icone nom={v.icone} taille={40} />
                  {v.libelle}
                </label>
              ))}
            </div>
          </fieldset>

          <div className="description">
            <p className="description-titre">Décrivez en quelques mots (facultatif)</p>
            <EnregistreurVocal onChange={setAudio} />
            <label>
              Ou écrivez
              <textarea
                rows={3}
                maxLength={300}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Ex. : tas d'ordures au bord de la route, près du marché"
              />
            </label>
          </div>
        </section>

        {message && <p className="signaler-message">{message}</p>}

        <button type="submit" className="btn btn-jaune" disabled={envoiEnCours}>
          {envoiEnCours ? 'Envoi en cours…' : 'Signaler'}
        </button>
      </form>
    </main>
  )
}