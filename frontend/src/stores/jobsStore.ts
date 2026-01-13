import { create } from 'zustand'
import type { JobStatus, JobStatusResponse } from '../types/api'

export type JobKind = 'processing' | 'database_build' | 'database_append'

export type JobTerminalStatus = Extract<
  JobStatus,
  'completed' | 'failed' | 'timeout'
>

export interface TrackedJob {
  jobId: string
  kind: JobKind
  label: string

  status: JobStatus
  percent: number
  message: string | null
  startedAt: string | null
  updatedAt: string | null

  /** Last N distinct status messages (best-effort) */
  messageHistory: string[]

  /** If true, we already ran completion side-effects (toasts, query invalidation, auto-dismiss). */
  completionHandled: boolean

  /** Soft hide from UI (auto after completion) */
  dismissed: boolean

  context?: {
    databaseName?: string
    databaseId?: string
  }
}

export interface ToastItem {
  id: string
  severity: 'success' | 'error' | 'info' | 'warning'
  title: string
  description?: string

  /**
   * Auto-dismiss duration.
   * - undefined: defaults to 3000ms
   * - number: custom duration in ms
   * - null: sticky toast (never auto-dismiss)
   */
  durationMs?: number | null
}

interface JobsState {
  jobs: Record<string, TrackedJob>
  toasts: ToastItem[]

  registerJob: (job: {
    jobId: string
    kind: JobKind
    label: string
    context?: TrackedJob['context']
  }) => void
  upsertJobFromStatus: (jobId: string, payload: JobStatusResponse) => void
  markCompletionHandled: (jobId: string) => void
  dismissJob: (jobId: string) => void
  removeJob: (jobId: string) => void

  addToast: (toast: Omit<ToastItem, 'id'>) => string
  removeToast: (toastId: string) => void
}

const MAX_HISTORY = 20
const DEFAULT_TOAST_DURATION_MS = 3000

// Best-effort timer bookkeeping to avoid leaking timeouts when users manually close toasts.
const toastTimers = new Map<string, ReturnType<typeof globalThis.setTimeout>>()

const buildHistory = (prev: string[], nextMessage: string): string[] => {
  const trimmed = nextMessage.trim()
  if (!trimmed) return prev
  const last = prev[prev.length - 1]
  if (last === trimmed) return prev
  const next = [...prev, trimmed]
  return next.length > MAX_HISTORY
    ? next.slice(next.length - MAX_HISTORY)
    : next
}

export const useJobsStore = create<JobsState>((set) => ({
  jobs: {},
  toasts: [],

  registerJob: ({ jobId, kind, label, context }) =>
    set((state) => {
      // Don't overwrite an existing job (e.g., reload / re-register)
      if (state.jobs[jobId]) {
        return {
          jobs: {
            ...state.jobs,
            [jobId]: {
              ...state.jobs[jobId],
              kind,
              label,
              context: { ...state.jobs[jobId].context, ...context }
            }
          }
        }
      }

      const nowIso = new Date().toISOString()
      const job: TrackedJob = {
        jobId,
        kind,
        label,
        status: 'queued',
        percent: 0,
        message: null,
        startedAt: null,
        updatedAt: nowIso,
        messageHistory: [],
        completionHandled: false,
        dismissed: false,
        context
      }

      return {
        jobs: { ...state.jobs, [jobId]: job }
      }
    }),

  upsertJobFromStatus: (jobId, payload) =>
    set((state) => {
      const existing = state.jobs[jobId]
      const nextMessage = payload.message ?? null
      const nextHistory = nextMessage
        ? buildHistory(existing?.messageHistory ?? [], nextMessage)
        : (existing?.messageHistory ?? [])

      const updated: TrackedJob = {
        jobId,
        kind: existing?.kind ?? 'processing',
        label: existing?.label ?? `Job ${jobId}`,
        status: payload.status,
        percent: payload.percent,
        message: nextMessage,
        startedAt: payload.started_at ?? existing?.startedAt ?? null,
        updatedAt: payload.updated_at ?? existing?.updatedAt ?? null,
        messageHistory: nextHistory,
        completionHandled: existing?.completionHandled ?? false,
        dismissed: existing?.dismissed ?? false,
        context: existing?.context
      }

      return {
        jobs: {
          ...state.jobs,
          [jobId]: updated
        }
      }
    }),

  markCompletionHandled: (jobId) =>
    set((state) => {
      const job = state.jobs[jobId]
      if (!job) return state
      return {
        jobs: {
          ...state.jobs,
          [jobId]: { ...job, completionHandled: true }
        }
      }
    }),

  dismissJob: (jobId) =>
    set((state) => {
      const job = state.jobs[jobId]
      if (!job) return state
      return {
        jobs: {
          ...state.jobs,
          [jobId]: { ...job, dismissed: true }
        }
      }
    }),

  removeJob: (jobId) =>
    set((state) => {
      const next = { ...state.jobs }
      delete next[jobId]
      return { jobs: next }
    }),

  addToast: (toast) => {
    const id = crypto.randomUUID()

    // Push toast first, then schedule auto-dismiss (default 3s).
    set((state) => ({ toasts: [...state.toasts, { ...toast, id }] }))

    const durationMs = toast.durationMs ?? DEFAULT_TOAST_DURATION_MS
    if (durationMs !== null) {
      const handle = globalThis.setTimeout(() => {
        // Clear timer bookkeeping then remove toast.
        toastTimers.delete(id)
        set((state) => ({
          toasts: state.toasts.filter((t) => t.id !== id)
        }))
      }, durationMs)
      toastTimers.set(id, handle)
    }

    return id
  },

  removeToast: (toastId) => {
    const handle = toastTimers.get(toastId)
    if (handle) {
      globalThis.clearTimeout(handle)
      toastTimers.delete(toastId)
    }
    set((state) => ({
      toasts: state.toasts.filter((t) => t.id !== toastId)
    }))
  }
}))

export const selectActiveJobs = (jobs: Record<string, TrackedJob>) =>
  Object.values(jobs).filter(
    (j) => !j.dismissed && ['queued', 'running'].includes(j.status)
  )

export const selectVisibleJobs = (jobs: Record<string, TrackedJob>) =>
  Object.values(jobs).filter((j) => !j.dismissed)
