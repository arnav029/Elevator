import { useCallback, useEffect, useRef, useState } from 'react'
import { BLANK, GRID, LIMITS, OBJECTS, PALETTE, WALLPAPERS, label } from '../constants'
import { drawPixels } from '../draw'
import { RoomScene } from './Scene'
import { Sprite } from './Canvases'

function PixelEditor({ pixels, getPixels, setPixels, color, setColor, tool }) {
  const ref = useRef(null)
  const drawing = useRef(false)
  const last = useRef(null)
  const [showGrid, setShowGrid] = useState(true)

  useEffect(() => {
    if (ref.current) drawPixels(ref.current, pixels)
  }, [pixels])

  const cellAt = (e) => {
    const r = ref.current.getBoundingClientRect()
    const x = Math.floor(((e.clientX - r.left) / r.width) * GRID)
    const y = Math.floor(((e.clientY - r.top) / r.height) * GRID)
    if (x < 0 || y < 0 || x >= GRID || y >= GRID) return null
    return y * GRID + x
  }

  const apply = (i, start) => {
    if (i == null) return
    const pixels = getPixels()
    if (tool === 'pick') {
      setColor(pixels[i])
      return
    }
    if (tool === 'fill') {
      if (!start) return
      const target = pixels[i]
      if (target === color) return
      const out = pixels.split('')
      const stack = [i]
      while (stack.length) {
        const k = stack.pop()
        if (out[k] !== target) continue
        out[k] = color
        const x = k % GRID
        if (x > 0) stack.push(k - 1)
        if (x < GRID - 1) stack.push(k + 1)
        if (k >= GRID) stack.push(k - GRID)
        if (k < GRID * (GRID - 1)) stack.push(k + GRID)
      }
      setPixels(out.join(''), start)
      return
    }
    // Pen and eraser: draw a line from the previous cell so fast strokes have no gaps.
    const c = tool === 'erase' ? 'c' : color
    const from = start || last.current == null ? i : last.current
    last.current = i
    const out = pixels.split('')
    const x0 = from % GRID, y0 = Math.floor(from / GRID), x1 = i % GRID, y1 = Math.floor(i / GRID)
    const steps = Math.max(Math.abs(x1 - x0), Math.abs(y1 - y0), 1)
    for (let s = 0; s <= steps; s++) {
      const x = Math.round(x0 + ((x1 - x0) * s) / steps)
      const y = Math.round(y0 + ((y1 - y0) * s) / steps)
      out[y * GRID + x] = c
    }
    const next = out.join('')
    if (next !== pixels || start) setPixels(next, start)
  }

  return (
    <div className="pixel-editor">
      <div className={`pixel-board ${showGrid ? 'grid' : ''}`}>
        <canvas
          ref={ref}
          className="pixelated"
          onPointerDown={(e) => {
            e.currentTarget.setPointerCapture(e.pointerId)
            drawing.current = true
            apply(cellAt(e), true)
          }}
          onPointerMove={(e) => drawing.current && tool !== 'fill' && apply(cellAt(e), false)}
          onPointerUp={() => { drawing.current = false; last.current = null }}
          onPointerCancel={() => (drawing.current = false)}
        />
      </div>
      <label className="grid-toggle">
        <input type="checkbox" checked={showGrid} onChange={(e) => setShowGrid(e.target.checked)} /> grid
      </label>
    </div>
  )
}

export default function Editor({ n, basement, initial, mode, onSave, onClose }) {
  const [name, setName] = useState(initial?.name || '')
  const [message, setMessage] = useState(initial?.message || '')
  const [pixels, setPixelsRaw] = useState(initial?.pixels || BLANK)
  const [wallpaper, setWallpaper] = useState(initial?.wallpaper ?? 0)
  const [objects, setObjects] = useState(initial?.objects || [])
  const [color, setColor] = useState('0')
  const [tool, setTool] = useState('pen')
  const [history, setHistory] = useState([])
  const [err, setErr] = useState('')
  const [saving, setSaving] = useState(false)

  const pixelsRef = useRef(pixels)
  const setPixels = useCallback((next, startOfStroke) => {
    if (startOfStroke) {
      const prev = pixelsRef.current
      setHistory((h) => [...h.slice(-40), prev])
    }
    pixelsRef.current = next
    setPixelsRaw(next)
  }, [])

  const undo = () => {
    if (!history.length) return
    const prev = history[history.length - 1]
    pixelsRef.current = prev
    setPixelsRaw(prev)
    setHistory(history.slice(0, -1))
  }

  useEffect(() => {
    const onKey = (e) => {
      if (e.key === 'Escape') onClose()
      if ((e.ctrlKey || e.metaKey) && e.key === 'z') { e.preventDefault(); undo() }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  })

  const toggleObject = (i) =>
    setObjects((o) => (o.includes(i) ? o.filter((x) => x !== i) : o.length < LIMITS.objects ? [...o, i] : o))

  async function save(e) {
    e.preventDefault()
    setSaving(true)
    setErr('')
    try {
      await onSave(basement ? { message } : { name, message, pixels, wallpaper, objects })
    } catch (ex) {
      setErr(ex.message)
      setSaving(false)
    }
  }

  const title = mode === 'edit' ? `Edit floor ${label(n)}` : basement ? `Basement ${label(n)}` : `Build floor ${label(n)}`

  if (basement) {
    return (
      <div className="modal-back" onClick={onClose}>
        <form className="modal editor basement-editor" onClick={(e) => e.stopPropagation()} onSubmit={save}>
          <h2>{title}</h2>
          <p className="muted">No windows, no drawings, no names. Just a bulb and what you need to say. It stays anonymous.</p>
          <textarea
            autoFocus
            rows={6}
            maxLength={LIMITS.message}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="a secret, a confession, a thing you never said out loud…"
          />
          <div className="count">{message.length}/{LIMITS.message}</div>
          {err && <div className="error">{err}</div>}
          <div className="modal-actions">
            <button type="button" className="btn ghost" onClick={onClose}>cancel</button>
            <button className="btn claim" disabled={saving || !message.trim()}>{mode === 'edit' ? 'save' : 'leave it here'}</button>
          </div>
        </form>
      </div>
    )
  }

  return (
    <div className="modal-back" onClick={onClose}>
      <form className="modal editor" onClick={(e) => e.stopPropagation()} onSubmit={save}>
        <h2>{title}</h2>
        <div className="editor-grid">
          <div className="editor-left">
            <div className="field-label">Wall art · 32×32</div>
            <PixelEditor pixels={pixels} getPixels={() => pixelsRef.current} setPixels={setPixels} color={color} setColor={setColor} tool={tool} />
            <div className="palette">
              {PALETTE.map((hex, i) => {
                const c = i.toString(16)
                return (
                  <button
                    type="button"
                    key={c}
                    className={`swatch ${color === c ? 'sel' : ''}`}
                    style={{ background: hex }}
                    onClick={() => { setColor(c); if (tool === 'erase' || tool === 'pick') setTool('pen') }}
                    aria-label={`colour ${i}`}
                  />
                )
              })}
            </div>
            <div className="tools">
              {[['pen', '✎ pen'], ['fill', '◧ fill'], ['erase', '⌫ erase'], ['pick', '⊙ pick']].map(([t, l]) => (
                <button type="button" key={t} className={`pill ${tool === t ? 'on' : ''}`} onClick={() => setTool(t)}>{l}</button>
              ))}
              <button type="button" className="pill" onClick={undo} disabled={!history.length}>↶ undo</button>
              <button type="button" className="pill" onClick={() => setPixels(BLANK, true)}>clear</button>
            </div>
          </div>
          <div className="editor-right">
            <label className="field-label" htmlFor="room-name">Room name</label>
            <input id="room-name" autoFocus maxLength={LIMITS.name} value={name} onChange={(e) => setName(e.target.value)} placeholder="what is this room called?" />
            <label className="field-label" htmlFor="room-msg">Message <span className="count">{message.length}/{LIMITS.message}</span></label>
            <textarea id="room-msg" rows={3} maxLength={LIMITS.message} value={message} onChange={(e) => setMessage(e.target.value)} placeholder="say something to whoever rides up here" />
            <div className="field-label">Wallpaper</div>
            <div className="wallpapers">
              {WALLPAPERS.map((w, i) => (
                <button type="button" key={w.name} title={w.name} className={`swatch big ${wallpaper === i ? 'sel' : ''}`} style={{ background: w.color }} onClick={() => setWallpaper(i)} />
              ))}
            </div>
            <div className="field-label">Objects <span className="count">{objects.length}/{LIMITS.objects}</span></div>
            <div className="objects">
              {OBJECTS.map((o, i) => (
                <button type="button" key={o} className={`object-btn ${objects.includes(i) ? 'sel' : ''}`} onClick={() => toggleObject(i)} title={o}>
                  <Sprite name={o} />
                  <span>{o}</span>
                </button>
              ))}
            </div>
            <div className="field-label">Preview</div>
            <div className="editor-preview">
              <RoomScene n={n} room={{ name, message, pixels, wallpaper, objects }} notes={[]} />
            </div>
          </div>
        </div>
        {err && <div className="error">{err}</div>}
        <div className="modal-actions">
          <span className="muted small">No links. Be kind. Rooms enter the random pool after a quick check.</span>
          <button type="button" className="btn ghost" onClick={onClose}>cancel</button>
          <button className="btn claim" disabled={saving || !name.trim()}>{mode === 'edit' ? 'save changes' : 'publish room'}</button>
        </div>
      </form>
    </div>
  )
}
