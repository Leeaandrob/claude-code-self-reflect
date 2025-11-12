# Testing & Certification Reports

This directory contains test certification reports, validation results, and quality assessments from previous releases.

## Certification Reports

### v3.2.0-certification-report.md (8.0K)
**Version:** v3.2.0
**Date:** 2024
**Status:** ✅ PASSED
**Summary:** Full system certification for v3.2.0 release
- Semantic search validation
- Migration testing (v2 → v3)
- Performance benchmarks
- Production readiness sign-off

### v3.1.0-certification-report.md (4.0K)
**Version:** v3.1.0
**Date:** 2024
**Status:** ✅ PASSED (after fixes)
**Summary:** Certification report for v3.1.0
- Initial failures documented
- Fixes applied
- Re-certification successful

### v3.1.0-FAILED-certification.md (4.0K)
**Version:** v3.1.0 (initial attempt)
**Date:** 2024
**Status:** ❌ FAILED
**Summary:** First certification attempt for v3.1.0
- Issues identified
- Root cause analysis
- Remediation plan

### v3.1.0-FAILED-v2-certification.md (8.0K)
**Version:** v3.1.0 (v2 compatibility)
**Date:** 2024
**Status:** ❌ FAILED
**Summary:** v2 backward compatibility test
- Migration path issues
- Breaking changes documented
- v3-only path decided

## Test Documentation

See also:
- **tests/README.md** - Test suite overview
- **tests/README_unified_state_tests.md** - v5.0 unified state tests

## Historical Context

These reports document:
- ✅ Quality standards evolution
- ✅ Lessons learned from failures
- ✅ Testing methodology improvements
- ✅ Release gate criteria

## Value

**Why keep failure reports:**
- Document what didn't work (avoid repeating mistakes)
- Show iterative improvement process
- Provide context for architectural decisions
- Demonstrate thorough QA process

**Why keep success reports:**
- Benchmark for future releases
- Reference for regression testing
- Proof of production readiness
- Compliance documentation

## Current Testing (v7.0.0)

For current v7.0.0 testing:
```bash
# Run comprehensive tests
python tests/run_all_tests.py

# Unified state tests
pytest tests/test_unified_state.py -v

# Memory decay tests
pytest tests/test_memory_decay.py -v

# Narrative generation tests
pytest tests/test_narrative_generation.py -v

# Package validation
python tests/test_npm_package_contents.py
```

## Policy

- **Keep last 2 major versions** of certification reports
- **Archive older reports** to `docs/archive/testing/`
- **Document all failures** before fixing
- **Include root cause analysis** in reports
- **Update test standards** based on learnings

---

*Last updated: 2025-11-12*
*Reports: 4 (v3.x era)*
*Current version: v7.0.0*
*Next certification: v8.0.0 (when released)*
