import axios, { type AxiosInstance, type AxiosProgressEvent } from 'axios';
import type {
  ProcessJobResponse,
  JobStatusResponse,
  ResultsPreviewResponse,
  ApiError,
} from '../types/api';

class ApiService {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: 'http://localhost:8000/api/v1',
      timeout: 60000, // 60 seconds for regular requests
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.data) {
          const apiError: ApiError = {
            detail: error.response.data.detail || 'Une erreur est survenue',
            status_code: error.response.status,
          };
          throw apiError;
        }
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
    const formData = new FormData();
    formData.append('file', file);

    const response = await this.client.post<ProcessJobResponse>('/process', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      timeout: 120000, // 2 minutes for file upload
      onUploadProgress,
    });

    return response.data;
  }

  /**
   * Get job status and progress
   */
  async getJobStatus(jobId: string): Promise<JobStatusResponse> {
    const response = await this.client.get<JobStatusResponse>(`/status/${jobId}`);
    return response.data;
  }

  /**
   * Get results preview (first 10 rows)
   */
  async getResultsPreview(jobId: string): Promise<ResultsPreviewResponse> {
    const response = await this.client.get<ResultsPreviewResponse>(`/results/${jobId}/preview`);
    return response.data;
  }

  /**
   * Download full results as CSV
   */
  async downloadResults(jobId: string): Promise<Blob> {
    const response = await this.client.get(`/results/${jobId}/download`, {
      responseType: 'blob',
      timeout: 300000, // 5 minutes for download
    });
    return response.data;
  }

  /**
   * Health check
   */
  async healthCheck(): Promise<{ status: string }> {
    const response = await this.client.get<{ status: string }>('/health');
    return response.data;
  }
}

// Export singleton instance
export const apiService = new ApiService();
export default apiService;
