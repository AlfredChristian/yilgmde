import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { getFileModeration, validerSignalement, rejeterSignalement } from '../api/client'
import Icone from '../components/Icone'
import './Admin.css'

const MOTIFS = ['Photo sans rapport', 'Position incohérente', 'Doublon', 'Pas un dépotoir', 'Autre']

// "doublon_probable:12" -> libelle lisible
function libelleAlerte(a) {
  const [code, ref] = a.split(':')
  const textes = { doublon_probable: `Doublon probable du signalement n°${ref}` }
  return textes[code] ?? a
}

function Carte({ s, onTraite, onErreur }) {
  const [motif, setMotif] = useState(MOTIFS[0])
  const [rejet, setRejet] = useState(false)
  const [occupe, setOccupe] = useState(false)

  async function agir(fn) {
    setOccupe(true)
    try {
      await fn()
      onTraite(s.id)
    } catch (e) {
      onErreur(e.message)
      setOccupe(false)
    }
  }

  const doublon = s.alertes.find((a) => a.startsWith('doublon_probable:'))
  const idDoublon = doublon ? Number(doublon.split(':')[1]) : null

  // score_auto peut etre null (signalement importe ou ancien) : pas de note
  const grade = s.score_auto == null ? '–' : s.score_auto >= 0.75 ? 'A' : s.score_auto >= 0.5 ? 'B' : 'C'
  const heure = new Date(s.cree_le).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })

  return (
    <article className="carte">
      <div className="carte-gauche">
        <span className="tuile"><Icone nom="carte" taille={28} /></span>
        <span className="statut statut-attente">À vérifier</span>
        <span className="carte-note">reçu à {heure}</span>
      </div>

      <div>
        <h3 className="carte-titre">Signalement n°{s.id}</h3>
        <p className="carte-texte">
          {s.type_dechet} · volume {s.volume_estime}
          <br />
          {s.latitude.toFixed(5)}, {s.longitude.toFixed(5)}
        </p>
        {s.photo_url && <img src={s.photo_url} alt="Photo du signalement" className="mod-photo" />}
        {s.audio_url && <audio controls src={s.audio_url} style={{ width: '100%', marginBottom: 12 }} />}
        {s.alertes.map((a) => (
          <p key={a} className="mod-alerte">{libelleAlerte(a)}</p>
        ))}

        {!rejet ? (
          <div className="carte-actions">
            <button className="btn-contour plein" disabled={occupe} onClick={() => agir(() => validerSignalement(s.id))}>
              <Icone nom="check" taille={18} /> Valider
            </button>
            {idDoublon && (
              <button className="btn-contour" disabled={occupe} onClick={() => agir(() => validerSignalement(s.id, idDoublon))}>
                <Icone nom="fusion" taille={18} /> Fusionner
              </button>
            )}
            <button className="btn-contour danger" disabled={occupe} onClick={() => setRejet(true)}>
              <Icone nom="croix" taille={18} /> Rejeter
            </button>
          </div>
        ) : (
          <div className="mod-rejet">
            <label>
              Motif du rejet
              <select value={motif} onChange={(e) => setMotif(e.target.value)}>
                {MOTIFS.map((m) => <option key={m}>{m}</option>)}
              </select>
            </label>
            <div className="carte-actions">
              <button className="btn-contour danger" disabled={occupe} onClick={() => agir(() => rejeterSignalement(s.id, motif))}>
                Confirmer le rejet
              </button>
              <button className="btn-contour" disabled={occupe} onClick={() => setRejet(false)}>Annuler</button>
            </div>
          </div>
        )}
      </div>

      <span className="badge" title={s.score_auto == null ? 'Pas de score automatique' : `Score automatique : ${Math.round(s.score_auto * 100)} %`}>{grade}</span>
    </article>
  )
}

export default function Admin() {
  const { session } = useAuth()
  const [file, setFile] = useState(null)
  const [erreur, setErreur] = useState(null)

  useEffect(() => {
    getFileModeration().then(setFile).catch((e) => setErreur(e.message))
  }, [])

  const retirer = (id) => setFile((f) => f.filter((s) => s.id !== id))

  return (
    <main className="admin">
      <h1>Espace mairie</h1>
      <p className="admin-intro">Connecté : {session.nom}</p>
      <Link to="/admin/plan" className="btn-contour plein" style={{ marginBottom: 24 }}>
        Plan de gestion
      </Link>
      <h2>Signalements à vérifier {file && `(${file.length})`}</h2>

      {erreur && <p className="mod-erreur">{erreur}</p>}
      {file === null && !erreur && <div className="admin-etat"><span className="admin-etat-icone"><Icone nom="suivi" taille={28} /></span><strong>Chargement de la file</strong><span>Nous récupérons les signalements à vérifier.</span></div>}
      {file?.length === 0 && <div className="admin-etat"><span className="admin-etat-icone admin-etat-ok"><Icone nom="check" taille={28} /></span><strong>Tout est à jour</strong><span>Rien à modérer pour le moment. Les nouveaux signalements apparaîtront ici.</span><Link to="/admin/plan" className="btn-contour">Ouvrir le plan de gestion</Link></div>}

      <div className="mod-grille">
        {file?.map((s) => (
          <Carte key={s.id} s={s} onTraite={retirer} onErreur={setErreur} />
        ))}
      </div>
    </main>
  )
}