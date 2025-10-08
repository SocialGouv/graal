# Frontend React

## Must Do
- Use React 18 patterns (no class components)
- Enable TypeScript strict mode
- Use Zustand for state management (see [`processingStore.ts`](frontend/src/stores/processingStore.ts))
- Use React Query for API calls (see [`useApi.ts`](frontend/src/hooks/useApi.ts))
- Organize: components/ (UI), hooks/ (logic), stores/ (state), services/ (API)

## Must Not Do
- Use useState for global state (use Zustand instead)
- Make direct fetch calls (use API service layer)
- Skip TypeScript type definitions

## Key Patterns
- Components: Functional components with TypeScript interfaces
- State: `const { status, setStatus } = useProcessingStore()`
- API calls: `const { data, isLoading } = useQuery(...)`
- File structure: `ComponentName/ComponentName.tsx`

## React Query
- Use for server state (job status, results)
- Configure polling for real-time updates
- Handle loading/error states consistently

## TypeScript
- Define props interfaces: `interface ComponentProps { ... }`
- Use auto-generated API types from [`api-generated.ts`](frontend/src/types/api-generated.ts)
- Avoid `any` type (use `unknown` when necessary)
