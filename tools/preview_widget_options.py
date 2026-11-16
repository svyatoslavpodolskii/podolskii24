"""Compare only shipped settings on identical native XML scenes."""
from generate import ROOT
from render import render,sheet

def main():
    out=ROOT/'docs/previews'
    shared=dict(style='sputnik',background='black',sectors='color',minute=True,
        minute_track='SputnikRing',complications=True,layout='bottom',hand_style='legacy_sputnik')
    sheet([(mode,render(**shared,digital_size='n_'+mode)) for mode in ('plain','outline','frame','box')],
        out/'time-decoration-5.7.2.jpg',columns=4,tile=432)
    for style,bg in (('instrument_classic','black'),('classic','ivory')):
        panels=[]
        for spread in ('','_wide'):
            for size in ('compact','normal','large','huge'):
                panels.append((size+spread,render(style=style,background=bg,minute=True,complications=True,
                    layout='br_round',complication_size=size+spread,digital_size='l_plain',
                    hand_color='br_orange' if style=='instrument_classic' else 'black')))
        sheet(panels,out/f'widget-sizes-{style}-5.7.2.jpg',columns=4,tile=432)

    panels=[]
    for style in ('classic','minimal','sputnik','instrument','aviator','instrument_classic'):
        for size,clock in (('normal',True),('huge',False)):
            panels.append((f'{style} / {size} / time {clock}',render(style=style,
                background='ivory' if style in ('classic','sputnik') else 'black',
                minute=True,minute_track='TicksOnly',complications=True,layout='trio',
                complication_size=size,digital_time=clock,digital_size='l_plain')))
    sheet(panels,out/'equal-trio-5.7.2.jpg',columns=4,tile=432)

if __name__=='__main__':main()
