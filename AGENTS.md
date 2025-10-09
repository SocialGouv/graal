# Agent Instructions for GRAAL Project

This project uses **modular rules** instead of one large instruction file. Rules are split into focused files in the `.rules/` directory, each covering a specific domain.

## ⚠️ Critical Requirement

**BEFORE starting ANY coding work, you MUST read the relevant rule files using the `read_file` tool.**

Rule files contain essential project-specific requirements, patterns, and constraints. Violating these rules will result in rejected code.

---

## Available Rule Files

| File | Domain | Purpose |
|------|--------|---------|
| [`architecture-features.md`](.rules/architecture-features.md) | Architecture & Features | Feature system, pipeline patterns, async patterns |
| [`backend-fastapi.md`](.rules/backend-fastapi.md) | FastAPI Backend | API structure, routes, error handling |
| [`backend-python.md`](.rules/backend-python.md) | Python Standards | Code style, type hints, naming conventions |
| [`frontend-react.md`](.rules/frontend-react.md) | React Frontend | Component patterns, state management, hooks |
| [`frontend-dsfr.md`](.rules/frontend-dsfr.md) | DSFR Design System | French gov design system usage |
| [`data-processing.md`](.rules/data-processing.md) | Data Processing | DataFrame operations, data validation |
| [`testing-standards.md`](.rules/testing-standards.md) | Testing | Test structure, fixtures, coverage |
| [`configuration.md`](.rules/configuration.md) | Configuration | Config files, environment variables |
| [`llm-integration.md`](.rules/llm-integration.md) | LLM Integration | Prompt engineering, LLM client usage |
| [`performance.md`](.rules/performance.md) | Performance | Async operations, optimization patterns |

---

## Rule Selection Guide

### Backend API Development
**MUST READ:**
- `.rules/backend-fastapi.md`
- `.rules/backend-python.md`

**SHOULD READ:**
- `.rules/architecture-features.md` (if implementing features)
- `.rules/performance.md` (if async/performance critical)

### Frontend Component Development
**MUST READ:**
- `.rules/frontend-react.md`
- `.rules/frontend-dsfr.md`

**SHOULD READ:**
- `.rules/performance.md` (if performance critical)

### Feature Implementation
**MUST READ:**
- `.rules/architecture-features.md`
- `.rules/backend-python.md`

**SHOULD READ:**
- `.rules/backend-fastapi.md` (if API exposed)
- `.rules/data-processing.md` (if data manipulation)

### Data Processing Tasks
**MUST READ:**
- `.rules/data-processing.md`
- `.rules/backend-python.md`

**SHOULD READ:**
- `.rules/performance.md` (for large datasets)

### Testing Work
**MUST READ:**
- `.rules/testing-standards.md`
- `.rules/backend-python.md`

### LLM/AI Integration
**MUST READ:**
- `.rules/llm-integration.md`
- `.rules/backend-python.md`

**SHOULD READ:**
- `.rules/performance.md` (for async LLM calls)

### Configuration Changes
**MUST READ:**
- `.rules/configuration.md`

### Performance Optimization
**MUST READ:**
- `.rules/performance.md`
- `.rules/backend-python.md`

---

## How to Use

1. **Identify your task** from the categories above
2. **Fetch MUST READ rules** using `read_file` tool before any code changes
3. **Follow rules as strict requirements** - they define project standards
4. **Fetch SHOULD READ rules** if your task touches those areas
5. **Ask for clarification** if rules conflict with your assigned task

## Example Workflow

```
Task: Add new API endpoint for similarity search

Step 1: Identify category → Backend API Development
Step 2: Read required rules:
  - read_file('.rules/backend-fastapi.md')
  - read_file('.rules/backend-python.md')
Step 3: Implement following the patterns defined in rules
Step 4: If using features, read architecture-features.md
```

---

**Remember:** These rules exist to maintain consistency and quality. Not following them will result in code that doesn't fit the project's patterns and standards.
