import type { WorkerInfo } from '../types'

interface WorkersListProps {
  workers: WorkerInfo[]
}

function formatUptime(seconds: number): string {
  if (seconds < 60) return `${Math.floor(seconds)}s`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`
  return `${Math.floor(seconds / 3600)}h`
}

export function WorkersList({ workers }: WorkersListProps) {
  const now = Date.now() / 1000

  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
      <div className="p-4 border-b border-gray-700 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h2 className="font-bold text-lg">👷 Workers</h2>
          <span className="bg-gray-700 text-xs px-2 py-1 rounded">
            {workers.length}
          </span>
        </div>
      </div>
      <div className="p-4 h-[500px] overflow-y-auto space-y-2">
        {workers.length === 0 ? (
          <div className="text-gray-500 text-center py-8">
            No workers connected
          </div>
        ) : (
          workers.map((w) => {
            const uptime = now - w.joinedAt
            const isLeader = false // يمكننا تحديدها لاحقاً
            return (
              <div
                key={w.id}
                className="bg-gray-900 rounded p-3 border border-gray-700"
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-sm text-blue-400">
                      {w.id}
                    </span>
                    {isLeader && (
                      <span className="text-xs">👑</span>
                    )}
                  </div>
                  <span className="w-2 h-2 rounded-full bg-green-500" />
                </div>
                <div className="grid grid-cols-4 gap-2 text-xs">
                  <div>
                    <div className="text-gray-500">Uptime</div>
                    <div className="text-gray-300">{formatUptime(uptime)}</div>
                  </div>
                  <div>
                    <div className="text-gray-500">✅ Done</div>
                    <div className="text-emerald-400">
                      {w.tasksCompleted}
                    </div>
                  </div>
                  <div>
                    <div className="text-gray-500">❌ Fail</div>
                    <div className="text-red-400">{w.tasksFailed}</div>
                  </div>
                  <div>
                    <div className="text-gray-500">⚠️ Retry</div>
                    <div className="text-yellow-400">
                      {w.tasksRetried}
                    </div>
                  </div>
                </div>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}