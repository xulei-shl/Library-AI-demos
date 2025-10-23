# Design: Modular Pipeline Architecture

## Context
The Matchbox pipeline currently lives in a single 285-line file ([pipeline.py](src/core/pipeline.py:1)) that mixes concerns: orchestration logic, stage execution, utilities, metadata generation, and output formatting. As the system grows (e.g., adding new stages or output formats), this monolithic structure becomes harder to navigate, test, and extend.

**Constraints:**
- Must maintain backward compatibility (no API changes)
- Must preserve existing behavior (zero functional changes)
- Must work with existing configuration (`settings.yaml`)
- Python 3.x, no new external dependencies

**Stakeholders:**
- Developers maintaining/extending the pipeline
- Future contributors adding new processing stages

## Goals / Non-Goals

**Goals:**
- Separate orchestration from stage execution logic
- Make each processing stage independently testable and reusable
- Extract utilities and output formatting into focused modules
- Reduce coupling between pipeline components

**Non-Goals:**
- Not changing the multi-stage pipeline flow (fact → function → series → correction)
- Not altering configuration format or entry points
- Not adding new features or capabilities (pure refactor)
- Not introducing new dependencies or frameworks

## Decisions

### Module Organization

**Decision:** Use a `src/core/stages/` directory for all processing stages

**Rationale:**
- Clear separation: stages vs orchestration vs utilities
- Scalable: easy to add new stages without touching main pipeline
- Testable: each stage module can be unit-tested independently

**Structure:**
```
src/core/
├── pipeline.py              # Orchestration only (~100 lines)
├── pipeline_utils.py        # Shared utilities (dir ops, JSON I/O, metadata)
├── output_formatter.py      # CSV/Excel export logic
└── stages/
    ├── __init__.py
    ├── fact_description.py  # Stage 1: fact extraction
    ├── function_type.py     # Stage 2: functional classification
    ├── series.py            # Series analysis stage
    └── correction.py        # Stage 3: field correction wrapper
```

**Alternatives Considered:**
1. **Keep everything in pipeline.py** - Rejected: doesn't solve maintainability problem
2. **Create separate `pipeline/` package** - Rejected: overkill for current scope, adds import complexity
3. **Extract only stages, keep utils in pipeline.py** - Rejected: incomplete separation, utils still mixed with orchestration

### Stage Module API

**Decision:** Each stage module exports a single `execute_stage()` function with signature:
```python
def execute_stage(
    image_paths: List[str],
    settings: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None
) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
    """
    Returns: (result_json, metadata)
    """
```

**Rationale:**
- Consistent interface across all stages
- `context` parameter allows passing prior stage outputs (e.g., fact_description JSON to function_type)
- Matches current `call_stage()` pattern in pipeline.py:78-97

**Alternatives Considered:**
1. **Class-based stages** - Rejected: adds complexity without clear benefit for stateless operations
2. **Different signatures per stage** - Rejected: inconsistent, harder to compose

### Utility Functions

**Decision:** Move utility functions to `pipeline_utils.py`:
- `ensure_dir()`, `now_iso()`, `write_json()`, `should_skip_output()` (lines 19-35)
- `fix_or_parse_json()` (lines 37-49)
- `make_meta()` (lines 51-61)
- `merge_series_name_into_object()` (lines 63-72)

**Rationale:**
- These are pure utility functions with no orchestration logic
- Shared across multiple stages and output formatting
- Can be imported where needed without circular dependencies

**Note:** `call_stage()` (lines 78-97) will be deprecated in favor of individual `execute_stage()` functions

### Output Formatting

**Decision:** Extract CSV/Excel logic to `output_formatter.py`:
- `flatten_record_for_excel()` (lines 129-157)
- `write_csv()` (lines 159-178)

**Rationale:**
- Output formatting is orthogonal to pipeline orchestration
- May need to support additional formats in future (JSON Lines, Parquet, etc.)
- Clean separation: pipeline orchestrates, formatter handles I/O

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| **Import cycles** between stages and utils | Use explicit imports, stages only import utils/messages/llm_api (never pipeline) |
| **Breaking existing code** if imports change | Maintain `pipeline.py` as entry point, no public API changes |
| **Increased file count** (1 file → 8 files) | Benefits outweigh: better organization, clearer responsibilities |
| **Testing burden** without existing tests | Document clear module boundaries; tests can be added incrementally |

**Trade-offs:**
- **More files** vs **better separation**: Accepting ~7 new files for clear single-responsibility modules
- **Import overhead** vs **modularity**: Negligible performance impact, significant maintainability gain

## Migration Plan

**Steps:**
1. Create new module files (`stages/`, `pipeline_utils.py`, `output_formatter.py`)
2. Copy-paste and adapt code from `pipeline.py` to new modules
3. Refactor `pipeline.py` to import and compose new modules
4. Validate: run pipeline on test images, compare outputs byte-for-byte with baseline
5. Manual testing: verify all group types (a_series, a_object, b) process correctly

**Rollback:**
- Git revert to pre-refactor commit
- Zero config changes required

**Verification:**
- Compare JSON outputs before/after refactor (should be identical)
- Compare CSV outputs before/after refactor (should be identical)
- Check logs for any new errors or warnings

## Open Questions
- Should `correction.py` be moved into `stages/` or kept as separate module?
  - **Decision:** Create thin wrapper in `stages/correction.py` that imports existing `src/core/correction.py` to maintain consistency
- Should we add `__all__` exports to stage modules?
  - **Decision:** Yes, for clarity: `__all__ = ["execute_stage"]`
