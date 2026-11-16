"""Reproducible 5.5 previews, using the actual generated WFF scene."""
from generate import ROOT,VISIBLE_HAND_STYLES
from render import render,sheet

def main():
    out=ROOT/'docs/previews'
    combinations=[('instrument_classic','bellross_photo','black','InstrumentRing'),('sputnik','legacy_sputnik','ivory','SputnikRing'),('classic','sword','white','FiveMinuteLabels')]
    sheet([(f'{s} / {c}',render(s,b,hand_style=h,minute=True,hand_color=c,dial_tone='charcoal',complications=True,minute_track=t))
           for s,h,b,t in combinations for c in ('original','white','black','orange','green')],out/'personalization-5.5.jpg',columns=5,tile=360)
    sheet([(f'{s} / {"AOD" if ambient else "Active"} / minutes {minutes}',render(s,b,hand_style=h,minute=not ambient,aod_minute=minutes,ambient=ambient,seconds=True,second=45,hour=10,mins=30,complications=True,minute_track=t))
           for s,h,b,t in combinations for ambient,minutes in ((False,False),(True,False),(True,True))],out/'active-aod-5.5.jpg',columns=3,tile=432)
    sheet([(f'{size} / {inset}',render('instrument_classic','black',hand_style='bellross_photo',minute=True,complications=True,complication_size=size,digital_size=size,scale_inset=inset,minute_track='InstrumentRing'))
           for size in ('compact','normal','large') for inset in ('original','wide')],out/'sizes-insets-5.5.jpg',columns=2,tile=432)
    sheet([(f'{i:02} / {h}',render('classic','ivory',hand_style=h,minute=True,hour=10,mins=30,component='hands',output_size=432))
           for i,h in enumerate(VISIBLE_HAND_STYLES,1)],out/'hand-selection-numbered-5.5.jpg',columns=4,tile=360)
    (out/'hand-selection-numbered-5.5.txt').write_text('\n'.join(f'{i:02} {h}' for i,h in enumerate(VISIBLE_HAND_STYLES,1))+'\n',encoding='utf-8')
    render('sputnik','black',hand_style='legacy_sputnik',minute=True,component='hands',output_size=864).save(out/'sputnik-hands-5.5.png')
    # Exact 432px watch display, without enlargement or a simulated bezel.
    render('instrument_classic','black',hand_style='bellross_photo',minute=True,complications=True,minute_track='InstrumentRing',output_size=432).save(out/'watch-size-5.5.png')

if __name__=='__main__':main()
