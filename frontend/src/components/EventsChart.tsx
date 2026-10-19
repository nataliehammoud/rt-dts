import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import type { ChartPoint } from '../types'

interface EventsChartProps {
  data: ChartPoint[]
}

export function EventsChart({ data }: EventsChartProps) {
  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
      <h2 className="font-bold text-lg mb-4">📈 Events Over Time</h2>
      <div className="h-[300px]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis
              dataKey="time"
              stroke="#9ca3af"
              style={{ fontSize: '12px' }}
            />
            <YAxis stroke="#9ca3af" style={{ fontSize: '12px' }} />
            <Tooltip
              contentStyle={{
                backgroundColor: '#1f2937',
                border: '1px solid #374151',
                borderRadius: '8px',
              }}
              labelStyle={{ color: '#f3f4f6' }}
            />
            <Legend />
            <Line
              type="monotone"
              dataKey="completed"
              stroke="#34d399"
              strokeWidth={2}
              dot={false}
              name="Completed"
            />
            <Line
              type="monotone"
              dataKey="failed"
              stroke="#ef4444"
              strokeWidth={2}
              dot={false}
              name="Failed"
            />
            <Line
              type="monotone"
              dataKey="retried"
              stroke="#fbbf24"
              strokeWidth={2}
              dot={false}
              name="Retried"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}