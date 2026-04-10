import { Alert } from '@codegouvfr/react-dsfr/Alert'
import { Button } from '@codegouvfr/react-dsfr/Button'
import { Table } from '@codegouvfr/react-dsfr/Table'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import React, { useState } from 'react'
import { apiService } from '../../services/api'
import type { ManagedDatabase } from '../../types/api'
import { DatabasePermissions } from '../DatabasePermissions/DatabasePermissions'

export const ManageDatabases: React.FC = () => {
  const queryClient = useQueryClient()
  const [selectedDatabase, setSelectedDatabase] = useState<{
    id: string
    name: string
  } | null>(null)

  // Fetch managed databases
  const {
    data: databases,
    isLoading,
    error
  } = useQuery<ManagedDatabase[], Error>({
    queryKey: ['managed-databases'],
    queryFn: () => apiService.getManagedDatabases()
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => apiService.deleteDatabaseForOwner(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['managed-databases'] })
    }
  })

  // Format bytes to human-readable size
  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 octets'
    const k = 1024
    const sizes = ['octets', 'Ko', 'Mo', 'Go']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`
  }

  // Format number with thousands separator
  const formatNumber = (num: number | null | undefined): string => {
    if (num === null || num === undefined) return 'N/A'
    return num.toLocaleString('fr-FR')
  }

  // If viewing permissions, show DatabasePermissions component
  if (selectedDatabase) {
    return (
      <DatabasePermissions
        databaseId={selectedDatabase.id}
        databaseName={selectedDatabase.name}
        onClose={() => setSelectedDatabase(null)}
      />
    )
  }

  if (isLoading) {
    return <div>Chargement des bases de données...</div>
  }

  if (error) {
    return (
      <Alert
        severity="error"
        title="Erreur"
        description={
          error.message || 'Erreur lors du chargement des bases de données'
        }
      />
    )
  }

  return (
    <div>
      <h2>Gérer les bases de données</h2>
      <p style={{ marginBottom: '2rem' }}>
        Liste des bases de données que vous possédez ou pour lesquelles vous
        avez des droits d'administration.
      </p>

      {databases && databases.length > 0 ? (
        <Table
          headers={[
            'Nom',
            'Date de création',
            'Nombre de lignes',
            'Taille',
            'Actions'
          ]}
          data={databases.map((db) => [
            db.name,
            new Date(db.created_at).toLocaleDateString('fr-FR', {
              year: 'numeric',
              month: 'long',
              day: 'numeric'
            }),
            formatNumber(db.row_count),
            formatBytes(db.size_bytes),
            <div
              key={db.id}
              style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}
            >
              <Button
                priority="secondary"
                size="small"
                onClick={() => setSelectedDatabase({ id: db.id, name: db.name })}
              >
                Gérer les permissions
              </Button>
              <Button
                priority="tertiary no outline"
                size="small"
                iconId="fr-icon-delete-line"
                title="Supprimer"
                onClick={() => {
                  if (
                    globalThis.confirm(
                      `Supprimer la base de données « ${db.name} » ?`
                    )
                  ) {
                    deleteMutation.mutate(db.id)
                  }
                }}
              />
            </div>
          ])}
        />
      ) : (
        <Alert
          severity="info"
          title="Aucune base de données"
          description="Vous ne possédez aucune base de données pour le moment. Créez-en une dans l'onglet 'Construire une base de données'."
        />
      )}
    </div>
  )
}
