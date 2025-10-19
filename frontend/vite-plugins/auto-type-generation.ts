import { exec } from 'child_process'
import chokidar from 'chokidar'
import path from 'path'
import { promisify } from 'util'
import type { Plugin } from 'vite'

const execAsync = promisify(exec)

interface AutoTypeGenerationOptions {
  /**
   * Paths to watch for changes (relative to project root)
   */
  watchPaths?: string[]
  /**
   * Command to run when files change
   */
  generateCommand?: string
  /**
   * Debounce delay in milliseconds
   */
  debounceMs?: number
  /**
   * Whether to generate types on server start
   */
  generateOnStart?: boolean
}

export function autoTypeGeneration(
  options: AutoTypeGenerationOptions = {}
): Plugin {
  const {
    watchPaths = [
      '../graal/api/routes/**/*.py',
      '../graal/api/models/**/*.py',
      '../graal/api/main.py'
    ],
    generateCommand = 'yarn generate-types:dev',
    debounceMs = 1000,
    generateOnStart = true
  } = options

  let watcher: chokidar.FSWatcher | null = null
  let debounceTimer: NodeJS.Timeout | null = null
  let isGenerating = false

  const generateTypes = async () => {
    if (isGenerating) {
      console.log('🔄 Type generation already in progress, skipping...')
      return
    }

    try {
      isGenerating = true
      console.log('🔄 Generating TypeScript types from OpenAPI schema...')

      const { stdout, stderr } = await execAsync(generateCommand)

      if (stderr && !stderr.includes('prettier')) {
        console.warn('⚠️  Type generation warnings:', stderr)
      }

      console.log('✅ TypeScript types generated successfully!')

      if (stdout) {
        console.log('📝 Generation output:', stdout.trim())
      }
    } catch (error) {
      console.error('❌ Failed to generate types:', error)
    } finally {
      isGenerating = false
    }
  }

  const debouncedGenerate = () => {
    if (debounceTimer) {
      clearTimeout(debounceTimer)
    }

    debounceTimer = setTimeout(() => {
      generateTypes()
    }, debounceMs)
  }

  return {
    name: 'auto-type-generation',

    async buildStart() {
      if (generateOnStart) {
        console.log(
          '🚀 Starting development server with auto type generation...'
        )
        await generateTypes()
      }
    },

    configureServer(server) {
      // Set up file watcher
      const absoluteWatchPaths = watchPaths.map((watchPath) =>
        path.resolve(process.cwd(), watchPath)
      )

      watcher = chokidar.watch(absoluteWatchPaths, {
        ignored: [
          '**/node_modules/**',
          '**/.git/**',
          '**/__pycache__/**',
          '**/*.pyc'
        ],
        persistent: true,
        ignoreInitial: true
      })

      watcher.on('change', (filePath: string) => {
        const relativePath = path.relative(process.cwd(), filePath)
        console.log(`📁 Backend file changed: ${relativePath}`)
        debouncedGenerate()
      })

      watcher.on('add', (filePath: string) => {
        const relativePath = path.relative(process.cwd(), filePath)
        console.log(`📁 Backend file added: ${relativePath}`)
        debouncedGenerate()
      })

      watcher.on('unlink', (filePath: string) => {
        const relativePath = path.relative(process.cwd(), filePath)
        console.log(`📁 Backend file removed: ${relativePath}`)
        debouncedGenerate()
      })

      watcher.on('error', (error: any) => {
        console.error('❌ File watcher error:', error)
      })

      console.log('👀 Watching backend files for changes:', absoluteWatchPaths)

      // Clean up on server close
      server.httpServer?.on('close', () => {
        if (watcher) {
          watcher.close()
          console.log('🛑 File watcher stopped')
        }
        if (debounceTimer) {
          clearTimeout(debounceTimer)
        }
      })
    }
  }
}
