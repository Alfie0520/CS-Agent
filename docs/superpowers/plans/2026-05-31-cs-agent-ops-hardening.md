# CS-Agent Ops Hardening Implementation Plan

Goal: make the WeChat/KF image and runtime-data workflow observable, quieter, and operable without code releases.

Architecture: add small focused helpers around timing and maintenance, keep existing FastAPI/router boundaries, and preserve asset_id/runtime JSON abstractions. Tests cover behavior at the function/API boundary before production changes.

Tasks:
1. Add observability tests and timing logs for agent handling, important tools, and asset delivery.
2. Add a KF service-state transition feature flag defaulting off, with router tests.
3. Harden media asset maintenance APIs with metadata/detail endpoints, safe validation, and tests.
4. Harden enterprise runtime data API with validation, stats, source path metadata, and tests.
5. Run full test/compile verification, commit, push, deploy.
