# Archived Migration Scripts

Historical migration scripts preserved for reference.

## Archive Structure

### v1-to-v2/
Migration scripts for upgrading from v1.x to v2.x (2023-2024)
- First major architecture revision
- Introduction of collection-based storage

### v2-to-v3/
Migration scripts for upgrading from v2.x to v3.x (2024)
- Enhanced search algorithms
- SHA-256 + UUID conversation IDs (from MD5)
- Qdrant authentication introduction

### v3-to-v4/
Migration scripts for upgrading from v3.x to v4.x (2024)
- Collection naming with dimension suffixes (`csr_` prefix)
- Support for local (384d) and cloud (1024d) embeddings
- Parallel migration capabilities
- Collection cleanup utilities

## Active Migration Scripts

Located in `scripts/migration/` (parent directory):

- **migrate-to-unified-state.py** - v5.0 migration (INCLUDED IN NPM PACKAGE)
  - Migrates from multiple JSON files to single unified-state.json
  - Critical for v5.0+ adoption
  - Atomic operations with file locking

- **safe-migrate-collections.py** - Safe collection migration utility
- **backup_qdrant.py** - Qdrant backup tool

## Current Version

**v7.0.0** - AI-powered narrative generation

## Why Archive?

These scripts are archived because:
1. Target versions are 2+ years old (v1-v3)
2. Users are expected to migrate to current version (v7.0.0) directly
3. Preserved for historical reference and troubleshooting legacy installations
4. No longer maintained or tested with current infrastructure

## Upgrading to v7.0.0

For users on old versions, we recommend:
1. Fresh installation of v7.0.0
2. Re-import conversations using current import pipeline
3. Contact support if historical data preservation is critical

---

*Archive created: 2025-11-12*
*Reason: Reduce maintenance burden of historical migration paths*
