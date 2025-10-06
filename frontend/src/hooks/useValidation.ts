import { useCallback } from 'react';

// Validation result interface
export interface ValidationResult {
  isValid: boolean;
  errorMessage: string | null;
}

// Origin project validation rules
const ORIGIN_PROJECT_MIN_LENGTH = 2;
const ORIGIN_PROJECT_MAX_LENGTH = 100;

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

  return {
    validateOriginProject,
    isOriginProjectValid,
    getOriginProjectError,
  };
};

export default useValidation;
