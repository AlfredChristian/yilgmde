import { useState } from 'react'
import { Link } from 'react-router-dom'
import { getSuivi } from '../api/client'
import './Suivi.css'

// [H] libelles a completer selon le modele de donnees
const STATUTS = {
  en_attente_revue: { titre: 'En cours de vérification', classe: 'attente' },
  verifie: { titre: 'Vérifié : le dépotoir est sur la carte', classe: 'ok' },
  rejete_auto: { titre: 'Non retenu automatiquement', classe: 'rejet' },
  rejete: { titre: 'Non retenu', classe: 'rejet' },
}

export default function Suivi() {
  const [code, setCode] = useState('')
  const [resultat, setResultat] = useState(null)
  const [erreur, setErreur] = useState(null)
  const [chargement, setChargement] = useState(false)

  async function chercher(e) {
    e.preventDefault()
    if (!code.trim()) return
    setErreur(null)
    setResultat(null)
    setChargement(true)
    try {
      setResultat(await getSuivi(code))
    } catch (err) {
      setErreur(
        err.introuvable
          ? "Aucun signalement avec ce code. Vérifiez qu'il est bien recopié."
          : `Recherche impossible : ${err.message}. Réessayez.`,
      )
    } finally {
      setChargement(false)
    }
  }

  const info = resultat && (STATUTS[resultat.statut] ?? { titre: resultat.statut, classe: 'attente' })

  return (
    <main className="suivi">
      <h1>Suivre mon signalement</h1>
      <p className="suivi-intro">Entrez le code reçu au moment du signalement.</p>

      <form onSubmit={chercher} className="suivi-form">
        <input
          value={code}
          onChange={(e) => setCode(e.target.value)}
          placeholder="Ex. : K7M-4QD"
          autoCapitalize="characters"
          autoComplete="off"
          aria-label="Code de suivi"
        />
        <button className="btn btn-jaune" disabled={chargement}>
          {chargement ? 'Recherche…' : 'Chercher'}
        </button>
      </form>

      {erreur && <p className="suivi-erreur">{erreur}</p>}

      {resultat && (
        <section className={`suivi-resultat suivi-${info.classe}`}>
          <p className="suivi-code">{resultat.code_suivi}</p>
          <h2>{info.titre}</h2>
          {resultat.motif && <p>Motif : {resultat.motif}</p>}
          {resultat.depotoir_id && (
            <Link to={`/carte?depotoir=${resultat.depotoir_id}`} className="btn btn-vert">Voir sur la carte</Link>
          )}
        </section>
      )}
    </main>
  )
}