# Release Policy

## Versioning
- Follows SemVer: `MAJOR.MINOR.PATCH`
- `MAJOR`: breaking CLI/API contract changes.
- `MINOR`: backward-compatible feature additions.
- `PATCH`: backward-compatible bug/security fixes.

## Tag Format
- Release tags must use `vX.Y.Z` format.
- Example: `v0.2.1`

## Branch Protection Expectations
- CI must pass on pull requests.
- Coverage gate must pass.
- No secret scanning violations.
- Release checklist must be completed.

## Supported Python Versions
- Python 3.11 and 3.12.

## Packaging Contract
- `pyproject.toml` is source of truth for package metadata.
- Wheel and sdist must both build successfully.
- `twine check dist/*` must pass before publish.
