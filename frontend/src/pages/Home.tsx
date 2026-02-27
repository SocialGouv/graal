import { fr } from '@codegouvfr/react-dsfr'
import { Alert } from '@codegouvfr/react-dsfr/Alert'
import { Badge } from '@codegouvfr/react-dsfr/Badge'
import { Tile } from '@codegouvfr/react-dsfr/Tile'
import { useNavigate } from 'react-router-dom'
import { DevLoginButtons } from '../components/Auth/DevLoginButtons'
import { LoginButton } from '../components/Auth/LoginButton'
import { LogoutButton } from '../components/Auth/LogoutButton'
import { useAuth } from '../hooks/useAuth'

export const Home = () => {
  const navigate = useNavigate()
  const { user, isAdmin, isLoading, error } = useAuth()

  if (isLoading) {
    return (
      <div className={fr.cx('fr-container', 'fr-py-6w')}>
        <div className={fr.cx('fr-grid-row', 'fr-grid-row--center')}>
          <div className={fr.cx('fr-col-12', 'fr-col-md-10', 'fr-col-lg-8')}>
            <Alert
              severity="info"
              title="Chargement..."
              description="Vérification de votre authentification en cours..."
            />
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className={fr.cx('fr-container', 'fr-py-6w')}>
        <div className={fr.cx('fr-grid-row', 'fr-grid-row--center')}>
          <div className={fr.cx('fr-col-12', 'fr-col-md-10', 'fr-col-lg-8')}>
            <Alert
              severity="error"
              title="Erreur d'authentification"
              description={error}
            />
            <div className={fr.cx('fr-mt-4w')}>
              <LoginButton />
            </div>
            <DevLoginButtons />
          </div>
        </div>
      </div>
    )
  }

  if (!user) {
    return (
      <div className={fr.cx('fr-container', 'fr-py-6w')}>
        <div className={fr.cx('fr-grid-row', 'fr-grid-row--center')}>
          <div className={fr.cx('fr-col-12', 'fr-col-md-10', 'fr-col-lg-8')}>
            <h1 className={fr.cx('fr-mb-2w')}>GRAAL</h1>
            <p className={fr.cx('fr-text--lead', 'fr-mb-4w')}>
              Gestion et Répartition Automatisée des Amendements Législatifs
            </p>
            <Alert
              severity="info"
              title="Authentification requise"
              description="Veuillez vous connecter avec ProConnect pour accéder à l'application."
            />
            <div className={fr.cx('fr-mt-4w')}>
              <LoginButton />
            </div>
            <DevLoginButtons />
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className={fr.cx('fr-container', 'fr-py-6w')}>
      {/* Header with user info and logout */}
      <div className={fr.cx('fr-mb-4w', 'fr-grid-row', 'fr-grid-row--middle')}>
        <div className={fr.cx('fr-col')}>
          <div className={fr.cx('fr-text--sm')}>
            <strong>Connecté en tant que:</strong> {user.email}
            {isAdmin && (
              <Badge severity="success" small className={fr.cx('fr-ml-2w')}>
                Administrateur
              </Badge>
            )}
          </div>
        </div>
        <div className={fr.cx('fr-ml-auto')}>
          <LogoutButton />
        </div>
      </div>

      <h1 className={fr.cx('fr-mb-2w')}>GRAAL</h1>
      <p className={fr.cx('fr-text--lead', 'fr-mb-6w')}>
        Gestion et Répartition Automatisée des Amendements Législatifs
      </p>

      <div className={fr.cx('fr-grid-row', 'fr-grid-row--gutters')}>
        {/* Tuile 1 : Traitement des amendements */}
        <div className={fr.cx('fr-col-12', 'fr-col-md-6')}>
          <Tile
            title="Traitement des amendements"
            desc="Allotissement, attribution, recherche de similarités et génération de résumés des amendements législatifs."
            linkProps={{
              href: '/processing',
              onClick: (e) => {
                e.preventDefault()
                navigate('/processing')
              }
            }}
          />
        </div>

        {/* Tuile 2 : Database Builder */}
        <div className={fr.cx('fr-col-12', 'fr-col-md-6')}>
          <Tile
            title="Constructeur de bases de données"
            desc="Construisez et gérez vos bases de données de similarités pour améliorer les résultats de recherche."
            linkProps={{
              href: '/database',
              onClick: (e) => {
                e.preventDefault()
                navigate('/database')
              }
            }}
          />
        </div>

        {/* Tuile 3 : Excel configs */}
        <div className={fr.cx('fr-col-12', 'fr-col-md-6')}>
          <Tile
            title="Configurations Excel"
            desc="Importez et partagez vos fichiers de configuration Excel pour le traitement des amendements."
            linkProps={{
              href: '/excel-configs',
              onClick: (e) => {
                e.preventDefault()
                navigate('/excel-configs')
              }
            }}
          />
        </div>

        {/* Tuile 4 : Admin (only for admins) */}
        {isAdmin && (
          <div className={fr.cx('fr-col-12', 'fr-col-md-6')}>
            <Tile
              title="Administration"
              desc="Gérez les fichiers S3 (configurations, bases de données, fichiers d'entrée). Accès réservé aux administrateurs."
              linkProps={{
                href: '/admin',
                onClick: (e) => {
                  e.preventDefault()
                  navigate('/admin')
                }
              }}
            />
          </div>
        )}
      </div>
    </div>
  )
}
