import axios, { type AxiosInstance, type AxiosProgressEvent } from 'axios';
import type {
  ApiError,
  JobStatusResponse,
  ProcessJobResponse,
  PreviewResponse,
} from '../types/api';

class ApiService {
  private readonly client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: 'http://localhost:8000/api/v1',
      timeout: 60000, // 60 seconds for regular requests
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor for logging
    this.client.interceptors.request.use(
      (config: any) => {
        console.log(`[API_CLIENT] ${config.method?.toUpperCase()} ${config.url}`, {
          timeout: config.timeout,
          headers: config.headers,
        });
        return config;
      },
      (error: Error) => {
        console.error('[API_CLIENT] Request error:', error);
        return Promise.reject(error);
      }
    );

    // Response interceptor for error handling and logging
    this.client.interceptors.response.use(
      (response: any) => {
        console.log(`[API_CLIENT] ${response.status} ${response.config.method?.toUpperCase()} ${response.config.url}`, {
          status: response.status,
          statusText: response.statusText,
          responseTime: response.headers['x-response-time'],
        });
        return response;
      },
      (error: { config: { method: string; url: string; }; response: { data: { detail: any; }; status: any; statusText: any; }; message: any; }) => {
        const method = error.config?.method?.toUpperCase() || 'UNKNOWN';
        const url = error.config?.url || 'unknown';

        if (error.response?.data) {
          console.error(`[API_CLIENT] ${error.response.status} ${method} ${url}`, {
            status: error.response.status,
            statusText: error.response.statusText,
            data: error.response.data,
          });

          const apiError: ApiError = {
            detail: error.response.data.detail || 'Une erreur est survenue',
            status_code: error.response.status,
          };
          throw apiError;
        }

        console.error(`[API_CLIENT] Network error ${method} ${url}:`, error.message);
        throw new Error('Erreur de connexion au serveur');
      }
    );
  }

  /**
   * Upload a JSON file and start processing
   */
  async uploadFile(
    file: File,
    onUploadProgress?: (progressEvent: AxiosProgressEvent) => void
  ): Promise<ProcessJobResponse> {
    console.log('[API_CLIENT] Starting file upload', {
      fileName: file.name,
      fileSize: file.size,
      fileType: file.type,
    });

    const formData = new FormData();
    formData.append('file', file);

    const startTime = Date.now();

    try {
      const response = await this.client.post<ProcessJobResponse>('/process', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        timeout: 120000, // 2 minutes for file upload
        onUploadProgress: (progressEvent: any) => {
          const percentCompleted = progressEvent.total
            ? Math.round((progressEvent.loaded * 100) / progressEvent.total)
            : 0;

          console.log(`[API_CLIENT] Upload progress: ${percentCompleted}%`, {
            loaded: progressEvent.loaded,
            total: progressEvent.total,
          });

          if (onUploadProgress) {
            onUploadProgress(progressEvent);
          }
        },
      });

      const uploadTime = Date.now() - startTime;
      console.log('[API_CLIENT] File upload completed', {
        jobId: response.data.job_id,
        status: response.data.status,
        uploadTime: `${uploadTime}ms`,
      });

      return response.data;
    } catch (error) {
      const uploadTime = Date.now() - startTime;
      console.error('[API_CLIENT] File upload failed', {
        fileName: file.name,
        uploadTime: `${uploadTime}ms`,
        error,
      });
      throw error;
    }
  }

  /**
   * Get job status and progress
   */
  async getJobStatus(jobId: string): Promise<JobStatusResponse> {
    console.log(`[API_CLIENT] Fetching job status for: ${jobId}`);

    try {
      const response = await this.client.get<JobStatusResponse>(`/status/${jobId}`);

      console.log(`[API_CLIENT] Job status retrieved for: ${jobId}`, {
        status: response.data.status,
        percent: response.data.percent,
        message: response.data.message,
      });

      return response.data;
    } catch (error) {
      console.error(`[API_CLIENT] Failed to get job status for: ${jobId}`, error);
      throw error;
    }
  }

  /**
   * Get results preview (first 10 rows)
   */
  async getResultsPreview(jobId: string): Promise<PreviewResponse> {
    console.log(`[API_CLIENT] Fetching results preview for: ${jobId}`);

    try {
      const response = await this.client.get<PreviewResponse>(`/results/${jobId}/preview`);

      console.log(`[API_CLIENT] Results preview retrieved for: ${jobId}`, {
        totalRows: response.data.total_rows,
        previewRows: response.data.preview_rows.length,
        columns: response.data.columns.length,
      });

      return response.data;
    } catch (error) {
      console.error(`[API_CLIENT] Failed to get results preview for: ${jobId}`, error);
      throw error;
    }
  }

  /**
   * Download full results as CSV
   */
  async downloadResults(jobId: string): Promise<Blob> {
    console.log(`[API_CLIENT] Starting CSV results download for: ${jobId}`);

    const startTime = Date.now();

    try {
      const response = await this.client.get(`/results/${jobId}/download`, {
        responseType: 'blob',
        timeout: 300000, // 5 minutes for download
      });

      const downloadTime = Date.now() - startTime;
      const fileSize = response.data.size;

      console.log(`[API_CLIENT] CSV results download completed for: ${jobId}`, {
        fileSize: `${fileSize} bytes`,
        downloadTime: `${downloadTime}ms`,
        contentType: response.headers['content-type'],
      });

      return response.data;
    } catch (error) {
      const downloadTime = Date.now() - startTime;
      console.error(`[API_CLIENT] CSV results download failed for: ${jobId}`, {
        downloadTime: `${downloadTime}ms`,
        error,
      });
      throw error;
    }
  }

  /**
   * Download full results as Excel
   */
  async downloadExcelResults(jobId: string): Promise<Blob> {
    console.log(`[API_CLIENT] Starting Excel results download for: ${jobId}`);

    const startTime = Date.now();

    try {
      const response = await this.client.get(`/results/${jobId}/download/excel`, {
        responseType: 'blob',
        timeout: 300000, // 5 minutes for download
      });

      const downloadTime = Date.now() - startTime;
      const fileSize = response.data.size;

      console.log(`[API_CLIENT] Excel results download completed for: ${jobId}`, {
        fileSize: `${fileSize} bytes`,
        downloadTime: `${downloadTime}ms`,
        contentType: response.headers['content-type'],
      });

      return response.data;
    } catch (error) {
      const downloadTime = Date.now() - startTime;
      console.error(`[API_CLIENT] Excel results download failed for: ${jobId}`, {
        downloadTime: `${downloadTime}ms`,
        error,
      });
      throw error;
    }
  }

  /**
   * Health check
   */
  async healthCheck(): Promise<{ status: string }> {
    console.log('[API_CLIENT] Performing health check');

    try {
      const response = await this.client.get<{ status: string }>('/health');

      console.log('[API_CLIENT] Health check completed', {
        status: response.data.status,
      });

      return response.data;
    } catch (error) {
      console.error('[API_CLIENT] Health check failed', error);
      throw error;
    }
  }
}

// Export singleton instance
export const apiService = new ApiService();
export default apiService;
