import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { MapContainer, TileLayer, CircleMarker, Circle, Tooltip } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import { getFileModeration, getSignalementDetail, validerSignalement, rejeterSignalement } from '../api/client'
import Icone from '../components/Icone'
import './Admin.css'

// Fiche d'un signalement (D54) : on examine tout (lieu, photo, voix, description, voisinage,
// fiabilité de l'appareil) avant de valider, fusionner avec un dépotoir connu ou rejeter.

const MOTIFS = ['Photo sans rapport', 'Position incohérente', 'Doublon', 'Pas un dépotoir', 'Autre']
const TYPES = { menager: 'Ordures ménagères', organique: 'Déchets organiques', plastiques: 'Plastiques', gravats: 'Gravats', encombrants: 'Encombrants', autre: 'Autre' }
const STATUTS_DEPOTOIR = { actif: 'actif', intervention_planifiee: 'intervention en cours', eradique: 'éradiqué', sous_surveillance: 'sous surveillance', classe: 'classé' }
const STATUTS_SIGNALEMENT = { en_attente_revue: 'à vérifier', verifie: 'validé', rejete: 'rejeté', rejete_auto: 'rejeté automatiquement', soumis: 'reçu' }

const dateHeure = (iso) => (iso ? new Date(iso).toLocaleString('fr-FR', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }) : null)

// Alertes de la vérification automatique, regroupées (le détail est dans « À proximité »).
function resumeAlertes(alertes) {
  const compte = (code) => alertes.filter((a) => a.startsWith(`${code}:`)).length
  const doublons = compte('doublon_probable')
  const depotoirs = compte('depotoir_proche')
  const autres = alertes.filter((a) => !a.startsWith('doublon_probable:') && !a.startsWith('depotoir_proche:'))
  return [
    doublons && `Doublon possible : ${doublons} autre${doublons > 1 ? 's' : ''} signalement${doublons > 1 ? 's' : ''} envoyé${doublons > 1 ? 's' : ''} tout près`,
    depotoirs && `${depotoirs} dépotoir${depotoirs > 1 ? 's' : ''} déjà connu${depotoirs > 1 ? 's' : ''} tout près : pensez à rattacher`,
    ...autres,
  ].filter(Boolean)
}

function Ligne({ titre, children }) {
  return children == null || children === '' ? null : (
    <div className="fiche-ligne"><dt>{titre}</dt><dd>{children}</dd></div>
  )
}

export default function ModerationDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [s, setS] = useState(null)
  const [suivantId, setSuivantId] = useState(null)
  const [erreur, setErreur] = useState(null)
  const [occupe, setOccupe] = useState(false)
  const [rejet, setRejet] = useState(false)
  const [motif, setMotif] = useState(MOTIFS[0])
  const [fusion, setFusion] = useState('')

  useEffect(() => {
    let actif = true
    setS(null)
    setErreur(null)
    setRejet(false)
    setFusion('')
    getSignalementDetail(Number(id))
      .then((d) => {
        if (!actif) return
        setS(d)
        const illegal = d.depotoirs_proches.find((x) => x.legalite !== 'officiel')
        if (illegal && illegal.distance_m <= 100) setFusion(String(illegal.id))   // suggestion, à confirmer
      })
      .catch((e) => actif && setErreur(e.message))
    getFileModeration()
      .then((file) => {
        if (!actif) return
        const i = file.findIndex((x) => x.id === Number(id))
        setSuivantId(file[i + 1]?.id ?? file.find((x) => x.id !== Number(id))?.id ?? null)
      })
      .catch(() => {})
    return () => { actif = false }
  }, [id])

  async function decider(action) {
    setOccupe(true)
    setErreur(null)
    try {
      await action()
      navigate(suivantId ? `/admin/signalements/${suivantId}` : '/admin', { replace: true })
    } catch (e) {
      setErreur(e.message)
    } finally {
      setOccupe(false)
    }
  }

  if (!s) {
    return (
      <main className="admin">
        <p><Link to="/admin" className="btn-contour">Retour à la file</Link></p>
        <p>{erreur ?? 'Chargement du signalement…'}</p>
      </main>
    )
  }

  const enAttente = s.statut === 'en_attente_revue'
  const c = s.contributeur
  const depotoirFusion = s.depotoirs_proches.find((x) => String(x.id) === fusion)

  return (
    <main className="admin fiche">
      <p className="fiche-nav">
        <Link to="/admin" className="btn-contour">Retour à la file</Link>
        {suivantId && <Link to={`/admin/signalements/${suivantId}`} className="btn-contour">Signalement suivant</Link>}
      </p>
      <h1>Signalement n°{s.id}</h1>
      <p className="admin-intro">
        {TYPES[s.type_dechet] ?? s.type_dechet}, volume {s.volume_estime}
        {s.secteur && `, ${s.secteur.toLowerCase()}${s.arrondissement ? ` de l’arrondissement ${s.arrondissement}` : ''}`}
      </p>

      {erreur && <p className="mod-erreur" role="alert">{erreur}</p>}

      <div className="fiche-grille">
        <section className="carte fiche-bloc fiche-carte">
          <h2 className="carte-titre">Emplacement</h2>
          <div className="fiche-carte-map">
            <MapContainer center={[s.latitude, s.longitude]} zoom={17} style={{ height: '100%', width: '100%' }}>
              <TileLayer attribution="&copy; OpenStreetMap" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
              <Circle center={[s.latitude, s.longitude]} radius={300} pathOptions={{ color: '#8fa89a', weight: 1, fillOpacity: 0.04, dashArray: '4 4' }} />
              {s.signalements_proches.map((v) => (
                <CircleMarker key={`s${v.id}`} center={[v.latitude, v.longitude]} radius={5}
                  pathOptions={{ color: '#ffffff', weight: 1.5, fillColor: '#2a78d6', fillOpacity: 1 }}>
                  <Tooltip>Signalement n°{v.id}, {STATUTS_SIGNALEMENT[v.statut] ?? v.statut}, à {v.distance_m} m</Tooltip>
                </CircleMarker>
              ))}
              {s.depotoirs_proches.map((d) => (
                <CircleMarker key={`d${d.id}`} center={[d.latitude, d.longitude]} radius={8}
                  pathOptions={{ color: '#ffffff', weight: 2, fillColor: d.legalite === 'officiel' ? '#1b6b4a' : '#d62828', fillOpacity: 1 }}>
                  <Tooltip>{d.legalite === 'officiel' ? 'Centre de collecte' : 'Dépotoir'} n°{d.id}, {STATUTS_DEPOTOIR[d.statut] ?? d.statut}, à {d.distance_m} m</Tooltip>
                </CircleMarker>
              ))}
              <CircleMarker center={[s.latitude, s.longitude]} radius={11}
                pathOptions={{ color: '#0b0b0b', weight: 3, fillColor: '#eda100', fillOpacity: 1 }}>
                <Tooltip permanent direction="top">Ce signalement</Tooltip>
              </CircleMarker>
            </MapContainer>
          </div>
          <p className="fiche-legende">
            <span><i style={{ background: '#eda100' }} /> ce signalement</span>
            <span><i style={{ background: '#d62828' }} /> dépotoir connu</span>
            <span><i style={{ background: '#1b6b4a' }} /> centre de collecte</span>
            <span><i style={{ background: '#2a78d6' }} /> autre signalement</span>
            <span>cercle : 300 m</span>
          </p>
          <p className="carte-texte">
            {s.latitude.toFixed(5)}, {s.longitude.toFixed(5)}.{' '}
            <a href={`https://www.openstreetmap.org/?mlat=${s.latitude}&mlon=${s.longitude}#map=18/${s.latitude}/${s.longitude}`} target="_blank" rel="noreferrer">
              ouvrir dans OpenStreetMap
            </a>
          </p>
        </section>

        <section className="carte fiche-bloc">
          <h2 className="carte-titre">Ce qu'a envoyé le citoyen</h2>
          {s.photo_url ? (
            <img src={s.photo_url} alt={`Photo du signalement n°${s.id}`} className="fiche-photo" />
          ) : (
            <p className="carte-texte fiche-vide">Pas de photo.</p>
          )}
          {s.photo_masquee && <p className="carte-note">Visages et plaques floutés automatiquement.</p>}
          {s.audio_url && (
            <div className="fiche-audio">
              <span className="carte-note">Note vocale</span>
              <audio controls src={s.audio_url} />
            </div>
          )}
          <dl className="fiche-infos">
            <Ligne titre="Description">{s.description || <span className="fiche-vide">aucune</span>}</Ligne>
            <Ligne titre="Type">{TYPES[s.type_dechet] ?? s.type_dechet}</Ligne>
            <Ligne titre="Volume">{s.volume_estime}</Ligne>
            <Ligne titre="Reçu le">{dateHeure(s.cree_le)}</Ligne>
            <Ligne titre="Photo prise le">{s.capture_le && s.capture_le !== s.cree_le ? `${dateHeure(s.capture_le)} (envoyé plus tard, hors connexion)` : null}</Ligne>
            <Ligne titre="Score automatique">{s.score_auto == null ? null : `${Math.round(s.score_auto * 100)} %`}</Ligne>
            <Ligne titre="Appareil">
              {c ? `${c.nb_signalements} signalement${c.nb_signalements > 1 ? 's' : ''}, ${c.verifies} validé${c.verifies > 1 ? 's' : ''}, ${c.rejetes} rejeté${c.rejetes > 1 ? 's' : ''}, confiance ${Math.round(c.score_confiance * 100)} %${c.bloque ? ', bloqué' : ''}` : 'inconnu (donnée importée)'}
            </Ligne>
          </dl>
          {resumeAlertes(s.alertes).map((t) => <p key={t} className="mod-alerte">{t}</p>)}
        </section>

        <section className="carte fiche-bloc">
          <h2 className="carte-titre">À proximité (300 m)</h2>
          {s.depotoirs_proches.length === 0 && s.signalements_proches.length === 0 && (
            <p className="carte-texte">Rien de connu autour : c'est probablement un nouveau dépotoir.</p>
          )}
          {s.depotoirs_proches.length > 0 && (
            <ul className="fiche-liste">
              {s.depotoirs_proches.map((d) => (
                <li key={d.id}>
                  <strong>{d.legalite === 'officiel' ? 'Centre de collecte' : 'Dépotoir'} n°{d.id}</strong> à {d.distance_m} m :{' '}
                  {STATUTS_DEPOTOIR[d.statut] ?? d.statut}, volume {d.volume_estime}, {d.nb_signalements} signalement{d.nb_signalements > 1 ? 's' : ''}
                </li>
              ))}
            </ul>
          )}
          {s.signalements_proches.length > 0 && (
            <ul className="fiche-liste">
              {s.signalements_proches.map((v) => (
                <li key={v.id}>
                  <Link to={`/admin/signalements/${v.id}`}>Signalement n°{v.id}</Link> à {v.distance_m} m :{' '}
                  {STATUTS_SIGNALEMENT[v.statut] ?? v.statut}, {TYPES[v.type_dechet] ?? v.type_dechet}, {dateHeure(v.cree_le)}
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="carte fiche-bloc fiche-decision">
          <h2 className="carte-titre">Décision</h2>
          {!enAttente ? (
            <p className="carte-texte">Ce signalement a déjà été traité ({STATUTS_SIGNALEMENT[s.statut] ?? s.statut}).</p>
          ) : !rejet ? (
            <>
              {s.depotoirs_proches.some((d) => d.legalite !== 'officiel') && (
                <label className="fiche-choix">
                  Rattacher à
                  <select value={fusion} onChange={(e) => setFusion(e.target.value)}>
                    <option value="">un nouveau dépotoir</option>
                    {s.depotoirs_proches.filter((d) => d.legalite !== 'officiel').map((d) => (
                      <option key={d.id} value={d.id}>dépotoir n°{d.id} existant ({d.distance_m} m)</option>
                    ))}
                  </select>
                </label>
              )}
              <div className="carte-actions">
                <button className="btn-contour plein" disabled={occupe}
                  onClick={() => decider(() => validerSignalement(s.id, depotoirFusion ? depotoirFusion.id : null))}>
                  <Icone nom="check" taille={18} /> {depotoirFusion ? `Valider et rattacher au n°${depotoirFusion.id}` : 'Valider : nouveau dépotoir'}
                </button>
                <button className="btn-contour danger" disabled={occupe} onClick={() => setRejet(true)}>
                  <Icone nom="croix" taille={18} /> Rejeter
                </button>
              </div>
              <p className="carte-note">
                Valider rend le dépotoir visible sur la carte publique et l'ajoute au prochain plan. Le citoyen voit la décision avec son code de suivi.
              </p>
            </>
          ) : (
            <div className="mod-rejet">
              <label>
                Motif du rejet
                <select value={motif} onChange={(e) => setMotif(e.target.value)}>
                  {MOTIFS.map((m) => <option key={m}>{m}</option>)}
                </select>
              </label>
              <div className="carte-actions">
                <button className="btn-contour danger" disabled={occupe} onClick={() => decider(() => rejeterSignalement(s.id, motif))}>
                  Confirmer le rejet
                </button>
                <button className="btn-contour" disabled={occupe} onClick={() => setRejet(false)}>Annuler</button>
              </div>
            </div>
          )}
        </section>
      </div>
    </main>
  )
}
