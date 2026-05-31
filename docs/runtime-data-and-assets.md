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

Validate without replacing the runtime file:

```bash
scripts/upload_enterprise_data.sh app/data/enterprises.json https://YOUR_HOST API_KEY --dry-run
```

The API checks required fields (`id`, `city`, `name`, `themes`,
`visit_experience`, `sharing_topics`, `core_value`, `knowledge_points`,
`pain_points`) before writing. A valid upload is written atomically so readers
never observe a half-written JSON file.

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

Useful read APIs:

```bash
curl "https://YOUR_HOST/api/assets/search?api_key=API_KEY&query=比亚迪&category=西安"
curl "https://YOUR_HOST/api/assets/stats?api_key=API_KEY"
curl "https://YOUR_HOST/api/assets/visit_image:16陕西:西安比亚迪（展厅）?api_key=API_KEY"
```

Uploads reject empty files, path-like file names, and unsupported image suffixes.
Every add, replace, delete, full sync, or restore should end by regenerating the
index through `/api/assets/rescan`.

The agent searches image assets by `asset_id` and sends them through
`send_asset(asset_id)`. The delivery layer uploads temporary media to the active
channel and caches `media_id` by `asset_id + sha256 + channel`.

## Restoring From Existing WeChat Permanent Media

If local image files are lost but the old `/data/media_index.json` still has
official-account permanent `media_id` values, restore them on the server:

```bash
python3 scripts/restore_wechat_material_assets.py \
  --media-index /data/media_index.json \
  --asset-root /data/cs-agent-assets \
  --asset-index /data/cs-agent-assets/asset_index.json
```

The script downloads each permanent image through the official-account material
API and writes it to:

```text
/data/cs-agent-assets/images/{category}/{image_name}
```

Images larger than 1 MB are converted to JPEG and compressed toward 200 KB
before the asset index is regenerated.
