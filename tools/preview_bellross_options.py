"""Full-size comparisons from the shipped scene, with QA complication data."""
from render import render,sheet
from generate import ROOT

if __name__=='__main__':
    out=ROOT/'docs/previews'
    themes=(('brown','br_orange'),('amber_dial','br_amber'),('mono_dial','br_mono'))
    sheet([(f'{tone} / {layout}',render('instrument_classic','black',complications=True,
        minute=True,dial_tone=tone,hand_color=hand,layout=layout))
        for tone,hand in themes for layout in ('br_round_belorus','br_square_podolskii')],
        out/'bellross-directions-5.6.jpg',columns=2,tile=432)
    styles=(('classic','white'),('minimal','black'),('sputnik','ivory'),
            ('instrument','black'),('aviator','black'),('instrument_classic','black'))
    sheet([(f'{style} / {size}',render(style,bg,complications=True,minute=True,
        layout='br_round',complication_size=size)) for style,bg in styles
        for size in ('compact','normal','large')],out/'large-widgets-all-styles-5.6.jpg',columns=3,tile=432)
    sheet([(f'{h:02}:{m:02} / {size}',render('instrument_classic','black',
        complications=True,minute=True,layout='br_round',hand_color='br_orange',
        complication_size=size,hour=h,mins=m))
        for size in ('compact','normal','large') for h,m in ((3,0),(10,30),(18,0))],
        out/'bellross-time-and-size-5.6.jpg',columns=3,tile=432)
    sheet([(f'{bg} / {palette}',render('instrument_classic',bg,minute=True,
        hand_color=palette)) for bg in ('white','ivory','black')
        for palette in ('br_orange','br_amber','br_mono')],
        out/'bellross-hand-backgrounds-5.6.jpg',columns=3,tile=432)
    render('instrument_classic','black',complications=True,minute=True,
        layout='br_round_podolskii',complication_size='large',dial_tone='brown',
        hand_color='br_orange').save(out/'watch-size-5.6.png')
    import xml.etree.ElementTree as E
    from generate import RES
    choices=[n.get('id') for n in E.parse(RES/'raw/watchface.xml').findall('UserConfigurations/ListConfiguration[@id="HandStyle"]/ListOption')]
    sheet([(f'{hand} / {bg} / auto',render('classic',bg,minute=True,hand_style=hand,
        hand_color='adaptive',digital_time=False)) for hand in choices
        for bg in ('white','ivory','black')],out/'adaptive-hands-all-5.6.jpg',columns=3,tile=432)
