import { useEffect, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { api } from '@/services/api'
import { formatBytes, formatRelativeTime } from '@/lib/utils'
import { Database, HardDrive, FileText, Activity } from 'lucide-react'

export function Dashboard() {
  const [metrics, setMetrics] = useState<any>(null)
  const [stats, setStats] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function loadData() {
      try {
        const [metricsData, statsData] = await Promise.all([
          api.getDashboardMetrics(),
          api.getSystemStats()
        ])
        setMetrics(metricsData)
        setStats(statsData)
      } catch (error) {
        console.error('Failed to load dashboard data:', error)
      } finally {
        setLoading(false)
      }
    }
    loadData()
    const interval = setInterval(loadData, 30000) // Refresh every 30s
    return () => clearInterval(interval)
  }, [])

  if (loading) {
    return <div>Loading...</div>
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Dashboard</h2>
        <p className="text-muted-foreground">System overview and statistics</p>
      </div>

      {/* Metrics Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Qdrant Status</CardTitle>
            <Database className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {metrics?.qdrant?.status === 'connected' ? (
                <Badge variant="success">Connected</Badge>
              ) : (
                <Badge variant="destructive">Disconnected</Badge>
              )}
            </div>
            <p className="text-xs text-muted-foreground">
              {metrics?.qdrant?.collections_count || 0} collections
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Vectors</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {(metrics?.qdrant?.total_vectors || 0).toLocaleString()}
            </div>
            <p className="text-xs text-muted-foreground">
              In {metrics?.qdrant?.collections_count || 0} collections
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Imported Files</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {metrics?.import?.imported_files || 0}
            </div>
            <p className="text-xs text-muted-foreground">
              {(metrics?.import?.total_messages || 0).toLocaleString()} messages
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Memory Usage</CardTitle>
            <HardDrive className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {metrics?.memory?.percentage?.toFixed(1) || 0}%
            </div>
            <p className="text-xs text-muted-foreground">
              {formatBytes(metrics?.memory?.used || 0)} / {formatBytes(metrics?.memory?.total || 0)}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Embedding Mode */}
      <Card>
        <CardHeader>
          <CardTitle>Embedding Configuration</CardTitle>
          <CardDescription>Current embedding mode and model</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4">
            <div>
              <p className="text-sm font-medium">Mode:</p>
              <Badge variant={metrics?.embedding?.mode === 'local' ? 'secondary' : 'info'}>
                {metrics?.embedding?.mode?.toUpperCase() || 'Unknown'}
              </Badge>
            </div>
            <div>
              <p className="text-sm font-medium">Model:</p>
              <code className="text-sm">{metrics?.embedding?.model || 'N/A'}</code>
            </div>
            <div>
              <p className="text-sm font-medium">Dimension:</p>
              <code className="text-sm">{metrics?.embedding?.dimension || 'N/A'}d</code>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        {/* Top Projects */}
        <Card>
          <CardHeader>
            <CardTitle>Top Projects</CardTitle>
            <CardDescription>Projects with most messages</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {stats?.top_projects?.slice(0, 5).map((project: any, index: number) => (
                <div key={project.name} className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-muted-foreground">#{index + 1}</span>
                    <span className="font-medium">{project.name}</span>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-medium">{project.message_count.toLocaleString()}</p>
                    <p className="text-xs text-muted-foreground">{project.file_count} files</p>
                  </div>
                </div>
              )) || <p className="text-sm text-muted-foreground">No projects found</p>}
            </div>
          </CardContent>
        </Card>

        {/* Recent Activity */}
        <Card>
          <CardHeader>
            <CardTitle>Recent Imports</CardTitle>
            <CardDescription>Last 10 imported files</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {stats?.recent_imports?.slice(0, 10).map((imp: any) => (
                <div key={imp.path} className="flex flex-col gap-1">
                  <p className="text-sm font-medium truncate">{imp.project}</p>
                  <div className="flex items-center justify-between">
                    <p className="text-xs text-muted-foreground">
                      {imp.message_count} messages
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {formatRelativeTime(imp.imported_at)}
                    </p>
                  </div>
                </div>
              )) || <p className="text-sm text-muted-foreground">No recent imports</p>}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
