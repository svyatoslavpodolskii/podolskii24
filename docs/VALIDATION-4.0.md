# TwentyFour 4.0 ? validation

Native WFF v4 resource-only APK; versionCode 5. Real-watch testing deferred by user.

- Gradle build and Android Lint: successful; 0 errors, 158 warnings.
- Official WFF validator, format version 4: PASSED.
- APK Signature Scheme v2: valid; no DEX/JAR/CLASS/SO.
- 16 native scene tests passed: 24000 hand combinations plus 1200 minute-track combinations.
- Instrument and Aviator: 96 closed RoundRectangle ticks; 24 hours and three quarter-hour marks between hours.
- Raster connectivity at 432x432: exactly 96 connected marks per scale, minimum 6 pixels; no separate dots.
- All four new Instrument Refined hand PNGs: one connected component, no detached fragments.
- 19 manual hand styles; old 16 PNGs remain byte-identical to version 2.0.
- 72 period fill/divider/label groups and all 3 complication slots preserved; hour-scale nodes intentionally excluded from period comparison.
- MinuteTrackStyle: None / TicksOnly / FiveMinuteLabels / SputnikRing / InstrumentRing.
- 300 minute-track renders passed; minute hand both on/off, both boundary presets covered.
- 342 hand renders at 03:00, 10:30, 18:00; three backgrounds, None/Color.
- 240 base preview cases, 40 divider cases, 30 populated complication cases; 30558 contrasting numeral pixels checked.
- AOD lit-pixel ratio 0.01261; common AOD scene retained.
- verify_apk.py confirms exact packaged XML and byte-identical new hand PNGs, and checks actual packaged 96-tick geometry.

Reports: graphics-checks.json, hand-checks.json, preview-checks.json, android-lint.txt.
Previews are local XML renders, not emulator/device screenshots. The 432x432 exports check pixel resolution, not physical display size or brightness.
APK: dist/TwentyFour-debug.apk; checksum: dist/SHA256SUMS.txt.
