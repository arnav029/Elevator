import { useEffect, useState } from 'react'
import { LIMITS, MAX_FLOOR, MIN_FLOOR, special } from '../constants'
import { settings, setMusic, setSound } from '../sound'

const KEYS = ['1', '2', '3', '4', '5', '6', '7', '8', '9', 'B', '0', '⌫']

export default function Panel({ display, busy, direction, onGo, onDice, onLobby, myFloor, onMyFloor, onScratch, claimed }) {
  const [entry, setEntry] = useState('')
  const [warn, setWarn] = useState('')
  const [music, setMusicState] = useState(settings.music)
  const [snd, setSnd] = useState(settings.sound)
  const [scratching, setScratching] = useState(false)
  const [line, setLine] = useState('')
  const [scratchMsg, setScratchMsg] = useState('')

  const basement = entry.startsWith('B')
  const digits = basement ? entry.slice(1) : entry

  function press(k) {
    setWarn('')
    if (k === '⌫') return setEntry((e) => e.slice(0, -1))
    if (k === 'B') return setEntry((e) => (e.startsWith('B') ? e.slice(1) : 'B' + e.replace(/^0+/, '')))
    const next = entry + k
    const num = Number((basement ? next.slice(1) : next) || 0)
    if (basement ? num > -MIN_FLOOR : num > MAX_FLOOR) {
      setWarn(basement ? 'only B1–B100' : 'top floor is 10,000')
      return
    }
    setEntry(next.replace(/^0+(?=\d)/, ''))
  }

  function go() {
    if (!digits) return
    const n = basement ? -Number(digits) : Number(digits)
    if (basement && n === 0) return
    if (special(n) === 'missing') {
      setWarn('there is no 13th floor')
      setEntry('')
      return
    }
    setEntry('')
    onGo(n)
  }

  useEffect(() => {
    const onKey = (e) => {
      if (e.target.closest('input, textarea, select, [contenteditable]')) return
      if (/^[0-9]$/.test(e.key)) press(e.key)
      else if (e.key === 'Backspace') press('⌫')
      else if (e.key.toLowerCase() === 'b') press('B')
      else if (e.key === 'Enter') go()
      else if (e.key.toLowerCase() === 'r') onDice(basement)
      else return
      e.preventDefault()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  })

  async function submitScratch(e) {
    e.preventDefault()
    try {
      await onScratch(line)
      setLine('')
      setScratching(false)
      setScratchMsg('scratched.')
    } catch (err) {
      setScratchMsg(err.message)
    }
  }

  const shown = entry ? entry : display
  const showsThirteen = digits === '13' && !basement

  return (
    <aside className="panel">
      <div className="led">
        <span className="led-arrow">{direction > 0 ? '▲' : direction < 0 ? '▼' : ' '}</span>
        <span className={`led-num ${entry ? 'typing' : ''}`}>{showsThirteen ? '--' : shown}</span>
      </div>
      <div className="panel-warn">{warn || (showsThirteen ? 'there is no 13th floor' : '')}</div>
      <div className="keypad">
        {KEYS.map((k) => (
          <button key={k} className={`key ${k === 'B' && basement ? 'lit' : ''}`} onClick={() => press(k)} aria-label={k === '⌫' ? 'delete' : k === 'B' ? 'basement' : k}>
            {k}
          </button>
        ))}
      </div>
      <button className="go" onClick={go} disabled={busy || !digits}>
        GO
      </button>
      <div className="panel-row">
        <button className="pill" onClick={() => onDice(basement)} disabled={busy} title="Random occupied floor (R)">
          ⚄ random
        </button>
        <button className="pill" onClick={onLobby} disabled={busy} title="Lobby">
          L lobby
        </button>
      </div>
      {myFloor != null && (
        <button className="pill wide" onClick={onMyFloor} disabled={busy}>
          ⌂ my floor
        </button>
      )}
      <div className="panel-row">
        <button className={`pill ${music ? 'on' : ''}`} onClick={() => { setMusic(!music); setMusicState(!music) }}>
          ♪ music
        </button>
        <button className={`pill ${snd ? 'on' : ''}`} onClick={() => { setSound(!snd); setSnd(!snd) }}>
          {snd ? '🔊' : '🔈'} sound
        </button>
      </div>
      {scratching ? (
        <form className="scratch-form" onSubmit={submitScratch}>
          <input
            autoFocus
            maxLength={LIMITS.graffiti}
            value={line}
            onChange={(e) => setLine(e.target.value)}
            placeholder="scratch one short line"
          />
          <div className="panel-row">
            <button className="pill" type="submit" disabled={!line.trim()}>scratch</button>
            <button className="pill" type="button" onClick={() => setScratching(false)}>cancel</button>
          </div>
        </form>
      ) : (
        <button className="pill wide" onClick={() => { setScratching(true); setScratchMsg('') }}>
          ✎ scratch the wall
        </button>
      )}
      {scratchMsg && <div className="panel-msg">{scratchMsg}</div>}
      <div className="panel-foot">
        {claimed ? `${claimed.claimed.toLocaleString()} / ${claimed.total.toLocaleString()} floors claimed` : ''}
        <div className="panel-hint">hold the doors (or space) to ride faster</div>
      </div>
    </aside>
  )
}
