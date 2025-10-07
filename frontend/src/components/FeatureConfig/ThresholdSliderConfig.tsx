import React from 'react';
import { Range } from '@codegouvfr/react-dsfr/Range';
import { fr } from '@codegouvfr/react-dsfr';

export interface ThresholdSliderConfigProps {
  label: string;
  hint?: string;
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  step?: number;
  disabled?: boolean;
  error?: string;
}

export const ThresholdSliderConfig: React.FC<ThresholdSliderConfigProps> = ({
  label,
  hint,
  value,
  onChange,
  min = 0,
  max = 1,
  step = 0.01,
  disabled = false,
  error,
}) => {
  return (
    <div className={fr.cx('fr-grid-row', 'fr-grid-row--gutters')}>
      <div className={fr.cx('fr-col-12', 'fr-col-md-6')}>
        <Range
          label={label}
          hintText={hint}
          min={min}
          max={max}
          step={step}
          state={error ? 'error' : 'default'}
          stateRelatedMessage={error || undefined}
          nativeInputProps={{
            value,
            onChange: (e) => {
              const newValue = parseFloat(e.target.value);
              if (!isNaN(newValue) && newValue >= min && newValue <= max) {
                onChange(newValue);
              }
            },
            disabled,
          }}
        />
        <div className={fr.cx('fr-text--sm', 'fr-mt-1w')}>
          Valeur actuelle: {value.toFixed(2)}
        </div>
      </div>
    </div>
  );
};

export default ThresholdSliderConfig;
