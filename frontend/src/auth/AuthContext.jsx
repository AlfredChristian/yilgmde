import { createContext, useContext, useState } from 'react'
import { login as apiLogin, lireSession, ecrireSession } from '../api/client'

const Ctx = createContext(null)

export function AuthProvider({ children }) {
  const [session, setSession] = useState(lireSession)

  async function connecter(email, motDePasse) {
    const r = await apiLogin(email, motDePasse)
    const s = { token: r.access_token, role: r.role, nom: r.nom }
    ecrireSession(s)
    setSession(s)
    return s
  }

  function deconnecter() {
    ecrireSession(null)
    setSession(null)
  }

  return <Ctx.Provider value={{ session, connecter, deconnecter }}>{children}</Ctx.Provider>
}

export const useAuth = () => useContext(Ctx)

// Page d'accueil de chaque role.
export const ACCUEIL_ROLE = { admin: '/admin', chauffeur: '/chauffeur', laabal: '/laabal' }