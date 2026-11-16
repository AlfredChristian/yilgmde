import './Legende.css'

// Les couleurs doivent rester identiques à celles de Carte.jsx.
const ELEMENTS = [
  { couleur: '#d62828', texte: 'Dépotoir actif' },
  { couleur: '#2a9d8f', texte: 'Dépotoir éradiqué' },
  { couleur: '#f77f00', texte: 'Signalement en attente', petit: true },
  { couleur: '#7b2cbf', texte: 'Signalement avec alerte', petit: true },
  { couleur: '#6c757d', texte: 'Signalement rejeté', petit: true },
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