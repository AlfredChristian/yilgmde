import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Entete from './components/Entete'
import Accueil from './pages/Accueil'
import Carte from './components/Carte'

export default function App() {
  return (
    <BrowserRouter>
      <Entete />
      <Routes>
        <Route path="/" element={<Accueil />} />
        <Route
          path="/carte"
          element={
            <div style={{ height: 'calc(100vh - 64px)' }}>
              <Carte />
            </div>
          }
        />
      </Routes>
    </BrowserRouter>
  )
}