import { Link } from 'react-router-dom'
import Icone from '../components/Icone'
import { NOM, SLOGAN } from '../config/projet'
import './Accueil.css'

const SERVICES = [
  { icone: 'carte', titre: 'Carte des dépotoirs', texte: 'Voir les dépotoirs vérifiés de la ville.', lien: '/carte' },
  { icone: 'alerte', titre: 'Signaler un dépotoir', texte: 'Sans compte, par la voix ou par écrit.', lien: '/signaler' },
  { icone: 'suivi', titre: 'Suivre mon signalement', texte: 'Entrez votre code de suivi.', lien: '/suivi' },
  { icone: 'mairie', titre: 'Espace mairie', texte: 'Modération, paramètres et plan de gestion.', lien: '/connexion' },
  { icone: 'camion', titre: 'Espace chauffeur', texte: 'Votre tournée et vos arrêts du jour.', lien: '/connexion' },
  { icone: 'bouclier', titre: 'Brigade Laabal', texte: 'Interventions et surveillance.', lien: '/connexion' },
]

const ETAPES = [
  { icone: 'alerte', titre: 'Signaler', texte: 'Placez un dépotoir sur la carte en quelques secondes, sans compte.' },
  { icone: 'bouclier', titre: 'Vérifier', texte: 'Doublons, positions incohérentes, abus : chaque rejet est expliqué.' },
  { icone: 'itineraire', titre: 'Planifier', texte: 'Points de regroupement et tournées, recalculés en quelques secondes.' },
]

export default function Accueil() {
  return (
    <div>
      <section className="hero">
        <div className="hero-contenu">
          <div className="hero-kicker"><span className="hero-point" /> Plateforme municipale de propreté</div>
          <p className="hero-avant">Bienvenue sur</p>
          <h1 className="hero-nom">{NOM}<span>.</span></h1>
          <p className="hero-slogan">{SLOGAN}</p>
          <p className="hero-description">Signalez un dépotoir, suivez les interventions et aidez la mairie à organiser les tournées plus efficacement.</p>

          <div className="hero-actions">
            <Link to="/signaler" className="hero-action hero-action-primaire"><Icone nom="alerte" taille={20} /> Signaler un dépotoir</Link>
            <Link to="/carte" className="hero-action hero-action-secondaire"><Icone nom="carte" taille={20} /> Explorer la carte</Link>
          </div>
          <div className="hero-stats" aria-label="Fonctions principales">
            <span><strong>01</strong> Signalement simple</span>
            <span><strong>02</strong> Vérification terrain</span>
            <span><strong>03</strong> Tournées optimisées</span>
          </div>
        </div>
        <div className="hero-bandeau">
          <span className="hero-bandeau-point" /> Version de démonstration, données fictives pour la présentation
        </div>
      </section>

      <section className="bloc">
        <h2 className="titre-section">Services</h2>
        <div className="grille-services">
          {SERVICES.map((s) => (
            <article key={s.titre} className="carte">
              <div className="carte-gauche">
                <span className="tuile"><Icone nom={s.icone} taille={28} /></span>
              </div>
              <div>
                <h3 className="carte-titre">{s.titre}</h3>
                <p className="carte-texte">{s.texte}</p>
                <Link to={s.lien} className="btn-contour">
                  Ouvrir
                </Link>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="bande-verte">
        <h2 className="titre-section titre-clair">Comment ça marche</h2>
        <div className="grille-etapes">
          {ETAPES.map((e, i) => (
            <article key={e.titre} className="carte">
              <div className="carte-gauche">
                <span className="tuile tuile-jaune"><Icone nom={e.icone} taille={28} /></span>
              </div>
              <div>
                <h3 className="carte-titre">{e.titre}</h3>
                <p className="carte-texte">{e.texte}</p>
              </div>
              <span className="badge">{i + 1}</span>
            </article>
          ))}
        </div>
      </section>

      <footer className="pied">
        <div className="pied-trait" />
        <p className="pied-nom">{NOM}</p>
        <p>Code libre MIT - Données cartographiques © contributeurs OpenStreetMap</p>
      </footer>
    </div>
  )
}