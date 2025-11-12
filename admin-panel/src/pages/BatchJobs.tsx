import { useEffect, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { api } from '@/services/api'
import { formatRelativeTime, formatDuration } from '@/lib/utils'
import { Clock, CheckCircle, XCircle, Loader2, Eye, X, RefreshCw } from 'lucide-react'

interface BatchJob {
  id: string
  status: 'pending' | 'in_progress' | 'completed' | 'failed'
  created_at: string
  completed_at?: string
  progress?: number
  total_items?: number
  input_params?: Record<string, any>
  output?: any
  error?: string
}

export function BatchJobs() {
  const [jobs, setJobs] = useState<BatchJob[]>([])
  const [filteredJobs, setFilteredJobs] = useState<BatchJob[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedJob, setSelectedJob] = useState<BatchJob | null>(null)
  const [statusFilter, setStatusFilter] = useState<string>('all')

  useEffect(() => {
    loadJobs()
    const interval = setInterval(loadJobs, 15000) // Auto-refresh every 15s
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    // Apply status filter
    if (statusFilter === 'all') {
      setFilteredJobs(jobs)
    } else {
      setFilteredJobs(jobs.filter(job => job.status === statusFilter))
    }
  }, [jobs, statusFilter])

  async function loadJobs() {
    try {
      const data = await api.listBatchJobs(50) as BatchJob[]
      setJobs(data)
    } catch (error) {
      console.error('Failed to load batch jobs:', error)
    } finally {
      setLoading(false)
    }
  }

  async function viewJobDetails(jobId: string) {
    try {
      const job = await api.getBatchJob(jobId) as BatchJob
      setSelectedJob(job)
    } catch (error) {
      console.error('Failed to load job details:', error)
    }
  }

  function getStatusBadge(status: string) {
    switch (status) {
      case 'pending':
        return <Badge variant="warning" className="gap-1"><Clock className="h-3 w-3" /> Pending</Badge>
      case 'in_progress':
        return <Badge variant="info" className="gap-1"><Loader2 className="h-3 w-3 animate-spin" /> In Progress</Badge>
      case 'completed':
        return <Badge variant="success" className="gap-1"><CheckCircle className="h-3 w-3" /> Completed</Badge>
      case 'failed':
        return <Badge variant="destructive" className="gap-1"><XCircle className="h-3 w-3" /> Failed</Badge>
      default:
        return <Badge variant="outline">{status}</Badge>
    }
  }

  function calculateDuration(job: BatchJob): string {
    if (!job.completed_at) return 'In progress'
    const start = new Date(job.created_at).getTime()
    const end = new Date(job.completed_at).getTime()
    return formatDuration((end - start) / 1000)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Batch Jobs</h2>
          <p className="text-muted-foreground">Monitor AI-powered narrative generation jobs</p>
        </div>
        <Button onClick={loadJobs} variant="outline" size="sm">
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Filter Controls */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center gap-4">
            <label className="text-sm font-medium">Filter by status:</label>
            <div className="flex gap-2">
              <Button
                variant={statusFilter === 'all' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setStatusFilter('all')}
              >
                All ({jobs.length})
              </Button>
              <Button
                variant={statusFilter === 'pending' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setStatusFilter('pending')}
              >
                Pending ({jobs.filter(j => j.status === 'pending').length})
              </Button>
              <Button
                variant={statusFilter === 'in_progress' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setStatusFilter('in_progress')}
              >
                In Progress ({jobs.filter(j => j.status === 'in_progress').length})
              </Button>
              <Button
                variant={statusFilter === 'completed' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setStatusFilter('completed')}
              >
                Completed ({jobs.filter(j => j.status === 'completed').length})
              </Button>
              <Button
                variant={statusFilter === 'failed' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setStatusFilter('failed')}
              >
                Failed ({jobs.filter(j => j.status === 'failed').length})
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Jobs List */}
      {filteredJobs.length === 0 ? (
        <Card>
          <CardContent className="pt-6">
            <p className="text-center text-muted-foreground">
              {statusFilter === 'all' ? 'No batch jobs found' : `No ${statusFilter} jobs found`}
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {filteredJobs.map((job) => (
            <Card key={job.id} className="hover:shadow-md transition-shadow">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="space-y-1">
                    <CardTitle className="text-lg font-mono">{job.id}</CardTitle>
                    <CardDescription className="flex items-center gap-2">
                      {getStatusBadge(job.status)}
                      <span>Created {formatRelativeTime(job.created_at)}</span>
                    </CardDescription>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => viewJobDetails(job.id)}
                    aria-label={`View details for job ${job.id}`}
                  >
                    <Eye className="h-4 w-4 mr-2" />
                    Details
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  <div>
                    <p className="text-muted-foreground">Progress</p>
                    <div className="flex items-center gap-2 mt-1">
                      <div className="flex-1 h-2 bg-secondary rounded-full overflow-hidden">
                        <div
                          className="h-full bg-primary transition-all duration-300"
                          style={{ width: `${job.progress || 0}%` }}
                          role="progressbar"
                          aria-valuenow={job.progress || 0}
                          aria-valuemin={0}
                          aria-valuemax={100}
                        />
                      </div>
                      <span className="font-medium">{job.progress || 0}%</span>
                    </div>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Items</p>
                    <p className="font-medium mt-1">{job.total_items || 'N/A'}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Duration</p>
                    <p className="font-medium mt-1">{calculateDuration(job)}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Completed</p>
                    <p className="font-medium mt-1">
                      {job.completed_at ? formatRelativeTime(job.completed_at) : '-'}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Job Details Modal */}
      {selectedJob && (
        <div
          className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50"
          onClick={() => setSelectedJob(null)}
          role="dialog"
          aria-modal="true"
          aria-labelledby="modal-title"
        >
          <Card
            className="max-w-3xl w-full max-h-[80vh] overflow-auto"
            onClick={(e: React.MouseEvent) => e.stopPropagation()}
          >
            <CardHeader>
              <div className="flex items-start justify-between">
                <div>
                  <CardTitle id="modal-title" className="font-mono">{selectedJob.id}</CardTitle>
                  <CardDescription className="mt-2">
                    {getStatusBadge(selectedJob.status)}
                  </CardDescription>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setSelectedJob(null)}
                  aria-label="Close dialog"
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Timestamps */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <h3 className="text-sm font-medium text-muted-foreground">Created</h3>
                  <p className="mt-1 text-sm">
                    {new Date(selectedJob.created_at).toLocaleString()}
                  </p>
                </div>
                {selectedJob.completed_at && (
                  <div>
                    <h3 className="text-sm font-medium text-muted-foreground">Completed</h3>
                    <p className="mt-1 text-sm">
                      {new Date(selectedJob.completed_at).toLocaleString()}
                    </p>
                  </div>
                )}
              </div>

              {/* Progress */}
              <div>
                <h3 className="text-sm font-medium text-muted-foreground">Progress</h3>
                <div className="mt-2 flex items-center gap-2">
                  <div className="flex-1 h-2 bg-secondary rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary transition-all"
                      style={{ width: `${selectedJob.progress || 0}%` }}
                      role="progressbar"
                      aria-valuenow={selectedJob.progress || 0}
                      aria-valuemin={0}
                      aria-valuemax={100}
                    />
                  </div>
                  <span className="text-sm font-medium">{selectedJob.progress || 0}%</span>
                </div>
                {selectedJob.total_items && (
                  <p className="mt-1 text-sm text-muted-foreground">
                    {selectedJob.total_items} total items
                  </p>
                )}
              </div>

              {/* Input Parameters */}
              {selectedJob.input_params && Object.keys(selectedJob.input_params).length > 0 && (
                <div>
                  <h3 className="text-sm font-medium text-muted-foreground mb-2">Input Parameters</h3>
                  <pre className="text-xs bg-secondary p-3 rounded-lg overflow-auto max-h-48">
                    {JSON.stringify(selectedJob.input_params, null, 2)}
                  </pre>
                </div>
              )}

              {/* Output/Results */}
              {selectedJob.output && (
                <div>
                  <h3 className="text-sm font-medium text-muted-foreground mb-2">Output</h3>
                  <pre className="text-xs bg-secondary p-3 rounded-lg overflow-auto max-h-64">
                    {JSON.stringify(selectedJob.output, null, 2)}
                  </pre>
                </div>
              )}

              {/* Error Message */}
              {selectedJob.error && (
                <div>
                  <h3 className="text-sm font-medium text-destructive mb-2">Error</h3>
                  <div className="bg-destructive/10 border border-destructive/20 p-3 rounded-lg">
                    <p className="text-sm text-destructive">{selectedJob.error}</p>
                  </div>
                </div>
              )}

              {/* Duration */}
              <div>
                <h3 className="text-sm font-medium text-muted-foreground">Duration</h3>
                <p className="mt-1 text-sm">{calculateDuration(selectedJob)}</p>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
