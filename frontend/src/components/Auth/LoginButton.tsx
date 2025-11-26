import { Button } from '@codegouvfr/react-dsfr/Button'

export const LoginButton = () => {
  return (
    <Button
      linkProps={{
        href: '/api/v1/auth/login'
      }}
      iconId="fr-icon-account-circle-line"
    >
      Se connecter avec ProConnect
    </Button>
  )
}
