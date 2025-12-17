# Authentication & Authorization Rules

## Overview

The authentication and authorization system in GRAAL provides access control for admin features. **Current MVP implementation uses hardcoded admin credentials** (any user is automatically granted admin privileges with user ID `"hardcoded-admin"` and email `"admin@graal.gouv.fr"`). This allows frontend development without database infrastructure.

The system follows SOLID principles with a provider-based architecture that enables easy migration to database-backed authentication in the future by changing only the provider implementation.

---

## Backend Architecture

### Core Components

**Auth Dependencies Module** ([`dependencies/auth.py`](../graal/api/dependencies/auth.py))
- **PRIMARY PATTERN**: Use FastAPI dependency injection for all auth
- `CurrentUser`: Type alias for authenticated user dependency
- `AdminUser`: Type alias for admin-only dependency
- Provides `get_current_user()` and `require_admin()` as FastAPI dependencies

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
- **Note**: Service is now primarily used via dependency injection

**UserResponse Model** ([`responses.py:152`](../graal/api/models/responses.py:152))
- **Single source of truth** for user data structure
- Fields: `user_id`, `email`, `is_admin`
- Never create duplicate user models (DRY principle)

**API Endpoint** ([`authorization.py:22`](../graal/api/routes/authorization.py:22))
- `GET /auth/me`: Returns current user info including admin status

---

## Backend Patterns

### ✅ DO

**Use FastAPI Dependencies (PRIMARY PATTERN)**
```python
from graal.api.dependencies.auth import CurrentUser, AdminUser

# For routes that need authenticated user
@router.get("/my-route")
async def my_route(current_user: CurrentUser):
    # current_user is automatically authenticated (401 if not)
    # Type: UserResponse with user_id, email, is_admin
    print(f"User {current_user.user_id} is accessing route")
    return {"message": "Success"}

# For admin-only routes
@router.post("/admin/sensitive")
async def admin_route(admin_user: AdminUser):
    # admin_user is automatically validated as admin (403 if not)
    # No manual auth checks needed!
    return {"message": "Admin operation completed"}
```

**Access User Data from Dependency**
```python
@router.post("/update-profile")
async def update_profile(data: ProfileData, current_user: CurrentUser):
    # Use current_user fields directly
    user_id = current_user.user_id
    email = current_user.email
    is_admin = current_user.is_admin

    # Perform operation with user context
    return {"updated_by": user_id}
```

**Protect Entire Router (Alternative Pattern)**
```python
from fastapi import APIRouter, Depends
from graal.api.dependencies.auth import get_current_user, require_admin

# All routes in this router require authentication
router = APIRouter(
    prefix="/user",
    dependencies=[Depends(get_current_user)]  # Applied to all routes
)

@router.get("/profile")  # Automatically protected!
async def get_profile():
    # No need to add current_user param if you don't need user data
    return {"message": "Profile data"}

@router.get("/settings", response_model=Settings)
async def get_settings(current_user: CurrentUser):
    # Can still access user if needed by adding the param
    return get_user_settings(current_user.user_id)

# For admin-only routers
admin_router = APIRouter(
    prefix="/admin",
    dependencies=[Depends(require_admin)]  # All routes require admin
)
```

**Use UserResponse for All User Models**
```python
from graal.api.models.responses import UserResponse

# Always use UserResponse - never create duplicate user models
def some_function() -> UserResponse:
    return UserResponse(user_id="123", email="user@example.com", is_admin=False)
```

### ❌ DON'T

**Don't Use Manual Auth Checks in Routes**
```python
# ❌ WRONG - Don't do this anymore!
@router.post("/my-route")
async def my_route(request: Request, session: Optional[str] = Cookie(default=None)):
    auth_service = get_authorization_service()
    user = await auth_service.get_current_user(request, session)
    # ...

# ✅ CORRECT - Use dependency injection
@router.post("/my-route")
async def my_route(current_user: CurrentUser):
    # Auth is automatic!
    # ...
```

**Don't Manually Check Admin Status in Routes**
```python
# ❌ WRONG
@router.post("/admin/feature")
async def admin_feature(current_user: CurrentUser):
    if not current_user.is_admin:
        raise HTTPException(403, "Not admin")
    # ...

# ✅ CORRECT - Use AdminUser dependency
@router.post("/admin/feature")
async def admin_feature(admin_user: AdminUser):
    # Admin check is automatic!
    # ...
```

**Don't Bypass Dependency Injection**
```python
# ❌ WRONG
if user_id == "hardcoded-admin":
    is_admin = True

# ✅ CORRECT - Let FastAPI handle it
# Just use CurrentUser or AdminUser dependency
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
from graal.api.dependencies.auth import AdminUser

@router.post("/admin/my-feature")
async def admin_feature(admin_user: AdminUser):
    # admin_user is automatically validated as admin (403 if not)
    # No manual auth checks needed!

    # Access user info if needed
    print(f"Admin {admin_user.email} performed operation")

    return {"message": "Admin operation completed"}
```

### Backend: Create Authenticated (Non-Admin) Endpoint

```python
from graal.api.dependencies.auth import CurrentUser

@router.get("/user/my-data")
async def get_user_data(current_user: CurrentUser):
    # current_user is automatically authenticated (401 if not)
    # Available to any authenticated user (not just admins)

    user_id = current_user.user_id
    # Fetch and return user-specific data
    return {"user_id": user_id, "data": "..."}
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

### Frontend: Protect Routes with ProtectedRoute

```typescript
// In App.tsx - wrap routes that require authentication
import { ProtectedRoute } from './components/ProtectedRoute'

<Routes>
  <Route path="/" element={<Home />} />

  {/* Routes requiring authentication */}
  <Route
    path="/processing"
    element={
      <ProtectedRoute>
        <ProcessingPage />
      </ProtectedRoute>
    }
  />

  {/* Admin-only routes */}
  <Route
    path="/admin"
    element={
      <ProtectedRoute requireAdmin>
        <AdminPage />
      </ProtectedRoute>
    }
  />
</Routes>
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
