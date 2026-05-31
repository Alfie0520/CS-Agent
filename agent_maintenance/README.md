# CS-Agent Maintenance Guide For Agents

This folder is the handoff package for Cursor, Trae, Codex, or any other agent
that needs to maintain CS-Agent business data.

Read this file first. Do not rely on old chat history.

## What You Can Maintain

1. Enterprise visit-plan data:
   - Runtime file on server: `/data/cs-agent-data/enterprises.json`
   - Source JSON commonly generated locally at: `app/data/enterprises.json`
   - Excel conversion script: `scripts/enterprise_db/build_enterprise_db.py`

2. Visit-plan image assets:
   - Runtime image folder on server: `/data/cs-agent-assets/images/`
   - Runtime index on server: `/data/cs-agent-assets/asset_index.json`
   - The agent only sees `asset_id`, not server file paths.

## Safety Rules

- Always run dry-run validation before publishing enterprise data.
- Never edit `/opt/CS-Agent/app/data/enterprises.json` on the server for runtime updates.
- Never restart the service just to update enterprise data or images.
- Never put API keys in query strings. Use `X-API-Key`.
- Never paste `CS_AGENT_API_KEY` into chat or docs.
- For delete operations, search first and confirm the exact `asset_id`.
- For image files, preserve a predictable folder and filename structure.

## Required Environment

Set these in your shell before using scripts:

```bash
export CS_AGENT_BASE_URL="https://bgtx.work"
export CS_AGENT_API_KEY="$(ssh ubuntu@43.129.183.181 "grep '^VISIT_IMAGE_API_KEY=' /opt/CS-Agent/.env | cut -d= -f2-")"
```

Do not print or paste `CS_AGENT_API_KEY`. The command above reads it from the
production server's `/opt/CS-Agent/.env` file without storing it in the repo.
If SSH prompts for a password, enter the server password manually.

If maintaining a non-production deployment, replace `CS_AGENT_BASE_URL` and the
SSH target/path with that deployment's values.

## Recommended Workflows

### Check Runtime State

```bash
agent_maintenance/scripts/check_runtime.sh
```

This reports enterprise row count and asset counts by category.

### Update Enterprise Visit Plans

If starting from the Excel file:

```bash
python3 scripts/enterprise_db/build_enterprise_db.py
```

Validate the generated JSON:

```bash
agent_maintenance/scripts/validate_enterprises.sh app/data/enterprises.json
```

Publish after validation passes:

```bash
agent_maintenance/scripts/publish_enterprises.sh app/data/enterprises.json
```

### Upload Or Replace One Image

```bash
agent_maintenance/scripts/upload_image.sh \
  "16陕西" \
  "西安比亚迪（展厅）.png" \
  "./西安比亚迪（展厅）.png"
```

Then verify:

```bash
agent_maintenance/scripts/search_assets.sh "比亚迪" "西安"
```

### Delete One Image

First search:

```bash
agent_maintenance/scripts/search_assets.sh "比亚迪" "西安"
```

Then delete the exact `asset_id`:

```bash
agent_maintenance/scripts/delete_asset.sh "visit_image:16陕西:西安比亚迪（展厅）"
```

### Full Image Folder Sync

Local folder must look like:

```text
visit-images/
  16陕西/
    西安比亚迪（展厅）.png
    西安比亚迪（工厂）.png
  广东-深圳/
    华为松山湖.png
```

Run:

```bash
agent_maintenance/scripts/sync_images.sh ./visit-images ubuntu@SERVER_IP
```

This uses `rsync --delete`, so it makes the server image folder match the local
folder exactly. Use with care.

## API Reference

See `agent_maintenance/API.md`.

## Troubleshooting

- If a search misses an image, check both the category and filename. Search now
  matches category, filename, enterprise names, asset id, and path.
- If an enterprise upload fails, read the validation error. Required fields are
  listed in `API.md`.
- If a URL contains Chinese `asset_id`, use `delete_asset.sh`; it handles URL
  encoding.
- If a customer says the agent cannot send an image, check:
  1. `search_assets.sh` can find the asset.
  2. The asset detail endpoint says `exists=true`.
  3. Server logs contain `asset_delivery` timing lines.
