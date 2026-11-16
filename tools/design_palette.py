"""One accent definition shared by hands, regular instrument scales and widgets."""
ORANGE='#F08A35'
AMBER='#FFC027'
MONO='#F0F2E9'
DARK='#222A29'
# Explicit hand sets take precedence over the optional background tone.
ACCENT=f'[CONFIGURATION.HandColor] == "br_mono" ? {MONO} : [CONFIGURATION.HandColor] == "br_amber" ? {AMBER} : [CONFIGURATION.HandColor] == "br_orange" ? {ORANGE} : [CONFIGURATION.DialTone] == "mono_dial" ? {MONO} : [CONFIGURATION.DialTone] == "amber_dial" ? {AMBER} : {ORANGE}'
INK=f'[CONFIGURATION.background] != "black" ? {DARK} : '+ACCENT
# For the dark-background digital branch: match the regular hour-scale ink.
DIGITAL_DARK_INK='[CONFIGURATION.sectors] != "color" && ([CONFIGURATION.style] == "instrument_classic" || ([CONFIGURATION.style] == "aviator" && [CONFIGURATION.HandColor] != "white")) ? ('+ACCENT+') : #F0F0E7'
