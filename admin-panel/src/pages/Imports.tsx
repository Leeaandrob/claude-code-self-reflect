import { useEffect, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { api } from '@/services/api'
import { formatRelativeTime } from '@/lib/utils'
import { FileText, Package, MessageSquare, TrendingUp, Filter, ChevronLeft, ChevronRight } from 'lucide-react'

interface ImportStatus {
  total_files: number
  imported_files: number
  total_messages: number
  progress: number
}

interface ImportedFile {
  path: string
  project: string
  imported_at: string
  message_count: number
  hash: string
}

const LIMIT_OPTIONS = [50, 100, 200, 500] as const
const ITEMS_PER_PAGE = 10

export function Imports() {
  const [status, setStatus] = useState<ImportStatus | null>(null)
  const [files, setFiles] = useState<ImportedFile[]>([])
  const [projects, setProjects] = useState<string[]>([])
  const [selectedProject, setSelectedProject] = useState<string>('all')
  const [limit, setLimit] = useState<number>(100)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [currentPage, setCurrentPage] = useState(1)

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true)
        setError(null)

        const [statusData, filesData, projectsData] = await Promise.all([
          api.getImportStatus(),
          api.listImportedFiles(selectedProject === 'all' ? undefined : selectedProject, limit),
          api.listProjects()
        ])

        setStatus(statusData)

        // Handle different response formats
        if (Array.isArray(filesData)) {
          setFiles(filesData)
        } else if (filesData.files) {
          setFiles(filesData.files)
        } else {
          setFiles([])
        }

        // Extract unique projects from projects list
        const projectNames = projectsData?.projects?.map((p: any) => p.name) || []
        setProjects(projectNames)
      } catch (err) {
        console.error('Failed to load imports data:', err)
        setError(err instanceof Error ? err.message : 'Failed to load data')
      } finally {
        setLoading(false)
      }
    }

    loadData()
    const interval = setInterval(loadData, 30000) // Refresh every 30s
    return () => clearInterval(interval)
  }, [selectedProject, limit])

  // Reset to first page when filters change
  useEffect(() => {
    setCurrentPage(1)
  }, [selectedProject, limit])

  // Pagination calculations
  const totalPages = Math.ceil(files.length / ITEMS_PER_PAGE)
  const startIndex = (currentPage - 1) * ITEMS_PER_PAGE
  const endIndex = startIndex + ITEMS_PER_PAGE
  const currentFiles = files.slice(startIndex, endIndex)

  const handlePreviousPage = () => {
    setCurrentPage(prev => Math.max(1, prev - 1))
  }

  const handleNextPage = () => {
    setCurrentPage(prev => Math.min(totalPages, prev + 1))
  }

  if (loading && !status) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-muted-foreground">Loading imports data...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-destructive">Error: {error}</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Imports</h2>
        <p className="text-muted-foreground">Import status and file tracking</p>
      </div>

      {/* Import Status Summary Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Files</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {status?.total_files?.toLocaleString() || 0}
            </div>
            <p className="text-xs text-muted-foreground">
              Files available for import
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Imported Files</CardTitle>
            <Package className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {status?.imported_files?.toLocaleString() || 0}
            </div>
            <p className="text-xs text-muted-foreground">
              Successfully imported
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Messages</CardTitle>
            <MessageSquare className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {status?.total_messages?.toLocaleString() || 0}
            </div>
            <p className="text-xs text-muted-foreground">
              Messages indexed
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Import Progress</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {status?.progress?.toFixed(1) || 0}%
            </div>
            <div className="mt-2">
              <div className="h-2 w-full bg-secondary rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary transition-all duration-300"
                  style={{ width: `${status?.progress || 0}%` }}
                />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Imported Files List */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Imported Files</CardTitle>
              <CardDescription>
                Browse and filter imported conversation files
              </CardDescription>
            </div>
            <Badge variant="secondary">
              {files.length} of {limit} loaded
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          {/* Filters */}
          <div className="flex items-center gap-4 mb-6">
            <div className="flex items-center gap-2">
              <Filter className="h-4 w-4 text-muted-foreground" />
              <label htmlFor="project-filter" className="text-sm font-medium">
                Project:
              </label>
              <select
                id="project-filter"
                value={selectedProject}
                onChange={(e) => setSelectedProject(e.target.value)}
                className="px-3 py-1.5 text-sm border rounded-md bg-background"
                disabled={loading}
              >
                <option value="all">All Projects</option>
                {projects.map((project) => (
                  <option key={project} value={project}>
                    {project}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-center gap-2">
              <label htmlFor="limit-selector" className="text-sm font-medium">
                Limit:
              </label>
              <select
                id="limit-selector"
                value={limit}
                onChange={(e) => setLimit(Number(e.target.value))}
                className="px-3 py-1.5 text-sm border rounded-md bg-background"
                disabled={loading}
              >
                {LIMIT_OPTIONS.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </div>

            {loading && (
              <div className="ml-auto">
                <Badge variant="secondary">Refreshing...</Badge>
              </div>
            )}
          </div>

          {/* Table */}
          {currentFiles.length > 0 ? (
            <>
              <div className="border rounded-lg overflow-hidden">
                <table className="w-full">
                  <thead className="bg-muted/50">
                    <tr className="border-b">
                      <th className="px-4 py-3 text-left text-sm font-medium">Project</th>
                      <th className="px-4 py-3 text-left text-sm font-medium">File Path</th>
                      <th className="px-4 py-3 text-left text-sm font-medium">Messages</th>
                      <th className="px-4 py-3 text-left text-sm font-medium">Imported</th>
                    </tr>
                  </thead>
                  <tbody>
                    {currentFiles.map((file, index) => (
                      <tr
                        key={file.hash || index}
                        className="border-b last:border-0 hover:bg-muted/30 transition-colors"
                      >
                        <td className="px-4 py-3">
                          <Badge variant="secondary">{file.project}</Badge>
                        </td>
                        <td className="px-4 py-3">
                          <div className="max-w-md truncate text-sm font-mono" title={file.path}>
                            {file.path}
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-1">
                            <MessageSquare className="h-3 w-3 text-muted-foreground" />
                            <span className="text-sm font-medium">
                              {file.message_count.toLocaleString()}
                            </span>
                          </div>
                        </td>
                        <td className="px-4 py-3 text-sm text-muted-foreground">
                          {formatRelativeTime(file.imported_at)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pagination Controls */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between mt-4">
                  <div className="text-sm text-muted-foreground">
                    Showing {startIndex + 1} to {Math.min(endIndex, files.length)} of {files.length} files
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={handlePreviousPage}
                      disabled={currentPage === 1}
                      className="px-3 py-1.5 text-sm border rounded-md bg-background hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      aria-label="Previous page"
                    >
                      <ChevronLeft className="h-4 w-4" />
                    </button>
                    <div className="text-sm font-medium">
                      Page {currentPage} of {totalPages}
                    </div>
                    <button
                      onClick={handleNextPage}
                      disabled={currentPage === totalPages}
                      className="px-3 py-1.5 text-sm border rounded-md bg-background hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      aria-label="Next page"
                    >
                      <ChevronRight className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="text-center py-12 text-muted-foreground">
              {selectedProject === 'all'
                ? 'No imported files found'
                : `No imported files found for project "${selectedProject}"`
              }
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
