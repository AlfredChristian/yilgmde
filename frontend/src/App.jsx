import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { AuthProvider } from './auth/AuthContext'
import RouteProtegee from './components/RouteProtegee'
import Entete from './components/Entete'
import BandeauReseau from './components/BandeauReseau'
import Accueil from './pages/Accueil'
import Carte from './components/Carte'
import Signaler from './pages/Signaler'
import Suivi from './pages/Suivi'
import Connexion from './pages/Connexion'
import Admin from './pages/Admin'
import Plan from './pages/Plan'
import Chauffeur from './pages/Chauffeur'
import Laabal from './pages/Laabal'

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Entete />
        <BandeauReseau />
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
          <Route path="/chauffeur" element={<RouteProtegee roles={['chauffeur']}><Chauffeur /></RouteProtegee>} />
          <Route path="/laabal" element={<RouteProtegee roles={['laabal']}><Laabal /></RouteProtegee>} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}