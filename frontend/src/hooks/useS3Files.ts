import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import apiService from '../services/api'
import type {
  ExcelConfigListResponse,
  S3DeleteResponse,
  S3FileListResponse
} from '../types/api'

/**
 * Query hook for fetching Excel config manifests (admin only)
 */
export const useAdminExcelConfigs = () => {
  return useQuery<ExcelConfigListResponse>({
    queryKey: ['excel-configs', 'admin'],
    queryFn: () => apiService.listAdminExcelConfigs()
  })
}

/**
 * Mutation hook for deleting Excel config manifests (admin only)
 */
export const useDeleteAdminExcelConfig = () => {
  const queryClient = useQueryClient()

  return useMutation<void, Error, string>({
    mutationFn: (configId: string) =>
      apiService.deleteAdminExcelConfig(configId),
    onSuccess: () => {
      // Invalidate parent key — React Query prefix matching clears both
      // ['excel-configs', 'user'] and ['excel-configs', 'admin'] at once.
      queryClient.invalidateQueries({ queryKey: ['excel-configs'] })
    }
  })
}

/**
 * Query hook for fetching config files from S3
 */
export const useConfigFiles = () => {
  return useQuery<S3FileListResponse>({
    queryKey: ['s3', 'config-files'],
    queryFn: () => apiService.listS3ConfigFiles(),
    refetchInterval: 30000, // Auto-refresh every 30 seconds
    staleTime: 10000 // Consider data stale after 10 seconds
  })
}

/**
 * Mutation hook for deleting config files from S3
 */
export const useDeleteConfigFile = () => {
  const queryClient = useQueryClient()

  return useMutation<S3DeleteResponse, Error, string>({
    mutationFn: (filename: string) => apiService.deleteS3ConfigFile(filename),
    onSuccess: () => {
      // Invalidate and refetch config files list
      queryClient.invalidateQueries({ queryKey: ['s3', 'config-files'] })
    }
  })
}

/**
 * Query hook for fetching database files from S3
 */
export const useDatabaseFiles = () => {
  return useQuery<S3FileListResponse>({
    queryKey: ['s3', 'database-files'],
    queryFn: () => apiService.listS3DatabaseFiles(),
    refetchInterval: 30000, // Auto-refresh every 30 seconds
    staleTime: 10000 // Consider data stale after 10 seconds
  })
}

/**
 * Mutation hook for deleting database files from S3
 */
export const useDeleteDatabaseFile = () => {
  const queryClient = useQueryClient()

  return useMutation<S3DeleteResponse, Error, string>({
    mutationFn: (databaseName: string) =>
      apiService.deleteS3DatabaseFile(databaseName),
    onSuccess: () => {
      // Invalidate and refetch database files list
      queryClient.invalidateQueries({ queryKey: ['s3', 'database-files'] })
    }
  })
}

/**
 * Query hook for fetching input pool files from S3
 */
export const useInputPoolFiles = () => {
  return useQuery<S3FileListResponse>({
    queryKey: ['s3', 'input-pool-files'],
    queryFn: () => apiService.listS3InputPoolFiles(),
    refetchInterval: 30000, // Auto-refresh every 30 seconds
    staleTime: 10000 // Consider data stale after 10 seconds
  })
}

/**
 * Mutation hook for deleting input pool files from S3
 */
export const useDeleteInputPoolFile = () => {
  const queryClient = useQueryClient()

  return useMutation<S3DeleteResponse, Error, string>({
    mutationFn: (s3Key: string) => apiService.deleteS3InputPoolFile(s3Key),
    onSuccess: () => {
      // Invalidate and refetch input pool files list
      queryClient.invalidateQueries({ queryKey: ['s3', 'input-pool-files'] })
    }
  })
}
