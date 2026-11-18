import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { MapContainer, Marker, useMap, useMapEvents } from '../carte'
import FondDeCarte from '../components/FondDeCarte'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import Icone from '../components/Icone'
import EnregistreurVocal from '../components/EnregistreurVocal'
import { signalerAvecFile } from '../api/client'
import { masquerPhoto } from '../masquage'
import PriseDeVue from '../components/PriseDeVue'
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

const pluriel = (n, mot) => `${n} ${mot}${n > 1 ? 's' : ''}`

function texteMasquage(m) {
  if (!m) return null
  if (m.etat === 'serveur') return 'Le masquage sera fait à la réception.'
  if (m.etat !== 'fait') return null
  if (!m.visages && !m.plaques) return 'Aucun visage ni plaque repéré. Position GPS de la photo retirée.'
  const parts = [m.visages && pluriel(m.visages, 'visage'), m.plaques && pluriel(m.plaques, 'plaque')].filter(Boolean)
  const accord = (m.visages ? 'masqué' : 'masquée') + (m.visages + m.plaques > 1 ? 's' : '')
  return `${parts.join(' et ')} ${accord} sur votre appareil.`
}

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
  const [photo, setPhoto] = useState(null)
  const [photoUrl, setPhotoUrl] = useState(null)
  const [cameraOuverte, setCameraOuverte] = useState(false)
  const choixFichier = useRef(null)
  // Téléphone ou tablette : l'attribut `capture` ouvre l'appareil photo. Ordinateur : la webcam en fenêtre.
  const ecranTactile = typeof window !== 'undefined' && window.matchMedia?.('(pointer: coarse)').matches
  const [masquage, setMasquage] = useState(null) // { etat: 'en_cours' | 'fait' | 'serveur', visages, plaques }
  const [audio, setAudio] = useState(null)
  const [message, setMessage] = useState(null)
  const [envoiEnCours, setEnvoiEnCours] = useState(false)
  const [confirmation, setConfirmation] = useState(null)

  useEffect(() => {
    if (!photo) {
      setPhotoUrl(null)
      return undefined
    }
    const url = URL.createObjectURL(photo)
    setPhotoUrl(url)
    return () => URL.revokeObjectURL(url)
  }, [photo])

  function choisirPhoto(e) {
    const fichier = e.target.files?.[0]
    e.target.value = ''
    if (fichier) traiterPhoto(fichier)
  }

  async function traiterPhoto(fichier) {
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(fichier.type)) {
      setMessage('Format non accepté. Utilisez une image JPEG, PNG ou WebP.')
      return
    }
    if (fichier.size > 25 * 1024 * 1024) {
      setMessage('Image trop volumineuse. La taille maximale est de 25 Mo.')
      return
    }
    setMessage(null)
    setPhoto(null)
    setMasquage({ etat: 'en_cours' })
    // Visages et plaques masqués ici, avant l'envoi : la photo d'origine reste sur le téléphone (D59).
    try {
      const r = await masquerPhoto(fichier)
      setPhoto(r.fichier)
      setMasquage({ etat: 'fait', visages: r.visages, plaques: r.plaques })
    } catch {
      if (fichier.size > 5 * 1024 * 1024) {
        setMasquage(null)
        setMessage('Image trop volumineuse pour ce téléphone. La taille maximale est de 5 Mo.')
        return
      }
      setPhoto(fichier)
      setMasquage({ etat: 'serveur' })
    }
  }

  function retirerPhoto() {
    setPhoto(null)
    setMasquage(null)
  }

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
      const resultat = await signalerAvecFile({
        type_dechet: type,
        volume_estime: volume,
        description,
        latitude: Number(position[0].toFixed(6)),
        longitude: Number(position[1].toFixed(6)),
        photo,
        audio,
      })
      setConfirmation(
        resultat.envoye
          ? resultat.reponse
          : { statut: 'hors_ligne' },
      )
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
    setPhoto(null)
    setMasquage(null)
    setAudio(null)
    setType('menager')
    setVolume('moyen')
  }

if (confirmation) {
        if (confirmation.statut === 'hors_ligne') {
      return (
        <main className="signaler">
          <section className="confirmation">
            <h1>Enregistré sur votre téléphone</h1>
            <p>
              Pas de réseau pour le moment. Votre signalement sera envoyé
              automatiquement dès que la connexion reviendra.
            </p>
            <div className="confirmation-actions">
              <button type="button" className="btn btn-vert" onClick={nouveau}>
                Faire un autre signalement
              </button>
              <Link to="/" className="btn btn-jaune">Retour à l'accueil</Link>
            </div>
          </section>
        </main>
      )
    }
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
    <main className="signaler signaler-deux">
      <section className="signaler-gauche">
        <h1 className="signaler-titre">Signaler un dépotoir</h1>
        <p className="signaler-intro">Aucun compte nécessaire. Placez le point à l’endroit exact du dépotoir.</p>
        <div className="signaler-question">
          <h2>Où est-il ?</h2>
          <button type="button" className="btn-contour plein" onClick={utiliserMaPosition}>
            <Icone nom="carte" taille={18} /> Utiliser ma position
          </button>
        </div>
          <div className="signaler-carte">
            <MapContainer center={CENTRE} zoom={13} style={{ height: '100%', width: '100%' }}>
              <FondDeCarte />
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
            ? `Point placé : ${position[0].toFixed(5)}, ${position[1].toFixed(5)}. Glissez-le pour ajuster.`
            : 'Touchez la carte pour placer le point.'}
        </p>
      </section>

      <form onSubmit={valider} className="signaler-droite signaler-form">
        <section className="signaler-bloc">
          <h2>De quoi s’agit-il ?</h2>
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

        </section>

        <section className="signaler-bloc">
          <h2>Photo <span className="facultatif">facultatif</span></h2>
          <p className="signaler-aide">Prenez une photo sur place ou choisissez une image dans votre appareil.</p>
          <div className="photo-actions">
                {ecranTactile ? (
                  <label className="btn-contour photo-bouton">
                    <Icone nom="photo" taille={18} /> Prendre une photo
                    <input type="file" accept="image/jpeg,image/png,image/webp" capture="environment" onChange={choisirPhoto} />
                  </label>
                ) : (
                  <button type="button" className="btn-contour photo-bouton" onClick={() => setCameraOuverte(true)}>
                    <Icone nom="photo" taille={18} /> Prendre une photo
                  </button>
                )}
                <label className="btn-contour photo-bouton">
                  <Icone nom="image" taille={18} /> Choisir une image
                  <input ref={choixFichier} type="file" accept="image/jpeg,image/png,image/webp" onChange={choisirPhoto} />
                </label>
                {cameraOuverte && (
                  <PriseDeVue
                    onFermer={() => setCameraOuverte(false)}
                    onPhoto={(f) => { setCameraOuverte(false); traiterPhoto(f) }}
                    onChoisirFichier={() => { setCameraOuverte(false); choixFichier.current?.click() }}
                  />
                )}
              </div>
              {masquage?.etat === 'en_cours' && (
                <p className="photo-masquage" role="status">Masquage des visages et des plaques sur votre appareil…</p>
              )}
              {photo && (
                <div className="photo-apercu">
                  {photoUrl && <img src={photoUrl} alt="Aperçu du dépotoir signalé, visages et plaques masqués" />}
                  <div className="photo-apercu-info">
                    <strong>{photo.name}</strong>
                    <span>{(photo.size / 1024 / 1024).toFixed(2)} Mo</span>
                    <span className="photo-masquage-etat">{texteMasquage(masquage)}</span>
                  </div>
                  <button type="button" className="photo-supprimer" onClick={retirerPhoto}>Supprimer</button>
                </div>
              )}
        </section>

        <section className="signaler-bloc">
          <h2>Description <span className="facultatif">facultatif</span></h2>
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
        </section>

        {message && <p className="signaler-message">{message}</p>}
        {!position && <p className="signaler-aide signaler-rappel">Placez d’abord le point sur la carte.</p>}
        <button type="submit" className="btn btn-primaire signaler-envoyer" disabled={envoiEnCours || masquage?.etat === 'en_cours'}>
          {envoiEnCours ? 'Envoi en cours…' : 'Envoyer le signalement'}
        </button>
      </form>
    </main>
  )
}