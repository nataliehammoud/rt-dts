import type { Stats } from '../types'

interface StatsCardsProps {
  stats: Stats
}

export function StatsCards({ stats }: StatsCardsProps) {
  const cards = [
    { label: 'Active Workers', value: stats.activeWorkers, color: 'text-blue-400', icon: '👷' },
    { label: 'Total Events', value: stats.totalEvents, color: 'text-purple-400', icon: '📡' },
    { label: 'Tasks Completed', value: stats.completed, color: 'text-emerald-400', icon: '✅' },
    { label: 'Tasks Failed', value: stats.failed, color: 'text-red-400', icon: '❌' },
  ]

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map((card) => (
        <div
          key={card.label}
          className="bg-gray-800 rounded-lg p-4 border border-gray-700 hover:border-gray-600 transition-colors"
        >
          <div className="flex items-center justify-between mb-2">
            <div className="text-gray-400 text-sm">{card.label}</div>
            <span className="text-xl">{card.icon}</span>
          </div>
          <div className={`text-3xl font-bold ${card.color}`}>
            {card.value}
          </div>
        </div>
      ))}
    </div>
  )
}