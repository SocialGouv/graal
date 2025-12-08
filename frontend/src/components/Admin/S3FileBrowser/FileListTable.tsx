import { fr } from '@codegouvfr/react-dsfr'
import { Button } from '@codegouvfr/react-dsfr/Button'
import { Checkbox } from '@codegouvfr/react-dsfr/Checkbox'
import { Pagination } from '@codegouvfr/react-dsfr/Pagination'
import { Table } from '@codegouvfr/react-dsfr/Table'
import { useState } from 'react'
import type { S3FileMetadata } from '../../../types/api'

interface FileListTableProps {
  files: S3FileMetadata[]
  isLoading: boolean
  onDelete: (fileKeys: string[]) => void
  fileType: 'config' | 'database' | 'input'
}

/**
 * Format file size from bytes to human-readable format
 */
const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

/**
 * Format date to French locale
 */
const formatDate = (dateString: string): string => {
  const date = new Date(dateString)
  return new Intl.DateTimeFormat('fr-FR', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  }).format(date)
}

export const FileListTable = ({
  files,
  isLoading,
  onDelete,
  fileType
}: FileListTableProps) => {
  const ITEMS_PER_PAGE = 50
  const [currentPage, setCurrentPage] = useState(1)
  const [selectedFiles, setSelectedFiles] = useState<Set<string>>(new Set())

  if (isLoading) {
    return (
      <div className={fr.cx('fr-py-4w')}>
        <p>Chargement des fichiers...</p>
      </div>
    )
  }

  if (files.length === 0) {
    return (
      <div className={fr.cx('fr-py-6w')} style={{ textAlign: 'center' }}>
        <p className={fr.cx('fr-text--lead')}>
          {fileType === 'config' && 'Aucun fichier de configuration'}
          {fileType === 'database' && 'Aucune base de données'}
          {fileType === 'input' && "Aucun fichier dans le pool d'entrée"}
        </p>
      </div>
    )
  }

  // Calculate pagination
  const totalPages = Math.ceil(files.length / ITEMS_PER_PAGE)
  const startIndex = (currentPage - 1) * ITEMS_PER_PAGE
  const endIndex = startIndex + ITEMS_PER_PAGE
  const currentFiles = files.slice(startIndex, endIndex)

  // Reset to page 1 if current page is out of bounds
  if (currentPage > totalPages && totalPages > 0) {
    setCurrentPage(1)
  }

  // Handle checkbox selection
  const handleSelectFile = (fileKey: string, checked: boolean) => {
    const newSelected = new Set(selectedFiles)
    if (checked) {
      newSelected.add(fileKey)
    } else {
      newSelected.delete(fileKey)
    }
    setSelectedFiles(newSelected)
  }

  // Handle select all on current page
  const handleSelectAll = (checked: boolean) => {
    const newSelected = new Set(selectedFiles)
    currentFiles.forEach((file) => {
      if (checked) {
        newSelected.add(file.key)
      } else {
        newSelected.delete(file.key)
      }
    })
    setSelectedFiles(newSelected)
  }

  // Check if all visible files are selected
  const allVisibleSelected =
    currentFiles.length > 0 &&
    currentFiles.every((file) => selectedFiles.has(file.key))

  // Handle batch delete
  const handleBatchDelete = () => {
    if (selectedFiles.size > 0) {
      onDelete(Array.from(selectedFiles))
      setSelectedFiles(new Set())
    }
  }

  return (
    <div className={fr.cx('fr-mt-4w')}>
      {/* File count and selection controls */}
      <div
        className={fr.cx('fr-mb-2w')}
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}
      >
        <p className={fr.cx('fr-text--sm')}>
          {files.length} fichier{files.length > 1 ? 's' : ''} au total
          {totalPages > 1 && ` - Page ${currentPage} sur ${totalPages}`}
          {selectedFiles.size > 0 &&
            ` - ${selectedFiles.size} sélectionné${selectedFiles.size > 1 ? 's' : ''}`}
        </p>
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          <Button
            priority="tertiary no outline"
            size="small"
            onClick={() => handleSelectAll(!allVisibleSelected)}
            disabled={files.length === 0}
          >
            {allVisibleSelected
              ? 'Tout désélectionner'
              : 'Tout sélectionner (page actuelle)'}
          </Button>
          <Button
            priority="secondary"
            size="small"
            iconId="ri-delete-bin-line"
            onClick={handleBatchDelete}
            disabled={selectedFiles.size === 0}
          >
            Supprimer ({selectedFiles.size})
          </Button>
        </div>
      </div>

      {/* Scrollable table container */}
      <div
        style={{
          maxHeight: '600px',
          overflowY: 'auto'
        }}
      >
        <Table
          fixed
          headers={['', 'Nom du fichier', 'Taille', 'Dernière modification']}
          data={currentFiles.map((file) => [
            <Checkbox
              key={`checkbox-${file.key}`}
              options={[
                {
                  label: '',
                  nativeInputProps: {
                    checked: selectedFiles.has(file.key),
                    onChange: (e) =>
                      handleSelectFile(file.key, e.target.checked)
                  }
                }
              ]}
            />,
            file.key,
            formatFileSize(file.size),
            formatDate(file.last_modified)
          ])}
        />
      </div>

      {/* Pagination controls */}
      {totalPages > 1 && (
        <div className={fr.cx('fr-mt-4w')}>
          <Pagination
            count={totalPages}
            defaultPage={currentPage}
            getPageLinkProps={(pageNumber) => ({
              onClick: (e) => {
                e.preventDefault()
                setCurrentPage(pageNumber)
                // Scroll to top of table
                window.scrollTo({ top: 0, behavior: 'smooth' })
              },
              href: '#',
              key: `page-${pageNumber}`
            })}
          />
        </div>
      )}
    </div>
  )
}
