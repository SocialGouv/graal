import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { Admin } from './Admin'

// Mock the useAuth hook
vi.mock('../../hooks/useAuth', () => ({
  useAuth: vi.fn()
}))

// Mock the S3FileBrowser component
vi.mock('./S3FileBrowser/S3FileBrowser', () => ({
  S3FileBrowser: () => <div data-testid="s3-file-browser">S3 File Browser</div>
}))

// Mock react-router-dom
const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate
  }
})

const { useAuth } = await import('../../hooks/useAuth')

describe('Admin', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Error state', () => {
    it('should display error alert when there is an auth error', () => {
      vi.mocked(useAuth).mockReturnValue({
        user: null,
        isAuthenticated: false,
        isAdmin: false,
        isLoading: false,
        error: 'Failed to authenticate',
        refetch: vi.fn()
      })

      render(
        <BrowserRouter>
          <Admin />
        </BrowserRouter>
      )

      expect(screen.getByText('Erreur')).toBeInTheDocument()
      expect(screen.getByText('Failed to authenticate')).toBeInTheDocument()
      expect(screen.queryByTestId('s3-file-browser')).not.toBeInTheDocument()
      expect(screen.queryByText('Administration')).not.toBeInTheDocument()
    })

    it('should not render admin content when error is present', () => {
      vi.mocked(useAuth).mockReturnValue({
        user: { user_id: '1', email: 'admin@example.com', is_admin: true },
        isAuthenticated: true,
        isAdmin: true,
        isLoading: false,
        error: 'Network error',
        refetch: vi.fn()
      })

      render(
        <BrowserRouter>
          <Admin />
        </BrowserRouter>
      )

      expect(screen.getByText('Network error')).toBeInTheDocument()
      expect(screen.queryByText('Administration')).not.toBeInTheDocument()
    })
  })

  describe('Defense-in-depth authorization', () => {
    it('should deny access when isAdmin is false (ProtectedRoute bypass scenario)', () => {
      vi.mocked(useAuth).mockReturnValue({
        user: { user_id: '1', email: 'user@example.com', is_admin: false },
        isAuthenticated: true,
        isAdmin: false,
        isLoading: false,
        error: null,
        refetch: vi.fn()
      })

      render(
        <BrowserRouter>
          <Admin />
        </BrowserRouter>
      )

      expect(screen.getByText('Accès refusé')).toBeInTheDocument()
      expect(
        screen.getByText(
          "Vous n'avez pas les droits nécessaires pour accéder à cette page."
        )
      ).toBeInTheDocument()
      expect(screen.queryByText('Administration')).not.toBeInTheDocument()
      expect(screen.queryByTestId('s3-file-browser')).not.toBeInTheDocument()
    })

    it('should deny access even when user object exists but isAdmin is false', () => {
      vi.mocked(useAuth).mockReturnValue({
        user: {
          user_id: '2',
          email: 'normaluser@example.com',
          is_admin: false
        },
        isAuthenticated: true,
        isAdmin: false,
        isLoading: false,
        error: null,
        refetch: vi.fn()
      })

      render(
        <BrowserRouter>
          <Admin />
        </BrowserRouter>
      )

      expect(screen.getByText('Accès refusé')).toBeInTheDocument()
      expect(screen.queryByText('Administration')).not.toBeInTheDocument()
    })

    it('should check isAdmin after error check but before content rendering', () => {
      // This test ensures the order: error check -> isAdmin check -> content
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
          <Admin />
        </BrowserRouter>
      )

      // Should show access denied (isAdmin check), not error
      expect(screen.getByText('Accès refusé')).toBeInTheDocument()
      expect(screen.queryByText('Erreur')).not.toBeInTheDocument()
      expect(screen.queryByText('Administration')).not.toBeInTheDocument()
    })
  })

  describe('Successful admin rendering', () => {
    it('should render admin content for admin users', () => {
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
          <Admin />
        </BrowserRouter>
      )

      expect(screen.getByText('Administration')).toBeInTheDocument()
      expect(screen.getByText("Retour à l'accueil")).toBeInTheDocument()
      expect(
        screen.getByText('Connecté en tant que : admin@example.com')
      ).toBeInTheDocument()
      expect(screen.getByTestId('s3-file-browser')).toBeInTheDocument()
    })

    it('should display user email when available', () => {
      vi.mocked(useAuth).mockReturnValue({
        user: { user_id: '1', email: 'test@example.com', is_admin: true },
        isAuthenticated: true,
        isAdmin: true,
        isLoading: false,
        error: null,
        refetch: vi.fn()
      })

      render(
        <BrowserRouter>
          <Admin />
        </BrowserRouter>
      )

      expect(
        screen.getByText('Connecté en tant que : test@example.com')
      ).toBeInTheDocument()
    })

    it('should not display user email section when user email is missing', () => {
      vi.mocked(useAuth).mockReturnValue({
        user: { user_id: '1', is_admin: true, email: null },
        isAuthenticated: true,
        isAdmin: true,
        isLoading: false,
        error: null,
        refetch: vi.fn()
      })

      render(
        <BrowserRouter>
          <Admin />
        </BrowserRouter>
      )

      expect(screen.queryByText(/Connecté en tant que/)).not.toBeInTheDocument()
    })
  })

  describe('Navigation', () => {
    it('should navigate to home when back button is clicked', async () => {
      const user = userEvent.setup()

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
          <Admin />
        </BrowserRouter>
      )

      const backButton = screen.getByRole('button', {
        name: /retour à l'accueil/i
      })
      await user.click(backButton)

      expect(mockNavigate).toHaveBeenCalledWith('/')
      expect(mockNavigate).toHaveBeenCalledTimes(1)
    })
  })

  describe('S3FileBrowser integration', () => {
    it('should properly integrate S3FileBrowser component', () => {
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
          <Admin />
        </BrowserRouter>
      )

      const s3Browser = screen.getByTestId('s3-file-browser')
      expect(s3Browser).toBeInTheDocument()
      expect(s3Browser).toHaveTextContent('S3 File Browser')
    })

    it('should not render S3FileBrowser when there is an error', () => {
      vi.mocked(useAuth).mockReturnValue({
        user: { user_id: '1', email: 'admin@example.com', is_admin: true },
        isAuthenticated: true,
        isAdmin: true,
        isLoading: false,
        error: 'Auth error',
        refetch: vi.fn()
      })

      render(
        <BrowserRouter>
          <Admin />
        </BrowserRouter>
      )

      expect(screen.queryByTestId('s3-file-browser')).not.toBeInTheDocument()
    })
  })

  describe('Edge cases', () => {
    it('should handle user without email gracefully', () => {
      vi.mocked(useAuth).mockReturnValue({
        user: { user_id: '1', is_admin: true, email: null },
        isAuthenticated: true,
        isAdmin: true,
        isLoading: false,
        error: null,
        refetch: vi.fn()
      })

      render(
        <BrowserRouter>
          <Admin />
        </BrowserRouter>
      )

      expect(screen.getByText('Administration')).toBeInTheDocument()
      expect(screen.getByTestId('s3-file-browser')).toBeInTheDocument()
    })

    it('should render admin interface even without a user object (edge case)', () => {
      vi.mocked(useAuth).mockReturnValue({
        user: null,
        isAuthenticated: true,
        isAdmin: true,
        isLoading: false,
        error: null,
        refetch: vi.fn()
      })

      render(
        <BrowserRouter>
          <Admin />
        </BrowserRouter>
      )

      expect(screen.getByText('Administration')).toBeInTheDocument()
      expect(screen.getByTestId('s3-file-browser')).toBeInTheDocument()
      expect(screen.queryByText(/Connecté en tant que/)).not.toBeInTheDocument()
    })
  })
})
