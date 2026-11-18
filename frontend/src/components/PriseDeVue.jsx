import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import './PriseDeVue.css'

// Caméra de l'ordinateur (webcam), en fenêtre. Sur un téléphone, le bouton « Prendre une photo »
// ouvre directement l'appareil photo (attribut `capture`) ; les navigateurs d'ordinateur
// ignorent cet attribut et ouvrent l'explorateur de fichiers, d'où cette fenêtre.

function messageErreur(e) {
  if (!window.isSecureContext) return 'La caméra n’est accessible que sur une adresse sécurisée (https ou localhost).'
  if (e?.name === 'NotAllowedError') return 'L’accès à la caméra a été refusé. Autorisez la caméra pour ce site dans votre navigateur.'
  if (e?.name === 'NotFoundError' || e?.name === 'OverconstrainedError') return 'Aucune caméra n’a été trouvée sur cet ordinateur.'
  if (e?.name === 'NotReadableError') return 'La caméra est déjà utilisée par une autre application.'
  return 'La caméra ne peut pas être ouverte sur cet appareil.'
}

export default function PriseDeVue({ onPhoto, onFermer, onChoisirFichier }) {
  const video = useRef(null)
  const flux = useRef(null)
  const disponible = Boolean(navigator.mediaDevices?.getUserMedia)
  const [etat, setEtat] = useState(disponible ? 'ouverture' : 'erreur') // ouverture | pret | erreur
  const [erreur, setErreur] = useState(disponible ? null : messageErreur(null))
  const [cliche, setCliche] = useState(null)     // { fichier, url }

  useEffect(() => {
    let actif = true
    if (!disponible) return undefined
    navigator.mediaDevices
      .getUserMedia({ video: { facingMode: 'environment', width: { ideal: 1920 }, height: { ideal: 1080 } }, audio: false })
      .then((s) => {
        if (!actif) { s.getTracks().forEach((t) => t.stop()); return }
        flux.current = s
        if (video.current) video.current.srcObject = s
        setEtat('pret')
      })
      .catch((e) => { if (actif) { setErreur(messageErreur(e)); setEtat('erreur') } })
    return () => {
      actif = false
      flux.current?.getTracks().forEach((t) => t.stop())
    }
  }, [disponible])

  useEffect(() => () => { if (cliche) URL.revokeObjectURL(cliche.url) }, [cliche])

  useEffect(() => {
    const touche = (e) => { if (e.key === 'Escape') onFermer() }
    window.addEventListener('keydown', touche)
    return () => window.removeEventListener('keydown', touche)
  }, [onFermer])

  function declencher() {
    const v = video.current
    if (!v?.videoWidth) return
    const toile = document.createElement('canvas')
    toile.width = v.videoWidth
    toile.height = v.videoHeight
    toile.getContext('2d').drawImage(v, 0, 0)
    toile.toBlob((b) => {
      if (!b) return
      const fichier = new File([b], `photo-${new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-')}.jpg`, { type: 'image/jpeg' })
      setCliche({ fichier, url: URL.createObjectURL(b) })
    }, 'image/jpeg', 0.92)
  }

  return createPortal(
    <div className="pdv-fond" role="dialog" aria-modal="true" aria-label="Prendre une photo avec la caméra">
      <div className="pdv">
        <header className="pdv-tete">
          <h2>Prendre une photo</h2>
          <button type="button" className="pdv-fermer" onClick={onFermer}>Fermer</button>
        </header>

        <div className="pdv-vue">
          {etat === 'erreur' ? (
            <div className="pdv-erreur" role="alert">
              <p>{erreur}</p>
              <button type="button" className="btn-contour plein" onClick={onChoisirFichier}>Choisir une image à la place</button>
            </div>
          ) : (
            <>
              <video ref={video} autoPlay playsInline muted className={cliche ? 'cache' : ''} aria-label="Image de la caméra" />
              {cliche && <img src={cliche.url} alt="Photo prise, à vérifier avant de l’utiliser" />}
              {etat === 'ouverture' && <p className="pdv-attente"><span className="role-spinner" /> Ouverture de la caméra</p>}
            </>
          )}
        </div>

        {etat === 'pret' && (
          <footer className="pdv-actions">
            {cliche ? (
              <>
                <button type="button" className="btn-contour" onClick={() => setCliche(null)}>Reprendre</button>
                <button type="button" className="btn btn-primaire" onClick={() => onPhoto(cliche.fichier)}>Utiliser cette photo</button>
              </>
            ) : (
              <button type="button" className="btn btn-primaire pdv-declencheur" onClick={declencher}>Prendre la photo</button>
            )}
          </footer>
        )}
      </div>
    </div>,
    document.body,
  )
}
