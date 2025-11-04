import type { AttributionProjectOption, ColumnOption } from '../../FeatureConfig'

/**
 * Column options for allotments and similarities within lectures
 */
export const COLUMN_OPTIONS: ColumnOption[] = [
    { label: 'Corps amdt', value: 'Corps amdt' },
    { label: 'Exposé amdt', value: 'Exposé amdt' }
]

/**
 * Project options for attribution feature
 */
export const PROJECT_OPTIONS: AttributionProjectOption[] = [
    { label: 'PLF (Projet de Loi de Finances)', value: 'PLF' },
    {
        label: 'PLFSS (Projet de Loi de Financement de la Sécurité Sociale)',
        value: 'PLFSS'
    }
]
