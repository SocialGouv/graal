import React from 'react';
import { Checkbox } from '@codegouvfr/react-dsfr/Checkbox';
import { Accordion } from '@codegouvfr/react-dsfr/Accordion';
import { fr } from '@codegouvfr/react-dsfr';

interface FeatureConfigSectionProps {
  // Feature identification
  title: string;
  description: string;

  // State management
  enabled: boolean;
  onEnabledChange: (enabled: boolean) => void;

  // UI behavior
  showAdvancedConfig?: boolean;
  accordionLabel?: string;
  disabled?: boolean;

  // Configuration content
  children?: React.ReactNode;
}

export const FeatureConfigSection: React.FC<FeatureConfigSectionProps> = ({
  title,
  description,
  enabled,
  onEnabledChange,
  showAdvancedConfig = true,
  accordionLabel = "Configuration avancée",
  disabled = false,
  children,
}) => {
  const handleChange = React.useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => onEnabledChange(e.target.checked),
    [onEnabledChange]
  );

  const checkboxOption = React.useMemo(
    () => ({
      label: title,
      hintText: description,
      nativeInputProps: {
        checked: enabled,
        onChange: handleChange,
        disabled,
      },
    }),
    [title, description, enabled, handleChange, disabled]
  );

  // If feature is disabled or no advanced config, show simple checkbox
  if (!enabled || !showAdvancedConfig || !children) {
    return (
      <div
        className={fr.cx('fr-p-2w')}
        style={{
          border: '1px solid #ddd',
          borderRadius: '4px',
          backgroundColor: enabled ? '#f8f9fa' : '#ffffff'
        }}
      >
        <Checkbox options={[checkboxOption]} />
      </div>
    );
  }

  // If feature is enabled and has advanced config, show accordion
  return (
    <Accordion
      label={
        <div className={fr.cx('fr-grid-row', 'fr-grid-row--gutters', 'fr-grid-row--middle')}>
          <div className={fr.cx('fr-col')}>
            <Checkbox options={[checkboxOption]} />
          </div>
          <div
            className={fr.cx('fr-col')}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'flex-end',
              flex: '0 0 auto'
            }}
          >
            <span className={fr.cx('fr-text--sm', 'fr-text--bold')}>
              {accordionLabel}
            </span>
          </div>
        </div>
      }
      defaultExpanded={false}
    >
      <div className={fr.cx('fr-mt-2w')}>
        {children}
      </div>
    </Accordion>
  );
};

export default FeatureConfigSection;
