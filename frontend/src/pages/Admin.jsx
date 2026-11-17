import { useAuth } from '../auth/AuthContext'

export default function Admin() {
  const { session } = useAuth()
  return (
    <main style={{ maxWidth: 720, margin: '0 auto', padding: 32 }}>
      <h1>Espace mairie</h1>
      <p>Connecté : {session.nom}. La file de modération arrive à l'étape suivante.</p>
    </main>
  )
}