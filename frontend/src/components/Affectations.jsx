import { useMemo, useState } from 'react'

// Écran des affectations, à la place de la carte du plan. Les rotations d'un même camion le
// même jour sont regroupées : un chauffeur conduit un camion pour la journée, on lui affecte
// donc toutes ses rotations d'un coup. Les tournées Laabal sont affectées une par une.
export default function Affectations({ tournees, utilisateurs, onAffecter, onRetour }) {
  const [onglet, setOnglet] = useState('collecte')
  const [jour, setJour] = useState('tous')
  const [seulementLibres, setSeulementLibres] = useState(false)
  const [choix, setChoix] = useState({})
  const [enCours, setEnCours] = useState(null)
  const [message, setMessage] = useState(null)

  const chauffeurs = utilisateurs.filter((u) => u.role === 'chauffeur')
  const brigades = utilisateurs.filter((u) => u.role === 'laabal')
  const nom = (id) => utilisateurs.find((u) => u.id === id)?.nom

  const groupes = useMemo(() => {
    const parCle = new Map()
    for (const t of tournees) {
      const cle = t.type === 'collecte' ? `c-${t.camion_id}-${t.jour ?? 1}` : `l-${t.id}`
      if (!parCle.has(cle)) parCle.set(cle, { cle, type: t.type, camion: t.camion_id, brigade: t.brigade, jour: t.jour ?? 1, tournees: [] })
      parCle.get(cle).tournees.push(t)
    }
    return [...parCle.values()].map((g) => {
      const agents = [...new Set(g.tournees.map((t) => t.affectee_a).filter(Boolean))]
      return {
        ...g,
        arrets: g.tournees.reduce((s, t) => s + t.arrets.length, 0),
        km: Math.round(g.tournees.reduce((s, t) => s + t.distance_km, 0) * 10) / 10,
        heures: Math.round((g.tournees.reduce((s, t) => s + t.duree_min, 0) / 60) * 10) / 10,
        agents,
        complet: g.tournees.every((t) => t.affectee_a),
      }
    }).sort((a, b) => a.jour - b.jour || String(a.camion ?? a.brigade).localeCompare(String(b.camion ?? b.brigade), 'fr', { numeric: true }))
  }, [tournees])

  const jours = [...new Set(groupes.filter((g) => g.type === 'collecte').map((g) => g.jour))].sort()
  const visibles = groupes.filter((g) => g.type === onglet && (onglet !== 'collecte' || jour === 'tous' || g.jour === Number(jour)) && (!seulementLibres || !g.complet))
  const total = groupes.filter((g) => g.type === onglet).length
  const faits = groupes.filter((g) => g.type === onglet && g.complet).length

  async function affecter(g) {
    const id = Number(choix[g.cle])
    if (!id) return
    setEnCours(g.cle)
    setMessage(null)
    try {
      for (const t of g.tournees) await onAffecter(t, id)
      setChoix((c) => ({ ...c, [g.cle]: '' }))
      setMessage(`${titre(g)} affecté à ${nom(id)}.`)
    } finally {
      setEnCours(null)
    }
  }

  const titre = (g) => (g.type === 'collecte' ? `${g.camion}, jour ${g.jour}` : `Brigade Laabal ${g.brigade ?? 1}`)
  const candidats = onglet === 'collecte' ? chauffeurs : brigades

  return (
    <section className="affectations">
      <header className="affectations-tete">
        <div>
          <h2>Affecter les tournées</h2>
          <p>{faits} sur {total} {onglet === 'collecte' ? 'journées de camion' : 'tournées Laabal'} affectées</p>
        </div>
        <button className="btn-contour" onClick={onRetour}>Revenir à la carte</button>
      </header>

      <div className="affectations-filtres">
        <div className="segment" role="tablist" aria-label="Type de tournée">
          <button role="tab" aria-selected={onglet === 'collecte'} className={onglet === 'collecte' ? 'actif' : ''} onClick={() => setOnglet('collecte')}>Collecte</button>
          <button role="tab" aria-selected={onglet === 'intervention'} className={onglet === 'intervention' ? 'actif' : ''} onClick={() => setOnglet('intervention')}>Brigade Laabal</button>
        </div>
        {onglet === 'collecte' && jours.length > 1 && (
          <div className="segment" role="group" aria-label="Jour du passage">
            <button className={jour === 'tous' ? 'actif' : ''} onClick={() => setJour('tous')}>Tous les jours</button>
            {jours.map((j) => (
              <button key={j} className={jour === String(j) ? 'actif' : ''} onClick={() => setJour(String(j))}>Jour {j}</button>
            ))}
          </div>
        )}
        <label className="affectations-case">
          <input type="checkbox" checked={seulementLibres} onChange={(e) => setSeulementLibres(e.target.checked)} />
          Non affectées seulement
        </label>
      </div>

      {message && <p className="util-message" role="status">{message}</p>}
      {candidats.length === 0 && (
        <p className="mod-alerte">
          Aucun compte {onglet === 'collecte' ? 'chauffeur' : 'Laabal'} actif. Créez-en un dans la page Comptes.
        </p>
      )}

      <div className="affectations-grille">
        {visibles.map((g) => (
          <article key={g.cle} className={`affectation${g.complet ? ' affectation-faite' : ''}`}>
            <div className="affectation-haut">
              <h3>{titre(g)}</h3>
              <span className={g.complet ? 'affectation-etat ok' : 'affectation-etat'}>{g.complet ? 'Affectée' : 'À affecter'}</span>
            </div>
            <ul className="puces">
              {g.type === 'collecte' && <li className="puce">{g.tournees.length} rotation{g.tournees.length > 1 ? 's' : ''}</li>}
              <li className="puce">{g.arrets} arrêts</li>
              <li className="puce">{g.km} km</li>
              <li className="puce">{g.heures} h</li>
            </ul>
            <p className="affectation-agent">
              {g.agents.length ? `Agent : ${g.agents.map(nom).filter(Boolean).join(', ')}` : 'Aucun agent pour le moment'}
            </p>
            <div className="affectation-action">
              <select value={choix[g.cle] ?? ''} onChange={(e) => setChoix((c) => ({ ...c, [g.cle]: e.target.value }))}
                aria-label={`Agent pour ${titre(g)}`} disabled={!candidats.length}>
                <option value="">{g.complet ? 'Changer d’agent' : 'Choisir un agent'}</option>
                {candidats.map((u) => <option key={u.id} value={u.id}>{u.nom}</option>)}
              </select>
              <button className="btn-contour plein" disabled={!choix[g.cle] || enCours === g.cle} onClick={() => affecter(g)}>
                {enCours === g.cle ? 'Affectation…' : 'Affecter'}
              </button>
            </div>
          </article>
        ))}
        {visibles.length === 0 && <p className="carte-texte">Aucune tournée ne correspond à ces filtres.</p>}
      </div>
    </section>
  )
}
