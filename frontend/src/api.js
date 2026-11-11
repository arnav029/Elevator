const DEVICE = 'elevator.device'
const KEYS = 'elevator.keys'

function randomId() {
  if (globalThis.crypto?.randomUUID) return crypto.randomUUID().replace(/-/g, '')
  return Array.from({ length: 32 }, () => Math.floor(Math.random() * 16).toString(16)).join('')
}

export function deviceId() {
  let d = localStorage.getItem(DEVICE)
  if (!d) {
    d = randomId()
    localStorage.setItem(DEVICE, d)
  }
  return d
}

export function ownerKeys() {
  try {
    return JSON.parse(localStorage.getItem(KEYS) || '{}')
  } catch {
    return {}
  }
}

export function saveOwnerKey(n, key) {
  localStorage.setItem(KEYS, JSON.stringify({ ...ownerKeys(), [n]: key }))
}

export function forgetOwnerKey(n) {
  const k = ownerKeys()
  delete k[n]
  localStorage.setItem(KEYS, JSON.stringify(k))
}

export class ApiError extends Error {
  constructor(status, message) {
    super(message)
    this.status = status
  }
}

async function req(method, path, body, headers = {}) {
  const res = await fetch(path, {
    method,
    headers: {
      'X-Device-Id': deviceId(),
      ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}),
      ...headers,
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
  let data = null
  try {
    data = await res.json()
  } catch {
    /* empty body */
  }
  if (!res.ok) {
    let msg = data?.detail
    if (Array.isArray(msg)) msg = 'Something in that form is not quite right.'
    throw new ApiError(res.status, msg || `Request failed (${res.status})`)
  }
  return data
}

const ownerHeader = (key) => (key ? { 'X-Owner-Key': key } : {})

export const api = {
  floor: (n, { visit = false, key } = {}) =>
    req('GET', `/api/floors/${n}${visit ? '?visit=1' : ''}`, undefined, ownerHeader(key)),
  random: (exclude, basement = false) => {
    const q = new URLSearchParams()
    if (exclude != null) q.set('exclude', exclude)
    if (basement) q.set('basement', 'true')
    return req('GET', `/api/floors/random?${q}`)
  },
  claim: (n, room) => req('POST', `/api/floors/${n}/claim`, room),
  update: (n, room, key) => req('PUT', `/api/floors/${n}`, room, ownerHeader(key)),
  owner: (n, key) => req('GET', `/api/floors/${n}/owner`, undefined, ownerHeader(key)),
  vacate: (n, key) => req('DELETE', `/api/floors/${n}`, undefined, ownerHeader(key)),
  note: (n, body) => req('POST', `/api/floors/${n}/notes`, { body }),
  deleteNote: (n, id, key) => req('DELETE', `/api/floors/${n}/notes/${id}`, undefined, ownerHeader(key)),
  lobby: () => req('GET', '/api/lobby'),
  graffiti: () => req('GET', '/api/graffiti'),
  scratch: (body) => req('POST', '/api/graffiti', { body }),
  report: (target_type, target_id, reason = '') => req('POST', '/api/reports', { target_type, target_id, reason }),
  halfFloor: (from, to) => req('GET', `/api/half-floors/pick?from=${Math.floor(from)}&to=${Math.floor(to)}`),
  admin: (method, path, token, body) => req(method, `/api/admin${path}`, body, { 'X-Admin-Token': token }),
}
