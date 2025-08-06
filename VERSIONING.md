# Versioning Guide

This document explains the versioning system for the OpenShift Partner Labs Cost Estimator project.

## Current Version

**Latest Release**: v1.0.0 (August 6, 2025)

Check your current version:
```bash
git describe --tags
```

## Version Schema

This project follows [Semantic Versioning](https://semver.org/) with the format **MAJOR.MINOR.PATCH**:

### Version Types
- **MAJOR** (X.0.0): Breaking changes, architectural shifts, API changes
  - Example: v1.0.0 introduced unified discovery (breaking change from individual services)
- **MINOR** (X.Y.0): New features that are backward compatible
  - Example: v0.2.0 added enhanced cost calculations (new features, no breaking changes)
- **PATCH** (X.Y.Z): Bug fixes and documentation updates
  - Example: v0.1.1 fixed resource count doubling issue

## Release History

| Version | Date | Description |
|---------|------|-------------|
| v1.0.0 | 2025-08-06 | Unified Resource Discovery System |
| v0.2.0 | 2025-07-31 | Enhanced cost calculation system |
| v0.1.1 | 2025-07-31 | Documentation and bug fixes |
| v0.1.0 | 2025-07-30 | Initial modular framework |

## Creating Releases

### Automated Release Process (Recommended)

1. **Navigate to GitHub Actions**:
   - Go to your repository → **Actions** tab
   - Find **"Create Release"** workflow
   - Click **"Run workflow"**

2. **Specify Release Details**:
   ```
   Version: v1.1.0
   Release Title: Add GCP Support
   Release Notes: (optional - will extract from CHANGELOG.md if empty)
   ```

3. **Workflow Steps**:
   - ✅ Validates version format (vX.Y.Z)
   - ✅ Checks that tag doesn't already exist
   - ✅ Runs full test suite
   - ✅ Creates git tag with annotations
   - ✅ Pushes tag to repository
   - ✅ Creates GitHub release with notes

### Manual Release Process (Advanced)

If you need to create releases manually:

```bash
# 1. Validate version
VERSION="v1.1.0"
if git tag --list | grep -q "^${VERSION}$"; then
  echo "Error: Tag already exists"
  exit 1
fi

# 2. Run tests
cd aws && python -m unittest discover -s . -p "test_*.py"

# 3. Create annotated tag
git tag -a "$VERSION" -m "$VERSION - Your release description"

# 4. Push tag
git push origin "$VERSION"

# 5. Create GitHub release (manual or via gh CLI)
gh release create "$VERSION" --title "Release Title" --notes "Release notes"
```

## Version Commands

### Checking Versions
```bash
# Current version
git describe --tags

# All versions
git tag --list

# Version details
git show v1.0.0

# Commits since last version
git log $(git describe --tags --abbrev=0)..HEAD --oneline
```

### Comparing Versions
```bash
# Changes between versions
git diff v0.2.0..v1.0.0

# Files changed between versions
git diff --name-only v0.2.0..v1.0.0

# Commits between versions
git log v0.2.0..v1.0.0 --oneline
```

## Version Guidelines

### When to Increment Major Version (X.0.0)
- Breaking API changes
- Architectural overhauls
- Incompatible CLI changes
- Major feature removals

**Example**: v1.0.0 introduced unified discovery, changing the default behavior and requiring new permissions.

### When to Increment Minor Version (X.Y.0)
- New features (backward compatible)
- New CLI options
- New AWS services support
- Performance improvements

**Example**: v0.2.0 added enhanced cost calculations without breaking existing functionality.

### When to Increment Patch Version (X.Y.Z)
- Bug fixes
- Documentation updates
- Security patches
- Minor improvements

**Example**: v0.1.1 fixed the resource count doubling bug and added documentation.

## Integration with Development

### For Developers
1. **Before starting work**: Check current version with `git describe --tags`
2. **During development**: Update [CHANGELOG.md](CHANGELOG.md) for significant changes
3. **Before release**: Ensure all tests pass and documentation is updated
4. **Release process**: Use GitHub Actions workflow for consistency

### For AI Assistants
- Always check current version before making changes
- Reference specific versions when discussing features or bugs
- Update CHANGELOG.md when implementing new features
- Never create version tags manually - use the established workflow

## Troubleshooting

### Common Issues

**Tag already exists**:
```bash
# Check existing tags
git tag --list | grep "v1.1.0"

# Delete local tag if needed
git tag -d v1.1.0

# Delete remote tag if needed (careful!)
git push origin --delete v1.1.0
```

**Workflow permission errors**:
- Ensure repository has Actions enabled
- Check that `GITHUB_TOKEN` has appropriate permissions

**Test failures during release**:
- Run tests locally: `cd aws && python -m unittest discover -s . -p "test_*.py"`
- Fix failing tests before attempting release

## Best Practices

1. **Test thoroughly** before creating releases
2. **Update CHANGELOG.md** before tagging
3. **Use descriptive release titles** and notes
4. **Follow semantic versioning** strictly
5. **Tag from main branch** for releases
6. **Document breaking changes** clearly in major releases

For more information, see:
- [CHANGELOG.md](CHANGELOG.md) - Complete version history
- [README.md](README.md) - Current version information
- [CLAUDE.md](CLAUDE.md) - Development workflow guidance