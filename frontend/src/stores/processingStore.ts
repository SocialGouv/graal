import { create } from 'zustand'
import type { AmendmentPreview, JobStatus } from '../types/api'

export interface ColumnToCopyConfig {
  enabled: boolean
  condition?: string
}

export type ThresholdConfig = Record<string, number>
export type ThresholdOverrides = Record<string, Record<string, number>>

export interface ProcessingConfig {
  allotments: {
    enabled: boolean
    column: 'Corps amdt' | 'Exposé amdt'
    similarity_threshold: number
  }
  similaritiesWithinLectures: {
    enabled: boolean
    column: 'Corps amdt' | 'Exposé amdt'
    similarity_threshold: number
  }
  similaritySearch: {
    enabled: boolean
    originProject: string
    clusteringSimilarityThresholds: ThresholdConfig
    fuzzyMatchSimilarityThresholds: ThresholdConfig
    similarityThresholdOverrides: ThresholdOverrides
    columnsToCopy: Record<string, ColumnToCopyConfig>
  }
  attribution: {
    enabled: boolean
    project_name: string
  }
  defaultOpinion: {
    enabled: boolean
  }
  // Processing options (top-level, not nested under any feature)
  no_value_overwrite: boolean
  placeholder_amdt_body: boolean
}

export interface ProcessingState {
  // File upload state
  uploadedFile: File | null
  uploadProgress: number

  // Config file selection
  selectedConfigFile: string | null

  // Processing configuration
  processingConfig: ProcessingConfig

  // Job processing state
  jobId: string | null
  processingStatus: 'idle' | 'uploading' | JobStatus
  progressPercent: number
  progressMessage: string | null
  startedAt: string | null
  updatedAt: string | null

  // Results state
  resultsPreview: AmendmentPreview[] | null
  totalRows: number

  // Error handling
  error: string | null

  // Actions
  setUploadedFile: (file: File | null) => void
  setUploadProgress: (progress: number) => void
  setSelectedConfigFile: (filename: string | null) => void
  setProcessingConfig: (config: ProcessingConfig) => void
  setJobId: (id: string | null) => void
  updateProgress: (
    status: ProcessingState['processingStatus'],
    percent: number,
    message?: string | null,
    startedAt?: string,
    updatedAt?: string
  ) => void
  setResults: (results: AmendmentPreview[], totalRows: number) => void
  setError: (error: string | null) => void
  reset: () => void
}

const initialState = {
  uploadedFile: null,
  uploadProgress: 0,
  selectedConfigFile: null,
  processingConfig: {
    allotments: {
      enabled: false,
      column: 'Corps amdt' as const,
      similarity_threshold: 0.999
    },
    similaritiesWithinLectures: {
      enabled: false,
      column: 'Exposé amdt' as const,
      similarity_threshold: 0.8
    },
    similaritySearch: {
      enabled: false,
      originProject: '',
      clusteringSimilarityThresholds: {
        'Exposé amdt': 0.4,
        'Corps amdt': 0.4
      },
      fuzzyMatchSimilarityThresholds: {
        'Exposé amdt': 0.4,
        'Corps amdt': 0.9
      },
      similarityThresholdOverrides: {},
      columnsToCopy: {
        Réponse: { enabled: true },
        Sort: { enabled: true, condition: 'irrecevable' },
        'Objet amdt': { enabled: false }
      }
    },
    attribution: {
      enabled: true,
      project_name: 'PLF'
    },
    defaultOpinion: {
      enabled: false
    },
    // Processing options at top level
    no_value_overwrite: false,
    placeholder_amdt_body: false
  },
  jobId: null,
  processingStatus: 'idle' as const,
  progressPercent: 0,
  progressMessage: null,
  startedAt: null,
  updatedAt: null,
  resultsPreview: null,
  totalRows: 0,
  error: null
}

export const useProcessingStore = create<ProcessingState>((set) => ({
  ...initialState,

  setUploadedFile: (file) =>
    set((state) => ({
      ...state,
      uploadedFile: file,
      error: null
    })),

  setUploadProgress: (progress) =>
    set((state) => ({
      ...state,
      uploadProgress: progress
    })),

  setSelectedConfigFile: (filename) =>
    set((state) => ({
      ...state,
      selectedConfigFile: filename,
      error: null
    })),

  setProcessingConfig: (config) =>
    set((state) => ({
      ...state,
      processingConfig: config,
      error: null
    })),

  setJobId: (id) =>
    set((state) => ({
      ...state,
      jobId: id
    })),

  updateProgress: (status, percent, message, startedAt, updatedAt) =>
    set((state) => ({
      ...state,
      processingStatus: status,
      progressPercent: percent,
      progressMessage: message ?? state.progressMessage,
      startedAt: startedAt ?? state.startedAt,
      updatedAt: updatedAt ?? state.updatedAt
    })),

  setResults: (results, totalRows) =>
    set((state) => ({
      ...state,
      resultsPreview: results,
      totalRows
    })),

  setError: (error) =>
    set((state) => ({
      ...state,
      error,
      processingStatus: error ? 'failed' : state.processingStatus
    })),

  reset: () => set(initialState)
}))
