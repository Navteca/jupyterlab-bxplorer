# Changelog

<!-- <START NEW CHANGELOG ENTRY> -->

<!-- <END NEW CHANGELOG ENTRY> -->

## Release tags

Git tags were added retroactively in September 2026 so that every PyPI
release can be traced to a commit. Each `vX.Y.Z` tag is annotated and its
message states how the commit was identified.

| PyPI version | Published | Tag | How identified |
|---|---|---|---|
| 0.1.19 | 2023-02-21 | `v0.1.19` | Approximate. Source matches sdist except `.gitignore`. |
| 0.1.21 | 2023-03-07 | `v0.1.21` | Commit sets this version. |
| 0.1.23 | 2023-06-29 | `v0.1.23` | All sdist files match the commit. |
| 0.1.24 | 2023-07-03 | `v0.1.24` | Commit sets this version. |
| 0.1.25 | 2025-02-12 | none | No matching commit exists. See below. |
| 0.1.26 | 2025-03-12 | `v0.1.26` | All source files match; 4 docs files were added in the next commit. |
| 0.2.0 | 2025-03-12 | `v0.2.0` | Commit sets this version. |
| 0.2.20 | 2025-04-22 | `v0.2.20` | Approximate. 3 of 48 sdist files differ from the commit. |
| 0.2.24 | 2025-06-09 | `v0.2.24` | Commit sets this version. |
| 0.2.25 | 2025-06-10 | `v0.2.25` | Commit sets this version. |
| 0.2.26 | 2025-06-10 | `v0.2.26` | Commit sets this version. |
| 0.2.27 | 2025-06-12 | `v0.2.27` | All sdist files match the commit. |
| 0.2.28 | 2025-06-12 | `v0.2.28` | Commit sets this version. |
| 0.2.29 | 2025-06-13 | `v0.2.29` | Commit sets this version. |
| 0.2.30 | 2025-07-11 | `v0.2.30` | Commit sets this version. |
| 0.2.31 | 2026-09-14 | `v0.2.31` | Commit sets this version. |

### 0.1.25 has no tag

Release 0.1.25 was built from a working tree that was never committed.
The closest commits in history differ from the published sdist in 8 files,
including `jupyterlab_bxplorer/handlers.py`, `src/components/OpenDataDropdownComponent.tsx`
and `style/index.css`, and no commit exists within a month of the publish
date. Tagging any commit would point to code that was not what shipped, so
this release is intentionally left untagged. The exact shipped source is
available in the sdist on PyPI.
