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

  /**
   * If true, the input is cleared after selecting an option.
   * Useful when using the Combobox as a picker for multi-select.
   */
  clearInputOnSelect?: boolean

  /**
   * If true (default), selecting an option closes the dropdown.
   * Set to false to keep the list open after selection (multi-pick UX).
   */
  closeOnSelect?: boolean

  /**
   * If true (default), typing an exact option value triggers `onChange`.
   * Set to false to only commit selection on explicit option click.
   */
  selectOnExactMatch?: boolean
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
  clearInputOnSelect = false,
  closeOnSelect = true,
  selectOnExactMatch = true
}) => {
  const [inputValue, setInputValue] = useState<string>(value || '')
  const [showDropdown, setShowDropdown] = useState<boolean>(false)
  const wrapperRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

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
      if (
        selectOnExactMatch &&
        (newValue === '' || options.includes(newValue))
      ) {
        onChange(newValue === '' ? null : newValue)
      }
    },
    [options, onChange, selectOnExactMatch]
  )

  // Handle focus to show dropdown
  const handleFocus = useCallback(() => {
    if (!disabled && !isLoading) {
      setShowDropdown(true)
    }
  }, [disabled, isLoading])

  // Some UX flows close the dropdown while keeping focus on the input.
  // In that case, focusing won't fire again; clicking should reopen.
  const handleClick = useCallback(() => {
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
      event?.stopPropagation()
      onChange(option)

      if (clearInputOnSelect) {
        setInputValue('')
      } else {
        setInputValue(option)
      }

      setShowDropdown(!closeOnSelect)

      // Ensure the input stays focused for fast consecutive selections.
      // Some browsers/UI flows may still move focus to the clicked item.
      inputRef.current?.focus()

      // In multi-pick mode we want the dropdown to remain visible immediately
      // after selection, even if any intermediate focus/blur/click handlers run.
      if (!closeOnSelect) {
        Promise.resolve().then(() => {
          setShowDropdown(true)
        })
      }
    },
    [clearInputOnSelect, closeOnSelect, onChange]
  )

  // Handle clear button
  const handleClear = useCallback(() => {
    setInputValue('')
    onChange(null)
    setShowDropdown(false)
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
              onClick: handleClick,
              onBlur: handleBlur,
              placeholder: effectivePlaceholder,
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
