import React, { useState, useMemo } from 'react'
import { Select } from '@codegouvfr/react-dsfr/Select'
import { Input } from '@codegouvfr/react-dsfr/Input'
import { fr } from '@codegouvfr/react-dsfr'
import { useQuery } from '@tanstack/react-query'
import { apiService } from '../../services/api'

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
  const [filterText, setFilterText] = useState('')

  // Fetch available databases using React Query
  const {
    data: databases = [],
    isLoading,
    isError,
    error
  } = useQuery({
    queryKey: ['similarity-databases'],
    queryFn: () => apiService.listSimilarityDatabases(),
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
    retry: 2
  })

  // Filter databases based on search text (case-insensitive)
  const filteredDatabases = useMemo(() => {
    if (!filterText.trim()) {
      return databases
    }

    const searchLower = filterText.toLowerCase()
    return databases.filter((db) => db.toLowerCase().includes(searchLower))
  }, [databases, filterText])

  // Get error message
  const errorMessage = isError
    ? error instanceof Error
      ? error.message
      : 'Erreur lors du chargement des bases de données'
    : undefined

  return (
    <div className={fr.cx('fr-grid-row', 'fr-grid-row--gutters')}>
      <div className={fr.cx('fr-col-12', 'fr-col-md-6')}>
        {/* Filter input */}
        <Input
          label="Rechercher une base de données"
          hintText="Tapez pour filtrer (ex: 'PLFSS' ou '2024')"
          nativeInputProps={{
            value: filterText,
            onChange: (e) => setFilterText(e.target.value),
            placeholder: 'Filtrer les bases de données...',
            disabled: disabled || isLoading
          }}
        />

        {/* Database selector */}
        <div className={fr.cx('fr-mt-2w')}>
          <Select
            label="Base de données de recherche de similarité"
            hint="Sélectionnez une base de données pré-traitée pour la correspondance par similarité"
            state={isError ? 'error' : 'default'}
            stateRelatedMessage={errorMessage}
            disabled={disabled || isLoading}
            nativeSelectProps={{
              value: value || '',
              onChange: (e) => {
                const newValue = e.target.value
                onChange(newValue === '' ? null : newValue)
              }
            }}
          >
            {isLoading ? (
              <option value="" disabled>
                Chargement des bases de données...
              </option>
            ) : isError ? (
              <option value="" disabled>
                Erreur de chargement
              </option>
            ) : (
              <>
                <option value="">Aucune (désactiver)</option>
                {filteredDatabases.length === 0 ? (
                  <option value="" disabled>
                    Aucune base de données trouvée
                  </option>
                ) : (
                  filteredDatabases.map((database) => (
                    <option key={database} value={database}>
                      {database}
                    </option>
                  ))
                )}
              </>
            )}
          </Select>
        </div>

        {/* Show count of filtered results */}
        {!isLoading && !isError && filterText && (
          <div className={fr.cx('fr-text--sm', 'fr-mt-1w')}>
            {filteredDatabases.length} base(s) de données trouvée(s)
          </div>
        )}
      </div>
    </div>
  )
}

export default DatabaseSelectorConfig
