# Deprecated Source Files

This directory contains source files that are no longer actively used but preserved for reference.

## Files

### embeddings_old.py
**Deprecated:** v7.0.0
**Reason:** Replaced by `embedding_manager.py`
**Status:** Zero active imports found in codebase

**Why Preserved:**
- Historical reference for embedding implementation evolution
- May contain useful patterns for future refactoring
- Documentation of previous approach

**Modern Alternative:**
Use `embedding_manager.py` which provides:
- Lazy initialization (faster startup)
- Runtime mode switching (local ↔ cloud)
- Connection pooling with circuit breaker
- Unified interface for FastEmbed and Voyage AI

## Policy

Files in this directory:
- ❌ Should NOT be imported by active code
- ❌ Should NOT be included in new features
- ✅ Are preserved for historical reference
- ✅ May be permanently deleted in future major versions

If you need functionality from a deprecated file, refactor and integrate into active codebase rather than importing deprecated code.

---

*Directory created: 2025-11-12*
*Purpose: Clean separation of deprecated code while preserving institutional knowledge*
