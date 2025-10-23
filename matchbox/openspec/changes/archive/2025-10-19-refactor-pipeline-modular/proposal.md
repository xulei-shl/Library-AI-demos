# Refactor Pipeline to Modular Architecture

## Why
The current [pipeline.py](src/core/pipeline.py) contains all pipeline orchestration logic, stage execution, utility functions, and output formatting in a single 285-line file. This makes the code harder to maintain, test, and extend. Decomposing it into focused, single-responsibility modules will improve code organization, testability, and make each processing stage independently reusable.

## What Changes
- Extract pipeline stages (fact description, function type, series analysis, correction) into individual modules under `src/core/stages/`
- Extract utility functions (directory management, JSON I/O, metadata generation) into `src/core/pipeline_utils.py`
- Extract output formatting logic (CSV/Excel export) into `src/core/output_formatter.py`
- Refactor `src/core/pipeline.py` to become a thin orchestration layer that imports and composes the modular components
- Maintain backward compatibility: existing entry point and public API remain unchanged

## Impact
- **Affected specs**: New capability `pipeline-orchestration` defining modular pipeline architecture
- **Affected code**:
  - `src/core/pipeline.py` - refactored to orchestration-only (reduces from ~285 to ~100 lines)
  - `src/core/stages/fact_description.py` - NEW, stage 1 logic
  - `src/core/stages/function_type.py` - NEW, stage 2 logic
  - `src/core/stages/series.py` - NEW, series analysis stage
  - `src/core/stages/correction.py` - NEW, wraps existing correction module
  - `src/core/pipeline_utils.py` - NEW, shared utilities
  - `src/core/output_formatter.py` - NEW, CSV/Excel export
- **Dependencies**: `src/core/correction.py` and `src/core/messages.py` remain unchanged, imported by new stage modules
- **Tests**: No existing tests to update; new modules are testable independently
- **Migration**: Zero-impact refactor, no API changes, no configuration changes
