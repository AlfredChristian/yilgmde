import { Link } from 'react-router-dom'
import DrapeauBF from './DrapeauBF'
import { Marque } from './Entete'
import './PiedDePage.css'

export default function PiedDePage() {
  return (
    <footer className="pied">
      <div className="bande-tissee" />
      <div className="pied-contenu">
        <div className="pied-marque">
          <Marque />
          <p>Signaler les dépotoirs, organiser la collecte et suivre les interventions dans la commune de Ouagadougou.</p>
        </div>
        <nav className="pied-liens" aria-label="Liens du pied de page">
          <Link to="/signaler">Signaler un dépotoir</Link>
          <Link to="/carte">Carte des dépotoirs</Link>
          <Link to="/suivi">Suivre un signalement</Link>
          <Link to="/connexion">Espace des équipes</Link>
        </nav>
        <div className="pied-commune">
          <span className="pied-pays"><DrapeauBF largeur={28} /> Ouagadougou, Burkina Faso</span>
          <p>Version de démonstration : les données sont fictives mais réalistes.</p>
        </div>
      </div>
      <p className="pied-licences">
        Code sous licence MIT. Données ouvertes sous licence ODbL. Fond de carte et réseau routier : contributeurs OpenStreetMap.
      </p>
    </footer>
  )
}
