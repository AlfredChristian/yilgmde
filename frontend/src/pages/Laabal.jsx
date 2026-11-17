import { useEffect, useState } from 'react'
import { useAuth } from '../auth/AuthContext'
import { getDepotoirsLaabal, changerStatutDepotoir } from '../api/client'
import Icone from '../components/Icone'
import './Roles.css'

const STATUTS = {
  actif: { texte: 'Actif', classe: 'statut-rejet' },
  surveille: { texte: 'Sous surveillance', classe: 'statut-attente' },
  eradique: { texte: 'Éradiqué', classe: 'statut-ok' },
}

export default function Laabal() {
  const { session } = useAuth()
  const [liste, setListe] = useState(null)
  const [erreur, setErreur] = useState(null)

  useEffect(() => {
    getDepotoirsLaabal().then(setListe).catch((e) => setErreur(e.message))
  }, [])

  async function changer(d, statut) {
    try {
      await changerStatutDepotoir(d.id, statut)
      setListe((l) => l.map((x) => (x.id === d.id ? { ...x, statut } : x)))
    } catch (e) {
      setErreur(e.message)
    }
  }

  if (!liste) return <main className="role-page"><p>{erreur ?? 'Chargement…'}</p></main>

  return (
    <main className="role-page role-page-large">
      <h1>Brigade Laabal</h1>
      <p className="role-intro">{session.nom} · dépotoirs illégaux à traiter</p>
      {erreur && <p className="mod-erreur">{erreur}</p>}

      <div className="role-liste">
        {liste.map((d) => {
          const s = STATUTS[d.statut] ?? { texte: d.statut, classe: 'statut-attente' }
          return (
            <article key={d.id} className="carte">
              <div className="carte-gauche">
                <span className="tuile"><Icone nom="bouclier" taille={28} /></span>
                <span className={`statut ${s.classe}`}>{s.texte}</span>
              </div>
              <div>
                <h3 className="carte-titre">Dépotoir n°{d.id}</h3>
                <p className="carte-texte">
                  Volume {d.volume_estime} · {d.legalite}
                  <br />
                  {d.latitude.toFixed(5)}, {d.longitude.toFixed(5)}
                </p>
                <div className="carte-actions">
                  {d.statut !== 'eradique' && (
                    <button className="btn-contour plein" onClick={() => changer(d, 'eradique')}>
                      <Icone nom="check" taille={18} /> Éradiqué
                    </button>
                  )}
                  {d.statut === 'actif' && (
                    <button className="btn-contour" onClick={() => changer(d, 'surveille')}>
                      <Icone nom="suivi" taille={18} /> Surveiller
                    </button>
                  )}
                </div>
              </div>
            </article>
          )
        })}
      </div>
    </main>
  )
}