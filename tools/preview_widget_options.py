"""Compare only shipped settings on identical native XML scenes."""
from generate import ROOT
from render import render,sheet

def main():
    out=ROOT/'docs/previews'
    shared=dict(style='sputnik',background='black',sectors='color',minute=True,
        minute_track='SputnikRing',complications=True,layout='bottom',hand_style='legacy_sputnik')
    sheet([(mode,render(**shared,digital_size='n_'+mode)) for mode in ('plain','outline','frame','box')],
        out/'time-decoration-5.7.jpg',columns=4,tile=432)
    for style,bg in (('instrument_classic','black'),('classic','ivory')):
        panels=[]
        for spread in ('','_wide'):
            for size in ('compact','normal','large','huge'):
                panels.append((size+spread,render(style=style,background=bg,minute=True,complications=True,
                    layout='br_round',complication_size=size+spread,digital_size='n_plain',
                    hand_color='br_orange' if style=='instrument_classic' else 'black')))
        sheet(panels,out/f'widget-sizes-{style}-5.7.jpg',columns=4,tile=432)

if __name__=='__main__':main()
