import { useCallback } from 'react'
import { useProcessingStore } from '../../../stores/processingStore'

/**
 * Custom hook to manage all ProcessingConfig handlers
 * Centralizes state updates to reduce code duplication
 */
export const useProcessingConfigHandlers = () => {
    const { processingConfig, setProcessingConfig } = useProcessingStore()

    // Allotments handlers
    const handleAllotmentsEnabledChange = useCallback(
        (checked: boolean) => {
            setProcessingConfig({
                ...processingConfig,
                allotments: {
                    ...processingConfig.allotments,
                    enabled: checked
                }
            })
        },
        [setProcessingConfig, processingConfig]
    )

    const handleAllotmentsColumnChange = useCallback(
        (value: string) => {
            setProcessingConfig({
                ...processingConfig,
                allotments: {
                    ...processingConfig.allotments,
                    column: value as 'Corps amdt' | 'Exposé amdt'
                }
            })
        },
        [setProcessingConfig, processingConfig]
    )

    // Attribution handlers
    const handleAttributionEnabledChange = useCallback(
        (checked: boolean) => {
            setProcessingConfig({
                ...processingConfig,
                attribution: {
                    ...processingConfig.attribution,
                    enabled: checked
                }
            })
        },
        [setProcessingConfig, processingConfig]
    )

    const handleAttributionProjectChange = useCallback(
        (value: string) => {
            setProcessingConfig({
                ...processingConfig,
                attribution: {
                    ...processingConfig.attribution,
                    project_name: value
                }
            })
        },
        [setProcessingConfig, processingConfig]
    )

    const handleAttributionShouldOverwriteChange = useCallback(
        (checked: boolean) => {
            setProcessingConfig({
                ...processingConfig,
                attribution: {
                    ...processingConfig.attribution,
                    should_overwrite: checked
                }
            })
        },
        [setProcessingConfig, processingConfig]
    )

    // Similarity Search handlers
    const handleSimilaritySearchEnabledChange = useCallback(
        (checked: boolean) => {
            setProcessingConfig({
                ...processingConfig,
                similaritySearch: {
                    ...processingConfig.similaritySearch,
                    enabled: checked
                }
            })
        },
        [setProcessingConfig, processingConfig]
    )

    const handleSimilaritySearchOriginProjectChange = useCallback(
        (value: string) => {
            setProcessingConfig({
                ...processingConfig,
                similaritySearch: {
                    ...processingConfig.similaritySearch,
                    originProject: value
                }
            })
        },
        [setProcessingConfig, processingConfig]
    )

    const handleSimilaritySearchDatabaseFileChange = useCallback(
        (value: string | null) => {
            setProcessingConfig({
                ...processingConfig,
                similaritySearch: {
                    ...processingConfig.similaritySearch,
                    databaseFile: value
                }
            })
        },
        [setProcessingConfig, processingConfig]
    )

    const handleSimilaritySearchShouldOverwriteChange = useCallback(
        (checked: boolean) => {
            setProcessingConfig({
                ...processingConfig,
                similaritySearch: {
                    ...processingConfig.similaritySearch,
                    should_overwrite: checked
                }
            })
        },
        [setProcessingConfig, processingConfig]
    )

    const handleColumnsToCopyChange = useCallback(
        (columnsToCopy: Record<string, any>) => {
            setProcessingConfig({
                ...processingConfig,
                similaritySearch: {
                    ...processingConfig.similaritySearch,
                    columnsToCopy
                }
            })
        },
        [setProcessingConfig, processingConfig]
    )

    // Similarities Within Lectures handlers
    const handleSimilaritiesWithinLecturesEnabledChange = useCallback(
        (checked: boolean) => {
            setProcessingConfig({
                ...processingConfig,
                similaritiesWithinLectures: {
                    ...processingConfig.similaritiesWithinLectures,
                    enabled: checked
                }
            })
        },
        [setProcessingConfig, processingConfig]
    )

    const handleSimilaritiesWithinLecturesColumnChange = useCallback(
        (value: string) => {
            setProcessingConfig({
                ...processingConfig,
                similaritiesWithinLectures: {
                    ...processingConfig.similaritiesWithinLectures,
                    column: value as 'Corps amdt' | 'Exposé amdt'
                }
            })
        },
        [setProcessingConfig, processingConfig]
    )

    // Default Opinion handlers
    const handleDefaultOpinionEnabledChange = useCallback(
        (checked: boolean) => {
            setProcessingConfig({
                ...processingConfig,
                defaultOpinion: {
                    ...processingConfig.defaultOpinion,
                    enabled: checked
                }
            })
        },
        [setProcessingConfig, processingConfig]
    )

    const handleDefaultOpinionShouldOverwriteChange = useCallback(
        (checked: boolean) => {
            setProcessingConfig({
                ...processingConfig,
                defaultOpinion: {
                    ...processingConfig.defaultOpinion,
                    should_overwrite: checked
                }
            })
        },
        [setProcessingConfig, processingConfig]
    )

    // Summary Generation handlers
    const handleSummaryGenerationEnabledChange = useCallback(
        (enabled: boolean) => {
            setProcessingConfig({
                ...processingConfig,
                summaryGeneration: {
                    ...processingConfig.summaryGeneration,
                    enabled
                }
            })
        },
        [setProcessingConfig, processingConfig]
    )

    const handleSummaryGenerationShouldOverwriteChange = useCallback(
        (shouldOverwrite: boolean) => {
            setProcessingConfig({
                ...processingConfig,
                summaryGeneration: {
                    ...processingConfig.summaryGeneration,
                    should_overwrite: shouldOverwrite
                }
            })
        },
        [setProcessingConfig, processingConfig]
    )

    const handleSummaryGenerationLlmTypeChange = useCallback(
        (llmType: string) => {
            setProcessingConfig({
                ...processingConfig,
                summaryGeneration: {
                    ...processingConfig.summaryGeneration,
                    llm_type: llmType as any
                }
            })
        },
        [setProcessingConfig, processingConfig]
    )

    const handleSummaryGenerationCredentialsChange = useCallback(
        (credentials: any) => {
            setProcessingConfig({
                ...processingConfig,
                summaryGeneration: {
                    ...processingConfig.summaryGeneration,
                    llm_credentials: credentials
                }
            })
        },
        [setProcessingConfig, processingConfig]
    )

    // Advanced options handlers
    const handlePlaceholderAmdtBodyChange = useCallback(
        (checked: boolean) => {
            setProcessingConfig({
                ...processingConfig,
                placeholder_amdt_body: checked
            })
        },
        [setProcessingConfig, processingConfig]
    )

    return {
        // Allotments
        handleAllotmentsEnabledChange,
        handleAllotmentsColumnChange,

        // Attribution
        handleAttributionEnabledChange,
        handleAttributionProjectChange,
        handleAttributionShouldOverwriteChange,

        // Similarity Search
        handleSimilaritySearchEnabledChange,
        handleSimilaritySearchOriginProjectChange,
        handleSimilaritySearchDatabaseFileChange,
        handleSimilaritySearchShouldOverwriteChange,
        handleColumnsToCopyChange,

        // Similarities Within Lectures
        handleSimilaritiesWithinLecturesEnabledChange,
        handleSimilaritiesWithinLecturesColumnChange,

        // Default Opinion
        handleDefaultOpinionEnabledChange,
        handleDefaultOpinionShouldOverwriteChange,

        // Summary Generation
        handleSummaryGenerationEnabledChange,
        handleSummaryGenerationShouldOverwriteChange,
        handleSummaryGenerationLlmTypeChange,
        handleSummaryGenerationCredentialsChange,

        // Advanced options
        handlePlaceholderAmdtBodyChange
    }
}
