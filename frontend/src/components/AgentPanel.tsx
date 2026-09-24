import { Bot, Check, Circle, LoaderCircle, Play } from 'lucide-react'
import type { AgentBrief } from '../api/types'

export function AgentPanel({
  brief,
  busy,
  canResume,
  onResume,
}: {
  brief: AgentBrief
  busy: boolean
  canResume: boolean
  onResume: () => void
}) {
  const workingIndex = busy ? brief.steps.findIndex((step) => step.status === 'pending') : -1
  return (
    <aside className="agent-panel" aria-label={brief.name}>
      <header className="agent-header">
        <span className="agent-icon" aria-hidden="true">
          <Bot size={16} />
        </span>
        <div>
          <strong>{brief.name}</strong>
          <small>Working for {brief.works_for}</small>
        </div>
        <span className={`agent-state ${busy ? 'working' : ''}`}>
          {busy ? 'Running' : 'Idle'}
        </span>
      </header>
      <p className="agent-summary" aria-live="polite">
        {brief.summary}
      </p>
      <ol className="agent-steps">
        {brief.steps.map((step, index) => {
          const working = index === workingIndex
          const state = step.status === 'done' ? 'done' : working ? 'working' : 'pending'
          return (
            <li className={`agent-step ${state}`} key={step.label}>
              <span className="agent-step-icon" aria-hidden="true">
                {state === 'done' && <Check size={13} strokeWidth={3} />}
                {state === 'working' && <LoaderCircle size={14} className="spin" />}
                {state === 'pending' && <Circle size={9} />}
              </span>
              <div>
                <strong>{step.label}</strong>
                <span>{working ? 'Working…' : step.detail}</span>
                {step.call && (
                  <code>
                    {step.status === 'done' && <em>200 OK</em>}
                    {step.call}
                  </code>
                )}
              </div>
            </li>
          )
        })}
      </ol>
      {canResume && !busy && (
        <button className="agent-resume" type="button" onClick={onResume}>
          <Play size={14} />
          Resume assistant tasks
        </button>
      )}
      <p className="agent-boundary">{brief.boundary}</p>
    </aside>
  )
}
