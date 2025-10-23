import { fr } from '@codegouvfr/react-dsfr'
import { Checkbox } from '@codegouvfr/react-dsfr/Checkbox'
import React from 'react'
import {
  DEFAULT_FEATURE_FLAGS,
  type FeatureFlags
} from '../../config/featureFlags'

export interface ColumnToCopyConfig {
  enabled: boolean
  condition?: string
}

export interface ColumnsToCopyConfigProps {
  columnsToCopy: Record<string, ColumnToCopyConfig>
  onChange: (columnsToCopy: Record<string, ColumnToCopyConfig>) => void
  disabled?: boolean
  /** Feature flags to control which columns are visible in the UI */
  featureFlags?: FeatureFlags
}

export const ColumnsToCopyConfig: React.FC<ColumnsToCopyConfigProps> = ({
  columnsToCopy,
  onChange,
  disabled = false,
  featureFlags = DEFAULT_FEATURE_FLAGS
}) => {
  const handleColumnEnabledChange = (columnName: string, enabled: boolean) => {
    const updatedColumns = {
      ...columnsToCopy,
      [columnName]: {
        ...columnsToCopy[columnName],
        enabled
      }
    }
    onChange(updatedColumns)
  }

  /**
   * Filter columns based on feature flags.
   * Hidden columns will still work with their backend default values,
   * they're just not shown in the UI.
   */
  const isColumnVisible = (columnName: string): boolean => {
    const visibility = featureFlags.columnsToCopyVisibility
    switch (columnName) {
      case 'Réponse':
        return visibility.showReponse
      case 'Sort':
        return visibility.showSort
      case 'Objet amdt':
        return visibility.showObjetAmdt
      default:
        // Show unknown columns by default for forward compatibility
        return true
    }
  }

  // Filter columns to only show visible ones
  const visibleColumns = Object.entries(columnsToCopy).filter(([columnName]) =>
    isColumnVisible(columnName)
  )

  return (
    <div className={fr.cx('fr-grid-row', 'fr-grid-row--gutters')}>
      <div className={fr.cx('fr-col-12')}>
        <h4 className={fr.cx('fr-h6', 'fr-mb-2w')}>
          Colonnes à copier depuis les amendements similaires
        </h4>
        <p className={fr.cx('fr-text--sm', 'fr-mb-3w')}>
          Configurez quelles colonnes doivent être copiées depuis les
          amendements similaires trouvés en plus de "Réponse" et "Sort".
        </p>

        {visibleColumns.length === 0 ? (
          <p className={fr.cx('fr-text--sm')}>
            Aucune colonne disponible à configurer.
          </p>
        ) : (
          visibleColumns.map(([columnName, config]) => (
            <div key={columnName} className={fr.cx('fr-p-2w')}>
              <div className={fr.cx('fr-grid-row', 'fr-grid-row--gutters')}>
                <div className={fr.cx('fr-col-12')}>
                  <Checkbox
                    options={[
                      {
                        label: columnName,
                        nativeInputProps: {
                          checked: config.enabled,
                          onChange: (e) =>
                            handleColumnEnabledChange(
                              columnName,
                              e.target.checked
                            ),
                          disabled
                        }
                      }
                    ]}
                  />
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

export default ColumnsToCopyConfig
