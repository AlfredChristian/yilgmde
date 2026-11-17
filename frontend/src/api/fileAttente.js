// File d'attente des signalements, stockee dans IndexedDB (supporte les Blob audio).
const BASE = 'yilgamde'
const TABLE = 'attente'

function ouvrir() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(BASE, 1)
    req.onupgradeneeded = () => req.result.createObjectStore(TABLE, { keyPath: 'cle' })
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error)
  })
}

async function transaction(mode, action) {
  const db = await ouvrir()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(TABLE, mode)
    const res = action(tx.objectStore(TABLE))
    tx.oncomplete = () => resolve(res.result)
    tx.onerror = () => reject(tx.error)
  })
}

// Cle au format accepte par le serveur (id_client : 8 a 64 caracteres A-Za-z0-9_.:-).
export function nouvelleCle() {
  return Date.now() + '-' + Math.random().toString(16).slice(2)
}

// La cle et la date peuvent etre choisies avant le premier essai d'envoi.
export function ajouter(donnees, { cle = nouvelleCle(), creeLe = Date.now() } = {}) {
  return transaction('readwrite', (s) => s.put({ cle, creeLe, donnees })).then(() => cle)
}
export const lister = () => transaction('readonly', (s) => s.getAll())
export const retirer = (cle) => transaction('readwrite', (s) => s.delete(cle))