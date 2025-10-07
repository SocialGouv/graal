import React from 'react'
import { Checkbox } from '@codegouvfr/react-dsfr/Checkbox'
import { fr } from '@codegouvfr/react-dsfr'

interface FeatureConfigSectionProps {
  // Feature identification
  title: string
  description: string

  // State management
  enabled: boolean
  onEnabledChange: (enabled: boolean) => void

  // UI behavior
  disabled?: boolean

  // Configuration content
  children?: React.ReactNode
}

export const FeatureConfigSection: React.FC<FeatureConfigSectionProps> = ({
  title,
  description,
  enabled,
  onEnabledChange,
  disabled = false,
  children
}) => {
  const handleChange = React.useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) =>
      onEnabledChange(e.target.checked),
    [onEnabledChange]
  )

  const checkboxOption = React.useMemo(
    () => ({
      label: title,
      hintText: description,
      nativeInputProps: {
        checked: enabled,
        onChange: handleChange,
        disabled
      }
    }),
    [title, description, enabled, handleChange, disabled]
  )

  return (
    <div
      className={fr.cx('fr-p-2w')}
      style={{
        border: '1px solid var(--border-default-grey, #ddd)',
        borderRadius: '4px',
        backgroundColor: enabled
          ? 'var(--background-alt-blue-france, #f5f5fe)'
          : 'var(--background-default-grey, #ffffff)'
      }}
    >
      <Checkbox options={[checkboxOption]} />

      {/* Show configuration fields directly when feature is enabled */}
      {enabled && children && (
        <section
          className={fr.cx('fr-mt-2w')}
          aria-live="polite"
          aria-label="Configuration options"
        >
          {children}
        </section>
      )}
    </div>
  )
}

export default FeatureConfigSection
