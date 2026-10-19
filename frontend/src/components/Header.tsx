import clsx from 'clsx'

interface HeaderProps {
  status: 'connecting' | 'connected' | 'disconnected'
}

export function Header({ status }: HeaderProps) {
  const statusConfig = {
    connecting: {
      dot: 'bg-yellow-500 animate-pulse',
      text: 'Connecting...',
      color: 'text-yellow-400',
    },
    connected: {
      dot: 'bg-green-500 animate-pulse',
      text: 'Connected',
      color: 'text-green-400',
    },
    disconnected: {
      dot: 'bg-red-500',
      text: 'Disconnected',
      color: 'text-red-400',
    },
  }

  const cfg = statusConfig[status]

  return (
    <header className="bg-gray-800 border-b border-gray-700 p-4">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-2xl">🖥️</span>
          <h1 className="text-2xl font-bold">RT-DTS Dashboard</h1>
        </div>
        <div className="flex items-center gap-3">
          <span className={clsx('w-3 h-3 rounded-full', cfg.dot)} />
          <span className={clsx('text-sm font-medium', cfg.color)}>
            {cfg.text}
          </span>
        </div>
      </div>
    </header>
  )
}