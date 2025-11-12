import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { useToast } from '@/components/ui/toast'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { api } from '@/services/api'
import type { EmbeddingConfig } from '@/types'
import { RefreshCw, AlertTriangle, Database, Zap } from 'lucide-react'

export function Settings() {
  const [config, setConfig] = useState<EmbeddingConfig | null>(null)
  const [loading, setLoading] = useState(true)
  const [switching, setSwitching] = useState(false)
  const [showConfirmDialog, setShowConfirmDialog] = useState(false)
  const [targetMode, setTargetMode] = useState<'local' | 'voyage' | 'qwen'>('local')
  const { addToast } = useToast()

  useEffect(() => {
    loadConfig()
  }, [])

  const loadConfig = async () => {
    try {
      setLoading(true)
      const data = await api.getEmbeddingConfig() as EmbeddingConfig
      setConfig(data)
    } catch (error) {
      addToast({
        title: 'Error',
        description: 'Failed to load embedding configuration',
        variant: 'error',
      })
      console.error('Failed to load config:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSwitchMode = (mode: 'local' | 'voyage' | 'qwen') => {
    setTargetMode(mode)
    setShowConfirmDialog(true)
  }

  const confirmSwitchMode = async () => {
    try {
      setSwitching(true)
      setShowConfirmDialog(false)

      await api.updateEmbeddingMode(targetMode)

      addToast({
        title: 'Success',
        description: `Switched to ${targetMode.toUpperCase()} embedding mode`,
        variant: 'success',
      })

      await loadConfig()
    } catch (error) {
      addToast({
        title: 'Error',
        description: `Failed to switch to ${targetMode.toUpperCase()} mode`,
        variant: 'error',
      })
      console.error('Failed to switch mode:', error)
    } finally {
      setSwitching(false)
    }
  }

  if (loading) {
    return (
      <div className="p-6">
        <div className="flex items-center justify-center h-64">
          <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </div>
    )
  }

  if (!config) {
    return (
      <div className="p-6">
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">Failed to load configuration</p>
          </CardContent>
        </Card>
      </div>
    )
  }

  const currentMode = config.mode
  const currentConfig = currentMode === 'local' ? config.local : currentMode === 'voyage' ? config.voyage : config.qwen

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground mt-2">
          Configure embedding mode and system preferences
        </p>
      </div>

      {/* Embedding Configuration Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Embedding Configuration</CardTitle>
              <CardDescription className="mt-1.5">
                Control how conversations are embedded for semantic search
              </CardDescription>
            </div>
            <Badge
              variant={currentMode === 'local' ? 'success' : 'info'}
              className="text-sm px-3 py-1"
            >
              {currentMode.toUpperCase()}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Current Configuration */}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                <Database className="h-4 w-4" />
                Model
              </div>
              <p className="text-sm font-mono bg-muted px-3 py-2 rounded-md">
                {currentConfig.model}
              </p>
            </div>

            <div className="space-y-2">
              <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                <Zap className="h-4 w-4" />
                Dimension
              </div>
              <p className="text-sm font-mono bg-muted px-3 py-2 rounded-md">
                {currentConfig.dimension}d
              </p>
            </div>

            {(currentMode === 'voyage' || currentMode === 'qwen') && (
              <div className="space-y-2">
                <div className="text-sm font-medium text-muted-foreground">
                  API Key Status
                </div>
                <Badge variant={currentConfig.api_key_set ? 'success' : 'destructive'}>
                  {currentConfig.api_key_set ? 'Configured' : 'Missing'}
                </Badge>
              </div>
            )}
          </div>

          {/* Warning Banner */}
          <div className="bg-yellow-50 dark:bg-yellow-950 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
            <div className="flex gap-3">
              <AlertTriangle className="h-5 w-5 text-yellow-600 dark:text-yellow-500 flex-shrink-0 mt-0.5" />
              <div className="space-y-1">
                <p className="text-sm font-medium text-yellow-900 dark:text-yellow-200">
                  Important: Switching modes requires rebuilding collections
                </p>
                <p className="text-sm text-yellow-700 dark:text-yellow-300">
                  Collections use different embedding dimensions and are not cross-compatible.
                  Existing collections will remain but won't be searchable in the new mode.
                </p>
              </div>
            </div>
          </div>

          {/* Mode Comparison */}
          <div className="grid gap-4 sm:grid-cols-3">
            {/* Local Mode */}
            <div className={`border rounded-lg p-4 ${currentMode === 'local' ? 'border-green-500 bg-green-50 dark:bg-green-950' : ''}`}>
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold">Local</h3>
                {currentMode === 'local' && (
                  <Badge variant="success" className="text-xs">Current</Badge>
                )}
              </div>
              <ul className="space-y-2 text-sm text-muted-foreground mb-4">
                <li>• Privacy-first</li>
                <li>• 384d FastEmbed</li>
                <li>• No API key</li>
                <li>• Lower cost</li>
              </ul>
              {currentMode !== 'local' && (
                <Button
                  onClick={() => handleSwitchMode('local')}
                  disabled={switching}
                  variant="outline"
                  size="sm"
                  className="w-full"
                >
                  {switching ? (
                    <>
                      <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                      Switching...
                    </>
                  ) : (
                    'Switch'
                  )}
                </Button>
              )}
            </div>

            {/* Voyage Mode */}
            <div className={`border rounded-lg p-4 ${currentMode === 'voyage' ? 'border-blue-500 bg-blue-50 dark:bg-blue-950' : ''}`}>
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold">Voyage AI</h3>
                {currentMode === 'voyage' && (
                  <Badge variant="info" className="text-xs">Current</Badge>
                )}
              </div>
              <ul className="space-y-2 text-sm text-muted-foreground mb-4">
                <li>• Best for search</li>
                <li>• 1024d voyage-3</li>
                <li>• Requires API key</li>
                <li>• Higher accuracy</li>
              </ul>
              {currentMode !== 'voyage' && (
                <Button
                  onClick={() => handleSwitchMode('voyage')}
                  disabled={switching || !config.voyage.api_key_set}
                  variant="outline"
                  size="sm"
                  className="w-full"
                >
                  {switching ? (
                    <>
                      <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                      Switching...
                    </>
                  ) : (
                    'Switch'
                  )}
                </Button>
              )}
              {currentMode !== 'voyage' && !config.voyage.api_key_set && (
                <p className="text-xs text-destructive mt-2">
                  Set VOYAGE_KEY
                </p>
              )}
            </div>

            {/* Qwen Mode */}
            <div className={`border rounded-lg p-4 ${currentMode === 'qwen' ? 'border-purple-500 bg-purple-50 dark:bg-purple-950' : ''}`}>
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold">Qwen (Alibaba)</h3>
                {currentMode === 'qwen' && (
                  <Badge variant="info" className="text-xs bg-purple-500">Current</Badge>
                )}
              </div>
              <ul className="space-y-2 text-sm text-muted-foreground mb-4">
                <li>• Highest quality</li>
                <li>• 2048d text-v4</li>
                <li>• Requires API key</li>
                <li>• Best accuracy</li>
              </ul>
              {currentMode !== 'qwen' && (
                <Button
                  onClick={() => handleSwitchMode('qwen')}
                  disabled={switching || !config.qwen.api_key_set}
                  variant="outline"
                  size="sm"
                  className="w-full"
                >
                  {switching ? (
                    <>
                      <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                      Switching...
                    </>
                  ) : (
                    'Switch'
                  )}
                </Button>
              )}
              {currentMode !== 'qwen' && !config.qwen.api_key_set && (
                <p className="text-xs text-destructive mt-2">
                  Set DASHSCOPE_API_KEY
                </p>
              )}
            </div>
          </div>

          {/* Additional Info */}
          <div className="text-xs text-muted-foreground space-y-1 pt-4 border-t">
            <p>
              <strong>Collection Naming:</strong> Collections use prefixed naming with dimension suffix
            </p>
            <p>
              • Local: <code className="bg-muted px-1 py-0.5 rounded">csr_project_local_384d</code>
            </p>
            <p>
              • Voyage: <code className="bg-muted px-1 py-0.5 rounded">csr_project_voyage_1024d</code>
            </p>
            <p>
              • Qwen: <code className="bg-muted px-1 py-0.5 rounded">csr_project_qwen_2048d</code>
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Confirmation Dialog */}
      <AlertDialog open={showConfirmDialog} onOpenChange={setShowConfirmDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Switch to {targetMode.toUpperCase()} mode?</AlertDialogTitle>
            <AlertDialogDescription className="space-y-3">
              <p>
                This will change the embedding mode from {currentMode.toUpperCase()} to {targetMode.toUpperCase()}.
              </p>
              <div className="bg-muted p-3 rounded-md space-y-2 text-sm">
                <p className="font-medium">What will happen:</p>
                <ul className="list-disc list-inside space-y-1 text-muted-foreground">
                  <li>New embeddings will use {targetMode === 'local' ? '384' : targetMode === 'voyage' ? '1024' : '2048'} dimensions</li>
                  <li>Future conversations will be indexed in new collections</li>
                  <li>Existing {currentMode} collections remain unchanged</li>
                  <li>You may need to re-import conversations for the new mode</li>
                </ul>
              </div>
              <p className="text-sm font-medium text-destructive">
                This action requires rebuilding collections to be searchable in the new mode.
              </p>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={confirmSwitchMode}>
              Continue
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
