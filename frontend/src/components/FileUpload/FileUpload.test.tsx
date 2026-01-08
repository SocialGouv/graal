import { fireEvent, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it } from 'vitest'
import { useProcessingStore } from '../../stores/processingStore'
import FileUpload from './FileUpload'

const makeJsonFile = (data: unknown, filename = 'amendements.json') => {
  const blob = new Blob([JSON.stringify(data)], { type: 'application/json' })
  return new File([blob], filename, { type: 'application/json' })
}

describe('FileUpload - mission filter', () => {
  beforeEach(() => {
    useProcessingStore.getState().reset()
  })

  it('should extract missions and allow adding/removing/clearing mission filters', async () => {
    const user = userEvent.setup()

    const onFileSelect = (file: File | null) =>
      useProcessingStore.getState().setUploadedFile(file)
    render(<FileUpload onFileSelect={onFileSelect} disabled={false} />)
    const input = screen.getByLabelText(/fichier json des amendements/i)
    const file = makeJsonFile({
      amendements: [
        { mission_titre_court: 'Santé' },
        { mission_titre_court: 'Travail' },
        { mission_titre_court: 'Santé' },
        { mission_titre_court: '  Solidarité  ' }
      ]
    })
    // DSFR Upload hides the native input (pointer-events: none), so we trigger a change event
    fireEvent.change(input, { target: { files: [file] } })
    expect(screen.getByText(/filtrer par mission/i)).toBeInTheDocument()
    // Ensure missions were extracted (multi-combobox should appear, not the "no mission" message)
    const missionInput = await screen.findByLabelText(/missions sélectionnées/i)
    await user.click(missionInput)
    // select "Santé"
    const listbox = screen.getByRole('listbox')
    await user.click(within(listbox).getByText('Santé'))
    // input should be cleared after selection so we can immediately select another mission
    expect(missionInput).toHaveValue('')
    // dropdown should remain visible (multi-pick UX)
    expect(screen.getByRole('listbox')).toBeInTheDocument()
    // selected chip appears (remove button)
    expect(
      screen.getByRole('button', { name: /retirer santé/i })
    ).toBeInTheDocument()
    expect(
      useProcessingStore.getState().processingConfig.missionShortTitleFilter
    ).toEqual(['Santé'])
    // select "Travail"
    await user.click(missionInput)
    await user.click(within(screen.getByRole('listbox')).getByText('Travail'))
    expect(
      useProcessingStore.getState().processingConfig.missionShortTitleFilter
    ).toEqual(['Santé', 'Travail'])
    // remove "Santé" (via chip remove button)
    await user.click(screen.getByRole('button', { name: /retirer santé/i }))
    expect(
      useProcessingStore.getState().processingConfig.missionShortTitleFilter
    ).toEqual(['Travail'])
    // clear
    await user.click(screen.getByRole('button', { name: /tout effacer/i }))
    expect(
      useProcessingStore.getState().processingConfig.missionShortTitleFilter
    ).toEqual([])
  })

  it('should allow navigating between chips with arrow keys and deleting a selected chip', async () => {
    const user = userEvent.setup()
    const onFileSelect = (file: File | null) =>
      useProcessingStore.getState().setUploadedFile(file)
    render(<FileUpload onFileSelect={onFileSelect} disabled={false} />)

    const input = screen.getByLabelText(/fichier json des amendements/i)
    const file = makeJsonFile({
      amendements: [
        { mission_titre_court: 'Santé' },
        { mission_titre_court: 'Travail' },
        { mission_titre_court: 'Solidarité' }
      ]
    })

    fireEvent.change(input, { target: { files: [file] } })

    const missionInput = await screen.findByLabelText(/missions sélectionnées/i)
    await user.click(missionInput)

    await user.click(within(screen.getByRole('listbox')).getByText('Santé'))
    await user.click(within(screen.getByRole('listbox')).getByText('Travail'))
    await user.click(
      within(screen.getByRole('listbox')).getByText('Solidarité')
    )

    // Move from the input to the last chip
    await user.type(missionInput, '{ArrowLeft}')

    // Then move to the previous chip and delete it
    await user.keyboard('{ArrowLeft}')
    await user.keyboard('{Delete}')

    expect(
      useProcessingStore.getState().processingConfig.missionShortTitleFilter
    ).toEqual(['Santé', 'Solidarité'])
  })

  it('should restore available missions when remounting with an already selected file', async () => {
    const user = userEvent.setup()

    const onFileSelect = (file: File | null) =>
      useProcessingStore.getState().setUploadedFile(file)

    const file = makeJsonFile({
      amendements: [
        { mission_titre_court: 'Santé' },
        { mission_titre_court: 'Travail' }
      ]
    })

    // Seed the store as if the user had already selected a file before navigating away.
    useProcessingStore.getState().setUploadedFile(file)

    render(<FileUpload onFileSelect={onFileSelect} disabled={false} />)

    const missionInput = await screen.findByLabelText(/missions sélectionnées/i)
    await user.click(missionInput)

    expect(screen.getByRole('listbox')).toBeInTheDocument()
    expect(within(screen.getByRole('listbox')).getByText('Santé')).toBeVisible()
    expect(
      within(screen.getByRole('listbox')).getByText('Travail')
    ).toBeVisible()
  })
})
