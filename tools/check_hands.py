"""Geometry, contrast, preservation, and requested-time checks for hand artwork."""
import itertools
import json
import math
import zipfile
import xml.etree.ElementTree as E
from PIL import Image
from generate import ROOT,RES,STYLES,BACKGROUNDS,HAND_STYLES,LEGACY_STYLES,number_specs,point,angle,palette,contrast
from render import render,font_file

def canonical(el):
    clone=E.fromstring(E.tostring(el))
    for n in clone.iter():
        if n.text is not None and not n.text.strip():n.text=None
        n.tail=None
    return E.tostring(clone)

def check():
    cases=0;min_gap=999;worst_contrast=999
    for style in STYLES:
        closest=999
        for h,r,size,family in number_specs(style):
            bb=font_file(family,round(size*3)).getbbox(str(h))
            w=(bb[2]-bb[0])/3*(.78 if style=='aviator' else 1);ht=(bb[3]-bb[1])/3;x,y=point(angle(h),r)
            closest=min(closest,math.hypot(max(abs(x-216)-w/2,0),max(abs(y-216)-ht/2,0)))
        tip_bound=158.1*(.75 if style=='aviator' else 1)
        gap=closest-tip_bound
        assert gap>1,(style,closest,tip_bound)
        min_gap=min(min_gap,gap)
    for kind,tone in itertools.product(HAND_STYLES[1:],('light','dark')):
        if kind.startswith(('legacy_','original_')) or kind=='bellross_photo':continue
        p=RES/'drawable-nodpi'/f'precision_hour_{kind}_{tone}.png'
        im=Image.open(p).convert('RGBA');alpha=im.getchannel('A');box=alpha.getbbox()
        assert box and box[0]>0 and box[2]<im.width,(kind,'horizontal clipping')
        assert box[1]>0 and box[3]<im.height,(kind,'vertical clipping')
        tip_y=40+box[1]/3
        assert (82<=tip_y<=85 if kind=='instrument_refined' else (102<=tip_y<=105 if kind.startswith('bellross') else 57<=tip_y<=60.5)),(kind,tip_y)
        assert 40+box[3]/3-216<=24,(kind,'oversized counterweight')
        # Each transverse section must offer a readable body OR outline on both tonal extremes.
        backgrounds=['#000000','#26332F','#E9E2CE','#FAFAF7'] if tone=='light' else ['#000000',*palette('sputnik','black')]
        for radius in ((28,70,125) if kind=='instrument_refined' else ((28,70,105) if kind.startswith('bellross') else (28,70,140,153))):
            y=round((216-radius-40)*3)
            pixels=[im.getpixel((x,y)) for x in range(im.width) if im.getpixel((x,y))[3]>=210]
            assert pixels,(kind,radius,'broken pointer')
            for bg in backgrounds:
                best=max(contrast('#%02X%02X%02X'%rgb[:3],bg) for rgb in pixels)
                assert best>=2.5,(kind,tone,radius,bg,best)
                worst_contrast=min(worst_contrast,best)
    # Genuine source-asset preservation against the previously delivered archive.
    previous=ROOT.parent/'TwentyFour-2.0-delivery.zip';preserved=0;stable_groups=0
    if previous.exists():
        with zipfile.ZipFile(previous) as z:
            for style,tone,part in itertools.product(LEGACY_STYLES,('light','dark'),('hand','minute')):
                path=RES/'drawable-nodpi'/f'{part}_{style}_{tone}.png'
                assert z.read('TwentyFour/'+path.relative_to(ROOT).as_posix())==path.read_bytes()
                preserved+=1
            old=E.fromstring(z.read('TwentyFour/watchface/src/main/res/raw/watchface.xml'));new=E.parse(RES/'raw/watchface.xml').getroot()
            for i in ('1','2','3'):
                assert canonical(old.find(f'Scene/ComplicationSlot[@slotId="{i}"]'))==canonical(new.find(f'Scene/ComplicationSlot[@slotId="{i}"]'))
            for style,bg,preset,mode in itertools.product(LEGACY_STYLES,BACKGROUNDS,('quarter','shifted_back_1_hour'),('lines','labels','color')):
                name=f'{style}_{bg}_{preset}_{mode}'
                # Hour scale intentionally changed; period fills/dividers/labels must not change.
                a=old.find(f'.//Group[@name="{name}"]');b=new.find(f'.//Group[@name="{name}"]')
                for el in (a,b):
                    for child in list(el):
                        if child.tag=='Group' and child.get('name','').startswith('scale_on_'):el.remove(child)
                assert canonical(a)==canonical(b),(name,'period mechanism changed')
                stable_groups+=1
    for kind,bg,(h,m) in itertools.product(HAND_STYLES[1:],BACKGROUNDS,((3,0),(10,30),(18,0))):
        for mode in ('none','color'):
            assert render('classic',bg,mode,hand_style=kind,hour=h,mins=m,minute=True).getbbox()
            cases+=1
    report={'hand_variants':len(HAND_STYLES)-1,'requested_time_renders':cases,'legacy_pngs_byte_identical':preserved,'original_sector_groups_identical':stable_groups,'minimum_hour_tip_to_numeral_gap_px':round(min_gap,2),'minimum_best_cross_section_contrast':round(worst_contrast,2),'times':['03:00','10:30','18:00'],'device_test':False}
    (ROOT/'docs/hand-checks.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(report)
if __name__=='__main__':check()
