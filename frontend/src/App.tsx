import { useEffect, useMemo, useState } from 'react'
import { Header } from './components/Header'
import { StatsCards } from './components/StatsCards'
import { EventStream } from './components/EventStream'
import { WorkersList } from './components/WorkersList'
import { EventsChart } from './components/EventsChart'
import { useWebSocket } from './hooks/useWebSocket'
import type { Stats, WorkerInfo, ChartPoint, WorkerEvent } from './types'

function getWsUrl(): string {
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${proto}//${window.location.host}/ws/events`
}

export default function App() {
  const { status, events, clearEvents } = useWebSocket(getWsUrl())

  // Workers state
  const [workers, setWorkers] = useState<Map<string, WorkerInfo>>(new Map())

  // Process events to update workers and stats
  useEffect(() => {
    if (events.length === 0) return
    const latest = events[0]
    updateWorkersFromEvent(latest)
  }, [events])

  const updateWorkersFromEvent = (event: WorkerEvent) => {
    const wid = event.worker_id
    if (!wid) return

    setWorkers((prev) => {
      const next = new Map(prev)
      const existing = next.get(wid)

      if (event.event === 'worker_joined') {
        next.set(wid, {
          id: wid,
          joinedAt: event.timestamp,
          lastSeen: event.timestamp,
          tasksCompleted: 0,
          tasksFailed: 0,
          tasksRetried: 0,
        })
      } else if (event.event === 'worker_left') {
        next.delete(wid)
      } else if (existing) {
        const updated = { ...existing, lastSeen: event.timestamp }
        if (event.event === 'task_completed') updated.tasksCompleted++
        if (event.event === 'task_failed') updated.tasksFailed++
        if (event.event === 'task_retry') updated.tasksRetried++
        next.set(wid, updated)
      }

      return next
    })
  }

  // Compute stats
  const stats: Stats = useMemo(() => {
    let completed = 0
    let failed = 0
    let retried = 0

    for (const ev of events) {
      if (ev.event === 'task_completed') completed++
      if (ev.event === 'task_failed') failed++
      if (ev.event === 'task_retry') retried++
    }

    return {
      totalEvents: events.length,
      completed,
      failed,
      retried,
      activeWorkers: workers.size,
    }
  }, [events, workers])

  // Chart data (aggregate by minute)
  const chartData: ChartPoint[] = useMemo(() => {
    const buckets = new Map<string, { c: number; f: number; r: number }>()

    for (const ev of events) {
      const d = new Date(ev.timestamp * 1000)
      const key = `${d.getHours()}:${String(d.getMinutes()).padStart(2, '0')}`
      const b = buckets.get(key) || { c: 0, f: 0, r: 0 }
      if (ev.event === 'task_completed') b.c++
      if (ev.event === 'task_failed') b.f++
      if (ev.event === 'task_retry') b.r++
      buckets.set(key, b)
    }

    return Array.from(buckets.entries())
      .map(([time, b]) => ({
        time,
        completed: b.c,
        failed: b.f,
        retried: b.r,
      }))
      .reverse()
  }, [events])

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100">
      <Header status={status} />

      <main className="max-w-7xl mx-auto p-6 space-y-6">
        <StatsCards stats={stats} />

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <EventStream events={events} onClear={clearEvents} />
          <WorkersList workers={Array.from(workers.values())} />
        </div>

        <EventsChart data={chartData} />
      </main>
    </div>
  )
}