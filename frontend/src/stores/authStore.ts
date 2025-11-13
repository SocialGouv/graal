import { create } from 'zustand'
import { UserResponse } from '../types/api'

export interface AuthState {
  user: UserResponse | null
  error: string | null

  // Actions
  setUser: (user: UserResponse | null) => void
  setError: (error: string | null) => void
  clearUser: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  error: null,

  setUser: (user) =>
    set({
      user,
      error: null
    }),

  setError: (error) =>
    set({
      error,
      user: null
    }),

  clearUser: () =>
    set({
      user: null,
      error: null
    })
}))
