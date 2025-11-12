# Operations Documentation

This directory contains operational procedures, checklists, and release management documentation.

## Release Management

### PACKAGING_CHECKLIST.md (7.3K)
**Purpose:** Pre-release validation checklist
**When to use:** Before publishing new npm package version

**Covers:**
- npm package integrity checks
- Dockerfile validation
- Documentation verification
- Test suite execution
- Version consistency
- Breaking changes review
- Migration path validation

**Target audience:** Maintainers preparing releases

### RELEASE_NOTES.md (8.6K)
**Purpose:** Release notes template and guidelines
**When to use:** Creating release announcements

**Covers:**
- Release notes structure
- Categorization of changes
- Breaking changes documentation
- Migration instructions
- Known issues format
- Version numbering guidelines

**Target audience:** Maintainers writing release notes

## Usage

### Pre-Release Workflow
```bash
# 1. Run packaging checklist
python scripts/quality-gate-staged.py
npm pack --dry-run
docker compose build --no-cache

# 2. Review PACKAGING_CHECKLIST.md
# - Check all items
# - Document any failures
# - Fix issues before proceeding

# 3. Create release notes using RELEASE_NOTES.md template
# 4. Update CHANGELOG.md
# 5. Create GitHub release
```

### Release Types
- **Major (x.0.0):** Breaking changes, architectural changes
- **Minor (x.y.0):** New features, enhancements
- **Patch (x.y.z):** Bug fixes, documentation

## Related Documentation

- **CHANGELOG.md** (root) - Complete version history
- **CONTRIBUTING.md** (root) - Contribution guidelines
- **docs/development/** - Development guides
- **docs/testing/** - Test reports

## Policy

- **Review checklists before every release**
- **Update checklists** when adding new validation steps
- **Keep release templates current** with project practices
- **Document all breaking changes** with migration paths

---

*Last updated: 2025-11-12*
*Files: 2 (Packaging checklist, Release notes template)*
*Purpose: Ensure consistent, high-quality releases*
