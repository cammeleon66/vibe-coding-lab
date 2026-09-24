import {
  Check,
  CircleAlert,
  ClipboardList,
  Eye,
  Info,
  LoaderCircle,
  RotateCcw,
  User,
  X,
} from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import type { SceneId } from '../api/types'
import { AgentPanel } from '../components/AgentPanel'
import { SystemDrawer } from '../components/SystemDrawer'
import { sceneEntryWork } from '../scenes/entryWork'
import { sceneComponents } from '../scenes/registry'
import { patientContext } from './patientContext'
import { useJourney } from './useJourney'

export function StoryShell() {
  const journey = useJourney()
  const { snapshot, busy, error, notice } = journey
  const [reviewing, setReviewing] = useState<SceneId | null>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const closeDrawer = useCallback(() => setDrawerOpen(false), [])
  const headingRef = useRef<HTMLHeadingElement>(null)
  const current = snapshot?.storyline.current_scene
  const shown = reviewing ?? current

  useEffect(() => {
    headingRef.current?.focus()
  }, [shown])

  if (!snapshot || !current || !shown) {
    return (
      <div className="app-loading" role="status">
        {error ? (
          <>
            <CircleAlert size={16} aria-hidden="true" />
            {error}
          </>
        ) : (
          <>
            <LoaderCircle size={16} className="spin" aria-hidden="true" />
            Loading…
          </>
        )}
      </div>
    )
  }

  const story = snapshot.storyline
  const scene = story.scenes.find((item) => item.id === shown) ?? story.scenes[story.current_index]
  const sceneIndex = story.scenes.findIndex((item) => item.id === scene.id)
  const readOnly = reviewing !== null && reviewing !== current
  const Scene = sceneComponents[scene.id]
  const pendingWork = readOnly ? [] : sceneEntryWork(current, snapshot)
  const agent = readOnly ? null : story.agent
  const patient = patientContext(snapshot, scene)

  return (
    <div className="ehr">
      <header className="ehr-appbar">
        <div className="ehr-product">
          <strong>OncoExchange</strong>
          <span>Federated oncology collaboration · synthetic data</span>
        </div>
        <div className="ehr-user">
          <User size={14} aria-hidden="true" />
          <span>
            <strong>{scene.actor.name}</strong> · {scene.actor.institution}
          </span>
        </div>
        <div className="ehr-appbar-tools">
          <button className="appbar-button" type="button" onClick={() => setDrawerOpen(true)}>
            <ClipboardList size={14} aria-hidden="true" />
            Audit log ({story.system_calls.length})
          </button>
          <button
            className="appbar-button"
            type="button"
            disabled={busy}
            onClick={() => {
              setReviewing(null)
              void journey.reset()
            }}
          >
            <RotateCcw size={14} aria-hidden="true" />
            Reset
          </button>
        </div>
      </header>

      <section className="ehr-patient" aria-label="Patient context">
        {patient ? (
          <>
            <span className="patient-name">{patient.name}</span>
            <span>
              <small>ID</small>
              {patient.id}
            </span>
            <span>{patient.detail}</span>
            <span>
              <small>Treating centre</small>
              {patient.institution}
            </span>
            <span className="badge neutral">Synthetic</span>
          </>
        ) : (
          <span className="patient-none">No patient selected</span>
        )}
      </section>

      <div className="ehr-body">
        <nav className="ehr-nav" aria-label="Workflow">
          {story.chapters.map((chapter) => (
            <div key={chapter.id} className="nav-group">
              <p className="nav-group-title">
                {chapter.title}
                <small>{chapter.scope}</small>
              </p>
              <ol>
                {story.scenes
                  .map((item, index) => ({ item, index }))
                  .filter(({ item }) => item.chapter === chapter.id)
                  .map(({ item, index }) => (
                    <li key={item.id}>
                      <button
                        type="button"
                        className={`nav-item ${item.status} ${item.id === scene.id ? 'shown' : ''}`}
                        disabled={index > story.current_index}
                        aria-current={item.id === scene.id ? 'step' : undefined}
                        onClick={() => setReviewing(item.id === current ? null : item.id)}
                      >
                        <span className="nav-status" aria-hidden="true">
                          {item.status === 'complete' ? <Check size={12} strokeWidth={3} /> : index + 1}
                        </span>
                        <span className="nav-label">{item.title}</span>
                        <span className="sr-only">
                          {item.status === 'complete' ? 'completed' : item.status}
                        </span>
                      </button>
                    </li>
                  ))}
              </ol>
            </div>
          ))}
        </nav>

        <main className="ehr-main">
          <div className="page-header">
            <div>
              <p className="page-breadcrumb">
                Step {sceneIndex + 1} of {story.scenes.length} ·{' '}
                {story.chapters.find((item) => item.id === scene.chapter)?.scope}
              </p>
              <h1 ref={headingRef} tabIndex={-1}>
                {scene.title}
              </h1>
            </div>
            <dl className="page-meta">
              <div>
                <dt>Responsible</dt>
                <dd>{scene.actor.name}</dd>
              </div>
              <div>
                <dt>Role</dt>
                <dd>{scene.actor.role}</dd>
              </div>
              <div>
                <dt>Status</dt>
                <dd>
                  <span className={`badge ${scene.status === 'complete' ? 'success' : 'info'}`}>
                    {scene.status === 'complete' ? 'Completed' : 'In progress'}
                  </span>
                </dd>
              </div>
            </dl>
          </div>

          {readOnly && (
            <div className="message info" role="status">
              <Eye size={15} aria-hidden="true" />
              <span>Read-only view of a completed step.</span>
              <button type="button" className="link-button" onClick={() => setReviewing(null)}>
                Return to step {story.current_index + 1}
              </button>
            </div>
          )}
          {!readOnly && story.handoff && (
            <div className="message info" role="note" aria-label="Handover">
              <Info size={15} aria-hidden="true" />
              <span>
                Transferred from <strong>{story.handoff.from_actor.name}</strong> (
                {story.handoff.from_actor.institution}): {story.handoff.carried}
              </span>
            </div>
          )}
          {error && (
            <div className="message error" role="alert">
              <CircleAlert size={15} aria-hidden="true" />
              <span>{error}</span>
              <button type="button" className="icon-button" onClick={journey.dismissError}>
                <X size={14} aria-hidden="true" />
                <span className="sr-only">Dismiss</span>
              </button>
            </div>
          )}
          {notice && (
            <div className="message success" role="status">
              <Check size={15} aria-hidden="true" />
              <span>{notice}</span>
            </div>
          )}

          <section className="work-area" aria-label={scene.title}>
            <Scene
              key={scene.id}
              snapshot={snapshot}
              busy={busy}
              readOnly={readOnly}
              act={journey.act}
              runAgent={journey.runAgent}
              deliverImagingEvent={journey.deliverImagingEvent}
              reset={journey.reset}
            />
          </section>
        </main>

        {agent && (
          <AgentPanel
            brief={agent}
            busy={busy}
            canResume={pendingWork.length > 0}
            onResume={() => void journey.runAgent(pendingWork)}
          />
        )}
      </div>

      {!readOnly && story.advance_label && (
        <footer className="ehr-toolbar">
          <p className={story.can_advance ? 'ready' : 'blocked'}>
            {story.can_advance ? (
              <>
                <Check size={14} aria-hidden="true" />
                Step complete. Next: {story.scenes[story.current_index + 1]?.title}
              </>
            ) : (
              <>
                <CircleAlert size={14} aria-hidden="true" />
                {story.blocked_reason}
              </>
            )}
          </p>
          <button
            className="btn primary"
            type="button"
            disabled={busy || !story.can_advance}
            onClick={() => void journey.advance()}
          >
            {busy && <LoaderCircle size={14} className="spin" aria-hidden="true" />}
            {story.advance_label}
          </button>
        </footer>
      )}

      <SystemDrawer
        open={drawerOpen}
        onClose={closeDrawer}
        calls={story.system_calls}
        activity={snapshot.activity}
        scenes={story.scenes}
      />
    </div>
  )
}
