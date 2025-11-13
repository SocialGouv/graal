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
  database_file?: string | null
  clustering_similarity_thresholds?: Record<string, number>
  fuzzy_match_similarity_thresholds?: Record<string, number>
  similarity_threshold_overrides?: Record<string, number>
  columns_to_copy?: Record<string, { enabled: boolean; condition?: string }>
  should_overwrite?: boolean
}

export interface AttributionConfig {
  enabled: boolean
  project_name?: string
  should_overwrite?: boolean
}

export interface SummaryGenerationConfig {
  enabled: boolean
  should_overwrite?: boolean
  llm_type?:
    | 'scaleway'
    | 'albert'
    | 'ollama'
    | 'vllm'
    | 'fake'
    | 'mistral'
    | null
  llm_credentials?: {
    base_url?: string
    api_key?: string
    model_name?: string
    endpoint?: string
    user?: string
    password?: string
  }
  timeout?: number
}

export interface DefaultOpinionConfig {
  enabled: boolean
  should_overwrite?: boolean
}

export interface ProcessingConfig {
  allotments?: AllotmentsConfig
  similarities_within_lectures?: SimilaritiesWithinLecturesConfig
  similarity_search?: SimilaritySearchConfig
  attribution?: AttributionConfig
  default_opinion?: DefaultOpinionConfig
  summary_generation?: SummaryGenerationConfig
  placeholder_amdt_body?: boolean
}

export interface ConfigFilesResponse {
  files: string[]
  total: number
}

export interface SimilarityDatabasesListResponse {
  databases: string[]
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

// Database Builder Types
export interface UploadFileResponse {
  upload_id: string
  filename: string
  file_hash: string
  s3_key: string
  already_existed: boolean
  size: number
  metadata: {
    default_processing_timestamp: number
    origin_project: string
  }
}

export interface FileReference {
  upload_id: string
  filename: string
  file_hash: string
  s3_key: string
  metadata: {
    default_processing_timestamp: number
    origin_project: string
  }
}

export interface BuildDatabaseRequest {
  config_file: string
  database_name: string
  file_references: FileReference[]
  drop_empty_columns?: string[]
  similarity_threshold?: number
  eps?: number
  group_by_columns?: string[]
}

export interface DatabaseInfo {
  name: string
  size_bytes: number
  last_modified: string
}

export interface DatabaseListResponse {
  databases: DatabaseInfo[]
  total: number
}

export interface DeleteFileResponse {
  message: string
}

export interface DatabaseManifest {
  database_name: string
  created_at: string
  last_updated_at: string
  files: FileReferenceWithMetadata[]
  total_files: number
}

export interface FileReferenceWithMetadata {
  upload_id: string
  filename: string
  file_hash: string
  s3_key: string
  uploaded_at: string
  metadata: {
    default_processing_timestamp: number
    origin_project: string
  }
}

export interface FileUploadResponse {
  upload_id: string
  filename: string
  file_hash: string
  s3_key: string
  already_existed: boolean
  size: number
  metadata: {
    default_processing_timestamp: number
    origin_project: string
  }
}

export interface AppendDatabaseRequest {
  config_file: string
  file_references: Array<{
    upload_id: string
    filename: string
    file_hash: string
    s3_key: string
    metadata: {
      default_processing_timestamp: number
      origin_project: string
    }
  }>
  drop_empty_columns?: string[]
  similarity_threshold?: number
  eps?: number
  group_by_columns?: string[]
}

// Authentication types
export interface UserResponse {
  user_id: string
  email: string | null
  is_admin: boolean
}
