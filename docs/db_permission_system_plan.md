# Amendment Database Permission System — Implementation Plan

This document tracks the full implementation plan for introducing **owner / writer / reader** permissions on amendment databases.
Roles are mutually exclusive; multiple owners are allowed; manifests do not store ownership.

---

## Checklist

### 1. Database Layer
- [ ] Create new table `amendment_database_permissions`
  - [ ] Fields: `db_id`, `user_id`, `role`, `created_at`
  - [ ] Enum roles: `owner`, `writer`, `reader`
  - [ ] Unique constraint `(db_id, user_id)`
- [ ] Create Alembic migration for the table
- [ ] Populate initial permissions for existing DBs (assign current admin or another default as owner)

### 2. Backend Services
- [ ] Implement `DatabasePermissionService`
  - [ ] `get_user_role(db_id, user_id)`
  - [ ] `set_user_role(db_id, user_id, role)`
  - [ ] `remove_user_role(db_id, user_id)`
  - [ ] `list_roles_for_db(db_id)`
  - [ ] `list_accessible_databases(user_id)`
  - [ ] Validate owner demotion (must leave at least one owner)

### 3. Authorization Service Extensions
- [ ] Add `DbRole` Enum (reader, writer, owner)
- [ ] Add hierarchical role rank lookup
- [ ] Add `get_role_for_user` logic calling permission service
- [ ] Add `require_db_role(db_id, min_role)` with hierarchy enforcement

### 4. API Layer
- [ ] Create new router `db_permissions.py`
  - [ ] `GET /api/v1/databases/{db_id}/permissions`
  - [ ] `POST /api/v1/databases/{db_id}/permissions/{user_id}` (owners only)
  - [ ] `DELETE /api/v1/databases/{db_id}/permissions/{user_id}` (owners only)
- [ ] Update existing DB listing endpoints to filter by user permissions (only show DBs where user has ≥ reader)
- [ ] Ensure all endpoints call `require_db_role` at appropriate levels

### 5. Integration With Existing Services
- [ ] Update `SimilarityDatabaseLoader` to require `DbRole.reader`
- [ ] Update `SimilarityDatabaseBuilderService` to require `DbRole.writer`
- [ ] Update any DB mutation features to specify one of:
  - [ ] `REQUIRED_ROLE = DbRole.owner`
  - [ ] `REQUIRED_ROLE = DbRole.writer`
  - [ ] `REQUIRED_ROLE = DbRole.reader`

### 6. Frontend
- [ ] Update database list query to show only permitted DBs
- [ ] Add UI for owners to manage roles
- [ ] Use React Query for permission endpoints
- [ ] Respect DSFR component rules & existing `useAuth` patterns

### 7. Future‑Proofing
- [ ] Ensure every new DB-related feature declares a required role
- [ ] Ensure every new operation uses:
  ```
  await auth.require_db_role(db_id, REQUIRED_ROLE)
  ```

---

This file serves as the progress tracker. Each checkbox will be marked upon completion during implementation.
