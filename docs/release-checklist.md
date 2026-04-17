# Release Checklist

## Pre-Release
1. Confirm target version (`X.Y.Z`) and update `pyproject.toml`.
2. Update `CHANGELOG.md` with user-visible changes.
3. Run local validation:
- `python -m compileall -q .`
- `pytest`
- `python scripts/build_artifacts.py`
- `twine check dist/*`

## Git and Tag
1. Commit release changes.
2. Create annotated tag:
- `git tag -a vX.Y.Z -m "Release vX.Y.Z"`
3. Push branch and tag:
- `git push origin <branch>`
- `git push origin vX.Y.Z`

## CI/CD
1. Confirm CI workflow passes.
2. Confirm release workflow builds artifacts.
3. Confirm PyPI publish step (if token configured).

## Post-Release
1. Verify `pip install kittycode==X.Y.Z` works in clean env.
2. Smoke test:
- `kitty --help`
- `kitty doctor`
- `kitty --json version`
3. Publish release notes in GitHub release description.
