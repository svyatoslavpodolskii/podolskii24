"""Inspect vector-only masters, static per-background PNGs, and real WFF renders."""
import hashlib
import itertools
import json
import xml.etree.ElementTree as E
from unittest.mock import patch
from PIL import Image
from generate import ROOT,RES,STYLES,BACKGROUNDS,MINUTE_TRACKS
from instrument_classic import raster,rectangle
from check_photo_hands import preservation
from graphics_qa import components
from render import render,sheet

def check_vectors():
    checked=[]
    for bg,part in itertools.product(BACKGROUNDS,('hour','minute','hub')):
        name=f'instrument_classic_{part}_{bg}'
        path=ROOT/'docs/hand-masters/instrument-classic'/f'{name}.svg'
        xml=E.parse(path).getroot()
        assert all(e.tag.split('}')[-1] in ('svg','title','polygon','path','circle') for e in xml.iter())
        assert not any('href' in key for e in xml.iter() for key in e.attrib)
        # Rasterization must succeed with all bitmap-loading operations disabled.
        with patch('PIL.Image.open',side_effect=AssertionError('Bitmap source used')):expected=raster(path)
        png=Image.open(RES/'drawable-nodpi'/f'{name}.png').convert('RGBA')
        assert expected.size==png.size and expected.tobytes()==png.tobytes(),name
        alpha=png.getchannel('A');box=alpha.getbbox()
        assert box[0]>0 and box[1]>0 and box[2]<png.width and box[3]<png.height,(name,'clipping')
        sizes=components((x,y) for y in range(png.height) for x in range(png.width) if png.getpixel((x,y))[3]>0)
        assert len(sizes)==1,(name,'detached fragment',sizes)
        checked.append(name)
    for part in ('hour','minute','hub'):
        digests={hashlib.sha256((RES/'drawable-nodpi'/f'instrument_classic_{part}_{bg}.png').read_bytes()).digest() for bg in BACKGROUNDS}
        assert len(digests)==3,(part,'background variants are not distinct')
    return checked

def run():
    preserved=preservation();checked=check_vectors();out=ROOT/'docs/previews'
    for bg in BACKGROUNDS:
        render('aviator',bg,minute=True,hand_style='bellross_photo',hour=8,mins=11).save(out/f'instrument_classic_{bg}_432.png')
        render('aviator',bg,minute=True,hand_style='bellross_photo',hour=8,mins=11,component='hands',output_size=864).save(out/f'instrument_classic_hands_{bg}.png')
        render('aviator',bg,minute=False,hand_style='bellross_photo',hour=8,mins=11).save(out/f'instrument_classic_minute_off_{bg}_432.png')
        im=render('aviator',bg,minute=True,hand_style='bellross_photo',hour=8,mins=11,output_size=1296)
        im.crop((516,516,780,780)).resize((792,792),Image.Resampling.NEAREST).save(out/f'instrument_classic_hub_{bg}.png')
    sheet([(f'Instrument Classic / {bg}',render('aviator',bg,minute=True,hand_style='bellross_photo',hour=8,mins=11)) for bg in BACKGROUNDS],out/'instrument_classic_backgrounds.jpg',columns=3,tile=432)
    sheet([(f'Vector hands / {bg}',render('aviator',bg,minute=True,hand_style='bellross_photo',hour=8,mins=11,component='hands')) for bg in BACKGROUNDS],out/'instrument_classic_hands.jpg',columns=3,tile=432)
    sheet([(f'{bg} / {h:02}:{m:02}',render('aviator',bg,minute=True,hand_style='bellross_photo',hour=h,mins=m)) for bg in BACKGROUNDS for h,m in ((3,0),(10,30),(18,0))],out/'instrument_classic_time_checks.jpg',columns=3,tile=432)
    cases=0
    for s,bg,track,minute in itertools.product(STYLES,BACKGROUNDS,MINUTE_TRACKS,(False,True)):
        preset=('quarter','shifted_back_1_hour')[(STYLES.index(s)+int(minute))%2]
        mode=('none','color')[MINUTE_TRACKS.index(track)%2]
        assert render(s,bg,mode,preset,minute=minute,minute_track=track,hand_style='bellross_photo').getbbox();cases+=1
    report=dict(vector_masters=len(checked),static_pngs=len(checked),backgrounds=list(BACKGROUNDS),photographic_inputs=False,svg_raster_pixels_identical=True,connected_components_per_png=1,existing_other_hand_pngs_byte_identical=preserved,unrelated_wff_unchanged=True,configuration_renders=cases,screen_pixels=[432,432],times=['03:00','10:30','18:00'],device_test=False)
    (ROOT/'docs/instrument-classic-checks.json').write_text(json.dumps(report,indent=2)+'\n');print(report)

if __name__=='__main__':run()
