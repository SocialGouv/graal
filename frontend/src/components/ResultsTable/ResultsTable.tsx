import React from 'react';
import { Table } from '@codegouvfr/react-dsfr/Table';
import { Alert } from '@codegouvfr/react-dsfr/Alert';
import { fr } from '@codegouvfr/react-dsfr';
import { useProcessingStore } from '../../stores/processingStore';
import type { AmendmentResult } from '../../types/api';

interface ResultsTableProps {
  className?: string;
}

export const ResultsTable: React.FC<ResultsTableProps> = ({ className }) => {
  const { resultsPreview, totalRows, processingStatus } = useProcessingStore();

  if (processingStatus !== 'completed' || !resultsPreview || resultsPreview.length === 0) {
    return null;
  }

  // Get all unique column names from the results
  const getColumns = (data: AmendmentResult[]): string[] => {
    const columnSet = new Set<string>();
    data.forEach(row => {
      Object.keys(row).forEach(key => columnSet.add(key));
    });
    return Array.from(columnSet);
  };

  const columns = getColumns(resultsPreview);

  // Format cell value for display
  const formatCellValue = (value: string | number | null | undefined): string => {
    if (value === null || value === undefined) {
      return '';
    }
    if (typeof value === 'string' && value.length > 100) {
      return value.substring(0, 100) + '...';
    }
    return String(value);
  };

  // Create table headers as ReactNode[]
  const headers = columns.map(column =>
    column.charAt(0).toUpperCase() + column.slice(1).replace(/_/g, ' ')
  );

  // Create table data as ReactNode[][]
  const tableData = resultsPreview.map((row, rowIndex) => {
    return columns.map((column, columnIndex) => (
      <span key={`${rowIndex}-${columnIndex}`} title={String(row[column] || '')}>
        {formatCellValue(row[column])}
      </span>
    ));
  });

  return (
    <div className={`${fr.cx('fr-mb-4w')} ${className || ''}`}>
      <div className={fr.cx('fr-mb-2w')}>
        <h3 className={fr.cx('fr-h6')}>Aperçu des résultats</h3>
        <p className={fr.cx('fr-text--sm')}>
          Affichage des 10 premiers résultats sur {totalRows} amendements traités.
        </p>
      </div>

      <Alert
        severity="info"
        title="Aperçu limité"
        description="Seuls les 10 premiers résultats sont affichés ici. Téléchargez le fichier CSV complet pour voir tous les résultats."
        className={fr.cx('fr-mb-3w')}
        small
      />

      <div className="fr-table--responsive">
        <Table
          headers={headers}
          data={tableData}
          caption="Aperçu des amendements traités par GRAAL"
        />
      </div>

      <div className={fr.cx('fr-mt-2w', 'fr-text--sm')}>
        <p>
          <strong>Note :</strong> Les cellules longues sont tronquées pour l'affichage.
          Les fichiers téléchargables contiennent données complètes.
        </p>
      </div>
    </div>
  );
};

export default ResultsTable;
