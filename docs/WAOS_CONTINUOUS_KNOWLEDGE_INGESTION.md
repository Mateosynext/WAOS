# WAOS Continuous Knowledge Ingestion

## Goal
Move from knowledge that was loaded once to a live knowledge layer that can absorb operational changes and publish them to runtime without heavy manual work.

## What changed
- Native source connections for `notion`, `drive`, `url`, `pdf`, and `form`.
- Watch/sync runs with `manual`, `polling`, and `webhook` trigger modes.
- Item normalization, validation, publication state, and per-item sync logs.
- Publication into the existing governed knowledge runtime so retrieval stays grounded and versioned.

## New runtime pieces
- `knowledge_source_connections`: source registry with owner, timestamps, publish policy, and watcher mode.
- `knowledge_source_sync_runs`: watcher executions and pipeline status.
- `knowledge_source_sync_items`: per-item validation/publication outcomes.
- `knowledge_source_publications`: current mapping from external source items to governed knowledge docs.

## API
- `GET /api/v1/knowledge/sources`
- `POST /api/v1/knowledge/sources`
- `POST /api/v1/knowledge/sources/{source_connection_id}/sync`
- `GET /api/v1/knowledge/sources/{source_connection_id}/runs`

## Publication flow
1. Register source connection with connector, owner, watch mode and publish policy.
2. Sync source with normalized items from the connector.
3. Validate each item.
4. Auto-publish valid items into `knowledge_documents` / `knowledge_document_versions`.
5. Expose publication state, owner and timestamps through knowledge traceability.

## Practical effect
The bot keeps using the same governed retrieval path, but now that path can be refreshed continuously from live operational sources instead of depending on manual config-only updates.
