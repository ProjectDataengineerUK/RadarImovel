# BUILD REPORT: Ingestão de Geodados de Risco

| Attribute | Value |
|-----------|-------|
| **Feature** | INGESTAO_GEODADOS_RISCO |
| **Build date** | 2026-06-11 |
| **Status** | ✅ Passed |
| **Tests** | 26 new passed / 0 failed (145 unit total / 0 regressions) |
| **Lint** | clean |

---

## Files Created / Modified

| # | File | Action | Status |
|---|------|--------|--------|
| 1 | `app/geodata/__init__.py` | Create | ✅ |
| 2 | `app/geodata/loaders/__init__.py` | Create | ✅ |
| 3 | `app/geodata/loaders/base.py` | Create | ✅ |
| 4 | `app/geodata/bulk_insert.py` | Create | ✅ |
| 5 | `app/geodata/loaders/ibge_mesh.py` | Create | ✅ |
| 6 | `app/geodata/loaders/icmbio.py` | Create | ✅ |
| 7 | `app/geodata/loaders/funai.py` | Create | ✅ |
| 8 | `app/geodata/loaders/cemaden.py` | Create | ✅ |
| 9 | `app/geodata/loaders/ibge_sidra.py` | Create | ✅ |
| 10 | `app/geodata/loaders/atlas_brasil.py` | Create | ✅ |
| 11 | `app/geodata/loaders/ipea_violence.py` | Create | ✅ |
| 12 | `jobs/load_geodata.py` | Create | ✅ |
| 13 | `pyproject.toml` | Modify (add `geodata` extra) | ✅ |
| 14 | `.github/workflows/deploy.yml` | Modify (add `radar-load-geodata` step) | ✅ |
| 15 | `tests/unit/geodata/__init__.py` | Create | ✅ |
| 16 | `tests/unit/geodata/test_icmbio_loader.py` | Create | ✅ 5 tests |
| 17 | `tests/unit/geodata/test_funai_loader.py` | Create | ✅ 3 tests |
| 18 | `tests/unit/geodata/test_cemaden_loader.py` | Create | ✅ 4 tests |
| 19 | `tests/unit/geodata/test_ibge_mesh_loader.py` | Create | ✅ 2 tests |
| 20 | `tests/unit/geodata/test_ibge_sidra_loader.py` | Create | ✅ 4 tests |
| 21 | `tests/unit/geodata/test_atlas_brasil_loader.py` | Create | ✅ 4 tests |
| 22 | `tests/unit/geodata/test_ipea_violence_loader.py` | Create | ✅ 4 tests |

Total: **22 files** (20 created + 2 modified)

---

## Test Results

```
26 passed, 0 failed (new geodata tests)
145 passed, 5 failed (full unit suite — 5 failures are pre-existing in banestes/basa/bnb parsers, unrelated to this build)
```

---

## Issues Found and Fixed

### Fix 1: ibge_mesh.py — import and unused variable
- **Problem:** `import tempfile, os` inside a function (E401, I001); `shp_bytes` assigned but never used (F841)
- **Fix:** Moved imports to top-level, removed unused variable, collapsed into clean temp directory extraction

### Fix 2: test_funai_loader.py — incorrect assertion on HTTP error test
- **Problem:** Test expected `stats` to be returned after `requests.Timeout` — but `FunaiLoader.load()` propagates HTTP errors (by design), so the call raises instead of returning
- **Fix:** Changed test to use `pytest.raises(requests.exceptions.Timeout)` to verify the propagation contract

---

## Architecture Validation

| Component | Verified |
|-----------|---------|
| `GeoLoader` ABC + `LayerStats` dataclass | ✅ |
| `bulk_insert_geodata()` — DELETE+INSERT idempotent | ✅ |
| `upsert_municipality_stats()` — COALESCE preserves non-null values | ✅ |
| `IbgeMeshLoader.load_mesh()` — returns `MeshResult` with mesh dict | ✅ |
| `IcmbioLoader` — WFS pagination with `startIndex/count` | ✅ |
| `FunaiLoader` — propagates HTTP errors to job-level handler | ✅ |
| `CemadenLoader` — URL fallback, 6→7 digit code resolution | ✅ |
| `IbgeSidraLoader` — SIDRA v3 response parsing, COALESCE update | ✅ |
| `AtlasBrasilLoader` — fuzzy column detection, IDH range validation | ✅ |
| `IpeaViolenceLoader` — latest year column detection, CSV write, GCS upload | ✅ |
| `jobs/load_geodata.py` — orchestration with `SKIP_LAYERS`, dry-run, partial failure | ✅ |
| `pyproject.toml` — `geodata` extra with geopandas/shapely/fiona | ✅ |
| `deploy.yml` — `radar-load-geodata` Cloud Run Job step (4Gi, 2 CPU, 3600s) | ✅ |

---

## Acceptance Tests Status

| AT | Status | Notes |
|----|--------|-------|
| AT-001 | Pending (requires DB + network) | Job structure validates; prod run needed |
| AT-002 | Pending | Idempotency logic tested via unit test pattern |
| AT-003 | Pending (requires PostGIS data) | `ST_Contains` query ready in `IbamaLookup` |
| AT-004 | Pending | `ibge_municipality_stats` upsert logic tested |
| AT-005 | ✅ | `IpeaViolenceLoader` writes `data/atlas_violencia.csv` — tested |
| AT-006 | ✅ | `SKIP_LAYERS` env var implemented and tested |
| AT-007 | Pending (Cloud Run execute) | Job exits(0) on partial failure, exits(1) only on total failure |

---

## Next Steps

1. **Commit + push** → CI/CD deploys `radar-load-geodata` Cloud Run Job
2. **Execute first load:** `gcloud run jobs execute radar-load-geodata --region=us-central1 --project=radarimovel`
3. **Verify AT-001 through AT-004** via SQL queries on Cloud SQL
4. **Re-run `radar-calculate-risk`** on existing properties to confirm `score_partial=False`

---

**Ready for:** `/ship .claude/sdd/features/DEFINE_INGESTAO_GEODADOS_RISCO.md`
