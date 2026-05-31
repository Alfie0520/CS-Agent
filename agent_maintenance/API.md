# CS-Agent Maintenance API

All endpoints require:

```http
X-API-Key: VISIT_IMAGE_API_KEY
```

Do not pass API keys in query strings.

## Enterprise Data

### Get Current Data

```bash
curl -fsS \
  -H "X-API-Key: $CS_AGENT_API_KEY" \
  "$CS_AGENT_BASE_URL/api/enterprises/data"
```

Response:

```json
{
  "success": true,
  "count": 404,
  "source_path": "/data/cs-agent-data/enterprises.json",
  "items": []
}
```

### Validate Or Publish Enterprise JSON

Dry-run:

```bash
curl -fsS -X POST "$CS_AGENT_BASE_URL/api/enterprises/data" \
  -H "X-API-Key: $CS_AGENT_API_KEY" \
  -F "dry_run=true" \
  -F "json_file=@app/data/enterprises.json;type=application/json"
```

Publish:

```bash
curl -fsS -X POST "$CS_AGENT_BASE_URL/api/enterprises/data" \
  -H "X-API-Key: $CS_AGENT_API_KEY" \
  -F "dry_run=false" \
  -F "json_file=@app/data/enterprises.json;type=application/json"
```

Required fields for every row:

```text
id
city
name
themes
visit_experience
sharing_topics
core_value
knowledge_points
pain_points
```

Validation rules:

- top-level JSON must be an array
- every row must be an object
- `id` must be unique integer
- `themes` must be a list of strings
- all required fields must exist

## Asset APIs

### Stats

```bash
curl -fsS \
  -H "X-API-Key: $CS_AGENT_API_KEY" \
  "$CS_AGENT_BASE_URL/api/assets/stats"
```

Response:

```json
{
  "success": true,
  "count": 402,
  "categories": {
    "16陕西": 11
  }
}
```

### Search

```bash
curl -fsS -G "$CS_AGENT_BASE_URL/api/assets/search" \
  -H "X-API-Key: $CS_AGENT_API_KEY" \
  --data-urlencode "query=比亚迪" \
  --data-urlencode "category=西安"
```

Search matches:

- image name
- category
- `enterprise_names`
- `asset_id`
- path

### Upload Or Replace One Image

```bash
curl -fsS -X POST "$CS_AGENT_BASE_URL/api/assets/image" \
  -H "X-API-Key: $CS_AGENT_API_KEY" \
  -F "category=16陕西" \
  -F "image_name=西安比亚迪（展厅）.png" \
  -F "image_file=@./西安比亚迪（展厅）.png;type=image/png"
```

Rules:

- `category` may contain nested folders but must not be absolute or contain `..`
- `image_name` must be a plain filename, not a path
- supported suffixes: `.jpg`, `.jpeg`, `.png`, `.gif`, `.bmp`, `.webp`
- empty files are rejected
- upload automatically rebuilds `asset_index.json`

### Asset Detail

`asset_id` must be URL encoded if it contains Chinese or slashes.

```bash
curl -fsS \
  -H "X-API-Key: $CS_AGENT_API_KEY" \
  "$CS_AGENT_BASE_URL/api/assets/ENCODED_ASSET_ID"
```

Response:

```json
{
  "success": true,
  "asset": {
    "asset_id": "visit_image:16陕西:西安比亚迪（展厅）",
    "kind": "image",
    "name": "西安比亚迪（展厅）",
    "category": "16陕西",
    "path": "images/16陕西/西安比亚迪（展厅）.png"
  },
  "exists": true,
  "size": 123456
}
```

### Delete Asset

Search first, then delete by exact `asset_id`.

```bash
curl -fsS -X DELETE \
  -H "X-API-Key: $CS_AGENT_API_KEY" \
  "$CS_AGENT_BASE_URL/api/assets/ENCODED_ASSET_ID"
```

Delete automatically rebuilds `asset_index.json`.

### Rescan

Use after server-side file operations or full rsync:

```bash
curl -fsS -X POST "$CS_AGENT_BASE_URL/api/assets/rescan" \
  -H "X-API-Key: $CS_AGENT_API_KEY"
```
