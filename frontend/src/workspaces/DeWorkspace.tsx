import { useState } from 'react'
import { Inbox } from 'lucide-react'
import { api } from '../api/client'
import type { InboxCase } from '../api/types'
import { useLoad } from '../lib'
import { CaseView } from './ReviewCase'

export function DeWorkspace({ onChanged }: { onChanged: () => void }) {
  const inbox = useLoad(api.de.inbox, 4000)
  const [selected, setSelected] = useState<InboxCase | null>(null)

  const open = async (caseId: string) => {
    setSelected(await api.de.case(caseId))
    void inbox.refresh()
  }

  return (
    <div className="split">
      <aside className="sidebar" aria-label="Inbox">
        <h2>
          <Inbox aria-hidden size={16} /> Peer-review inbox
        </h2>
        {inbox.error && (
          <p className="alert danger" role="alert">
            {inbox.error}
          </p>
        )}
        <ul className="worklist">
          {inbox.data?.map((item) => (
            <li key={item.case_id}>
              <button type="button" aria-current={selected?.case_id === item.case_id} onClick={() => void open(item.case_id)}>
                <strong>
                  {item.from_site} · {item.case_id}
                </strong>
                <span>
                  {item.bundle.subject.sex}, {item.bundle.subject.ageBand} · {item.report.shared_resources} resources
                </span>
                <span className="muted">{item.question.slice(0, 80)}…</span>
                <span className={`pill ${item.status === 'new' ? 'warn' : item.status === 'completed' ? 'ok' : ''}`}>
                  {item.status === 'new' ? 'New' : item.status === 'completed' ? 'Opinion sent' : 'In review'}
                </span>
              </button>
            </li>
          ))}
        </ul>
        {inbox.data?.length === 0 && (
          <p className="empty small">No cases yet. Cases appear here when a hospital shares an approved package.</p>
        )}
      </aside>
      <section className="content">
        {selected ? (
          <CaseView
            item={selected}
            onChanged={(value) => {
              setSelected(value)
              void inbox.refresh()
              onChanged()
            }}
          />
        ) : (
          <p className="empty">Open a case from the inbox.</p>
        )}
      </section>
    </div>
  )
}
