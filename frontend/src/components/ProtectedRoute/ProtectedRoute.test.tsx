import { render, screen } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ProtectedRoute } from './ProtectedRoute'

// Mock the useAuth hook
vi.mock('../../hooks/useAuth', () => ({
  useAuth: vi.fn()
}))

// Mock react-router-dom Navigate
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    Navigate: ({ to }: { to: string }) => <div data-testid="navigate">{to}</div>
  }
})

const { useAuth } = await import('../../hooks/useAuth')

describe('ProtectedRoute', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Loading state', () => {
    it('should show loading state while authentication is loading', () => {
      vi.mocked(useAuth).mockReturnValue({
        user: null,
        isAuthenticated: false,
        isAdmin: false,
        isLoading: true,
        error: null,
        refetch: vi.fn()
      })

      render(
        <BrowserRouter>
          <ProtectedRoute>
            <div>Protected Content</div>
          </ProtectedRoute>
        </BrowserRouter>
      )

      expect(screen.getByText('Chargement...')).toBeInTheDocument()
      expect(screen.queryByText('Protected Content')).not.toBeInTheDocument()
    })
  })

  describe('Admin protection (requireAdmin=true)', () => {
    it('should render children when user is admin and requireAdmin is true', () => {
      vi.mocked(useAuth).mockReturnValue({
        user: { user_id: '1', email: 'admin@example.com', is_admin: true },
        isAuthenticated: true,
        isAdmin: true,
        isLoading: false,
        error: null,
        refetch: vi.fn()
      })

      render(
        <BrowserRouter>
          <ProtectedRoute requireAdmin={true}>
            <div>Admin Content</div>
          </ProtectedRoute>
        </BrowserRouter>
      )

      expect(screen.getByText('Admin Content')).toBeInTheDocument()
      expect(screen.queryByText('Chargement...')).not.toBeInTheDocument()
      expect(screen.queryByTestId('navigate')).not.toBeInTheDocument()
    })

    it('should redirect to home when user is not admin and requireAdmin is true', () => {
      vi.mocked(useAuth).mockReturnValue({
        user: { user_id: '2', email: 'user@example.com', is_admin: false },
        isAuthenticated: true,
        isAdmin: false,
        isLoading: false,
        error: null,
        refetch: vi.fn()
      })

      render(
        <BrowserRouter>
          <ProtectedRoute requireAdmin={true}>
            <div>Admin Content</div>
          </ProtectedRoute>
        </BrowserRouter>
      )

      expect(screen.queryByText('Admin Content')).not.toBeInTheDocument()
      expect(screen.getByTestId('navigate')).toHaveTextContent('/')
    })

    it('should redirect to home when user is null and requireAdmin is true', () => {
      vi.mocked(useAuth).mockReturnValue({
        user: null,
        isAuthenticated: false,
        isAdmin: false,
        isLoading: false,
        error: null,
        refetch: vi.fn()
      })

      render(
        <BrowserRouter>
          <ProtectedRoute requireAdmin={true}>
            <div>Admin Content</div>
          </ProtectedRoute>
        </BrowserRouter>
      )

      expect(screen.queryByText('Admin Content')).not.toBeInTheDocument()
      expect(screen.getByTestId('navigate')).toHaveTextContent('/')
    })
  })

  describe('Non-admin protection (requireAdmin=false or undefined)', () => {
    it('should render children when requireAdmin is false (default)', () => {
      vi.mocked(useAuth).mockReturnValue({
        user: { user_id: '2', email: 'user@example.com', is_admin: false },
        isAuthenticated: true,
        isAdmin: false,
        isLoading: false,
        error: null,
        refetch: vi.fn()
      })

      render(
        <BrowserRouter>
          <ProtectedRoute>
            <div>Protected Content</div>
          </ProtectedRoute>
        </BrowserRouter>
      )

      expect(screen.getByText('Protected Content')).toBeInTheDocument()
      expect(screen.queryByTestId('navigate')).not.toBeInTheDocument()
    })

    it('should render children for admin users when requireAdmin is false', () => {
      vi.mocked(useAuth).mockReturnValue({
        user: { user_id: '1', email: 'admin@example.com', is_admin: true },
        isAuthenticated: true,
        isAdmin: true,
        isLoading: false,
        error: null,
        refetch: vi.fn()
      })

      render(
        <BrowserRouter>
          <ProtectedRoute requireAdmin={false}>
            <div>Protected Content</div>
          </ProtectedRoute>
        </BrowserRouter>
      )

      expect(screen.getByText('Protected Content')).toBeInTheDocument()
      expect(screen.queryByTestId('navigate')).not.toBeInTheDocument()
    })

    it('should redirect to home when user is not authenticated', () => {
      vi.mocked(useAuth).mockReturnValue({
        user: null,
        isAuthenticated: false,
        isAdmin: false,
        isLoading: false,
        error: null,
        refetch: vi.fn()
      })

      render(
        <BrowserRouter>
          <ProtectedRoute>
            <div>Protected Content</div>
          </ProtectedRoute>
        </BrowserRouter>
      )

      expect(screen.queryByText('Protected Content')).not.toBeInTheDocument()
      expect(screen.getByTestId('navigate')).toHaveTextContent('/')
    })
  })

  describe('Edge cases', () => {
    it('should handle transition from loading to admin user correctly', () => {
      const { rerender } = render(
        <BrowserRouter>
          <ProtectedRoute requireAdmin={true}>
            <div>Admin Content</div>
          </ProtectedRoute>
        </BrowserRouter>
      )

      // Initially loading
      vi.mocked(useAuth).mockReturnValue({
        user: null,
        isAuthenticated: false,
        isAdmin: false,
        isLoading: true,
        error: null,
        refetch: vi.fn()
      })

      rerender(
        <BrowserRouter>
          <ProtectedRoute requireAdmin={true}>
            <div>Admin Content</div>
          </ProtectedRoute>
        </BrowserRouter>
      )

      expect(screen.getByText('Chargement...')).toBeInTheDocument()

      // Then loaded as admin
      vi.mocked(useAuth).mockReturnValue({
        user: { user_id: '1', email: 'admin@example.com', is_admin: true },
        isAuthenticated: true,
        isAdmin: true,
        isLoading: false,
        error: null,
        refetch: vi.fn()
      })

      rerender(
        <BrowserRouter>
          <ProtectedRoute requireAdmin={true}>
            <div>Admin Content</div>
          </ProtectedRoute>
        </BrowserRouter>
      )

      expect(screen.getByText('Admin Content')).toBeInTheDocument()
      expect(screen.queryByText('Chargement...')).not.toBeInTheDocument()
    })

    it('should display error alert when authentication fails', () => {
      vi.mocked(useAuth).mockReturnValue({
        user: null,
        isAuthenticated: false,
        isAdmin: false,
        isLoading: false,
        error: 'Authentication failed',
        refetch: vi.fn()
      })

      render(
        <BrowserRouter>
          <ProtectedRoute requireAdmin={true}>
            <div>Admin Content</div>
          </ProtectedRoute>
        </BrowserRouter>
      )

      // Should display error alert instead of redirecting
      expect(screen.getByText("Erreur d'authentification")).toBeInTheDocument()
      expect(screen.getByText('Authentication failed')).toBeInTheDocument()
      expect(screen.queryByText('Admin Content')).not.toBeInTheDocument()
      expect(screen.queryByTestId('navigate')).not.toBeInTheDocument()
    })

    it('should not redirect when there is an error', () => {
      vi.mocked(useAuth).mockReturnValue({
        user: null,
        isAuthenticated: false,
        isAdmin: false,
        isLoading: false,
        error: 'Network connection failed',
        refetch: vi.fn()
      })

      render(
        <BrowserRouter>
          <ProtectedRoute>
            <div>Protected Content</div>
          </ProtectedRoute>
        </BrowserRouter>
      )

      // Should show error alert, not redirect
      expect(screen.getByText("Erreur d'authentification")).toBeInTheDocument()
      expect(screen.getByText('Network connection failed')).toBeInTheDocument()
      expect(screen.queryByTestId('navigate')).not.toBeInTheDocument()
      expect(screen.queryByText('Protected Content')).not.toBeInTheDocument()
    })

    it('should display custom error messages correctly', () => {
      const customError = 'Session expired. Please log in again.'
      vi.mocked(useAuth).mockReturnValue({
        user: null,
        isAuthenticated: false,
        isAdmin: false,
        isLoading: false,
        error: customError,
        refetch: vi.fn()
      })

      render(
        <BrowserRouter>
          <ProtectedRoute requireAdmin={true}>
            <div>Admin Content</div>
          </ProtectedRoute>
        </BrowserRouter>
      )

      expect(screen.getByText("Erreur d'authentification")).toBeInTheDocument()
      expect(screen.getByText(customError)).toBeInTheDocument()
    })
  })
})
