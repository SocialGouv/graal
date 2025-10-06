import { useCallback } from 'react';

// Validation result interface
export interface ValidationResult {
  isValid: boolean;
  errorMessage: string | null;
}

// Origin project validation rules
const ORIGIN_PROJECT_MIN_LENGTH = 2;
const ORIGIN_PROJECT_MAX_LENGTH = 100;

// Allotments validation rules
const SIMILARITY_THRESHOLD_MIN = 0;
const SIMILARITY_THRESHOLD_MAX = 1;
const VALID_COLUMNS = ['Corps amdt', 'Exposé amdt'] as const;

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
  const validateOriginProject = useCallback((value: string): ValidationResult => {
    const trimmed = value.trim();

    if (!trimmed) {
      return {
        isValid: false,
        errorMessage: 'Le projet d\'origine est obligatoire.',
      };
    }

    if (trimmed.length < ORIGIN_PROJECT_MIN_LENGTH) {
      return {
        isValid: false,
        errorMessage: 'Le projet d\'origine doit contenir au moins 2 caractères.',
      };
    }

    if (trimmed.length > ORIGIN_PROJECT_MAX_LENGTH) {
      return {
        isValid: false,
        errorMessage: 'Le projet d\'origine ne peut pas dépasser 100 caractères.',
      };
    }

    return {
      isValid: true,
      errorMessage: null,
    };
  }, []);

  /**
   * Validates the origin project field and returns only boolean
   * @param value - The value to validate
   * @returns boolean indicating if the value is valid
   */
  const isOriginProjectValid = useCallback((value: string): boolean => {
    return validateOriginProject(value).isValid;
  }, [validateOriginProject]);

  /**
   * Validates the origin project field and returns only error message
   * @param value - The value to validate
   * @returns string error message or null if valid
   */
  const getOriginProjectError = useCallback((value: string): string | null => {
    return validateOriginProject(value).errorMessage;
  }, [validateOriginProject]);

  /**
   * Validates the allotments column field
   * @param value - The column value to validate
   * @param enabled - Whether allotments is enabled
   * @returns ValidationResult with isValid boolean and errorMessage
   */
  const validateAllotmentsColumn = useCallback((value: string, enabled: boolean): ValidationResult => {
    if (!enabled) {
      return { isValid: true, errorMessage: null };
    }

    if (!value) {
      return {
        isValid: false,
        errorMessage: 'La colonne est obligatoire quand l\'allotissement est activé.',
      };
    }

    if (!VALID_COLUMNS.includes(value as any)) {
      return {
        isValid: false,
        errorMessage: 'Veuillez sélectionner une colonne valide.',
      };
    }

    return { isValid: true, errorMessage: null };
  }, []);

  /**
   * Validates the similarity threshold field
   * @param value - The threshold value to validate
   * @param enabled - Whether allotments is enabled
   * @returns ValidationResult with isValid boolean and errorMessage
   */
  const validateSimilarityThreshold = useCallback((value: number, enabled: boolean): ValidationResult => {
    if (!enabled) {
      return { isValid: true, errorMessage: null };
    }

    if (isNaN(value)) {
      return {
        isValid: false,
        errorMessage: 'Le seuil de similarité doit être un nombre.',
      };
    }

    if (value < SIMILARITY_THRESHOLD_MIN || value > SIMILARITY_THRESHOLD_MAX) {
      return {
        isValid: false,
        errorMessage: `Le seuil doit être compris entre ${SIMILARITY_THRESHOLD_MIN} et ${SIMILARITY_THRESHOLD_MAX}.`,
      };
    }

    return { isValid: true, errorMessage: null };
  }, []);

  /**
   * Gets error message for allotments column
   */
  const getAllotmentsColumnError = useCallback((value: string, enabled: boolean): string | null => {
    return validateAllotmentsColumn(value, enabled).errorMessage;
  }, [validateAllotmentsColumn]);

  /**
   * Gets error message for similarity threshold
   */
  const getSimilarityThresholdError = useCallback((value: number, enabled: boolean): string | null => {
    return validateSimilarityThreshold(value, enabled).errorMessage;
  }, [validateSimilarityThreshold]);

  return {
    validateOriginProject,
    isOriginProjectValid,
    getOriginProjectError,
    validateAllotmentsColumn,
    validateSimilarityThreshold,
    getAllotmentsColumnError,
    getSimilarityThresholdError,
  };
};

export default useValidation;
