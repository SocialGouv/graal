import { fr } from '@codegouvfr/react-dsfr'
import { Alert } from '@codegouvfr/react-dsfr/Alert'
import { Badge } from '@codegouvfr/react-dsfr/Badge'
import { Button } from '@codegouvfr/react-dsfr/Button'
import { Card } from '@codegouvfr/react-dsfr/Card'
import { useNavigate } from 'react-router-dom'
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
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className={fr.cx('fr-container', 'fr-py-6w')}>
      <div className={fr.cx('fr-grid-row', 'fr-grid-row--center')}>
        <div className={fr.cx('fr-col-12', 'fr-col-md-10', 'fr-col-lg-8')}>
          {/* Header with user info and logout */}
          <div
            className={fr.cx('fr-mb-4w', 'fr-grid-row', 'fr-grid-row--middle')}
          >
            <div className={fr.cx('fr-col-12', 'fr-col-md-6')}>
              <div className={fr.cx('fr-text--sm')}>
                <strong>Connecté en tant que:</strong> {user.email}
                {isAdmin && (
                  <Badge severity="success" small className={fr.cx('fr-ml-2w')}>
                    Administrateur
                  </Badge>
                )}
              </div>
            </div>
            <div
              className={fr.cx('fr-col-12', 'fr-col-md-6')}
              style={{ textAlign: 'right' }}
            >
              <LogoutButton />
            </div>
          </div>

          <h1 className={fr.cx('fr-mb-2w')}>GRAAL</h1>
          <p className={fr.cx('fr-text--lead', 'fr-mb-6w')}>
            Gestion et Répartition Automatisée des Amendements Législatifs
          </p>

          <div className={fr.cx('fr-grid-row', 'fr-grid-row--gutters')}>
            {/* Carte 1 : Traitement des amendements */}
            <div className={fr.cx('fr-col-12', 'fr-col-md-6', 'fr-col-lg-4')}>
              <Card
                title="Traitement des amendements"
                desc="Traitez et analysez automatiquement les amendements législatifs avec des fonctionnalités d'allotissement, d'attribution, de recherche de similarités et de génération de résumés."
                start={
                  <ul className={fr.cx('fr-badges-group')}>
                    <li>
                      <Badge severity="info" small>
                        Allotissement
                      </Badge>
                    </li>
                    <li>
                      <Badge severity="info" small>
                        Attribution
                      </Badge>
                    </li>
                    <li>
                      <Badge severity="info" small>
                        Similarités
                      </Badge>
                    </li>
                  </ul>
                }
                footer={
                  <Button
                    iconId="fr-icon-arrow-right-line"
                    iconPosition="right"
                    onClick={() => navigate('/processing')}
                  >
                    Commencer le traitement
                  </Button>
                }
              />
            </div>

            {/* Carte 2 : Database Builder */}
            <div className={fr.cx('fr-col-12', 'fr-col-md-6', 'fr-col-lg-4')}>
              <Card
                title="Constructeur de bases de données"
                desc="Construisez et gérez vos bases de données de similarités pour améliorer les résultats de recherche et optimiser le traitement des amendements."
                start={
                  <ul className={fr.cx('fr-badges-group')}>
                    <li>
                      <Badge severity="info" small>
                        Base de données
                      </Badge>
                    </li>
                    <li>
                      <Badge severity="info" small>
                        Gestion
                      </Badge>
                    </li>
                  </ul>
                }
                footer={
                  <Button
                    iconId="fr-icon-arrow-right-line"
                    iconPosition="right"
                    onClick={() => navigate('/database')}
                  >
                    Ouvrir le constructeur de bases de données
                  </Button>
                }
              />
            </div>

            {/* Carte 3 : Excel configs */}
            <div className={fr.cx('fr-col-12', 'fr-col-md-6', 'fr-col-lg-4')}>
              <Card
                title="Configurations Excel"
                desc="Importez et partagez vos fichiers de configuration Excel pour le traitement des amendements."
                start={
                  <ul className={fr.cx('fr-badges-group')}>
                    <li>
                      <Badge severity="info" small>
                        Excel
                      </Badge>
                    </li>
                    <li>
                      <Badge severity="info" small>
                        Permissions
                      </Badge>
                    </li>
                  </ul>
                }
                footer={
                  <Button
                    iconId="fr-icon-arrow-right-line"
                    iconPosition="right"
                    onClick={() => navigate('/excel-configs')}
                  >
                    Gérer les configurations Excel
                  </Button>
                }
              />
            </div>

            {/* Carte 4 : Admin (only for admins) */}
            {isAdmin && (
              <div className={fr.cx('fr-col-12', 'fr-col-md-6', 'fr-col-lg-4')}>
                <Card
                  title="Administration"
                  desc="Gérez les fichiers S3 (configurations, bases de données, fichiers d'entrée). Accès réservé aux administrateurs."
                  start={
                    <ul className={fr.cx('fr-badges-group')}>
                      <li>
                        <Badge severity="success" small>
                          Admin
                        </Badge>
                      </li>
                      <li>
                        <Badge severity="info" small>
                          Gestion S3
                        </Badge>
                      </li>
                    </ul>
                  }
                  footer={
                    <Button
                      iconId="fr-icon-settings-5-line"
                      iconPosition="right"
                      onClick={() => navigate('/admin')}
                    >
                      Accéder à l'administration
                    </Button>
                  }
                />
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
