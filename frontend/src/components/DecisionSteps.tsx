import { Check } from 'lucide-react'
import type { ReactNode } from 'react'

export interface DecisionStep {
  id: string
  title: string
  done: boolean
  doneSummary: string
  content: ReactNode
}

/** A short list of decisions where only the next open decision is expanded. */
export function DecisionSteps({ steps }: { steps: DecisionStep[] }) {
  const openIndex = steps.findIndex((step) => !step.done)
  return (
    <ol className="decision-steps">
      {steps.map((step, index) => {
        const state = step.done ? 'done' : index === openIndex ? 'open' : 'later'
        return (
          <li className={`decision-step ${state}`} key={step.id}>
            <span className="decision-marker" aria-hidden="true">
              {step.done ? <Check size={14} strokeWidth={3} /> : index + 1}
            </span>
            <div className="decision-body">
              <h2>{step.title}</h2>
              {state === 'done' && <p className="decision-summary">{step.doneSummary}</p>}
              {state === 'open' && step.content}
            </div>
          </li>
        )
      })}
    </ol>
  )
}
