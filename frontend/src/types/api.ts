// Import and re-export the generated types for easier imports
import type { components, operations, paths } from './api-generated'

export type { components, operations, paths }

// Type aliases for commonly used types
export type JobStatus = components['schemas']['JobStatus']
export type ProcessingResponse = components['schemas']['ProcessingResponse']
export type ProgressResponse = components['schemas']['ProgressResponse']
export type PreviewResponse = components['schemas']['PreviewResponse']
export type AmendmentPreview = components['schemas']['AmendmentPreview']

export interface ProcessJobResponse {
  job_id: string
  status: JobStatus
  message: string
}

export interface JobStatusResponse {
  job_id: string
  status: JobStatus
  percent: number
  message: string | null
  started_at: string
  updated_at: string
}

export interface AllotmentsConfig {
  enabled: boolean
  column?: string
  similarity_threshold?: number
}

export interface SimilaritiesWithinLecturesConfig {
  enabled: boolean
  column?: string
  similarity_threshold?: number
}

export interface SimilaritySearchConfig {
  enabled: boolean
  origin_project?: string
  clustering_similarity_thresholds?: Record<string, number>
  fuzzy_match_similarity_thresholds?: Record<string, number>
  similarity_threshold_overrides?: Record<string, number>
  columns_to_copy?: Record<string, { enabled: boolean; condition?: string }>
}

export interface AttributionConfig {
  enabled: boolean
  project_name?: string
}

export interface SummaryConfig {
  enabled: boolean
}

export interface OpinionConfig {
  enabled: boolean
}

export interface ProcessingConfig {
  allotments?: AllotmentsConfig
  similarities_within_lectures?: SimilaritiesWithinLecturesConfig
  similarity_search?: SimilaritySearchConfig
  attribution?: AttributionConfig
  opinion?: OpinionConfig
  summary?: SummaryConfig
}

export interface ConfigFilesResponse {
  files: string[]
  total: number
}

export interface ProcessingRequest {
  config_file: string
  processing_config: ProcessingConfig
}

export interface ApiError {
  detail: string
  status_code: number
}
