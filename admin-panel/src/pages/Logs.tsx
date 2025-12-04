import { useEffect, useState, useRef } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { api } from '@/services/api'
import { RefreshCw, Copy, Check, AlertCircle, Server, Container } from 'lucide-react'
import { cn } from '@/lib/utils'

interface Worker {
  worker_id: string
  hostname: string
  is_online: boolean
  services: {
    name: string
    status: string
  }[]
}

const LINE_OPTIONS = [50, 100, 200, 500]

export function Logs() {
  const [workers, setWorkers] = useState<Worker[]>([])
  const [selectedWorker, setSelectedWorker] = useState<string | null>(null)
  const [selectedService, setSelectedService] = useState<string | null>(null)
  const [lines, setLines] = useState(100)
  const [autoRefresh, setAutoRefresh] = useState(false)
  const [logs, setLogs] = useState<string>('')
  const [loading, setLoading] = useState(false)
  const [loadingWorkers, setLoadingWorkers] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const logContainerRef = useRef<HTMLDivElement>(null)
  const autoScrollRef = useRef(true)

  // Load workers on mount
  useEffect(() => {
    loadWorkers()
    const interval = setInterval(loadWorkers, 30000) // Refresh workers list every 30s
    return () => clearInterval(interval)
  }, [])

  const loadWorkers = async () => {
    try {
      setLoadingWorkers(true)
      const data = await api.listWorkers() as { workers: Worker[] }
      const onlineWorkers = (data.workers || []).filter(w => w.is_online)
      setWorkers(onlineWorkers)

      // Auto-select first online worker if none selected
      if (!selectedWorker && onlineWorkers.length > 0) {
        setSelectedWorker(onlineWorkers[0].worker_id)
        // Auto-select first service
        if (onlineWorkers[0].services.length > 0) {
          setSelectedService(onlineWorkers[0].services[0].name)
        }
      }
    } catch (err) {
      console.error('Failed to load workers:', err)
    } finally {
      setLoadingWorkers(false)
    }
  }

  const currentWorker = workers.find(w => w.worker_id === selectedWorker)
  const availableServices = currentWorker?.services || []

  // When worker changes, select first service
  useEffect(() => {
    if (currentWorker && currentWorker.services.length > 0) {
      if (!selectedService || !currentWorker.services.find(s => s.name === selectedService)) {
        setSelectedService(currentWorker.services[0].name)
      }
    } else {
      setSelectedService(null)
    }
  }, [selectedWorker, currentWorker])

  const fetchLogs = async () => {
    if (!selectedWorker || !selectedService) {
      setLogs('')
      return
    }

    try {
      setLoading(true)
      setError(null)

      const response = await api.getWorkerServiceLogs(selectedWorker, selectedService, lines)

      if (response?.logs) {
        setLogs(response.logs)

        // Auto-scroll to bottom if enabled
        if (autoScrollRef.current && logContainerRef.current) {
          setTimeout(() => {
            if (logContainerRef.current) {
              logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight
            }
          }, 100)
        }
      } else {
        setLogs('')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch logs')
      setLogs('')
    } finally {
      setLoading(false)
    }
  }

  // Fetch logs when worker/service/lines change
  useEffect(() => {
    if (selectedWorker && selectedService) {
      fetchLogs()
    }
  }, [selectedWorker, selectedService, lines])

  // Auto-refresh interval
  useEffect(() => {
    if (!autoRefresh) return

    const interval = setInterval(() => {
      fetchLogs()
    }, 5000)

    return () => clearInterval(interval)
  }, [autoRefresh, selectedWorker, selectedService, lines])

  const handleCopyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(logs)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      console.error('Failed to copy logs:', err)
    }
  }

  const handleScroll = () => {
    if (!logContainerRef.current) return

    const { scrollTop, scrollHeight, clientHeight } = logContainerRef.current
    const isAtBottom = Math.abs(scrollHeight - clientHeight - scrollTop) < 10
    autoScrollRef.current = isAtBottom
  }

  // Syntax highlighting for log levels
  const highlightLogs = (logText: string): React.ReactElement[] => {
    if (!logText) return []

    const lines = logText.split('\n')
    return lines.map((line, index) => {
      let className = 'text-gray-300'

      // Detect log levels (case-insensitive)
      if (/\b(ERROR|FAIL|FATAL|CRITICAL)\b/i.test(line)) {
        className = 'text-red-400 font-medium'
      } else if (/\b(WARN|WARNING)\b/i.test(line)) {
        className = 'text-yellow-400'
      } else if (/\b(INFO)\b/i.test(line)) {
        className = 'text-blue-400'
      } else if (/\b(DEBUG|TRACE)\b/i.test(line)) {
        className = 'text-gray-500'
      } else if (/\b(SUCCESS|OK)\b/i.test(line)) {
        className = 'text-green-400'
      }

      return (
        <div key={index} className={className}>
          {line}
        </div>
      )
    })
  }

  if (loadingWorkers) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Logs</h2>
        <p className="text-muted-foreground">View and monitor system logs from workers</p>
      </div>

      {workers.length === 0 ? (
        <Card>
          <CardContent className="pt-6">
            <div className="flex flex-col items-center justify-center text-center py-12">
              <Server className="h-12 w-12 text-muted-foreground mb-4" />
              <h3 className="text-lg font-semibold mb-2">No Workers Online</h3>
              <p className="text-sm text-muted-foreground max-w-md">
                No worker agents are currently online. Start a worker agent to view logs.
              </p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Log Viewer</CardTitle>
                <CardDescription>Real-time log monitoring from worker agents</CardDescription>
              </div>
              <div className="flex items-center gap-2">
                {autoRefresh && (
                  <Badge variant="success" className="animate-pulse">
                    Auto-refresh: 5s
                  </Badge>
                )}
                {loading && (
                  <RefreshCw className="h-4 w-4 animate-spin text-muted-foreground" />
                )}
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Controls */}
            <div className="flex flex-wrap items-center gap-4">
              {/* Worker Selector */}
              <div className="flex items-center gap-2">
                <Server className="h-4 w-4 text-muted-foreground" />
                <label className="text-sm font-medium">Worker:</label>
                <select
                  className="rounded-md border bg-background px-3 py-1.5 text-sm"
                  value={selectedWorker || ''}
                  onChange={(e) => setSelectedWorker(e.target.value)}
                >
                  {workers.map(worker => (
                    <option key={worker.worker_id} value={worker.worker_id}>
                      {worker.hostname} {worker.is_online ? '(online)' : '(offline)'}
                    </option>
                  ))}
                </select>
              </div>

              {/* Service Selector */}
              <div className="flex items-center gap-2">
                <Container className="h-4 w-4 text-muted-foreground" />
                <label className="text-sm font-medium">Service:</label>
                <select
                  className="rounded-md border bg-background px-3 py-1.5 text-sm"
                  value={selectedService || ''}
                  onChange={(e) => setSelectedService(e.target.value)}
                  disabled={availableServices.length === 0}
                >
                  {availableServices.map(service => (
                    <option key={service.name} value={service.name}>
                      {service.name} ({service.status})
                    </option>
                  ))}
                </select>
              </div>

              {/* Lines Selector */}
              <div className="flex items-center gap-2">
                <label className="text-sm font-medium">Lines:</label>
                <div className="flex gap-1">
                  {LINE_OPTIONS.map(option => (
                    <Button
                      key={option}
                      variant={lines === option ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => setLines(option)}
                    >
                      {option}
                    </Button>
                  ))}
                </div>
              </div>

              {/* Auto-refresh Toggle */}
              <div className="flex items-center gap-2">
                <label className="text-sm font-medium">Auto-refresh:</label>
                <Button
                  variant={autoRefresh ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setAutoRefresh(!autoRefresh)}
                >
                  {autoRefresh ? 'On' : 'Off'}
                </Button>
              </div>

              {/* Manual Refresh */}
              <Button
                variant="outline"
                size="sm"
                onClick={fetchLogs}
                disabled={loading || !selectedWorker || !selectedService}
              >
                <RefreshCw className={cn('h-4 w-4', loading && 'animate-spin')} />
                Refresh
              </Button>

              {/* Copy to Clipboard */}
              <Button
                variant="outline"
                size="sm"
                onClick={handleCopyToClipboard}
                disabled={!logs}
              >
                {copied ? (
                  <>
                    <Check className="h-4 w-4" />
                    Copied
                  </>
                ) : (
                  <>
                    <Copy className="h-4 w-4" />
                    Copy
                  </>
                )}
              </Button>
            </div>

            {/* Log Display */}
            <div className="relative">
              {error && (
                <div className="mb-4 flex items-center gap-2 rounded-md bg-destructive/10 p-4 text-destructive">
                  <AlertCircle className="h-4 w-4" />
                  <p className="text-sm font-medium">{error}</p>
                </div>
              )}

              <div
                ref={logContainerRef}
                onScroll={handleScroll}
                className="h-[600px] overflow-y-auto rounded-md border bg-black/90 p-4"
              >
                {logs ? (
                  <pre className="font-mono text-xs leading-relaxed">
                    {highlightLogs(logs)}
                  </pre>
                ) : (
                  <div className="flex h-full items-center justify-center">
                    <p className="text-sm text-muted-foreground">
                      {loading ? 'Loading logs...' : 'Select a worker and service to view logs'}
                    </p>
                  </div>
                )}
              </div>

              {/* Scroll indicator */}
              {logs && !autoScrollRef.current && (
                <div className="absolute bottom-4 left-1/2 -translate-x-1/2">
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => {
                      if (logContainerRef.current) {
                        logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight
                        autoScrollRef.current = true
                      }
                    }}
                  >
                    Scroll to bottom
                  </Button>
                </div>
              )}
            </div>

            {/* Log Stats */}
            {logs && (
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <div className="flex gap-4">
                  <span>Total lines: {logs.split('\n').length}</span>
                  <span>Characters: {logs.length.toLocaleString()}</span>
                </div>
                <div>
                  Last updated: {new Date().toLocaleTimeString()}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Log Legend */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Log Level Legend</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-4 text-xs">
            <div className="flex items-center gap-2">
              <div className="h-3 w-3 rounded-full bg-red-400" />
              <span>ERROR / FAIL / FATAL / CRITICAL</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="h-3 w-3 rounded-full bg-yellow-400" />
              <span>WARN / WARNING</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="h-3 w-3 rounded-full bg-blue-400" />
              <span>INFO</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="h-3 w-3 rounded-full bg-green-400" />
              <span>SUCCESS / OK</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="h-3 w-3 rounded-full bg-gray-500" />
              <span>DEBUG / TRACE</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
