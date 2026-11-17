import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Entete from './components/Entete'
import Accueil from './pages/Accueil'
import Signaler from './pages/Signaler'
import Suivi from './pages/Suivi'
import Carte from './components/Carte'

export default function App() {
  return (
    <BrowserRouter>
      <Entete />
      <Routes>
        <Route path="/" element={<Accueil />} />
        <Route path="/signaler" element={<Signaler />} />
        <Route path="/suivi" element={<Suivi />} />
        <Route
          path="/carte"
          element={
            <div style={{ height: 'calc(100vh - 64px)', position: 'relative'}}>
              <Carte />
            </div>
          }
        />
      </Routes>
    </BrowserRouter>
  )
}