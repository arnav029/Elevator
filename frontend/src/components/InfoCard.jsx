import { useEffect, useState } from 'react'
import { api, forgetOwnerKey } from '../api'
import { LIMITS, halfLabel, label, urlFor } from '../constants'

function timeAgo(iso) {
  const s = (Date.now() - new Date(iso).getTime()) / 1000
  if (s < 60) return 'just now'
  if (s < 3600) return `${Math.floor(s / 60)}m ago`
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`
  return `${Math.floor(s / 86400)}d ago`
}

function ReportButton({ type, id, small }) {
  const [state, setState] = useState('idle')
  if (state === 'done') return <span className="reported">reported</span>
  if (state === 'confirm')
    return (
      <span className="report-confirm">
        report?{' '}
        <button className="link" onClick={async () => {
          try { await api.report(type, id); setState('done') } catch { setState('done') }
        }}>yes</button>{' '}
        <button className="link" onClick={() => setState('idle')}>no</button>
      </span>
    )
  return (
    <button className={`link report ${small ? 'small' : ''}`} onClick={() => setState('confirm')} title="Report">
      ⚑{small ? '' : ' report'}
    </button>
  )
}

function Neighbour({ dir, info, onStairs }) {
  if (!info) return <span />
  const hint = info.special
    ? { lobby: 'the lobby', brick: 'a brick wall?', roof: 'the roof', missing: '' }[info.special]
    : info.empty
      ? 'empty'
      : `“${info.name}”`
  return (
    <button className="stairs" onClick={() => onStairs(info.number)}>
      {dir === 'up' ? '↑ upstairs' : '↓ downstairs'} <span className="stairs-n">{label(info.number)}</span>
      <span className="stairs-hint">{hint}</span>
    </button>
  )
}

function OwnerBox({ n, ownerKey, onEdit, onVacated, onNotesChanged }) {
  const [info, setInfo] = useState(null)
  const [vacating, setVacating] = useState(false)
  useEffect(() => {
    let live = true
    api.owner(n, ownerKey).then((d) => live && setInfo(d)).catch((e) => {
      if (e.status === 403) forgetOwnerKey(n)
    })
    return () => { live = false }
  }, [n, ownerKey])
  if (!info) return null
  return (
    <div className="owner-box">
      <div className="owner-head">This is your floor.</div>
      <div className="owner-stats">
        <span><b>{info.room.visit_count}</b> visits</span>
        <span><b>{info.new_notes}</b> new note{info.new_notes === 1 ? '' : 's'} since {timeAgo(info.last_seen)}</span>
        {!info.in_pool && <span className="muted">not in the random pool yet</span>}
      </div>
      <div className="owner-actions">
        <button className="btn" onClick={onEdit}>✎ edit room</button>
        {vacating ? (
          <span>
            give it up for good?{' '}
            <button className="link danger" onClick={async () => { await api.vacate(n, ownerKey); forgetOwnerKey(n); onVacated() }}>yes, move out</button>{' '}
            <button className="link" onClick={() => setVacating(false)}>no</button>
          </span>
        ) : (
          <button className="link muted" onClick={() => setVacating(true)}>move out</button>
        )}
      </div>
      {info.notes.some((x) => x.new) && (
        <ul className="notes owner-new">
          {info.notes.filter((x) => x.new).map((note) => (
            <li key={note.id} className="new">
              <span>{note.body}</span>
              <button className="link small" title="remove note" onClick={async () => {
                await api.deleteNote(n, note.id, ownerKey)
                setInfo({ ...info, notes: info.notes.filter((x) => x.id !== note.id) })
                onNotesChanged()
              }}>✕</button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export default function InfoCard({ here, ownerKey, onClaim, onEdit, onStairs, onResume, onRefresh, onRide, toast }) {
  const [note, setNote] = useState('')
  const [err, setErr] = useState('')
  const [sending, setSending] = useState(false)
  const d = here.data

  useEffect(() => { setNote(''); setErr('') }, [here.n, here.half])

  if (here.half) {
    const h = here.half
    return (
      <section className="card half-card">
        <div className="card-floor">FLOOR {halfLabel(h.at)}</div>
        <h1>{h.name}</h1>
        <p className="message">{h.message}</p>
        <p className="muted">The elevator has stopped between floors. This floor isn't on any panel.</p>
        <button className="btn emergency" onClick={onResume}>● press the emergency button</button>
      </section>
    )
  }
  if (!d || d.error) return <section className="card" />

  const n = d.number
  const share = async () => {
    const url = location.origin + urlFor(n)
    try {
      if (navigator.share) await navigator.share({ title: `Floor ${label(n)}`, url })
      else {
        await navigator.clipboard.writeText(url)
        toast('Link copied.')
      }
    } catch { /* cancelled */ }
  }

  async function sendNote(e) {
    e.preventDefault()
    setSending(true)
    setErr('')
    try {
      await api.note(n, note)
      setNote('')
      toast('Note left on the wall.')
      onRefresh()
    } catch (ex) {
      setErr(ex.message)
    } finally {
      setSending(false)
    }
  }

  const neighbours = (
    <div className="neighbours">
      <Neighbour dir="up" info={d.neighbours?.above} onStairs={onStairs} />
      <Neighbour dir="down" info={d.neighbours?.below} onStairs={onStairs} />
    </div>
  )

  if (d.kind === 'special') {
    const text = {
      lobby: ['The Lobby', 'Welcome to the building. Press any floor, roll the dice, or read the directory. Floors 1 to 9,999 and B1 to B100 belong to strangers. One of them could be yours.'],
      brick: ['Floor 404', 'The doors opened onto a brick wall. Someone chalked a number on it. It is not clear the floor was ever here.'],
      roof: ['The Roof', 'Floor 10,000. Nobody owns the roof. People come up here to look at the stars and clap at meteors.'],
    }[d.special] || ['', '']
    return (
      <section className="card">
        <div className="card-floor">FLOOR {label(n)}</div>
        <h1>{text[0]}</h1>
        <p className="message">{text[1]}</p>
        {d.special === 'lobby' && (
          <p className="muted">Tip: press <kbd>R</kbd> for a random floor, <kbd>B</kbd> for the basement.</p>
        )}
        {neighbours}
      </section>
    )
  }

  if (d.kind === 'hidden') {
    return (
      <section className="card">
        <div className="card-floor">FLOOR {label(n)}</div>
        <h1>Closed for inspection</h1>
        <p className="message">Residents reported this floor. Building staff will take a look.</p>
        {neighbours}
      </section>
    )
  }

  if (d.kind === 'empty') {
    return (
      <section className="card">
        <div className="card-floor">{d.basement ? 'BASEMENT' : 'FLOOR'} {label(n)}</div>
        <h1>{d.reserved ? 'Reserved' : d.basement ? 'An empty basement room' : 'For rent'}</h1>
        <p className="message">
          {d.reserved
            ? 'Management is holding this floor for something special.'
            : d.basement
              ? 'No windows, no drawings. Just a bulb and whatever you need to say anonymously.'
              : 'Bare concrete. Your footsteps echo. Nobody lives here yet.'}
        </p>
        {d.claimable && (
          <button className="btn claim" onClick={onClaim}>
            {d.basement ? 'Leave a secret here' : `Claim floor ${label(n)}`}
          </button>
        )}
        {neighbours}
      </section>
    )
  }

  const room = d.room
  return (
    <section className="card">
      <div className="card-floor">
        {d.basement ? 'BASEMENT' : 'FLOOR'} {label(n)}
        {room.is_staff && <span className="badge">Furnished by building staff</span>}
      </div>
      {!d.basement && <h1>{room.name}</h1>}
      {room.message && !d.basement && <p className="message">{room.message}</p>}
      {d.basement && <p className="muted">An anonymous secret, left in the dark.</p>}
      <div className="meta">
        <span>{room.visit_count.toLocaleString()} visit{room.visit_count === 1 ? '' : 's'}</span>
        <button className="link" onClick={share}>↗ share</button>
        {!room.is_staff && !ownerKey && <ReportButton type="floor" id={n} />}
      </div>

      {ownerKey && <OwnerBox n={n} ownerKey={ownerKey} onEdit={onEdit} onVacated={onRefresh} onNotesChanged={onRefresh} />}

      <div className="notes-head">Sticky notes</div>
      {d.notes.length === 0 && <p className="muted">No notes yet. Be the first.</p>}
      <ul className="notes">
        {d.notes.map((x) => (
          <li key={x.id}>
            <span>{x.body}</span>
            <span className="note-meta">
              {timeAgo(x.created_at)} <ReportButton type="note" id={x.id} small />
            </span>
          </li>
        ))}
      </ul>
      <form className="note-form" onSubmit={sendNote}>
        <input
          value={note}
          maxLength={LIMITS.note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="leave a sticky note…"
        />
        <button className="btn" disabled={!note.trim() || sending}>stick</button>
      </form>
      {err && <div className="error">{err}</div>}
      {neighbours}
      {!d.basement && <button className="link muted claim-own" onClick={() => onRide('claim')}>want a floor of your own?</button>}
    </section>
  )
}
