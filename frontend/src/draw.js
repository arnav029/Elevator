import { GRID, PALETTE } from './constants'

export function drawPixels(canvas, pixels) {
  canvas.width = GRID
  canvas.height = GRID
  const g = canvas.getContext('2d')
  for (let i = 0; i < GRID * GRID; i++) {
    g.fillStyle = PALETTE[parseInt(pixels[i] || 'c', 16)]
    g.fillRect(i % GRID, Math.floor(i / GRID), 1, 1)
  }
}

export function drawSprite(canvas, rows) {
  const w = Math.max(...rows.map((r) => r.length))
  canvas.width = w
  canvas.height = rows.length
  const g = canvas.getContext('2d')
  g.clearRect(0, 0, w, rows.length)
  rows.forEach((row, y) => {
    for (let x = 0; x < row.length; x++) {
      const ch = row[x]
      if (ch === '.' || ch === ' ') continue
      g.fillStyle = PALETTE[parseInt(ch, 16)]
      g.fillRect(x, y, 1, 1)
    }
  })
}

// ------------------------------------------------------------------ the window

function rng(seed) {
  let s = (seed * 2654435761) >>> 0 || 1
  return () => {
    s ^= s << 13
    s ^= s >>> 17
    s ^= s << 5
    return ((s >>> 0) % 100000) / 100000
  }
}

const SKY = {
  dawn: ['#f7b27a', '#9fc2e6'],
  day: ['#6fb8ea', '#cfeaf8'],
  dusk: ['#3c2f6b', '#e0705a'],
  night: ['#070a22', '#1e2a5a'],
}

function sky(g, w, h, top, bottom) {
  const grad = g.createLinearGradient(0, 0, 0, h)
  grad.addColorStop(0, top)
  grad.addColorStop(1, bottom)
  g.fillStyle = grad
  g.fillRect(0, 0, w, h)
}

function stars(g, w, h, r, count, color = '#f4f4f4') {
  for (let i = 0; i < count; i++) {
    g.fillStyle = r() < 0.15 ? '#ffcd75' : color
    g.fillRect(Math.floor(r() * w), Math.floor(r() * h), 1, 1)
  }
}

function sunOrMoon(g, tod, w) {
  if (tod === 'night') {
    g.fillStyle = '#f4f4f4'
    g.beginPath()
    g.arc(w - 10, 8, 4, 0, Math.PI * 2)
    g.fill()
    g.fillStyle = '#1a2250'
    g.beginPath()
    g.arc(w - 8, 7, 3.5, 0, Math.PI * 2)
    g.fill()
  } else {
    g.fillStyle = tod === 'day' ? '#fff3b0' : '#ffcd75'
    g.beginPath()
    g.arc(w - 11, tod === 'day' ? 8 : 24, 5, 0, Math.PI * 2)
    g.fill()
  }
}

function cloud(g, x, y, s, color) {
  g.fillStyle = color
  g.fillRect(x, y, 10 * s, 3 * s)
  g.fillRect(x + 2 * s, y - 2 * s, 5 * s, 2 * s)
  g.fillRect(x + 5 * s, y - 3 * s, 3 * s, 1 * s)
}

function buildings(g, w, h, r, { base, minH, maxH, color, lit, night }) {
  let x = -2
  while (x < w) {
    const bw = 4 + Math.floor(r() * 7)
    const bh = minH + Math.floor(r() * (maxH - minH))
    g.fillStyle = color
    g.fillRect(x, base - bh, bw, bh)
    for (let wy = base - bh + 2; wy < base - 1; wy += 3) {
      for (let wx = x + 1; wx < x + bw - 1; wx += 2) {
        if (r() < (night ? 0.45 : 0.15)) {
          g.fillStyle = night ? lit : '#94b0c2'
          g.fillRect(wx, wy, 1, 1)
        }
      }
    }
    x += bw + (r() < 0.3 ? 1 : 0)
  }
}

/**
 * Draws the room window on a small canvas (scaled up with pixelated rendering).
 * `t` is time in seconds, used for drifting clouds and passing cars.
 */
export function drawWindow(canvas, { view, tod, floor, t = 0 }) {
  const w = 48
  const h = 40
  canvas.width = w
  canvas.height = h
  const g = canvas.getContext('2d')
  const night = tod === 'night'
  const r = rng(Math.abs(floor) + 7)

  if (view === 'stars') {
    sky(g, w, h, '#000004', '#0b0f2a')
    stars(g, w, h, r, 70)
    if (floor % 3 === 0) {
      g.fillStyle = '#ef7d57'
      g.beginPath()
      g.arc(12, 28, 4, 0, Math.PI * 2)
      g.fill()
    }
    return
  }
  if (view === 'thin') {
    sky(g, w, h, '#03051a', night ? '#101a48' : '#2b4aa0')
    stars(g, w, h * 0.7, r, night ? 40 : 18)
    g.fillStyle = night ? '#1b2a66' : '#73b6f0'
    g.beginPath()
    g.ellipse(w / 2, h + 40, 70, 48, 0, 0, Math.PI * 2)
    g.fill()
    g.fillStyle = night ? '#29366f' : '#cfeaf8'
    g.beginPath()
    g.ellipse(w / 2, h + 42, 68, 46, 0, 0, Math.PI * 2)
    g.fill()
    return
  }

  sky(g, w, h, ...SKY[tod])
  if (night) stars(g, w, h * 0.6, r, 20)
  sunOrMoon(g, tod, w)

  if (view === 'clouds') {
    const cloudColor = night ? '#566c86' : tod === 'dusk' ? '#f0b8a0' : '#f4f4f4'
    for (let i = 0; i < 6; i++) {
      const cx = ((r() * 80 + t * (1.5 + i * 0.4)) % 80) - 20
      cloud(g, Math.floor(cx), Math.floor(6 + r() * 30), 1 + (i % 2), cloudColor)
    }
    g.fillStyle = night ? '#94b0c2' : '#ffffff'
    g.globalAlpha = 0.5
    g.fillRect(0, h - 6, w, 6)
    g.globalAlpha = 1
    return
  }
  if (view === 'skyline') {
    buildings(g, w, h, r, { base: h, minH: 8, maxH: 24, color: night ? '#0e1230' : '#566c86', lit: '#ffcd75', night })
    buildings(g, w, h, r, { base: h, minH: 3, maxH: 12, color: night ? '#1a1c2c' : '#333c57', lit: '#ffcd75', night })
    cloud(g, Math.floor((t * 2) % 70) - 15, 10, 1, night ? '#29366f' : '#ffffffcc')
    return
  }
  // street level: the building across the road, the pavement, cars going by.
  g.fillStyle = night ? '#2a1d22' : '#b13e53'
  g.fillRect(0, 4, w, h)
  for (let y = 7; y < h - 12; y += 6) {
    for (let x = 3; x < w; x += 7) {
      g.fillStyle = night && r() < 0.6 ? '#ffcd75' : '#29366f'
      g.fillRect(x, y, 4, 4)
    }
  }
  g.fillStyle = '#94b0c2'
  g.fillRect(0, h - 10, w, 3)
  g.fillStyle = '#333c57'
  g.fillRect(0, h - 7, w, 7)
  g.fillStyle = '#f4f4f4'
  for (let x = 0; x < w; x += 8) g.fillRect(x, h - 4, 4, 1)
  const carX = Math.floor(((t * 14) % (w + 40)) - 20)
  g.fillStyle = '#41a6f6'
  g.fillRect(carX, h - 7, 9, 3)
  g.fillRect(carX + 2, h - 9, 5, 2)
  g.fillStyle = night ? '#ffcd75' : '#1a1c2c'
  g.fillRect(carX + 9, h - 6, 1, 1)
  g.fillStyle = '#38b764'
  g.fillRect(36, h - 18, 6, 6)
  g.fillStyle = '#8a5a3c'
  g.fillRect(38, h - 12, 2, 3)
}
