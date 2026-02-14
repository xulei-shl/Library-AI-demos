---
name: cbdb-query
description: Query China Biographical Database (CBDB) to retrieve historical person information. Use when querying Chinese historical figures (mainly Tang, Song, Ming, Qing dynasties), or when user asks about person life, official positions, social relationships. Auto-triggers when user mentions Chinese historical figures, ancient officials, scholars, poets, or examination candidates.
context: fork
agent: general-purpose
allowed-tools: Read, Bash, Write
---

# CBDB Person Query

China Biographical Database (CBDB) API query for historical person biographical information.

---

## Execution Mode

This skill runs in an **isolated sub-agent context** (`context: fork`).

- Independent conversation history
- Returns structured results to main agent
- Interactive flow handled by calling command/agent

---

## Query Operations

### Basic Query

```bash
# Query by name
python $CLAUDE_PROJECT_DIR/.claude/skills/cbdb-query/scripts/cbdb_api.py --name "person_name" --save

# Query by ID
python $CLAUDE_PROJECT_DIR/.claude/skills/cbdb-query/scripts/cbdb_api.py --id person_id --save

# Query by pinyin
python $CLAUDE_PROJECT_DIR/.claude/skills/cbdb-query/scripts/cbdb_api.py --name "name" --pinyin --save
```

**Output files** (`temps/cbdb/`):
- `cbdb_raw_{identifier}_{timestamp}.json` - Complete API response
- `cbdb_summary_{identifier}_{timestamp}.json` - Extracted summary

### Detail Search

```bash
# Basic search
python $CLAUDE_PROJECT_DIR/.claude/skills/cbdb-query/scripts/cbdb_json_search.py \
    -f temps/cbdb/cbdb_raw_{identifier}_{timestamp}.json \
    -n {node_name} \
    -k "{keyword}" \
    -l 50

# All records (limit=0 or --all)
python $CLAUDE_PROJECT_DIR/.claude/skills/cbdb-query/scripts/cbdb_json_search.py \
    -f temps/cbdb/cbdb_raw_{identifier}_{timestamp}.json \
    -n {node_name} \
    -k "" \
    --all
```

---

## Parameters

### Query Parameters (cbdb_api.py)

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `--name` | string | One of name/id | - | Person name (Chinese or pinyin) |
| `--id` | int | One of name/id | - | CBDB person ID |
| `--pinyin` | flag | No | - | Name is pinyin format |
| `--format` | json/html | No | json | Output format |
| `--save` | flag | No | - | Save results to files |
| `--output-dir` | string | No | temps/cbdb | Output directory |

### Search Parameters (cbdb_json_search.py)

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `-f, --file` | string | Required | Path to JSON file |
| `-n, --node` | string | Required | Node group name to search |
| `-k, --keyword` | string | "" | Keyword filter (empty = all records) |
| `-o, --output` | text/json | text | Output format |
| `-c, --case-sensitive` | flag | false | Case sensitive search |
| `-l, --limit` | int | 20 | Max results (0 = all) |
| `--all` | flag | - | Return all results (ignore limit) |
| `--list-nodes` | flag | - | List available node groups |

---

## Node Types

| Node Name | Description |
|-----------|-------------|
| `BasicInfo` | Basic personal information |
| `PersonAliases` | Aliases |
| `PersonAddresses` | Addresses |
| `PersonPostings` | Official posts/career |
| `PersonSocialStatus` | Social status |
| `PersonKinshipInfo` | Family relationships |
| `PersonSocialAssociation` | Social relationships |
| `PersonTexts` | Related texts/writings |

---

## Output Format

Return structured results for the main agent:

### Query Result

```
Status: success
Person: {chinese_name} ({english_name})
CBDB ID: {cbdb_id}
Birth-Death: {birth_year}-{death_year}
Dynasty: {dynasty}
Brief: {brief_description}

Files saved:
- temps/cbdb/cbdb_raw_{identifier}_{timestamp}.json
- temps/cbdb/cbdb_summary_{identifier}_{timestamp}.json
```

### Search Result

```
Node: {node_name}
Records: {count} found

[Formatted content of search results]
```

---

## Error Handling

| Error Type | Action |
|------------|--------|
| `person_not_found` | Suggest similar names |
| `network_error` | Retry once, then report |
| `invalid_parameter` | Report required parameters |
| `api_error` | Log details and report |
| `multiple_matches` | List candidates for selection |
| `search_error` | Report error, continue without results |

---

## Data Coverage

- **Time Span**: 7th-19th century (Tang to Qing)
- **Richest Data**: Tang, Song, Ming, Qing dynasties
- **Person Types**: Officials, scholars, poets, military personnel
- **Content**: Basic info, addresses, relationships, career, writings

---

## Dependencies

```bash
pip install requests
```