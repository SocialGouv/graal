import { useQuery } from '@tanstack/react-query'
import { useEffect } from 'react'
import apiService from '../services/api'
import { useAuthStore } from '../stores/authStore'
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
  const { user, error, setUser, setError } = useAuthStore()

  const query = useQuery({
    queryKey: ['currentUser'],
    queryFn: async (): Promise<UserResponse> => {
      return apiService.getCurrentUser()
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

  // Update auth store when query state changes
  useEffect(() => {
    if (query.isLoading) return
    if (query.data) {
      setUser(query.data)
    } else if (query.error) {
      const errorMessage =
        (query.error as any).detail ||
        'Erreur lors de la récupération des informations utilisateur'
      setError(errorMessage)
      setUser(null)
    }
  }, [query.isLoading, query.data, query.error, setUser, setError])

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
