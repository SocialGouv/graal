import React from 'react';
import { Select } from '@codegouvfr/react-dsfr/Select';
import { Range } from '@codegouvfr/react-dsfr/Range';
import { Input } from '@codegouvfr/react-dsfr/Input';
import { fr } from '@codegouvfr/react-dsfr';

export interface ColumnOption {
  label: string;
  value: string;
}

export interface ColumnSimilarityConfigProps {
  // Column selection
  columnLabel?: string;
  columnHint?: string;
  columnOptions: ColumnOption[];
  selectedColumn: string;
  onColumnChange: (value: string) => void;
  columnError?: string;

  // Similarity threshold
  thresholdLabel?: string;
  thresholdHint?: string;
  thresholdMin?: number;
  thresholdMax?: number;
  thresholdStep?: number;
  thresholdValue: number;
  onThresholdChange: (value: number) => void;
  thresholdError?: string;

  // General
  disabled?: boolean;
}

export const ColumnSimilarityConfig: React.FC<ColumnSimilarityConfigProps> = ({
  columnLabel = "Colonne à analyser",
  columnHint = "Choisissez la colonne utilisée pour comparer la similarité",
  columnOptions,
  selectedColumn,
  onColumnChange,
  columnError,
  thresholdLabel = "Seuil de similarité",
  thresholdHint = "Seuil au-dessus duquel les éléments sont considérés comme similaires",
  thresholdMin = 0,
  thresholdMax = 1,
  thresholdStep = 0.001,
  thresholdValue,
  onThresholdChange,
  thresholdError,
  disabled = false,
}) => {
  return (
    <div className={fr.cx('fr-grid-row', 'fr-grid-row--gutters')}>
      <div className={fr.cx('fr-col-12', 'fr-col-md-6')}>
        <Select
          label={columnLabel}
          hint={columnHint}
          state={columnError ? 'error' : 'default'}
          stateRelatedMessage={columnError || undefined}
          nativeSelectProps={{
            value: selectedColumn,
            onChange: (e) => onColumnChange(e.target.value),
            disabled,
          }}
        >
          <option value="" disabled>
            Sélectionnez une colonne
          </option>
          {columnOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </Select>
      </div>

      <div className={fr.cx('fr-col-12', 'fr-col-md-6')}>
        <div className={fr.cx('fr-grid-row', 'fr-grid-row--gutters')}>
          <div className={fr.cx('fr-col-8')}>
            <Range
              label={thresholdLabel}
              hintText={thresholdHint}
              min={thresholdMin}
              max={thresholdMax}
              step={thresholdStep}
              nativeInputProps={{
                value: thresholdValue,
                onChange: (e) => onThresholdChange(parseFloat(e.target.value)),
                disabled,
              }}
            />
          </div>
          <div className={fr.cx('fr-col-4')}>
            <Input
              label="Valeur"
              state={thresholdError ? 'error' : 'default'}
              stateRelatedMessage={thresholdError || undefined}
              nativeInputProps={{
                type: 'number',
                min: thresholdMin,
                max: thresholdMax,
                step: thresholdStep,
                value: thresholdValue,
                onChange: (e) => {
                  const parsed = parseFloat(e.target.value);
                  if (!isNaN(parsed)) {
                    onThresholdChange(parsed);
                  }
                },
                disabled,
              }}
            />
          </div>
        </div>
      </div>
    </div>
  );
};

export default ColumnSimilarityConfig;
