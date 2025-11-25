import { Input } from '@codegouvfr/react-dsfr/Input'
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import styles from './Combobox.module.css'

export interface ComboboxProps {
  /** List of selectable options */
  options: string[]
  /** Current selected value */
  value: string | null
  /** Callback when value changes */
  onChange: (value: string | null) => void
  /** Field label */
  label: string
  /** Optional hint text */
  hint?: string
  /** DSFR input state */
  state?: 'error' | 'success' | 'default'
  /** Error/success message */
  stateRelatedMessage?: string
  /** Whether input is disabled */
  disabled?: boolean
  /** Show loading state */
  isLoading?: boolean
  /** Input placeholder */
  placeholder?: string
  /** Message when no options match */
  emptyMessage?: string
  /** Additional CSS class for wrapper */
  className?: string
  /** Whether input should auto-focus on mount */
  autoFocus?: boolean
}

export const Combobox: React.FC<ComboboxProps> = ({
  options,
  value,
  onChange,
  label,
  hint,
  state = 'default',
  stateRelatedMessage,
  disabled = false,
  isLoading = false,
  placeholder,
  emptyMessage = 'Aucun résultat trouvé',
  className,
  autoFocus = false
}) => {
  const [inputValue, setInputValue] = useState<string>(value || '')
  const [showDropdown, setShowDropdown] = useState<boolean>(false)
  const wrapperRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const justSelectedRef = useRef<boolean>(false)

  // Sync input value with prop changes
  useEffect(() => {
    setInputValue(value || '')
  }, [value])

  // Filter options based on input
  const filteredOptions = useMemo(() => {
    if (!inputValue) return options
    const lowerInput = inputValue.toLowerCase()
    return options.filter((option) => option.toLowerCase().includes(lowerInput))
  }, [options, inputValue])

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

      // Only update parent if value is valid (empty or in options list)
      if (newValue === '' || options.includes(newValue)) {
        onChange(newValue === '' ? null : newValue)
      }
    },
    [options, onChange]
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

  // Handle blur to revert invalid values
  const handleBlur = useCallback(() => {
    // If the current input value is not in the list and not empty, revert to the last valid value
    if (inputValue !== '' && !options.includes(inputValue)) {
      setInputValue(value || '')
    }
  }, [inputValue, options, value])

  // Handle option selection
  const handleSelectOption = useCallback(
    (option: string, event?: React.MouseEvent) => {
      // Prevent blur event from firing when clicking option
      event?.preventDefault()
      setInputValue(option)
      onChange(option)
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

  // Handle dropdown toggle
  const handleToggleDropdown = useCallback(() => {
    if (!disabled && !isLoading) {
      setShowDropdown(!showDropdown)
    }
  }, [disabled, isLoading, showDropdown])

  // Get effective placeholder
  const effectivePlaceholder = isLoading
    ? 'Chargement...'
    : placeholder || 'Tapez ou sélectionnez...'

  return (
    <div className={className} ref={wrapperRef}>
      <div className={styles.comboboxWrapper}>
        <div className={styles.inputContainer}>
          <Input
            className={styles.comboboxInput}
            label={label}
            hintText={hint}
            state={state}
            stateRelatedMessage={stateRelatedMessage}
            nativeInputProps={{
              ref: inputRef,
              value: inputValue,
              onChange: handleInputChange,
              onFocus: handleFocus,
              onBlur: handleBlur,
              placeholder: effectivePlaceholder,
              disabled: disabled || isLoading,
              autoComplete: 'off',
              type: 'text',
              role: 'combobox',
              'aria-expanded': showDropdown,
              'aria-autocomplete': 'list',
              autoFocus
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
            onClick={handleToggleDropdown}
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
        </div>

        {showDropdown && !isLoading && filteredOptions.length > 0 && (
          <ul className={styles.dropdownMenu} role="listbox">
            {filteredOptions.map((option) => (
              <li
                key={option}
                className={styles.dropdownItem}
                onMouseDown={(e) => handleSelectOption(option, e)}
                role="option"
                aria-selected={option === inputValue}
              >
                {option}
              </li>
            ))}
          </ul>
        )}

        {showDropdown && !isLoading && filteredOptions.length === 0 && (
          <div className={styles.dropdownMenu}>
            <div className={styles.dropdownEmpty}>{emptyMessage}</div>
          </div>
        )}
      </div>
    </div>
  )
}

export default Combobox
