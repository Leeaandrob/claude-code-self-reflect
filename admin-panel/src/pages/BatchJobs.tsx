import { useEffect, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { api } from '@/services/api'
import { formatRelativeTime, formatDuration } from '@/lib/utils'
import {
  Clock,
  CheckCircle,
  XCircle,
  Loader2,
  Eye,
  X,
  RefreshCw,
  Plus,
  Play,
  Search,
  FileText,
  Sparkles,
  Download,
  StopCircle
} from 'lucide-react'

interface BatchJob {
  id: string
  status: 'pending' | 'in_progress' | 'completed' | 'failed' | 'submitted'
  model?: string
  project?: string
  conversations_count: number
  progress: number
  completed_count: number
  failed_count: number
  created_at: string
  updated_at: string
  completed_at?: string
  error?: string
}

interface PendingConversation {
  id: string
  path: string
  project: string
  chunks: number
  imported_at: string
}

interface Model {
  id: string
  name: string
  description: string
  price_input: string
  price_output: string
}

interface NarrativeStats {
  total_narratives: number
  collections: Array<{ name: string; count: number }>
}

export function BatchJobs() {
  const [jobs, setJobs] = useState<BatchJob[]>([])
  const [filteredJobs, setFilteredJobs] = useState<BatchJob[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedJob, setSelectedJob] = useState<BatchJob | null>(null)
  const [statusFilter, setStatusFilter] = useState<string>('all')

  // Create job modal state
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [pendingConversations, setPendingConversations] = useState<PendingConversation[]>([])
  const [selectedConversations, setSelectedConversations] = useState<string[]>([])
  const [models, setModels] = useState<Model[]>([])
  const [selectedModel, setSelectedModel] = useState('qwen-plus')
  const [creating, setCreating] = useState(false)

  // Narrative stats
  const [narrativeStats, setNarrativeStats] = useState<NarrativeStats | null>(null)

  // Search narratives
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<any[]>([])
  const [searching, setSearching] = useState(false)

  useEffect(() => {
    loadJobs()
    loadNarrativeStats()
    const interval = setInterval(loadJobs, 15000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
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

  async function loadNarrativeStats() {
    try {
      const stats = await api.getNarrativeStats() as NarrativeStats
      setNarrativeStats(stats)
    } catch (error) {
      console.error('Failed to load narrative stats:', error)
    }
  }

  async function openCreateModal() {
    setShowCreateModal(true)
    try {
      const [pending, modelsData] = await Promise.all([
        api.getPendingConversations(undefined, 500) as Promise<{ conversations: PendingConversation[] }>,
        api.getBatchModels() as Promise<{ models: Model[]; default: string }>
      ])
      setPendingConversations(pending.conversations || [])
      setModels(modelsData.models || [])
      setSelectedModel(modelsData.default || 'qwen-plus')
    } catch (error) {
      console.error('Failed to load pending conversations:', error)
    }
  }

  async function createJob() {
    if (selectedConversations.length === 0) return

    setCreating(true)
    try {
      await api.createBatchJob(selectedConversations, undefined, selectedModel)
      setShowCreateModal(false)
      setSelectedConversations([])
      loadJobs()
    } catch (error) {
      console.error('Failed to create batch job:', error)
      alert('Failed to create batch job')
    } finally {
      setCreating(false)
    }
  }

  async function refreshJob(jobId: string) {
    try {
      await api.refreshBatchJob(jobId)
      loadJobs()
    } catch (error) {
      console.error('Failed to refresh job:', error)
    }
  }

  async function cancelJob(jobId: string) {
    if (!confirm('Are you sure you want to cancel this job?')) return
    try {
      await api.cancelBatchJob(jobId)
      loadJobs()
    } catch (error) {
      console.error('Failed to cancel job:', error)
    }
  }

  async function processResults(jobId: string) {
    try {
      const result = await api.processBatchResults(jobId) as any
      alert(`Processed ${result.stored_count} narratives`)
      loadNarrativeStats()
    } catch (error) {
      console.error('Failed to process results:', error)
      alert('Failed to process results')
    }
  }

  async function searchNarratives() {
    if (!searchQuery.trim()) return

    setSearching(true)
    try {
      const result = await api.searchNarratives(searchQuery) as { results: any[] }
      setSearchResults(result.results || [])
    } catch (error) {
      console.error('Failed to search narratives:', error)
    } finally {
      setSearching(false)
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
      case 'submitted':
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

  function toggleConversation(id: string) {
    setSelectedConversations(prev =>
      prev.includes(id) ? prev.filter(c => c !== id) : [...prev, id]
    )
  }

  function selectAllConversations() {
    if (selectedConversations.length === pendingConversations.length) {
      setSelectedConversations([])
    } else {
      setSelectedConversations(pendingConversations.map(c => c.id))
    }
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
          <p className="text-muted-foreground">Generate AI-powered narratives for conversations</p>
        </div>
        <div className="flex gap-2">
          <Button onClick={loadJobs} variant="outline" size="sm">
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
          <Button onClick={openCreateModal} size="sm">
            <Plus className="h-4 w-4 mr-2" />
            Create Batch Job
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Total Jobs</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{jobs.length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">In Progress</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">
              {jobs.filter(j => j.status === 'in_progress' || j.status === 'submitted').length}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Completed</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              {jobs.filter(j => j.status === 'completed').length}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Total Narratives</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-purple-600">
              {narrativeStats?.total_narratives || 0}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Search Narratives */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Search className="h-5 w-5" />
            Search Narratives
          </CardTitle>
          <CardDescription>Search stored narratives using semantic similarity</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2">
            <Input
              placeholder="Search for past solutions, decisions, patterns..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && searchNarratives()}
              className="flex-1"
            />
            <Button onClick={searchNarratives} disabled={searching}>
              {searching ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
            </Button>
          </div>

          {searchResults.length > 0 && (
            <div className="mt-4 space-y-3">
              {searchResults.map((result, idx) => (
                <div key={idx} className="p-3 bg-secondary rounded-lg">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <p className="font-medium">{result.summary}</p>
                      {result.problem && (
                        <p className="text-sm text-muted-foreground mt-1">
                          <span className="font-medium">Problem:</span> {result.problem}
                        </p>
                      )}
                      {result.solution && (
                        <p className="text-sm text-muted-foreground mt-1">
                          <span className="font-medium">Solution:</span> {result.solution}
                        </p>
                      )}
                      <div className="flex gap-1 mt-2 flex-wrap">
                        {result.tags?.map((tag: string, i: number) => (
                          <Badge key={i} variant="outline" className="text-xs">{tag}</Badge>
                        ))}
                      </div>
                    </div>
                    <Badge variant="secondary">{Math.round(result.score * 100)}%</Badge>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Filter Controls */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center gap-4">
            <label className="text-sm font-medium">Filter by status:</label>
            <div className="flex gap-2 flex-wrap">
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
                Pending ({jobs.filter(j => j.status === 'pending' || j.status === 'submitted').length})
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
            <div className="text-center py-8">
              <Sparkles className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <p className="text-muted-foreground mb-4">
                {statusFilter === 'all' ? 'No batch jobs found. Create your first job to generate narratives.' : `No ${statusFilter} jobs found`}
              </p>
              {statusFilter === 'all' && (
                <Button onClick={openCreateModal}>
                  <Plus className="h-4 w-4 mr-2" />
                  Create Batch Job
                </Button>
              )}
            </div>
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
                    <CardDescription className="flex items-center gap-2 flex-wrap">
                      {getStatusBadge(job.status)}
                      {job.model && <Badge variant="outline">{job.model}</Badge>}
                      <span>Created {formatRelativeTime(job.created_at)}</span>
                    </CardDescription>
                  </div>
                  <div className="flex gap-2">
                    {(job.status === 'in_progress' || job.status === 'submitted' || job.status === 'pending') && (
                      <>
                        <Button variant="outline" size="sm" onClick={() => refreshJob(job.id)}>
                          <RefreshCw className="h-4 w-4" />
                        </Button>
                        <Button variant="outline" size="sm" onClick={() => cancelJob(job.id)}>
                          <StopCircle className="h-4 w-4" />
                        </Button>
                      </>
                    )}
                    {job.status === 'completed' && (
                      <Button variant="outline" size="sm" onClick={() => processResults(job.id)}>
                        <Download className="h-4 w-4 mr-2" />
                        Process
                      </Button>
                    )}
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => viewJobDetails(job.id)}
                    >
                      <Eye className="h-4 w-4 mr-2" />
                      Details
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-sm">
                  <div>
                    <p className="text-muted-foreground">Progress</p>
                    <div className="flex items-center gap-2 mt-1">
                      <div className="flex-1 h-2 bg-secondary rounded-full overflow-hidden">
                        <div
                          className="h-full bg-primary transition-all duration-300"
                          style={{ width: `${job.progress || 0}%` }}
                        />
                      </div>
                      <span className="font-medium">{job.progress || 0}%</span>
                    </div>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Conversations</p>
                    <p className="font-medium mt-1">{job.conversations_count || 0}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Completed</p>
                    <p className="font-medium mt-1 text-green-600">{job.completed_count || 0}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Failed</p>
                    <p className="font-medium mt-1 text-red-600">{job.failed_count || 0}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Duration</p>
                    <p className="font-medium mt-1">{calculateDuration(job)}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Create Job Modal */}
      {showCreateModal && (
        <div
          className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50"
          onClick={() => setShowCreateModal(false)}
        >
          <Card
            className="max-w-4xl w-full max-h-[80vh] overflow-auto"
            onClick={(e: React.MouseEvent) => e.stopPropagation()}
          >
            <CardHeader>
              <div className="flex items-start justify-between">
                <div>
                  <CardTitle>Create Batch Job</CardTitle>
                  <CardDescription>Select conversations to generate narratives</CardDescription>
                </div>
                <Button variant="ghost" size="icon" onClick={() => setShowCreateModal(false)}>
                  <X className="h-4 w-4" />
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Model Selection */}
              <div>
                <label className="text-sm font-medium mb-2 block">Model</label>
                <div className="grid gap-2 md:grid-cols-3">
                  {models.map((model) => (
                    <div
                      key={model.id}
                      className={`p-3 border rounded-lg cursor-pointer transition-colors ${
                        selectedModel === model.id ? 'border-primary bg-primary/5' : 'hover:border-muted-foreground'
                      }`}
                      onClick={() => setSelectedModel(model.id)}
                    >
                      <p className="font-medium">{model.name}</p>
                      <p className="text-xs text-muted-foreground mt-1">{model.description}</p>
                      <p className="text-xs text-muted-foreground mt-1">
                        {model.price_input} / {model.price_output}
                      </p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Conversations Selection */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-sm font-medium">
                    Conversations without narratives ({pendingConversations.length})
                  </label>
                  <Button variant="outline" size="sm" onClick={selectAllConversations}>
                    {selectedConversations.length === pendingConversations.length ? 'Deselect All' : 'Select All'}
                  </Button>
                </div>
                <div className="border rounded-lg max-h-64 overflow-auto">
                  {pendingConversations.length === 0 ? (
                    <p className="p-4 text-center text-muted-foreground">
                      All conversations already have narratives!
                    </p>
                  ) : (
                    pendingConversations.map((conv) => (
                      <div
                        key={conv.id}
                        className={`p-2 border-b last:border-b-0 flex items-center gap-3 cursor-pointer hover:bg-secondary/50 ${
                          selectedConversations.includes(conv.id) ? 'bg-primary/10' : ''
                        }`}
                        onClick={() => toggleConversation(conv.id)}
                      >
                        <input
                          type="checkbox"
                          checked={selectedConversations.includes(conv.id)}
                          onChange={() => {}}
                          className="h-4 w-4"
                        />
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-mono truncate">{conv.id}</p>
                          <p className="text-xs text-muted-foreground">
                            {conv.project} - {conv.chunks} chunks
                          </p>
                        </div>
                        <span className="text-xs text-muted-foreground">
                          {formatRelativeTime(conv.imported_at)}
                        </span>
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* Summary & Submit */}
              <div className="flex items-center justify-between pt-4 border-t">
                <div className="text-sm text-muted-foreground">
                  {selectedConversations.length} conversations selected
                </div>
                <div className="flex gap-2">
                  <Button variant="outline" onClick={() => setShowCreateModal(false)}>
                    Cancel
                  </Button>
                  <Button
                    onClick={createJob}
                    disabled={selectedConversations.length === 0 || creating}
                  >
                    {creating ? (
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    ) : (
                      <Play className="h-4 w-4 mr-2" />
                    )}
                    Create Job
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Job Details Modal */}
      {selectedJob && (
        <div
          className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50"
          onClick={() => setSelectedJob(null)}
        >
          <Card
            className="max-w-3xl w-full max-h-[80vh] overflow-auto"
            onClick={(e: React.MouseEvent) => e.stopPropagation()}
          >
            <CardHeader>
              <div className="flex items-start justify-between">
                <div>
                  <CardTitle className="font-mono">{selectedJob.id}</CardTitle>
                  <CardDescription className="mt-2 flex items-center gap-2">
                    {getStatusBadge(selectedJob.status)}
                    {selectedJob.model && <Badge variant="outline">{selectedJob.model}</Badge>}
                  </CardDescription>
                </div>
                <Button variant="ghost" size="icon" onClick={() => setSelectedJob(null)}>
                  <X className="h-4 w-4" />
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Timestamps */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <h3 className="text-sm font-medium text-muted-foreground">Created</h3>
                  <p className="mt-1 text-sm">{new Date(selectedJob.created_at).toLocaleString()}</p>
                </div>
                {selectedJob.completed_at && (
                  <div>
                    <h3 className="text-sm font-medium text-muted-foreground">Completed</h3>
                    <p className="mt-1 text-sm">{new Date(selectedJob.completed_at).toLocaleString()}</p>
                  </div>
                )}
              </div>

              {/* Progress */}
              <div>
                <h3 className="text-sm font-medium text-muted-foreground">Progress</h3>
                <div className="mt-2 flex items-center gap-2">
                  <div className="flex-1 h-3 bg-secondary rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary transition-all"
                      style={{ width: `${selectedJob.progress || 0}%` }}
                    />
                  </div>
                  <span className="text-sm font-medium">{selectedJob.progress || 0}%</span>
                </div>
                <div className="mt-2 grid grid-cols-3 gap-4 text-sm">
                  <div>
                    <p className="text-muted-foreground">Total</p>
                    <p className="font-medium">{selectedJob.conversations_count}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Completed</p>
                    <p className="font-medium text-green-600">{selectedJob.completed_count}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Failed</p>
                    <p className="font-medium text-red-600">{selectedJob.failed_count}</p>
                  </div>
                </div>
              </div>

              {/* Error */}
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

              {/* Actions */}
              {selectedJob.status === 'completed' && (
                <div className="pt-4 border-t">
                  <Button onClick={() => processResults(selectedJob.id)} className="w-full">
                    <Download className="h-4 w-4 mr-2" />
                    Process Results & Store Narratives
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
