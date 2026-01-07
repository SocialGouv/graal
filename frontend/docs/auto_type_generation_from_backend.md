# Automatic Type Generation for GRAAL Frontend

This document explains the automatic TypeScript type generation system that keeps frontend and backend schemas synchronized during development.

## Overview

The system automatically regenerates TypeScript types from the FastAPI OpenAPI schema whenever backend files change, ensuring that frontend and backend always stay in sync during development.

## How It Works

### 1. File Watching

The system watches these backend files for changes:

- `../graal/api/routes/**/*.py` - All API route files
- `../graal/api/models/**/*.py` - All Pydantic model files
- `../graal/api/main.py` - Main FastAPI application file

### 2. Automatic Regeneration

When any watched file changes:

1. The change is detected by the file watcher (using `chokidar`)
2. After a 5-second debounce delay, the type generation command runs
3. Types are regenerated from `http://localhost:8000/openapi.json`
4. New types are saved to `src/types/api-generated.ts`

### 3. Development Server Integration

- Types are automatically generated when the dev server starts
- File watching runs alongside the Vite development server
- No manual intervention required during development

## Files Involved

### Core Plugin

- `vite-plugins/auto-type-generation.ts` - Custom Vite plugin that handles file watching and type generation

### Configuration

- `vite.config.ts` - Vite configuration that includes the auto-type-generation plugin
- `tsconfig.node.json` - TypeScript configuration for Node.js environment (includes plugin files)
- `package.json` - Contains type generation scripts and dependencies

### Generated Types

- `src/types/api-generated.ts` - Auto-generated TypeScript types from OpenAPI schema
- `src/types/api.ts` - Re-exports generated types and provides convenience aliases

## Usage

### Starting Development

```bash
cd frontend
pnpm dev
```

The system will:

1. ✅ Generate initial types from the backend
2. ✅ Start the Vite development server
3. ✅ Begin watching backend files for changes

### During Development

When you modify any backend API file:

1. 📁 File change is detected and logged
2. 🔄 Type generation starts automatically
3. ✅ New types are generated and saved
4. 🔄 Frontend automatically picks up the new types

### Manual Type Generation

If needed, you can manually generate types:

```bash
# Basic generation
pnpm generate-types

# With prettier formatting (recommended for development)
pnpm generate-types:dev
```

## Configuration Options

The plugin accepts these options in `vite.config.ts`:

```typescript
autoTypeGeneration({
  // Files to watch for changes
  watchPaths: [
    '../graal/api/routes/**/*.py',
    '../graal/api/models/**/*.py',
    '../graal/api/main.py'
  ],

  // Command to run when files change
  generateCommand: 'pnpm generate-types:dev',

  // Debounce delay in milliseconds
  debounceMs: 1000,

  // Generate types on server start
  generateOnStart: true
})
```

## Benefits

### ✅ Always In Sync

- Frontend types automatically match backend schema
- No more manual type generation steps
- Immediate feedback when backend changes

### ✅ Developer Experience

- Seamless integration with development workflow
- Real-time type checking and IntelliSense
- Automatic error detection for schema mismatches

### ✅ Reliability

- Debounced generation prevents excessive regeneration
- Error handling and logging for troubleshooting
- Graceful cleanup when development server stops

## Troubleshooting

### Backend Not Running

If the backend isn't running on `http://localhost:8000`, type generation will fail. Make sure to start the backend server first:

```bash
# In the root directory
poetry run python start_web_server.py
```

### File Watching Issues

If file changes aren't detected:

1. Check that the watch paths in `vite.config.ts` are correct
2. Verify that the backend files exist at the specified paths
3. Look for error messages in the development server console

### Type Generation Errors

If type generation fails:

1. Ensure the backend server is responding at `/openapi.json`
2. Check that `openapi-typescript` is installed
3. Verify the generate command in `package.json` is correct

## Dependencies

### Required Packages

- `chokidar` - File watching
- `@types/node` - Node.js type definitions
- `openapi-typescript` - OpenAPI to TypeScript conversion

### Installation

These are automatically installed with:

```bash
pnpm install
```

## Integration with Existing Workflow

This system integrates seamlessly with:

- ✅ Vite development server
- ✅ React Hot Module Replacement
- ✅ TypeScript compilation
- ✅ ESLint and Prettier
- ✅ Existing API hooks and services

No changes to existing code are required - the system works transparently in the background.
