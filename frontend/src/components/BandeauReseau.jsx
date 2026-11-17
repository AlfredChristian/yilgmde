import { useEffect, useState } from 'react'
import { nombreEnAttente, viderFile } from '../api/client'

export default function BandeauReseau() {
  const [enLigne, setEnLigne] = useState(navigator.onLine)
  const [attente, setAttente] = useState(0)
  const [info, setInfo] = useState(null)

  async function rafraichir() {
    setAttente(await nombreEnAttente())
  }

  async function envoyer() {
    const n = await viderFile()
    if (n > 0) setInfo(`${n} signalement(s) envoyé(s).`)
    rafraichir()
  }

  useEffect(() => {
    rafraichir()
    envoyer()
    const haut = () => { setEnLigne(true); envoyer() }
    const bas = () => setEnLigne(false)
    window.addEventListener('online', haut)
    window.addEventListener('offline', bas)
    const t = setInterval(rafraichir, 5000)
    return () => {
      window.removeEventListener('online', haut)
      window.removeEventListener('offline', bas)
      clearInterval(t)
    }
  }, [])

  if (enLigne && attente === 0 && !info) return null
  const texte = !enLigne
    ? `Hors ligne${attente ? ` · ${attente} signalement(s) en attente` : ''}`
    : attente
      ? `${attente} signalement(s) en attente d'envoi…`
      : info
  return (
    <div style={{ background: enLigne ? '#1b6b4a' : '#7a5a00', color: 'white', padding: '8px 16px', textAlign: 'center', fontWeight: 600 }}>
      {texte}
    </div>
  )
}