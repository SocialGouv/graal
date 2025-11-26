import { useQuery } from '@tanstack/react-query'
import apiService from '../services/api'
import { UserResponse } from '../types/api'

export interface UseAuthReturn {
  user: UserResponse | null
  isAdmin: boolean
  isLoading: boolean
  error: string | null
  refetch: () => void
}

/**
 * Custom hook for authentication state management
 * Uses React Query to fetch user data and updates the auth store
 */
export const useAuth = (): UseAuthReturn => {
  const query = useQuery({
    queryKey: ['currentUser'],
    queryFn: async (): Promise<UserResponse | null> => {
      try {
        return await apiService.getCurrentUser()
      } catch (error: any) {
        // 401 means not authenticated - return null instead of throwing
        if (error?.status_code === 401) {
          return null
        }
        // Other errors should be thrown
        throw error
      }
    },
    retry: (failureCount, error: any) => {
      // Don't retry on 401/403 (auth failures)
      if (error?.status_code === 401 || error?.status_code === 403) {
        return false
      }
      // Retry up to 2 times for other errors
      return failureCount < 2
    },
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
    staleTime: 5 * 60 * 1000, // Consider data fresh for 5 minutes
    refetchOnMount: true,
    refetchOnWindowFocus: false
  })

  // React Query is the source of truth - no need for Zustand sync
  const user = query.data ?? null
  const error = query.error
    ? (query.error as any).detail ||
      'Erreur lors de la récupération des informations utilisateur'
    : null

  return {
    user,
    isAdmin: user?.is_admin ?? false,
    isLoading: query.isLoading,
    error,
    refetch: () => {
      query.refetch()
    }
  }
}
