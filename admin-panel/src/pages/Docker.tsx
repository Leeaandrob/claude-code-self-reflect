import { useEffect, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { api } from '@/services/api'
import { formatDuration } from '@/lib/utils'
import { Play, Square, RefreshCw, Container, AlertCircle } from 'lucide-react'

interface DockerService {
  name: string
  status: 'running' | 'stopped' | 'starting' | 'stopping' | 'unknown'
  container_id?: string
  image?: string
  uptime?: number
  created_at?: string
  ports?: string[]
}

interface ServiceAction {
  serviceName: string
  action: 'start' | 'stop'
}

export function Docker() {
  const [services, setServices] = useState<DockerService[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [actionInProgress, setActionInProgress] = useState<ServiceAction | null>(null)
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null)

  // Auto-refresh every 10 seconds (more frequent than other pages)
  useEffect(() => {
    loadServices()
    const interval = setInterval(loadServices, 10000)
    return () => clearInterval(interval)
  }, [])

  // Auto-hide toast after 3 seconds
  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => setToast(null), 3000)
      return () => clearTimeout(timer)
    }
  }, [toast])

  async function loadServices() {
    try {
      const data = await api.listDockerServices()
      setServices(data.services || [])
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load Docker services')
      console.error('Failed to load Docker services:', err)
    } finally {
      setLoading(false)
    }
  }

  async function handleServiceAction(serviceName: string, action: 'start' | 'stop') {
    setActionInProgress({ serviceName, action })
    try {
      if (action === 'start') {
        await api.startService(serviceName)
        setToast({ message: `Service "${serviceName}" started successfully`, type: 'success' })
      } else {
        await api.stopService(serviceName)
        setToast({ message: `Service "${serviceName}" stopped successfully`, type: 'success' })
      }
      // Refresh services immediately after action
      await loadServices()
    } catch (err) {
      const message = err instanceof Error ? err.message : `Failed to ${action} service`
      setToast({ message, type: 'error' })
      console.error(`Failed to ${action} service:`, err)
    } finally {
      setActionInProgress(null)
    }
  }

  function getStatusBadge(status: DockerService['status']) {
    switch (status) {
      case 'running':
        return <Badge variant="success">Running</Badge>
      case 'stopped':
        return <Badge variant="destructive">Stopped</Badge>
      case 'starting':
        return <Badge variant="warning">Starting</Badge>
      case 'stopping':
        return <Badge variant="warning">Stopping</Badge>
      default:
        return <Badge variant="secondary">Unknown</Badge>
    }
  }

  function isActionDisabled(service: DockerService, action: 'start' | 'stop'): boolean {
    // Disable if any action is in progress
    if (actionInProgress) return true

    // Disable start if already running or starting
    if (action === 'start' && (service.status === 'running' || service.status === 'starting')) {
      return true
    }

    // Disable stop if already stopped or stopping
    if (action === 'stop' && (service.status === 'stopped' || service.status === 'stopping')) {
      return true
    }

    return false
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
          <h2 className="text-3xl font-bold tracking-tight">Docker Services</h2>
          <p className="text-muted-foreground">Manage Docker containers and services</p>
        </div>
        <Button
          onClick={loadServices}
          variant="outline"
          size="sm"
          disabled={loading}
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* Toast Notification */}
      {toast && (
        <div
          className={`fixed top-4 right-4 z-50 rounded-lg p-4 shadow-lg ${
            toast.type === 'success'
              ? 'bg-green-500 text-white'
              : 'bg-red-500 text-white'
          }`}
        >
          <div className="flex items-center gap-2">
            {toast.type === 'error' && <AlertCircle className="h-4 w-4" />}
            <p className="text-sm font-medium">{toast.message}</p>
          </div>
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

      {/* Services Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {services.length === 0 && !error ? (
          <Card className="col-span-full">
            <CardContent className="pt-6">
              <p className="text-center text-muted-foreground">No Docker services found</p>
            </CardContent>
          </Card>
        ) : (
          services.map((service) => (
            <Card key={service.name} className="relative">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2">
                    <Container className="h-5 w-5 text-muted-foreground" />
                    <CardTitle className="text-lg">{service.name}</CardTitle>
                  </div>
                  {getStatusBadge(service.status)}
                </div>
                <CardDescription>
                  {service.image ? `Image: ${service.image.split(':')[0]}` : 'No image info'}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Service Details */}
                <div className="space-y-2 text-sm">
                  {service.container_id && (
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Container ID:</span>
                      <code className="text-xs bg-muted px-2 py-1 rounded">
                        {service.container_id.substring(0, 12)}
                      </code>
                    </div>
                  )}

                  {service.uptime !== undefined && service.status === 'running' && (
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Uptime:</span>
                      <span className="font-medium">{formatDuration(service.uptime)}</span>
                    </div>
                  )}

                  {service.ports && service.ports.length > 0 && (
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Ports:</span>
                      <span className="font-medium text-xs">{service.ports.join(', ')}</span>
                    </div>
                  )}
                </div>

                {/* Action Buttons */}
                <div className="flex gap-2 pt-2">
                  <Button
                    onClick={() => handleServiceAction(service.name, 'start')}
                    disabled={isActionDisabled(service, 'start')}
                    variant="outline"
                    size="sm"
                    className="flex-1"
                  >
                    <Play className="h-4 w-4" />
                    {actionInProgress?.serviceName === service.name &&
                    actionInProgress?.action === 'start'
                      ? 'Starting...'
                      : 'Start'}
                  </Button>
                  <Button
                    onClick={() => handleServiceAction(service.name, 'stop')}
                    disabled={isActionDisabled(service, 'stop')}
                    variant="outline"
                    size="sm"
                    className="flex-1"
                  >
                    <Square className="h-4 w-4" />
                    {actionInProgress?.serviceName === service.name &&
                    actionInProgress?.action === 'stop'
                      ? 'Stopping...'
                      : 'Stop'}
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>

      {/* Service Status Summary */}
      {services.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Service Status Summary</CardTitle>
            <CardDescription>Overview of all Docker services</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center">
                <p className="text-2xl font-bold text-green-600">
                  {services.filter((s) => s.status === 'running').length}
                </p>
                <p className="text-sm text-muted-foreground">Running</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-red-600">
                  {services.filter((s) => s.status === 'stopped').length}
                </p>
                <p className="text-sm text-muted-foreground">Stopped</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-yellow-600">
                  {services.filter((s) => s.status === 'starting' || s.status === 'stopping').length}
                </p>
                <p className="text-sm text-muted-foreground">Transitioning</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold">
                  {services.length}
                </p>
                <p className="text-sm text-muted-foreground">Total</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
