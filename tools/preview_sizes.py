"""Independent size comparisons from the actual generated WFF scene."""
from render import render,sheet
from generate import ROOT

if __name__=='__main__':
    out=ROOT/'docs/previews'
    styles=(('classic','white'),('minimal','black'),('sputnik','ivory'),
            ('instrument','black'),('aviator','black'),('instrument_classic','black'))
    sizes=('compact','normal','large')
    for layout in ('bottom','top'):
        sheet([(f'{style} / widgets: {size}',render(style,bg,
            complications=True,minute=True,layout=layout,complication_size=size,
            digital_size='normal')) for style,bg in styles for size in sizes],
            out/f'widget-sizes-{layout}-5.5.3.jpg',columns=3,tile=432)
        sheet([(f'{style} / time: {size}',render(style,bg,
            complications=True,minute=True,layout=layout,complication_size='normal',
            digital_size=size)) for style,bg in styles for size in sizes],
            out/f'clock-sizes-{layout}-5.5.3.jpg',columns=3,tile=432)
    for style,bg in (styles[2],styles[-1]):
        sheet([(f'widgets {comp} / clock {clock}',render(style,bg,
            complications=True,minute=True,complication_size=comp,digital_size=clock))
            for comp in sizes for clock in sizes],out/f'{style}-sizes-matrix-5.5.3.jpg',columns=3,tile=432)
