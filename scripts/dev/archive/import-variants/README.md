# Import Script Variants Archive

Historical import script implementations showing evolution of the import system.

## Archived Variants

### import-conversations-unified-enhanced.py
Enhanced version with additional features
- Performance optimizations
- Enhanced error handling
- Experimental features

### import-conversations-unified-old.py
Older unified import implementation
- Pre-v5.0 unified state
- Original import logic

### import-conversations-unified-v3.py
v3-era import implementation
- MD5-based conversation IDs
- Pre-SHA256+UUID migration

### import-old-format.py
Import tool for legacy conversation formats
- Handles pre-v2.0 JSONL structure
- Backward compatibility

### import-conversations-enhanced.py
Alternative enhanced implementation
- Different optimization approach
- Experimental features

### import-modular.py
Modular import architecture prototype
- Pluggable import strategies
- Design exploration

## Current Import System

**Production Import:**
- **Primary:** `src/runtime/import-conversations-unified.py`
- **Async:** `src/runtime/streaming-importer.py` (v4.0+)
- **Watcher:** `src/runtime/streaming-watcher.py` (HOT/WARM/COLD priority)

**Architecture:**
```
File System Monitor (streaming-watcher.py)
    ↓
Priority Queues (HOT < 5min, WARM < 24hrs, COLD > 24hrs)
    ↓
Async Import Pipeline (streaming-importer.py)
    ↓
Unified State Manager (unified_state_manager.py)
    ↓
Qdrant (vector embeddings)
```

## Evolution Timeline

1. **v1-v2:** Basic import scripts
2. **v3:** Unified import with MD5 IDs
3. **v4:** Async imports, SHA256+UUID
4. **v5:** Unified state management
5. **v6:** Performance optimizations
6. **v7:** AI narrative generation integration

## Why Archive?

These variants represent evolutionary development:
- Multiple approaches were tested
- Features were consolidated into production code
- Preserved for reference and pattern analysis
- No longer maintained or used in production

## Current Best Practices

For new import features:
1. Modify `src/runtime/import-conversations-unified.py`
2. Use `unified_state_manager.py` for state tracking
3. Leverage async/await for performance
4. Add tests in `tests/test_import_*.py`
5. Document in `docs/development/`

---

*Archive created: 2025-11-12*
*Purpose: Consolidate import implementations while preserving development history*
