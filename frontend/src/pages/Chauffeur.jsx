import { useEffect, useState } from 'react'
import { useAuth } from '../auth/AuthContext'
import { getTournee, marquerArret } from '../api/client'
import Icone from '../components/Icone'
import './Roles.css'

export default function Chauffeur() {
  const { session } = useAuth()
  const [tournee, setTournee] = useState(null)
  const [erreur, setErreur] = useState(null)

  const [charge, setCharge] = useState(false)

  useEffect(() => {
    getTournee().then(setTournee).catch((e) => setErreur(e.message)).finally(() => setCharge(true))
  }, [])

  // Un arret coche ne se decoche pas (le serveur garde la trace du passage).
  async function cocher(a) {
    try {
      await marquerArret(a)
      setTournee((t) => ({ ...t, arrets: t.arrets.map((x) => (x.ordre === a.ordre ? { ...x, statut: 'effectue' } : x)) }))
    } catch (e) {
      setErreur(e.message)
    }
  }

  if (!tournee) {
    const texte = !charge ? 'Chargement…' : erreur ?? "Aucune tournée ne vous est affectée aujourd'hui. Demandez à l'administrateur."
    return <main className="role-page"><p>{texte}</p></main>
  }
  const faits = tournee.arrets.filter((a) => a.statut === 'effectue').length

  return (
    <main className="role-page">
      <h1>Ma tournée</h1>
      <p className="role-intro">
        {session.nom} · {tournee.camion_id} · {tournee.distance_km} km · {tournee.duree_min} min
        <br />
        {faits} / {tournee.arrets.length} arrêts effectués
      </p>
      {erreur && <p className="mod-erreur">{erreur}</p>}

      <div className="role-liste">
        {tournee.arrets.map((a) => {
          const fait = a.statut === 'effectue'
          return (
            <article key={a.ordre} className="carte">
              <div className="carte-gauche">
                <span className={fait ? 'tuile' : 'tuile tuile-jaune'}>
                  <Icone nom={fait ? 'check' : 'camion'} taille={28} />
                </span>
                <span className={fait ? 'statut statut-ok' : 'statut statut-attente'}>
                  {fait ? 'Effectué' : 'À faire'}
                </span>
              </div>
              <div>
                <h3 className="carte-titre">{a.nom}</h3>
                <p className="carte-texte">{a.latitude.toFixed(5)}, {a.longitude.toFixed(5)}</p>
                <div className="carte-actions">
                  {!fait && (
                    <button className="btn-contour plein" onClick={() => cocher(a)}>
                      <Icone nom="check" taille={18} /> Marquer effectué
                    </button>
                  )}
                  <a
                    className="btn-contour"
                    target="_blank"
                    rel="noreferrer"
                    href={`https://www.openstreetmap.org/directions?to=${a.latitude},${a.longitude}`}
                  >
                    <Icone nom="itineraire" taille={18} /> Itinéraire
                  </a>
                </div>
              </div>
              <span className="badge">{a.ordre}</span>
            </article>
          )
        })}
      </div>
    </main>
  )
}