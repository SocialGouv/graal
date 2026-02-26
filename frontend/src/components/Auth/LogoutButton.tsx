import { Button } from '@codegouvfr/react-dsfr/Button'

export const LogoutButton = () => {
  const handleLogout = async () => {
    try {
      await fetch(`${import.meta.env.VITE_API_URL || ''}/api/v1/auth/logout`, {
        method: 'POST',
        credentials: 'include'
      })
      // Reload page to clear state
      globalThis.location.href = '/'
    } catch (error) {
      console.error('Logout failed:', error)
      // Still redirect to clear client state
      globalThis.location.href = '/'
    }
  }

  return (
    <Button
      onClick={handleLogout}
      priority="secondary"
      iconId="fr-icon-logout-box-r-line"
    >
      Se déconnecter
    </Button>
  )
}
