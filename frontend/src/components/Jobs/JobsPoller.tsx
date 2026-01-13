import { useQuery } from '@tanstack/react-query'
import React, { useEffect, useMemo } from 'react'
import { queryClient } from '../../providers/QueryProvider'
import { apiService } from '../../services/api'
import { useJobsStore, type TrackedJob } from '../../stores/jobsStore'
const DB_RELATED_QUERY_KEYS = [
  ['databases'],
  ['appendable-databases'],
  ['similarity-databases']
] as const
const isTerminal = (status: string) =>
  ['completed', 'failed', 'timeout'].includes(status)
const toastForTerminalStatus = (job: TrackedJob) => {
  if (job.status === 'completed') {
    return {
      severity: 'success' as const,
      title: `${job.label} — terminé`,
      description: job.message ?? undefined
    }
  }
  return {
    severity: 'error' as const,
    title: `${job.label} — ${job.status}`,
    description: job.message ?? undefined
  }
}
/**
 * Global poller that:
 * - polls each active job status
 * - updates jobs store
 * - triggers completion side-effects once (toasts + invalidations + auto-dismiss)
 */
export const JobsPoller: React.FC = () => {
  const {
    jobs,
    upsertJobFromStatus,
    markCompletionHandled,
    addToast,
    dismissJob
  } = useJobsStore()
  const activeJobs = Object.values(jobs).filter(
    (j) => !j.dismissed && !isTerminal(j.status)
  )
  const activeJobIds = useMemo(
    () => activeJobs.map((j) => j.jobId).sort(),
    [activeJobs]
  )
  const pollQuery = useQuery({
    queryKey: ['jobsStatus', activeJobIds],
    queryFn: async () => {
      const results = await Promise.all(
        activeJobIds.map((jobId) => apiService.getJobStatus(jobId))
      )
      return results
    },
    enabled: activeJobIds.length > 0,
    refetchInterval: activeJobIds.length > 0 ? 2000 : false,
    retry: 1
  })
  useEffect(() => {
    if (!pollQuery.data) return
    for (const payload of pollQuery.data) {
      upsertJobFromStatus(payload.job_id, payload)
    }
  }, [pollQuery.data, upsertJobFromStatus])
  // Completion handler
  useEffect(() => {
    for (const job of Object.values(jobs)) {
      if (job.dismissed) continue
      if (!isTerminal(job.status)) continue
      if (job.completionHandled) continue
      // Toast
      addToast(toastForTerminalStatus(job))
      // Invalidate DB-related queries when DB jobs complete
      if (job.kind === 'database_build' || job.kind === 'database_append') {
        for (const queryKey of DB_RELATED_QUERY_KEYS) {
          void queryClient.invalidateQueries({ queryKey })
        }
        const dbName = job.context?.databaseName
        if (dbName) {
          void queryClient.invalidateQueries({
            queryKey: ['database-manifest', dbName]
          })
        }
      }

      markCompletionHandled(job.jobId)

      // Auto-dismiss (as requested)
      globalThis.setTimeout(() => {
        dismissJob(job.jobId)
      }, 3000)
    }
  }, [jobs, addToast, dismissJob, markCompletionHandled])

  return null
}
