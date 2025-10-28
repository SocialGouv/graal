# DSPy Prompt Optimization Guide

This guide explains how to use the DSPy prompt optimization system to train model-specific prompts for amendment summary generation.

## Overview

The GRAAL DSPy integration provides tools to optimize prompts using MIPROv2, creating model-specific prompts that are saved to S3 for production use.

## Prerequisites

1. **Training Data**: Prepared training and validation datasets
2. **Environment Variables**: LLM API credentials configured
3. **S3 Access**: S3 bucket configured for prompt storage

### Required Environment Variables

Depending on which model you're optimizing for:

**Albert:**
```bash
export ETALAB_API_KEY="<your_key>"
export ETALAB_BASE_URL="https://albert.api.etalab.gouv.fr/v1"
export ETALAB_MODEL_NAME="meta-llama/Meta-Llama-3.1-70B-Instruct"
```

**Scaleway:**
```bash
export SCALEWAY_API_KEY="<your_key>"
export SCALEWAY_BASE_URL="https://api.scaleway.ai/v1"
export SCALEWAY_MODEL_NAME="meta-llama/Meta-Llama-3.3-70B-Instruct"
```

**Ollama:**
```bash
export OLLAMA_ENDPOINT="http://localhost:11434"
export OLLAMA_MODEL_NAME="llama3.1"
export OLLAMA_USER="user"
export OLLAMA_PASSWORD="<password>"
```

**VLLM:**
```bash
export VLLM_ENDPOINT="http://your-vllm-server:8000"
export VLLM_MODEL_NAME="meta-llama/Llama-3.1-70B"
export VLLM_USER="user"
export VLLM_PASSWORD="<password>"
```

**S3 Storage:**
```bash
export S3_BUCKET_NAME="your-bucket"
export S3_BUCKET_ENDPOINT="https://s3.region.scw.cloud"
export S3_BUCKET_ACCESS_KEY="<your_access_key>"
export S3_BUCKET_SECRET_KEY="<your_secret_key>"
export S3_BUCKET_REGION="region"
```

## Step 1: Prepare Training Data

First, prepare your training datasets using the [`prepare_dspy_training_data.py`](../scripts/prepare_dspy_training_data.py) script:

```bash
python scripts/prepare_dspy_training_data.py \
  --input data/raw_training_data.json \
  --output-dir data/dspy_training/ \
  --validate \
  --train-ratio 0.8
```

This will create:
- `data/dspy_training/train.json` - Training set (80%)
- `data/dspy_training/validation.json` - Validation set (20%)

## Step 2: Run Optimization

### Basic Usage

Optimize prompts for a specific model and office:

```bash
python scripts/optimize_summary_prompts.py \
  --office office_A \
  --model albert \
  --train-data data/dspy_training/train.json \
  --val-data data/dspy_training/validation.json \
  --save-to-s3
```

### Dry Run Mode

Test your configuration without running optimization:

```bash
python scripts/optimize_summary_prompts.py \
  --office office_A \
  --model albert \
  --train-data data/dspy_training/train.json \
  --val-data data/dspy_training/validation.json \
  --dry-run
```

This will:
- Load and validate the training data
- Display dataset statistics
- Show configuration parameters
- Exit without running optimization

### Custom Hyperparameters

Adjust optimization parameters:

```bash
python scripts/optimize_summary_prompts.py \
  --office office_A \
  --model scaleway \
  --train-data data/train.json \
  --val-data data/val.json \
  --num-candidates 15 \
  --num-iterations 30 \
  --early-stopping-patience 5 \
  --save-to-s3
```

**Key Parameters:**
- `--num-candidates`: Number of prompt candidates per iteration (default: 10)
- `--num-iterations`: Maximum optimization iterations (default: 50)
- `--batch-size`: Batch size for processing (default: 25)
- `--early-stopping-patience`: Stop if no improvement for N iterations (default: 0=disabled)
- `--rate-limit-per-minute`: Max API calls per minute (default: 0=unlimited)

### Metric Weights

Customize the evaluation metric weights:

```bash
python scripts/optimize_summary_prompts.py \
  --office office_A \
  --model albert \
  --train-data data/train.json \
  --val-data data/val.json \
  --semantic-weight 0.8 \
  --length-weight 0.2 \
  --verb-weight 0.0 \
  --save-to-s3
```

**Metric Components:**
- `--semantic-weight`: Semantic similarity to reference (default: 0.7)
- `--length-weight`: Length constraint (8-20 words) (default: 0.3)
- `--verb-weight`: Infinitive verb form bonus (default: 0.0)

### Loading Data from S3

Load training datasets directly from S3:

```bash
python scripts/optimize_summary_prompts.py \
  --office office_B \
  --model vllm \
  --train-data s3://dspy_datasets/office_B/train \
  --val-data s3://dspy_datasets/office_B/val \
  --save-to-s3
```

### Save Optimization Report

Generate and save a detailed optimization report:

```bash
python scripts/optimize_summary_prompts.py \
  --office office_A \
  --model albert \
  --train-data data/train.json \
  --val-data data/val.json \
  --save-to-s3 \
  --report-path reports/optimization_albert_office_A.json
```

The report includes:
- Dataset statistics
- Optimization results (scores, iterations, time)
- Progress history
- S3 storage information

### Checkpointing

Save intermediate checkpoints during optimization:

```bash
python scripts/optimize_summary_prompts.py \
  --office office_A \
  --model albert \
  --train-data data/train.json \
  --val-data data/val.json \
  --checkpoint-dir checkpoints/albert/ \
  --save-to-s3
```

Checkpoints are saved every 10 iterations by default.

## Step 3: Verify Optimized Prompts

After optimization, verify the prompt was saved to S3:

**S3 Path Structure:**
```
s3://your-bucket/summary_prompts/
├── office_A/
│   ├── albert/
│   │   ├── latest.json
│   │   └── 2025-10-28_15-30-00.json
│   ├── scaleway/
│   │   └── latest.json
│   └── vllm/
│       └── latest.json
└── office_B/
    └── ollama/
        └── latest.json
```

## Complete Examples

### Example 1: Optimize for Multiple Models

Optimize prompts for all models in your office:

```bash
# Albert
python scripts/optimize_summary_prompts.py \
  --office office_A \
  --model albert \
  --train-data data/office_A/train.json \
  --val-data data/office_A/val.json \
  --num-iterations 50 \
  --save-to-s3 \
  --report-path reports/albert.json

# Scaleway
python scripts/optimize_summary_prompts.py \
  --office office_A \
  --model scaleway \
  --train-data data/office_A/train.json \
  --val-data data/office_A/val.json \
  --num-iterations 50 \
  --save-to-s3 \
  --report-path reports/scaleway.json

# VLLM
python scripts/optimize_summary_prompts.py \
  --office office_A \
  --model vllm \
  --train-data data/office_A/train.json \
  --val-data data/office_A/val.json \
  --num-iterations 50 \
  --save-to-s3 \
  --report-path reports/vllm.json
```

### Example 2: Production Optimization

Recommended settings for production optimization:

```bash
python scripts/optimize_summary_prompts.py \
  --office production_office \
  --model albert \
  --train-data s3://training-data/production/train \
  --val-data s3://training-data/production/val \
  --num-candidates 15 \
  --num-iterations 100 \
  --batch-size 50 \
  --early-stopping-patience 10 \
  --rate-limit-per-minute 60 \
  --checkpoint-dir checkpoints/production/ \
  --save-to-s3 \
  --report-path reports/production_optimization.json \
  --verbose
```

### Example 3: Quick Test Optimization

For quick testing with small datasets:

```bash
python scripts/optimize_summary_prompts.py \
  --office test_office \
  --model albert \
  --train-data data/test_train_small.json \
  --val-data data/test_val_small.json \
  --num-candidates 5 \
  --num-iterations 10 \
  --batch-size 10 \
  --report-path reports/test_run.json
```

## Understanding the Output

### Console Output

During optimization, you'll see:

```
================================================================================
                   DSPy Prompt Optimization: office_A / albert
================================================================================

--------------------------------------------------------------------------------
Loading Training Data
--------------------------------------------------------------------------------
✓ Loaded 150 training examples
✓ Loaded 30 validation examples

Training Set Statistics:
  Total examples: 150
  Summary length (words):
    mean: 12.45
    min: 8
    max: 20
    median: 12

--------------------------------------------------------------------------------
Creating LLM Client: albert
--------------------------------------------------------------------------------
✓ Created albert client: albert

--------------------------------------------------------------------------------
Creating DSPy Adapter
--------------------------------------------------------------------------------
✓ Created DSPy adapter for albert

--------------------------------------------------------------------------------
Initializing Optimizer
--------------------------------------------------------------------------------
✓ Optimizer initialized

================================================================================
                      Running MIPROv2 Optimization
================================================================================

This may take a while depending on dataset size and iterations...
Progress will be logged as optimization proceeds.

2025-10-28 15:30:00 - Iteration 1/50: train=0.6500, val=0.6200, best=0.6200 (iter 1), improvement=+0.0000, elapsed=45.2s
2025-10-28 15:35:00 - Iteration 10/50: train=0.7800, val=0.7600, best=0.7600 (iter 10), improvement=+0.0100, elapsed=350.5s
...
```

### Optimization Report

The JSON report contains:

```json
{
  "optimization_info": {
    "office": "office_A",
    "model": "albert",
    "timestamp": "2025-10-28 15:45:00"
  },
  "dataset_info": {
    "train_size": 150,
    "val_size": 30,
    "train_summary_length": {...},
    "val_summary_length": {...}
  },
  "optimization_results": {
    "best_score": 0.8523,
    "train_score": 0.8612,
    "num_iterations": 50,
    "total_time_seconds": 3245.7,
    "early_stopped": false
  },
  "optimization_history": {
    "iterations": 50,
    "initial_val_score": 0.6200,
    "final_val_score": 0.8523
  },
  "s3_info": {
    "saved": true,
    "version": "2025-10-28_15-45-00"
  }
}
```
