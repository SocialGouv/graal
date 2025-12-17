import { Alert } from '@codegouvfr/react-dsfr/Alert'
import { Button } from '@codegouvfr/react-dsfr/Button'
import { ButtonsGroup } from '@codegouvfr/react-dsfr/ButtonsGroup'
import { Input } from '@codegouvfr/react-dsfr/Input'
import { Select } from '@codegouvfr/react-dsfr/Select'
import { Table } from '@codegouvfr/react-dsfr/Table'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import React, { useState } from 'react'
import { apiService } from '../../services/api'
import type { DatabasePermission, UserResponse } from '../../types/api'

interface DatabasePermissionsProps {
  databaseId: string
  databaseName: string
  onClose: () => void
}

const ROLE_DESCRIPTIONS = {
  owner:
    'Contrôle total : peut gérer les permissions, renommer et supprimer la base de données',
  writer:
    'Peut modifier le contenu de la base de données (fonctionnalité future)',
  reader: 'Accès en lecture seule à la base de données'
}

export const DatabasePermissions: React.FC<DatabasePermissionsProps> = ({
  databaseId,
  databaseName,
  onClose
}) => {
  const queryClient = useQueryClient()
  const [emailSearch, setEmailSearch] = useState('')
  const [selectedUser, setSelectedUser] = useState<UserResponse | null>(null)
  const [role, setRole] = useState<'owner' | 'writer' | 'reader'>('reader')
  const [successMessage, setSuccessMessage] = useState<string | null>(null)
  const [userToRemove, setUserToRemove] = useState<string | null>(null)
  const [showUserResults, setShowUserResults] = useState(false)

  // Fetch permissions
  const {
    data: permissions,
    isLoading,
    error
  } = useQuery<DatabasePermission[], Error>({
    queryKey: ['database-permissions', databaseId],
    queryFn: () => apiService.getDatabasePermissions(databaseId)
  })

  // Search users by email
  const { data: userSearchResults } = useQuery<UserResponse[], Error>({
    queryKey: ['user-search', emailSearch],
    queryFn: () => apiService.searchUsersByEmail(emailSearch),
    enabled: emailSearch.length >= 3 && showUserResults
  })

  // Assign permission mutation
  const assignMutation = useMutation({
    mutationFn: (data: {
      user_id: string
      role: 'owner' | 'writer' | 'reader'
    }) => apiService.assignDatabasePermission(databaseId, data),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ['database-permissions', databaseId]
      })
      // Check if this was an update or new assignment
      const wasUpdate =
        selectedUser &&
        permissions?.some((p) => p.user_id === selectedUser.user_id)

      setEmailSearch('')
      setSelectedUser(null)
      setRole('reader')
      setShowUserResults(false)
      setSuccessMessage(
        wasUpdate
          ? 'Permission modifiée avec succès'
          : 'Permission ajoutée avec succès'
      )
      setTimeout(() => setSuccessMessage(null), 3000)
    }
  })

  // Remove permission mutation
  const removeMutation = useMutation({
    mutationFn: (userId: string) =>
      apiService.removeDatabasePermission(databaseId, userId),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ['database-permissions', databaseId]
      })
      setUserToRemove(null)
      setSuccessMessage('Permission retirée avec succès')
      setTimeout(() => setSuccessMessage(null), 3000)
    }
  })

  const handleAssign = (e: React.FormEvent) => {
    e.preventDefault()
    if (selectedUser && role) {
      assignMutation.mutate({ user_id: selectedUser.user_id, role })
    }
  }

  const handleUserSelect = (user: UserResponse) => {
    setSelectedUser(user)
    setEmailSearch(user.email || '')
    setShowUserResults(false)

    // Pre-fill role if user already has permissions
    const existingPerm = permissions?.find((p) => p.user_id === user.user_id)
    if (existingPerm) {
      setRole(existingPerm.role as 'owner' | 'writer' | 'reader')
    } else {
      setRole('reader') // Default for new users
    }
  }

  const handleRemove = (userId: string, userEmail: string) => {
    if (
      window.confirm(
        `Êtes-vous sûr de vouloir retirer les permissions de ${userEmail} ?`
      )
    ) {
      setUserToRemove(userId)
      removeMutation.mutate(userId)
    }
  }

  const ownerCount = permissions?.filter((p) => p.role === 'owner').length || 0

  if (isLoading) {
    return <div>Chargement des permissions...</div>
  }

  if (error) {
    return (
      <Alert
        severity="error"
        title="Erreur"
        description={
          error.message || 'Erreur lors du chargement des permissions'
        }
      />
    )
  }

  return (
    <div>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '2rem'
        }}
      >
        <h2>Permissions pour "{databaseName}"</h2>
        <Button priority="secondary" size="small" onClick={onClose}>
          Retour
        </Button>
      </div>

      {successMessage && (
        <Alert
          severity="success"
          title="Succès"
          description={successMessage}
          style={{ marginBottom: '2rem' }}
        />
      )}

      {/* Role descriptions */}
      <div style={{ marginBottom: '2rem' }}>
        <h3>Rôles disponibles</h3>
        <ul style={{ marginLeft: '1.5rem' }}>
          <li>
            <strong>Propriétaire (Owner) :</strong> {ROLE_DESCRIPTIONS.owner}
          </li>
          <li>
            <strong>Éditeur (Writer) :</strong> {ROLE_DESCRIPTIONS.writer}
          </li>
          <li>
            <strong>Lecteur (Reader) :</strong> {ROLE_DESCRIPTIONS.reader}
          </li>
        </ul>
      </div>

      {/* Add permission form */}
      <div style={{ marginBottom: '3rem' }}>
        <h3>Ajouter ou modifier une permission</h3>
        <p
          style={{ fontSize: '0.875rem', color: '#666', marginBottom: '1rem' }}
        >
          Recherchez un utilisateur par email et attribuez-lui un rôle. Si
          l'utilisateur a déjà un rôle, il sera remplacé par le nouveau.
        </p>
        <form onSubmit={handleAssign}>
          <div style={{ display: 'flex', gap: '1rem', alignItems: 'flex-end' }}>
            <div style={{ flex: 1, position: 'relative' }}>
              <Input
                label="Email de l'utilisateur"
                nativeInputProps={{
                  type: 'text',
                  value: emailSearch,
                  onChange: (e) => {
                    setEmailSearch(e.target.value)
                    setSelectedUser(null)
                    setShowUserResults(true)
                  },
                  onFocus: () => setShowUserResults(true),
                  required: true,
                  placeholder: 'Rechercher par email...'
                }}
              />
              {/* User search results dropdown */}
              {showUserResults &&
                emailSearch.length >= 3 &&
                userSearchResults &&
                userSearchResults.length > 0 && (
                  <div
                    style={{
                      position: 'absolute',
                      top: '100%',
                      left: 0,
                      right: 0,
                      backgroundColor: 'white',
                      border: '1px solid #ddd',
                      borderRadius: '4px',
                      maxHeight: '200px',
                      overflowY: 'auto',
                      zIndex: 1000,
                      boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
                    }}
                  >
                    {userSearchResults.map((user) => {
                      const existingPerm = permissions?.find(
                        (p) => p.user_id === user.user_id
                      )

                      return (
                        <div
                          key={user.user_id}
                          style={{
                            padding: '0.75rem',
                            cursor: 'pointer',
                            borderBottom: '1px solid #eee',
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center'
                          }}
                          onClick={() => handleUserSelect(user)}
                          onMouseEnter={(e) => {
                            e.currentTarget.style.backgroundColor = '#f6f6f6'
                          }}
                          onMouseLeave={(e) => {
                            e.currentTarget.style.backgroundColor = 'white'
                          }}
                        >
                          <div>
                            {user.email}
                            {user.is_admin && (
                              <span
                                style={{
                                  marginLeft: '0.5rem',
                                  fontSize: '0.875rem',
                                  color: '#666'
                                }}
                              >
                                (Admin)
                              </span>
                            )}
                          </div>
                          {existingPerm && (
                            <span
                              style={{
                                fontSize: '0.875rem',
                                color: '#000091',
                                fontWeight: 500
                              }}
                            >
                              {existingPerm.role === 'owner'
                                ? 'Propriétaire'
                                : existingPerm.role === 'writer'
                                  ? 'Éditeur'
                                  : 'Lecteur'}
                            </span>
                          )}
                        </div>
                      )
                    })}
                  </div>
                )}
              {emailSearch.length > 0 &&
                emailSearch.length < 3 &&
                showUserResults && (
                  <p
                    style={{
                      fontSize: '0.875rem',
                      color: '#666',
                      marginTop: '0.25rem'
                    }}
                  >
                    Tapez au moins 3 caractères pour rechercher
                  </p>
                )}
            </div>
            <div style={{ flex: 1 }}>
              <Select
                label="Rôle"
                nativeSelectProps={{
                  value: role,
                  onChange: (e) =>
                    setRole(e.target.value as 'owner' | 'writer' | 'reader')
                }}
              >
                <option value="reader">Lecteur</option>
                <option value="writer">Éditeur</option>
                <option value="owner">Propriétaire</option>
              </Select>
            </div>
            <Button
              type="submit"
              disabled={assignMutation.isPending || !selectedUser}
            >
              {assignMutation.isPending
                ? selectedUser &&
                  permissions?.find((p) => p.user_id === selectedUser.user_id)
                  ? 'Modification...'
                  : 'Ajout...'
                : selectedUser &&
                    permissions?.find((p) => p.user_id === selectedUser.user_id)
                  ? 'Modifier'
                  : 'Ajouter'}
            </Button>
          </div>
        </form>
        {assignMutation.isError && (
          <Alert
            severity="error"
            title="Erreur"
            description={
              (assignMutation.error as any)?.detail ||
              "Erreur lors de l'ajout de la permission"
            }
            style={{ marginTop: '1rem' }}
          />
        )}
      </div>

      {/* Permissions table */}
      <div>
        <h3>Permissions existantes</h3>
        {permissions && permissions.length > 0 ? (
          <Table
            headers={['Email', 'Rôle', "Date d'ajout", 'Actions']}
            data={permissions.map((perm) => {
              const isLastOwner = perm.role === 'owner' && ownerCount <= 1
              const isRemoving = userToRemove === perm.user_id

              return [
                perm.email,
                perm.role === 'owner'
                  ? 'Propriétaire'
                  : perm.role === 'writer'
                    ? 'Éditeur'
                    : 'Lecteur',
                new Date(perm.created_at).toLocaleDateString('fr-FR'),
                <ButtonsGroup
                  key={perm.user_id}
                  buttons={[
                    {
                      children: isRemoving ? 'Suppression...' : 'Retirer',
                      priority: 'secondary',
                      size: 'small',
                      onClick: () => handleRemove(perm.user_id, perm.email),
                      disabled:
                        isLastOwner || removeMutation.isPending || isRemoving,
                      title: isLastOwner
                        ? 'Impossible de retirer le dernier propriétaire'
                        : 'Retirer cette permission'
                    }
                  ]}
                  inlineLayoutWhen="always"
                />
              ]
            })}
          />
        ) : (
          <p>Aucune permission définie</p>
        )}
        {removeMutation.isError && (
          <Alert
            severity="error"
            title="Erreur"
            description={
              (removeMutation.error as any)?.detail ||
              'Erreur lors de la suppression de la permission'
            }
            style={{ marginTop: '1rem' }}
          />
        )}
      </div>
    </div>
  )
}
