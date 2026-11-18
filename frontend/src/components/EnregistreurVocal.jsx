import { useEffect, useRef, useState } from 'react'
import Icone from './Icone'
import './EnregistreurVocal.css'

const DUREE_MAX = 60 // secondes [H]

// Chrome/Android produisent du webm, Safari/iPhone du mp4.
function choisirFormat() {
  if (!window.MediaRecorder) return null
  const formats = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4']
  return formats.find((f) => MediaRecorder.isTypeSupported(f)) ?? ''
}

export default function EnregistreurVocal({ onChange }) {
  const [etat, setEtat] = useState('repos') // repos | enregistrement | pret
  const [secondes, setSecondes] = useState(0)
  const [url, setUrl] = useState(null)
  const [erreur, setErreur] = useState(null)

  const recorder = useRef(null)
  const flux = useRef(null)
  const morceaux = useRef([])
  const minuteur = useRef(null)
  const duree = useRef(0)
  const urlRef = useRef(null)

  // Nettoyage si on quitte la page en cours d'enregistrement.
  useEffect(() => {
    return () => {
      clearInterval(minuteur.current)
      flux.current?.getTracks().forEach((t) => t.stop())
      if (urlRef.current) URL.revokeObjectURL(urlRef.current)
    }
  }, [])

  async function demarrer() {
    setErreur(null)
    const format = choisirFormat()
    if (!window.isSecureContext) {
      setErreur("La note vocale demande une adresse sécurisée (https). Ouvrez l'application par son adresse https.")
      return
    }
    if (format === null || !navigator.mediaDevices?.getUserMedia) {
      setErreur("L'enregistrement vocal n'est pas disponible sur cet appareil.")
      return
    }
    try {
      flux.current = await navigator.mediaDevices.getUserMedia({ audio: true })
    } catch {
      setErreur("Microphone refusé ou indisponible. Autorisez-le dans le navigateur.")
      return
    }

    const rec = new MediaRecorder(flux.current, format ? { mimeType: format } : undefined)
    morceaux.current = []
    rec.ondataavailable = (e) => {
      if (e.data.size) morceaux.current.push(e.data)
    }
    rec.onstop = () => {
      flux.current?.getTracks().forEach((t) => t.stop())
      const blob = new Blob(morceaux.current, { type: rec.mimeType || format })
      const nouvelleUrl = URL.createObjectURL(blob)
      urlRef.current = nouvelleUrl
      setUrl(nouvelleUrl)
      setEtat('pret')
      onChange({ blob, duree: duree.current })
    }

    recorder.current = rec
    duree.current = 0
    setSecondes(0)
    rec.start()
    setEtat('enregistrement')

    minuteur.current = setInterval(() => {
      duree.current += 1
      setSecondes(duree.current)
      if (duree.current >= DUREE_MAX) arreter()
    }, 1000)
  }

  function arreter() {
    clearInterval(minuteur.current)
    if (recorder.current?.state === 'recording') recorder.current.stop()
  }

  function supprimer() {
    if (urlRef.current) URL.revokeObjectURL(urlRef.current)
    urlRef.current = null
    setUrl(null)
    setEtat('repos')
    setSecondes(0)
    onChange(null)
  }

  return (
    <div className="vocal">
      {etat === 'repos' && (
        <button type="button" className="vocal-micro" onClick={demarrer}>
          <Icone nom="micro" taille={36} />
          <span>Appuyez pour parler</span>
        </button>
      )}

      {etat === 'enregistrement' && (
        <button type="button" className="vocal-micro vocal-en-cours" onClick={arreter}>
          <span className="vocal-carre" />
          <span>
            Enregistrement… {secondes} s / {DUREE_MAX} s. Appuyez pour arrêter
          </span>
        </button>
      )}

      {etat === 'pret' && (
        <div className="vocal-pret">
          <audio controls src={url} />
          <button type="button" className="vocal-refaire" onClick={supprimer}>
            Refaire
          </button>
        </div>
      )}

      {erreur && <p className="vocal-erreur">{erreur}</p>}
    </div>
  )
}