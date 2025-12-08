import axios, { type AxiosInstance, type AxiosProgressEvent } from 'axios'
import type {
  ApiError,
  AppendDatabaseRequest,
  BuildDatabaseRequest,
  ConfigFilesResponse,
  DatabaseListResponse,
  DatabaseManifest,
  DeleteFileResponse,
  JobStatusResponse,
  PreviewResponse,
  ProcessingRequest,
  ProcessJobResponse,
  S3DeleteResponse,
  S3FileListResponse,
  SimilarityDBManifestCreate,
  SimilarityDBManifestRead,
  SimilarityDBManifestUpdate,
  UploadFileResponse,
  UserConfigurationCreate,
  UserConfigurationRead,
  UserConfigurationUpdate,
  UserResponse
} from '../types/api'

class ApiService {
  private readonly client: AxiosInstance

  constructor() {
    // Use VITE_API_URL from environment or empty string for development
    // Empty string uses relative URLs which go through Vite proxy, enabling same-origin cookies
    const apiBaseUrl = import.meta.env.VITE_API_URL || ''

    this.client = axios.create({
      baseURL: apiBaseUrl ? `${apiBaseUrl}/api/v1` : '/api/v1',
      timeout: 60000, // 60 seconds for regular requests
      headers: {
        'Content-Type': 'application/json'
      },
      withCredentials: true // Required for session cookies
    })

    // Request interceptor for logging
    this.client.interceptors.request.use(
      (config: any) => {
        console.log(
          `[API_CLIENT] ${config.method?.toUpperCase()} ${config.url}`,
          {
            timeout: config.timeout,
            headers: config.headers
          }
        )
        return config
      },
      (error: Error) => {
        console.error('[API_CLIENT] Request error:', error)
        return Promise.reject(error)
      }
    )

    // Response interceptor for error handling and logging
    this.client.interceptors.response.use(
      (response: any) => {
        console.log(
          `[API_CLIENT] ${response.status} ${response.config.method?.toUpperCase()} ${response.config.url}`,
          {
            status: response.status,
            statusText: response.statusText,
            responseTime: response.headers['x-response-time']
          }
        )
        return response
      },
      (error: {
        config: { method: string; url: string }
        response: { data: { detail: any }; status: any; statusText: any }
        message: any
      }) => {
        const method = error.config?.method?.toUpperCase() || 'UNKNOWN'
        const url = error.config?.url || 'unknown'

        if (error.response?.data) {
          console.error(
            `[API_CLIENT] ${error.response.status} ${method} ${url}`,
            {
              status: error.response.status,
              statusText: error.response.statusText,
              data: error.response.data
            }
          )

          const apiError: ApiError = {
            detail: error.response.data.detail || 'Une erreur est survenue',
            status_code: error.response.status
          }
          throw apiError
        }

        console.error(
          `[API_CLIENT] Network error ${method} ${url}:`,
          error.message
        )
        throw new Error('Erreur de connexion au serveur')
      }
    )
  }

  /**
   * List available configuration files from S3
   */
  async listConfigFiles(): Promise<ConfigFilesResponse> {
    console.log('[API_CLIENT] Fetching available config files')

    try {
      const response =
        await this.client.get<ConfigFilesResponse>('/config-files')

      console.log('[API_CLIENT] Config files retrieved', {
        total: response.data.total,
        files: response.data.files
      })

      return response.data
    } catch (error) {
      console.error('[API_CLIENT] Failed to fetch config files', error)
      throw error
    }
  }

  /**
   * List available similarity database manifests
   */
  async listSimilarityDatabases(): Promise<SimilarityDBManifestRead[]> {
    console.log('[API_CLIENT] Fetching available similarity databases')

    try {
      const response = await this.client.get<SimilarityDBManifestRead[]>(
        '/similarity-databases'
      )

      console.log('[API_CLIENT] Similarity databases retrieved', {
        count: response.data.length
      })

      return response.data
    } catch (error) {
      console.error('[API_CLIENT] Failed to fetch similarity databases', error)
      throw error
    }
  }

  /**
   * Sync similarity database manifests from S3 (admin only)
   */
  async syncSimilarityDatabaseManifests(): Promise<SimilarityDBManifestRead[]> {
    console.log('[API_CLIENT] Syncing similarity database manifests from S3')

    try {
      const response = await this.client.post<SimilarityDBManifestRead[]>(
        '/admin/similarity-databases/sync'
      )

      console.log('[API_CLIENT] Similarity databases synced', {
        count: response.data.length
      })

      return response.data
    } catch (error) {
      console.error('[API_CLIENT] Failed to sync similarity databases', error)
      throw error
    }
  }

  /**
   * Create a similarity database manifest (admin only)
   */
  async createSimilarityDatabaseManifest(
    data: SimilarityDBManifestCreate
  ): Promise<SimilarityDBManifestRead> {
    console.log('[API_CLIENT] Creating similarity database manifest', {
      name: data.name
    })

    try {
      const response = await this.client.post<SimilarityDBManifestRead>(
        '/admin/similarity-databases',
        data
      )

      console.log('[API_CLIENT] Similarity database manifest created', {
        id: response.data.id,
        name: response.data.name
      })

      return response.data
    } catch (error) {
      console.error(
        '[API_CLIENT] Failed to create similarity database manifest',
        error
      )
      throw error
    }
  }

  /**
   * Update a similarity database manifest (admin only)
   */
  async updateSimilarityDatabaseManifest(
    id: string,
    data: SimilarityDBManifestUpdate
  ): Promise<SimilarityDBManifestRead> {
    console.log('[API_CLIENT] Updating similarity database manifest', { id })

    try {
      const response = await this.client.patch<SimilarityDBManifestRead>(
        `/admin/similarity-databases/${id}`,
        data
      )

      console.log('[API_CLIENT] Similarity database manifest updated', {
        id: response.data.id,
        name: response.data.name
      })

      return response.data
    } catch (error) {
      console.error(
        '[API_CLIENT] Failed to update similarity database manifest',
        error
      )
      throw error
    }
  }

  /**
   * Deactivate a similarity database manifest (admin only, soft delete)
   */
  async deactivateSimilarityDatabaseManifest(id: string): Promise<void> {
    console.log('[API_CLIENT] Deactivating similarity database manifest', {
      id
    })

    try {
      await this.client.delete(`/admin/similarity-databases/${id}`)

      console.log('[API_CLIENT] Similarity database manifest deactivated', {
        id
      })
    } catch (error) {
      console.error(
        '[API_CLIENT] Failed to deactivate similarity database manifest',
        error
      )
      throw error
    }
  }

  /**
   * Upload a JSON file and start processing
   */
  async uploadFile(
    file: File,
    processingRequest: ProcessingRequest,
    onUploadProgress?: (progressEvent: AxiosProgressEvent) => void
  ): Promise<ProcessJobResponse> {
    console.log('[API_CLIENT] Starting file upload', {
      fileName: file.name,
      fileSize: file.size,
      fileType: file.type,
      configFile: processingRequest.config_file,
      processingRequest: processingRequest
    })

    const formData = new FormData()
    formData.append('file', file)
    formData.append('request', JSON.stringify(processingRequest))

    const startTime = Date.now()

    try {
      const response = await this.client.post<ProcessJobResponse>(
        '/process',
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data'
          },
          timeout: 120000, // 2 minutes for file upload
          onUploadProgress: (progressEvent: any) => {
            const percentCompleted = progressEvent.total
              ? Math.round((progressEvent.loaded * 100) / progressEvent.total)
              : 0

            console.log(`[API_CLIENT] Upload progress: ${percentCompleted}%`, {
              loaded: progressEvent.loaded,
              total: progressEvent.total
            })

            if (onUploadProgress) {
              onUploadProgress(progressEvent)
            }
          }
        }
      )

      const uploadTime = Date.now() - startTime
      console.log('[API_CLIENT] File upload completed', {
        jobId: response.data.job_id,
        status: response.data.status,
        uploadTime: `${uploadTime}ms`
      })

      return response.data
    } catch (error) {
      const uploadTime = Date.now() - startTime
      console.error('[API_CLIENT] File upload failed', {
        fileName: file.name,
        uploadTime: `${uploadTime}ms`,
        error
      })
      throw error
    }
  }

  /**
   * Get job status and progress
   */
  async getJobStatus(jobId: string): Promise<JobStatusResponse> {
    console.log(`[API_CLIENT] Fetching job status for: ${jobId}`)

    try {
      const response = await this.client.get<JobStatusResponse>(
        `/status/${jobId}`
      )

      console.log(`[API_CLIENT] Job status retrieved for: ${jobId}`, {
        status: response.data.status,
        percent: response.data.percent,
        message: response.data.message
      })

      return response.data
    } catch (error) {
      console.error(
        `[API_CLIENT] Failed to get job status for: ${jobId}`,
        error
      )
      throw error
    }
  }

  /**
   * Get results preview (first 10 rows)
   */
  async getResultsPreview(jobId: string): Promise<PreviewResponse> {
    console.log(`[API_CLIENT] Fetching results preview for: ${jobId}`)

    try {
      const response = await this.client.get<PreviewResponse>(
        `/results/${jobId}/preview`
      )

      console.log(`[API_CLIENT] Results preview retrieved for: ${jobId}`, {
        totalRows: response.data.total_rows,
        previewRows: response.data.preview_rows.length,
        columns: response.data.columns.length
      })

      return response.data
    } catch (error) {
      console.error(
        `[API_CLIENT] Failed to get results preview for: ${jobId}`,
        error
      )
      throw error
    }
  }

  /**
   * Download full results as CSV
   */
  async downloadResults(jobId: string): Promise<Blob> {
    console.log(`[API_CLIENT] Starting CSV results download for: ${jobId}`)

    const startTime = Date.now()

    try {
      const response = await this.client.get(`/results/${jobId}/download`, {
        responseType: 'blob',
        timeout: 300000 // 5 minutes for download
      })

      const downloadTime = Date.now() - startTime
      const fileSize = response.data.size

      console.log(`[API_CLIENT] CSV results download completed for: ${jobId}`, {
        fileSize: `${fileSize} bytes`,
        downloadTime: `${downloadTime}ms`,
        contentType: response.headers['content-type']
      })

      return response.data
    } catch (error) {
      const downloadTime = Date.now() - startTime
      console.error(`[API_CLIENT] CSV results download failed for: ${jobId}`, {
        downloadTime: `${downloadTime}ms`,
        error
      })
      throw error
    }
  }

  /**
   * Download full results as Excel
   */
  async downloadExcelResults(jobId: string): Promise<Blob> {
    console.log(`[API_CLIENT] Starting Excel results download for: ${jobId}`)

    const startTime = Date.now()

    try {
      const response = await this.client.get(
        `/results/${jobId}/download/excel`,
        {
          responseType: 'blob',
          timeout: 300000 // 5 minutes for download
        }
      )

      const downloadTime = Date.now() - startTime
      const fileSize = response.data.size

      console.log(
        `[API_CLIENT] Excel results download completed for: ${jobId}`,
        {
          fileSize: `${fileSize} bytes`,
          downloadTime: `${downloadTime}ms`,
          contentType: response.headers['content-type']
        }
      )

      return response.data
    } catch (error) {
      const downloadTime = Date.now() - startTime
      console.error(
        `[API_CLIENT] Excel results download failed for: ${jobId}`,
        {
          downloadTime: `${downloadTime}ms`,
          error
        }
      )
      throw error
    }
  }

  /**
   * Health check
   */
  async healthCheck(): Promise<{ status: string }> {
    console.log('[API_CLIENT] Performing health check')

    try {
      const response = await this.client.get<{ status: string }>('/health')

      console.log('[API_CLIENT] Health check completed', {
        status: response.data.status
      })

      return response.data
    } catch (error) {
      console.error('[API_CLIENT] Health check failed', error)
      throw error
    }
  }

  /**
   * Upload amendment file for database building
   */
  async uploadAmendmentFile(
    file: File,
    metadata: { default_processing_timestamp?: number; origin_project: string },
    onUploadProgress?: (progressEvent: AxiosProgressEvent) => void
  ): Promise<UploadFileResponse> {
    console.log('[API_CLIENT] Uploading amendment file for database builder', {
      fileName: file.name,
      fileSize: file.size,
      metadata
    })

    const formData = new FormData()
    formData.append('file', file)
    formData.append('metadata', JSON.stringify(metadata))

    const startTime = Date.now()

    try {
      const response = await this.client.post<UploadFileResponse>(
        '/databases/upload-file',
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data'
          },
          timeout: 300000, // 5 minutes for large files
          onUploadProgress: (progressEvent: any) => {
            const percentCompleted = progressEvent.total
              ? Math.round((progressEvent.loaded * 100) / progressEvent.total)
              : 0

            console.log(
              `[API_CLIENT] Amendment file upload progress: ${percentCompleted}%`,
              {
                loaded: progressEvent.loaded,
                total: progressEvent.total
              }
            )

            if (onUploadProgress) {
              onUploadProgress(progressEvent)
            }
          }
        }
      )

      const uploadTime = Date.now() - startTime
      console.log('[API_CLIENT] Amendment file upload completed', {
        uploadId: response.data.upload_id,
        fileName: response.data.filename,
        uploadTime: `${uploadTime}ms`
      })

      return response.data
    } catch (error) {
      const uploadTime = Date.now() - startTime
      console.error('[API_CLIENT] Amendment file upload failed', {
        fileName: file.name,
        uploadTime: `${uploadTime}ms`,
        error
      })
      throw error
    }
  }

  /**
   * Build database from uploaded files
   */
  async buildDatabase(
    request: BuildDatabaseRequest,
    onUploadProgress?: (progressEvent: AxiosProgressEvent) => void
  ): Promise<ProcessJobResponse> {
    console.log('[API_CLIENT] Starting database build', {
      databaseName: request.database_name,
      fileCount: request.file_references.length
    })

    const startTime = Date.now()

    try {
      const response = await this.client.post<ProcessJobResponse>(
        '/databases/build',
        request,
        {
          timeout: 120000, // 2 minutes
          onUploadProgress
        }
      )

      const buildTime = Date.now() - startTime
      console.log('[API_CLIENT] Database build started', {
        jobId: response.data.job_id,
        status: response.data.status,
        buildTime: `${buildTime}ms`
      })

      return response.data
    } catch (error) {
      const buildTime = Date.now() - startTime
      console.error('[API_CLIENT] Database build failed', {
        databaseName: request.database_name,
        buildTime: `${buildTime}ms`,
        error
      })
      throw error
    }
  }

  /**
   * List available databases
   */
  async listDatabases(): Promise<DatabaseListResponse> {
    console.log('[API_CLIENT] Fetching available databases')

    try {
      const response = await this.client.get<DatabaseListResponse>('/databases')

      console.log('[API_CLIENT] Databases retrieved', {
        total: response.data.total,
        databases: response.data.databases
      })

      return response.data
    } catch (error) {
      console.error('[API_CLIENT] Failed to fetch databases', error)
      throw error
    }
  }

  /**
   * Delete uploaded file
   */
  async deleteUploadedFile(uploadId: string): Promise<DeleteFileResponse> {
    console.log(`[API_CLIENT] Deleting uploaded file: ${uploadId}`)

    try {
      const response = await this.client.delete<DeleteFileResponse>(
        `/databases/uploads/${uploadId}`
      )

      console.log(`[API_CLIENT] File deleted successfully: ${uploadId}`)

      return response.data
    } catch (error: any) {
      // 404 means file already deleted - treat as success since desired state is achieved
      if (error?.response?.status === 404) {
        console.log(`[API_CLIENT] File already deleted: ${uploadId}`)
        return { message: 'File already deleted' }
      }

      console.error(`[API_CLIENT] Failed to delete file: ${uploadId}`, error)
      throw error
    }
  }

  /**
   * Get database manifest with file references
   */
  async getDatabaseManifest(databaseName: string): Promise<DatabaseManifest> {
    console.log(`[API_CLIENT] Fetching manifest for database: ${databaseName}`)

    try {
      const response = await this.client.get<DatabaseManifest>(
        `/databases/${databaseName}/manifest`
      )

      console.log(`[API_CLIENT] Manifest retrieved for: ${databaseName}`, {
        totalFiles: response.data.total_files,
        createdAt: response.data.created_at
      })

      return response.data
    } catch (error) {
      console.error(
        `[API_CLIENT] Failed to get manifest for: ${databaseName}`,
        error
      )
      throw error
    }
  }

  /**
   * Append files to existing database and rebuild
   */
  async appendToDatabase(
    databaseName: string,
    request: AppendDatabaseRequest
  ): Promise<ProcessJobResponse> {
    console.log(`[API_CLIENT] Appending to database: ${databaseName}`, {
      fileCount: request.file_references.length,
      configFile: request.config_file
    })

    const startTime = Date.now()

    try {
      const response = await this.client.post<ProcessJobResponse>(
        `/databases/${databaseName}/append`,
        request,
        {
          timeout: 5 * 60 * 1000 // 5 minutes
        }
      )

      const appendTime = Date.now() - startTime
      console.log(`[API_CLIENT] Database append started for: ${databaseName}`, {
        jobId: response.data.job_id,
        status: response.data.status,
        appendTime: `${appendTime}ms`
      })

      return response.data
    } catch (error) {
      const appendTime = Date.now() - startTime
      console.error(
        `[API_CLIENT] Database append failed for: ${databaseName}`,
        {
          appendTime: `${appendTime}ms`,
          error
        }
      )
      throw error
    }
  }

  /**
   * Get current user information
   */
  async getCurrentUser(): Promise<UserResponse> {
    console.log('[API_CLIENT] Fetching current user information')

    try {
      const response = await this.client.get<UserResponse>('/auth/me')

      console.log('[API_CLIENT] Current user retrieved', {
        userId: response.data.user_id,
        isAdmin: response.data.is_admin
      })

      return response.data
    } catch (error) {
      console.error('[API_CLIENT] Failed to get current user', error)

      // Transform to ApiError for consistent error handling
      if (error && typeof error === 'object' && 'status_code' in error) {
        throw error
      }

      const apiError: ApiError = {
        detail: 'Failed to retrieve user information',
        status_code: 500
      }
      throw apiError
    }
  }

  /**
   * Get all configurations for the current user
   */
  async getUserConfigurations(): Promise<UserConfigurationRead[]> {
    console.log('[API_CLIENT] Fetching user configurations')

    try {
      const response = await this.client.get<UserConfigurationRead[]>(
        '/users/me/configurations'
      )

      console.log('[API_CLIENT] User configurations retrieved', {
        count: response.data.length
      })

      return response.data
    } catch (error) {
      console.error('[API_CLIENT] Failed to get user configurations', error)
      throw error
    }
  }

  /**
   * Create a new user configuration
   */
  async createUserConfiguration(
    data: UserConfigurationCreate
  ): Promise<UserConfigurationRead> {
    console.log('[API_CLIENT] Creating user configuration', {
      name: data.name
    })

    try {
      const response = await this.client.post<UserConfigurationRead>(
        '/users/me/configurations',
        data
      )

      console.log('[API_CLIENT] User configuration created', {
        id: response.data.id,
        name: response.data.name
      })

      return response.data
    } catch (error) {
      console.error('[API_CLIENT] Failed to create user configuration', error)
      throw error
    }
  }

  /**
   * Get the user's default configuration
   */
  async getDefaultConfiguration(): Promise<UserConfigurationRead> {
    console.log('[API_CLIENT] Fetching default configuration')

    try {
      const response = await this.client.get<UserConfigurationRead>(
        '/users/me/configurations/default'
      )

      console.log('[API_CLIENT] Default configuration retrieved', {
        id: response.data.id,
        name: response.data.name
      })

      return response.data
    } catch (error) {
      console.error('[API_CLIENT] Failed to get default configuration', error)
      throw error
    }
  }

  /**
   * Update a user configuration
   */
  async updateUserConfiguration(
    id: string,
    data: UserConfigurationUpdate
  ): Promise<UserConfigurationRead> {
    console.log('[API_CLIENT] Updating user configuration', { id })

    try {
      const response = await this.client.patch<UserConfigurationRead>(
        `/users/me/configurations/${id}`,
        data
      )

      console.log('[API_CLIENT] User configuration updated', {
        id: response.data.id,
        name: response.data.name
      })

      return response.data
    } catch (error) {
      console.error('[API_CLIENT] Failed to update user configuration', error)
      throw error
    }
  }

  /**
   * Set a configuration as the user's default
   */
  async setDefaultConfiguration(id: string): Promise<UserConfigurationRead> {
    console.log('[API_CLIENT] Setting default configuration', { id })

    try {
      const response = await this.client.post<UserConfigurationRead>(
        `/users/me/configurations/${id}/set-default`
      )

      console.log('[API_CLIENT] Default configuration set', {
        id: response.data.id,
        name: response.data.name
      })

      return response.data
    } catch (error) {
      console.error('[API_CLIENT] Failed to set default configuration', error)
      throw error
    }
  }

  /**
   * Delete a user configuration
   */
  async deleteUserConfiguration(id: string): Promise<void> {
    console.log('[API_CLIENT] Deleting user configuration', { id })

    try {
      await this.client.delete(`/users/me/configurations/${id}`)

      console.log('[API_CLIENT] User configuration deleted', { id })
    } catch (error) {
      console.error('[API_CLIENT] Failed to delete user configuration', error)
      throw error
    }
  }

  /**
   * List all config files from S3 with metadata (admin only)
   */
  async listS3ConfigFiles(): Promise<S3FileListResponse> {
    console.log('[API_CLIENT] Fetching S3 config files with metadata')

    try {
      const response = await this.client.get<S3FileListResponse>(
        '/admin/s3/config-files'
      )

      console.log('[API_CLIENT] S3 config files retrieved', {
        total: response.data.total_count
      })

      return response.data
    } catch (error) {
      console.error('[API_CLIENT] Failed to fetch S3 config files', error)
      throw error
    }
  }

  /**
   * Delete a config file from S3 (admin only)
   */
  async deleteS3ConfigFile(filename: string): Promise<S3DeleteResponse> {
    console.log('[API_CLIENT] Deleting S3 config file', { filename })

    try {
      const response = await this.client.delete<S3DeleteResponse>(
        `/admin/s3/config-files/${encodeURIComponent(filename)}`
      )

      console.log('[API_CLIENT] S3 config file deleted', { filename })

      return response.data
    } catch (error) {
      console.error('[API_CLIENT] Failed to delete S3 config file', error)
      throw error
    }
  }

  /**
   * List all database files from S3 with metadata (admin only)
   */
  async listS3DatabaseFiles(): Promise<S3FileListResponse> {
    console.log('[API_CLIENT] Fetching S3 database files with metadata')

    try {
      const response = await this.client.get<S3FileListResponse>(
        '/admin/s3/databases'
      )

      console.log('[API_CLIENT] S3 database files retrieved', {
        total: response.data.total_count
      })

      return response.data
    } catch (error) {
      console.error('[API_CLIENT] Failed to fetch S3 database files', error)
      throw error
    }
  }

  /**
   * Delete a database file from S3 (admin only)
   */
  async deleteS3DatabaseFile(databaseName: string): Promise<S3DeleteResponse> {
    console.log('[API_CLIENT] Deleting S3 database file', { databaseName })

    try {
      const response = await this.client.delete<S3DeleteResponse>(
        `/admin/s3/databases/${encodeURIComponent(databaseName)}`
      )

      console.log('[API_CLIENT] S3 database file deleted', { databaseName })

      return response.data
    } catch (error) {
      console.error('[API_CLIENT] Failed to delete S3 database file', error)
      throw error
    }
  }

  /**
   * List all input pool files from S3 with metadata (admin only)
   */
  async listS3InputPoolFiles(): Promise<S3FileListResponse> {
    console.log('[API_CLIENT] Fetching S3 input pool files with metadata')

    try {
      const response = await this.client.get<S3FileListResponse>(
        '/admin/s3/input-pool'
      )

      console.log('[API_CLIENT] S3 input pool files retrieved', {
        total: response.data.total_count
      })

      return response.data
    } catch (error) {
      console.error('[API_CLIENT] Failed to fetch S3 input pool files', error)
      throw error
    }
  }

  /**
   * Delete a file from input pool in S3 (admin only)
   */
  async deleteS3InputPoolFile(s3Key: string): Promise<S3DeleteResponse> {
    console.log('[API_CLIENT] Deleting S3 input pool file', { s3Key })

    try {
      const response = await this.client.delete<S3DeleteResponse>(
        `/admin/s3/input-pool/${encodeURIComponent(s3Key)}`
      )

      console.log('[API_CLIENT] S3 input pool file deleted', { s3Key })

      return response.data
    } catch (error) {
      console.error('[API_CLIENT] Failed to delete S3 input pool file', error)
      throw error
    }
  }
}

// Export singleton instance
export const apiService = new ApiService()
export default apiService
