# Podolskii24 5.7.4 / code 28

Targeted editor resource reduction and concrete background tint binding. This
patch does not establish the cause of the reported Samsung editor crash:
no current logcat, connected watch or running Wear OS emulator was available.

## Changes

- Picker-only images: 144 to 80 pixels per side (69.1% less decoded storage
  per thumbnail). Runtime dial, hands, complication outlines and scale assets
  retain their previous resolution and geometry. All option IDs are retained.
- Background tint Transform and themeSurface Reference now belong to the
  actual PartDraw rather than its parent Group. This removes the parent tint
  filter from the background rendering path; device behavior still needs testing.
- Tests exercise Ivory, charcoal and brown background values and cap editor
  images at 80 pixels and packaged PNG decoded storage at 18,150,000 bytes.

## Measurements

| Measurement | 5.7.3 | 5.7.4 |
|---|---:|---:|
| Packaged PNG decoded upper bound, bytes | 19,208,528 | 18,004,304 |
| Release APK, bytes | 1,158,925 | 986,713 |
| Official evaluator maximum active, bytes | 13,343,296 | 13,343,296 |
| Official evaluator maximum ambient, bytes | 2,532,480 | 2,532,480 |

The evaluator measures scene resources, not Samsung editor process RAM. Its
unchanged estimate is expected: only editor artwork was reduced. Do not claim
that this is a major runtime-memory optimization or a verified crash fix.
Raw evaluator reports are stored alongside this report.

Release and debug Gradle builds, WFF v4 validation, Android Lint and release APK
resource verification passed. Background comparison: ../previews/5.7.4-backgrounds.jpg.

For a non-black surface matching the original Bell & Ross hand bases: choose
Black background and DialTone charcoal (Graphite Bell & Ross) or brown; use
sectors None/Lines/Labels to see the base surface rather than colored sectors.
Existing saved settings are preserved when installing this update.

Release SHA-256: 2b6299317a9ae05f8f8500969b505deae8286c0eabe46ae18a73e4db2854687c.

Regression suite: 71 of 72 tests passed initially; the remaining test found two
late-generated 144px picker icons. Both generators now produce 80px icons.
All four stability tests passed after regeneration; final APK rebuilt and verified.
