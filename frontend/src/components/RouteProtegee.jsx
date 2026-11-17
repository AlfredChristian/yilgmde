import { Navigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

// roles : liste des roles autorises. L'affichage n'est qu'un confort :
// les droits reels sont verifies par le serveur.
export default function RouteProtegee({ roles, children }) {
  const { session } = useAuth()
  if (!session) return <Navigate to="/connexion" replace />
  if (roles && !roles.includes(session.role)) {
    return (
      <main style={{ maxWidth: 560, margin: '0 auto', padding: 32 }}>
        <h1>Accès refusé</h1>
        <p>Votre rôle ne permet pas d'ouvrir cette page.</p>
      </main>
    )
  }
  return children
}