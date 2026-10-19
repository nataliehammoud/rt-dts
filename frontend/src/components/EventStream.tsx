import clsx from 'clsx'
import type { WorkerEvent } from '../types'

interface EventStreamProps {
  events: WorkerEvent[]
  onClear: () => void
}

const EVENT_CONFIG: Record<string, { icon: string; color: string; bg: string }> = {
  worker_joined: { icon: '🟢', color: 'text-green-400', bg: 'bg-green-900/20' },
  worker_left: { icon: '🔴', color: 'text-red-400', bg: 'bg-red-900/20' },
  task_started: { icon: '▶️', color: 'text-blue-400', bg: 'bg-blue-900/20' },
  task_completed: { icon: '✅', color: 'text-emerald-400', bg: 'bg-emerald-900/20' },
  task_retry: { icon: '⚠️', color: 'text-yellow-400', bg: 'bg-yellow-900/20' },
  task_failed: { icon: '❌', color: 'text-red-400', bg: 'bg-red-900/20' },
}

export function EventStream({ events, onClear }: EventStreamProps) {
  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
      <div className="p-4 border-b border-gray-700 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h2 className="font-bold text-lg">📡 Live Events</h2>
          <span className="bg-gray-700 text-xs px-2 py-1 rounded">
            {events.length}
          </span>
        </div>
        <button
          onClick={onClear}
          className="text-xs text-gray-400 hover:text-white bg-gray-700 hover:bg-gray-600 px-3 py-1 rounded transition-colors"
        >
          Clear
        </button>
      </div>
      <div className="p-4 h-[500px] overflow-y-auto space-y-2">
        {events.length === 0 ? (
          <div className="text-gray-500 text-center py-8">
            Waiting for events...
          </div>
        ) : (
          events.map((ev, idx) => {
            const cfg = EVENT_CONFIG[ev.event] || {
              icon: 'ℹ️',
              color: 'text-gray-400',
              bg: 'bg-gray-900/20',
            }
            const time = new Date(ev.timestamp * 1000).toLocaleTimeString()
            return (
              <div
                key={`${ev.timestamp}-${idx}`}
                className={clsx(
                  'rounded p-2 text-sm border border-gray-700 animate-[slideIn_0.3s_ease-out]',
                  cfg.bg
                )}
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span>{cfg.icon}</span>
                    <span className={clsx('font-mono text-xs', cfg.color)}>
                      {ev.event}
                    </span>
                    {ev.worker_id && (
                      <span className="text-gray-500 text-xs">
                        [{ev.worker_id}]
                      </span>
                    )}
                    {ev.task_name && (
                      <span className="text-gray-300">{ev.task_name}</span>
                    )}
                    {ev.attempt && (
                      <span className="text-yellow-400 text-xs">
                        (attempt {ev.attempt})
                      </span>
                    )}
                  </div>
                  <span className="text-gray-500 text-xs whitespace-nowrap">
                    {time}
                  </span>
                </div>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}