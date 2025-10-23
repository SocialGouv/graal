/**
 * Feature flags for controlling UI visibility and behavior.
 *
 * These flags allow easily enabling/disabling UI features without
 * removing the underlying code functionality.
 *
 * ## How to Re-enable Hidden Columns:
 *
 * To show "Réponse" or "Sort" columns in the UI again:
 * 1. Set the corresponding flag to `true` in DEFAULT_FEATURE_FLAGS below
 * 2. The columns will appear in the similarity search configuration
 * 3. Users can then modify their settings in the UI
 *
 * ## Important Notes:
 *
 * - Hidden columns still use their backend default values
 * - Backend defaults are defined in:
 *   - Backend: graal/api/models/requests.py (SimilaritySearchConfig)
 *   - Frontend: frontend/src/stores/processingStore.ts (initialState)
 * - The defaults are:
 *   - Réponse: { enabled: true }
 *   - Sort: { enabled: true, condition: "irrecevable" }
 *   - Objet amdt: { enabled: false }
 * - These defaults are sent to the backend regardless of UI visibility
 */

export interface ColumnToCopyVisibility {
  /** Whether to show the "Réponse" column configuration in the UI */
  showReponse: boolean
  /** Whether to show the "Sort" column configuration in the UI */
  showSort: boolean
  /** Whether to show the "Objet amdt" column configuration in the UI */
  showObjetAmdt: boolean
}

export interface FeatureFlags {
  /** Controls which columns to copy are visible in the UI */
  columnsToCopyVisibility: ColumnToCopyVisibility
  /** Whether to show the summary generation (Objet amdt) feature in the UI */
  showSummaryGeneration: boolean
}

/**
 * Default feature flags configuration.
 *
 * Modify these values to show/hide features in the UI.
 * The backend will continue to use the default values for hidden columns.
 */
export const DEFAULT_FEATURE_FLAGS: FeatureFlags = {
  columnsToCopyVisibility: {
    // Hide Réponse and Sort from UI - they use backend defaults
    showReponse: false,
    showSort: false,
    // Show Objet amdt as it's user-configurable
    showObjetAmdt: true
  },
  // Show summary generation feature
  showSummaryGeneration: true
}
