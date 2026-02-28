// Import and re-export the generated types for easier imports
import type { components } from './api-generated'
import type { UUID } from './common'
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
  database_id?: UUID
  clustering_similarity_thresholds?: Record<string, number>
  fuzzy_match_similarity_thresholds?: Record<string, number>
  similarity_threshold_overrides?: Record<string, Record<string, number>>
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
  llm_config_id?: UUID
  timeout?: number
}

export type LlmProvider = 'albert' // | 'scaleway' | 'mistral' | 'ollama' | 'vllm'

export interface LlmConfigBase {
  name: string
  provider: LlmProvider
  model_name: string
  base_url?: string
  api_key?: string
}

export type LlmConfigCreate = LlmConfigBase

export interface LlmConfigUpdate {
  name?: string
  provider?: LlmProvider
  model_name?: string
  base_url?: string | null
  endpoint?: string | null
  api_key?: string | null
  user?: string | null
  password?: string | null
}

export interface LlmConfigRead extends LlmConfigBase {
  id: UUID
  created_at: string
  updated_at: string
}

export interface DefaultOpinionConfig {
  enabled: boolean
  should_overwrite?: boolean
}

export interface ProcessingConfig {
  mission_short_title_filter?: string[]
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
  config_file_id: string
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
  config_file_id: string
  database_name: string
  file_references: FileReference[]
  drop_empty_columns?: string[]
  similarity_threshold?: number
  eps?: number
  group_by_columns?: string[]
}

export interface DatabaseInfo {
  id: string
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
  config_file_id: string
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

export interface DeleteFilesFromDatabaseRequest {
  config_file_id: string
  file_hashes_to_delete: string[]
  drop_empty_columns?: string[]
  similarity_threshold?: number
  eps?: number
  group_by_columns?: string[]
}

// Similarity Database Manifest types
export interface SimilarityDBManifestRead {
  id: string
  name: string
  s3_key: string
  size_bytes: number
  row_count: number | null
  db_metadata: Record<string, any> | null
  created_by_user_id: string
  last_modified: string
  is_active: boolean
  created_at: string
}

export interface SimilarityDBManifestCreate {
  name: string
  s3_key: string
  size_bytes: number
  row_count?: number | null
  db_metadata?: Record<string, any> | null
  last_modified: string
}

export interface SimilarityDBManifestUpdate {
  name?: string
  size_bytes?: number
  row_count?: number | null
  last_modified?: string
  db_metadata?: Record<string, any> | null
  is_active?: boolean
}

// S3 File Management types
export interface S3FileMetadata {
  key: string
  size: number
  last_modified: string
  file_type: string

  // Optional enrichment fields (input pool UI)
  display_name?: string | null
  file_hash?: string | null
  known_filenames?: string[] | null
  referenced_by_databases?: Array<{ id: string; name: string }> | null
}

export interface S3FileListResponse {
  files: S3FileMetadata[]
  total_count: number
  folder: string
}

export interface S3DeleteResponse {
  success: boolean
  message: string
  deleted_file: string
}

// Authentication types
export interface UserResponse {
  user_id: string
  email: string | null
  is_admin: boolean
}

// User Configuration types
export interface UserConfigurationBase {
  name: string
  feature_settings: Record<string, any>
  is_default: boolean
}

export type UserConfigurationCreate = UserConfigurationBase

export interface UserConfigurationUpdate {
  name?: string
  feature_settings?: Record<string, any>
  is_default?: boolean
}

export interface UserConfigurationRead extends UserConfigurationBase {
  id: string
  user_id: string
  created_at: string
  updated_at: string
}

// Database Permission types
export type DbRole = components['schemas']['DbRoleEnum']

// Excel Config types
export type ExcelConfigRole = 'reader' | 'owner'

export interface ExcelConfigManifest {
  id: string
  owner_user_id: string
  file_name: string
  s3_key: string
  file_size_bytes: number
  sheet_metadata: Record<string, unknown> | null
  created_at: string
  updated_at: string
  deleted_at: string | null
  current_user_role: ExcelConfigRole
}

export interface ExcelConfigListResponse {
  configs: ExcelConfigManifest[]
  total: number
}

export interface ExcelConfigPermission {
  config_id: string
  user_id: string
  email: string | null
  role: ExcelConfigRole
  created_at: string
}

export type DatabasePermission =
  components['schemas']['DatabasePermissionResponse']
export type ManagedDatabase = components['schemas']['ManagedDatabaseResponse']
export type AssignPermissionRequest =
  components['schemas']['AssignPermissionRequest']
