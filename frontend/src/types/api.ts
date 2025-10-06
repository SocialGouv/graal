// Import and re-export the generated types for easier imports
import type {
  components,
  operations,
  paths
} from './api-generated';

export type {
  components,
  operations,
  paths
};

// Type aliases for commonly used types
export type JobStatus = components['schemas']['JobStatus'];
export type ProcessingResponse = components['schemas']['ProcessingResponse'];
export type ProgressResponse = components['schemas']['ProgressResponse'];
export type PreviewResponse = components['schemas']['PreviewResponse'];
export type AmendmentPreview = components['schemas']['AmendmentPreview'];

export interface ProcessJobResponse {
  job_id: string;
  status: JobStatus;
  message: string;
}

export interface JobStatusResponse {
  job_id: string;
  status: JobStatus;
  percent: number;
  message: string | null;
  started_at: string;
  updated_at: string;
}

export interface ProcessingConfig {
  origin_project: string;
  // Future configuration fields will be added here:
  // processing_date?: string;
  // enabled_features?: string[];
  // custom_thresholds?: Record<string, number>;
}

export interface ProcessingRequest {
  processing_config: ProcessingConfig;
  // Future parameters can be easily added here:
  // processingDate?: string;
  // userPreferences?: Record<string, any>;
  // featureFlags?: string[];
}

export interface ApiError {
  detail: string;
  status_code: number;
}
