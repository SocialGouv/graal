import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useProcessingStore } from '../stores/processingStore'
import { ProcessingPage } from './ProcessingPage'

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => vi.fn()
  }
})

// Mock API hooks
const mockMutate = vi.fn()
vi.mock('../hooks/useApi', () => ({
  useUploadFile: () => ({ mutate: mockMutate, isPending: false }),
  useDownloadResults: () => ({ mutate: vi.fn(), isPending: false }),
  useDownloadExcelResults: () => ({ mutate: vi.fn(), isPending: false }),
  useJobStatus: () => ({}),
  useResultsPreview: () => ({})
}))

// Mock API service used by useQuery in the page
vi.mock('../services/api', () => ({
  apiService: {
    listSimilarityDatabases: vi.fn().mockResolvedValue([])
  }
}))

const renderWithProviders = (ui: React.ReactElement) => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } }
  })

  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
  )
}

describe('ProcessingPage - mission filter payload', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useProcessingStore.getState().reset()

    // Put the page at step 3 and fill required fields
    useProcessingStore.setState((state) => ({
      ...state,
      currentStep: 3,
      selectedConfigFile: 'Fichier.xlsx',
      uploadedFile: new File(['{}'], 'amendements.json', {
        type: 'application/json'
      }),
      processingConfig: {
        ...state.processingConfig,
        // Make similarity search config valid (the page now blocks submission otherwise)
        similaritySearch: {
          ...state.processingConfig.similaritySearch,
          enabled: false
        },
        // Summary generation requires an LLM type when enabled; disable for this test.
        summaryGeneration: {
          ...state.processingConfig.summaryGeneration,
          enabled: false
        },
        missionShortTitleFilter: ['Santé', 'Travail'],
        // ensure form validation passes: at least one feature enabled
        attribution: {
          ...state.processingConfig.attribution,
          enabled: true
        }
      }
    }))
  })

  it('should include mission_short_title_filter in /process request payload when non-empty', async () => {
    const user = userEvent.setup()

    renderWithProviders(<ProcessingPage />)

    await user.click(
      screen.getByRole('button', { name: /commencer le traitement/i })
    )

    expect(mockMutate).toHaveBeenCalledTimes(1)
    const args = mockMutate.mock.calls[0][0]
    expect(
      args.processingRequest.processing_config.mission_short_title_filter
    ).toEqual(['Santé', 'Travail'])
  })

  it('should omit mission_short_title_filter when empty', async () => {
    const user = userEvent.setup()

    useProcessingStore.setState((state) => ({
      ...state,
      processingConfig: {
        ...state.processingConfig,
        similaritySearch: {
          ...state.processingConfig.similaritySearch,
          enabled: false
        },
        summaryGeneration: {
          ...state.processingConfig.summaryGeneration,
          enabled: false
        },
        missionShortTitleFilter: [],
        attribution: {
          ...state.processingConfig.attribution,
          enabled: true
        }
      }
    }))

    renderWithProviders(<ProcessingPage />)

    await user.click(
      screen.getByRole('button', { name: /commencer le traitement/i })
    )

    expect(mockMutate).toHaveBeenCalledTimes(1)
    const args = mockMutate.mock.calls[0][0]
    expect(
      'mission_short_title_filter' in args.processingRequest.processing_config
    ).toBe(false)
  })
})

describe('ProcessingPage - similarity search validation blocks start', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useProcessingStore.getState().reset()

    // Step 3 with required fields
    useProcessingStore.setState((state) => ({
      ...state,
      currentStep: 3,
      selectedConfigFile: 'Fichier.xlsx',
      uploadedFile: new File(['{}'], 'amendements.json', {
        type: 'application/json'
      }),
      processingConfig: {
        ...state.processingConfig,
        similaritySearch: {
          ...state.processingConfig.similaritySearch,
          enabled: true,
          originProject: '',
          databaseId: null
        },
        attribution: {
          ...state.processingConfig.attribution,
          enabled: true
        }
      }
    }))
  })

  it('should not start processing when similarity search is enabled but required fields are missing', async () => {
    const user = userEvent.setup()
    renderWithProviders(<ProcessingPage />)

    await user.click(
      screen.getByRole('button', { name: /commencer le traitement/i })
    )

    expect(mockMutate).toHaveBeenCalledTimes(0)
  })
})

describe('ProcessingPage - back to configuration on processing failure', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useProcessingStore.getState().reset()

    // Put page in processing mode with an error
    useProcessingStore.setState((state) => ({
      ...state,
      currentStep: 4,
      selectedConfigFile: 'Fichier.xlsx',
      uploadedFile: new File(['{}'], 'amendements.json', {
        type: 'application/json'
      }),
      processingStatus: 'failed',
      error: 'Boom'
    }))
  })

  it('should return to step 2 and exit processing mode when clicking "Retour à la configuration"', async () => {
    const user = userEvent.setup()

    renderWithProviders(<ProcessingPage />)

    await user.click(
      screen.getByRole('button', { name: /retour à la configuration/i })
    )

    const state = useProcessingStore.getState()
    expect(state.currentStep).toBe(2)
    expect(state.processingStatus).toBe('idle')
    expect(state.selectedConfigFile).toBe('Fichier.xlsx')
  })
})
