import { Link } from 'react-router-dom'

// Adresse inconnue : on dit où aller plutôt que d'afficher une page vide.
export default function Introuvable() {
  return (
    <main className="introuvable">
      <img src={`${import.meta.env.BASE_URL}marque/symbole.png`} alt="" width="96" height="100" />
      <h1>Cette page n’existe pas</h1>
      <p>L’adresse est peut-être incomplète. Vous pouvez signaler un dépotoir, consulter la carte ou revenir à l’accueil.</p>
      <div className="introuvable-actions">
        <Link to="/signaler" className="btn btn-primaire">Signaler un dépotoir</Link>
        <Link to="/carte" className="btn-contour">Voir la carte</Link>
        <Link to="/" className="btn-contour">Accueil</Link>
      </div>
    </main>
  )
}
