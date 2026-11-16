# Podolskii24 5.5.2

Restores the bottom complication center to y=264 when digital time is below.
Digital time moves independently to y=299; the top layout remains unchanged.
No hand, scale, background, or provider rendering changes.

Visually inspected native-size 432px preview and four dial styles at large
complication size, plus 03:00 / 12:00 / 18:00 on Instrument Classic and Sputnik.
Known limitation: the existing long Bell & Ross minute counterweight can cover
complications at some angles. This patch does not alter the approved hands.

Checks: six personalization tests, three hand-update tests, WFF v4,
release Gradle build and lintDebug passed. APK resource verification passed.
No device validation or editor latency measurements.
