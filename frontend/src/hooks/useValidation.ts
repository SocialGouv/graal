import { useCallback } from 'react'

// Validation result interface
export interface ValidationResult {
  isValid: boolean
  errorMessage: string | null
}

// Origin project validation rules
const ORIGIN_PROJECT_MIN_LENGTH = 2
const ORIGIN_PROJECT_MAX_LENGTH = 100
// Mirrors the backend blocklist: control chars and HTML/injection vectors.
// Unicode letters (accents, apostrophes, etc.) are explicitly allowed.
// NOTE: We use a Unicode property escape instead of explicit ASCII control ranges
// to satisfy ESLint's `no-control-regex` rule.
const ORIGIN_PROJECT_FORBIDDEN = /[\p{Cc}<>&"\\]/u

// Allotments validation rules
const SIMILARITY_THRESHOLD_MIN = 0
const SIMILARITY_THRESHOLD_MAX = 1
const VALID_COLUMNS = ['Corps amdt', 'Exposé amdt'] as const

/**
 * Custom hook for form validation logic
 * Provides consistent validation across components
 */
export const useValidation = () => {
  /**
   * Validates the origin project field
   * @param value - The value to validate
   * @returns ValidationResult with isValid boolean and errorMessage
   */
  const validateOriginProject = useCallback(
    (value: string): ValidationResult => {
      const trimmed = value.trim()

      if (!trimmed) {
        return {
          isValid: false,
          errorMessage: "Le projet d'origine est obligatoire."
        }
      }

      if (trimmed.length < ORIGIN_PROJECT_MIN_LENGTH) {
        return {
          isValid: false,
          errorMessage:
            "Le projet d'origine doit contenir au moins 2 caractères."
        }
      }

      if (trimmed.length > ORIGIN_PROJECT_MAX_LENGTH) {
        return {
          isValid: false,
          errorMessage:
            "Le projet d'origine ne peut pas dépasser 100 caractères."
        }
      }

      if (ORIGIN_PROJECT_FORBIDDEN.test(trimmed)) {
        return {
          isValid: false,
          errorMessage:
            'Le projet d\'origine contient des caractères invalides (évitez < > & " \\).'
        }
      }

      return {
        isValid: true,
        errorMessage: null
      }
    },
    []
  )

  /**
   * Validates the origin project field and returns only boolean
   * @param value - The value to validate
   * @returns boolean indicating if the value is valid
   */
  const isOriginProjectValid = useCallback(
    (value: string): boolean => {
      return validateOriginProject(value).isValid
    },
    [validateOriginProject]
  )

  /**
   * Validates the origin project field and returns only error message
   * @param value - The value to validate
   * @returns string error message or null if valid
   */
  const getOriginProjectError = useCallback(
    (value: string): string | null => {
      return validateOriginProject(value).errorMessage
    },
    [validateOriginProject]
  )

  /**
   * Validates the allotments column field
   * @param value - The column value to validate
   * @param enabled - Whether allotments is enabled
   * @returns ValidationResult with isValid boolean and errorMessage
   */
  const validateAllotmentsColumn = useCallback(
    (value: string, enabled: boolean): ValidationResult => {
      if (!enabled) {
        return { isValid: true, errorMessage: null }
      }

      if (!value) {
        return {
          isValid: false,
          errorMessage:
            "La colonne est obligatoire quand l'allotissement est activé."
        }
      }

      if (!VALID_COLUMNS.includes(value as any)) {
        return {
          isValid: false,
          errorMessage: 'Veuillez sélectionner une colonne valide.'
        }
      }

      return { isValid: true, errorMessage: null }
    },
    []
  )

  /**
   * Validates the similarity threshold field
   * @param value - The threshold value to validate
   * @param enabled - Whether allotments is enabled
   * @returns ValidationResult with isValid boolean and errorMessage
   */
  const validateSimilarityThreshold = useCallback(
    (value: number, enabled: boolean): ValidationResult => {
      if (!enabled) {
        return { isValid: true, errorMessage: null }
      }

      if (isNaN(value)) {
        return {
          isValid: false,
          errorMessage: 'Le seuil de similarité doit être un nombre.'
        }
      }

      if (
        value < SIMILARITY_THRESHOLD_MIN ||
        value > SIMILARITY_THRESHOLD_MAX
      ) {
        return {
          isValid: false,
          errorMessage: `Le seuil doit être compris entre ${SIMILARITY_THRESHOLD_MIN} et ${SIMILARITY_THRESHOLD_MAX}.`
        }
      }

      return { isValid: true, errorMessage: null }
    },
    []
  )

  /**
   * Gets error message for allotments column
   */
  const getAllotmentsColumnError = useCallback(
    (value: string, enabled: boolean): string | null => {
      return validateAllotmentsColumn(value, enabled).errorMessage
    },
    [validateAllotmentsColumn]
  )

  /**
   * Gets error message for similarity threshold
   */
  const getSimilarityThresholdError = useCallback(
    (value: number, enabled: boolean): string | null => {
      return validateSimilarityThreshold(value, enabled).errorMessage
    },
    [validateSimilarityThreshold]
  )

  /**
   * Validates the config file selection
   * @param configFile - The config file path
   * @returns string error message or null if valid
   */
  const getConfigFileError = useCallback(
    (configFile: string | null): string | null => {
      if (!configFile) {
        return 'Veuillez sélectionner un fichier de configuration'
      }

      if (!configFile.endsWith('.xlsx')) {
        return 'Le fichier doit être au format Excel (.xlsx)'
      }

      return null
    },
    []
  )

  /**
   * Checks if at least one feature is enabled
   * Future-proof: Automatically checks all properties with an 'enabled' field
   * @param processingConfig - The processing configuration to check
   * @returns boolean indicating if at least one feature is enabled
   */
  const isAnyFeatureEnabled = useCallback(
    (processingConfig: Record<string, any>): boolean => {
      // Iterate through all properties in processingConfig
      // and check if any have an 'enabled' property set to true
      return Object.values(processingConfig).some(
        (featureConfig) =>
          featureConfig &&
          typeof featureConfig === 'object' &&
          'enabled' in featureConfig &&
          featureConfig.enabled === true
      )
    },
    []
  )

  return {
    validateOriginProject,
    isOriginProjectValid,
    getOriginProjectError,
    validateAllotmentsColumn,
    validateSimilarityThreshold,
    getAllotmentsColumnError,
    getSimilarityThresholdError,
    getConfigFileError,
    isAnyFeatureEnabled
  }
}

export default useValidation
