# Runtime Data And Assets

This service now keeps mutable business data under `/data` so updating visit
plans or images does not require a code deploy.

## Enterprise Data

The agent reads enterprise visit plans from:

```text
/data/cs-agent-data/enterprises.json
```

`app.enterprise_data` reads the JSON on each query. The upload endpoint validates
JSON and replaces the file atomically:

```bash
scripts/upload_enterprise_data.sh app/data/enterprises.json https://YOUR_HOST API_KEY
```

The Excel-to-JSON conversion remains local:

```bash
python3 scripts/enterprise_db/build_enterprise_db.py
scripts/upload_enterprise_data.sh app/data/enterprises.json https://YOUR_HOST API_KEY
```

## Image Assets

The server stores all visit images under:

```text
/data/cs-agent-assets/images/
  广东-深圳/
    华为.png
  河南/
    胖东来.png
```

The generated index lives at:

```text
/data/cs-agent-assets/asset_index.json
```

For full synchronization from a local image folder, use rsync plus a rescan:

```bash
scripts/sync_assets.sh ./visit-images ubuntu@YOUR_SERVER https://YOUR_HOST API_KEY
```

Daily single-image maintenance can use the internal API:

```bash
curl -X POST https://YOUR_HOST/api/assets/image \
  -F "api_key=API_KEY" \
  -F "category=广东-深圳" \
  -F "image_name=华为.png" \
  -F "image_file=@./华为.png"
```

The agent searches image assets by `asset_id` and sends them through
`send_asset(asset_id)`. The delivery layer uploads temporary media to the active
channel and caches `media_id` by `asset_id + sha256 + channel`.
