import { useEffect, useMemo, useRef, useState } from 'react'
import { Marker, Polyline, Tooltip } from '../carte'
import { iconeCamion } from './iconeCamion'

// Camion qui parcourt un trajet (liste de [lat, lon]) en `duree` ms, puis appelle `onFin`.
// Utilisé sur la carte de la brigade Laabal (D61) : aller vers le dépotoir, retour à la base.

function distance([la1, lo1], [la2, lo2]) {
  const r = Math.PI / 180
  const a = Math.sin(((la2 - la1) * r) / 2) ** 2 + Math.cos(la1 * r) * Math.cos(la2 * r) * Math.sin(((lo2 - lo1) * r) / 2) ** 2
  return 12742000 * Math.asin(Math.sqrt(a))
}

/** Position et sens (vers la gauche ?) à la fraction f du trajet. */
function pointSur(trace, cumul, f) {
  const total = cumul.at(-1)
  const cible = f * total
  let i = cumul.findIndex((c) => c >= cible)
  if (i <= 0) i = 1
  const l = cumul[i] - cumul[i - 1]
  const g = l > 0 ? (cible - cumul[i - 1]) / l : 1
  const [a, b] = [trace[i - 1], trace[i]]
  return { pos: [a[0] + (b[0] - a[0]) * g, a[1] + (b[1] - a[1]) * g], versGauche: b[1] < a[1] }
}

const icones = {}
const icone = (versGauche) => (icones[versGauche] ??= iconeCamion({ couleur: '#0e5a3a', largeur: 50, versGauche }))

export default function CamionEnRoute({ trace, duree, libelle, onFin, onProgres }) {
  const [f, setF] = useState(0)
  const fin = useRef(onFin)
  const progres = useRef(onProgres)
  useEffect(() => { fin.current = onFin; progres.current = onProgres })
  const cumul = useMemo(() => {
    const c = [0]
    for (let i = 1; i < trace.length; i++) c.push(c[i - 1] + distance(trace[i - 1], trace[i]))
    return c
  }, [trace])

  useEffect(() => {
    const reduit = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
    const total = reduit ? 0 : duree
    const debut = performance.now()
    let id
    const pas = (t) => {
      const x = total > 0 ? Math.min(1, (t - debut) / total) : 1
      // départ et arrivée en douceur
      const lisse = x < 0.5 ? 2 * x * x : 1 - (-2 * x + 2) ** 2 / 2
      setF(lisse)
      progres.current?.(lisse)
      if (x < 1) id = requestAnimationFrame(pas)
      else fin.current?.()
    }
    id = requestAnimationFrame(pas)
    return () => cancelAnimationFrame(id)
  }, [trace, duree])

  const { pos, versGauche } = pointSur(trace, cumul, f)
  const fait = trace.slice(0, Math.max(1, cumul.findIndex((c) => c >= f * cumul.at(-1)))).concat([pos])
  return (
    <>
      <Polyline positions={trace} pathOptions={{ color: '#0e5a3a', weight: 4, opacity: 0.25, dashArray: '2 7' }} />
      <Polyline positions={fait} pathOptions={{ color: '#0e5a3a', weight: 4, opacity: 0.8 }} />
      <Marker position={pos} icon={icone(versGauche)} zIndexOffset={2000} keyboard={false}>
        <Tooltip direction="top" permanent>{libelle}</Tooltip>
      </Marker>
    </>
  )
}
