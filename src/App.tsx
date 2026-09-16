import { useCallback, useEffect, useState, type FormEvent } from 'react'
import {
  addRegistration, cancelRegistration, getEvents, getRegistrations, resetDemo,
  setFailureMode, updateEventCapacity,
  type Event, type FailureMode, type Registration,
} from './api'

const errorMessage = (error: unknown) => error instanceof Error ? error.message : '请求失败，请重试。'

export default function App() {
  const [events, setEvents] = useState<Event[]>([])
  const [selectedId, setSelectedId] = useState('e1')
  const [registrations, setRegistrations] = useState<Registration[]>([])
  const [registrationsEventId, setRegistrationsEventId] = useState('')
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [capacityInput, setCapacityInput] = useState('')
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [failureMode, updateFailureMode] = useState<FailureMode>('none')
  const [reloadKey, setReloadKey] = useState(0)
  const event = events.find((item) => item.id === selectedId)
  const refresh = useCallback(() => setReloadKey((key) => key + 1), [])
  const registrationStats = registrations.reduce((counts, registration) => {
    counts[registration.status] += 1
    return counts
  }, { active: 0, waitlisted: 0, cancelled: 0 })
  const rosterReady = registrationsEventId === selectedId
  const activeCount = rosterReady ? registrationStats.active : null
  const waitlistedCount = rosterReady ? registrationStats.waitlisted : null
  const cancelledCount = rosterReady ? registrationStats.cancelled : null
  const remainingCount = event && activeCount !== null
    ? Math.max(event.capacity - activeCount, 0)
    : null
  const waitlistPositions = new Map<string, number>()
  let waitlistPosition = 0
  registrations.forEach((registration) => {
    if (registration.status === 'waitlisted') {
      waitlistPosition += 1
      waitlistPositions.set(registration.id, waitlistPosition)
    }
  })

  useEffect(() => {
    let active = true
    setLoading(true)
    Promise.all([getEvents(), getRegistrations(selectedId)])
      .then(([eventData, registrationData]) => {
        if (!active) return
        setEvents(eventData.items)
        setRegistrations(registrationData.items)
        setRegistrationsEventId(selectedId)
        const selectedEvent = eventData.items.find((item) => item.id === selectedId)
        setCapacityInput(selectedEvent ? String(selectedEvent.capacity) : '')
      })
      .catch((reason: unknown) => { if (active) setError(errorMessage(reason)) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [selectedId, reloadKey])

  async function submitRegistration(submitEvent: FormEvent) {
    submitEvent.preventDefault()
    setBusy(true)
    setError('')
    setNotice('')
    try {
      const registration = await addRegistration(selectedId, name.trim(), email.trim())
      setName('')
      setEmail('')
      setNotice(registration.status === 'waitlisted'
        ? '活动已满，已加入候补。'
        : '报名已确认。')
      refresh()
    } catch (reason) {
      setError(errorMessage(reason))
      refresh()
    } finally {
      setBusy(false)
    }
  }

  async function cancel(registration: Registration) {
    setBusy(true)
    setError('')
    setNotice('')
    try {
      await cancelRegistration(selectedId, registration.id)
      setNotice(registration.status === 'active'
        ? '退出已保存；如有候补，系统已自动补位。'
        : '候补已退出。')
      refresh()
    } catch (reason) {
      setError(errorMessage(reason))
      refresh()
    } finally {
      setBusy(false)
    }
  }

  async function saveCapacity(submitEvent: FormEvent) {
    submitEvent.preventDefault()
    const capacity = Number(capacityInput)
    if (!Number.isInteger(capacity) || capacity < 0) {
      setError('活动名额必须是非负整数。')
      return
    }
    setBusy(true)
    setError('')
    setNotice('')
    try {
      await updateEventCapacity(selectedId, capacity)
      setNotice('活动名额已更新，候补补位结果已同步。')
      refresh()
    } catch (reason) {
      setError(errorMessage(reason))
      refresh()
    } finally {
      setBusy(false)
    }
  }

  async function reset() {
    setBusy(true)
    setError('')
    setNotice('')
    try {
      await resetDemo()
      refresh()
      setNotice('已恢复初始演示数据。')
    } catch (reason) {
      setError(errorMessage(reason))
      refresh()
    } finally {
      setBusy(false)
    }
  }

  function selectEvent(id: string) {
    setSelectedId(id)
    setError('')
    setNotice('')
    setName('')
    setEmail('')
    setRegistrations([])
    setRegistrationsEventId('')
    const selectedEvent = events.find((item) => item.id === id)
    setCapacityInput(selectedEvent ? String(selectedEvent.capacity) : '')
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="Gather 首页"><span className="brand-mark">g</span>gather<span className="brand-dot">.</span></a>
        <span className="workspace-name">社区活动工作台</span>
        <span className="local-badge"><i />本地演示</span>
      </header>

      <main>
        <section className="page-heading">
          <div><p className="eyebrow">GOOD THINGS HAPPEN TOGETHER</p><h1>让每一次相聚，都有条不紊。</h1><p className="intro">活动、名额与报名名单，在一个地方管理。</p></div>
          <div className="edition">WORKSHOP<br /><strong>01 / GATHER</strong></div>
        </section>

        <div className="workspace-grid">
          <aside className="events-panel" aria-label="活动列表">
            <div className="section-label"><h2>近期活动</h2><span>{events.length.toString().padStart(2, '0')}</span></div>
            {events.map((item, index) => (
              <button key={item.id} className={`event-card ${selectedId === item.id ? 'selected' : ''}`} disabled={busy}
                onClick={() => selectEvent(item.id)} aria-pressed={selectedId === item.id}>
                <div className="event-card-top"><span className={`category category-${index}`}>{item.category}</span><span className="card-arrow">↗</span></div>
                <h3>{item.title}</h3><p>{item.date} · {item.time}</p>
                <div className="event-card-bottom"><span>{item.location}</span><strong>{item.id === selectedId ? (activeCount ?? '…') : item.activeCount}<span> / {item.capacity} 人</span></strong></div>
              </button>
            ))}
            <div className="sidebar-note"><span>✳</span><p>小小的活动，<br />让社区更有温度。</p></div>
          </aside>

          <section className="detail-panel" aria-label="报名管理" aria-busy={loading}>
            <div className="detail-heading"><div><p className="eyebrow">REGISTRATION DESK</p><h2>{event?.title ?? '加载活动…'}</h2><p>{event?.description ?? '正在获取活动信息。'}</p></div><span className="detail-symbol">✳</span></div>
            <div className="stats-row">
              <div><span>已报名</span><strong data-testid="active-count">{activeCount ?? '—'}<small> 人</small></strong></div>
              <div><span>候补</span><strong>{waitlistedCount ?? '—'}<small> 人</small></strong></div>
              <div><span>已退出</span><strong>{cancelledCount ?? '—'}<small> 人</small></strong></div>
              <div><span>剩余名额</span><strong>{remainingCount ?? '—'}<small> 席</small></strong></div>
              <div><span>活动地点</span><strong className="location-stat">{event?.location ?? '—'}</strong></div>
            </div>

            {error && <div className="message error" role="alert">{error}</div>}
            {notice && <div className="message success" role="status">{notice}</div>}

            <section className="capacity-control">
              <div><h3>活动名额</h3><p>提交总名额；增加后系统会依候补顺序自动补位。</p></div>
              <form onSubmit={saveCapacity}>
                <label>总名额<input name="capacity" type="number" min="0" step="1" value={capacityInput}
                  onChange={(changeEvent) => setCapacityInput(changeEvent.target.value)} required disabled={busy || loading || !event} /></label>
                <button className="secondary-button" type="submit" disabled={busy || loading || !event}>保存名额</button>
              </form>
            </section>

            <section className="registration-form">
              <div className="form-heading"><h3>添加报名</h3><span>为新的参与者留一个位置</span></div>
              <form onSubmit={submitRegistration}>
                <label>姓名<input name="name" value={name} onChange={(e) => setName(e.target.value)} placeholder="例如：林舟" required maxLength={60} disabled={busy || loading} /></label>
                <label>邮箱<input name="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="例如：lin@example.test" required maxLength={160} disabled={busy || loading} /></label>
                <button className="primary-button" type="submit" disabled={busy || loading}>{busy ? '保存中…' : '添加报名'}<span>＋</span></button>
              </form>
            </section>

            <section className="roster">
              <div className="roster-heading"><h3>全部记录 <span>{loading ? '…' : registrations.length}</span></h3><button className="text-button" disabled={loading || busy} onClick={refresh}>刷新列表 ↻</button></div>
              <div className="table-scroll"><table><thead><tr><th>参与者</th><th>联系邮箱</th><th>状态</th><th>操作</th></tr></thead>
                <tbody>{!loading && registrations.map((registration, index) => (
                  <tr key={registration.id} data-testid={`registration-${registration.id}`}>
                    <td><span className={`avatar avatar-${index % 3}`}>{registration.name.slice(0, 1)}</span><strong>{registration.name}</strong></td>
                    <td className="email-cell">{registration.email}</td>
                    <td><span className={`status ${registration.status}`}>{registration.status === 'active' ? '已报名' : registration.status === 'waitlisted' ? '候补' : '已退出'}</span>
                      {registration.status === 'waitlisted' && <small className="waitlist-position">候补第 {waitlistPositions.get(registration.id)} 位</small>}</td>
                    <td>{registration.status !== 'cancelled' && <button className="exit-button" type="button" disabled={busy || loading}
                      onClick={() => cancel(registration)} aria-label={`退出 ${registration.name}`}>退出</button>}</td>
                  </tr>
                ))}</tbody></table></div>
              {loading && <p className="empty-state">正在加载名单…</p>}
              {!loading && registrations.length === 0 && <p className="empty-state">还没有报名或候补记录，添加第一位参与者吧。</p>}
            </section>
            <div className="detail-footer"><span className="tiny-dot" />数据保存在本地服务内存中，重启后恢复初始状态。</div>
          </section>
        </div>

        <details className="demo-tools"><summary>演示工具</summary><div>
          <label className="failure-control">故障模式<select value={failureMode} onChange={(e) => {
            const mode = e.target.value as FailureMode
            updateFailureMode(mode)
            setFailureMode(mode)
          }}>
            <option value="none">正常请求</option>
            <option value="before">写入前失败（数据不变）</option>
            <option value="after">写入后响应丢失（数据可能已变）</option>
          </select></label>
          <button className="text-button" onClick={reset} disabled={busy || loading}>恢复演示数据</button>
          <p>两种故障都会返回 503，读取不受影响。重试或恢复数据前请切回正常请求。所有人物、邮箱和活动均为虚构。</p>
        </div></details>
      </main>
      <footer className="page-footer"><span>GATHER / A SMALL COMMUNITY WORKSPACE</span><span>虚构场景 · 本地运行 · 无外部服务</span></footer>
    </div>
  )
}
