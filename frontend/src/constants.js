import C from '../../shared/constants.json'

export const MIN_FLOOR = C.minFloor
export const MAX_FLOOR = C.maxFloor
export const PALETTE = C.palette
export const WALLPAPERS = C.wallpapers
export const OBJECTS = C.objects
export const LIMITS = C.limits
export const SPECIAL = C.special
export const BREAKDOWN_CHANCE = C.breakdownChance
export const GRID = C.limits.gridSize
export const BLANK = 'c'.repeat(GRID * GRID)

export function windowView(n) {
  if (n <= 0) return null
  for (const b of C.windowBands) if (n <= b.max) return b.view
  return C.windowBands[C.windowBands.length - 1].view
}

export const special = (n) => SPECIAL[String(n)] || null

export function label(n) {
  if (n < 0) return `B${-n}`
  return Number(n).toLocaleString('en-US')
}

export function halfLabel(at) {
  return `${label(at)}½`
}

export function parseLabel(s) {
  if (s == null) return null
  s = String(s).trim().toUpperCase().replace(/,/g, '')
  let m = s.match(/^B(\d{1,3})$/)
  if (m) return -Number(m[1])
  m = s.match(/^-?\d{1,5}$/)
  if (m) return Number(s)
  return null
}

export const urlFor = (n) => `/floor/${n < 0 ? `B${-n}` : n}`

/** Time of day for the window, from the visitor's real clock. */
export function timeOfDay(date = new Date()) {
  const h = date.getHours() + date.getMinutes() / 60
  if (h >= 5 && h < 8) return 'dawn'
  if (h >= 8 && h < 17.5) return 'day'
  if (h >= 17.5 && h < 20.5) return 'dusk'
  return 'night'
}
