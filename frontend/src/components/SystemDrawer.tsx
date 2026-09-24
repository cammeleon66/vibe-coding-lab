import { History, Network, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import type { JourneyActivity, StoryScene, SystemCall } from '../api/types'

export function SystemDrawer({
  open,
  onClose,
  calls,
  activity,
  scenes,
}: {
  open: boolean
  onClose: () => void
  calls: SystemCall[]
  activity: JourneyActivity[]
  scenes: StoryScene[]
}) {
  const [tab, setTab] = useState<'calls' | 'timeline'>('calls')
  const closeRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (!open) return
    closeRef.current?.focus()
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null
  const sceneTitle = (id: string) => scenes.find((scene) => scene.id === id)?.title ?? id

  return (
    <div className="drawer-backdrop" onClick={onClose}>
      <aside
        className="system-drawer"
        role="dialog"
        aria-modal="true"
        aria-label="Audit log"
        onClick={(event) => event.stopPropagation()}
      >
        <header>
          <div>
            <p className="eyebrow">Audit log</p>
            <h2>Session activity</h2>
          </div>
          <button ref={closeRef} className="icon-button" type="button" onClick={onClose}>
            <X size={18} />
            <span className="sr-only">Close</span>
          </button>
        </header>
        <div className="drawer-tabs" role="tablist">
          <button
            role="tab"
            type="button"
            aria-selected={tab === 'calls'}
            onClick={() => setTab('calls')}
          >
            <Network size={15} />
            System requests <span>{calls.length}</span>
          </button>
          <button
            role="tab"
            type="button"
            aria-selected={tab === 'timeline'}
            onClick={() => setTab('timeline')}
          >
            <History size={15} />
            Clinical events <span>{activity.length}</span>
          </button>
        </div>
        {tab === 'calls' ? (
          <div role="tabpanel" aria-label="System requests">
            {calls.length === 0 ? (
              <p className="drawer-empty">No source system requests recorded.</p>
            ) : (
              <ol className="call-list">
                {[...calls].reverse().map((call) => (
                  <li key={call.id}>
                    <div>
                      <strong>{call.system}</strong>
                      <em className={call.status === '200 OK' ? 'ok' : 'failed'}>{call.status}</em>
                    </div>
                    <code>{call.endpoint}</code>
                    <p>{call.detail}</p>
                    <small>{sceneTitle(call.scene)}</small>
                  </li>
                ))}
              </ol>
            )}
            <p className="drawer-note">
              Requests are answered by the source institution's own systems. No central data store is used.
            </p>
          </div>
        ) : (
          <div role="tabpanel" aria-label="Clinical events">
            {activity.length === 0 ? (
              <p className="drawer-empty">No clinical events recorded.</p>
            ) : (
              <ol className="timeline-list">
                {[...activity].reverse().map((event) => (
                  <li key={event.id}>
                    <small>
                      {event.actor} · {event.institution}
                    </small>
                    <strong>{event.title}</strong>
                    <p>{event.detail}</p>
                  </li>
                ))}
              </ol>
            )}
          </div>
        )}
      </aside>
    </div>
  )
}
