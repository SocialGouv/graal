import { fr } from '@codegouvfr/react-dsfr'
import React, {
  useCallback,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState
} from 'react'
import styles from './MultiCombobox.module.css'

export interface MultiComboboxProps {
  /** Full list of selectable options */
  options: string[]
  /** Currently selected values */
  values: string[]
  /** Called whenever the selection changes */
  onChange: (values: string[]) => void

  label: string
  hint?: string
  placeholder?: string
  emptyMessage?: string
  disabled?: boolean

  /** DSFR input state */
  state?: 'error' | 'success' | 'default'
  /** Error/success message */
  stateRelatedMessage?: string
}

export const MultiCombobox: React.FC<MultiComboboxProps> = ({
  options,
  values,
  onChange,
  label,
  hint,
  placeholder = 'Tapez pour filtrer…',
  emptyMessage = 'Aucun résultat trouvé',
  disabled = false,
  state = 'default',
  stateRelatedMessage
}) => {
  const inputId = useId()
  const dropdownId = useId()

  const [inputValue, setInputValue] = useState('')
  const [showDropdown, setShowDropdown] = useState(false)
  const [activeChipIndex, setActiveChipIndex] = useState<number>(-1)

  const wrapperRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const chipRefs = useRef<Array<HTMLSpanElement | null>>([])

  const availableOptions = useMemo(() => {
    const selected = new Set(values)
    return options.filter((opt) => !selected.has(opt))
  }, [options, values])

  const filteredOptions = useMemo(() => {
    if (!inputValue) return availableOptions
    const q = inputValue.toLowerCase()
    return availableOptions.filter((opt) => opt.toLowerCase().includes(q))
  }, [availableOptions, inputValue])

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

  // Keep active chip index valid when the list changes.
  useEffect(() => {
    if (activeChipIndex === -1) return
    if (values.length === 0) {
      setActiveChipIndex(-1)
      return
    }
    if (activeChipIndex >= values.length) {
      setActiveChipIndex(values.length - 1)
    }
  }, [activeChipIndex, values.length])

  useEffect(() => {
    if (activeChipIndex === -1) return
    chipRefs.current[activeChipIndex]?.focus()
  }, [activeChipIndex])

  const openDropdown = useCallback(() => {
    if (disabled) return
    setShowDropdown(true)
  }, [disabled])

  const focusInput = useCallback(() => {
    setActiveChipIndex(-1)
    inputRef.current?.focus()
    openDropdown()
  }, [openDropdown])

  const handleShellMouseDown = useCallback(
    (e: React.MouseEvent) => {
      if (disabled) return
      // Prevent losing focus when clicking inside the shell.
      e.preventDefault()
      focusInput()
    },
    [disabled, focusInput]
  )

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      setInputValue(e.target.value)
      openDropdown()
      setActiveChipIndex(-1)
    },
    [openDropdown]
  )

  const commitAdd = useCallback(
    (value: string) => {
      if (disabled) return
      if (values.includes(value)) return
      onChange([...values, value])
      setInputValue('')
      // Keep dropdown open for fast consecutive picks.
      Promise.resolve().then(() => setShowDropdown(true))
      focusInput()
    },
    [disabled, focusInput, onChange, values]
  )

  const commitRemoveAtIndex = useCallback(
    (index: number) => {
      if (index < 0 || index >= values.length) return
      const nextValues = values.filter((_, i) => i !== index)
      onChange(nextValues)
      openDropdown()

      if (nextValues.length === 0) {
        setActiveChipIndex(-1)
        Promise.resolve().then(() => {
          inputRef.current?.focus()
        })
        return
      }

      // Keep selection near the deleted chip:
      // - if we deleted the last one, select the previous
      // - otherwise, select the chip that shifted into this index
      const nextIndex = Math.min(
        index >= nextValues.length ? nextValues.length - 1 : index,
        nextValues.length - 1
      )
      setActiveChipIndex(nextIndex)
    },
    [onChange, openDropdown, values]
  )

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (disabled) return

      if (e.key === 'ArrowLeft' && inputValue === '' && values.length > 0) {
        e.preventDefault()
        setActiveChipIndex(values.length - 1)
        return
      }

      if (e.key === 'Backspace' && inputValue === '' && values.length > 0) {
        e.preventDefault()
        commitRemoveAtIndex(values.length - 1)
        return
      }

      if (e.key === 'Escape') {
        setShowDropdown(false)
      }
    },
    [commitRemoveAtIndex, disabled, inputValue, values]
  )

  let stateClass = ''
  if (state === 'error') {
    stateClass = fr.cx('fr-input-group--error')
  } else if (state === 'success') {
    stateClass = fr.cx('fr-input-group--valid')
  }

  const inputGroupClassName = [fr.cx('fr-input-group'), stateClass]
    .filter(Boolean)
    .join(' ')

  let messageClass = fr.cx('fr-hint-text')
  if (state === 'error') {
    messageClass = fr.cx('fr-error-text')
  } else if (state === 'success') {
    messageClass = fr.cx('fr-valid-text')
  }

  const inputShellClassName = `${fr.cx('fr-input')} ${styles.inputShell}`

  return (
    <div ref={wrapperRef} className={inputGroupClassName}>
      <label className={fr.cx('fr-label')} htmlFor={inputId}>
        {label}
        {hint && <span className={fr.cx('fr-hint-text')}>{hint}</span>}
      </label>

      <div style={{ position: 'relative' }}>
        <div
          className={inputShellClassName}
          aria-disabled={disabled}
          onMouseDown={handleShellMouseDown}
        >
          {values.map((v, index) => (
            <span
              key={`${v}-${index}`}
              ref={(el) => {
                chipRefs.current[index] = el
              }}
              className={[
                fr.cx('fr-tag', 'fr-tag--sm'),
                styles.chip,
                activeChipIndex === index ? styles.chipSelected : ''
              ]
                .filter(Boolean)
                .join(' ')}
              role="button"
              tabIndex={activeChipIndex === index ? 0 : -1}
              aria-pressed={activeChipIndex === index}
              aria-label={v}
              onMouseDown={(e) => {
                e.preventDefault()
                e.stopPropagation()
                setActiveChipIndex(index)
              }}
              onKeyDown={(e) => {
                if (e.key === 'ArrowLeft') {
                  e.preventDefault()
                  if (index > 0) setActiveChipIndex(index - 1)
                  return
                }

                if (e.key === 'ArrowRight') {
                  e.preventDefault()
                  if (index < values.length - 1) setActiveChipIndex(index + 1)
                  else focusInput()
                  return
                }

                if (e.key === 'Backspace' || e.key === 'Delete') {
                  e.preventDefault()
                  commitRemoveAtIndex(index)
                }
              }}
            >
              <span className={styles.chipText}>{v}</span>
              <button
                type="button"
                className={styles.chipRemove}
                onClick={(e) => {
                  e.preventDefault()
                  e.stopPropagation()
                  commitRemoveAtIndex(index)
                }}
                aria-label={`Retirer ${v}`}
                disabled={disabled}
              >
                <span
                  className={fr.cx('fr-icon-close-line', 'fr-icon--sm')}
                  aria-hidden="true"
                />
              </button>
            </span>
          ))}

          <input
            id={inputId}
            ref={inputRef}
            className={styles.textInput}
            value={inputValue}
            onChange={handleInputChange}
            onFocus={openDropdown}
            onClick={() => setActiveChipIndex(-1)}
            onKeyDown={handleKeyDown}
            placeholder={values.length === 0 ? placeholder : ''}
            disabled={disabled}
            aria-haspopup="listbox"
            aria-expanded={showDropdown}
            aria-controls={showDropdown ? dropdownId : undefined}
            autoComplete="off"
          />
        </div>

        {showDropdown && (
          <ul id={dropdownId} className={styles.dropdownMenu} role="listbox">
            {filteredOptions.length > 0 ? (
              filteredOptions.map((opt) => (
                <li
                  key={opt}
                  className={styles.dropdownItem}
                  role="option"
                  onMouseDown={(e) => {
                    // Use mousedown to avoid blur before selection.
                    e.preventDefault()
                    e.stopPropagation()
                    commitAdd(opt)
                  }}
                >
                  {opt}
                </li>
              ))
            ) : (
              <li
                className={styles.dropdownEmpty}
                role="option"
                aria-disabled="true"
              >
                {emptyMessage}
              </li>
            )}
          </ul>
        )}
      </div>

      {stateRelatedMessage && (
        <p className={messageClass} aria-live="polite">
          {stateRelatedMessage}
        </p>
      )}
    </div>
  )
}

export default MultiCombobox
