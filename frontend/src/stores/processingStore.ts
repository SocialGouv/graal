import { create } from 'zustand';
import type { AmendmentPreview, JobStatus } from '../types/api';

export interface ProcessingConfig {
  originProject: string;
  allotments: {
    enabled: boolean;
    column: 'Corps amdt' | 'Exposé amdt';
    similarity_threshold: number;
  };
  similaritiesWithinLectures: {
    enabled: boolean;
    column: 'Corps amdt' | 'Exposé amdt';
    similarity_threshold: number;
  };
  similaritySearch: {
    enabled: boolean;
  };
  attribution: {
    enabled: boolean;
    project_name: string;
  };
  defaultOpinion: {
    enabled: boolean;
  };
}

export interface ProcessingState {
  // File upload state
  uploadedFile: File | null;
  uploadProgress: number;

  // Processing configuration
  processingConfig: ProcessingConfig;

  // Job processing state
  jobId: string | null;
  processingStatus: 'idle' | 'uploading' | JobStatus;
  progressPercent: number;
  progressMessage: string | null;
  startedAt: string | null;
  updatedAt: string | null;

  // Results state
  resultsPreview: AmendmentPreview[] | null;
  totalRows: number;

  // Error handling
  error: string | null;

  // Actions
  setUploadedFile: (file: File | null) => void;
  setUploadProgress: (progress: number) => void;
  setProcessingConfig: (config: ProcessingConfig) => void;
  setJobId: (id: string | null) => void;
  updateProgress: (
    status: ProcessingState['processingStatus'],
    percent: number,
    message?: string | null,
    startedAt?: string,
    updatedAt?: string
  ) => void;
  setResults: (results: AmendmentPreview[], totalRows: number) => void;
  setError: (error: string | null) => void;
  reset: () => void;
}

const initialState = {
  uploadedFile: null,
  uploadProgress: 0,
  processingConfig: {
    originProject: '',
    allotments: {
      enabled: false,
      column: 'Corps amdt' as const,
      similarity_threshold: 0.9999,
    },
    similaritiesWithinLectures: {
      enabled: false,
      column: 'Exposé amdt' as const,
      similarity_threshold: 0.8,
    },
    similaritySearch: {
      enabled: false,
    },
    attribution: {
      enabled: true,
      project_name: 'PLF',
    },
    defaultOpinion: {
      enabled: false,
    },
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
};

export const useProcessingStore = create<ProcessingState>((set) => ({
  ...initialState,

  setUploadedFile: (file) =>
    set((state) => ({
      ...state,
      uploadedFile: file,
      error: null,
    })),

  setUploadProgress: (progress) =>
    set((state) => ({
      ...state,
      uploadProgress: progress,
    })),

  setProcessingConfig: (config) =>
    set((state) => ({
      ...state,
      processingConfig: config,
      error: null,
    })),

  setJobId: (id) =>
    set((state) => ({
      ...state,
      jobId: id,
    })),

  updateProgress: (status, percent, message, startedAt, updatedAt) =>
    set((state) => ({
      ...state,
      processingStatus: status,
      progressPercent: percent,
      progressMessage: message ?? state.progressMessage,
      startedAt: startedAt ?? state.startedAt,
      updatedAt: updatedAt ?? state.updatedAt,
    })),

  setResults: (results, totalRows) =>
    set((state) => ({
      ...state,
      resultsPreview: results,
      totalRows,
    })),

  setError: (error) =>
    set((state) => ({
      ...state,
      error,
      processingStatus: error ? 'failed' : state.processingStatus,
    })),

  reset: () => set(initialState),
}));
