import React, { useState, useCallback, useMemo, useRef, useEffect } from 'react'
import { Input } from '@codegouvfr/react-dsfr/Input'
import { fr } from '@codegouvfr/react-dsfr'
import { useQuery } from '@tanstack/react-query'
import { apiService } from '../../services/api'
import styles from './DatabaseSelectorConfig.module.css'

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
  const [inputValue, setInputValue] = useState<string>(value || '')
  const [showDropdown, setShowDropdown] = useState<boolean>(false)
  const wrapperRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const justSelectedRef = useRef<boolean>(false)

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

  // Get error message
  const errorMessage = isError
    ? error instanceof Error
      ? error.message
      : 'Erreur lors du chargement des bases de données'
    : undefined

  // Sync input value with prop changes
  useEffect(() => {
    setInputValue(value || '')
  }, [value])

  // Filter databases based on input
  const filteredDatabases = useMemo(() => {
    if (!inputValue) return databases
    const lowerInput = inputValue.toLowerCase()
    return databases.filter((db) => db.toLowerCase().includes(lowerInput))
  }, [databases, inputValue])

  // Handle click outside to close dropdown
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        wrapperRef.current &&
        !wrapperRef.current.contains(event.target as Node)
      ) {
        setShowDropdown(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [])

  // Handle input change with validation
  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const newValue = e.target.value
      setInputValue(newValue)
      setShowDropdown(true)

      // Only update parent if value is valid (empty or in database list)
      if (newValue === '' || databases.includes(newValue)) {
        onChange(newValue === '' ? null : newValue)
      }
    },
    [databases, onChange]
  )

  // Handle focus to show dropdown
  const handleFocus = useCallback(() => {
    // Don't open dropdown if we just selected an option
    if (justSelectedRef.current) {
      justSelectedRef.current = false
      return
    }
    if (!disabled && !isLoading) {
      setShowDropdown(true)
    }
  }, [disabled, isLoading])

  // Handle blur to revert invalid values and hide dropdown
  const handleBlur = useCallback(() => {
    // If the current input value is not in the list and not empty, revert to the last valid value
    if (inputValue !== '' && !databases.includes(inputValue)) {
      setInputValue(value || '')
    }
  }, [inputValue, databases, value])

  // Handle option selection
  const handleSelectOption = useCallback(
    (database: string) => {
      setInputValue(database)
      onChange(database)
      setShowDropdown(false)
      // Set flag to prevent dropdown from reopening on focus
      justSelectedRef.current = true
      inputRef.current?.focus()
    },
    [onChange]
  )

  // Handle clear button
  const handleClear = useCallback(() => {
    setInputValue('')
    onChange(null)
    setShowDropdown(false)
    // Set flag to prevent dropdown from reopening on focus
    justSelectedRef.current = true
    inputRef.current?.focus()
  }, [onChange])

  // Show loading or error placeholder
  const placeholder = isLoading
    ? 'Chargement...'
    : isError
      ? 'Erreur de chargement'
      : 'Tapez ou sélectionnez (ex: PLFSS 2024)...'

  return (
    <div className={fr.cx('fr-grid-row', 'fr-grid-row--gutters')}>
      <div className={fr.cx('fr-col-12', 'fr-col-md-6')} ref={wrapperRef}>
        <div className={styles.databaseSelectorWrapper}>
          <Input
            className={styles.databaseSelectorInput}
            label="Base de données de recherche de similarité"
            hintText="Recherchez et sélectionnez une base de données pré-traitée pour la correspondance par similarité. Laissez vide pour désactiver."
            state={isError ? 'error' : 'default'}
            stateRelatedMessage={errorMessage}
            nativeInputProps={{
              ref: inputRef,
              value: inputValue,
              onChange: handleInputChange,
              onFocus: handleFocus,
              onBlur: handleBlur,
              placeholder,
              disabled: disabled || isLoading,
              autoComplete: 'off',
              type: 'text',
              role: 'combobox',
              'aria-expanded': showDropdown,
              'aria-autocomplete': 'list'
            }}
          />
          {inputValue && !disabled && !isLoading && (
            <button
              type="button"
              className={styles.clearButton}
              onClick={handleClear}
              aria-label="Effacer la sélection"
            >
              ×
            </button>
          )}
          <button
            type="button"
            className={styles.dropdownToggle}
            onClick={() => setShowDropdown(!showDropdown)}
            disabled={disabled || isLoading}
            aria-label="Afficher les options"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="16"
              height="16"
              fill="currentColor"
              viewBox="0 0 16 16"
            >
              <path d="M8 11L3 6h10z" />
            </svg>
          </button>

          {showDropdown &&
            !isLoading &&
            !isError &&
            filteredDatabases.length > 0 && (
              <ul className={styles.dropdownMenu} role="listbox">
                {filteredDatabases.map((database) => (
                  <li
                    key={database}
                    className={styles.dropdownItem}
                    onClick={() => handleSelectOption(database)}
                    role="option"
                    aria-selected={database === inputValue}
                  >
                    {database}
                  </li>
                ))}
              </ul>
            )}

          {showDropdown &&
            !isLoading &&
            !isError &&
            filteredDatabases.length === 0 && (
              <div className={styles.dropdownMenu}>
                <div className={styles.dropdownEmpty}>
                  Aucun résultat trouvé
                </div>
              </div>
            )}
        </div>
      </div>
    </div>
  )
}

export default DatabaseSelectorConfig
