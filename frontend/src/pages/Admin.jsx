import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { getFileModeration } from '../api/client'
import Icone from '../components/Icone'
import './Admin.css'

const TYPES = { menager: 'Ordures ménagères', organique: 'Déchets organiques', plastiques: 'Plastiques', gravats: 'Gravats', encombrants: 'Encombrants', autre: 'Autre' }

// Une ligne de la file : un résumé. Valider ou rejeter se fait dans la fiche, après examen (D54).
function Ligne({ s }) {
  const recu = new Date(s.cree_le).toLocaleString('fr-FR', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
  const medias = [s.a_photo && 'Photo', s.a_audio && 'Note vocale'].filter(Boolean)
  return (
    <li>
      <Link to={`/admin/signalements/${s.id}`} className="file-ligne">
        <span className="file-id">n°{s.id}</span>
        <span className="file-quoi">
          <strong>{TYPES[s.type_dechet] ?? s.type_dechet}</strong>
          <span>Volume {s.volume_estime}</span>
        </span>
        <span className="file-recu">{recu}</span>
        <span className="file-tags">
          {medias.map((m) => <span key={m} className="puce">{m}</span>)}
          {s.alertes.length > 0 && <span className="puce puce-alerte">{s.alertes.length} à proximité</span>}
        </span>
        <span className="btn-contour file-bouton">Examiner</span>
      </Link>
    </li>
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
      <header className="espace-tete">
        <div>
          <h1>Espace mairie</h1>
          <p>Connecté en tant que {session.nom}</p>
        </div>
        <nav className="espace-actions" aria-label="Outils de la mairie">
          <Link to="/admin/plan" className="btn-contour plein"><Icone nom="itineraire" taille={18} /> Plan de gestion</Link>
          <Link to="/admin/utilisateurs" className="btn-contour"><Icone nom="mairie" taille={18} /> Comptes</Link>
        </nav>
      </header>

      <section className="file">
        <div className="file-tete">
          <h2>Signalements à vérifier</h2>
          {file && <span className="file-compte">{file.length}</span>}
        </div>
        <p className="admin-intro">Ouvrez un signalement pour voir son emplacement, sa photo et son voisinage avant de décider.</p>

        {erreur && <p className="mod-erreur" role="alert">{erreur}</p>}
        {file === null && !erreur && <div className="admin-etat"><span className="role-spinner" /> Chargement des signalements</div>}
        {file?.length === 0 && (
          <div className="admin-etat">
            <span className="admin-etat-icone"><Icone nom="check" taille={26} /></span>
            <strong>Aucun signalement en attente</strong>
            <span>Les nouveaux signalements apparaîtront ici.</span>
          </div>
        )}
        {file?.length > 0 && (
          <ol className="file-liste">
            {file.map((s) => <Ligne key={s.id} s={s} />)}
          </ol>
        )}
      </section>
    </main>
  )
}
