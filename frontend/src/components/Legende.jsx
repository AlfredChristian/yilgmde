import { COULEURS_DEPOTOIR, COULEURS_SIGNALEMENT } from '../config/couleurs'
import './Legende.css'

function Ligne({ couleur, libelle }) {
  return (
    <li>
      <span className="legende-pastille" style={{ background: couleur }} />
      {libelle}
    </li>
  )
}

export default function Legende() {
  return (
    <div className="legende" role="region" aria-label="Légende de la carte">
      <h3>Dépotoirs</h3>
      <ul>
        <Ligne couleur={COULEURS_DEPOTOIR.actif} libelle="Actif" />
        <Ligne couleur={COULEURS_DEPOTOIR.eradique} libelle="Éradiqué" />
      </ul>
      <h3>Signalements (test)</h3>
      <ul>
        <Ligne couleur={COULEURS_SIGNALEMENT.enAttente} libelle="En attente de revue" />
        <Ligne couleur={COULEURS_SIGNALEMENT.alerte} libelle="Alerte automatique" />
        <Ligne couleur={COULEURS_SIGNALEMENT.rejete} libelle="Rejeté" />
      </ul>
    </div>
  )
}