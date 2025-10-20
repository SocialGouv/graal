import axios, { type AxiosInstance, type AxiosProgressEvent } from 'axios'
import type {
  ApiError,
  BuildDatabaseRequest,
  ConfigFilesResponse,
  DatabaseListResponse,
  DeleteFileResponse,
  JobStatusResponse,
  PreviewResponse,
  ProcessingRequest,
  ProcessJobResponse,
  SimilarityDatabasesListResponse,
  UploadFileResponse
} from '../types/api'

class ApiService {
  private readonly client: AxiosInstance

  constructor() {
    // Use VITE_API_URL from environment or fallback to localhost for development
    const apiBaseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'

    this.client = axios.create({
      baseURL: `${apiBaseUrl}/api/v1`,
      timeout: 60000, // 60 seconds for regular requests
      headers: {
        'Content-Type': 'application/json'
      }
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
   * List available similarity database files from S3
   */
  async listSimilarityDatabases(): Promise<string[]> {
    console.log('[API_CLIENT] Fetching available similarity databases')

    try {
      const response = await this.client.get<SimilarityDatabasesListResponse>(
        '/similarity-databases'
      )

      console.log('[API_CLIENT] Similarity databases retrieved', {
        total: response.data.total,
        databases: response.data.databases
      })

      return response.data.databases
    } catch (error) {
      console.error('[API_CLIENT] Failed to fetch similarity databases', error)
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
    } catch (error) {
      console.error(`[API_CLIENT] Failed to delete file: ${uploadId}`, error)
      throw error
    }
  }
}

// Export singleton instance
export const apiService = new ApiService()
export default apiService
