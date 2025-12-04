import { useEffect, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { api } from '@/services/api'
import { formatRelativeTime } from '@/lib/utils'
import {
  Server,
  Play,
  Square,
  RefreshCw,
  Container,
  AlertCircle,
  Cpu,
  HardDrive,
  Database,
  Wifi,
  WifiOff,
  Trash2,
  ChevronDown,
  ChevronRight,
} from 'lucide-react'

interface ServiceInfo {
  name: string
  status: 'running' | 'stopped' | 'starting' | 'error' | 'unknown'
  container_id?: string
  image?: string
  uptime?: string
  ports: string[]
  memory_mb?: number
  cpu_percent?: number
}

interface Worker {
  worker_id: string
  hostname: string
  ip_address?: string
  platform: string
  last_heartbeat: string
  is_online: boolean
  services: ServiceInfo[]
  docker_available: boolean
  cpu_percent?: number
  memory_percent?: number
  total_files: number
  imported_files: number
  total_messages: number
  qdrant_connected: boolean
  qdrant_collections: number
  qdrant_vectors: number
  embedding_mode?: string
  agent_version: string
}

interface WorkersSummary {
  total_workers: number
  online_workers: number
  offline_workers: number
  total_services_running: number
  total_vectors: number
  total_messages: number
}

interface WorkersResponse {
  workers: Worker[]
  summary: WorkersSummary
}

export function Workers() {
  const [workers, setWorkers] = useState<Worker[]>([])
  const [summary, setSummary] = useState<WorkersSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [expandedWorkers, setExpandedWorkers] = useState<Set<string>>(new Set())
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null)

  useEffect(() => {
    loadWorkers()
    const interval = setInterval(loadWorkers, 10000) // Refresh every 10s
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => setToast(null), 3000)
      return () => clearTimeout(timer)
    }
  }, [toast])

  async function loadWorkers() {
    try {
      const data = await api.listWorkers() as WorkersResponse
      setWorkers(data.workers || [])
      setSummary(data.summary || null)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load workers')
      console.error('Failed to load workers:', err)
    } finally {
      setLoading(false)
    }
  }

  function toggleWorkerExpand(workerId: string) {
    setExpandedWorkers(prev => {
      const next = new Set(prev)
      if (next.has(workerId)) {
        next.delete(workerId)
      } else {
        next.add(workerId)
      }
      return next
    })
  }

  async function handleRemoveWorker(workerId: string) {
    if (!confirm(`Remove worker "${workerId}" from the registry?`)) return

    try {
      await api.removeWorker(workerId)
      setToast({ message: `Worker "${workerId}" removed`, type: 'success' })
      await loadWorkers()
    } catch (err) {
      setToast({ message: 'Failed to remove worker', type: 'error' })
    }
  }

  async function handleStartService(workerId: string, serviceName: string) {
    try {
      await api.startWorkerService(workerId, serviceName)
      setToast({ message: `Starting ${serviceName}...`, type: 'success' })
      setTimeout(loadWorkers, 2000) // Refresh after 2s
    } catch (err) {
      setToast({ message: `Failed to start ${serviceName}`, type: 'error' })
    }
  }

  async function handleStopService(workerId: string, serviceName: string) {
    try {
      await api.stopWorkerService(workerId, serviceName)
      setToast({ message: `Stopping ${serviceName}...`, type: 'success' })
      setTimeout(loadWorkers, 2000) // Refresh after 2s
    } catch (err) {
      setToast({ message: `Failed to stop ${serviceName}`, type: 'error' })
    }
  }

  function getStatusBadge(status: string) {
    switch (status) {
      case 'running':
        return <Badge variant="success">Running</Badge>
      case 'stopped':
        return <Badge variant="destructive">Stopped</Badge>
      case 'starting':
        return <Badge variant="warning">Starting</Badge>
      default:
        return <Badge variant="secondary">Unknown</Badge>
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Workers</h2>
          <p className="text-muted-foreground">Monitor remote Claude Self-Reflect agents</p>
        </div>
        <Button onClick={loadWorkers} variant="outline" size="sm">
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* Toast */}
      {toast && (
        <div
          className={`fixed top-4 right-4 z-50 rounded-lg p-4 shadow-lg ${
            toast.type === 'success' ? 'bg-green-500 text-white' : 'bg-red-500 text-white'
          }`}
        >
          <p className="text-sm font-medium">{toast.message}</p>
        </div>
      )}

      {/* Error State */}
      {error && (
        <Card className="border-destructive">
          <CardContent className="pt-6">
            <div className="flex items-center gap-2 text-destructive">
              <AlertCircle className="h-5 w-5" />
              <p className="font-medium">{error}</p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Summary Cards */}
      {summary && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Workers</CardTitle>
              <Server className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{summary.total_workers}</div>
              <p className="text-xs text-muted-foreground">
                <span className="text-green-600">{summary.online_workers} online</span>
                {summary.offline_workers > 0 && (
                  <span className="text-red-600 ml-2">{summary.offline_workers} offline</span>
                )}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Services Running</CardTitle>
              <Container className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{summary.total_services_running}</div>
              <p className="text-xs text-muted-foreground">Across all workers</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Vectors</CardTitle>
              <Database className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{summary.total_vectors.toLocaleString()}</div>
              <p className="text-xs text-muted-foreground">In Qdrant collections</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Messages</CardTitle>
              <HardDrive className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{summary.total_messages.toLocaleString()}</div>
              <p className="text-xs text-muted-foreground">Imported conversations</p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* No Workers State */}
      {workers.length === 0 && !error && (
        <Card>
          <CardContent className="pt-6">
            <div className="flex flex-col items-center justify-center text-center py-12">
              <Server className="h-12 w-12 text-muted-foreground mb-4" />
              <h3 className="text-lg font-semibold mb-2">No Workers Connected</h3>
              <p className="text-sm text-muted-foreground max-w-md mb-4">
                No worker agents have reported in yet. Install and run the agent on each machine
                where Claude Self-Reflect is deployed.
              </p>
              <pre className="bg-muted p-4 rounded-md text-xs text-left">
                {`# Install and run the worker agent
python -m claude_self_reflect.agent \\
  --api-url http://your-admin-api:8000`}
              </pre>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Workers List */}
      <div className="space-y-4">
        {workers.map((worker) => (
          <Card key={worker.worker_id} className={!worker.is_online ? 'opacity-60' : ''}>
            <CardHeader className="cursor-pointer" onClick={() => toggleWorkerExpand(worker.worker_id)}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  {expandedWorkers.has(worker.worker_id) ? (
                    <ChevronDown className="h-5 w-5 text-muted-foreground" />
                  ) : (
                    <ChevronRight className="h-5 w-5 text-muted-foreground" />
                  )}
                  <div className="flex items-center gap-2">
                    {worker.is_online ? (
                      <Wifi className="h-5 w-5 text-green-500" />
                    ) : (
                      <WifiOff className="h-5 w-5 text-red-500" />
                    )}
                    <CardTitle className="text-lg">{worker.hostname}</CardTitle>
                  </div>
                  <Badge variant={worker.is_online ? 'success' : 'destructive'}>
                    {worker.is_online ? 'Online' : 'Offline'}
                  </Badge>
                </div>
                <div className="flex items-center gap-4">
                  <div className="text-right text-sm text-muted-foreground">
                    <p>{worker.ip_address || 'No IP'}</p>
                    <p className="text-xs">Last seen: {formatRelativeTime(worker.last_heartbeat)}</p>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation()
                      handleRemoveWorker(worker.worker_id)
                    }}
                  >
                    <Trash2 className="h-4 w-4 text-destructive" />
                  </Button>
                </div>
              </div>
              <CardDescription>
                {worker.platform} | Agent v{worker.agent_version} |{' '}
                {worker.embedding_mode ? `${worker.embedding_mode.toUpperCase()} mode` : 'Unknown mode'}
              </CardDescription>
            </CardHeader>

            {expandedWorkers.has(worker.worker_id) && (
              <CardContent className="space-y-4">
                {/* System Metrics */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="flex items-center gap-2">
                    <Cpu className="h-4 w-4 text-muted-foreground" />
                    <div>
                      <p className="text-xs text-muted-foreground">CPU</p>
                      <p className="font-medium">{worker.cpu_percent?.toFixed(1) || 'N/A'}%</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <HardDrive className="h-4 w-4 text-muted-foreground" />
                    <div>
                      <p className="text-xs text-muted-foreground">Memory</p>
                      <p className="font-medium">{worker.memory_percent?.toFixed(1) || 'N/A'}%</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Database className="h-4 w-4 text-muted-foreground" />
                    <div>
                      <p className="text-xs text-muted-foreground">Qdrant</p>
                      <p className="font-medium">
                        {worker.qdrant_connected ? (
                          <span className="text-green-600">{worker.qdrant_vectors.toLocaleString()} vectors</span>
                        ) : (
                          <span className="text-red-600">Disconnected</span>
                        )}
                      </p>
                    </div>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Import Status</p>
                    <p className="font-medium">
                      {worker.imported_files} / {worker.total_files} files
                    </p>
                  </div>
                </div>

                {/* Docker Services */}
                {worker.docker_available && worker.services.length > 0 ? (
                  <div className="border rounded-lg overflow-hidden">
                    <table className="w-full">
                      <thead className="bg-muted/50">
                        <tr className="border-b">
                          <th className="px-4 py-2 text-left text-sm font-medium">Service</th>
                          <th className="px-4 py-2 text-left text-sm font-medium">Status</th>
                          <th className="px-4 py-2 text-left text-sm font-medium">Ports</th>
                          <th className="px-4 py-2 text-left text-sm font-medium">Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {worker.services.map((service) => (
                          <tr key={service.name} className="border-b last:border-0">
                            <td className="px-4 py-2">
                              <div className="flex items-center gap-2">
                                <Container className="h-4 w-4 text-muted-foreground" />
                                <span className="font-medium">{service.name}</span>
                              </div>
                            </td>
                            <td className="px-4 py-2">{getStatusBadge(service.status)}</td>
                            <td className="px-4 py-2 text-sm text-muted-foreground">
                              {service.ports?.join(', ') || '-'}
                            </td>
                            <td className="px-4 py-2">
                              <div className="flex gap-1">
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  disabled={service.status === 'running' || !worker.is_online}
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    handleStartService(worker.worker_id, service.name)
                                  }}
                                  title="Start service"
                                >
                                  <Play className="h-3 w-3" />
                                </Button>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  disabled={service.status === 'stopped' || !worker.is_online}
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    handleStopService(worker.worker_id, service.name)
                                  }}
                                  title="Stop service"
                                >
                                  <Square className="h-3 w-3" />
                                </Button>
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="text-center py-4 text-muted-foreground text-sm">
                    {worker.docker_available
                      ? 'No Docker services found'
                      : 'Docker not available on this worker'}
                  </div>
                )}
              </CardContent>
            )}
          </Card>
        ))}
      </div>
    </div>
  )
}
