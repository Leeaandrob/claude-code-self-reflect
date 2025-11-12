import { useEffect, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { api } from '@/services/api'
import { formatRelativeTime } from '@/lib/utils'
import { FolderOpen, FileText, MessageSquare, Database, RefreshCw, AlertCircle } from 'lucide-react'

interface Collection {
  name: string
  points: number
}

interface Project {
  name: string
  message_count: number
  file_count: number
  last_updated: string
  collections?: Collection[]
}

export function Projects() {
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isRefreshing, setIsRefreshing] = useState(false)

  const loadProjects = async (isAutoRefresh = false) => {
    if (!isAutoRefresh) {
      setLoading(true)
    } else {
      setIsRefreshing(true)
    }
    setError(null)

    try {
      const data = await api.listProjects()
      setProjects(data)
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load projects'
      setError(errorMessage)
      console.error('Failed to load projects:', err)
    } finally {
      setLoading(false)
      setIsRefreshing(false)
    }
  }

  useEffect(() => {
    loadProjects()
    const interval = setInterval(() => loadProjects(true), 30000) // Auto-refresh every 30s
    return () => clearInterval(interval)
  }, [])

  const extractCollectionMode = (collectionName: string): string => {
    if (collectionName.includes('_local_')) return 'local'
    if (collectionName.includes('_cloud_')) return 'cloud'
    if (collectionName.includes('voyage')) return 'cloud'
    return 'unknown'
  }

  const getTotalVectors = (collections: Collection[]): number => {
    return collections.reduce((sum, col) => sum + col.points, 0)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex flex-col items-center gap-2">
          <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
          <p className="text-sm text-muted-foreground">Loading projects...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Projects</h2>
          <p className="text-muted-foreground">Manage your conversation projects</p>
        </div>
        <Card className="border-destructive">
          <CardContent className="pt-6">
            <div className="flex items-center gap-2 text-destructive">
              <AlertCircle className="h-5 w-5" />
              <p className="font-medium">{error}</p>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Projects</h2>
          <p className="text-muted-foreground">
            {projects.length} {projects.length === 1 ? 'project' : 'projects'} with indexed conversations
          </p>
        </div>
        <button
          onClick={() => loadProjects()}
          disabled={isRefreshing}
          className="flex items-center gap-2 px-4 py-2 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
        >
          <RefreshCw className={`h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {projects.length === 0 ? (
        <Card>
          <CardContent className="pt-6">
            <div className="flex flex-col items-center justify-center text-center py-12">
              <FolderOpen className="h-12 w-12 text-muted-foreground mb-4" />
              <h3 className="text-lg font-semibold mb-2">No Projects Found</h3>
              <p className="text-sm text-muted-foreground max-w-md">
                No conversation projects have been imported yet. Start using Claude Code to create conversations
                and they will appear here.
              </p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {projects.map((project) => (
            <Card key={project.name} className="hover:shadow-lg transition-shadow">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2">
                    <FolderOpen className="h-5 w-5 text-primary" />
                    <CardTitle className="text-lg truncate">{project.name}</CardTitle>
                  </div>
                  {project.collections && project.collections.length > 0 && (
                    <Badge variant={extractCollectionMode(project.collections[0].name) === 'local' ? 'secondary' : 'info'}>
                      {extractCollectionMode(project.collections[0].name)}
                    </Badge>
                  )}
                </div>
                <CardDescription className="text-xs">
                  Last updated {formatRelativeTime(project.last_updated)}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {/* Statistics Grid */}
                  <div className="grid grid-cols-2 gap-4">
                    <div className="flex flex-col">
                      <div className="flex items-center gap-2 text-muted-foreground mb-1">
                        <MessageSquare className="h-4 w-4" />
                        <span className="text-xs font-medium">Messages</span>
                      </div>
                      <p className="text-2xl font-bold">{project.message_count.toLocaleString()}</p>
                    </div>
                    <div className="flex flex-col">
                      <div className="flex items-center gap-2 text-muted-foreground mb-1">
                        <FileText className="h-4 w-4" />
                        <span className="text-xs font-medium">Files</span>
                      </div>
                      <p className="text-2xl font-bold">{project.file_count}</p>
                    </div>
                  </div>

                  {/* Collections Info */}
                  {project.collections && project.collections.length > 0 && (
                    <div className="pt-4 border-t">
                      <div className="flex items-center gap-2 text-muted-foreground mb-2">
                        <Database className="h-4 w-4" />
                        <span className="text-xs font-medium">Vector Collections</span>
                      </div>
                      <div className="space-y-2">
                        {project.collections.map((collection) => (
                          <div
                            key={collection.name}
                            className="flex items-center justify-between p-2 rounded-md bg-muted/50"
                          >
                            <div className="flex-1 min-w-0">
                              <p className="text-xs font-mono truncate" title={collection.name}>
                                {collection.name}
                              </p>
                            </div>
                            <Badge variant="outline" className="ml-2 shrink-0">
                              {collection.points.toLocaleString()} pts
                            </Badge>
                          </div>
                        ))}
                        {project.collections.length > 1 && (
                          <div className="pt-2 text-xs text-muted-foreground">
                            Total vectors: {getTotalVectors(project.collections).toLocaleString()}
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* No Collections Warning */}
                  {project.collections && project.collections.length === 0 && (
                    <div className="pt-4 border-t">
                      <div className="flex items-center gap-2 text-yellow-600 dark:text-yellow-500">
                        <AlertCircle className="h-4 w-4" />
                        <p className="text-xs">No vector collections found</p>
                      </div>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Summary Card */}
      {projects.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Summary</CardTitle>
            <CardDescription>Aggregate statistics across all projects</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
              <div>
                <p className="text-sm font-medium text-muted-foreground mb-1">Total Projects</p>
                <p className="text-3xl font-bold">{projects.length}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-muted-foreground mb-1">Total Messages</p>
                <p className="text-3xl font-bold">
                  {projects.reduce((sum, p) => sum + p.message_count, 0).toLocaleString()}
                </p>
              </div>
              <div>
                <p className="text-sm font-medium text-muted-foreground mb-1">Total Files</p>
                <p className="text-3xl font-bold">
                  {projects.reduce((sum, p) => sum + p.file_count, 0)}
                </p>
              </div>
              <div>
                <p className="text-sm font-medium text-muted-foreground mb-1">Total Collections</p>
                <p className="text-3xl font-bold">
                  {projects.reduce((sum, p) => sum + (p.collections?.length || 0), 0)}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
