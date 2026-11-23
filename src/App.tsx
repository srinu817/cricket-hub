import { FormEvent, useEffect, useMemo, useRef, useState } from 'react'
import { Link, NavLink, Route, Routes, useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import {
  CalendarDays, ChevronDown, ChevronRight, CircleUserRound, LayoutDashboard,
  LogOut, Menu, Search, ShieldCheck, Trophy, X
} from 'lucide-react'

type Status = 'Upcoming' | 'Completed'
type BattingRow = { player: string; playerId?: string | null; dismissal: string; runs: number; balls: number; fours: number; sixes: number }
type BowlingRow = { player: string; playerId?: string | null; overs: string; maidens: number; runs: number; wickets: number }
type Innings = { teamCode: string; total: string; overs: string; batting: BattingRow[]; bowling: BowlingRow[] }
type Match = {
  id: string; series: string; seriesId?: string | null; stage: string; status: Status
  team1: string; team1Code: string; team1Id?: string | null
  team2: string; team2Code: string; team2Id?: string | null
  date: string; time: string; venue: string; format: string
  result: string; toss: string; innings: Innings[]; commentary: string[]
}
type TeamMaster = { id: string; name: string; shortName: string; country: string | null; category: string | null; isActive: boolean; createdAt: string; updatedAt: string }
type PlayerMaster = { id: string; fullName: string; displayName: string | null; playingRole: string; battingStyle: string | null; bowlingStyle: string | null; isActive: boolean; teamIds: string[]; createdAt: string; updatedAt: string }
type SeriesMaster = { id: string; name: string; category: string | null; startDate: string | null; endDate: string | null; isActive: boolean; teamIds: string[]; createdAt: string; updatedAt: string }
type MasterKind = 'teams' | 'players' | 'series'
type MasterSection = 'matches' | MasterKind
type MasterRecord = TeamMaster | PlayerMaster | SeriesMaster
type SelectOption = { id: string; label: string; name?: string; shortName?: string; teamIds?: string[] }
type MasterDraft = {
  name: string; shortName: string; country: string; category: string
  fullName: string; displayName: string; playingRole: string; battingStyle: string; bowlingStyle: string
  startDate: string; endDate: string; isActive: boolean; teamIds: string[]
}

const emptyScore = (teamCode: string): Innings => ({ teamCode, total: '', overs: '', batting: [], bowling: [] })
const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/+$/, '')
const api = async <T,>(url: string, init?: RequestInit): Promise<T> => {
  const response = await fetch(`${apiBaseUrl}${url}`, {
    ...init,
    credentials: 'include',
    headers: { 'content-type': 'application/json', ...init?.headers },
  })
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

function SearchableSelect({
  label, value, options, placeholder, onChange, search, selectedOption, onSearchError,
}: {
  label: string
  value: string
  options: SelectOption[]
  placeholder: string
  onChange: (id: string, option: SelectOption) => void
  search?: (query: string) => Promise<SelectOption[]>
  selectedOption?: SelectOption
  onSearchError?: (cause: unknown) => void
}) {
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const [remoteOptions, setRemoteOptions] = useState<SelectOption[]>([])
  const searchTimer = useRef<number | null>(null)
  const allOptions = [...options, ...remoteOptions, ...(selectedOption ? [selectedOption] : [])]
    .filter((option, index, items) => items.findIndex(item => item.id === option.id) === index)
  const selected = allOptions.find(option => option.id === value)
  const filtered = allOptions.filter(option => option.label.toLowerCase().includes(query.toLowerCase())).slice(0, 30)
  useEffect(() => () => {
    if (searchTimer.current !== null) window.clearTimeout(searchTimer.current)
  }, [])
  const updateQuery = (nextQuery: string) => {
    setQuery(nextQuery)
    setOpen(true)
    if (searchTimer.current !== null) window.clearTimeout(searchTimer.current)
    if (!nextQuery.trim() || !search) {
      setRemoteOptions([])
      return
    }
    searchTimer.current = window.setTimeout(() => {
      void search(nextQuery.trim())
        .then(setRemoteOptions)
        .catch(cause => onSearchError?.(cause))
    }, 200)
  }
  return <div className="searchable-field">
    <label>{label}<input
      role="combobox"
      aria-expanded={open}
      aria-autocomplete="list"
      value={open ? query : selected?.label || ''}
      placeholder={placeholder}
      onFocus={() => { setOpen(true); setQuery('') }}
      onBlur={() => setOpen(false)}
      onChange={event => updateQuery(event.target.value)}
    /></label>
    {open && <div className="searchable-options" role="listbox">
      {filtered.length ? filtered.map(option => <button
        type="button"
        role="option"
        aria-selected={option.id === value}
        key={option.id}
        onMouseDown={event => event.preventDefault()}
        onClick={() => { onChange(option.id, option); setQuery(''); setOpen(false) }}
      >{option.label}</button>) : <span className="searchable-empty">No matching records</span>}
    </div>}
  </div>
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
  const series = params.get('series') || ''
  const team = params.get('team') || ''
  useEffect(() => setQuery(params.get('q') || ''), [params])
  const filtered = matches.filter(match =>
    (status === 'All' || match.status === status) &&
    (format === 'All' || match.format === format) &&
    (!date || match.date === date) &&
    (!series || match.series === series) &&
    (!team || match.team1 === team || match.team2 === team) &&
    `${match.team1} ${match.team2} ${match.series} ${match.team1Code} ${match.team2Code}`.toLowerCase().includes(query.toLowerCase())
  ).sort((first, second) => first.date.localeCompare(second.date) || first.time.localeCompare(second.time) || first.stage.localeCompare(second.stage))
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
    {(series || team) && <div className="active-filters">{series && <button onClick={() => setFilter('series', '')}>Series: {series} ×</button>}{team && <button onClick={() => setFilter('team', '')}>Team: {team} ×</button>}</div>}
    {filtered.length ? <div className="match-grid page-grid">{filtered.map(match => <MatchCard key={match.id} match={match}/>)}</div> :
      <EmptyState title="No matches found" message="Try a different search or filter. Admins can add matches from the admin area."/ >}
  </main>
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

function emptyMasterDraft(): MasterDraft {
  return {
    name: '', shortName: '', country: '', category: '',
    fullName: '', displayName: '', playingRole: 'Batter', battingStyle: '', bowlingStyle: '',
    startDate: '', endDate: '', isActive: true, teamIds: [],
  }
}

function masterDraftFrom(kind: MasterKind, record: MasterRecord): MasterDraft {
  if (kind === 'teams') {
    const team = record as TeamMaster
    return { ...emptyMasterDraft(), name: team.name, shortName: team.shortName, country: team.country || '', category: team.category || '', isActive: team.isActive }
  }
  if (kind === 'players') {
    const player = record as PlayerMaster
    return {
      ...emptyMasterDraft(), fullName: player.fullName, displayName: player.displayName || '',
      playingRole: player.playingRole, battingStyle: player.battingStyle || '',
      bowlingStyle: player.bowlingStyle || '', isActive: player.isActive, teamIds: player.teamIds,
    }
  }
  const series = record as SeriesMaster
  return {
    ...emptyMasterDraft(), name: series.name, category: series.category || '',
    startDate: series.startDate || '', endDate: series.endDate || '',
    isActive: series.isActive, teamIds: series.teamIds,
  }
}

function masterPayload(kind: MasterKind, draft: MasterDraft): Record<string, unknown> {
  if (kind === 'teams') {
    return {
      name: draft.name, shortName: draft.shortName,
      country: draft.country || null, category: draft.category || null, isActive: draft.isActive,
    }
  }
  if (kind === 'players') {
    return {
      fullName: draft.fullName, displayName: draft.displayName || null,
      playingRole: draft.playingRole, battingStyle: draft.battingStyle || null,
      bowlingStyle: draft.bowlingStyle || null, isActive: draft.isActive, teamIds: draft.teamIds,
    }
  }
  return {
    name: draft.name, category: draft.category || null,
    startDate: draft.startDate || null, endDate: draft.endDate || null,
    isActive: draft.isActive, teamIds: draft.teamIds,
  }
}

function MasterManagement({
  kind, teams, hasMatchDraft, onReturnToMatch, onSave, onSaved,
}: {
  kind: MasterKind
  teams: TeamMaster[]
  hasMatchDraft: boolean
  onReturnToMatch: () => void
  onSave: (kind: MasterKind, id: string | null, payload: Record<string, unknown>) => Promise<void>
  onSaved: () => Promise<void>
}) {
  const [items, setItems] = useState<MasterRecord[]>([])
  const [query, setQuery] = useState('')
  const [offset, setOffset] = useState(0)
  const [hasNext, setHasNext] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [draft, setDraft] = useState<MasterDraft>(emptyMasterDraft)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [teamQuery, setTeamQuery] = useState('')
  const [associationTeams, setAssociationTeams] = useState(teams)
  const title = kind === 'teams' ? 'Teams' : kind === 'players' ? 'Players' : 'Series'

  useEffect(() => {
    let active = true
    const params = new URLSearchParams({ limit: '51', offset: String(offset) })
    if (query.trim()) params.set('q', query.trim())
    setLoading(true)
    setError('')
    api<MasterRecord[]>(`/api/v1/admin/${kind}?${params.toString()}`)
      .then(records => {
        if (!active) return
        setItems(records.slice(0, 50))
        setHasNext(records.length > 50)
      })
      .catch(cause => {
        if (active) setError(cause instanceof Error ? cause.message : `Could not load ${title.toLowerCase()}`)
      })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [kind, offset, query, refreshKey, title])

  useEffect(() => {
    if (kind === 'teams' || !teamQuery.trim()) {
      setAssociationTeams(teams)
      return
    }
    let active = true
    const timer = window.setTimeout(() => {
      const params = new URLSearchParams({ q: teamQuery.trim(), limit: '100', offset: '0' })
      api<TeamMaster[]>(`/api/v1/admin/teams?${params.toString()}`)
        .then(records => { if (active) setAssociationTeams(records) })
        .catch(cause => {
          if (active) setError(cause instanceof Error ? cause.message : 'Could not search teams')
        })
    }, 200)
    return () => {
      active = false
      window.clearTimeout(timer)
    }
  }, [kind, teamQuery, teams])

  const edit = (record: MasterRecord) => {
    setEditingId(record.id)
    setDraft(masterDraftFrom(kind, record))
    setError('')
    setNotice('')
  }
  const save = async (event: FormEvent) => {
    event.preventDefault()
    setBusy(true)
    setError('')
    setNotice('')
    try {
      await onSave(kind, editingId, masterPayload(kind, draft))
      await onSaved()
      setEditingId(null)
      setDraft(emptyMasterDraft())
      setRefreshKey(value => value + 1)
      setNotice(`${title.slice(0, -1)} ${editingId ? 'updated' : 'added'}.`)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : `Could not save ${title.toLowerCase()}`)
    } finally {
      setBusy(false)
    }
  }
  const toggleActive = async (record: MasterRecord) => {
    setBusy(true)
    setError('')
    setNotice('')
    try {
      const current = masterDraftFrom(kind, record)
      await onSave(kind, record.id, masterPayload(kind, { ...current, isActive: !record.isActive }))
      await onSaved()
      setRefreshKey(value => value + 1)
      setNotice(`${title.slice(0, -1)} ${record.isActive ? 'deactivated' : 'reactivated'}.`)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : `Could not update ${title.toLowerCase()}`)
    } finally {
      setBusy(false)
    }
  }
  const toggleTeam = (teamId: string) => setDraft(current => ({
    ...current,
    teamIds: current.teamIds.includes(teamId)
      ? current.teamIds.filter(id => id !== teamId)
      : [...current.teamIds, teamId],
  }))

  return <section className="master-management">
    <div className="master-heading"><div><span className="eyebrow">MASTER DATA</span><h2>{title} management</h2><p className="muted-copy">Inactive records are retained for existing matches and scorecards.</p></div>
      {hasMatchDraft && <button className="secondary-button" type="button" onClick={onReturnToMatch}>Return to match draft</button>}
    </div>
    {error && <div className="error-banner" role="alert">{error}</div>}
    {notice && <div className="notice" role="status">{notice}</div>}
    <div className="master-layout">
      <form className="match-form master-form" onSubmit={save}>
        <div className="form-heading"><div><h3>{editingId ? `Edit ${title.slice(0, -1).toLowerCase()}` : `Add ${title.slice(0, -1).toLowerCase()}`}</h3><p>Save reusable records for match entry.</p></div></div>
        <div className="form-grid">
          {kind === 'teams' && <>
            <label>Team name<input required maxLength={100} value={draft.name} onChange={event => setDraft(current => ({ ...current, name: event.target.value }))}/></label>
            <label>Short name / code<input required maxLength={10} value={draft.shortName} onChange={event => setDraft(current => ({ ...current, shortName: event.target.value.toUpperCase() }))}/></label>
            <label>Country<input maxLength={100} value={draft.country} onChange={event => setDraft(current => ({ ...current, country: event.target.value }))}/></label>
            <label>Category<input maxLength={60} value={draft.category} onChange={event => setDraft(current => ({ ...current, category: event.target.value }))} placeholder="National, franchise…"/></label>
          </>}
          {kind === 'players' && <>
            <label>Full name<input required maxLength={120} value={draft.fullName} onChange={event => setDraft(current => ({ ...current, fullName: event.target.value }))}/></label>
            <label>Display name<input maxLength={100} value={draft.displayName} onChange={event => setDraft(current => ({ ...current, displayName: event.target.value }))}/></label>
            <label>Playing role<select value={draft.playingRole} onChange={event => setDraft(current => ({ ...current, playingRole: event.target.value }))}>
              <option>Batter</option><option>Bowler</option><option>All-rounder</option><option>Wicketkeeper</option>
            </select></label>
            <label>Batting style<input maxLength={60} value={draft.battingStyle} onChange={event => setDraft(current => ({ ...current, battingStyle: event.target.value }))} placeholder="Right-hand bat…"/></label>
            <label>Bowling style<input maxLength={80} value={draft.bowlingStyle} onChange={event => setDraft(current => ({ ...current, bowlingStyle: event.target.value }))} placeholder="Right-arm fast…"/></label>
          </>}
          {kind === 'series' && <>
            <label>Series name<input required maxLength={160} value={draft.name} onChange={event => setDraft(current => ({ ...current, name: event.target.value }))}/></label>
            <label>Category<input maxLength={60} value={draft.category} onChange={event => setDraft(current => ({ ...current, category: event.target.value }))} placeholder="Bilateral, tournament…"/></label>
            <label>Start date<input type="date" value={draft.startDate} onChange={event => setDraft(current => ({ ...current, startDate: event.target.value }))}/></label>
            <label>End date<input type="date" value={draft.endDate} onChange={event => setDraft(current => ({ ...current, endDate: event.target.value }))}/></label>
          </>}
          {(kind === 'players' || kind === 'series') && <fieldset className="wide-field master-team-choices">
            <legend>{kind === 'players' ? 'Team associations (multiple allowed)' : 'Participating teams'}</legend>
            <label className="team-association-search">Search teams<input value={teamQuery} onChange={event => setTeamQuery(event.target.value)} placeholder="Search by team name or code"/></label>
            {associationTeams.length ? associationTeams.map(team => <label key={team.id}>
              <input type="checkbox" checked={draft.teamIds.includes(team.id)} disabled={!team.isActive && !draft.teamIds.includes(team.id)} onChange={() => toggleTeam(team.id)}/>
              {team.name} ({team.shortName}){!team.isActive && ' · Inactive'}
            </label>) : <p className="muted-copy">{teamQuery ? 'No matching teams.' : 'Add an active team before assigning one here.'}</p>}
            {draft.teamIds.some(id => !associationTeams.some(team => team.id === id)) && <p className="muted-copy">Some selected teams are outside these results; search by name or code to review them.</p>}
          </fieldset>}
          {editingId && <label className="wide-field active-toggle"><input type="checkbox" checked={draft.isActive} onChange={event => setDraft(current => ({ ...current, isActive: event.target.checked }))}/> Active</label>}
        </div>
        <div className="form-actions">
          {editingId && <button className="secondary-button" type="button" onClick={() => { setEditingId(null); setDraft(emptyMasterDraft()) }}>Cancel edit</button>}
          <button className="primary-button" disabled={busy}>{busy ? 'Saving…' : editingId ? 'Save changes' : `Add ${title.slice(0, -1).toLowerCase()}`}</button>
        </div>
      </form>
      <div className="master-records">
        <label className="master-search">Search {title.toLowerCase()}<input value={query} onChange={event => { setQuery(event.target.value); setOffset(0) }} placeholder={`Search ${title.toLowerCase()}`}/></label>
        {loading ? <div className="loading-state">Loading {title.toLowerCase()}…</div> : items.length ? items.map(record => {
          const recordTitle = 'fullName' in record ? record.fullName : record.name
          const summary = 'shortName' in record
            ? `${record.shortName}${record.country ? ` · ${record.country}` : ''}`
            : 'playingRole' in record
              ? `${record.displayName || record.fullName} · ${record.playingRole}`
              : `${record.category || 'Series'} · ${record.teamIds.length} participating team(s)`
          return <div className="master-record" key={record.id}>
            <div><strong>{recordTitle}</strong><small>{summary}</small><span className={`status ${record.isActive ? 'upcoming' : 'completed'}`}>{record.isActive ? 'Active' : 'Inactive'}</span></div>
            <div className="row-actions"><button type="button" onClick={() => edit(record)}>Edit</button><button type="button" disabled={busy} onClick={() => void toggleActive(record)}>{record.isActive ? 'Deactivate' : 'Activate'}</button></div>
          </div>
        }) : <div className="empty-inline">No {title.toLowerCase()} found.</div>}
        <div className="master-pagination"><button className="secondary-button" disabled={offset === 0 || loading} onClick={() => setOffset(value => Math.max(0, value - 50))}>Previous</button><button className="secondary-button" disabled={!hasNext || loading} onClick={() => setOffset(value => value + 50)}>Next</button></div>
      </div>
    </div>
  </section>
}

function Admin({ matches, onRefresh }: { matches: Match[]; onRefresh: () => Promise<void> }) {
  const [authenticated, setAuthenticated] = useState<boolean | null>(null)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [editing, setEditing] = useState<Match | null>(null)
  const [notice, setNotice] = useState('')
  const [section, setSection] = useState<MasterSection>('matches')
  const [teams, setTeams] = useState<TeamMaster[]>([])
  const [players, setPlayers] = useState<PlayerMaster[]>([])
  const [series, setSeries] = useState<SeriesMaster[]>([])
  const [masterError, setMasterError] = useState('')

  const loadMasterChoices = async () => {
    const [teamData, playerData, seriesData] = await Promise.all([
      api<TeamMaster[]>('/api/v1/admin/teams?limit=100&offset=0'),
      api<PlayerMaster[]>('/api/v1/admin/players?limit=100&offset=0'),
      api<SeriesMaster[]>('/api/v1/admin/series?limit=100&offset=0'),
    ])
    setTeams(teamData)
    setPlayers(playerData)
    setSeries(seriesData)
    setMasterError('')
  }

  useEffect(() => {
    api<{ authenticated: boolean }>('/api/v1/auth/session')
      .then(session => setAuthenticated(session.authenticated))
      .catch(() => setAuthenticated(false))
  }, [])
  useEffect(() => {
    if (authenticated) {
      loadMasterChoices().catch(cause => setMasterError(cause instanceof Error ? cause.message : 'Could not load master data'))
    }
  }, [authenticated])
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
  const saveMaster = async (kind: MasterKind, id: string | null, payload: Record<string, unknown>) => {
    const endpoint = `/api/v1/admin/${kind}${id ? `/${id}` : ''}`
    await api(endpoint, { method: id ? 'PUT' : 'POST', body: JSON.stringify(payload) })
  }
  const remove = async (match: Match) => {
    if (!window.confirm(`Delete ${match.stage}: ${match.team1} vs ${match.team2}?`)) return
    try { await api(`/api/v1/matches/${match.id}`, { method: 'DELETE' }); await onRefresh(); setNotice('Match deleted.') }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not delete match') }
  }
  if (authenticated === null) return <main className="login-page"><p>Checking admin session…</p></main>
  if (!authenticated) return <main className="login-page"><form className="login-card" onSubmit={login}>
    <div className="login-mark"><ShieldCheck size={24}/></div><span className="eyebrow">ADMINISTRATION</span><h1>Admin sign in</h1>
    <p className="muted-copy">One administrator account is created from server configuration. Public signup is disabled.</p>
    {error && <p className="form-error" role="alert">{error}</p>}
    <label>Email<input type="email" autoComplete="username" required value={email} onChange={event => setEmail(event.target.value)} placeholder="admin@crickethub.com"/></label>
    <label>Password<input type="password" autoComplete="current-password" required value={password} onChange={event => setPassword(event.target.value)} placeholder="Password"/></label>
    <button className="primary-button" type="submit" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}</button>
  </form></main>
  const sectionTitles: Record<MasterSection, string> = { matches: 'Match management', teams: 'Teams management', players: 'Players management', series: 'Series management' }
  return <main className="admin-page"><aside className="admin-side"><div className="admin-brand"><ShieldCheck size={20}/><b>Cricket Hub Admin</b></div>
    <button className={section === 'matches' ? 'active' : ''} onClick={() => setSection('matches')}><LayoutDashboard size={17}/> Match management</button>
    <button className={section === 'teams' ? 'active' : ''} onClick={() => setSection('teams')}><ShieldCheck size={17}/> Teams</button>
    <button className={section === 'players' ? 'active' : ''} onClick={() => setSection('players')}><CircleUserRound size={17}/> Players</button>
    <button className={section === 'series' ? 'active' : ''} onClick={() => setSection('series')}><Trophy size={17}/> Series</button>
    <button onClick={logout}><LogOut size={17}/> Sign out</button>
  </aside>
    <section className="admin-main">
      <div className="admin-title"><div><span className="eyebrow">ADMINISTRATION</span><h1>{sectionTitles[section]}</h1><p className="muted-copy">Changes are saved on this server and shown on public pages.</p></div>
        {section === 'matches' && <button className="primary-button" onClick={() => { setError(''); setEditing(newMatch()) }}>+ Add match</button>}
      </div>
      <div className="admin-tabs" role="tablist" aria-label="Admin sections">
        {(['matches', 'teams', 'players', 'series'] as MasterSection[]).map(item => <button
          type="button" role="tab" aria-selected={section === item} key={item}
          className={section === item ? 'active' : ''} onClick={() => setSection(item)}
        >{sectionTitles[item]}</button>)}
      </div>
      {error && <div className="error-banner" role="alert">{error}</div>}
      {notice && <div className="notice" role="status">{notice}</div>}
      {masterError && <div className="error-banner" role="alert">{masterError}</div>}
      <div hidden={section !== 'matches'}>
        {editing && <MatchForm
          match={editing}
          teams={teams}
          players={players}
          series={series}
          onManage={setSection}
          onSearchError={cause => setMasterError(cause instanceof Error ? cause.message : 'Could not search master data')}
          onCancel={() => setEditing(null)}
          onSave={async match => {
            setBusy(true); setError(''); setNotice('')
            try {
              const exists = matches.some(item => item.id === match.id)
              await api(exists ? `/api/v1/matches/${match.id}` : '/api/v1/matches', { method: exists ? 'PUT' : 'POST', body: JSON.stringify(match) })
              await onRefresh(); setEditing(null); setNotice(exists ? 'Match changes saved.' : 'Match added.')
            } catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not save match') }
            finally { setBusy(false) }
          }}
          busy={busy}
        />}
        <div className="admin-table"><div className="admin-table-head"><b>Match</b><b>Status</b><b>Actions</b></div>
          {matches.length ? matches.map(match => <div className="admin-table-row" key={match.id}><div><TeamBadge code={match.team1Code} small/><b>{match.team1Code}</b><span>vs</span><b>{match.team2Code}</b><small>{match.stage} · {formatDate(match.date)}</small></div><span className={`status ${match.status.toLowerCase()}`}>{match.status}</span><div className="row-actions"><button onClick={() => { setError(''); setEditing(match) }}>Edit</button><button className="danger-button" onClick={() => void remove(match)}>Delete</button></div></div>) : <div className="empty-inline">No matches yet. Use “Add match” to publish the first one.</div>}
        </div>
      </div>
      {section !== 'matches' && <MasterManagement
        kind={section}
        teams={teams}
        hasMatchDraft={editing !== null}
        onReturnToMatch={() => setSection('matches')}
        onSave={saveMaster}
        onSaved={loadMasterChoices}
      />}
    </section>
  </main>
}

function newMatch(): Match {
  return { id: '', series: '', stage: '', status: 'Upcoming', team1: '', team1Code: '', team2: '', team2Code: '', date: today(), time: '', venue: '', format: 'ODI', result: '', toss: '', innings: [], commentary: [] }
}
function MatchForm({
  match, teams, players, series, onManage, onSearchError, onCancel, onSave, busy,
}: {
  match: Match
  teams: TeamMaster[]
  players: PlayerMaster[]
  series: SeriesMaster[]
  onManage: (section: MasterSection) => void
  onSearchError: (cause: unknown) => void
  onCancel: () => void
  onSave: (match: Match) => Promise<void>
  busy: boolean
}) {
  const [form, setForm] = useState<Match>(() => structuredClone(match))
  const [formError, setFormError] = useState('')
  const set = (key: keyof Match, value: string) => setForm(current => ({ ...current, [key]: value }))
  const selectedSeries = series.find(item => item.id === form.seriesId)
  const [selectedSeriesTeamIds, setSelectedSeriesTeamIds] = useState<string[] | null>(null)
  const participatingIds = selectedSeries?.teamIds || selectedSeriesTeamIds || []
  const allowedTeam = (team: TeamMaster) => (
    team.isActive || team.id === form.team1Id || team.id === form.team2Id
  ) && (!participatingIds.length || participatingIds.includes(team.id) || team.id === form.team1Id || team.id === form.team2Id)
  const team1Options = teams.filter(team => allowedTeam(team) && team.id !== form.team2Id)
  const team2Options = teams.filter(team => allowedTeam(team) && team.id !== form.team1Id)
  const seriesOptions = series.filter(item => item.isActive || item.id === form.seriesId)
  const seriesSelectOptions = seriesOptions.map(item => ({ id: item.id, label: item.name, name: item.name, teamIds: item.teamIds }))
  const teamOptions = (items: TeamMaster[]) => items.map(item => ({ id: item.id, label: `${item.name} (${item.shortName})`, name: item.name, shortName: item.shortName }))
  const playerOptionsFor = (teamId: string | null | undefined, keepId?: string | null) => players
    .filter(player => (player.isActive && !!teamId && player.teamIds.includes(teamId)) || player.id === keepId)
    .map(player => ({
      id: player.id,
      label: `${player.displayName || player.fullName}${player.displayName && player.displayName !== player.fullName ? ` (${player.fullName})` : ''}${player.teamIds.length ? ` · ${player.teamIds.map(id => teams.find(team => team.id === id)?.shortName).filter(Boolean).join(', ')}` : ''}`,
      name: player.displayName || player.fullName,
    }))
  const searchMasters = async (kind: MasterKind, query: string, teamId?: string | null) => {
    const params = new URLSearchParams({ q: query, limit: '100', offset: '0', active_only: 'true' })
    if (kind === 'players' && teamId) params.set('team_id', teamId)
    const records = await api<MasterRecord[]>(`/api/v1/admin/${kind}?${params.toString()}`)
    if (kind === 'series') return (records as SeriesMaster[]).map(item => ({ id: item.id, label: item.name, name: item.name, teamIds: item.teamIds }))
    if (kind === 'teams') return (records as TeamMaster[]).filter(allowedTeam).map(item => ({ id: item.id, label: `${item.name} (${item.shortName})`, name: item.name, shortName: item.shortName }))
    return (records as PlayerMaster[]).map(item => ({
      id: item.id,
      label: `${item.displayName || item.fullName}${item.displayName && item.displayName !== item.fullName ? ` (${item.fullName})` : ''} · ${item.playingRole}`,
      name: item.displayName || item.fullName,
    }))
  }
  const updateInnings = (index: number, update: (innings: Innings) => Innings) => {
    const teamCode = index % 2 === 0 ? form.team1Code : form.team2Code
    setForm(current => {
      const innings = [...current.innings]
      innings[index] = update({ ...emptyScore(teamCode), ...innings[index], teamCode })
      return { ...current, innings }
    })
  }
  const selectPlayer = (inningIndex: number, type: 'batting' | 'bowling', rowIndex: number, playerId: string, playerName: string) => {
    const player = players.find(item => item.id === playerId)
    updateInnings(inningIndex, innings => ({
      ...innings,
      [type]: innings[type].map((row, index) => index === rowIndex
        ? { ...row, playerId: playerId || undefined, player: player ? player.displayName || player.fullName : playerName || row.player }
        : row),
    }))
  }
  const save = (event: FormEvent) => {
    event.preventDefault()
    setFormError('')
    try {
      if (!form.seriesId || !form.team1Id || !form.team2Id) {
        throw new Error('Select a registered series and two different registered teams before saving.')
      }
      if (form.team1Id === form.team2Id) throw new Error('Choose two different teams.')
      const inningsCount = form.format.toLowerCase().includes('test') ? 4 : 2
      const innings = form.status === 'Upcoming' ? [] : Array.from({ length: inningsCount }, (_, index) => ({
        teamCode: index % 2 === 0 ? form.team1Code : form.team2Code,
        total: form.innings[index]?.total || '', overs: form.innings[index]?.overs || '',
        batting: form.innings[index]?.batting || [], bowling: form.innings[index]?.bowling || [],
      })).filter(item => item.total || item.batting.length || item.bowling.length)
      for (const inning of innings) {
        if (inning.batting.some(row => !row.player.trim() || !row.dismissal.trim())) {
          throw new Error('Every batting row needs a player name and dismissal.')
        }
        if (inning.bowling.some(row => !row.player.trim() || !/^\d+(\.\d)?$/.test(row.overs))) {
          throw new Error('Every bowling row needs a player name and valid overs.')
        }
      }
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
    {match.id && (!match.seriesId || !match.team1Id || !match.team2Id) && <p className="legacy-link-note">This match uses preserved text snapshots. Choose registered records to link it when saving; historical records are not linked automatically.</p>}
    <div className="form-grid">
      <div className="master-select-row"><SearchableSelect label="Series" value={form.seriesId || ''} options={seriesSelectOptions} selectedOption={form.seriesId ? { id: form.seriesId, label: form.series, name: form.series } : undefined} search={query => searchMasters('series', query)} onSearchError={onSearchError} placeholder="Search active series" onChange={(id, option) => {
        const selected = series.find(item => item.id === id)
        setSelectedSeriesTeamIds(selected?.teamIds || option.teamIds || [])
        setForm(current => ({ ...current, seriesId: id, series: selected?.name || option.name || current.series }))
      }}/><button type="button" className="secondary-button" onClick={() => onManage('series')}>Manage series</button></div>
      <label>Match / stage<input required maxLength={160} value={form.stage} onChange={e => set('stage', e.target.value)} placeholder="e.g. 1st ODI"/></label>
      <label>Status<select value={form.status} onChange={e => set('status', e.target.value)}><option>Upcoming</option><option>Completed</option></select></label>
      <label>Format<input required maxLength={40} value={form.format} onChange={e => set('format', e.target.value)} placeholder="ODI, Test, T20I…"/></label>
      <div className="master-select-row"><SearchableSelect label="Team 1" value={form.team1Id || ''} options={teamOptions(team1Options)} selectedOption={form.team1Id ? { id: form.team1Id, label: `${form.team1} (${form.team1Code})`, name: form.team1, shortName: form.team1Code } : undefined} search={query => searchMasters('teams', query).then(items => items.filter(item => item.id !== form.team2Id))} onSearchError={onSearchError} placeholder="Search registered teams" onChange={(id, option) => {
        const selected = teams.find(team => team.id === id)
        const fromSearch = team1Options.find(team => team.id === id)
        const team = selected || fromSearch
        setForm(current => ({ ...current, team1Id: id, team1: team?.name || option.name || current.team1, team1Code: team?.shortName || option.shortName || current.team1Code }))
      }}/><button type="button" className="secondary-button" onClick={() => onManage('teams')}>Manage teams</button></div>
      <div className="master-select-row"><SearchableSelect label="Team 2" value={form.team2Id || ''} options={teamOptions(team2Options)} selectedOption={form.team2Id ? { id: form.team2Id, label: `${form.team2} (${form.team2Code})`, name: form.team2, shortName: form.team2Code } : undefined} search={query => searchMasters('teams', query).then(items => items.filter(item => item.id !== form.team1Id))} onSearchError={onSearchError} placeholder="Search registered teams" onChange={(id, option) => {
        const selected = teams.find(team => team.id === id)
        const fromSearch = team2Options.find(team => team.id === id)
        const team = selected || fromSearch
        setForm(current => ({ ...current, team2Id: id, team2: team?.name || option.name || current.team2, team2Code: team?.shortName || option.shortName || current.team2Code }))
      }}/><button type="button" className="secondary-button" onClick={() => onManage('teams')}>Manage teams</button></div>
      <label>Date<input required type="date" value={form.date} onChange={e => set('date', e.target.value)}/></label>
      <label>Start time<input required value={form.time} onChange={e => set('time', e.target.value)} placeholder="Local venue time"/></label>
      <label className="wide-field">Venue<input required maxLength={160} value={form.venue} onChange={e => set('venue', e.target.value)}/></label>
      <label className="wide-field">Toss details<input value={form.toss} onChange={e => set('toss', e.target.value)} placeholder="Optional"/></label>
      {form.status === 'Completed' && <label className="wide-field">Result<input value={form.result} onChange={e => set('result', e.target.value)} placeholder="Optional result text"/></label>}
    </div>
    {form.status === 'Completed' && <div className="score-input-section"><h3>Scorecard (optional)</h3><p>Use registered players where available. Existing text snapshots remain editable.</p>
      {inningsCodes.map((code, index) => <fieldset className="innings-editor" key={index}><legend>{code} innings {index + 1}</legend>
        <div className="form-grid"><label>Total<input value={form.innings[index]?.total || ''} onChange={event => updateInnings(index, innings => ({ ...innings, total: event.target.value }))} placeholder="e.g. 245/7"/></label>
        <label>Overs<input value={form.innings[index]?.overs || ''} onChange={event => updateInnings(index, innings => ({ ...innings, overs: event.target.value }))} placeholder="e.g. 50"/></label></div>
        <div className="score-entry-group"><h4>Batting entries</h4>
          {(form.innings[index]?.batting || []).map((row, rowIndex) => <div className="score-entry-row" key={`bat-${index}-${rowIndex}`}>
            <SearchableSelect label="Registered player" value={row.playerId || ''} options={playerOptionsFor(index % 2 === 0 ? form.team1Id : form.team2Id, row.playerId)} selectedOption={row.playerId ? { id: row.playerId, label: row.player, name: row.player } : undefined} search={query => searchMasters('players', query, index % 2 === 0 ? form.team1Id : form.team2Id)} onSearchError={onSearchError} placeholder="Search players on this team" onChange={(id, option) => selectPlayer(index, 'batting', rowIndex, id, option.name || '')}/>
            {!row.playerId && <label>Player name<input maxLength={100} value={row.player} onChange={event => updateInnings(index, innings => ({ ...innings, batting: innings.batting.map((item, i) => i === rowIndex ? { ...item, player: event.target.value } : item) }))}/></label>}
            <label>Dismissal<input maxLength={150} value={row.dismissal} onChange={event => updateInnings(index, innings => ({ ...innings, batting: innings.batting.map((item, i) => i === rowIndex ? { ...item, dismissal: event.target.value } : item) }))}/></label>
            <label>Runs<input type="number" min="0" value={row.runs} onChange={event => updateInnings(index, innings => ({ ...innings, batting: innings.batting.map((item, i) => i === rowIndex ? { ...item, runs: Number(event.target.value) } : item) }))}/></label>
            <label>Balls<input type="number" min="0" value={row.balls} onChange={event => updateInnings(index, innings => ({ ...innings, batting: innings.batting.map((item, i) => i === rowIndex ? { ...item, balls: Number(event.target.value) } : item) }))}/></label>
            <label>4s<input type="number" min="0" value={row.fours} onChange={event => updateInnings(index, innings => ({ ...innings, batting: innings.batting.map((item, i) => i === rowIndex ? { ...item, fours: Number(event.target.value) } : item) }))}/></label>
            <label>6s<input type="number" min="0" value={row.sixes} onChange={event => updateInnings(index, innings => ({ ...innings, batting: innings.batting.map((item, i) => i === rowIndex ? { ...item, sixes: Number(event.target.value) } : item) }))}/></label>
            <button type="button" className="danger-button" onClick={() => updateInnings(index, innings => ({ ...innings, batting: innings.batting.filter((_, i) => i !== rowIndex) }))}>Remove</button>
          </div>)}
          <button type="button" className="secondary-button" onClick={() => updateInnings(index, innings => ({ ...innings, batting: [...innings.batting, { player: '', dismissal: 'not out', runs: 0, balls: 0, fours: 0, sixes: 0 }] }))}>Add batter</button>
        </div>
        <div className="score-entry-group"><h4>Bowling entries</h4>
          {(form.innings[index]?.bowling || []).map((row, rowIndex) => <div className="score-entry-row" key={`bowl-${index}-${rowIndex}`}>
            <SearchableSelect label="Registered player" value={row.playerId || ''} options={playerOptionsFor(index % 2 === 0 ? form.team1Id : form.team2Id, row.playerId)} selectedOption={row.playerId ? { id: row.playerId, label: row.player, name: row.player } : undefined} search={query => searchMasters('players', query, index % 2 === 0 ? form.team1Id : form.team2Id)} onSearchError={onSearchError} placeholder="Search players on this team" onChange={(id, option) => selectPlayer(index, 'bowling', rowIndex, id, option.name || '')}/>
            {!row.playerId && <label>Player name<input maxLength={100} value={row.player} onChange={event => updateInnings(index, innings => ({ ...innings, bowling: innings.bowling.map((item, i) => i === rowIndex ? { ...item, player: event.target.value } : item) }))}/></label>}
            <label>Overs<input value={row.overs} onChange={event => updateInnings(index, innings => ({ ...innings, bowling: innings.bowling.map((item, i) => i === rowIndex ? { ...item, overs: event.target.value } : item) }))}/></label>
            <label>Maidens<input type="number" min="0" value={row.maidens} onChange={event => updateInnings(index, innings => ({ ...innings, bowling: innings.bowling.map((item, i) => i === rowIndex ? { ...item, maidens: Number(event.target.value) } : item) }))}/></label>
            <label>Runs<input type="number" min="0" value={row.runs} onChange={event => updateInnings(index, innings => ({ ...innings, bowling: innings.bowling.map((item, i) => i === rowIndex ? { ...item, runs: Number(event.target.value) } : item) }))}/></label>
            <label>Wickets<input type="number" min="0" value={row.wickets} onChange={event => updateInnings(index, innings => ({ ...innings, bowling: innings.bowling.map((item, i) => i === rowIndex ? { ...item, wickets: Number(event.target.value) } : item) }))}/></label>
            <button type="button" className="danger-button" onClick={() => updateInnings(index, innings => ({ ...innings, bowling: innings.bowling.filter((_, i) => i !== rowIndex) }))}>Remove</button>
          </div>)}
          <button type="button" className="secondary-button" onClick={() => updateInnings(index, innings => ({ ...innings, bowling: [...innings.bowling, { player: '', overs: '0', maidens: 0, runs: 0, wickets: 0 }] }))}>Add bowler</button>
        </div>
      </fieldset>)}
      <label className="wide-field">Commentary (optional, one entry per line)<textarea value={form.commentary.join('\n')} onChange={e => setForm(current => ({ ...current, commentary: e.target.value.split('\n') }))}/></label>
    </div>}
    <div className="form-actions"><button className="secondary-button" type="button" onClick={onCancel}>Cancel</button><button className="primary-button" disabled={busy}>{busy ? 'Saving…' : 'Save match'}</button></div>
  </form>
}

function ListingPage({ title, matches }: { title: string; matches: Match[] }) {
  const records = useMemo(() => {
    if (title === 'Series') return [...new Set([...matches].sort((first, second) => first.date.localeCompare(second.date)).map(match => match.series))]
    if (title === 'Teams') return [...new Set(matches.flatMap(match => [match.team1, match.team2]))].sort((first, second) => first.localeCompare(second))
    if (title === 'Players') return [...new Set(matches.flatMap(match => match.innings.flatMap(innings => [...innings.batting.map(row => row.player), ...innings.bowling.map(row => row.player)])))]
    return []
  }, [matches, title])
  return <main className="page"><div className="page-title"><span className="eyebrow">CRICKET HUB</span><h1>{title}</h1></div>
    {records.length ? <div className={title === 'Players' ? 'player-grid' : 'team-grid'}>{records.map((record, index) => {
      const destination = title === 'Series' ? `/matches?series=${encodeURIComponent(record)}` : title === 'Teams' ? `/matches?team=${encodeURIComponent(record)}` : ''
      const content = <>{title === 'Players' ? <div className="avatar">{record.split(' ').map(part => part[0]).join('').slice(0, 2)}</div> : <TeamBadge code={record.slice(0, 3)}/>}<div><h3>{record}</h3><span>{title === 'Series' ? 'View fixtures' : title === 'Teams' ? 'View fixtures' : `Scorecard entries · ${index + 1}`}</span></div></>
      return destination ? <Link className="team-card" key={record} to={destination}>{content}</Link> : <div className="player-card" key={record}>{content}</div>
    })}</div> :
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
