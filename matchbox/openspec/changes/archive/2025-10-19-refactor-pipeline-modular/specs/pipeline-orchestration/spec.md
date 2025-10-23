# Pipeline Orchestration Capability

## ADDED Requirements

### Requirement: Modular Stage Architecture
The pipeline SHALL organize processing stages as independent, reusable modules under `src/core/stages/` with consistent interfaces.

#### Scenario: Stage module structure
- **WHEN** a developer navigates to `src/core/stages/`
- **THEN** they find separate modules for each processing stage: `fact_description.py`, `function_type.py`, `series.py`, `correction.py`
- **AND** each module has an `__init__.py` declaring `__all__ = ["execute_stage"]`

#### Scenario: Stage execution interface
- **WHEN** a stage module exports an `execute_stage()` function
- **THEN** the function signature SHALL be `execute_stage(image_paths: List[str], settings: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]`
- **AND** the return value SHALL be `(result_json, metadata)` matching the current `call_stage()` pattern

#### Scenario: Stage independence
- **WHEN** a stage module is imported
- **THEN** it SHALL NOT import `src/core/pipeline` (to prevent circular dependencies)
- **AND** it MAY import `src/core/pipeline_utils`, `src/core/messages`, `src/utils.llm_api`, and other utility modules

### Requirement: Pipeline Utilities Module
The pipeline SHALL provide shared utility functions in `src/core/pipeline_utils.py` for directory operations, JSON handling, and metadata generation.

#### Scenario: Utility functions available
- **WHEN** a stage or orchestrator imports `pipeline_utils`
- **THEN** the following functions SHALL be available: `ensure_dir()`, `now_iso()`, `write_json()`, `should_skip_output()`, `fix_or_parse_json()`, `make_meta()`, `merge_series_name_into_object()`
- **AND** these functions SHALL have identical behavior to their current implementations in pipeline.py:19-72

#### Scenario: JSON repair integration
- **WHEN** `fix_or_parse_json(raw: str)` is called with LLM output
- **THEN** it SHALL attempt to repair malformed JSON using `repair_json_output()` from `src/utils/json_repair`
- **AND** return `Optional[Dict[str, Any]]` (None if unrepairable)

### Requirement: Output Formatting Module
The pipeline SHALL delegate CSV/Excel export logic to `src/core/output_formatter.py` for separation of concerns.

#### Scenario: Excel record flattening
- **WHEN** `flatten_record_for_excel(obj: Dict[str, Any])` is called
- **THEN** it SHALL return a flat `Dict[str, str]` with series info reduced to `name` field only
- **AND** exclude all `*_meta` fields from the output
- **AND** handle None values as empty strings, lists joined with `|`

#### Scenario: CSV export
- **WHEN** `write_csv(records: List[Dict[str, str]], out_path: str)` is called
- **THEN** it SHALL dynamically compute headers as the union of all record keys
- **AND** write a UTF-8 CSV file with JSON-quoted cells to handle commas and newlines

### Requirement: Orchestration Layer
The refactored `src/core/pipeline.py` SHALL serve as a thin orchestration layer that composes stage modules without containing stage execution logic.

#### Scenario: Pipeline entry point unchanged
- **WHEN** `run_pipeline(settings: Optional[Dict[str, Any]] = None)` is called
- **THEN** it SHALL execute the same multi-stage workflow: fact description → function type → correction → series analysis
- **AND** produce identical JSON and CSV outputs compared to pre-refactor behavior

#### Scenario: Stage invocation
- **WHEN** the orchestrator processes an image group
- **THEN** it SHALL import and call `execute_stage()` from the appropriate stage module
- **AND** pass image paths, settings, and optional context (prior stage outputs)

#### Scenario: Error handling preserved
- **WHEN** a stage fails (returns None result or raises exception)
- **THEN** the orchestrator SHALL record failure metadata with `make_meta()`
- **AND** continue to the next group (same behavior as pipeline.py:231-242)

### Requirement: Backward Compatibility
The refactored pipeline SHALL maintain 100% backward compatibility with existing configuration, entry points, and output formats.

#### Scenario: No API changes
- **WHEN** existing code calls `run_pipeline()` from `src/core/pipeline`
- **THEN** the function SHALL execute without requiring any code changes
- **AND** accept the same `settings` parameter format

#### Scenario: Configuration compatibility
- **WHEN** the pipeline reads `config/settings.yaml`
- **THEN** all task definitions (`fact_description`, `function_type`, `series`, `correction`) SHALL work unchanged
- **AND** no new configuration keys are required

#### Scenario: Output format preservation
- **WHEN** the pipeline completes processing
- **THEN** the generated JSON files SHALL have identical structure and content compared to pre-refactor
- **AND** the CSV export SHALL produce byte-identical output (modulo timestamp fields)

### Requirement: Stage Module Implementation
Each processing stage SHALL be implemented as a dedicated module in `src/core/stages/` with an `execute_stage()` function that encapsulates stage-specific logic.

#### Scenario: Fact description stage
- **WHEN** `stages/fact_description.py:execute_stage()` is called
- **THEN** it SHALL invoke the `fact_description` or `fact_description_noseries` task based on `context.get("noseries", False)`
- **AND** return parsed JSON and metadata matching pipeline.py:99-103 behavior

#### Scenario: Function type stage
- **WHEN** `stages/function_type.py:execute_stage()` is called with prior fact description in `context`
- **THEN** it SHALL construct user_text from context JSON (pipeline.py:110-114)
- **AND** invoke the `function_type` task to classify the item

#### Scenario: Series stage
- **WHEN** `stages/series.py:execute_stage()` is called
- **THEN** it SHALL invoke the `series` task for series sample groups
- **AND** return series JSON with `name` field (or None on failure)

#### Scenario: Correction stage wrapper
- **WHEN** `stages/correction.py:execute_stage()` is called with fact description JSON in `context`
- **THEN** it SHALL import and delegate to `src/core/correction.stage_correction()`
- **AND** return correction JSON and metadata for structured field validation
