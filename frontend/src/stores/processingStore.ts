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
    databaseFile: string | null
    clusteringSimilarityThresholds: ThresholdConfig
    fuzzyMatchSimilarityThresholds: ThresholdConfig
    similarityThresholdOverrides: ThresholdOverrides
    columnsToCopy: Record<string, ColumnToCopyConfig>
    should_overwrite: boolean
  }
  attribution: {
    enabled: boolean
    project_name: string
    should_overwrite: boolean
  }
  defaultOpinion: {
    enabled: boolean
    should_overwrite: boolean
  }
  summaryGeneration: {
    enabled: boolean
    should_overwrite: boolean
    llm_type: 'scaleway' | 'albert' | 'ollama' | 'vllm' | 'fake' | null
    llm_credentials: {
      base_url?: string
      api_key?: string
      model_name?: string
      endpoint?: string
      user?: string
      password?: string
    }
  }
  // Processing options (top-level, not nested under any feature)
  placeholder_amdt_body: boolean
}

export interface UploadedFileInfo {
  uploadId: string
  filename: string
  fileHash: string
  s3Key: string
  size: number
  timestamp: number
  originProject: string
  uploadProgress: number
  dateAutoExtracted?: boolean
}

export interface DatabaseBuilderState {
  selectedConfigFile: string | null
  databaseName: string
  uploadedFiles: UploadedFileInfo[]
  buildProgress: number
  isBuilding: boolean
}

export interface ProcessingState {
  // Stepper navigation
  currentStep: number

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

  // Database builder state
  databaseBuilder: DatabaseBuilderState

  // Actions
  setCurrentStep: (step: number) => void
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

  // Database builder actions
  setDatabaseConfigFile: (filename: string | null) => void
  setDatabaseName: (name: string) => void
  addUploadedFile: (file: Omit<UploadedFileInfo, 'uploadProgress'>) => void
  removeUploadedFile: (uploadId: string) => void
  updateFileUploadProgress: (uploadId: string, progress: number) => void
  setBuildProgress: (progress: number) => void
  setIsBuilding: (isBuilding: boolean) => void
  clearUploadedFiles: () => void
  resetDatabaseBuilder: () => void
}

const initialState = {
  currentStep: 1,
  uploadedFile: null,
  uploadProgress: 0,
  selectedConfigFile: null,
  processingConfig: {
    allotments: {
      enabled: true,
      column: 'Corps amdt' as const,
      similarity_threshold: 0.999
    },
    similaritiesWithinLectures: {
      enabled: true,
      column: 'Exposé amdt' as const,
      similarity_threshold: 0.8
    },
    similaritySearch: {
      enabled: true,
      originProject: '',
      databaseFile: null,
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
      },
      should_overwrite: true
    },
    attribution: {
      enabled: true,
      project_name: 'PLFSS',
      should_overwrite: true
    },
    defaultOpinion: {
      enabled: true,
      should_overwrite: true
    },
    summaryGeneration: {
      enabled: true,
      should_overwrite: true,
      llm_type: 'fake',
      llm_credentials: {}
    },
    // Processing options at top level
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
  error: null,
  databaseBuilder: {
    selectedConfigFile: null,
    databaseName: '',
    uploadedFiles: [],
    buildProgress: 0,
    isBuilding: false
  }
}

export const useProcessingStore = create<ProcessingState>((set) => ({
  ...initialState,

  setCurrentStep: (step) =>
    set((state) => ({
      ...state,
      currentStep: step
    })),

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

  reset: () => set(initialState),

  // Database builder action implementations
  setDatabaseConfigFile: (filename) =>
    set((state) => ({
      databaseBuilder: {
        ...state.databaseBuilder,
        selectedConfigFile: filename
      }
    })),

  setDatabaseName: (name) =>
    set((state) => ({
      databaseBuilder: { ...state.databaseBuilder, databaseName: name }
    })),

  addUploadedFile: (file) =>
    set((state) => ({
      databaseBuilder: {
        ...state.databaseBuilder,
        uploadedFiles: [
          ...state.databaseBuilder.uploadedFiles,
          { ...file, uploadProgress: 100 }
        ]
      }
    })),

  removeUploadedFile: (uploadId) =>
    set((state) => ({
      databaseBuilder: {
        ...state.databaseBuilder,
        uploadedFiles: state.databaseBuilder.uploadedFiles.filter(
          (f) => f.uploadId !== uploadId
        )
      }
    })),

  updateFileUploadProgress: (uploadId, progress) =>
    set((state) => ({
      databaseBuilder: {
        ...state.databaseBuilder,
        uploadedFiles: state.databaseBuilder.uploadedFiles.map((f) =>
          f.uploadId === uploadId ? { ...f, uploadProgress: progress } : f
        )
      }
    })),

  setBuildProgress: (progress) =>
    set((state) => ({
      databaseBuilder: { ...state.databaseBuilder, buildProgress: progress }
    })),

  setIsBuilding: (isBuilding) =>
    set((state) => ({
      databaseBuilder: { ...state.databaseBuilder, isBuilding }
    })),

  clearUploadedFiles: () =>
    set((state) => ({
      databaseBuilder: {
        ...state.databaseBuilder,
        uploadedFiles: []
      }
    })),

  resetDatabaseBuilder: () =>
    set((_state) => ({
      databaseBuilder: {
        selectedConfigFile: null,
        databaseName: '',
        uploadedFiles: [],
        buildProgress: 0,
        isBuilding: false
      }
    }))
}))
