import { Button } from '@codegouvfr/react-dsfr/Button'

export const LoginButton = () => {
  return (
    <Button
      linkProps={{
        href: `${import.meta.env.VITE_API_URL}/api/v1/auth/login`
      }}
      iconId="fr-icon-account-circle-line"
    >
      Se connecter avec ProConnect
    </Button>
  )
}
