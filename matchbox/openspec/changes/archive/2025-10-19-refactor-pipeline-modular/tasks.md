# Implementation Tasks

## 1. Create Module Infrastructure
- [x] 1.1 Create `src/core/stages/` directory
- [x] 1.2 Create `src/core/stages/__init__.py` with module docstring
- [x] 1.3 Create `src/core/pipeline_utils.py` skeleton
- [x] 1.4 Create `src/core/output_formatter.py` skeleton

## 2. Extract Utility Functions
- [x] 2.1 Move `ensure_dir()`, `now_iso()`, `write_json()` from pipeline.py:19-29 to `pipeline_utils.py`
- [x] 2.2 Move `should_skip_output()` from pipeline.py:31-35 to `pipeline_utils.py`
- [x] 2.3 Move `fix_or_parse_json()` from pipeline.py:37-49 to `pipeline_utils.py`
- [x] 2.4 Move `make_meta()` from pipeline.py:51-61 to `pipeline_utils.py`
- [x] 2.5 Move `merge_series_name_into_object()` from pipeline.py:63-72 to `pipeline_utils.py`
- [x] 2.6 Add imports and type hints to `pipeline_utils.py`

## 3. Extract Output Formatting
- [x] 3.1 Move `flatten_record_for_excel()` from pipeline.py:129-157 to `output_formatter.py`
- [x] 3.2 Move `write_csv()` from pipeline.py:159-178 to `output_formatter.py`
- [x] 3.3 Add imports (`json`, `os`, `List`, `Dict`) to `output_formatter.py`
- [x] 3.4 Import `ensure_dir` from `pipeline_utils` in `output_formatter.py`

## 4. Create Stage Modules
- [x] 4.1 Create `stages/fact_description.py` with `execute_stage()` function
  - Implement logic from `stage_fact_description()` (pipeline.py:99-103)
  - Import `build_messages_for_task`, `invoke_model`, `fix_or_parse_json`, `make_meta`
  - Handle `noseries` flag via context parameter
- [x] 4.2 Create `stages/function_type.py` with `execute_stage()` function
  - Implement logic from `stage_function_type()` (pipeline.py:105-118)
  - Construct user_text from context["previous_json"]
- [x] 4.3 Create `stages/series.py` with `execute_stage()` function
  - Implement logic from `stage_series()` (pipeline.py:120-123)
- [x] 4.4 Create `stages/correction.py` as thin wrapper
  - Import `stage_correction` from `src/core/correction`
  - Extract `input_json` from context and delegate to existing function
- [x] 4.5 Add `__all__ = ["execute_stage"]` to each stage module

## 5. Refactor Pipeline Orchestration
- [x] 5.1 Add imports to `pipeline.py`: `from src.core.pipeline_utils import *`, `from src.core.output_formatter import *`
- [x] 5.2 Add imports for stages: `from src.core.stages import fact_description, function_type, series, correction`
- [x] 5.3 Remove extracted utility functions (lines 19-72) from `pipeline.py`
- [x] 5.4 Remove extracted formatting functions (lines 129-178) from `pipeline.py`
- [x] 5.5 Refactor series group handling (lines 209-224) to call `series.execute_stage()`
- [x] 5.6 Refactor fact description stage (lines 227-242) to call `fact_description.execute_stage()` with `context={"noseries": noseries_flag}`
- [x] 5.7 Refactor function type stage (lines 248-252) to call `function_type.execute_stage()` with `context={"previous_json": fact_json}`
- [x] 5.8 Refactor correction stage (lines 259-267) to call `correction.execute_stage()` with `context={"input_json": fact_json}`
- [x] 5.9 Update CSV export call (lines 279-280) to use `write_csv()` and `flatten_record_for_excel()` from `output_formatter`

## 6. Validation and Testing
- [x] 6.1 Create baseline: run existing pipeline on test images, save outputs to `baseline/`
- [x] 6.2 Run refactored pipeline on same test images, save outputs to `refactored/`
- [x] 6.3 Compare JSON outputs byte-for-byte (ignoring timestamp differences)
- [x] 6.4 Compare CSV outputs for structural equivalence
- [x] 6.5 Verify all group types process correctly: `a_series`, `a_object`, `b`
- [x] 6.6 Check logs for any new errors or warnings
- [x] 6.7 Verify no import errors or circular dependencies

## 7. Documentation
- [x] 7.1 Add module docstrings to all new files explaining purpose and API
- [x] 7.2 Add inline comments in `pipeline.py` explaining stage composition pattern
- [x] 7.3 Update any README or architecture docs if they exist (check `docs/` or root README)

## Notes
- Each stage's `execute_stage()` should follow the signature: `(image_paths, settings, context=None) -> (result_json, metadata)`
- Maintain error handling: stages return `(None, error_meta)` on failure
- No configuration changes required: all task definitions in `settings.yaml` work as-is
- `call_stage()` helper function (pipeline.py:78-97) can be kept as internal helper or deprecated in favor of direct `execute_stage()` calls
