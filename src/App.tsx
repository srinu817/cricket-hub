import { FormEvent, useEffect, useMemo, useState } from 'react'
import { Link, NavLink, Route, Routes, useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import {
  CalendarDays, ChevronDown, ChevronRight, CircleUserRound, LayoutDashboard,
  LogOut, Menu, Search, ShieldCheck, Trophy, X
} from 'lucide-react'

type Status = 'Upcoming' | 'Completed'
type BattingRow = { player: string; dismissal: string; runs: number; balls: number; fours: number; sixes: number }
type BowlingRow = { player: string; overs: string; maidens: number; runs: number; wickets: number }
type Innings = { teamCode: string; total: string; overs: string; batting: BattingRow[]; bowling: BowlingRow[] }
type Match = {
  id: string; series: string; stage: string; status: Status; team1: string; team1Code: string
  team2: string; team2Code: string; date: string; time: string; venue: string; format: string
  result: string; toss: string; innings: Innings[]; commentary: string[]
}

const emptyScore = (teamCode: string): Innings => ({ teamCode, total: '', overs: '', batting: [], bowling: [] })
const api = async <T,>(url: string, init?: RequestInit): Promise<T> => {
  const response = await fetch(url, { ...init, headers: { 'content-type': 'application/json', ...init?.headers } })
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    const detail = typeof body.detail === 'string'
      ? body.detail
      : Array.isArray(body.detail)
        ? body.detail.map((item: { msg?: string }) => item.msg).filter(Boolean).join('; ')
        : undefined
    throw new Error(body.error || detail || `Request failed (${response.status})`)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}
const today = () => {
  const date = new Date()
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}
const formatDate = (date: string) => date ? new Date(`${date}T12:00:00`).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' }) : 'Date not set'
const ordinal = (index: number) => {
  const number = index + 1
  const suffix = number % 100 >= 11 && number % 100 <= 13 ? 'th' : ({ 1: 'st', 2: 'nd', 3: 'rd' } as Record<number, string>)[number % 10] || 'th'
  return `${number}${suffix}`
}

function TeamBadge({ code, small = false }: { code: string; small?: boolean }) {
  return <span className={small ? 'badge small' : 'badge'}>{(code || '?').slice(0, 3).toUpperCase()}</span>
}

function Header() {
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')
  const navigate = useNavigate()
  const location = useLocation()
  const submit = (event: FormEvent) => {
    event.preventDefault()
    if (search.trim()) navigate(`/matches?q=${encodeURIComponent(search.trim())}`)
  }
  useEffect(() => setOpen(false), [location.pathname])
  return <header className="header"><div className="header-inner">
    <Link className="brand" to="/" aria-label="Cricket Hub home"><span className="brand-mark"><Trophy size={19}/></span><span>CRICKET <b>HUB</b></span></Link>
    <nav className={open ? 'nav open' : 'nav'} aria-label="Primary navigation">
      <NavLink to="/" end>Home</NavLink><NavLink to="/matches">Matches</NavLink><NavLink to="/series">Series</NavLink>
      <NavLink to="/teams">Teams</NavLink><NavLink to="/players">Players</NavLink><NavLink to="/stats">Stats</NavLink>
    </nav>
    <div className="header-actions">
      <form className="search" onSubmit={submit}><Search size={16}/><input value={search} onChange={event => setSearch(event.target.value)} placeholder="Search matches" aria-label="Search matches"/></form>
      <Link className="admin-link" to="/admin" title="Admin login"><CircleUserRound size={19}/></Link>
      <button className="menu-button" onClick={() => setOpen(value => !value)} aria-label="Toggle menu">{open ? <X/> : <Menu/>}</button>
    </div>
  </div></header>
}

function MatchCard({ match }: { match: Match }) {
  const firstInnings = match.innings.find(innings => innings.teamCode === match.team1Code)
  const secondInnings = match.innings.find(innings => innings.teamCode === match.team2Code)
  return <Link className="match-card" to={`/matches/${match.id}`}>
    <div className="match-top"><span>{match.series} · {match.stage}</span><span className={`status ${match.status.toLowerCase()}`}>{match.status}</span></div>
    <div className="match-teams">
      <div className="team-row"><TeamBadge code={match.team1Code} small/><strong>{match.team1}</strong><b>{firstInnings?.total || '—'}</b></div>
      <div className="team-row"><TeamBadge code={match.team2Code} small/><strong>{match.team2}</strong><b>{secondInnings?.total || '—'}</b></div>
    </div>
    {match.status === 'Completed' ? <div className="match-result">{match.result || 'Result not entered'}</div> :
      <div className="match-meta"><CalendarDays size={14}/><span>{formatDate(match.date)}, {match.time}</span><span className="dot">•</span><span>{match.format}</span></div>}
  </Link>
}

function EmptyState({ title, message }: { title: string; message: string }) {
  return <div className="empty-state"><ShieldCheck size={28}/><h3>{title}</h3><p>{message}</p></div>
}

function Home({ matches, loading, error }: { matches: Match[]; loading: boolean; error: string }) {
  const todayMatches = matches.filter(match => match.date === today())
  const upcoming = matches.filter(match => match.status === 'Upcoming').sort((a, b) => a.date.localeCompare(b.date))
  const completed = matches.filter(match => match.status === 'Completed').sort((a, b) => b.date.localeCompare(a.date))
  return <main>
    <section className="hero"><div className="hero-content"><div><span className="eyebrow">MATCH CENTRE</span><h1>Cricket, at a glance.</h1><p>Match schedules, results and scorecards entered by Cricket Hub administrators.</p></div>
      <div className="date-picker"><div><b>Today</b><span>{formatDate(today())}</span></div></div></div></section>
    <div className="content">
      {error && <div className="error-banner" role="alert">{error}</div>}
      <section className="section"><div className="section-heading"><div><span className="eyebrow">FIXTURES</span><h2>Today’s matches</h2></div><Link to="/matches">All matches <ChevronRight size={16}/></Link></div>
        {loading ? <div className="loading-state">Loading matches…</div> : todayMatches.length ? <div className="match-grid">{todayMatches.map(match => <MatchCard key={match.id} match={match}/>)}</div> :
          <div className="empty-inline">No matches listed for today.</div>}
      </section>
      <div className="home-columns">
        <section className="section"><div className="section-heading"><div><span className="eyebrow">SCHEDULE</span><h2>Upcoming matches</h2></div><Link to="/matches?status=Upcoming">View all <ChevronRight size={16}/></Link></div>
          {upcoming.length ? <div className="fixture-list">{upcoming.slice(0, 5).map(match => <Link className="fixture-row" key={match.id} to={`/matches/${match.id}`}>
            <div className="fixture-date"><b>{new Date(`${match.date}T12:00:00`).getDate()}</b><span>{new Date(`${match.date}T12:00:00`).toLocaleString(undefined, { month: 'short' })}</span></div>
            <div className="fixture-series"><span>{match.series}</span><strong>{match.team1Code} vs {match.team2Code}</strong></div>
            <div className="fixture-venue"><span>{match.venue}</span><b>{match.time}</b></div><ChevronRight size={18}/></Link>)}</div> :
            <div className="empty-inline">No upcoming matches have been added.</div>}
        </section>
        <aside className="rankings-card"><div className="ranking-head"><div><span className="eyebrow">ADMIN-ENTERED DATA</span><h3>Recent results</h3></div><Link to="/matches?status=Completed">View all</Link></div>
          {completed.length ? completed.slice(0, 3).map(match => <Link className="recent-result" key={match.id} to={`/matches/${match.id}`}><strong>{match.team1Code} <span>vs</span> {match.team2Code}</strong><small>{match.result || match.stage}</small></Link>) :
            <p className="muted-copy">Completed results will appear here after an admin adds them.</p>}
        </aside>
      </div>
      <section className="section"><div className="section-heading"><div><span className="eyebrow">FINISHED</span><h2>Recent results</h2></div></div>
        {completed.length ? <div className="match-grid">{completed.slice(0, 3).map(match => <MatchCard key={match.id} match={match}/>)}</div> : <div className="empty-inline">No completed matches have been added yet.</div>}
      </section>
    </div>
  </main>
}

function MatchesPage({ matches }: { matches: Match[] }) {
  const [params, setParams] = useSearchParams()
  const [query, setQuery] = useState(params.get('q') || '')
  const status = params.get('status') || 'All'
  const format = params.get('format') || 'All'
  const date = params.get('date') || ''
  useEffect(() => setQuery(params.get('q') || ''), [params])
  const filtered = matches.filter(match =>
    (status === 'All' || match.status === status) &&
    (format === 'All' || match.format === format) &&
    (!date || match.date === date) &&
    `${match.team1} ${match.team2} ${match.series} ${match.team1Code} ${match.team2Code}`.toLowerCase().includes(query.toLowerCase())
  )
  const setFilter = (key: string, value: string) => setParams(current => {
    const next = new URLSearchParams(current)
    if (value === 'All' || !value) next.delete(key)
    else next.set(key, value)
    return next
  })
  return <main className="page"><div className="page-title"><span className="eyebrow">MATCH CENTRE</span><h1>Matches</h1></div>
    <div className="filter-bar"><div className="tabs">{['All', 'Upcoming', 'Completed'].map(item => <button key={item} className={status === item ? 'active' : ''} onClick={() => setFilter('status', item)}>{item}</button>)}</div>
      <label className="inline-search"><Search size={15}/><input value={query} onChange={event => setQuery(event.target.value)} placeholder="Search team or series"/></label>
      <label className="date-filter"><span className="visually-hidden">Match date</span><input aria-label="Match date" type="date" value={date} onChange={event => setFilter('date', event.target.value)}/></label>
      <label className="select-filter"><span className="visually-hidden">Format</span><select value={format} onChange={event => setFilter('format', event.target.value)}><option value="All">All formats</option>{[...new Set(matches.map(match => match.format))].sort().map(item => <option key={item}>{item}</option>)}</select><ChevronDown size={15}/></label>
    </div>
    {filtered.length ? <div className="match-grid page-grid">{filtered.map(match => <MatchCard key={match.id} match={match}/>)}</div> :
      <EmptyState title="No matches found" message="Try a different search or filter. Admins can add matches from the admin area."/ >}
  </main>
}

function parseBattingRows(value: string): BattingRow[] {
  return value.split('\n').map(line => line.trim()).filter(Boolean).map(line => {
    const [player = '', dismissal = '', runs = '', balls = '', fours = '', sixes = ''] = line.split('|').map(part => part.trim())
    const values = [runs, balls, fours, sixes]
    if (!player || !dismissal || values.some(value => !/^\d+$/.test(value))) throw new Error('Batting rows need a player, dismissal, and non-negative whole-number figures.')
    return { player, dismissal, runs: Number(runs), balls: Number(balls), fours: Number(fours), sixes: Number(sixes) }
  })
}
function parseBowlingRows(value: string): BowlingRow[] {
  return value.split('\n').map(line => line.trim()).filter(Boolean).map(line => {
    const [player = '', overs = '', maidens = '', runs = '', wickets = ''] = line.split('|').map(part => part.trim())
    if (!player || !/^\d+(\.\d)?$/.test(overs) || [maidens, runs, wickets].some(value => !/^\d+$/.test(value))) throw new Error('Bowling rows need a player, valid overs, and non-negative whole-number figures.')
    return { player, overs, maidens: Number(maidens), runs: Number(runs), wickets: Number(wickets) }
  })
}

function MatchDetail({ matches }: { matches: Match[] }) {
  const { id = '' } = useParams()
  const match = matches.find(item => item.id === id)
  const [tab, setTab] = useState('Overview')
  if (!match) return <main className="page"><EmptyState title="Match not found" message="This match may have been removed or its link may be incorrect."/></main>
  const tabs = ['Overview', 'Scorecard', 'Commentary', 'Statistics', 'Playing XI', 'Squads']
  return <main className="detail-page">
    <div className="match-banner"><div className="breadcrumb"><Link to="/matches">Matches</Link><ChevronRight size={13}/>{match.series}</div>
      <div className="banner-series"><span>{match.series}</span><b>{match.stage}</b></div>
      <div className="banner-teams"><div className="banner-team"><TeamBadge code={match.team1Code}/><b>{match.team1}</b></div>
        <div className="banner-score"><b>{match.innings.find(i => i.teamCode === match.team1Code)?.total || '—'}</b><span>{match.status === 'Completed' ? match.result || 'Completed' : `${formatDate(match.date)} · ${match.time}`}</span><b>{match.innings.find(i => i.teamCode === match.team2Code)?.total || '—'}</b></div>
        <div className="banner-team right"><b>{match.team2}</b><TeamBadge code={match.team2Code}/></div></div>
      <div className="banner-meta">{match.venue} · {formatDate(match.date)} · {match.format}</div>
    </div>
    <div className="detail-tabs">{tabs.map(item => <button key={item} onClick={() => setTab(item)} className={tab === item ? 'active' : ''}>{item}</button>)}</div>
    <div className="detail-content">
      {tab === 'Overview' && <div className="overview-grid"><section className="info-card"><h3>Match information</h3><dl><div><dt>Series</dt><dd>{match.series}</dd></div><div><dt>Match</dt><dd>{match.stage}</dd></div><div><dt>Format</dt><dd>{match.format}</dd></div><div><dt>Date</dt><dd>{formatDate(match.date)} · {match.time}</dd></div><div><dt>Venue</dt><dd>{match.venue}</dd></div><div><dt>Toss</dt><dd>{match.toss || 'Not entered'}</dd></div><div><dt>Status</dt><dd>{match.status}</dd></div></dl></section>
        <section className="info-card"><h3>Match summary</h3><p>{match.result || 'Result has not been entered.'}</p>{match.innings.map((innings, index) => <p key={`${innings.teamCode}-${index}`}><b>{innings.teamCode}</b> {innings.total || '—'}{innings.overs ? ` (${innings.overs} overs)` : ''}</p>)}</section></div>}
      {tab === 'Scorecard' && (match.innings.length ? <div className="innings-stack">{match.innings.map((innings, index) => <section className="scorecard" key={`${innings.teamCode}-${index}`}>
        <div className="innings-head"><div><TeamBadge code={innings.teamCode} small/><b>{innings.teamCode} · {ordinal(index)} innings</b></div><strong>{innings.total} {innings.overs && `(${innings.overs})`}</strong></div>
        {innings.batting.length ? <div className="table-wrap"><table><thead><tr><th>Batter</th><th>Dismissal</th><th>R</th><th>B</th><th>4s</th><th>6s</th><th>SR</th></tr></thead><tbody>{innings.batting.map((row, i) => <tr key={`${row.player}-${i}`}><td>{row.player}</td><td>{row.dismissal}</td><td>{row.runs}</td><td>{row.balls}</td><td>{row.fours}</td><td>{row.sixes}</td><td>{row.balls ? (row.runs * 100 / row.balls).toFixed(2) : '—'}</td></tr>)}</tbody></table></div> : <p className="empty-inline">Batting figures are not available.</p>}
        {innings.bowling.length > 0 && <div className="table-wrap"><table><thead><tr><th>Bowler</th><th>Overs</th><th>M</th><th>R</th><th>W</th></tr></thead><tbody>{innings.bowling.map((row, i) => <tr key={`${row.player}-${i}`}><td>{row.player}</td><td>{row.overs}</td><td>{row.maidens}</td><td>{row.runs}</td><td>{row.wickets}</td></tr>)}</tbody></table></div>}
      </section>)}</div> : <EmptyState title="Scorecard not added" message="An administrator can add innings and scorecard details in the admin area."/>)}
      {tab === 'Commentary' && (match.commentary.length ? <div className="info-card commentary-list">{match.commentary.map((line, index) => <p key={index}>{line}</p>)}</div> : <EmptyState title="Commentary unavailable" message="No commentary has been entered for this match."/>)}
      {['Statistics', 'Playing XI', 'Squads'].includes(tab) && <EmptyState title={`${tab} unavailable`} message="These details have not been entered for this match."/ >}
    </div>
  </main>
}

function Admin({ matches, onRefresh }: { matches: Match[]; onRefresh: () => Promise<void> }) {
  const [authenticated, setAuthenticated] = useState<boolean | null>(null)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [editing, setEditing] = useState<Match | null>(null)
  const [notice, setNotice] = useState('')

  useEffect(() => { api('/api/v1/auth/session').then(() => setAuthenticated(true)).catch(() => setAuthenticated(false)) }, [])
  const login = async (event: FormEvent) => {
    event.preventDefault(); setError(''); setBusy(true)
    try { await api('/api/v1/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) }); setAuthenticated(true) }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Sign-in failed') }
    finally { setBusy(false) }
  }
  const logout = async () => {
    try { await api('/api/v1/auth/logout', { method: 'POST', body: '{}' }); setAuthenticated(false); setEditing(null) }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Sign-out failed') }
  }
  const remove = async (match: Match) => {
    if (!window.confirm(`Delete ${match.stage}: ${match.team1} vs ${match.team2}?`)) return
    try { await api(`/api/v1/matches/${match.id}`, { method: 'DELETE' }); await onRefresh(); setNotice('Match deleted.') }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not delete match') }
  }
  if (authenticated === null) return <main className="login-page"><p>Checking admin session…</p></main>
  if (!authenticated) return <main className="login-page"><form className="login-card" onSubmit={login}>
    <div className="login-mark"><ShieldCheck size={24}/></div><span className="eyebrow">ADMINISTRATION</span><h1>Admin sign in</h1>
    <p className="muted-copy">Sign in with the credentials configured on the server.</p>
    {error && <p className="form-error" role="alert">{error}</p>}
    <label>Email<input type="email" autoComplete="username" required value={email} onChange={event => setEmail(event.target.value)} placeholder="Admin email"/></label>
    <label>Password<input type="password" autoComplete="current-password" required value={password} onChange={event => setPassword(event.target.value)} placeholder="Password"/></label>
    <button className="primary-button" type="submit" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}</button>
  </form></main>
  return <main className="admin-page"><aside className="admin-side"><div className="admin-brand"><ShieldCheck size={20}/><b>Cricket Hub Admin</b></div><button className="active"><LayoutDashboard size={17}/> Match management</button><button onClick={logout}><LogOut size={17}/> Sign out</button></aside>
    <section className="admin-main"><div className="admin-title"><div><span className="eyebrow">ADMINISTRATION</span><h1>Match management</h1><p className="muted-copy">Changes are saved on this server and shown on public pages.</p></div><button className="primary-button" onClick={() => { setError(''); setEditing(newMatch()) }}>+ Add match</button></div>
      {error && <div className="error-banner" role="alert">{error}</div>}{notice && <div className="notice" role="status">{notice}</div>}
      {editing && <MatchForm match={editing} onCancel={() => setEditing(null)} onSave={async match => {
        setBusy(true); setError(''); setNotice('')
        try {
          const exists = matches.some(item => item.id === match.id)
          await api(exists ? `/api/v1/matches/${match.id}` : '/api/v1/matches', { method: exists ? 'PUT' : 'POST', body: JSON.stringify(match) })
          await onRefresh(); setEditing(null); setNotice(exists ? 'Match changes saved.' : 'Match added.')
        } catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not save match') }
        finally { setBusy(false) }
      }} busy={busy}/>}
      <div className="admin-table"><div className="admin-table-head"><b>Match</b><b>Status</b><b>Actions</b></div>
        {matches.length ? matches.map(match => <div className="admin-table-row" key={match.id}><div><TeamBadge code={match.team1Code} small/><b>{match.team1Code}</b><span>vs</span><b>{match.team2Code}</b><small>{match.stage} · {formatDate(match.date)}</small></div><span className={`status ${match.status.toLowerCase()}`}>{match.status}</span><div className="row-actions"><button onClick={() => { setError(''); setEditing(match) }}>Edit</button><button className="danger-button" onClick={() => void remove(match)}>Delete</button></div></div>) : <div className="empty-inline">No matches yet. Use “Add match” to publish the first one.</div>}
      </div>
    </section>
  </main>
}

function newMatch(): Match {
  return { id: '', series: '', stage: '', status: 'Upcoming', team1: '', team1Code: '', team2: '', team2Code: '', date: today(), time: '', venue: '', format: 'ODI', result: '', toss: '', innings: [], commentary: [] }
}
function MatchForm({ match, onCancel, onSave, busy }: { match: Match; onCancel: () => void; onSave: (match: Match) => Promise<void>; busy: boolean }) {
  const [form, setForm] = useState<Match>(() => structuredClone(match))
  const [batting, setBatting] = useState(() => [0, 1, 2, 3].map(index => (match.innings[index]?.batting || []).map(row => `${row.player} | ${row.dismissal} | ${row.runs} | ${row.balls} | ${row.fours} | ${row.sixes}`).join('\n')))
  const [bowling, setBowling] = useState(() => [0, 1, 2, 3].map(index => (match.innings[index]?.bowling || []).map(row => `${row.player} | ${row.overs} | ${row.maidens} | ${row.runs} | ${row.wickets}`).join('\n')))
  const [formError, setFormError] = useState('')
  const set = (key: keyof Match, value: string) => setForm(current => ({ ...current, [key]: value }))
  const save = (event: FormEvent) => {
    event.preventDefault()
    setFormError('')
    try {
      const inningsCount = form.format.toLowerCase().includes('test') ? 4 : 2
      const innings = form.status === 'Upcoming' ? [] : Array.from({ length: inningsCount }, (_, index) => ({
        teamCode: index % 2 === 0 ? form.team1Code : form.team2Code,
        total: form.innings[index]?.total || '', overs: form.innings[index]?.overs || '',
        batting: parseBattingRows(batting[index] || ''), bowling: parseBowlingRows(bowling[index] || ''),
      })).filter(item => item.total || item.batting.length || item.bowling.length)
      void onSave({ ...form, innings, commentary: form.commentary.filter(line => line.trim()) })
    } catch (cause) {
      setFormError(cause instanceof Error ? cause.message : 'Scorecard entries are invalid.')
    }
  }
  const inningsCount = form.format.toLowerCase().includes('test') ? 4 : 2
  const inningsCodes = Array.from({ length: inningsCount }, (_, index) => index % 2 === 0 ? form.team1Code || 'TEAM 1' : form.team2Code || 'TEAM 2')
  return <form className="match-form" onSubmit={save}>
    <div className="form-heading"><div><h2>{match.id ? 'Edit match' : 'Add match'}</h2><p>Only saved information is published. Do not enter unverified scores.</p></div><button type="button" className="icon-close" onClick={onCancel} aria-label="Close form"><X size={19}/></button></div>
    {formError && <p className="form-error" role="alert">{formError}</p>}
    <div className="form-grid">
      <label>Series<input required maxLength={160} value={form.series} onChange={e => set('series', e.target.value)}/></label>
      <label>Match / stage<input required maxLength={160} value={form.stage} onChange={e => set('stage', e.target.value)} placeholder="e.g. 1st ODI"/></label>
      <label>Status<select value={form.status} onChange={e => set('status', e.target.value)}><option>Upcoming</option><option>Completed</option></select></label>
      <label>Format<input required maxLength={40} value={form.format} onChange={e => set('format', e.target.value)} placeholder="ODI, Test, T20I…"/></label>
      <label>Team 1<input required maxLength={100} value={form.team1} onChange={e => set('team1', e.target.value)}/></label>
      <label>Team 1 code<input required maxLength={10} value={form.team1Code} onChange={e => set('team1Code', e.target.value.toUpperCase())}/></label>
      <label>Team 2<input required maxLength={100} value={form.team2} onChange={e => set('team2', e.target.value)}/></label>
      <label>Team 2 code<input required maxLength={10} value={form.team2Code} onChange={e => set('team2Code', e.target.value.toUpperCase())}/></label>
      <label>Date<input required type="date" value={form.date} onChange={e => set('date', e.target.value)}/></label>
      <label>Start time<input required value={form.time} onChange={e => set('time', e.target.value)} placeholder="Local venue time"/></label>
      <label className="wide-field">Venue<input required maxLength={160} value={form.venue} onChange={e => set('venue', e.target.value)}/></label>
      <label className="wide-field">Toss details<input value={form.toss} onChange={e => set('toss', e.target.value)} placeholder="Optional"/></label>
      {form.status === 'Completed' && <label className="wide-field">Result<input value={form.result} onChange={e => set('result', e.target.value)} placeholder="Optional result text"/></label>}
    </div>
    {form.status === 'Completed' && <div className="score-input-section"><h3>Scorecard (optional)</h3><p>One batter/bowler per line. Use the field order shown in the hints.</p>
      {inningsCodes.map((code, index) => <fieldset className="innings-editor" key={index}><legend>{code} innings {index + 1}</legend>
        <div className="form-grid"><label>Total<input value={form.innings[index]?.total || ''} onChange={e => setForm(current => { const innings = [...current.innings]; innings[index] = { ...emptyScore(index === 0 ? current.team1Code : current.team2Code), ...innings[index], teamCode: index === 0 ? current.team1Code : current.team2Code, total: e.target.value }; return { ...current, innings } })} placeholder="e.g. 245/7"/></label>
        <label>Overs<input value={form.innings[index]?.overs || ''} onChange={e => setForm(current => { const innings = [...current.innings]; innings[index] = { ...emptyScore(index === 0 ? current.team1Code : current.team2Code), ...innings[index], teamCode: index === 0 ? current.team1Code : current.team2Code, overs: e.target.value }; return { ...current, innings } })} placeholder="e.g. 50"/></label></div>
        <label>Batting entries<textarea value={batting[index] || ''} onChange={e => setBatting(current => current.map((value, i) => i === index ? e.target.value : value))} placeholder={'Player | dismissal | runs | balls | fours | sixes'}/></label>
        <label>Bowling entries<textarea value={bowling[index] || ''} onChange={e => setBowling(current => current.map((value, i) => i === index ? e.target.value : value))} placeholder={'Bowler | overs | maidens | runs | wickets'}/></label>
      </fieldset>)}
      <label className="wide-field">Commentary (optional, one entry per line)<textarea value={form.commentary.join('\n')} onChange={e => setForm(current => ({ ...current, commentary: e.target.value.split('\n') }))}/></label>
    </div>}
    <div className="form-actions"><button className="secondary-button" type="button" onClick={onCancel}>Cancel</button><button className="primary-button" disabled={busy}>{busy ? 'Saving…' : 'Save match'}</button></div>
  </form>
}

function ListingPage({ title, matches }: { title: string; matches: Match[] }) {
  const records = useMemo(() => {
    if (title === 'Series') return [...new Set(matches.map(match => match.series))]
    if (title === 'Teams') return [...new Set(matches.flatMap(match => [match.team1, match.team2]))]
    if (title === 'Players') return [...new Set(matches.flatMap(match => match.innings.flatMap(innings => [...innings.batting.map(row => row.player), ...innings.bowling.map(row => row.player)])))]
    return []
  }, [matches, title])
  return <main className="page"><div className="page-title"><span className="eyebrow">CRICKET HUB</span><h1>{title}</h1></div>
    {records.length ? <div className={title === 'Players' ? 'player-grid' : 'team-grid'}>{records.map((record, index) => <div className={title === 'Players' ? 'player-card' : 'team-card'} key={record}>{title === 'Players' ? <div className="avatar">{record.split(' ').map(part => part[0]).join('').slice(0, 2)}</div> : <TeamBadge code={record.slice(0, 3)}/>}<div><h3>{record}</h3><span>{title === 'Series' ? 'Series in match schedule' : title === 'Teams' ? 'Listed in match schedule' : `Scorecard entries · ${index + 1}`}</span></div></div>)}</div> :
      <EmptyState title={`No ${title.toLowerCase()} yet`} message="This section is populated from match information entered by an administrator."/ >}
  </main>
}

function StatsPage({ matches }: { matches: Match[] }) {
  const stats = matches.flatMap(match => match.innings.flatMap(innings => innings.batting.map(row => ({ ...row, teamCode: innings.teamCode, match }))))
  const top = [...stats].sort((a, b) => b.runs - a.runs).slice(0, 5)
  return <main className="page"><div className="page-title"><span className="eyebrow">MATCH DATA</span><h1>Statistics</h1></div>
    {top.length ? <div className="stats-grid">{top.map((row, index) => <div className="stat-panel" key={`${row.player}-${row.match.id}-${index}`}><span>Runs · {row.match.stage}</span><b>{row.runs}</b><small>{row.player} · {row.teamCode}</small></div>)}</div> :
      <EmptyState title="Statistics unavailable" message="Statistics will appear when administrators enter verified scorecard data."/ >}
  </main>
}

export default function App() {
  const [matches, setMatches] = useState<Match[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const refresh = async () => {
    try { const data = await api<Match[]>('/api/v1/matches'); setMatches(data); setError('') }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Unable to load matches') }
    finally { setLoading(false) }
  }
  useEffect(() => { void refresh() }, [])
  return <><Header/><Routes>
    <Route path="/" element={<Home matches={matches} loading={loading} error={error}/>}/>
    <Route path="/matches" element={<MatchesPage matches={matches}/>}/>
    <Route path="/matches/:id" element={<MatchDetail matches={matches}/>}/>
    <Route path="/series" element={<ListingPage title="Series" matches={matches}/>}/>
    <Route path="/teams" element={<ListingPage title="Teams" matches={matches}/>}/>
    <Route path="/players" element={<ListingPage title="Players" matches={matches}/>}/>
    <Route path="/stats" element={<StatsPage matches={matches}/>}/>
    <Route path="/admin" element={<Admin matches={matches} onRefresh={refresh}/>}/>
    <Route path="*" element={<main className="page"><EmptyState title="Page not found" message="The page you requested does not exist."/></main>}/>
  </Routes></>
}
