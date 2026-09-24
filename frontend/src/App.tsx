import { useEffect, useMemo, useState } from 'react'
import { Building2, CheckCircle2, Circle, ListChecks, ShieldCheck } from 'lucide-react'
import './App.css'
import { api } from './api/client'
import type { Role, SiteStatus } from './api/types'
import { useLoad } from './lib'
import { NlWorkspace } from './workspaces/NlWorkspace'
import { DeWorkspace } from './workspaces/DeWorkspace'
import { ControlRoom } from './workspaces/ControlRoom'
import { ResearchView } from './workspaces/ResearchView'

const ROLES: {
  id: Role
  label: string
  person: string
  institution: string
  site: 'nl' | 'de' | 'hub'
}[] = [
  { id: 'nl', label: 'NL oncologist', person: 'Dr Pieter de Boer', institution: 'UMC Utrecht', site: 'nl' },
  { id: 'de', label: 'Heidelberg expert', person: 'Dr Anna Müller', institution: 'Universitätsklinikum Heidelberg', site: 'de' },
  { id: 'control', label: 'Control room', person: 'Federation operations', institution: 'Federation hub', site: 'hub' },
  { id: 'research', label: 'Researcher', person: 'Clinical researcher', institution: 'Federation hub', site: 'hub' },
]

function roleFromHash(): Role {
  const value = window.location.hash.replace('#', '')
  return (ROLES.find((role) => role.id === value)?.id ?? 'nl') as Role
}

export interface LocalProgress {
  openedChart: boolean
  searchedExperts: boolean
}

export default function App() {
  const [role, setRole] = useState<Role>(roleFromHash)
  const [checklistOpen, setChecklistOpen] = useState(false)
  const [local, setLocal] = useState<LocalProgress>({ openedChart: false, searchedExperts: false })
  const sites = useLoad(api.sites, 5000)
  const progress = useLoad(api.progress, 5000)

  useEffect(() => {
    const onHash = () => setRole(roleFromHash())
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])

  const switchRole = (next: Role) => {
    window.history.replaceState(null, '', `#${next}`)
    setRole(next)
  }

  const current = ROLES.find((item) => item.id === role)!
  const siteStatus: SiteStatus | undefined = sites.data?.sites.find((s) => s.site === current.site)
  const refreshShared = () => {
    void sites.refresh()
    void progress.refresh()
  }

  const checklist = useMemo(
    () => [
      { label: "Open Maria's chart (NL oncologist)", done: local.openedChart },
      { label: 'Search the expertise catalogue', done: local.searchedExperts },
      { label: 'Send the secure case to Heidelberg', done: !!progress.data?.case_sent },
      { label: 'Compare with Heidelberg patients', done: !!progress.data?.cohort_compared },
      { label: 'Return the opinion to UMC Utrecht', done: !!progress.data?.opinion_returned },
      { label: 'Turn it into a research question', done: !!progress.data?.research_run },
      { label: 'Disconnect test: stop Heidelberg', done: !!progress.data?.disconnect_seen },
    ],
    [local, progress.data],
  )
  const doneCount = checklist.filter((item) => item.done).length

  return (
    <div className={`app role-${role}`}>
      <header className="topbar">
        <div className="brand">
          <ShieldCheck aria-hidden size={22} />
          <div>
            <strong>European Oncology Network</strong>
            <span>One patient. Europe&apos;s expertise.</span>
          </div>
          <span className="pill synthetic">Synthetic data</span>
        </div>
        <nav className="role-switcher" aria-label="Demo role">
          <span className="role-switcher-label">Current role</span>
          {ROLES.map((item) => (
            <button
              key={item.id}
              type="button"
              className={item.id === role ? 'role active' : 'role'}
              aria-pressed={item.id === role}
              onClick={() => switchRole(item.id)}
            >
              <span className="role-name">{item.label}</span>
              <span className="role-institution">{item.institution}</span>
            </button>
          ))}
        </nav>
        <div className="checklist-wrap">
          <button
            type="button"
            className="checklist-toggle"
            aria-expanded={checklistOpen}
            aria-controls="presenter-checklist"
            onClick={() => setChecklistOpen((open) => !open)}
          >
            <ListChecks aria-hidden size={16} /> Presenter checklist {doneCount}/{checklist.length}
          </button>
          {checklistOpen && (
            <div id="presenter-checklist" className="checklist" role="region" aria-label="Presenter checklist">
              <ol>
                {checklist.map((item) => (
                  <li key={item.label} className={item.done ? 'done' : ''}>
                    {item.done ? <CheckCircle2 aria-hidden size={16} /> : <Circle aria-hidden size={16} />}
                    <span>{item.label}</span>
                    <span className="sr-only">{item.done ? '(done)' : '(open)'}</span>
                  </li>
                ))}
              </ol>
              <p className="muted">Tracks progress only. Switch roles and click freely; nothing is scripted.</p>
            </div>
          )}
        </div>
      </header>

      <div
        className={`env-banner env-${current.site} ${siteStatus && !siteStatus.reachable ? 'env-down' : ''}`}
        role="status"
      >
        <Building2 aria-hidden size={16} />
        <strong>{siteStatus?.environment ?? current.institution.toUpperCase()}</strong>
        <span>
          Signed in as {current.person} · {current.institution}
        </span>
        <span className="env-meta">
          {siteStatus
            ? siteStatus.reachable
              ? `Separate hospital service · version ${siteStatus.version ?? 'n/a'} · generation ${siteStatus.generation ?? '?'}`
              : `${current.site === 'de' ? 'Heidelberg' : current.institution} unavailable — federated result incomplete`
            : 'Connecting…'}
        </span>
      </div>

      <main className="workspace" id="main">
        {role === 'nl' && (
          <NlWorkspace
            onOpenedChart={() => setLocal((value) => ({ ...value, openedChart: true }))}
            onSearched={() => setLocal((value) => ({ ...value, searchedExperts: true }))}
            onChanged={refreshShared}
            onShowControlRoom={() => switchRole('control')}
          />
        )}
        {role === 'de' && <DeWorkspace onChanged={refreshShared} />}
        {role === 'control' && (
          <ControlRoom sites={sites.data} sitesError={sites.error} onChanged={refreshShared} />
        )}
        {role === 'research' && <ResearchView sites={sites.data} onChanged={refreshShared} />}
      </main>
      <footer className="footer">
        Synthetic demonstration. Real institution names are used for illustration only and imply no
        endorsement; all patients, clinicians, opinions and numbers are fictional.
      </footer>
    </div>
  )
}
