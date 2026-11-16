import { Link } from 'react-router-dom'
import Icone from '../components/Icone'
import { NOM, SLOGAN } from '../config/projet'
import './Accueil.css'

const SERVICES = [
  { icone: 'carte', titre: 'Carte des dépotoirs', lien: '/carte' },
  { icone: 'alerte', titre: 'Signaler un dépotoir' },
  { icone: 'suivi', titre: 'Suivre mon signalement' },
  { icone: 'mairie', titre: 'Espace mairie' },
  { icone: 'camion', titre: 'Espace chauffeur' },
  { icone: 'bouclier', titre: 'Brigade Laabal' },
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
        <div className="hero-contenu apparait">
          <p className="hero-avant">Bienvenue sur</p>
          <h1 className="hero-nom">{NOM}</h1>
          <p className="hero-slogan">{SLOGAN}</p>

          <Link to="/carte" className="hero-barre">
            <span className="hero-barre-texte">Où sont les dépotoirs de Ouagadougou ?</span>
            <span className="hero-barre-bouton">
              <Icone nom="carte" taille={28} />
            </span>
          </Link>
        </div>
        <div className="hero-bandeau">
          Version de démonstration · les données affichées sont fictives
        </div>
      </section>

      <section className="bloc">
        <h2 className="titre-section">Services</h2>
        <div className="grille-services">
          {SERVICES.map((s) => {
            const contenu = (
              <>
                <Icone nom={s.icone} taille={44} />
                <span className="service-titre">{s.titre}</span>
                {!s.lien && <span className="service-bientot">Bientôt</span>}
              </>
            )
            return s.lien ? (
              <Link key={s.titre} to={s.lien} className="service">
                {contenu}
              </Link>
            ) : (
              <div key={s.titre} className="service service-inactif">
                {contenu}
              </div>
            )
          })}
        </div>
      </section>

      <section className="bande-verte">
        <h2 className="titre-section titre-clair">Comment ça marche</h2>
        <div className="grille-etapes">
          {ETAPES.map((e) => (
            <article key={e.titre} className="etape">
              <Icone nom={e.icone} taille={32} />
              <div>
                <h3>{e.titre}</h3>
                <p>{e.texte}</p>
              </div>
            </article>
          ))}
        </div>
      </section>

      <footer className="pied">
        <div className="pied-trait" />
        <p className="pied-nom">{NOM}</p>
        <p>Code libre (Apache-2.0) · Données cartographiques © contributeurs OpenStreetMap</p>
      </footer>
    </div>
  )
}