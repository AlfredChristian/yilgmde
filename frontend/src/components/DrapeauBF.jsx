// Drapeau du Burkina Faso : rouge, vert, étoile jaune.
export default function DrapeauBF({ largeur = 36 }) {
  return (
    <svg
      width={largeur}
      height={(largeur * 2) / 3}
      viewBox="0 0 30 20"
      role="img"
      aria-label="Drapeau du Burkina Faso"
      style={{ borderRadius: 3, boxShadow: '0 0 0 1px rgba(0,0,0,0.15)' }}
    >
      <rect width="30" height="10" fill="#ef2b2d" />
      <rect y="10" width="30" height="10" fill="#009e49" />
      <polygon
        fill="#fcd116"
        points="15,5.8 15.94,8.71 18.99,8.7 16.52,10.49 17.47,13.4 15,11.6 12.53,13.4 13.48,10.49 11.01,8.7 14.06,8.71"
      />
    </svg>
  )
}