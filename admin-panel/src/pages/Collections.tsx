import { useEffect, useState, useMemo } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { api } from '@/services/api'
import { Database, Search, ChevronDown, ChevronUp, RefreshCw } from 'lucide-react'

interface VectorConfig {
  size: number
  distance: string
}

interface CollectionConfig {
  params: {
    vectors: VectorConfig | Record<string, VectorConfig>
  }
}

interface Collection {
  name: string
  points_count: number
  vectors_count: number
  config: CollectionConfig
  status: string
  segments_count?: number
  indexed_vectors_count?: number
}

interface CollectionDetails extends Collection {
  payload_schema?: Record<string, unknown>
  optimizer_status?: string
}

export function Collections() {
  const [collections, setCollections] = useState<Collection[]>([])
  const [selectedCollection, setSelectedCollection] = useState<string | null>(null)
  const [collectionDetails, setCollectionDetails] = useState<CollectionDetails | null>(null)
  const [loading, setLoading] = useState(true)
  const [detailsLoading, setDetailsLoading] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc')

  const loadCollections = async () => {
    try {
      setLoading(true)
      const data = await api.listCollections()
      setCollections(data as Collection[])
    } catch (error) {
      console.error('Failed to load collections:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadCollectionDetails = async (name: string) => {
    try {
      setDetailsLoading(true)
      const data = await api.getCollectionInfo(name)
      setCollectionDetails(data as CollectionDetails)
    } catch (error) {
      console.error('Failed to load collection details:', error)
      setCollectionDetails(null)
    } finally {
      setDetailsLoading(false)
    }
  }

  const handleCollectionClick = (name: string) => {
    if (selectedCollection === name) {
      setSelectedCollection(null)
      setCollectionDetails(null)
    } else {
      setSelectedCollection(name)
      loadCollectionDetails(name)
    }
  }

  useEffect(() => {
    loadCollections()
    const interval = setInterval(loadCollections, 30000)
    return () => clearInterval(interval)
  }, [])

  const getVectorSize = (config: CollectionConfig): number => {
    const vectors = config.params.vectors
    if ('size' in vectors && typeof vectors.size === 'number') {
      return vectors.size
    }
    const firstVector = Object.values(vectors)[0] as VectorConfig | undefined
    return firstVector?.size || 0
  }

  const getDistanceMetric = (config: CollectionConfig): string => {
    const vectors = config.params.vectors
    if ('distance' in vectors && typeof vectors.distance === 'string') {
      return vectors.distance
    }
    const firstVector = Object.values(vectors)[0] as VectorConfig | undefined
    return firstVector?.distance || 'Unknown'
  }

  const filteredAndSortedCollections = useMemo(() => {
    let filtered = collections.filter(collection =>
      collection.name.toLowerCase().includes(searchTerm.toLowerCase())
    )

    filtered.sort((a, b) => {
      const aCount = a.points_count || 0
      const bCount = b.points_count || 0
      return sortDirection === 'desc' ? bCount - aCount : aCount - bCount
    })

    return filtered
  }, [collections, searchTerm, sortDirection])

  const toggleSort = () => {
    setSortDirection(prev => prev === 'desc' ? 'asc' : 'desc')
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-muted-foreground">Loading collections...</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Collections</h2>
          <p className="text-muted-foreground">Qdrant vector database collections</p>
        </div>
        <Button onClick={loadCollections} variant="outline" size="sm">
          <RefreshCw className="h-4 w-4" />
          Refresh
        </Button>
      </div>

      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search collections..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-9"
          />
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={toggleSort}
          className="gap-2"
        >
          Points Count
          {sortDirection === 'desc' ? (
            <ChevronDown className="h-4 w-4" />
          ) : (
            <ChevronUp className="h-4 w-4" />
          )}
        </Button>
      </div>

      {filteredAndSortedCollections.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Database className="h-12 w-12 text-muted-foreground mb-4" />
            <p className="text-muted-foreground">
              {searchTerm ? 'No collections found matching your search' : 'No collections found'}
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filteredAndSortedCollections.map((collection) => {
            const isSelected = selectedCollection === collection.name
            const vectorSize = getVectorSize(collection.config)
            const distanceMetric = getDistanceMetric(collection.config)

            return (
              <Card
                key={collection.name}
                className={`cursor-pointer transition-all hover:shadow-md ${
                  isSelected ? 'ring-2 ring-primary' : ''
                }`}
                onClick={() => handleCollectionClick(collection.name)}
              >
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <CardTitle className="text-lg truncate" title={collection.name}>
                        {collection.name}
                      </CardTitle>
                      <CardDescription className="mt-1">
                        <Badge
                          variant={collection.status === 'green' ? 'success' : 'destructive'}
                          className="text-xs"
                        >
                          {collection.status}
                        </Badge>
                      </CardDescription>
                    </div>
                    <Database className="h-5 w-5 text-muted-foreground flex-shrink-0 ml-2" />
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-muted-foreground">Points:</span>
                      <span className="font-semibold">
                        {collection.points_count.toLocaleString()}
                      </span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-muted-foreground">Vectors:</span>
                      <span className="font-semibold">
                        {collection.vectors_count.toLocaleString()}
                      </span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-muted-foreground">Dimension:</span>
                      <span className="font-semibold">{vectorSize}d</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-muted-foreground">Distance:</span>
                      <span className="font-semibold text-xs">{distanceMetric}</span>
                    </div>
                    {collection.segments_count !== undefined && (
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-muted-foreground">Segments:</span>
                        <span className="font-semibold">{collection.segments_count}</span>
                      </div>
                    )}
                  </div>

                  {isSelected && (
                    <div className="mt-4 pt-4 border-t space-y-3">
                      {detailsLoading ? (
                        <div className="text-sm text-muted-foreground text-center py-4">
                          Loading details...
                        </div>
                      ) : collectionDetails ? (
                        <>
                          {collectionDetails.indexed_vectors_count !== undefined && (
                            <div className="flex justify-between items-center">
                              <span className="text-sm text-muted-foreground">Indexed:</span>
                              <span className="text-sm font-medium">
                                {collectionDetails.indexed_vectors_count.toLocaleString()}
                              </span>
                            </div>
                          )}
                          {collectionDetails.optimizer_status && (
                            <div className="flex justify-between items-center">
                              <span className="text-sm text-muted-foreground">Optimizer:</span>
                              <Badge variant="secondary" className="text-xs">
                                {collectionDetails.optimizer_status}
                              </Badge>
                            </div>
                          )}
                          {collectionDetails.payload_schema && (
                            <div className="mt-2">
                              <div className="text-sm font-medium mb-1">Payload Schema:</div>
                              <div className="bg-muted rounded-md p-2 max-h-32 overflow-y-auto">
                                <pre className="text-xs">
                                  {JSON.stringify(collectionDetails.payload_schema, null, 2)}
                                </pre>
                              </div>
                            </div>
                          )}
                        </>
                      ) : (
                        <div className="text-sm text-muted-foreground text-center py-4">
                          Failed to load details
                        </div>
                      )}
                    </div>
                  )}

                  {isSelected && (
                    <div className="mt-3 text-xs text-center text-muted-foreground">
                      Click again to collapse
                    </div>
                  )}
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}

      <div className="flex items-center justify-between text-sm text-muted-foreground">
        <div>
          Showing {filteredAndSortedCollections.length} of {collections.length} collections
        </div>
        <div>
          Total vectors: {collections.reduce((sum, c) => sum + (c.vectors_count || 0), 0).toLocaleString()}
        </div>
      </div>
    </div>
  )
}
