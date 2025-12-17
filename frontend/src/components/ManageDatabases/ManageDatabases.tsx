import { Alert } from '@codegouvfr/react-dsfr/Alert'
import { ButtonsGroup } from '@codegouvfr/react-dsfr/ButtonsGroup'
import { Table } from '@codegouvfr/react-dsfr/Table'
import { useQuery } from '@tanstack/react-query'
import React, { useState } from 'react'
import { apiService } from '../../services/api'
import type { ManagedDatabase } from '../../types/api'
import { DatabasePermissions } from '../DatabasePermissions/DatabasePermissions'

export const ManageDatabases: React.FC = () => {
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

  // Format bytes to human-readable size
  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 octets'
    const k = 1024
    const sizes = ['octets', 'Ko', 'Mo', 'Go']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`
  }

  // Format number with thousands separator
  const formatNumber = (num: number | null): string => {
    if (num === null) return 'N/A'
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
            <ButtonsGroup
              key={db.id}
              buttons={[
                {
                  children: 'Gérer les permissions',
                  priority: 'secondary',
                  size: 'small',
                  onClick: () =>
                    setSelectedDatabase({ id: db.id, name: db.name })
                }
              ]}
              inlineLayoutWhen="always"
            />
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
