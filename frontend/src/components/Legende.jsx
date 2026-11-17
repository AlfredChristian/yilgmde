import './Legende.css'
import { COULEURS_DEPOTOIR, COULEURS_SIGNALEMENT } from '../config/couleurs'

// Les couleurs viennent de config/couleurs.js, comme dans Carte.jsx.
const ELEMENTS = [
  { couleur: COULEURS_DEPOTOIR.actif, texte: 'Dépotoir actif' },
  { couleur: COULEURS_DEPOTOIR.eradique, texte: 'Dépotoir éradiqué' },
  { couleur: COULEURS_SIGNALEMENT.enAttente, texte: 'Signalement en attente', petit: true },
  { couleur: COULEURS_SIGNALEMENT.alerte, texte: 'Signalement avec alerte', petit: true },
  { couleur: COULEURS_SIGNALEMENT.rejete, texte: 'Signalement rejeté', petit: true },
]

export default function Legende() {
  return (
    <aside className="legende">
      <h3>Légende</h3>
      <ul>
        {ELEMENTS.map((e) => (
          <li key={e.texte}>
            <span
              className={e.petit ? 'point point-petit' : 'point'}
              style={{ background: e.couleur }}
            />
            {e.texte}
          </li>
        ))}
      </ul>
    </aside>
  )
}