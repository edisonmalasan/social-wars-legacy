# Original game frames (private-use build)

These PNGs are converted frames of the original Social Wars art. They were produced by
the repository's Group D pipeline (`scripts/convert-assets.mjs` and
`scripts/pack-atlases.mjs`) from the read-only original checkout at
`C:\Users\Edison\Desktop\socialwarriors`; that checkout was not modified.

Only the 28 distinct frames needed by the starting Command Center and item ids 1–5 are
shipped, as individual trimmed PNGs (~2 MB). `frame-manifest.json` points each needed
image at `frames/<hash>.png`, so the renderer fetches small files instead of multi-megabyte
atlas sheets. No SWF, audio or proprietary configuration is vendored.

**Rights:** these are Zynga's original media, not CC0. GPL v3 on the upstream server code
does not license them. This build is for the owner's private use; public redistribution
remains blocked by `docs/LICENSING.md` and ADR 0022. No Flash runtime is shipped — only
converted PNG frames.
