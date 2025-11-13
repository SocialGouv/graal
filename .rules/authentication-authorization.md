# Authentication & Authorization Rules

## Overview

The authentication and authorization system in GRAAL provides access control for admin features. **Current MVP implementation uses hardcoded admin credentials** (any user is automatically granted admin privileges with user ID `"hardcoded-admin"` and email `"admin@graal.gouv.fr"`). This allows frontend development without database infrastructure.

The system follows SOLID principles with a provider-based architecture that enables easy migration to database-backed authentication in the future by changing only the provider implementation.

---

## Backend Architecture

### Core Components

**AuthorizationProvider Interface** ([`authorization_service.py:25`](../graal/api/services/authorization_service.py:25))
- Abstract base class defining the authorization contract
- Enables swapping implementations without changing service code

**HardcodedAuthorizationProvider** ([`authorization_service.py:46`](../graal/api/services/authorization_service.py:46))
- Current MVP implementation returning hardcoded admin user
- All `TODO: DATABASE MIGRATION` comments mark future database query locations

**AuthorizationService** ([`authorization_service.py:86`](../graal/api/services/authorization_service.py:86))
- Singleton service providing:
  - `get_current_user()`: Retrieve current authenticated user
  - `check_admin()`: Check if current user is admin
  - `require_admin()`: Enforce admin access (raises HTTP 403 if not admin)
- Factory: [`get_authorization_service()`](../graal/api/services/authorization_service.py:188)

**UserResponse Model** ([`responses.py:152`](../graal/api/models/responses.py:152))
- **Single source of truth** for user data structure
- Fields: `user_id`, `email`, `is_admin`
- Never create duplicate user models (DRY principle)

**API Endpoint** ([`authorization.py:22`](../graal/api/routes/authorization.py:22))
- `GET /auth/me`: Returns current user info including admin status

---

## Backend Patterns

### ✅ DO

**Use Authorization Service Methods**
```python
from graal.api.services.authorization_service import get_authorization_service

auth_service = get_authorization_service()
user = await auth_service.get_current_user()        # Get current user
is_admin = await auth_service.check_admin()         # Check admin status
user = await auth_service.require_admin()           # Require admin (raises 403 if not)
```

**Use UserResponse for All User Models**
```python
from graal.api.models.responses import UserResponse

# Always use UserResponse - never create duplicate user models
def some_function() -> UserResponse:
    return UserResponse(user_id="123", email="user@example.com", is_admin=False)
```

**Protect Admin Endpoints**
```python
@router.post("/admin/sensitive-operation")
async def admin_only_endpoint():
    auth_service = get_authorization_service()
    user = await auth_service.require_admin()  # Enforce admin access
    # Proceed with admin operation...
```

### ❌ DON'T

**Don't Bypass Authorization Service**
```python
# ❌ WRONG
if user_id == "hardcoded-admin":
    is_admin = True

# ✅ CORRECT
auth_service = get_authorization_service()
is_admin = await auth_service.check_admin()
```

---

## Frontend Architecture

### Core Components

**Auth Store** ([`authStore.ts`](../frontend/src/stores/authStore.ts))
- Zustand global state for user authentication
- Fields: `user`, `error`, `setUser`, `setError`, `clearUser`
- Automatically updated by `useAuth` hook

**useAuth Hook** ([`useAuth.ts`](../frontend/src/hooks/useAuth.ts))
- Primary hook for authentication logic
- Returns: `user`, `isAdmin` (computed from `user.is_admin`), `isLoading`, `error`, `refetch`
- React Query integration with 5-minute cache, no retry on 401/403

**API Integration** ([`api.ts:597`](../frontend/src/services/api.ts:597))
```typescript
async getCurrentUser(): Promise<UserResponse> {
  const response = await this.client.get<UserResponse>('/auth/me')
  return response.data
}
```

**Type Definitions** ([`api.ts:217`](../frontend/src/types/api.ts:217))
- Auto-generated from backend `UserResponse`
- Never manually edit

---

## Frontend Patterns

### ✅ DO

**Use useAuth Hook**
```typescript
import { useAuth } from '../hooks/useAuth'

function MyComponent() {
  const { user, isAdmin, isLoading, error } = useAuth()

  if (isLoading) return <Loading />
  if (error) return <Error message={error} />
  if (!isAdmin) return <AccessDenied />

  return <AdminContent />
}
```

**Conditional Rendering Based on Admin Status**
```typescript
function FeatureList() {
  const { isAdmin } = useAuth()

  return (
    <div>
      <PublicFeature />
      {isAdmin && <AdminOnlyFeature />}
    </div>
  )
}
```

**Check Loading and Error States First**
```typescript
function AdminPage() {
  const { user, isAdmin, isLoading, error } = useAuth()

  if (isLoading) return <Spinner />
  if (error) return <Alert severity="error" description={error} />
  if (!isAdmin) return <Alert severity="warning" description="Accès refusé" />

  return <AdminContent user={user} />
}
```

**Follow Component Pattern** (see [`Admin.tsx`](../frontend/src/components/Admin/Admin.tsx))
- Import `useAuth` hook
- Extract `{ user, isAdmin, isLoading, error }`
- Handle loading/error states before checking `isAdmin`

### ❌ DON'T

**Don't Access authStore Directly**
```typescript
// ❌ WRONG
import { useAuthStore } from '../stores/authStore'
const { user } = useAuthStore()

// ✅ CORRECT
import { useAuth } from '../hooks/useAuth'
const { user } = useAuth()
```

**Don't Call API Directly for User Info**
```typescript
// ❌ WRONG
const response = await apiService.getCurrentUser()

// ✅ CORRECT
const { user } = useAuth()
```

**Don't Check user.is_admin Directly**
```typescript
// ❌ WRONG
if (user?.is_admin) { ... }

// ✅ CORRECT
const { isAdmin } = useAuth()
if (isAdmin) { ... }
```

---

## Adding New Admin Features

### Backend: Create Admin-Only Endpoint

```python
from graal.api.services.authorization_service import get_authorization_service

@router.post("/admin/my-feature")
async def admin_feature():
    auth_service = get_authorization_service()
    user = await auth_service.require_admin()  # Require admin first

    # User is admin if we reach here
    return {"message": "Admin operation completed"}
```

### Frontend: Create Protected Component

```typescript
import { useAuth } from '../../hooks/useAuth'

export const MyAdminFeature = () => {
  const { isAdmin, isLoading, error } = useAuth()

  if (isLoading) return <Loading />
  if (error) return <ErrorDisplay error={error} />
  if (!isAdmin) return <AccessDenied />

  return <div>{/* Your admin feature UI */}</div>
}
```

### Frontend: Add API Method & Use with React Query

```typescript
// In frontend/src/services/api.ts
async myAdminFeature(): Promise<ResponseType> {
  const response = await this.client.post<ResponseType>('/admin/my-feature')
  return response.data
}

// In component
import { useMutation } from '@tanstack/react-query'

const mutation = useMutation({
  mutationFn: () => apiService.myAdminFeature()
})
```
