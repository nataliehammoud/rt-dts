export type EventType =
  | 'worker_joined'
  | 'worker_left'
  | 'task_started'
  | 'task_completed'
  | 'task_retry'
  | 'task_failed'

export interface WorkerEvent {
  event: EventType
  worker_id: string
  timestamp: number
  task_id?: string
  task_name?: string
  attempt?: number
  error?: string
  duration?: number
  tasks_completed?: number
  tasks_failed?: number
  tasks_retried?: number
}

export interface WebSocketMessage {
  type: 'welcome' | 'event'
  data: any
}

export interface WorkerInfo {
  id: string
  joinedAt: number
  lastSeen: number
  tasksCompleted: number
  tasksFailed: number
  tasksRetried: number
}

export interface Stats {
  totalEvents: number
  completed: number
  failed: number
  retried: number
  activeWorkers: number
}

export interface ChartPoint {
  time: string
  completed: number
  failed: number
  retried: number
}