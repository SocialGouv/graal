# DSPy Integration Plan for GRAAL Summary Generation

## Overview

This plan outlines the integration of DSPy into GRAAL's summary generation system to create model-optimized prompts for different LLM providers and office teams.

### Key Requirements
- Use **MIPROv2** optimizer for best results
- Train **separate prompts per model** (Albert, Scaleway, Ollama, VLLM)
- Store optimized prompts in **S3**: `{office_name}/prompt_for_{model_name}`
- Support **multiple offices** with their own custom prompts
- Maintain **legacy prompt system** as alternative strategy (not fallback)
- Users choose between DSPy-optimized or legacy prompts
- Priority metrics: **semantic quality** > **length** > verb form

---

## Phase 1: Foundation Setup

### 1.1 Dependencies & Project Structure
- [x] Add `dspy-ai` to `pyproject.toml`
- [x] Run `poetry install` to install DSPy
- [x] Create directory structure:
  ```
  graal/summary/dspy_modules/
  ├── signatures.py          # DSPy signature definitions
  ├── programs.py            # DSPy module implementations
  ├── adapters.py            # LLM client → DSPy LM adapters
  ├── optimizers.py          # MIPROv2 optimization logic
  ├── metrics.py             # Evaluation metrics
  ├── dataset.py             # Training data management
  └── storage.py             # S3 prompt storage/retrieval
  ```

### 1.2 Configuration Schema
- [x] Define config schema for DSPy mode in `.rules/configuration.md`
- [x] Add DSPy config section to `config/default.yml`:
  ```yaml
  summary_generation:
    enabled: true
    strategy: "dspy"  # or "legacy"
    should_overwrite: true
    dspy:
      office_name: "office_A"
      s3_prompt_bucket: "graal-prompts"
      s3_prompt_prefix: "summary_prompts/"
  ```
- [x] Update `graal/custom_types.py` with DSPy-related types
---

## Phase 2: DSPy Adapters & Core Components

### 2.1 LLM Client Adapters
- [x] Create `adapters.py` to wrap existing LLM clients as DSPy LMs
- [x] Implement `GraalLMAdapter` base class
- [x] Create specific adapters:
  - [x] `AlbertDSPyAdapter`
  - [x] `ScalewayDSPyAdapter`
  - [x] `OllamaDSPyAdapter`
  - [x] `VllmDSPyAdapter`
- [x] Test adapters with DSPy `Predict` module
- [x] Add unit tests for each adapter

### 2.2 DSPy Signature Definition
- [x] Create `signatures.py`
- [x] Define `AmendmentSummary` signature:
  ```python
  class AmendmentSummary(dspy.Signature):
      """Generate concise French summary for legislative amendment"""
      expose_amdt: str = dspy.InputField(desc="Exposé de l'amendement")
      corps_amdt: str = dspy.InputField(desc="Corps de l'amendement")
      summary: str = dspy.OutputField(desc="Résumé (8-20 mots, commencer par verbe infinitif)")
  ```
- [x] Add documentation with examples
- [x] Write unit tests for signature

### 2.3 DSPy Program Implementation
- [x] Create `programs.py`
- [x] Implement `AmendmentSummarizer` using `dspy.ChainOfThought`
- [x] Add support for model-specific configurations
- [x] Test program with different LM adapters
- [x] Write unit tests

---

## Phase 3: Evaluation Metrics

### 3.1 Metric Implementation
- [x] Create `metrics.py`
- [x] Implement `french_summary_metric()`:
  - [x] **Semantic quality**: Embedding-based similarity to reference
  - [x] **Length constraint**: 8-20 words (strict)
  - [x] **Verb form**: Infinitive verb detection (bonus)
  - [x] Combined score calculation
- [x] Choose embedding model for semantic similarity (e.g., `sentence-transformers`)
- [x] Add French verb form validator (optional, using spaCy or pattern matching)
- [x] Write comprehensive tests for metrics

### 3.2 Metric Configuration
- [x] Define metric weights in configuration:
  ```yaml
  dspy:
    metrics:
      semantic_weight: 0.7
      length_weight: 0.3
      verb_weight: 0.0  # bonus only
  ```
- [x] Document metric calculation methodology

---

## Phase 4: S3 Storage Infrastructure

### 4.1 Prompt Storage Module
- [x] Create `storage.py`
- [x] Implement `DSPyPromptStorage` class:
  - [x] `save_optimized_prompt(office, model, prompt_data)`
  - [x] `load_optimized_prompt(office, model)`
  - [x] `list_available_prompts(office)`
  - [x] Handle versioning (timestamp-based)
- [x] Use existing S3 utilities from `graal/utils/s3_utils.py`
- [x] Add caching layer for frequently accessed prompts
- [x] Write integration tests with mocked S3

### 4.2 S3 Bucket Structure
- [x] Define S3 path structure:
  ```
  s3://summary_prompts/
  ├── office_A/
  │   ├── albert/
  │   │   ├── latest.json
  │   │   └── 2025-10-23_14-30-00.json
  │   ├── scaleway/
  │   └── ollama/
  ├── office_B/
  └── shared/  # optional: shared prompts
  ```
- [x] Document storage format (JSON schema)
- [x] Implement prompt metadata (timestamp, metrics, training info)

---

## Phase 5: Training Dataset Preparation

### 5.1 Dataset Schema
- [x] Define training data format:
  ```python
  {
    "expose_amdt": str,
    "corps_amdt": str,
    "summary": str,  # reference/ground truth
    "metadata": {
      "office": str,
      "quality_score": float,  # optional
      "human_validated": bool
    }
  }
  ```
- [x] Create `graal/summary/dspy_modules/dataset.py`
- [x] Implement dataset loading utilities
- [x] Add train/validation split logic

### 5.2 Dataset Management
- [x] Create script `scripts/prepare_dspy_training_data.py`
- [x] Support multiple input formats:
  - [x] CSV/Excel exports
  - [x] JSON files
  - [x] Parquet files from S3
- [x] Implement data validation and cleaning
- [x] Add dataset statistics reporting
- [x] Store datasets in S3 for reproducibility

---

## Phase 6: MIPROv2 Optimizer Implementation

### 6.1 Optimizer Setup
- [ ] Create `optimizers.py`
- [ ] Implement `AmendmentSummaryOptimizer` class
- [ ] Configure MIPROv2 with appropriate parameters:
  - [ ] Number of candidates
  - [ ] Number of iterations
  - [ ] Batch size
  - [ ] Temperature settings
- [ ] Add progress tracking and logging
- [ ] Implement checkpoint saving during optimization

### 6.2 Model-Specific Optimization
- [ ] Create optimization pipeline for each model type
- [ ] Implement parallel optimization support (optional)
- [ ] Add early stopping based on metric plateau
- [ ] Save optimization history and statistics
- [ ] Document optimal hyperparameters per model

---

## Phase 7: Training & Optimization Scripts

### 7.1 Main Training Script
- [ ] Create `scripts/optimize_summary_prompts.py`
- [ ] Command-line interface:
  ```bash
  python scripts/optimize_summary_prompts.py \
    --office office_A \
    --model albert \
    --train-data path/to/train.json \
    --val-data path/to/val.json \
    --save-to-s3
  ```
- [ ] Support configuration file input
- [ ] Add dry-run mode
- [ ] Implement logging and progress bars
- [ ] Generate optimization report (metrics, examples)

### 7.2 Batch Optimization
- [ ] Create script for optimizing all models at once
- [ ] Add office-specific batch optimization
- [ ] Implement comparison reports across models
- [ ] Add automated testing of optimized prompts

---

## Phase 8: Pipeline Integration

### 8.1 Strategy Selection
- [ ] Update `SummaryHandler` to support strategy selection
- [ ] Implement `DSPySummaryHandler` class
- [ ] Create strategy factory pattern:
  ```python
  strategy = SummaryStrategyFactory.create(
      strategy_type="dspy",  # or "legacy"
      config=config
  )
  ```
- [ ] Load appropriate prompts based on office and model
- [ ] Add fallback logic if DSPy prompt not found

### 8.2 Feature Integration
- [ ] Update `SummaryGenerationFeature` to support both strategies
- [ ] Add strategy selection to configuration
- [ ] Implement prompt caching for performance
- [ ] Add telemetry/logging for strategy usage
- [ ] Update `summary_feature.py` with DSPy support

### 8.3 Load Balancer Integration
- [ ] Update `SummaryGenerationLoadBalancer` for DSPy
- [ ] Support model-specific prompt loading
- [ ] Maintain compatibility with legacy prompts
- [ ] Add performance metrics collection

---

## Phase 9: API & Frontend Support

### 9.1 Backend API Updates
- [ ] Add API endpoint to list available prompts per office
- [ ] Add endpoint to select summary strategy
- [ ] Update processing configuration model in `graal/api/models/requests.py`
- [ ] Add validation for DSPy configuration
- [ ] Update API documentation

### 9.2 Frontend Configuration UI
- [ ] Add strategy selector to `SummaryGenerationConfig.tsx`
- [ ] Display available prompts per model
- [ ] Show optimization metadata (date, metrics)
- [ ] Add prompt management interface
- [ ] Update types in `frontend/src/types/api.ts`

---

## Phase 10: Testing & Validation

### 10.1 Unit Tests
- [ ] Test DSPy adapters
- [ ] Test signature definitions
- [ ] Test metric calculations
- [ ] Test S3 storage operations
- [ ] Test dataset loading utilities
- [ ] Achieve >80% coverage for DSPy modules

### 10.2 Integration Tests
- [ ] Test full DSPy pipeline end-to-end
- [ ] Test strategy switching (DSPy ↔ legacy)
- [ ] Test multi-office prompt loading
- [ ] Test optimization with sample data
- [ ] Test S3 integration with real bucket

### 10.3 Comparison Tests
- [ ] Create benchmark dataset
- [ ] Compare DSPy vs legacy on same data
- [ ] Measure quality metrics for both strategies
- [ ] Generate comparison report
- [ ] Document findings and recommendations

---

## Phase 11: Documentation

### 11.1 Technical Documentation
- [ ] Document DSPy architecture in `.rules/llm-integration.md`
- [ ] Create DSPy usage guide in `docs/dspy_summary_optimization.md`
- [ ] Document training process and best practices
- [ ] Add troubleshooting guide
- [ ] Document S3 prompt structure

### 11.2 User Documentation
- [ ] Write guide for office teams to optimize their prompts
- [ ] Create tutorial with example optimization run
- [ ] Document how to choose between strategies
- [ ] Add FAQ section
- [ ] Create video/walkthrough (optional)

### 11.3 API Documentation
- [ ] Update `docs/api_documentation.md` with DSPy endpoints
- [ ] Add OpenAPI/Swagger specs
- [ ] Document configuration schema
- [ ] Add example requests/responses

---

## Phase 12: Deployment & Monitoring

### 12.1 Deployment Preparation
- [ ] Create migration guide from legacy to DSPy
- [ ] Add feature flag for gradual rollout
- [ ] Set up S3 bucket and permissions
- [ ] Upload initial optimized prompts to S3
- [ ] Create deployment checklist

### 12.2 Monitoring & Observability
- [ ] Add metrics for DSPy strategy usage
- [ ] Track summary quality over time
- [ ] Monitor prompt loading performance
- [ ] Log optimization runs and results
- [ ] Set up alerts for failures

### 12.3 Optimization Workflow
- [ ] Document re-optimization schedule
- [ ] Create automated re-training pipeline (optional)
- [ ] Add prompt version comparison tools
- [ ] Implement A/B testing framework
- [ ] Create prompt performance dashboard

---

## Phase 13: Advanced Features (Optional)

### 13.1 Multi-Office Prompt Sharing
- [ ] Implement shared prompt repository
- [ ] Add prompt import/export between offices
- [ ] Create prompt versioning UI
- [ ] Add prompt forking/merging capabilities

### 13.2 Continuous Optimization
- [ ] Implement incremental learning from new data
- [ ] Add feedback loop from human corrections
- [ ] Create automated re-optimization triggers
- [ ] Implement prompt drift detection

### 13.3 Advanced Metrics
- [ ] Add human evaluation interface
- [ ] Implement inter-rater agreement tracking
- [ ] Create quality degradation alerts
- [ ] Add custom metric definitions per office

---

## Success Criteria

- [ ] DSPy optimization produces better summaries than legacy prompts (measured by metrics)
- [ ] Each office can train and deploy custom prompts independently
- [ ] Model-specific prompts improve performance over universal prompts
- [ ] System maintains backward compatibility with legacy prompts
- [ ] Training pipeline is documented and reproducible
- [ ] S3 storage is reliable and performant
- [ ] Users can easily switch between strategies

---

## Notes & Decisions

### Technology Choices
- **Optimizer**: MIPROv2 (best quality, more computation)
- **Storage**: S3 with JSON format
- **Metrics**: Semantic similarity + length (primary), verb form (bonus)
- **Embedding Model**: TBD - choose during Phase 3

### Open Questions
- [x] Decide on embedding model for semantic similarity
  - **Decision**: Using `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` for French text support
- [ ] Determine optimal training dataset size per model
- [ ] Define re-optimization schedule
- [x] Choose S3 bucket name and region
  - **Decision**: Using `s3://summary_prompts/` as base path
- [x] Decide on prompt caching strategy (Redis? In-memory?)
  - **Decision**: In-memory caching with 5-minute TTL using custom cache implementation

### Future Enhancements
- Support for more LLM providers
- Multi-language support beyond French
- Automated hyperparameter tuning for MIPROv2
- Prompt explanation/interpretability tools
- Integration with human feedback systems
