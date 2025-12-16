import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import apiService from '../services/api'
import type { SimilarityDBManifestRead } from '../types/api'

/**
 * Admin-only hook for listing similarity database manifests.
 *
 * Uses the existing listSimilarityDatabases API, which already returns
 * SimilarityDBManifestRead objects (including the database UUID).
 */
export const useAdminDatabases = () => {
  return useQuery<SimilarityDBManifestRead[]>({
    queryKey: ['admin', 'similarity-databases'],
    queryFn: () => apiService.listSimilarityDatabases(),
    refetchInterval: 30000,
    staleTime: 10000
  })
}

/**
 * Admin-only hook for deleting a database by manifest ID.
 *
 * This removes both the S3 parquet file and the manifest, keeping S3 and
 * Postgres consistent. It calls the new ID-based backend endpoint.
 */
export const useDeleteAdminDatabase = () => {
  const queryClient = useQueryClient()

  return useMutation<void, Error, string>({
    mutationFn: (id: string) => apiService.deleteSimilarityDatabaseWithFile(id),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['admin', 'similarity-databases']
      })
    }
  })
}
