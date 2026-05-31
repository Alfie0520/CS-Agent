# Visit Image Folder Template

Use this folder shape for full image synchronization:

```text
visit-images/
  16陕西/
    西安比亚迪（展厅）.png
    西安比亚迪（工厂）.png
  广东-深圳/
    华为松山湖.png
```

Rules:

- Category folder names become the asset category.
- File stem becomes the asset name.
- `asset_id` is generated as `visit_image:{category}:{file_stem}`.
- Keep names stable; changing folder or filename changes `asset_id`.
- Replacing file content keeps `asset_id` stable and changes `sha256`.
- Avoid huge images when possible. If a file is larger than needed, compress
  it before upload.
