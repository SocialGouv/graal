# Auto-Type Generation System Guide

This guide explains how to set up automatic TypeScript type generation from a FastAPI backend, as implemented in the GRAAL project.

## Overview

The auto-type generation system automatically creates TypeScript types from your FastAPI backend's OpenAPI schema. When backend files change during development, the frontend types are automatically regenerated, ensuring type safety and eliminating manual synchronization.

## How It Works

The system consists of **4 key components** that work together:

### 1. FastAPI Backend with OpenAPI Schema

Your FastAPI backend automatically generates an OpenAPI schema at the `/openapi.json` endpoint. This schema contains all your API routes, request/response models, and type definitions from your Pydantic models.

**Example FastAPI setup:**

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class ProcessingResponse(BaseModel):
    job_id: str
    status: str
    message: str

@app.post("/api/v1/process", response_model=ProcessingResponse)
async def process_amendments():
    # Your endpoint logic
    pass
```

### 2. openapi-typescript Tool

The `openapi-typescript` npm package converts the OpenAPI schema into comprehensive TypeScript types.

**Package.json scripts:**

```json
{
  "scripts": {
    "generate-types": "openapi-typescript http://localhost:8000/openapi.json -o src/types/api-generated.ts",
    "generate-types:dev": "openapi-typescript http://localhost:8000/openapi.json -o src/types/api-generated.ts --prettier"
  }
}
```

**Generated types include:**

- API endpoint paths and methods
- Request/response types
- Component schemas
- Operation definitions

### 3. Custom Vite Plugin for Auto-Watching

The `auto-type-generation.ts` Vite plugin provides automatic file watching and type regeneration:

**Key features:**

- **Watches backend files** (routes, models, main.py) using `chokidar`
- **Debounces changes** (configurable delay) to avoid excessive regeneration
- **Automatically runs** the type generation command when backend files change
- **Generates on startup** to ensure types are current when dev server starts

**Plugin configuration options:**

```typescript
interface AutoTypeGenerationOptions {
  watchPaths?: string[]        // Paths to watch for changes
  generateCommand?: string     // Command to run when files change
  debounceMs?: number         // Debounce delay in milliseconds
  generateOnStart?: boolean   // Whether to generate types on server start
}
```

### 4. Integration in Vite Config

The plugin is configured in `vite.config.ts`:

```typescript
import { autoTypeGeneration } from './vite-plugins/auto-type-generation'

export default defineConfig({
  plugins: [
    react(),
    autoTypeGeneration({
      watchPaths: [
        '../graal/api/routes/**/*.py',
        '../graal/api/models/**/*.py',
        '../graal/api/main.py'
      ],
      generateCommand: 'pnpm generate-types:dev',
      debounceMs: 5000,
      generateOnStart: true
    })
  ]
})
```

## Setup Instructions for New Projects

### Prerequisites

- FastAPI backend that exposes `/openapi.json`
- React/TypeScript frontend with Vite
- Backend and frontend running simultaneously during development

### Step-by-Step Setup

#### 1. Install Dependencies

```bash
npm install -D openapi-typescript chokidar @types/node
```

#### 2. Add Scripts to package.json

```json
{
  "scripts": {
    "generate-types": "openapi-typescript http://localhost:8000/openapi.json -o src/types/api-generated.ts",
    "generate-types:dev": "openapi-typescript http://localhost:8000/openapi.json -o src/types/api-generated.ts --prettier"
  }
}
```

#### 3. Create the Vite Plugin

Create `vite-plugins/auto-type-generation.ts`:

```typescript
import type { Plugin } from 'vite'
import chokidar from 'chokidar'
import { exec } from 'child_process'
import { promisify } from 'util'
import path from 'path'

const execAsync = promisify(exec)

interface AutoTypeGenerationOptions {
  watchPaths?: string[]
  generateCommand?: string
  debounceMs?: number
  generateOnStart?: boolean
}

export function autoTypeGeneration(options: AutoTypeGenerationOptions = {}): Plugin {
  const {
    watchPaths = [
      '../backend/routes/**/*.py',
      '../backend/models/**/*.py',
      '../backend/main.py'
    ],
    generateCommand = 'npm run generate-types:dev',
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
        console.log('🚀 Starting development server with auto type generation...')
        await generateTypes()
      }
    },

    configureServer(server) {
      const absoluteWatchPaths = watchPaths.map(watchPath =>
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
```

#### 4. Configure Vite

Add the plugin to your `vite.config.ts`:

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { autoTypeGeneration } from './vite-plugins/auto-type-generation'

export default defineConfig({
  plugins: [
    react(),
    autoTypeGeneration({
      watchPaths: [
        '../your-backend/routes/**/*.py',
        '../your-backend/models/**/*.py',
        '../your-backend/main.py'
      ],
      generateCommand: 'npm run generate-types:dev',
      debounceMs: 5000,
      generateOnStart: true
    })
  ],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
```

#### 5. Customize Configuration

**Adjust for your project:**

- Update `watchPaths` to match your backend structure
- Change the OpenAPI URL if your backend runs on a different port
- Modify the output path in the generate command if needed
- Adjust debounce timing based on your needs

## Usage

### Development Workflow

1. **Start your FastAPI backend** (must be running for type generation)
2. **Start your frontend dev server** with `pnpm dev`
3. **Types are automatically generated** on startup
4. **Make changes to backend files** (routes, models, etc.)
5. **Types are automatically regenerated** after the debounce delay

### Generated Types Structure

The generated `api-generated.ts` file contains:

```typescript
export interface paths {
  "/api/v1/process": {
    post: operations["process_amendments_api_v1_process_post"];
  };
  // ... other endpoints
}

export interface components {
  schemas: {
    ProcessingResponse: {
      job_id: string;
      status: "queued" | "running" | "completed" | "failed" | "timeout";
      message: string;
    };
    // ... other schemas
  };
}

export interface operations {
  process_amendments_api_v1_process_post: {
    requestBody: {
      content: {
        "multipart/form-data": components["schemas"]["Body_process_amendments_api_v1_process_post"];
      };
    };
    responses: {
      200: {
        content: {
          "application/json": components["schemas"]["ProcessingResponse"];
        };
      };
    };
  };
  // ... other operations
}
```

### Using Generated Types

```typescript
import type { components, operations } from './types/api-generated'

// Use component schemas
type ProcessingResponse = components['schemas']['ProcessingResponse']

// Use operation types
type ProcessEndpoint = operations['process_amendments_api_v1_process_post']
type ProcessRequest = ProcessEndpoint['requestBody']['content']['multipart/form-data']
type ProcessResponse = ProcessEndpoint['responses'][200]['content']['application/json']

// Type-safe API calls
const response: ProcessResponse = await api.post('/api/v1/process', formData)
```

## Benefits

### Type Safety

- **Full TypeScript coverage** for all API interactions
- **Compile-time error detection** for API mismatches
- **IntelliSense support** for API endpoints and data structures

### Developer Experience

- **Auto-sync**: Types automatically update when backend changes
- **No manual maintenance** required
- **Immediate feedback** when API contracts change
- **Seamless integration** with development workflow

### Build Integration

- **Works with any build system** that supports Vite plugins
- **Development and production** type generation
- **CI/CD friendly** with manual generation commands

## Troubleshooting

### Common Issues

**Types not generating:**

- Ensure FastAPI backend is running and accessible
- Check that `/openapi.json` endpoint is available
- Verify watch paths are correct relative to frontend directory

**File watcher not working:**

- Check file permissions on watched directories
- Ensure paths exist and are accessible
- Try adjusting debounce timing

**Generation command fails:**

- Verify `openapi-typescript` is installed
- Check network connectivity to backend
- Ensure output directory exists and is writable

### Debug Tips

- Enable verbose logging in the plugin
- Test manual type generation with `npm run generate-types`
- Check browser network tab for OpenAPI schema availability
- Verify backend Pydantic models are properly typed

## Advanced Configuration

### Multiple Backends

```typescript
// Watch multiple backend services
autoTypeGeneration({
  watchPaths: [
    '../backend-service-1/**/*.py',
    '../backend-service-2/**/*.py',
  ],
  generateCommand: 'npm run generate-types:all'
})
```

### Custom Output Processing

```typescript
// Add custom post-processing
const generateTypes = async () => {
  await execAsync(generateCommand)
  // Add custom transformations
  await execAsync('npm run format-generated-types')
}
```

### Environment-Specific Configuration

```typescript
const isDevelopment = process.env.NODE_ENV === 'development'

autoTypeGeneration({
  generateOnStart: isDevelopment,
  debounceMs: isDevelopment ? 1000 : 5000,
  watchPaths: isDevelopment ? devWatchPaths : prodWatchPaths
})
```

This system ensures your frontend types are always in sync with your backend API, eliminating type mismatches and significantly improving development velocity and code reliability.
