# Podolskii24 5.2.1 — minute track colors

Independent native WFF v4 `MinuteColor` list: Original, Neutral, Orange,
Green, Blue. Neutral uses light ink on dark backgrounds/sectors and dark ink
on light ones. Original retains every previous literal color exactly.
Only the existing shared minute-track sprites receive tint transforms;
hands, hour scales, period labels, dividers and complications are unchanged.
The setting works independently of minute-hand visibility.

WFF limits a ColorOption palette to five colors; the original artwork uses
six distinct inks. A native ListConfiguration plus supported tintColor
transforms preserves all six without duplicate scene branches or bitmaps.
Reference: https://developer.android.com/reference/wear-os/wff/user-configuration/list-configuration

Validation:

- 31 automated tests pass, including native palette evaluation and unchanged
  inverse geometry contracts.
- Official WFF v4 schema validator passes.
- Gradle debug and release builds succeed.
- XML: 1,334,098 -> 1,372,632 bytes; elements: 18,712 -> 18,846.
- Decoded runtime PNG upper bound remains 27,252,300 bytes.
- Actual device RAM, CPU and editor latency have not been measured.
- No emulator/watch test available. AOD, editor crashes and complication
  layout remain unresolved by this narrowly scoped color patch.

The experimental sector-mask preclipping pass was rejected: although it
removed runtime masks, its decoded PNG bound increased to 39,730,736 bytes.
It is not included in this APK.

All hand options are retained pending the user's numbered selection.
`previews/hand-selection-numbered-5.2.jpg` maps 01–22 to current choices.
`previews/minute-colors-5.2.1.jpg` is an offline XML preview, not a screenshot
from Wear OS.
