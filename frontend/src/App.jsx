import { lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom'
import { AuthProvider } from './auth/AuthContext'
import RouteProtegee from './components/RouteProtegee'
import Entete from './components/Entete'
import BandeauReseau from './components/BandeauReseau'
import PiedDePage from './components/PiedDePage'
import Accueil from './pages/Accueil'
import Introuvable from './pages/Introuvable'

// Chaque page est chargée quand on l'ouvre (D66) : le citoyen qui signale ne télécharge
// ni le plan de gestion ni les suivis. Toutes restent disponibles hors ligne (service worker).
const Carte = lazy(() => import('./components/Carte'))
const Signaler = lazy(() => import('./pages/Signaler'))
const Suivi = lazy(() => import('./pages/Suivi'))
const Connexion = lazy(() => import('./pages/Connexion'))
const Admin = lazy(() => import('./pages/Admin'))
const Plan = lazy(() => import('./pages/Plan'))
const Chauffeur = lazy(() => import('./pages/Chauffeur'))
const Laabal = lazy(() => import('./pages/Laabal'))
const Utilisateurs = lazy(() => import('./pages/Utilisateurs'))
const ModerationDetail = lazy(() => import('./pages/ModerationDetail'))

function Chargement() {
  return <p className="page-chargement" role="status"><span className="role-spinner" /> Chargement…</p>
}

// Le pied de page accompagne les pages publiques ; les cartes plein écran et les espaces de travail s'en passent.
function PiedSiPublic() {
  const { pathname } = useLocation()
  return ['/', '/suivi', '/connexion'].includes(pathname) ? <PiedDePage /> : null
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Entete />
        <BandeauReseau />
        <Suspense fallback={<Chargement />}>
        <Routes>
          <Route path="/" element={<Accueil />} />
          <Route
            path="/carte"
            element={
              <div style={{ height: 'calc(100vh - 64px)', position: 'relative' }}>
                <Carte />
              </div>
            }
          />
          <Route path="/signaler" element={<Signaler />} />
          <Route path="/suivi" element={<Suivi />} />
          <Route path="/connexion" element={<Connexion />} />
          <Route
            path="/admin"
            element={
              <RouteProtegee roles={['admin']}>
                <Admin />
              </RouteProtegee>
            }
          />
          <Route 
            path="/admin/plan" 
            element={
              <RouteProtegee roles={['admin']}>
                <Plan />
              </RouteProtegee>
            } 
          />
          <Route path="/admin/signalements/:id" element={<RouteProtegee roles={['admin']}><ModerationDetail /></RouteProtegee>} />
          <Route path="/admin/utilisateurs" element={<RouteProtegee roles={['admin']}><Utilisateurs /></RouteProtegee>} />
          <Route path="/chauffeur" element={<RouteProtegee roles={['chauffeur']}><Chauffeur /></RouteProtegee>} />
          <Route path="/laabal" element={<RouteProtegee roles={['laabal']}><Laabal /></RouteProtegee>} />
          <Route path="*" element={<Introuvable />} />
        </Routes>
        </Suspense>
        <PiedSiPublic />
      </AuthProvider>
    </BrowserRouter>
  )
}