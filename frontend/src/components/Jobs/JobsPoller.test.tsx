import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, cleanup, render } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useJobsStore } from '../../stores/jobsStore'
import { JobsPoller } from './JobsPoller'

describe('JobsPoller', () => {
  let queryClient: QueryClient

  beforeEach(async () => {
    vi.useFakeTimers()
    vi.clearAllMocks()

    // Ensure store isolation.
    await act(async () => {
      useJobsStore.setState({ jobs: {}, toasts: [] })
    })

    // Fresh query client per test to avoid cache/state leakage.
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false
        }
      }
    })
  })

  afterEach(async () => {
    // Ensure components are unmounted before we reset shared stores/clients.
    cleanup()

    // Best-effort: drain any timers scheduled during the test.
    await act(async () => {
      await vi.runOnlyPendingTimersAsync()
    })

    queryClient.clear()
    await act(async () => {
      useJobsStore.setState({ jobs: {}, toasts: [] })
    })
    vi.clearAllTimers()
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  it('invalidates database-manifest by databaseId when a DB job completes', async () => {
    // We only care about the call signature; prevent QueryClient internal state updates
    // from causing act() warnings or cross-test leakage.
    const invalidateSpy = vi
      .spyOn(queryClient, 'invalidateQueries')
      .mockResolvedValue(undefined)

    // Seed the store with a terminal DB job.
    // The completion effect should run once on mount.
    const dbId = '11111111-1111-1111-1111-111111111111'
    await act(async () => {
      useJobsStore.setState({
        jobs: {
          'job-1': {
            jobId: 'job-1',
            kind: 'database_append',
            label: 'Rebuild base MyDB',
            status: 'completed',
            percent: 100,
            message: 'done',
            startedAt: null,
            updatedAt: null,
            messageHistory: [],
            completionHandled: false,
            dismissed: false,
            context: {
              databaseId: dbId,
              databaseName: 'MyDB'
            }
          }
        },
        toasts: []
      })
    })

    await act(async () => {
      render(
        <QueryClientProvider client={queryClient}>
          <JobsPoller />
        </QueryClientProvider>
      )

      // Flush microtasks so React effects + external store updates happen within act().
      await Promise.resolve()
    })

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ['database-manifest', dbId]
    })
  })
})
