# Editorial and Publishing Workflow

## Streamlit Control Plane

File: `ui/app.py`

Tabs:

- Source management
- Review inbox
- Bundle and publish
- Pipeline metrics

## Review Flow

1. Open inbox filtered to `ready_for_review`.
2. Inspect insight details (claims, protocols).
3. Approve or reject.
4. Edits are persisted via insight patch endpoint.

## Bundle Building

Endpoint: `POST /v1/bundles/build`

Supports:

- Date-range auto-selection
- Optional explicit `insight_ids`

Approvals transition to `bundled` when included.

## Beehiiv Draft Publishing

Endpoint: `POST /v1/bundles/{id}/publish/beehiiv`

Behavior:

- Draft-only mode
- On success captures `external_post_id` and `external_url`
- On failure stores `publish_error`

## Audit Coverage

Actions audited in `audit_logs` include:

- Source create/update
- Manual ingestion
- Insight approve/reject/edit
- Bundle build
- Publish attempt
- Manual document transitions
