import { create } from 'zustand';
import type { AmendmentPreview, JobStatus } from '../types/api';

export interface ProcessingState {
  // File upload state
  uploadedFile: File | null;
  uploadProgress: number;

  // Origin project state
  originProject: string;

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
  setOriginProject: (project: string) => void;
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
  originProject: '',
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

  setOriginProject: (project) =>
    set((state) => ({
      ...state,
      originProject: project,
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
