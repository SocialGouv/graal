import { Alert } from '@codegouvfr/react-dsfr/Alert'
import { Button } from '@codegouvfr/react-dsfr/Button'
import { ButtonsGroup } from '@codegouvfr/react-dsfr/ButtonsGroup'
import { Input } from '@codegouvfr/react-dsfr/Input'
import { Select } from '@codegouvfr/react-dsfr/Select'
import { Table } from '@codegouvfr/react-dsfr/Table'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import React, { useState } from 'react'
import { apiService } from '../../services/api'
import type {
  ExcelConfigPermission,
  ExcelConfigRole,
  UserResponse
} from '../../types/api'

interface ExcelConfigPermissionsProps {
  configId: string
  configName: string
  onClose: () => void
}

const ROLE_DESCRIPTIONS: Record<ExcelConfigRole, string> = {
  owner:
    'Contrôle total : peut gérer les permissions et supprimer la configuration',
  reader: 'Accès en lecture seule à la configuration'
}

const ROLE_LABELS: Record<ExcelConfigRole, string> = {
  owner: 'Propriétaire',
  reader: 'Lecteur'
}

export const ExcelConfigPermissions: React.FC<ExcelConfigPermissionsProps> = ({
  configId,
  configName,
  onClose
}) => {
  const queryClient = useQueryClient()
  const [emailSearch, setEmailSearch] = useState('')
  const [selectedUser, setSelectedUser] = useState<UserResponse | null>(null)
  const [role, setRole] = useState<ExcelConfigRole>('reader')
  const [successMessage, setSuccessMessage] = useState<string | null>(null)
  const [userToRemove, setUserToRemove] = useState<string | null>(null)
  const [showUserResults, setShowUserResults] = useState(false)

  const {
    data: permissions,
    isLoading,
    error
  } = useQuery<ExcelConfigPermission[], Error>({
    queryKey: ['excel-config-permissions', configId],
    queryFn: () => apiService.getExcelConfigPermissions(configId)
  })

  const { data: userSearchResults } = useQuery<UserResponse[], Error>({
    queryKey: ['excel-config-user-search', emailSearch],
    queryFn: () => apiService.searchUsersByEmail(emailSearch),
    enabled: emailSearch.length >= 3 && showUserResults
  })

  const assignMutation = useMutation({
    mutationFn: (data: { user_id: string; role: ExcelConfigRole }) =>
      apiService.assignExcelConfigPermission(configId, data),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ['excel-config-permissions', configId]
      })

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

  const removeMutation = useMutation({
    mutationFn: (userId: string) =>
      apiService.removeExcelConfigPermission(configId, userId),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ['excel-config-permissions', configId]
      })
      setUserToRemove(null)
      setSuccessMessage('Permission retirée avec succès')
      setTimeout(() => setSuccessMessage(null), 3000)
    }
  })

  const handleAssign = (event: React.FormEvent) => {
    event.preventDefault()
    if (!selectedUser) return
    assignMutation.mutate({ user_id: selectedUser.user_id, role })
  }

  const handleUserSelect = (user: UserResponse) => {
    setSelectedUser(user)
    setEmailSearch(user.email || '')
    setShowUserResults(false)

    const existingPerm = permissions?.find((p) => p.user_id === user.user_id)
    if (existingPerm) {
      setRole(existingPerm.role)
    } else {
      setRole('reader')
    }
  }

  const handleRemove = (userId: string, userEmail: string | null) => {
    if (
      globalThis.confirm(
        `Êtes-vous sûr de vouloir retirer les permissions de ${userEmail || 'cet utilisateur'} ?`
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
        <h2>Permissions pour "{configName}"</h2>
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

      <div style={{ marginBottom: '2rem' }}>
        <h3>Rôles disponibles</h3>
        <ul style={{ marginLeft: '1.5rem' }}>
          <li>
            <strong>Propriétaire (Owner) :</strong> {ROLE_DESCRIPTIONS.owner}
          </li>
          <li>
            <strong>Lecteur (Reader) :</strong> {ROLE_DESCRIPTIONS.reader}
          </li>
        </ul>
      </div>

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
                  onChange: (event) => {
                    setEmailSearch(event.target.value)
                    setSelectedUser(null)
                    setShowUserResults(true)
                  },
                  onFocus: () => setShowUserResults(true),
                  onBlur: () => {
                    // Delay to allow click on an option before closing
                    setTimeout(() => setShowUserResults(false), 150)
                  },
                  required: true,
                  placeholder: 'Rechercher par email...'
                }}
              />
              {showUserResults &&
                emailSearch.length >= 3 &&
                userSearchResults &&
                userSearchResults.length > 0 && (
                  <ul
                    aria-label="Résultats de recherche d'utilisateurs"
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
                      boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                      listStyle: 'none',
                      padding: 0,
                      margin: 0
                    }}
                  >
                    {userSearchResults.map((user) => {
                      const existingPerm = permissions?.find(
                        (p) => p.user_id === user.user_id
                      )

                      return (
                        <li
                          key={user.user_id}
                          style={{ borderBottom: '1px solid #eee' }}
                        >
                          <button
                            type="button"
                            aria-pressed={
                              selectedUser?.user_id === user.user_id
                            }
                            style={{
                              padding: '0.75rem',
                              cursor: 'pointer',
                              display: 'flex',
                              justifyContent: 'space-between',
                              alignItems: 'center',
                              width: '100%',
                              background: 'transparent',
                              border: 'none',
                              textAlign: 'left'
                            }}
                            onClick={() => handleUserSelect(user)}
                            onMouseEnter={(event) => {
                              event.currentTarget.style.backgroundColor =
                                '#f6f6f6'
                            }}
                            onMouseLeave={(event) => {
                              event.currentTarget.style.backgroundColor =
                                'transparent'
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
                                {ROLE_LABELS[existingPerm.role]}
                              </span>
                            )}
                          </button>
                        </li>
                      )
                    })}
                  </ul>
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
                  onChange: (event) =>
                    setRole(event.target.value as ExcelConfigRole)
                }}
              >
                <option value="reader">Lecteur</option>
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

      <div>
        <h3>Permissions existantes</h3>
        {permissions && permissions.length > 0 ? (
          <Table
            headers={['Email', 'Rôle', "Date d'ajout", 'Actions']}
            data={permissions.map((perm) => {
              const isLastOwner = perm.role === 'owner' && ownerCount <= 1
              const isRemoving = userToRemove === perm.user_id

              return [
                perm.email || '—',
                ROLE_LABELS[perm.role],
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
