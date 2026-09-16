export interface Event {
  id: string
  title: string
  category: string
  date: string
  time: string
  location: string
  capacity: number
  activeCount: number
  description: string
}

export interface Registration {
  id: string
  eventId: string
  name: string
  email: string
  status: 'active' | 'waitlisted' | 'cancelled'
  createdAt: string
}

export type FailureMode = 'none' | 'before' | 'after'
let failureMode: FailureMode = 'none'

export function setFailureMode(mode: FailureMode) {
  failureMode = mode
}

export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  if (init.body) headers.set('Content-Type', 'application/json')
  if (failureMode !== 'none' && !['GET', 'HEAD'].includes(init.method ?? 'GET')) {
    headers.set('X-Demo-Fail', failureMode === 'before' ? '1' : 'after')
  }
  const response = await fetch(`/api${path}`, { ...init, headers })
  const data = await response.json()
  if (!response.ok) {
    throw new Error(typeof data.detail === 'string' ? data.detail : '请检查输入后重试。')
  }
  return data as T
}

export const getEvents = () => request<{ items: Event[] }>('/events')
export const getRegistrations = (id: string) =>
  request<{ items: Registration[] }>(`/events/${id}/registrations`)
export const addRegistration = (id: string, name: string, email: string) =>
  request<Registration>(`/events/${id}/registrations`, {
    method: 'POST', body: JSON.stringify({ name, email }),
  })
export const cancelRegistration = (eventId: string, registrationId: string) =>
  request<Registration>(`/events/${eventId}/registrations/${registrationId}`, {
    method: 'PATCH', body: JSON.stringify({ status: 'cancelled' }),
  })
export const updateEventCapacity = (eventId: string, capacity: number) =>
  request<Event>(`/events/${eventId}`, {
    method: 'PATCH', body: JSON.stringify({ capacity }),
  })
export const resetDemo = () => request<{ ok: boolean }>('/demo/reset', { method: 'POST' })
