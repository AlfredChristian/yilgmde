import { useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { useAuth, ACCUEIL_ROLE } from '../auth/AuthContext'
import './Connexion.css'

export default function Connexion() {
  const { session, connecter } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [mdp, setMdp] = useState('')
  const [erreur, setErreur] = useState(null)
  const [chargement, setChargement] = useState(false)

  if (session) return <Navigate to={ACCUEIL_ROLE[session.role] ?? '/'} replace />

  async function valider(e) {
    e.preventDefault()
    setErreur(null)
    setChargement(true)
    try {
      const s = await connecter(email, mdp)
      navigate(ACCUEIL_ROLE[s.role] ?? '/', { replace: true })
    } catch (err) {
      setErreur(
        err.identifiants
          ? 'Email ou mot de passe incorrect.'
          : `Connexion impossible : ${err.message}. Réessayez.`,
      )
    } finally {
      setChargement(false)
    }
  }

  return (
    <main className="connexion">
      <h1>Connexion</h1>
      <form onSubmit={valider}>
        <label>
          Email
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="username" />
        </label>
        <label>
          Mot de passe
          <input type="password" value={mdp} onChange={(e) => setMdp(e.target.value)} required autoComplete="current-password" />
        </label>
        {erreur && <p className="connexion-erreur">{erreur}</p>}
        <button className="btn btn-vert" disabled={chargement}>
          {chargement ? 'Connexion…' : 'Se connecter'}
        </button>
      </form>
    </main>
  )
}