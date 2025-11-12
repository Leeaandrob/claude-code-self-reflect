export interface Project {
  name: string
  file_count: number
  message_count: number
  last_updated: string
  collection_local?: string
  collection_cloud?: string
}

export interface ImportStats {
  total_files: number
  imported_files: number
  pending_files: number
  total_messages: number
  import_progress: number
}

export interface FileImportStatus {
  path: string
  hash: string
  imported_at: string
  project: string
  message_count: number
  status: 'imported' | 'pending' | 'error'
}

export interface Collection {
  name: string
  vectors_count: number
  points_count: number
  segments_count: number
  status: 'green' | 'yellow' | 'red'
  config: {
    params: {
      vectors: {
        size: number
        distance: string
      }
    }
  }
}

export interface DockerService {
  name: string
  status: 'running' | 'stopped' | 'starting' | 'error'
  container_id?: string
  uptime?: string
  memory_usage?: number
  cpu_usage?: number
  profile: string[]
}

export interface BatchJob {
  id: string
  status: 'queued' | 'processing' | 'completed' | 'failed'
  created_at: string
  updated_at: string
  conversations_count: number
  project: string
  result_url?: string
}

export interface SystemMetrics {
  qdrant: {
    status: 'connected' | 'disconnected'
    collections_count: number
    total_vectors: number
  }
  embedding: {
    mode: 'local' | 'cloud'
    model: string
    dimension: number
  }
  import: ImportStats
  memory: {
    used: number
    total: number
    percentage: number
  }
}

export interface LogEntry {
  timestamp: string
  level: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL'
  service: string
  message: string
}

export interface EmbeddingConfig {
  mode: 'local' | 'cloud'
  local: {
    model: string
    dimension: number
  }
  cloud: {
    provider: 'voyage' | 'openai'
    model: string
    dimension: number
    api_key_set: boolean
  }
}
