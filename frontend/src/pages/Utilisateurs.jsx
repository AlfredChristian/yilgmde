import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getUtilisateurs, creerUtilisateur, modifierUtilisateur, reinitialiserMotDePasse } from '../api/client'
import './Utilisateurs.css'

// Gestion des comptes par l'admin (D49) : creer, renommer, changer de role,
// desactiver / reactiver, fixer un nouveau mot de passe. Pas de suppression :
// le journal d'audit garde l'auteur de chaque action.
const ROLES = [
  { valeur: 'chauffeur', texte: 'Chauffeur' },
  { valeur: 'laabal', texte: 'Brigade Laabal' },
  { valeur: 'admin', texte: 'Administrateur' },
]
const VIDE = { nom: '', email: '', mot_de_passe: '', role: 'chauffeur' }

export default function Utilisateurs() {
  const [comptes, setComptes] = useState(null)
  const [nouveau, setNouveau] = useState(VIDE)
  const [erreur, setErreur] = useState(null)
  const [message, setMessage] = useState(null)
  const [enCours, setEnCours] = useState(null) // id du compte (ou 'nouveau') en cours d'enregistrement
  const [edition, setEdition] = useState({}) // id -> { nom } ou { mot_de_passe }

  useEffect(() => {
    getUtilisateurs().then(setComptes).catch((e) => setErreur(e.message))
  }, [])

  async function agir(id, action, succes) {
    setEnCours(id)
    setErreur(null)
    setMessage(null)
    try {
      const r = await action()
      if (r && id !== 'nouveau') setComptes((cs) => cs.map((c) => (c.id === id ? { ...c, ...r } : c)))
      setMessage(succes)
      return true
    } catch (e) {
      setErreur(e.message)
      return false
    } finally {
      setEnCours(null)
    }
  }

  async function creer(e) {
    e.preventDefault()
    let cree = null
    const ok = await agir('nouveau', async () => (cree = await creerUtilisateur(nouveau)), `Compte créé pour ${nouveau.nom}.`)
    if (ok) {
      setComptes((cs) => [...cs, cree])
      setNouveau(VIDE)
    }
  }

  function editer(id, champ, valeur) {
    setEdition((ed) => ({ ...ed, [id]: { ...(ed[id] ?? {}), [champ]: valeur } }))
  }

  function fermer(id) {
    setEdition((ed) => {
      const copie = { ...ed }
      delete copie[id]
      return copie
    })
  }

  async function renommer(c) {
    const nom = edition[c.id]?.nom?.trim()
    if (!nom) return
    if (await agir(c.id, () => modifierUtilisateur(c.id, { nom }), 'Nom modifié.')) fermer(c.id)
  }

  async function changerMotDePasse(c) {
    const mdp = edition[c.id]?.mot_de_passe ?? ''
    if (await agir(c.id, () => reinitialiserMotDePasse(c.id, mdp), `Nouveau mot de passe enregistré pour ${c.nom}. Transmettez-le-lui.`)) fermer(c.id)
  }

  if (!comptes) return <main className="admin"><p>{erreur ?? 'Chargement…'}</p></main>

  const actifs = comptes.filter((c) => c.actif).length
  return (
    <main className="admin">
      <p><Link to="/admin" className="btn-contour">Retour à l’espace mairie</Link></p>
      <h1>Comptes</h1>
      <p className="admin-intro">
        {comptes.length} comptes, dont {actifs} actifs. Un compte désactivé ne peut plus se connecter
        et perd ses tournées affectées ; il peut être réactivé.
      </p>

      {erreur && <p className="mod-erreur" role="alert">{erreur}</p>}
      {message && <p className="util-message" role="status">{message}</p>}

      <section className="carte util-bloc">
        <h2 className="carte-titre">Nouveau compte</h2>
        <form className="util-form" onSubmit={creer}>
          <label>Nom<input value={nouveau.nom} required maxLength={100} onChange={(e) => setNouveau({ ...nouveau, nom: e.target.value })} /></label>
          <label>E-mail<input type="email" value={nouveau.email} required onChange={(e) => setNouveau({ ...nouveau, email: e.target.value })} /></label>
          <label>Mot de passe (8 caractères min.)
            <input type="text" value={nouveau.mot_de_passe} required minLength={8} autoComplete="new-password"
              onChange={(e) => setNouveau({ ...nouveau, mot_de_passe: e.target.value })} />
          </label>
          <label>Rôle
            <select value={nouveau.role} onChange={(e) => setNouveau({ ...nouveau, role: e.target.value })}>
              {ROLES.map((r) => <option key={r.valeur} value={r.valeur}>{r.texte}</option>)}
            </select>
          </label>
          <button className="btn-contour plein" disabled={enCours === 'nouveau'}>
            {enCours === 'nouveau' ? 'Création…' : 'Créer le compte'}
          </button>
        </form>
      </section>

      <section className="carte util-bloc">
        <h2 className="carte-titre">Comptes existants</h2>
        <div className="util-tableau-wrap">
          <table className="util-tableau">
            <thead><tr><th>Nom</th><th>E-mail</th><th>Rôle</th><th>Statut</th><th>Actions</th></tr></thead>
            <tbody>
              {comptes.map((c) => {
                const ed = edition[c.id]
                const occupe = enCours === c.id
                return (
                  <tr key={c.id} className={c.actif ? '' : 'util-inactif'}>
                    <td>
                      {ed?.nom !== undefined ? (
                        <span className="util-ligne">
                          <input value={ed.nom} maxLength={100} onChange={(e) => editer(c.id, 'nom', e.target.value)} aria-label="Nouveau nom" />
                          <button className="btn-contour" disabled={occupe} onClick={() => renommer(c)}>OK</button>
                          <button className="btn-contour" onClick={() => fermer(c.id)}>Annuler</button>
                        </span>
                      ) : c.nom}
                    </td>
                    <td>{c.email}</td>
                    <td>
                      <select value={c.role} disabled={occupe} aria-label={`Rôle de ${c.nom}`}
                        onChange={(e) => agir(c.id, () => modifierUtilisateur(c.id, { role: e.target.value }), 'Rôle modifié.')}>
                        {ROLES.map((r) => <option key={r.valeur} value={r.valeur}>{r.texte}</option>)}
                      </select>
                    </td>
                    <td><span className={c.actif ? 'statut-ok' : 'statut-rejet'}>{c.actif ? 'Actif' : 'Désactivé'}</span></td>
                    <td>
                      {ed?.mot_de_passe !== undefined ? (
                        <span className="util-ligne">
                          <input type="text" value={ed.mot_de_passe} minLength={8} placeholder="nouveau mot de passe"
                            autoComplete="new-password" onChange={(e) => editer(c.id, 'mot_de_passe', e.target.value)} aria-label="Nouveau mot de passe" />
                          <button className="btn-contour" disabled={occupe || ed.mot_de_passe.length < 8} onClick={() => changerMotDePasse(c)}>OK</button>
                          <button className="btn-contour" onClick={() => fermer(c.id)}>Annuler</button>
                        </span>
                      ) : (
                        <span className="util-ligne">
                          <button className="btn-contour" onClick={() => editer(c.id, 'nom', c.nom)}>Renommer</button>
                          <button className="btn-contour" onClick={() => editer(c.id, 'mot_de_passe', '')}>Mot de passe</button>
                          <button className="btn-contour" disabled={occupe}
                            onClick={() => agir(c.id, () => modifierUtilisateur(c.id, { actif: !c.actif }), c.actif ? `${c.nom} est désactivé.` : `${c.nom} est réactivé.`)}>
                            {c.actif ? 'Désactiver' : 'Réactiver'}
                          </button>
                        </span>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  )
}
