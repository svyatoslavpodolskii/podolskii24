"""Native-size lettering, layer-order and light-hand comparisons for 5.6.1."""
from render import render,sheet
from generate import ROOT

if __name__=='__main__':
    out=ROOT/'docs/previews'
    sheet([(bg+' / '+name,render('instrument_classic',bg,minute=True,
        complications=True,layout=name,hand_color='br_orange'))
        for bg in ('white','ivory','black')
        for name in ('br_round_belorus','br_round_podolskii')],
        out/'lettering-and-backgrounds-5.6.1.jpg',columns=2,tile=432)
    sheet([(bg+' / '+str(h),render('instrument_classic',bg,minute=True,
        layout='br_round_belorus',hand_color='br_orange',hour=h,mins=m))
        for bg in ('white','ivory','black') for h,m in ((12,0),(10,8),(18,0))],
        out/'lettering-layer-check-5.6.1.jpg',columns=3,tile=432)
    render('instrument_classic','ivory',minute=True,complications=True,
        layout='br_round_belorus',hand_color='br_orange').save(out/'watch-size-5.6.1.png')
