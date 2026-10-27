import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'

type Scenario = { id: string; name: string; description: string; evidence_id: string }
type Backup = { id: string; evidence_id: string; created_at: string; location_id: string; exists: boolean; freshness: string; integrity_status: string; usable: boolean; malware_status: string; restore_status: string; scenario_trust: string }
type Service = {
  id: string; name: string; status: string; dependencies: string[]; current_blockers: string[]; backup_existence: string; backup_count: number
  selected_backup_id: string | null; selected_backup_evidence_id: string | null; selected_backup_freshness: string; selected_backup_integrity: string
  selected_backup_location: string | null; selected_backup_malware_status: string; rpo_target_seconds: number; rpo_gap_seconds: number | null
  rto_target_seconds: number; estimated_restore_seconds: number; estimated_rto_gap_seconds: number; recovery_status: string
  recovery_blockers: { id: string; reason: string }[]; restore_test: { status: string; duration_seconds?: number; result?: Record<string, unknown> }; backups: Backup[]
}
type Assessment = {
  scenario: Scenario; observed_at: string; metrics: Record<string, number>; services: Service[]
  recovery_plan: { order: number; service_id: string; service: string; status: string; backup_id: string | null; evidence_id: string | null }[]
  evidence: { id: string; type: string; subject: string; detail: string }[]; assurance_notes: string[]
}
type Action = {
  id: string; scenario_id: string; service_id: string; backup_id: string; status: string; duration_seconds?: number
  result?: { status: string; duration_seconds?: number; checksum_match?: boolean; bytes_copied?: number; source_sha256?: string; restored_sha256?: string; malware_status?: string; fixture_health?: { status: string; record_count?: number; database_engine_tested?: boolean; detail?: string }; restored_file?: string }
}
type Assistant = { mode: string; summary: string; recommendations: { action_id: string; text: string }[]; uncertainties: string[]; evidence_ids: string[]; execution_authority: string }

const api = async <T,>(path: string, init?: RequestInit): Promise<T> => {
  const response = await fetch(path, { ...init, headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) } })
  if (!response.ok) {
    const detail = await response.json().catch(() => ({ detail: response.statusText }))
    throw new Error(detail.detail || 'Request failed')
  }
  return response.json() as Promise<T>
}

const hours = (seconds: number | null) => seconds === null ? '—' : `${(seconds / 3600).toFixed(1)}h`
const titleCase = (value: string) => value.replaceAll('_', ' ')

function Icon({ kind }: { kind: 'shield' | 'grid' | 'nodes' | 'file' | 'settings' | 'arrow' | 'download' | 'check' | 'clock' | 'alert' }) {
  const common = { width: 18, height: 18, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 1.8, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const }
  const paths: Record<string, ReactNode> = {
    shield: <><path d="M12 3 20 6v5c0 5-3.3 8.2-8 10-4.7-1.8-8-5-8-10V6l8-3Z"/><path d="m8.5 12 2.2 2.2 4.8-5"/></>,
    grid: <><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></>,
    nodes: <><circle cx="6" cy="6" r="2.5"/><circle cx="18" cy="6" r="2.5"/><circle cx="12" cy="18" r="2.5"/><path d="M8.3 7.3 10.8 16M15.7 7.3 13.2 16M8.5 6h7"/></>,
    file: <><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"/><path d="M14 2v6h6M8 13h8M8 17h8"/></>,
    settings: <><circle cx="12" cy="12" r="3"/><path d="m19.4 15 .1.1 1.2 1-1.4 2.4-1.5-.6a8 8 0 0 1-1.6.9l-.3 1.6h-2.8l-.3-1.6a8 8 0 0 1-1.6-.9l-1.5.6-1.4-2.4 1.2-1a8 8 0 0 1 0-1.9l-1.2-1 1.4-2.4 1.5.6a8 8 0 0 1 1.6-.9l.3-1.6h2.8l.3 1.6a8 8 0 0 1 1.6.9l1.5-.6 1.4 2.4-1.2 1a8 8 0 0 1 0 1.8Z" transform="translate(-2 -2)"/></>,
    arrow: <><path d="M5 12h14M13 6l6 6-6 6"/></>,
    download: <><path d="M12 3v12m-5-5 5 5 5-5"/><path d="M4 17v3h16v-3"/></>,
    check: <><path d="m5 12 4 4L19 6"/></>,
    clock: <><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></>,
    alert: <><path d="M12 3 2.8 19a1 1 0 0 0 .9 1.5h16.6a1 1 0 0 0 .9-1.5L12 3Z"/><path d="M12 9v4m0 3h.01"/></>,
  }
  return <svg {...common}>{paths[kind]}</svg>
}

function App() {
  const [scenarios, setScenarios] = useState<Scenario[]>([])
  const [scenarioId, setScenarioId] = useState('physical-disaster')
  const [assessment, setAssessment] = useState<Assessment | null>(null)
  const [actions, setActions] = useState<Action[]>([])
  const [selectedService, setSelectedService] = useState('clinical-db')
  const [selectedBackup, setSelectedBackup] = useState('')
  const [assistant, setAssistant] = useState<Assistant | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [apiReady, setApiReady] = useState(false)

  const refresh = useCallback(async (id = scenarioId) => {
    setBusy(true); setError('')
    try {
      const [s, a, h, ac] = await Promise.all([
        api<Scenario[]>('/api/scenarios'), api<Assessment>(`/api/assessment?scenario_id=${encodeURIComponent(id)}`),
        api<{ status: string }>('/api/health'), api<Action[]>('/api/actions'),
      ])
      setScenarios(s); setAssessment(a); setActions(ac); setApiReady(h.status === 'ok')
      const preferred = a.services.find((item) => item.id === selectedService) || a.services.find((item) => item.backup_count > 0)
      if (preferred) {
        setSelectedService(preferred.id)
        const backups = [...preferred.backups].sort((left, right) => Number(right.usable) - Number(left.usable) || right.created_at.localeCompare(left.created_at))
        setSelectedBackup(backups.find((item) => item.usable)?.id || backups[0]?.id || '')
      }
    } catch (err) { setError(err instanceof Error ? err.message : 'Could not reach the API'); setApiReady(false) }
    finally { setBusy(false) }
  }, [scenarioId, selectedService])

  useEffect(() => { void refresh(scenarioId) }, [scenarioId])

  const currentScenario = useMemo(() => scenarios.find((item) => item.id === scenarioId), [scenarios, scenarioId])
  const selectedServiceRow = assessment?.services.find((item) => item.id === selectedService)
  const selectedBackupRow = selectedServiceRow?.backups.find((item) => item.id === selectedBackup)
  const latestRestore = actions.find((item) => item.status === 'completed' && item.result?.duration_seconds !== undefined)
  const pendingAction = [...actions].reverse().find((item) => item.scenario_id === scenarioId && item.status === 'pending')
  const completedAction = [...actions].reverse().find((item) => item.scenario_id === scenarioId && item.status === 'completed')

  const setScenario = (value: string) => { setScenarioId(value); setAssistant(null) }
  const propose = async () => {
    if (!selectedBackupRow?.usable) return
    setBusy(true); setError('')
    try {
      await api<Action>('/api/actions', { method: 'POST', body: JSON.stringify({ scenario_id: scenarioId, service_id: selectedService, backup_id: selectedBackup }) })
      await refresh(scenarioId)
    } catch (err) { setError(err instanceof Error ? err.message : 'Could not create proposal') }
    finally { setBusy(false) }
  }
  const decide = async (decision: 'approve' | 'reject') => {
    if (!pendingAction) return
    setBusy(true); setError('')
    try {
      await api<Action>(`/api/actions/${pendingAction.id}/decision`, { method: 'POST', body: JSON.stringify({ decision, rationale: decision === 'approve' ? 'Approved for isolated synthetic fixture validation.' : 'Rejected by operator.' }) })
      await refresh(scenarioId)
    } catch (err) { setError(err instanceof Error ? err.message : 'Could not record decision') }
    finally { setBusy(false) }
  }
  const askAssistant = async () => {
    setBusy(true); setError('')
    try { setAssistant(await api<Assistant>('/api/assistant', { method: 'POST', body: JSON.stringify({ scenario_id: scenarioId, question: 'Summarize the blockers, recovery evidence, and safe next test.' }) })) }
    catch (err) { setError(err instanceof Error ? err.message : 'Assistant is unavailable') }
    finally { setBusy(false) }
  }

  const chooseService = (id: string) => {
    setSelectedService(id)
    const row = assessment?.services.find((item) => item.id === id)
    const sorted = [...(row?.backups || [])].sort((left, right) => Number(right.usable) - Number(left.usable) || right.created_at.localeCompare(left.created_at))
    setSelectedBackup(sorted.find((item) => item.usable)?.id || sorted[0]?.id || '')
  }

  if (!assessment) return <div className="loading-screen"><div className="loading-mark"><Icon kind="shield" /></div><strong>ResilienceGuard</strong><span>{error || 'Connecting to the local recovery service…'}</span><button className="button button-primary" onClick={() => void refresh(scenarioId)}>Retry connection</button></div>

  const { metrics, services, recovery_plan: plan } = assessment
  const restoreHistory = actions.filter((item) => item.scenario_id === scenarioId).slice(-5).reverse()

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-symbol"><Icon kind="shield" /></div><div><strong>ResilienceGuard</strong><small>RECOVERY ASSURANCE</small></div></div>
      <div className="workspace-label">WORKSPACE</div>
      <nav className="main-nav" aria-label="Main navigation">
        <a className="nav-item active" href="#overview"><Icon kind="grid" /><span>Overview</span></a>
        <a className="nav-item" href="#dependencies"><Icon kind="nodes" /><span>Dependency map</span></a>
        <a className="nav-item" href="#approvals"><Icon kind="check" /><span>Recovery approvals</span><span className="nav-count">{actions.filter((item) => item.status === 'pending').length}</span></a>
        <a className="nav-item" href="#evidence"><Icon kind="file" /><span>Evidence & reports</span></a>
      </nav>
      <div className="sidebar-spacer" />
      <div className="sidebar-note"><span className="tiny-dot" /> LOCAL SYNTHETIC ENVIRONMENT<p>Production systems are not connected.</p></div>
      <div className="profile"><div className="avatar">RG</div><div><strong>Recovery operator</strong><small>Local demo workspace</small></div><span className="profile-dots">•••</span></div>
    </aside>

    <main className="main-content" id="overview">
      <header className="topbar"><div className="breadcrumb">Resilience <span>/</span> Readiness overview</div><div className="topbar-right"><span className={`api-status ${apiReady ? 'ok' : 'down'}`}><i />{apiReady ? 'API connected' : 'API unavailable'}</span><button className="icon-button" aria-label="Refresh data" onClick={() => void refresh(scenarioId)}><span className={busy ? 'spin' : ''}>↻</span></button><div className="avatar small-avatar">RG</div></div></header>
      <div className="page-heading"><div><div className="eyebrow">RECOVERY READINESS / SYNTHETIC ENVIRONMENT</div><h1>Know what comes back.</h1><p>Evidence-led recovery status for critical services, backup copies and dependencies.</p></div><div className="heading-actions"><a className="button button-quiet" href={`/api/report.pdf?scenario_id=${encodeURIComponent(scenarioId)}`}><Icon kind="download" /> Export assessment</a><button className="button button-primary" onClick={() => document.getElementById('approvals')?.scrollIntoView({ behavior: 'smooth' })}>Review recovery plan <Icon kind="arrow" /></button></div></div>
      <div className="synthetic-banner"><span className="banner-icon"><Icon kind="alert" /></span><div><strong>Demo data only</strong><span>Hashes verify file integrity only. Malware scanning is not performed; malware status remains unknown.</span></div><span className="banner-seal"><Icon kind="shield" /> SANDBOXED</span></div>

      <section className="scenario-bar">
        <div className="scenario-icon"><Icon kind="nodes" /></div><div className="scenario-copy"><span>ACTIVE DISASTER SCENARIO</span><strong>{currentScenario?.name || assessment.scenario.name}</strong></div>
        <select aria-label="Select disaster scenario" value={scenarioId} onChange={(event) => setScenario(event.target.value)}>{scenarios.map((scenario) => <option key={scenario.id} value={scenario.id}>{scenario.name}</option>)}</select>
        <div className="scenario-description">{currentScenario?.description || assessment.scenario.description}</div>
        <button className="text-button" onClick={() => void refresh(scenarioId)} disabled={busy}>{busy ? 'Updating…' : 'Reassess'} <Icon kind="arrow" /></button>
      </section>

      <section className="metrics-grid" aria-label="Readiness summary">
        <Metric title="Critical services" value={`${metrics.service_count}`} subtitle="in synthetic catalog" icon="grid" tone="blue" />
        <Metric title="Ready to recover" value={`${metrics.ready_to_recover}`} subtitle={`${metrics.unavailable_services} currently unavailable`} icon="check" tone="green" />
        <Metric title="Recovery blockers" value={`${metrics.blocked_services}`} subtitle="missing dependency or candidate" icon="alert" tone="amber" />
        <Metric title="Integrity alerts" value={`${metrics.integrity_failures}`} subtitle={`${metrics.stale_usable_backups} usable copies stale`} icon="shield" tone="red" />
      </section>

      {error && <div className="inline-error"><Icon kind="alert" />{error}<button onClick={() => setError('')}>Dismiss</button></div>}

      <section className="content-grid">
        <div className="panel dependency-panel" id="dependencies">
          <div className="panel-header"><div><div className="eyebrow">DEPENDENCY ASSESSMENT</div><h2>Recovery sequence</h2><p>Prerequisites are evaluated before a service is marked recoverable.</p></div><span className="panel-tag"><Icon kind="nodes" /> VERIFIED GRAPH</span></div>
          <div className="sequence-list">
            {plan.map((item) => {
              const service = services.find((row) => row.id === item.service_id)!
              const blockers = service.recovery_blockers
              return <div className={`sequence-row ${item.status}`} key={item.service_id}>
                <div className="sequence-order">{String(item.order).padStart(2, '0')}</div><div className="sequence-rail"><div className="sequence-node"><span /></div>{item.order < Math.max(...plan.map((row) => row.order), 0) && <div className="sequence-line" />}</div>
                <div className="sequence-main"><div className="sequence-title"><strong>{item.service}</strong><span className={`status-pill ${item.status}`}>{item.status}</span></div><div className="sequence-meta">{service.dependencies.length ? <>Depends on {service.dependencies.map((dep) => services.find((row) => row.id === dep)?.name || dep).join(' · ')}</> : 'No upstream service dependency'}</div>
                  {blockers.length > 0 && <div className="blocker-list">{blockers.map((blocker) => <span className="blocker-chip" key={`${item.service_id}-${blocker.id}`}><Icon kind="alert" />{blocker.reason}</span>)}</div>}
                  {item.status === 'ready' && <div className="evidence-inline"><Icon kind="check" /> Candidate {item.backup_id} verified · {item.evidence_id}</div>}
                </div>
                <button className="row-arrow" aria-label={`Review ${item.service}`} onClick={() => { chooseService(item.service_id); document.getElementById('approvals')?.scrollIntoView({ behavior: 'smooth' }) }}><Icon kind="arrow" /></button>
              </div>
            })}
          </div>
          <div className="sequence-footnote"><span className="legend-dot green" /> Recovery ready <span className="legend-dot amber" /> Blocked by evidence or dependency <span className="footnote-evidence">Scenario evidence: {assessment.scenario.evidence_id}</span></div>
        </div>

        <div className="panel signals-panel" id="evidence">
          <div className="panel-header compact"><div><div className="eyebrow">BACKUP ASSURANCE</div><h2>Evidence signals</h2></div><a href={`/api/report.pdf?scenario_id=${encodeURIComponent(scenarioId)}`} className="small-link">Full report <Icon kind="arrow" /></a></div>
          <div className="signal-summary"><div className="signal-ring"><div><strong>{metrics.backup_count}</strong><span>copies</span></div></div><div className="signal-copy"><strong>Inventory coverage</strong><span>Backup records observed across configured locations</span><div className="coverage-track"><i style={{ width: `${Math.max(8, Math.round((metrics.backup_count / Math.max(1, services.length * 2)) * 100))}%` }} /></div><small>{metrics.missing_backup_services} service without backup metadata</small></div></div>
          <div className="signal-rows"><Signal label="SHA-256 verification" value={`${metrics.integrity_failures} failed`} tone={metrics.integrity_failures ? 'red' : 'green'} detail="Digest comparison performed" /><Signal label="Backup freshness" value={`${metrics.stale_usable_backups} stale`} tone={metrics.stale_usable_backups ? 'amber' : 'green'} detail="Compared with configured RPO" /><Signal label="Malware scan" value="Not performed" tone="muted" detail="Cleanliness is unknown" /></div>
          <div className="evidence-note"><Icon kind="alert" /><span>Integrity checks show changes against the fixture manifest. They do not prove that a matching copy is malware-free.</span></div>
          <div className="panel-divider" />
          <div className="panel-subhead"><strong>RPO / RTO outlook</strong><span>configured targets</span></div>
          {services.filter((row) => row.status === 'unavailable').slice(0, 3).map((service) => <div className="rpo-row" key={service.id}><span>{service.name}</span><div><b>RPO gap</b><strong className={service.rpo_gap_seconds ? 'warn-text' : ''}>{service.rpo_gap_seconds === null ? 'No candidate' : service.rpo_gap_seconds ? `${hours(service.rpo_gap_seconds)} over` : 'On target'}</strong></div><div><b>RTO gap</b><strong className={service.estimated_rto_gap_seconds ? 'warn-text' : ''}>{service.estimated_rto_gap_seconds ? `${Math.ceil(service.estimated_rto_gap_seconds / 60)}m est.` : 'Within est.'}</strong></div></div>)}
          <div className="estimate-note">RTO uses configured estimates until a restore test records an observed duration.</div>
        </div>
      </section>

      <section className="lower-grid">
        <div className="panel approvals-panel" id="approvals">
          <div className="panel-header"><div><div className="eyebrow">HUMAN DECISION REQUIRED</div><h2>Sandbox recovery approval</h2><p>Choose a synthetic backup, review the evidence, then approve or reject the isolated copy test.</p></div><span className="approval-lock"><Icon kind="shield" /> NO PRODUCTION ACTIONS</span></div>
          <div className="approval-form">
            <label>Service<select value={selectedService} onChange={(event) => chooseService(event.target.value)}>{services.map((service) => <option key={service.id} value={service.id}>{service.name}</option>)}</select></label>
            <label>Backup candidate<select value={selectedBackup} onChange={(event) => setSelectedBackup(event.target.value)}>{selectedServiceRow?.backups.map((backup) => <option key={backup.id} value={backup.id} disabled={!backup.usable}>{backup.id} — {titleCase(backup.freshness)}, {titleCase(backup.integrity_status)}{backup.scenario_trust === 'untrusted' ? ', untrusted' : ''}</option>)}</select></label>
            <button className="button button-primary propose-button" onClick={() => void propose()} disabled={busy || !selectedBackupRow?.usable || !selectedBackup}><span>Prepare proposal</span><Icon kind="arrow" /></button>
          </div>
          {selectedBackupRow ? <div className={`candidate-summary ${selectedBackupRow.usable ? 'usable' : 'blocked'}`}><div className="candidate-icon"><Icon kind={selectedBackupRow.usable ? 'check' : 'alert'} /></div><div className="candidate-copy"><strong>{selectedBackupRow.usable ? 'Candidate can be tested in the isolated fixture runner' : 'This candidate is not eligible for a restore proposal'}</strong><span>{selectedBackupRow.evidence_id} · {selectedBackupRow.location_id} · {new Date(selectedBackupRow.created_at).toLocaleString()} · malware status: unknown</span></div><div className="candidate-state">{selectedBackupRow.usable ? 'VERIFIED' : 'BLOCKED'}</div></div> : <div className="candidate-summary blocked"><div className="candidate-icon"><Icon kind="alert" /></div><div className="candidate-copy"><strong>No backup records exist for this service.</strong><span>Recovery cannot be proposed without an inventoried sample.</span></div><div className="candidate-state">MISSING</div></div>}
          {pendingAction && <div className="decision-card"><div className="decision-head"><div className="decision-icon"><Icon kind="clock" /></div><div><strong>Action awaiting your decision</strong><span>Restore {pendingAction.backup_id} into the isolated test directory</span></div><span className="status-pill pending">pending</span></div><div className="decision-disclaimer">Approval authorizes only a file copy of the synthetic fixture into the sandbox output path. No production credentials or connectors are configured.</div><div className="decision-buttons"><button className="button button-danger-quiet" disabled={busy} onClick={() => void decide('reject')}>Reject proposal</button><button className="button button-primary" disabled={busy} onClick={() => void decide('approve')}><Icon kind="check" /> Approve sandbox restore</button></div></div>}
          {completedAction?.result && <div className="restore-result"><div className="restore-result-head"><div className="success-badge"><Icon kind="check" /></div><div><strong>Sandbox restore {completedAction.result.status}</strong><span>Measured file copy and verification · {completedAction.result.duration_seconds?.toFixed(4)} seconds</span></div><a className="button button-quiet button-small" href={`/api/actions/${completedAction.id}/download`}><Icon kind="download" /> Download restored file</a></div><div className="restore-checks"><span><Icon kind="check" /> SHA-256 match</span><span><Icon kind="check" /> Fixture structure {completedAction.result.fixture_health?.status}</span><span><Icon kind="alert" /> Malware unknown</span><span><Icon kind="clock" /> {completedAction.result.bytes_copied} bytes copied</span></div><div className="restore-hash"><span>RESTORED SHA-256</span><code>{completedAction.result.restored_sha256}</code></div><p className="restore-limit">This checks a synthetic JSON snapshot only; no live database engine or application was started.</p></div>}
          {restoreHistory.length > 0 && !completedAction && <div className="action-history">{restoreHistory.map((action) => <div key={action.id}><span className={`history-mark ${action.status}`} /><strong>{action.service_id}</strong><span>{action.status}</span><small>{action.backup_id}</small></div>)}</div>}
        </div>

        <div className="panel assistant-panel">
          <div className="panel-header compact"><div><div className="eyebrow">GOVERNED AI ASSISTANT</div><h2>Recovery brief</h2></div><span className="ai-orb">AI</span></div>
          <p className="assistant-intro">Ask for an evidence-backed summary of this scenario. Deterministic checks remain authoritative.</p>
          <button className="assistant-prompt" onClick={() => void askAssistant()} disabled={busy}><span className="prompt-icon">✦</span><span>Summarize the blockers and safest next test</span><Icon kind="arrow" /></button>
          {assistant ? <div className="assistant-answer"><div className="answer-mode"><span className="tiny-dot" />{assistant.mode === 'local_llm_advisory' ? 'LOCAL MODEL · ADVISORY' : 'RULE-BASED FALLBACK'}<span className="answer-grounded">{assistant.evidence_ids.length} evidence refs</span></div><p>{assistant.summary}</p>{assistant.recommendations.map((item) => <div className="recommendation" key={item.action_id}><span className="recommendation-arrow"><Icon kind="arrow" /></span><span>{item.text}</span></div>)}<div className="uncertainty-box"><strong>Uncertainties</strong>{assistant.uncertainties.slice(0, 2).map((line) => <span key={line}>• {line}</span>)}</div><small className="no-authority">Execution authority: none · approval stays with the operator</small></div> : <div className="assistant-placeholder"><div className="assistant-mini-graphic"><div className="mini-ring" /><span>RG</span><i /><i /><i /></div><p>Assistant summaries include evidence references and known uncertainties. If the local model is unavailable, the deterministic fallback responds.</p></div>}
          <div className="assistant-foot"><span><Icon kind="shield" /> ADVISORY ONLY</span><span>Optional Ollama / Qwen3</span></div>
        </div>
      </section>

      <footer className="page-footer"><span>ResilienceGuard · Prototype build 0.1.0</span><span>Assessment time {new Date(assessment.observed_at).toLocaleString()} · Synthetic test data</span><a href="/api/report.pdf?scenario_id=physical-disaster">Sample evidence report</a></footer>
    </main>
  </div>
}

function Metric({ title, value, subtitle, icon, tone }: { title: string; value: string; subtitle: string; icon: 'grid' | 'check' | 'alert' | 'shield'; tone: string }) {
  return <div className="metric-card"><div className={`metric-icon ${tone}`}><Icon kind={icon} /></div><div className="metric-label">{title}</div><div className="metric-value">{value}</div><div className="metric-subtitle">{subtitle}</div><div className={`metric-accent ${tone}`} /></div>
}

function Signal({ label, value, tone, detail }: { label: string; value: string; tone: string; detail: string }) {
  return <div className="signal-row"><div className={`signal-dot ${tone}`} /><div className="signal-text"><strong>{label}</strong><small>{detail}</small></div><span className={`signal-value ${tone}`}>{value}</span></div>
}

export default App
