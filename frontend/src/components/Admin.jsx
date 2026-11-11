import { useCallback, useEffect, useState } from 'react'
import { api } from '../api'
import { WALLPAPERS, label } from '../constants'
import { PixelArt } from './Canvases'

function Item({ item, act }) {
  const [confirm, setConfirm] = useState(null)
  const id = item.id
  const run = (action) => {
    if ((action === 'delete' || action === 'ban') && confirm !== action) return setConfirm(action)
    setConfirm(null)
    act(item.type, id, action)
  }
  return (
    <div className={`admin-item status-${item.status}`}>
      <div className="admin-item-head">
        <b>{item.type}</b>{' '}
        {item.type === 'floor' ? `floor ${label(id)}` : `#${id}`}
        {item.floor_number != null && ` on floor ${label(item.floor_number)}`}
        <span className={`tag ${item.status}`}>{item.status}</span>
        {item.pool_status && <span className="tag">{item.pool_status}</span>}
        {item.is_staff && <span className="tag">staff</span>}
      </div>
      <div className="admin-item-body">
        {item.type === 'floor' && item.id > 0 && (
          <div className="admin-art" style={{ background: WALLPAPERS[item.wallpaper]?.color }}>
            <PixelArt pixels={item.pixels} />
          </div>
        )}
        <div>
          {item.name && <div className="admin-name">{item.name}</div>}
          <div className="admin-text">{item.body ?? item.message}</div>
          {item.reports.length > 0 && (
            <ul className="admin-reports">
              {item.reports.map((r, i) => <li key={i}>⚑ {r.reason || 'no reason'} · {new Date(r.at).toLocaleString()}</li>)}
            </ul>
          )}
        </div>
      </div>
      <div className="admin-actions">
        {item.type === 'floor' && item.pool_status === 'pending' && <button className="btn" onClick={() => run('approve')}>approve for dice</button>}
        {item.status === 'hidden' ? (
          <button className="btn" onClick={() => run('restore')}>restore</button>
        ) : (
          <button className="btn" onClick={() => run('hide')}>hide</button>
        )}
        {item.reports.length > 0 && item.status !== 'hidden' && <button className="btn ghost" onClick={() => run('restore')}>dismiss reports</button>}
        <button className="btn danger" onClick={() => run('delete')}>{confirm === 'delete' ? 'really delete?' : 'delete'}</button>
        <button className="btn danger" onClick={() => run('ban')}>{confirm === 'ban' ? 'really ban?' : 'ban author'}</button>
      </div>
    </div>
  )
}

export default function Admin() {
  const [token, setToken] = useState(() => sessionStorage.getItem('elevator.admin') || '')
  const [input, setInput] = useState('')
  const [queue, setQueue] = useState(null)
  const [err, setErr] = useState('')
  const [msg, setMsg] = useState('')

  const load = useCallback(async () => {
    if (!token) return
    try {
      setQueue(await api.admin('GET', '/queue', token))
      setErr('')
    } catch (e) {
      setErr(e.message)
      if (e.status === 401) {
        sessionStorage.removeItem('elevator.admin')
        setToken('')
      }
    }
  }, [token])

  useEffect(() => { load() }, [load])

  async function act(type, id, action) {
    try {
      const path = action === 'approve' ? `/floor/${id}/approve` : `/${type}/${id}/${action}`
      await api.admin('POST', path, token, action === 'ban' ? { reason: 'admin' } : undefined)
      setMsg(`${action}: ${type} ${id}`)
      load()
    } catch (e) {
      setErr(e.message)
    }
  }

  if (!token) {
    return (
      <div className="admin">
        <h1>Building management</h1>
        <form onSubmit={(e) => { e.preventDefault(); sessionStorage.setItem('elevator.admin', input); setToken(input) }}>
          <input type="password" value={input} onChange={(e) => setInput(e.target.value)} placeholder="admin token" autoFocus />
          <button className="btn">enter</button>
        </form>
        {err && <div className="error">{err}</div>}
        <p><a href="/">back to the elevator</a></p>
      </div>
    )
  }

  return (
    <div className="admin">
      <h1>Building management</h1>
      <div className="admin-bar">
        {queue && <span>{queue.stats.floors} floors · {queue.stats.notes} notes · {queue.stats.graffiti} graffiti · {queue.stats.bans} bans</span>}
        <button className="btn" onClick={load}>refresh</button>
        <button className="btn" onClick={async () => { const r = await api.admin('POST', '/sweep', token); setMsg(`sweep: ${r.dusted} dusted, ${r.reclaimed} reclaimed`) }}>run dust sweep</button>
        <button className="btn ghost" onClick={() => { sessionStorage.removeItem('elevator.admin'); setToken('') }}>log out</button>
        <a href="/">elevator</a>
      </div>
      {msg && <div className="panel-msg">{msg}</div>}
      {err && <div className="error">{err}</div>}
      <h2>Review queue {queue && `(${queue.reported.length})`}</h2>
      {queue?.reported.length === 0 && <p className="muted">Nothing reported or hidden. Quiet day in the building.</p>}
      {queue?.reported.map((it) => <Item key={`${it.type}-${it.id}`} item={it} act={act} />)}
      <h2>Waiting for the dice pool {queue && `(${queue.pending_pool.length})`}</h2>
      {queue?.pending_pool.length === 0 && <p className="muted">No rooms waiting.</p>}
      {queue?.pending_pool.map((it) => <Item key={`p-${it.id}`} item={it} act={act} />)}
    </div>
  )
}
