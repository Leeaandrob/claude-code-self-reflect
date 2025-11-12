# Design Documents & Prototypes

This directory contains design documents, prototypes, and experimental code for feature research.

## Contents

### Prototypes
- **batch_import_v3.py** - v3 prototype for batch import system
- **extract_events_v3.py** - Event extraction analysis tool
- **conversation-analyzer/** - Conversation analysis toolkit with SKILL definitions

## Policy

This directory is for:
- ✅ Design documents and proposals
- ✅ Prototype implementations for evaluation
- ✅ Research and analysis tools
- ✅ Proof-of-concept code

This directory is NOT for:
- ❌ Production operational tools → Use `src/`
- ❌ Development utilities → Use `scripts/dev/`
- ❌ Evaluation tools → Use `scripts/evaluation/`
- ❌ Active service implementations → Use `src/runtime/`

## Moved Files (2025-11-12)

The following operational files were moved to appropriate locations:

**Moved to `src/batch/`:**
- batch_import_all_projects.py (operational batch tool)
- recover_batch_results.py (batch result recovery)
- recover_all_batches.py (bulk batch recovery)
- import_existing_batch.py (batch import utility)

**Moved to `scripts/evaluation/`:**
- batch_ground_truth_generator.py (evaluation/testing tool)

## Contributing

When adding new files here:
1. If it's operational code → move to `src/` or `scripts/`
2. If it's a prototype → add documentation explaining the experiment
3. If implemented → move to appropriate location and archive prototype
4. Keep this directory focused on design/research, not production

---

*Purpose: Separate exploratory work from production code*
*Updated: 2025-11-12*
