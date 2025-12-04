import { useMutation, useQuery } from '@tanstack/react-query'
import type { AxiosProgressEvent } from 'axios'
import React from 'react'
import apiService from '../services/api'
import { useProcessingStore } from '../stores/processingStore'
import type {
  JobStatusResponse,
  PreviewResponse,
  ProcessJobResponse,
  ProcessingRequest
} from '../types/api'

// Upload file mutation
export const useUploadFile = () => {
  const { setJobId, setUploadProgress, updateProgress, setError } =
    useProcessingStore()

  return useMutation({
    mutationFn: async ({
      file,
      processingRequest
    }: {
      file: File
      processingRequest: ProcessingRequest
    }): Promise<ProcessJobResponse> => {
      updateProgress('uploading', 0, 'Téléchargement du fichier...')

      const response = await apiService.uploadFile(
        file,
        processingRequest,
        (progressEvent: AxiosProgressEvent) => {
          if (progressEvent.total) {
            const percent = Math.round(
              (progressEvent.loaded * 100) / progressEvent.total
            )
            setUploadProgress(percent)
          }
        }
      )

      return response
    },
    onSuccess: (data: { job_id: string }) => {
      setJobId(data.job_id)
      updateProgress('queued', 0, 'Fichier téléchargé, traitement en cours...')
      setError(null)
    },
    onError: (error: any) => {
      const errorMessage =
        error.detail || 'Erreur lors du téléchargement du fichier'
      setError(errorMessage)
      updateProgress('failed', 0, errorMessage)
    }
  })
}

// Job status polling query
export const useJobStatus = (jobId: string | null, enabled: boolean = true) => {
  const { updateProgress, setError } = useProcessingStore()

  const query = useQuery({
    queryKey: ['jobStatus', jobId],
    queryFn: async (): Promise<JobStatusResponse> => {
      if (!jobId) throw new Error('Job ID is required')
      return apiService.getJobStatus(jobId)
    },
    enabled: enabled && !!jobId,
    refetchInterval: (query: { state: { data: any } }) => {
      // Stop polling if job is completed, failed, or timeout
      const data = query.state.data
      if (
        data?.status &&
        ['completed', 'failed', 'timeout'].includes(data.status)
      ) {
        return false
      }
      return 2000 // Poll every 2 seconds
    }
  })

  // Handle data updates
  React.useEffect(() => {
    if (query.data) {
      updateProgress(
        query.data.status,
        query.data.percent,
        query.data.message,
        query.data.started_at,
        query.data.updated_at
      )

      if (query.data.status === 'failed' || query.data.status === 'timeout') {
        setError(query.data.message || `Erreur: ${query.data.status}`)
      }
    }
  }, [query.data, updateProgress, setError])

  // Handle errors
  React.useEffect(() => {
    if (query.error) {
      const errorMessage =
        (query.error as any).detail ||
        'Erreur lors de la récupération du statut'
      setError(errorMessage)
    }
  }, [query.error, setError])

  return query
}

// Results preview query
export const useResultsPreview = (
  jobId: string | null,
  enabled: boolean = false
) => {
  const { setResults, setError } = useProcessingStore()

  const query = useQuery({
    queryKey: ['resultsPreview', jobId],
    queryFn: async (): Promise<PreviewResponse> => {
      if (!jobId) throw new Error('Job ID is required')
      return apiService.getResultsPreview(jobId)
    },
    enabled: enabled && !!jobId
  })

  // Handle data updates
  React.useEffect(() => {
    if (query.data) {
      setResults(query.data.preview_rows, query.data.total_rows)
      setError(null)
    }
  }, [query.data, setResults, setError])

  // Handle errors
  React.useEffect(() => {
    if (query.error) {
      const errorMessage =
        (query.error as any).detail ||
        'Erreur lors de la récupération des résultats'
      setError(errorMessage)
    }
  }, [query.error, setError])

  return query
}

// Download results mutation
export const useDownloadResults = () => {
  const { setError } = useProcessingStore()

  return useMutation({
    mutationFn: async (jobId: string): Promise<Blob> => {
      return apiService.downloadResults(jobId)
    },
    onSuccess: (blob: Blob, jobId: string) => {
      // Create download link
      const url = globalThis.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `graal-results-${jobId}.csv`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      globalThis.URL.revokeObjectURL(url)
      setError(null)
    },
    onError: (error: any) => {
      const errorMessage =
        error.detail || 'Erreur lors du téléchargement des résultats CSV'
      setError(errorMessage)
    }
  })
}

// Download Excel results mutation
export const useDownloadExcelResults = () => {
  const { setError } = useProcessingStore()

  return useMutation({
    mutationFn: async (jobId: string): Promise<Blob> => {
      return apiService.downloadExcelResults(jobId)
    },
    onSuccess: (blob: Blob, jobId: string) => {
      // Create download link
      const url = globalThis.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `graal-results-${jobId}.xlsx`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      globalThis.URL.revokeObjectURL(url)
      setError(null)
    },
    onError: (error: any) => {
      const errorMessage =
        error.detail || 'Erreur lors du téléchargement des résultats Excel'
      setError(errorMessage)
    }
  })
}

// Health check query
export const useHealthCheck = () => {
  return useQuery({
    queryKey: ['health'],
    queryFn: () => apiService.healthCheck(),
    refetchInterval: 30000, // Check every 30 seconds
    retry: 3
  })
}
