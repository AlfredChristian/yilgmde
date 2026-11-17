import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { getFileModeration } from '../api/client'
import Icone from '../components/Icone'
import './Admin.css'

const TYPES = { menager: 'Ordures ménagères', organique: 'Déchets organiques', plastiques: 'Plastiques', gravats: 'Gravats', encombrants: 'Encombrants', autre: 'Autre' }

// Une carte de la file : un résumé. Valider ou rejeter se fait dans la fiche, après examen (D54).
function Carte({ s }) {
  // score_auto peut etre null (signalement importe ou ancien) : pas de note
  const grade = s.score_auto == null ? '–' : s.score_auto >= 0.75 ? 'A' : s.score_auto >= 0.5 ? 'B' : 'C'
  const recu = new Date(s.cree_le).toLocaleString('fr-FR', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
  return (
    <Link to={`/admin/signalements/${s.id}`} className="carte mod-carte" aria-label={`Examiner le signalement n°${s.id}`}>
      <div className="carte-gauche">
        <span className="tuile"><Icone nom="carte" taille={28} /></span>
        <span className="statut statut-attente">À vérifier</span>
        <span className="carte-note">reçu le {recu}</span>
      </div>
      <div>
        <h3 className="carte-titre">Signalement n°{s.id}</h3>
        <p className="carte-texte">
          {TYPES[s.type_dechet] ?? s.type_dechet} · volume {s.volume_estime}
          {(s.a_photo || s.a_audio) && <><br />{[s.a_photo && 'photo', s.a_audio && 'note vocale'].filter(Boolean).join(' · ')}</>}
        </p>
        {s.alertes.length > 0 && (
          <p className="mod-alerte">{s.alertes.length} alerte{s.alertes.length > 1 ? 's' : ''} : doublon ou dépotoir proche</p>
        )}
        <span className="mod-examiner">Examiner →</span>
      </div>
      <span className="badge" title={s.score_auto == null ? 'Pas de score automatique' : `Score automatique : ${Math.round(s.score_auto * 100)} %`}>{grade}</span>
    </Link>
  )
}

export default function Admin() {
  const { session } = useAuth()
  const [file, setFile] = useState(null)
  const [erreur, setErreur] = useState(null)

  useEffect(() => {
    getFileModeration().then(setFile).catch((e) => setErreur(e.message))
  }, [])

  return (
    <main className="admin">
      <h1>Espace mairie</h1>
      <p className="admin-intro">Connecté : {session.nom}</p>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, marginBottom: 24 }}>
        <Link to="/admin/plan" className="btn-contour plein">Plan de gestion</Link>
        <Link to="/admin/utilisateurs" className="btn-contour">Comptes</Link>
      </div>
      <h2>Signalements à vérifier {file && `(${file.length})`}</h2>
      <p className="admin-intro">Cliquez sur un signalement pour voir son emplacement, sa photo et son voisinage, puis décider.</p>

      {erreur && <p className="mod-erreur">{erreur}</p>}
      {file === null && !erreur && <div className="admin-etat"><span className="admin-etat-icone"><Icone nom="suivi" taille={28} /></span><strong>Chargement de la file</strong><span>Nous récupérons les signalements à vérifier.</span></div>}
      {file?.length === 0 && <div className="admin-etat"><span className="admin-etat-icone admin-etat-ok"><Icone nom="check" taille={28} /></span><strong>Tout est à jour</strong><span>Rien à modérer pour le moment. Les nouveaux signalements apparaîtront ici.</span><Link to="/admin/plan" className="btn-contour">Ouvrir le plan de gestion</Link></div>}

      <div className="mod-grille">
        {file?.map((s) => (
          <Carte key={s.id} s={s} />
        ))}
      </div>
    </main>
  )
}