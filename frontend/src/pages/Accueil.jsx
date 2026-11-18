import { Link } from 'react-router-dom'
import Icone from '../components/Icone'
import CarteOuaga from '../components/CarteOuaga'
import './Accueil.css'

const ACTIONS = [
  { icone: 'alerte', titre: 'Signaler un dépotoir', texte: 'Sans compte. Placez le point, choisissez le type de déchets, ajoutez une photo ou un message vocal.', lien: '/signaler', bouton: 'Signaler' },
  { icone: 'carte', titre: 'Consulter la carte', texte: 'Les dépotoirs vérifiés, ceux qui ont été traités et les centres de collecte de la mairie.', lien: '/carte', bouton: 'Ouvrir la carte' },
  { icone: 'suivi', titre: 'Suivre un signalement', texte: 'Avec le code reçu après l’envoi, voyez si votre signalement a été vérifié et traité.', lien: '/suivi', bouton: 'Suivre' },
]

const PARCOURS = [
  { titre: 'Vous signalez', texte: 'Même sans réseau : l’envoi part dès que la connexion revient.' },
  { titre: 'La mairie vérifie', texte: 'Lieu, photo et signalements voisins sont examinés avant toute décision.' },
  { titre: 'Le plan s’adapte', texte: 'Points de regroupement et tournées sont recalculés sur les vraies rues.' },
  { titre: 'Les équipes interviennent', texte: 'Chauffeurs et brigade Laabal cochent chaque arrêt depuis leur téléphone.' },
]

const EQUIPES = [
  { icone: 'mairie', titre: 'Mairie', texte: 'Vérification des signalements, plan de gestion, suivi de la flotte et des comptes.' },
  { icone: 'camion', titre: 'Chauffeurs', texte: 'La tournée du jour sur la carte et les arrêts à valider un par un.' },
  { icone: 'bouclier', titre: 'Brigade Laabal', texte: 'Les dépotoirs à éradiquer par ordre de priorité, puis leur surveillance.' },
]

export default function Accueil() {
  return (
    <main className="accueil">
      <section className="hero">
        <div className="hero-texte">
          <h1>Signalez un dépotoir. La mairie organise la collecte.</h1>
          <p className="hero-chapo">
            Yilgmdé relie les habitants de Ouagadougou, la mairie et les équipes de terrain. Chaque signalement
            vérifié entre dans les tournées de collecte des 12 arrondissements.
          </p>
          <div className="hero-actions">
            <Link to="/signaler" className="btn btn-primaire hero-bouton"><Icone nom="alerte" taille={20} /> Signaler un dépotoir</Link>
            <Link to="/carte" className="btn btn-secondaire hero-bouton"><Icone nom="carte" taille={20} /> Voir la carte</Link>
          </div>
        </div>
        <div className="hero-carte">
          <CarteOuaga />
        </div>
      </section>

      <section className="accueil-section">
        <h2>Ce que vous pouvez faire</h2>
        <div className="accueil-actions">
          {ACTIONS.map((a) => (
            <article key={a.titre} className="accueil-action">
              <span className="tuile"><Icone nom={a.icone} taille={24} /></span>
              <h3>{a.titre}</h3>
              <p>{a.texte}</p>
              <Link to={a.lien} className="btn-contour">{a.bouton}</Link>
            </article>
          ))}
        </div>
      </section>

      <section className="accueil-section accueil-parcours">
        <h2>D’un signalement à la collecte</h2>
        <ol className="parcours">
          {PARCOURS.map((p) => (
            <li key={p.titre}>
              <h3>{p.titre}</h3>
              <p>{p.texte}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="accueil-section">
        <div className="accueil-equipes-tete">
          <h2>Pour les équipes de la ville</h2>
          <Link to="/connexion" className="btn-contour plein">Se connecter</Link>
        </div>
        <div className="accueil-equipes">
          {EQUIPES.map((e) => (
            <article key={e.titre} className="accueil-equipe">
              <Icone nom={e.icone} taille={22} />
              <div>
                <h3>{e.titre}</h3>
                <p>{e.texte}</p>
              </div>
            </article>
          ))}
        </div>
      </section>
    </main>
  )
}
