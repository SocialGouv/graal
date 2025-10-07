import React from 'react';
import { Checkbox } from '@codegouvfr/react-dsfr/Checkbox';
import { fr } from '@codegouvfr/react-dsfr';

export interface SimpleToggleConfigProps {
  label: string;
  description?: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
}

export const SimpleToggleConfig: React.FC<SimpleToggleConfigProps> = ({
  label,
  description,
  checked,
  onChange,
  disabled = false,
}) => {
  return (
    <div className={fr.cx('fr-p-2w')}>
      <Checkbox
        options={[
          {
            label,
            hintText: description,
            nativeInputProps: {
              checked,
              onChange: (e: React.ChangeEvent<HTMLInputElement>) => onChange(e.target.checked),
              disabled,
            },
          },
        ]}
      />
    </div>
  );
};

export default SimpleToggleConfig;
