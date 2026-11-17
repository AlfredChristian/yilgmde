import { useState } from 'react'
import { Link } from 'react-router-dom'
import Icone from './Icone'
import DrapeauBF from './DrapeauBF'
import { NOM } from '../config/projet'
import './Entete.css'
import { useAuth, ACCUEIL_ROLE } from '../auth/AuthContext'

export default function Entete() {
  const [ouvert, setOuvert] = useState(false)

  const { session, deconnecter } = useAuth()

  return (
    <header className="entete">
      <button
        className="entete-menu"
        onClick={() => setOuvert(!ouvert)}
        aria-label="Menu"
        aria-expanded={ouvert}
      >
        <Icone nom="menu" taille={28} />
      </button>

      <Link to="/" className="entete-nom" onClick={() => setOuvert(false)}>
        {NOM}
      </Link>

      <nav className="entete-liens">
        <Link to="/carte">Carte</Link>

        {session ? (
            <>
                <Link to={ACCUEIL_ROLE[session.role] ?? '/'}>Mon espace</Link>
                <button className="entete-lien-bouton" onClick={deconnecter}>Déconnexion</button>
            </>
        ) : (
            <Link to="/connexion">Connexion</Link>
        )}
      </nav>

      <div className="entete-drapeau">
        <DrapeauBF largeur={40} />
      </div>

      {ouvert && (
        <nav className="entete-panneau">
          <Link to="/" onClick={() => setOuvert(false)}>Accueil</Link>
          <Link to="/carte" onClick={() => setOuvert(false)}>Carte des dépotoirs</Link>
        </nav>
      )}
    </header>
  )
}