import { Alert } from '@codegouvfr/react-dsfr/Alert'
import React, { useEffect } from 'react'
import { useJobsStore } from '../../stores/jobsStore'

/**
 * Minimal toast center based on DSFR Alert.
 * Auto-dismiss behavior is handled where the toast is created.
 */
export const ToastCenter: React.FC = () => {
  const { toasts, removeToast } = useJobsStore()

  // Ensure ESC/close behavior is possible (manual close)
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        // Remove newest toast first
        const last = toasts[toasts.length - 1]
        if (last) removeToast(last.id)
      }
    }
    globalThis.addEventListener('keydown', onKeyDown)
    return () => globalThis.removeEventListener('keydown', onKeyDown)
  }, [toasts, removeToast])

  if (toasts.length === 0) return null

  return (
    <div
      aria-live="polite"
      aria-atomic="true"
      style={{
        position: 'fixed',
        top: 16,
        right: 16,
        zIndex: 10000,
        width: 420,
        maxWidth: 'calc(100vw - 32px)'
      }}
    >
      {toasts
        .slice()
        .reverse()
        .map((t) => (
          <div key={t.id} style={{ marginBottom: 12 }}>
            <Alert
              severity={t.severity}
              title={t.title}
              description={t.description ?? ''}
              closable
              onClose={() => removeToast(t.id)}
              small
            />
          </div>
        ))}
    </div>
  )
}
