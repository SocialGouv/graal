import React from 'react';
import { Select } from '@codegouvfr/react-dsfr/Select';
import { fr } from '@codegouvfr/react-dsfr';

export interface ProjectOption {
  label: string;
  value: string;
}

export interface ProjectSelectionConfigProps {
  label?: string;
  hint?: string;
  projectOptions: ProjectOption[];
  selectedProject: string;
  onProjectChange: (value: string) => void;
  error?: string;
  disabled?: boolean;
}

export const ProjectSelectionConfig: React.FC<ProjectSelectionConfigProps> = ({
  label = "Projet",
  hint = "Sélectionnez le projet pour cette fonctionnalité",
  projectOptions,
  selectedProject,
  onProjectChange,
  error,
  disabled = false,
}) => {
  return (
    <div className={fr.cx('fr-grid-row', 'fr-grid-row--gutters')}>
      <div className={fr.cx('fr-col-12', 'fr-col-md-6')}>
        <Select
          label={label}
          hint={hint}
          state={error ? 'error' : 'default'}
          stateRelatedMessage={error || undefined}
          nativeSelectProps={{
            value: selectedProject,
            onChange: (e) => onProjectChange(e.target.value),
            disabled,
          }}
        >
          <option value="" disabled>
            Sélectionnez un projet
          </option>
          {projectOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </Select>
      </div>
    </div>
  );
};

export default ProjectSelectionConfig;
