import { fr } from '@codegouvfr/react-dsfr'
import { useQuery } from '@tanstack/react-query'
import React from 'react'
import { apiService } from '../../services/api'
import { Combobox } from '../Combobox'

export interface DatabaseSelectorConfigProps {
  value: string | null
  onChange: (value: string | null) => void
  disabled?: boolean
}

export const DatabaseSelectorConfig: React.FC<DatabaseSelectorConfigProps> = ({
  value,
  onChange,
  disabled = false
}) => {
  // Fetch available databases using React Query
  const {
    data: manifests = [],
    isLoading,
    isError,
    error
  } = useQuery({
    queryKey: ['similarity-databases'],
    queryFn: () => apiService.listSimilarityDatabases(),
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
    retry: 2
  })

  // Extract database names from manifests with defensive check
  // Ensures manifests is always treated as an array to prevent crashes
  const databases = Array.isArray(manifests)
    ? manifests.map((manifest) => manifest.name)
    : []

  // Get error message
  const errorMessage = isError
    ? error instanceof Error
      ? error.message
      : 'Erreur lors du chargement des bases de données'
    : undefined

  // Show loading or error placeholder
  const placeholder = isLoading
    ? 'Chargement...'
    : isError
      ? 'Erreur de chargement'
      : 'Tapez ou sélectionnez (ex: PLFSS 2024)...'

  return (
    <div className={fr.cx('fr-grid-row', 'fr-grid-row--gutters')}>
      <div className={fr.cx('fr-col-12', 'fr-col-md-6')}>
        <Combobox
          options={databases}
          value={value}
          onChange={onChange}
          label="Base de données de recherche de similarité"
          hint="Recherchez et sélectionnez une base de données de précédentes lectures."
          state={isError ? 'error' : 'default'}
          stateRelatedMessage={errorMessage}
          disabled={disabled}
          isLoading={isLoading}
          placeholder={placeholder}
          emptyMessage="Aucun résultat trouvé"
        />
      </div>
    </div>
  )
}

export default DatabaseSelectorConfig
