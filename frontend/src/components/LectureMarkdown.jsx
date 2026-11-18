// Affiche le plan de gestion renvoyé par le serveur (Markdown simple : titres, paragraphes,
// listes, tableaux, gras, blocs de code). Pas de HTML injecté : tout passe par React.

function enLigne(texte) {
  const morceaux = texte.split(/(\*\*[^*]+\*\*|`[^`]+`)/g)
  return morceaux.map((m, i) => {
    if (m.startsWith('**') && m.endsWith('**')) return <strong key={i}>{m.slice(2, -2)}</strong>
    if (m.startsWith('`') && m.endsWith('`')) return <code key={i}>{m.slice(1, -1)}</code>
    return m
  })
}

const cellules = (ligne) => ligne.trim().replace(/^\||\|$/g, '').split('|').map((c) => c.trim())

export default function LectureMarkdown({ texte }) {
  const lignes = texte.split('\n')
  const blocs = []
  let i = 0
  while (i < lignes.length) {
    const l = lignes[i]
    if (!l.trim()) { i++; continue }
    if (l.startsWith('```')) {
      const code = []
      i++
      while (i < lignes.length && !lignes[i].startsWith('```')) code.push(lignes[i++])
      i++
      blocs.push(<pre key={blocs.length}>{code.join('\n')}</pre>)
      continue
    }
    const titre = l.match(/^(#{1,3})\s+(.*)$/)
    if (titre) {
      const Balise = `h${Math.min(titre[1].length + 1, 4)}`
      blocs.push(<Balise key={blocs.length}>{enLigne(titre[2])}</Balise>)
      i++
      continue
    }
    if (l.trim().startsWith('|')) {
      const tableau = []
      while (i < lignes.length && lignes[i].trim().startsWith('|')) tableau.push(lignes[i++])
      const [entete, , ...corps] = tableau
      blocs.push(
        <div key={blocs.length} className="md-tableau">
          <table>
            <thead><tr>{cellules(entete).map((c, k) => <th key={k}>{enLigne(c)}</th>)}</tr></thead>
            <tbody>{corps.map((r, n) => <tr key={n}>{cellules(r).map((c, k) => <td key={k}>{enLigne(c)}</td>)}</tr>)}</tbody>
          </table>
        </div>,
      )
      continue
    }
    if (/^\s*[-*]\s+/.test(l)) {
      const items = []
      while (i < lignes.length && /^\s*[-*]\s+/.test(lignes[i])) items.push(lignes[i++].replace(/^\s*[-*]\s+/, ''))
      blocs.push(<ul key={blocs.length}>{items.map((t, k) => <li key={k}>{enLigne(t)}</li>)}</ul>)
      continue
    }
    const paragraphe = []
    while (i < lignes.length && lignes[i].trim() && !/^(#|\||```|\s*[-*]\s)/.test(lignes[i])) paragraphe.push(lignes[i++])
    blocs.push(<p key={blocs.length}>{enLigne(paragraphe.join(' '))}</p>)
  }
  return <div className="md">{blocs}</div>
}
