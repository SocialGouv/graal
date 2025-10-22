import { fr } from '@codegouvfr/react-dsfr'
import { Checkbox } from '@codegouvfr/react-dsfr/Checkbox'
import { Input } from '@codegouvfr/react-dsfr/Input'
import React from 'react'

export interface ColumnToCopyConfig {
  enabled: boolean
  condition?: string
}

export interface ColumnsToCopyConfigProps {
  columnsToCopy: Record<string, ColumnToCopyConfig>
  onChange: (columnsToCopy: Record<string, ColumnToCopyConfig>) => void
  disabled?: boolean
}

export const ColumnsToCopyConfig: React.FC<ColumnsToCopyConfigProps> = ({
  columnsToCopy,
  onChange,
  disabled = false
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

  const handleColumnConditionChange = (
    columnName: string,
    condition: string
  ) => {
    const updatedColumns = {
      ...columnsToCopy,
      [columnName]: {
        ...columnsToCopy[columnName],
        condition: condition.trim() || undefined
      }
    }
    onChange(updatedColumns)
  }

  return (
    <div className={fr.cx('fr-grid-row', 'fr-grid-row--gutters')}>
      <div className={fr.cx('fr-col-12')}>
        <h4 className={fr.cx('fr-h6', 'fr-mb-2w')}>
          Colonnes à copier depuis les amendements similaires
        </h4>
        <p className={fr.cx('fr-text--sm', 'fr-mb-3w')}>
          Configurez quelles colonnes doivent être copiées depuis les
          amendements similaires trouvés.
        </p>

        {Object.entries(columnsToCopy).length === 0 ? (
          <p className={fr.cx('fr-text--sm')}>
            Aucune colonne disponible à configurer.
          </p>
        ) : (
          Object.entries(columnsToCopy).map(([columnName, config]) => (
            <div
              key={columnName}
              className={fr.cx('fr-mb-3w', 'fr-p-2w', 'fr-fieldset')}
            >
              <div className={fr.cx('fr-grid-row', 'fr-grid-row--gutters')}>
                <div className={fr.cx('fr-col-12', 'fr-col-md-6')}>
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

                {config.enabled && (
                  <div className={fr.cx('fr-col-12', 'fr-col-md-6')}>
                    <Input
                      label="Condition (optionnelle)"
                      hintText="Ne copier que si la valeur correspond à cette condition"
                      nativeInputProps={{
                        placeholder: 'Ex: irrecevable',
                        value: config.condition || '',
                        onChange: (e) =>
                          handleColumnConditionChange(
                            columnName,
                            e.target.value
                          ),
                        disabled
                      }}
                    />
                  </div>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

export default ColumnsToCopyConfig
