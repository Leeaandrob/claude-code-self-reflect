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
import { RefreshCw, AlertTriangle, Database, Zap, Cloud } from 'lucide-react'

export function Settings() {
  const [config, setConfig] = useState<EmbeddingConfig | null>(null)
  const [loading, setLoading] = useState(true)
  const [switching, setSwitching] = useState(false)
  const [showConfirmDialog, setShowConfirmDialog] = useState(false)
  const [targetMode, setTargetMode] = useState<'voyage' | 'qwen'>('voyage')
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

  const handleSwitchMode = (mode: 'voyage' | 'qwen') => {
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
  const isConfigured = currentMode === 'voyage' || currentMode === 'qwen'
  const currentConfig = currentMode === 'voyage' ? config.voyage : currentMode === 'qwen' ? config.qwen : null
  const defaultConfig = { model: 'Not configured', dimension: 0, api_key_set: false }

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground mt-2">
          Configure embedding mode and system preferences
        </p>
      </div>

      {/* Cloud-Only Notice */}
      <div className="bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
        <div className="flex gap-3">
          <Cloud className="h-5 w-5 text-blue-600 dark:text-blue-500 flex-shrink-0 mt-0.5" />
          <div className="space-y-1">
            <p className="text-sm font-medium text-blue-900 dark:text-blue-200">
              Cloud-Only Mode (v8.0.0+)
            </p>
            <p className="text-sm text-blue-700 dark:text-blue-300">
              This system uses cloud embeddings exclusively. Local embeddings have been removed for better search quality.
              Choose between Voyage AI (1024d) or Qwen/DashScope (2048d).
            </p>
          </div>
        </div>
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
              variant={isConfigured ? 'success' : 'destructive'}
              className="text-sm px-3 py-1"
            >
              {isConfigured ? currentMode.toUpperCase() : 'NOT CONFIGURED'}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Current Configuration */}
          {isConfigured && currentConfig && (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                  <Database className="h-4 w-4" />
                  Model
                </div>
                <p className="text-sm font-mono bg-muted px-3 py-2 rounded-md">
                  {currentConfig.model || defaultConfig.model}
                </p>
              </div>

              <div className="space-y-2">
                <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                  <Zap className="h-4 w-4" />
                  Dimension
                </div>
                <p className="text-sm font-mono bg-muted px-3 py-2 rounded-md">
                  {currentConfig.dimension || defaultConfig.dimension}d
                </p>
              </div>

              <div className="space-y-2">
                <div className="text-sm font-medium text-muted-foreground">
                  API Key Status
                </div>
                <Badge variant={currentConfig.api_key_set ? 'success' : 'destructive'}>
                  {currentConfig.api_key_set ? 'Configured' : 'Missing'}
                </Badge>
              </div>
            </div>
          )}

          {/* Unconfigured Warning */}
          {!isConfigured && (
            <div className="bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-lg p-4">
              <div className="flex gap-3">
                <AlertTriangle className="h-5 w-5 text-red-600 dark:text-red-500 flex-shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <p className="text-sm font-medium text-red-900 dark:text-red-200">
                    No API key configured
                  </p>
                  <p className="text-sm text-red-700 dark:text-red-300">
                    Set either <code className="bg-red-100 dark:bg-red-900 px-1 rounded">DASHSCOPE_API_KEY</code> for Qwen
                    or <code className="bg-red-100 dark:bg-red-900 px-1 rounded">VOYAGE_KEY</code> for Voyage AI
                    in your environment to enable embeddings.
                  </p>
                </div>
              </div>
            </div>
          )}

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

          {/* Mode Comparison - Only Voyage and Qwen */}
          <div className="grid gap-4 sm:grid-cols-2">
            {/* Voyage Mode */}
            <div className={`border rounded-lg p-4 ${currentMode === 'voyage' ? 'border-blue-500 bg-blue-50 dark:bg-blue-950' : ''}`}>
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold">Voyage AI</h3>
                {currentMode === 'voyage' && (
                  <Badge variant="info" className="text-xs">Current</Badge>
                )}
              </div>
              <ul className="space-y-2 text-sm text-muted-foreground mb-4">
                <li>• Best for semantic search</li>
                <li>• 1024d voyage-3 model</li>
                <li>• Requires VOYAGE_KEY</li>
                <li>• Excellent accuracy</li>
              </ul>
              {currentMode !== 'voyage' && (
                <Button
                  onClick={() => handleSwitchMode('voyage')}
                  disabled={switching || !config.voyage?.api_key_set}
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
              {currentMode !== 'voyage' && !config.voyage?.api_key_set && (
                <p className="text-xs text-destructive mt-2">
                  Set VOYAGE_KEY env var
                </p>
              )}
            </div>

            {/* Qwen Mode */}
            <div className={`border rounded-lg p-4 ${currentMode === 'qwen' ? 'border-purple-500 bg-purple-50 dark:bg-purple-950' : ''}`}>
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold">Qwen (DashScope)</h3>
                {currentMode === 'qwen' && (
                  <Badge variant="info" className="text-xs bg-purple-500">Current</Badge>
                )}
              </div>
              <ul className="space-y-2 text-sm text-muted-foreground mb-4">
                <li>• Highest quality embeddings</li>
                <li>• 2048d text-embedding-v4</li>
                <li>• Requires DASHSCOPE_API_KEY</li>
                <li>• Best accuracy</li>
              </ul>
              {currentMode !== 'qwen' && (
                <Button
                  onClick={() => handleSwitchMode('qwen')}
                  disabled={switching || !config.qwen?.api_key_set}
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
              {currentMode !== 'qwen' && !config.qwen?.api_key_set && (
                <p className="text-xs text-destructive mt-2">
                  Set DASHSCOPE_API_KEY env var
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
              • Voyage: <code className="bg-muted px-1 py-0.5 rounded">conv_project_voyage_1024d</code>
            </p>
            <p>
              • Qwen: <code className="bg-muted px-1 py-0.5 rounded">conv_project_qwen_2048d</code>
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
                  <li>New embeddings will use {targetMode === 'voyage' ? '1024' : '2048'} dimensions</li>
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
