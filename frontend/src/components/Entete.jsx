import { useState } from 'react'
import { Link, NavLink } from 'react-router-dom'
import Icone from './Icone'
import { NOM } from '../config/projet'
import './Entete.css'
import { useAuth, ACCUEIL_ROLE } from '../auth/AuthContext'

const ESPACES = { admin: 'Espace mairie', chauffeur: 'Ma tournée', laabal: 'Mes interventions' }

export function Marque() {
  return (
    <span className="marque">
      <span className="marque-tissu" aria-hidden="true" />
      {NOM}
    </span>
  )
}

export default function Entete() {
  const [ouvert, setOuvert] = useState(false)
  const { session, deconnecter } = useAuth()
  const fermer = () => setOuvert(false)

  const liens = (
    <>
      <NavLink to="/carte" onClick={fermer}>Carte</NavLink>
      <NavLink to="/signaler" onClick={fermer}>Signaler</NavLink>
      <NavLink to="/suivi" onClick={fermer}>Suivre un signalement</NavLink>
    </>
  )
  const compte = session ? (
    <>
      <NavLink to={ACCUEIL_ROLE[session.role] ?? '/'} className="entete-espace" onClick={fermer}>
        {ESPACES[session.role] ?? 'Mon espace'}
      </NavLink>
      <button className="btn-contour entete-sortie" onClick={() => { fermer(); deconnecter() }}>Se déconnecter</button>
    </>
  ) : (
    <Link to="/connexion" className="btn-contour plein entete-connexion" onClick={fermer}>Se connecter</Link>
  )

  return (
    <header className="entete">
      <Link to="/" className="entete-nom" onClick={fermer} aria-label={`${NOM}, accueil`}>
        <Marque />
      </Link>

      <nav className="entete-liens" aria-label="Navigation principale">{liens}</nav>
      <div className="entete-compte">{compte}</div>

      <button className="entete-menu" onClick={() => setOuvert(!ouvert)} aria-label="Menu" aria-expanded={ouvert}>
        <Icone nom={ouvert ? 'croix' : 'menu'} taille={24} />
      </button>

      {ouvert && (
        <nav className="entete-panneau" aria-label="Menu">
          {liens}
          <div className="entete-panneau-compte">{compte}</div>
        </nav>
      )}
    </header>
  )
}
