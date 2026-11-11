// All sounds are synthesised with WebAudio, so there are no audio files to ship.

let ctx = null
let hum = null
let musicTimer = null
let musicStep = 0
let nextNoteTime = 0

const pref = (k, d) => (localStorage.getItem(k) ?? d) === 'on'
export const settings = {
  sound: pref('elevator.sound', 'on'),
  music: pref('elevator.music', 'off'),
}

function ac() {
  if (!ctx) {
    const AC = window.AudioContext || window.webkitAudioContext
    if (!AC) return null
    ctx = new AC()
  }
  if (ctx.state === 'suspended') ctx.resume().catch(() => {})
  return ctx
}

function tone(freq, start, dur, { type = 'sine', gain = 0.2, dest } = {}) {
  const c = ac()
  if (!c) return
  const o = c.createOscillator()
  const g = c.createGain()
  o.type = type
  o.frequency.value = freq
  g.gain.setValueAtTime(0, start)
  g.gain.linearRampToValueAtTime(gain, start + 0.01)
  g.gain.exponentialRampToValueAtTime(0.0001, start + dur)
  o.connect(g).connect(dest || c.destination)
  o.start(start)
  o.stop(start + dur + 0.05)
}

function noise(dur, { freq = 800, gain = 0.15, start } = {}) {
  const c = ac()
  if (!c) return
  const t = start ?? c.currentTime
  const buf = c.createBuffer(1, Math.ceil(c.sampleRate * dur), c.sampleRate)
  const d = buf.getChannelData(0)
  for (let i = 0; i < d.length; i++) d[i] = (Math.random() * 2 - 1) * (1 - i / d.length)
  const src = c.createBufferSource()
  src.buffer = buf
  const f = c.createBiquadFilter()
  f.type = 'lowpass'
  f.frequency.value = freq
  const g = c.createGain()
  g.gain.value = gain
  src.connect(f).connect(g).connect(c.destination)
  src.start(t)
}

export const sound = {
  /** The arrival chime. `echo` for empty floors, which sound hollow. */
  ding(echo = false) {
    if (!settings.sound) return
    const c = ac()
    if (!c) return
    const t = c.currentTime + 0.02
    let dest = c.destination
    if (echo) {
      const delay = c.createDelay()
      delay.delayTime.value = 0.28
      const fb = c.createGain()
      fb.gain.value = 0.55
      delay.connect(fb).connect(delay)
      const mix = c.createGain()
      delay.connect(c.destination)
      mix.connect(c.destination)
      mix.connect(delay)
      dest = mix
    }
    tone(1318.5, t, 1.4, { gain: 0.18, dest })
    tone(1046.5, t + 0.32, 1.8, { gain: 0.16, dest })
  },
  doors() {
    if (settings.sound) noise(0.7, { freq: 500, gain: 0.12 })
  },
  steps() {
    if (!settings.sound) return
    const c = ac()
    if (!c) return
    for (let i = 0; i < 6; i++) noise(0.08, { freq: 300, gain: 0.25, start: c.currentTime + i * 0.13 })
  },
  clunk() {
    if (!settings.sound) return
    const c = ac()
    if (!c) return
    const o = c.createOscillator()
    const g = c.createGain()
    o.frequency.setValueAtTime(90, c.currentTime)
    o.frequency.exponentialRampToValueAtTime(30, c.currentTime + 0.4)
    g.gain.setValueAtTime(0.5, c.currentTime)
    g.gain.exponentialRampToValueAtTime(0.001, c.currentTime + 0.5)
    o.connect(g).connect(c.destination)
    o.start()
    o.stop(c.currentTime + 0.6)
    noise(0.4, { freq: 1200, gain: 0.2 })
  },
  humStart() {
    if (!settings.sound || hum) return
    const c = ac()
    if (!c) return
    const g = c.createGain()
    g.gain.setValueAtTime(0, c.currentTime)
    g.gain.linearRampToValueAtTime(0.06, c.currentTime + 0.4)
    const a = c.createOscillator()
    const b = c.createOscillator()
    a.type = 'sawtooth'
    a.frequency.value = 55
    b.type = 'sine'
    b.frequency.value = 110.5
    const f = c.createBiquadFilter()
    f.type = 'lowpass'
    f.frequency.value = 220
    a.connect(f)
    b.connect(f)
    f.connect(g).connect(c.destination)
    a.start()
    b.start()
    hum = { g, a, b }
  },
  humStop() {
    if (!hum || !ctx) return
    const { g, a, b } = hum
    hum = null
    g.gain.cancelScheduledValues(ctx.currentTime)
    g.gain.setValueAtTime(g.gain.value, ctx.currentTime)
    g.gain.linearRampToValueAtTime(0, ctx.currentTime + 0.3)
    a.stop(ctx.currentTime + 0.35)
    b.stop(ctx.currentTime + 0.35)
  },
}

// ---- elevator music: a slow, slightly cheesy loop of seventh chords.
const CHORDS = [
  [174.6, 220.0, 261.6, 329.6], // Fmaj7
  [164.8, 196.0, 246.9, 293.7], // Em7
  [146.8, 174.6, 220.0, 261.6], // Dm7
  [130.8, 164.8, 196.0, 246.9], // Cmaj7
]
const PATTERN = [0, 2, 1, 3, 2, 1, 3, 2]
const STEP = 0.32

function scheduleMusic() {
  const c = ac()
  if (!c) return
  while (nextNoteTime < c.currentTime + 0.6) {
    const chord = CHORDS[Math.floor(musicStep / 8) % CHORDS.length]
    const i = musicStep % 8
    tone(chord[PATTERN[i]] * 2, nextNoteTime, STEP * 2.2, { type: 'triangle', gain: 0.035 })
    if (i === 0) tone(chord[0] / 2, nextNoteTime, STEP * 7, { type: 'sine', gain: 0.06 })
    if (i === 4 && Math.random() < 0.5) tone(chord[3] * 4, nextNoteTime, STEP * 1.5, { gain: 0.02 })
    nextNoteTime += STEP
    musicStep++
  }
}

export function setMusic(on) {
  settings.music = on
  localStorage.setItem('elevator.music', on ? 'on' : 'off')
  if (on && !musicTimer) {
    const c = ac()
    if (!c) return
    nextNoteTime = c.currentTime + 0.1
    musicTimer = setInterval(scheduleMusic, 150)
  } else if (!on && musicTimer) {
    clearInterval(musicTimer)
    musicTimer = null
  }
}

export function setSound(on) {
  settings.sound = on
  localStorage.setItem('elevator.sound', on ? 'on' : 'off')
  if (!on) sound.humStop()
}
