"""Reproducible previews of the shipped complication layout (not device captures)."""
from render import render, sheet
from generate import ROOT

if __name__ == '__main__':
    out=ROOT/'docs/previews'
    sheet([(f'{layout} / {size} / {bg}',render('instrument_classic',bg,
        complications=True,minute=True,complication_size=size,layout=layout))
        for layout in ('bottom','top') for bg in ('black','ivory')
        for size in ('compact','normal','large')],out/'layout-5.5.2.jpg',columns=3)
    sheet([(f'{style} / {layout} / {size}',render(style,bg,complications=True,
        minute=True,complication_size=size,layout=layout))
        for style,bg in (('sputnik','ivory'),('classic','white'),('minimal','black'))
        for layout in ('bottom','top') for size in ('compact','normal','large')],
        out/'layout-other-styles-5.5.2.jpg',columns=3)
