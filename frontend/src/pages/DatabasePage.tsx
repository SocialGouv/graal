import { fr } from '@codegouvfr/react-dsfr'
import { Alert } from '@codegouvfr/react-dsfr/Alert'
import { Button } from '@codegouvfr/react-dsfr/Button'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { DatabaseBuilder } from '../components/DatabaseBuilder'
import { useAuth } from '../hooks/useAuth'
import apiService from '../services/api'

export const DatabasePage = () => {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { isAdmin, isLoading: authLoading } = useAuth()
  const [successMessage, setSuccessMessage] = useState<string | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  // Clear messages after 5 seconds
  useEffect(() => {
    if (successMessage || errorMessage) {
      const timer = setTimeout(() => {
        setSuccessMessage(null)
        setErrorMessage(null)
      }, 5000)
      return () => clearTimeout(timer)
    }
  }, [successMessage, errorMessage])

  // Mutation for syncing manifests from S3
  const syncMutation = useMutation({
    mutationFn: () => apiService.syncSimilarityDatabaseManifests(),
    onSuccess: (data) => {
      setSuccessMessage(
        `Synchronisation réussie : ${data.length} base(s) de données synchronisée(s)`
      )
      setErrorMessage(null)
      // Invalidate databases query to refresh the list
      queryClient.invalidateQueries({ queryKey: ['databases'] })
    },
    onError: (error: any) => {
      setErrorMessage(
        error?.detail ||
          'Erreur lors de la synchronisation des bases de données'
      )
      setSuccessMessage(null)
    }
  })

  const handleSyncDatabases = () => {
    syncMutation.mutate()
  }

  return (
    <div className={fr.cx('fr-container', 'fr-py-6w')}>
      <main>
        {/* Back to Home Button */}
        <div className={fr.cx('fr-mb-4w')}>
          <Button
            priority="tertiary no outline"
            iconId="fr-icon-arrow-left-line"
            iconPosition="left"
            onClick={() => navigate('/')}
            size="small"
          >
            Retour à l'accueil
          </Button>
        </div>

        {/* Success/Error Messages */}
        {successMessage && (
          <Alert
            severity="success"
            title="Succès"
            description={successMessage}
            className={fr.cx('fr-mb-4w')}
            closable
            onClose={() => setSuccessMessage(null)}
          />
        )}
        {errorMessage && (
          <Alert
            severity="error"
            title="Erreur"
            description={errorMessage}
            className={fr.cx('fr-mb-4w')}
            closable
            onClose={() => setErrorMessage(null)}
          />
        )}

        {/* Admin Section - Sync Databases */}
        {!authLoading && isAdmin && (
          <div className={fr.cx('fr-mb-6w')}>
            <div className={fr.cx('fr-callout')}>
              <h3 className={fr.cx('fr-callout__title')}>
                Administration des bases de données de similarité
              </h3>
              <p className={fr.cx('fr-callout__text')}>
                Synchronisez les bases de données de similarité depuis S3 pour
                mettre à jour le catalogue. Cette opération scanne le bucket S3
                et crée ou met à jour les manifestes pour chaque base de données
                trouvée.
              </p>
              <Button
                priority="secondary"
                iconId="fr-icon-refresh-line"
                iconPosition="left"
                onClick={handleSyncDatabases}
                disabled={syncMutation.isPending}
              >
                {syncMutation.isPending
                  ? 'Synchronisation en cours...'
                  : 'Synchroniser les bases de données'}
              </Button>
            </div>
          </div>
        )}

        {/* Database Builder Component */}
        <DatabaseBuilder />
      </main>
    </div>
  )
}
