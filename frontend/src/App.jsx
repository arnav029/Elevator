import { useCallback, useEffect, useRef, useState } from 'react'
import { api, ownerKeys, saveOwnerKey } from './api'
import { BREAKDOWN_CHANCE, MAX_FLOOR, MIN_FLOOR, halfLabel, label, parseLabel, special, urlFor } from './constants'
import { sound, settings as soundSettings, setMusic } from './sound'
import Admin from './components/Admin'
import Editor from './components/Editor'
import InfoCard from './components/InfoCard'
import KeyModal from './components/KeyModal'
import Panel from './components/Panel'
import { Scene } from './components/Scene'

const wait = (ms) => new Promise((r) => setTimeout(r, ms))
const ease = (p) => (p < 0.5 ? 2 * p * p : 1 - Math.pow(-2 * p + 2, 2) / 2)

function parseRoute() {
  const path = location.pathname
  if (path.startsWith('/admin')) return { admin: true }
  const m = path.match(/^\/floor\/([^/]+)(\/edit)?\/?$/)
  if (m) {
    const n = parseLabel(decodeURIComponent(m[1]))
    if (n != null && n >= MIN_FLOOR && n <= MAX_FLOOR) return { n, edit: !!m[2] }
  }
  return { n: 0 }
}

function titleFor(n, data) {
  const base = 'The Internet Elevator'
  if (n === 0) return base
  if (data?.kind === 'room' && data.room.name) return `${data.room.name} · Floor ${label(n)}`
  return `Floor ${label(n)} · ${base}`
}

function Doors({ open, graffiti }) {
  const lines = (side) =>
    graffiti
      .filter((_, i) => i % 2 === side)
      .map((g, i) => (
        <span
          key={g.id}
          className="scratch"
          style={{
            top: `${5 + i * 9}%`,
            left: `${6 + ((g.id * 17) % 34)}%`,
            transform: `rotate(${((g.id * 7) % 9) - 4}deg)`,
            fontSize: `${0.7 + ((g.id * 13) % 4) * 0.08}em`,
          }}
        >
          {g.body}
        </span>
      ))
  return (
    <div className={`doors ${open ? 'open' : ''}`} aria-hidden={open}>
      <div className="door left">{lines(0)}</div>
      <div className="door right">{lines(1)}</div>
    </div>
  )
}

function Building({ initial }) {
  const [here, setHere] = useState({ n: 0, data: null, half: null })
  const [phase, setPhase] = useState('closed') // closed | closing | riding | stuck | opening | open | stairs
  const [display, setDisplay] = useState('0')
  const [direction, setDirection] = useState(0)
  const [graffiti, setGraffiti] = useState([])
  const [editor, setEditor] = useState(null)
  const [keyModal, setKeyModal] = useState(null)
  const [toastMsg, setToastMsg] = useState('')
  const [keys, setKeys] = useState(ownerKeys)
  const [claimed, setClaimed] = useState(null)
  const [fresh, setFresh] = useState(false)

  const busy = useRef(false)
  const hold = useRef(false)
  const hereRef = useRef(here)
  hereRef.current = here
  const resumeTarget = useRef(null)
  const forceBreakdown = useRef(new URLSearchParams(location.search).has('breakdown'))
  const toastTimer = useRef()

  const toast = useCallback((msg) => {
    setToastMsg(msg)
    clearTimeout(toastTimer.current)
    toastTimer.current = setTimeout(() => setToastMsg(''), 2800)
  }, [])

  const loadFloor = async (n) => {
    try {
      return await api.floor(n, { visit: true, key: ownerKeys()[n] })
    } catch (e) {
      return { error: e.message, number: n }
    }
  }

  const animate = (from, to, duration) =>
    new Promise((resolve) => {
      let p = 0
      let last = performance.now()
      const step = (now) => {
        const dt = now - last
        last = now
        // Holding the doors speeds the ride up, but it is never skippable.
        p = Math.min(1, p + (dt * (hold.current ? 2.6 : 1)) / duration)
        let shown = Math.round(from + (to - from) * ease(p))
        if (shown === 13) shown = to > from ? 14 : 12
        setDisplay(label(shown))
        if (p < 1) requestAnimationFrame(step)
        else resolve()
      }
      requestAnimationFrame(step)
    })

  const pushUrl = (n) => {
    const url = n === 0 ? '/' : urlFor(n)
    if (location.pathname !== url) history.pushState({ n }, '', url)
  }

  const arrive = async (n, data, { push = true } = {}) => {
    sound.humStop()
    sound.ding(data?.kind === 'empty')
    setDirection(0)
    setDisplay(label(n))
    setFresh(true)
    setHere({ n, data, half: null })
    if (push) pushUrl(n)
    document.title = titleFor(n, data)
    setPhase('opening')
    await wait(750)
    setPhase('open')
  }

  const rideTo = useCallback(async (target, opts = {}) => {
    if (busy.current) return
    target = Math.max(MIN_FLOOR, Math.min(MAX_FLOOR, Math.round(target)))
    if (special(target) === 'missing') {
      toast('This building has no 13th floor.')
      return
    }
    const cur = hereRef.current
    const from = cur.half ? cur.half.at + 0.5 : cur.n
    if (!cur.half && target === cur.n && cur.data) return
    busy.current = true
    try {
      const dataP = loadFloor(target)
      api.graffiti().then(setGraffiti).catch(() => {})
      if (!opts.initial) {
        sound.doors()
        setPhase('closing')
        await wait(750)
      }
      setPhase('riding')
      setDirection(Math.sign(target - from))
      sound.humStart()
      const dist = Math.abs(target - from)
      // 1.5s for one floor, up to 4s for the whole building.
      const duration = 1500 + 2500 * Math.min(1, Math.log10(Math.max(1, dist)) / 4)

      const forced = forceBreakdown.current
      if (!cur.half && !opts.noBreakdown && dist >= 3 && (forced || Math.random() < BREAKDOWN_CHANCE)) {
        forceBreakdown.current = false
        const half = await api.halfFloor(from, target).catch(() => null)
        const stop = half ? half.at + 0.5 : null
        const between = half && (stop - from) * (target - from) > 0 && Math.abs(stop - from) < dist
        if (half && (between || forced)) {
          const stopAt = between ? stop : from + (target - from) / 2
          await animate(from, stopAt, duration * Math.max(0.2, Math.abs(stopAt - from) / dist))
          sound.humStop()
          sound.clunk()
          setPhase('stuck')
          setDisplay(halfLabel(half.at))
          await wait(1800)
          resumeTarget.current = target
          setHere({ n: half.at, half, data: null })
          setDirection(0)
          setFresh(true)
          document.title = `${half.name} · Floor ${halfLabel(half.at)}`
          sound.ding(true)
          setPhase('opening')
          await wait(750)
          setPhase('open')
          return
        }
      }
      await animate(from, target, duration)
      await arrive(target, await dataP, opts)
    } finally {
      busy.current = false
    }
  }, [toast])

  const takeStairs = async (n) => {
    if (busy.current) return
    busy.current = true
    try {
      setPhase('stairs')
      sound.steps()
      const [data] = await Promise.all([loadFloor(n), wait(800)])
      setHere({ n, data, half: null })
      setDisplay(label(n))
      setFresh(true)
      pushUrl(n)
      document.title = titleFor(n, data)
      await wait(60)
      setPhase('open')
    } finally {
      busy.current = false
    }
  }

  const refresh = useCallback(async () => {
    const n = hereRef.current.n
    const data = await loadFloor(n)
    setFresh(false)
    setKeys(ownerKeys())
    setHere((h) => (h.n === n && !h.half ? { ...h, data } : h))
  }, [])

  const dice = async (basement) => {
    if (busy.current) return
    try {
      const { number } = await api.random(hereRef.current.n, basement)
      rideTo(number)
    } catch (e) {
      toast(e.message)
    }
  }

  const findEmpty = async () => {
    for (let i = 0; i < 10; i++) {
      const n = 1 + Math.floor(Math.random() * 9998)
      if (special(n)) continue
      try {
        const d = await api.floor(n)
        if (d.kind === 'empty' && d.claimable) return rideTo(n)
      } catch { /* try another */ }
    }
    toast('Could not find a free floor. Try the keypad.')
  }

  // First load: land inside the elevator, then ride to the linked floor.
  useEffect(() => {
    api.lobby().then((d) => setClaimed({ claimed: d.claimed, total: d.total })).catch(() => {})
    api.graffiti().then(setGraffiti).catch(() => {})
    const { n, edit } = initial
    if (edit) {
      const m = location.hash.match(/key=([\w-]+)/)
      if (m) {
        saveOwnerKey(n, m[1])
        setKeys(ownerKeys())
      }
      history.replaceState(null, '', urlFor(n))
    }
    if (soundSettings.music) {
      // Browsers only allow audio after a gesture, so start music on the first click.
      const start = () => setMusic(true)
      window.addEventListener('pointerdown', start, { once: true })
    }
    if (n === 0) {
      busy.current = true
      loadFloor(0).then(async (data) => {
        await wait(500)
        await arrive(0, data, { push: false })
        busy.current = false
      })
    } else {
      rideTo(n, { initial: true, noBreakdown: true, push: false })
    }
    const onPop = () => {
      const r = parseRoute()
      if (!r.admin) rideTo(r.n, { push: false })
    }
    window.addEventListener('popstate', onPop)
    const down = (e) => {
      if (e.code === 'Space' && !e.target.closest('input, textarea, button')) {
        hold.current = true
        e.preventDefault()
      }
    }
    const up = (e) => { if (e.code === 'Space') hold.current = false }
    window.addEventListener('keydown', down)
    window.addEventListener('keyup', up)
    return () => {
      window.removeEventListener('popstate', onPop)
      window.removeEventListener('keydown', down)
      window.removeEventListener('keyup', up)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const d = here.data
  const ownerKey = !here.half && d?.kind === 'room' ? keys[here.n] : null
  const myFloor = Object.keys(keys)[0] ?? null
  const doorsOpen = phase === 'open' || phase === 'opening' || phase === 'stairs'
  const moving = phase !== 'open'

  return (
    <div className="app">
      <header className="topbar">
        <a className="brand" href="/" onClick={(e) => { e.preventDefault(); rideTo(0) }}>THE INTERNET ELEVATOR</a>
        <span className="tagline">One building. 10,000 floors. Every floor belongs to a stranger.</span>
      </header>
      <main className="layout">
        <div className="left">
          <div className="indicator">
            <span className="ind-arrow">{direction > 0 ? '▲' : direction < 0 ? '▼' : '•'}</span>
            <span className="ind-num">{display}</span>
          </div>
          <div
            className={`shaft phase-${phase}`}
            onPointerDown={() => (hold.current = true)}
            onPointerUp={() => (hold.current = false)}
            onPointerLeave={() => (hold.current = false)}
          >
            <div className="viewport">
              <div className={`scene-wrap ${phase === 'stairs' ? 'fade' : ''}`}>
                <Scene here={here} onRide={rideTo} fresh={fresh} />
              </div>
              <Doors open={doorsOpen} graffiti={graffiti} />
              {toastMsg && <div className="toast">{toastMsg}</div>}
            </div>
          </div>
          <InfoCard
            here={here}
            ownerKey={ownerKey}
            toast={toast}
            onClaim={() => setEditor({ n: d.number, basement: d.basement, mode: 'claim' })}
            onEdit={() => setEditor({ n: d.number, basement: d.basement, mode: 'edit', initial: d.room })}
            onStairs={takeStairs}
            onResume={() => rideTo(resumeTarget.current ?? 0, { noBreakdown: true })}
            onRefresh={refresh}
            onRide={(x) => (x === 'claim' ? findEmpty() : rideTo(x))}
          />
        </div>
        <Panel
          display={display}
          direction={direction}
          busy={moving}
          onGo={rideTo}
          onDice={dice}
          onLobby={() => rideTo(0)}
          myFloor={myFloor}
          onMyFloor={() => rideTo(Number(myFloor))}
          onScratch={async (body) => {
            const g = await api.scratch(body)
            setGraffiti((list) => [g, ...list].slice(0, 20))
          }}
          claimed={claimed}
        />
      </main>
      <footer className="foot">
        No accounts. No links. Be kind to the neighbours. · <a href="/admin">management</a>
      </footer>
      {editor && (
        <Editor
          {...editor}
          onClose={() => setEditor(null)}
          onSave={async (room) => {
            const { n, mode, basement } = editor
            if (mode === 'claim') {
              const r = await api.claim(n, room)
              saveOwnerKey(n, r.owner_key)
              setEditor(null)
              setKeyModal({ n, ownerKey: r.owner_key, basement })
              setClaimed((c) => (c ? { ...c, claimed: c.claimed + 1 } : c))
            } else {
              await api.update(n, room, keys[n])
              setEditor(null)
              toast('Room saved.')
            }
            refresh()
          }}
        />
      )}
      {keyModal && <KeyModal {...keyModal} onClose={() => setKeyModal(null)} />}
    </div>
  )
}

export default function App() {
  const [route] = useState(parseRoute)
  if (route.admin) return <Admin />
  return <Building initial={route} />
}
