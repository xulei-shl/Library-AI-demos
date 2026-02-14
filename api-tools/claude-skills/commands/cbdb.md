---
description: Query CBDB database for Chinese historical figures biographical information. Use when user explicitly invokes /cbdb or asks to query a specific person from CBDB.
argument-hint: [person_name|person_id]
allowed-tools: Read, Bash, Write, Skill
---

# CBDB Query Command

Query China Biographical Database (CBDB) for historical person information.

## Input

User provides: `$ARGUMENTS` (person name or CBDB ID)

## Workflow

### Phase 1: Execute Query

Use the cbdb-query skill to perform the initial query. The skill runs in an isolated context.

**Trigger the skill:**

```
Query CBDB for: $ARGUMENTS
```

Wait for the skill to complete and return results.

### Phase 2: Display Summary

After the skill returns, display the summary to the user:

```
Query Complete! {person_name} (CBDB ID: {cbdb_id})
- Birth-Death: {birth_year}-{death_year}
- Dynasty: {dynasty}
- Identity: {brief_description}
```

### Phase 3: Interactive Follow-up

Ask the user if they want to explore detailed information:

```
Would you like to explore detailed information from the full JSON data?

Available nodes:
- PersonAliases (aliases)
- PersonAddresses (addresses)  
- PersonPostings (official career)
- PersonKinshipInfo (family relationships)
- PersonSocialAssociation (social relationships)
- PersonTexts (writings)

Reply:
- "View [node name]" to search specific node
- "All" to list all available node contents
- "No" or "End" to finish query
```

### Phase 4: Execute Detail Search

If user requests details, trigger the skill again with search parameters:

```
Search CBDB node {node_name} for {person_name} with keyword "{keyword}"
```

### Phase 5: Continue or End

```
Would you like to search other nodes? Reply with node name or "End".
```

Repeat Phase 4-5 until user says "End" or "No".

## Error Handling

| Error | Action |
|-------|--------|
| Person not found | Suggest similar names |
| Multiple matches | List candidates for selection |
| Network error | Retry once, then report |
| Invalid ID | Ask for correct ID or name |

## Notes

- The cbdb-query skill runs in `context: fork` (isolated sub-agent)
- Interactive flow remains in main context
- User can also trigger automatic discovery by mentioning historical figures