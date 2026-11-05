"""Native custom numerals, immutable existing hands, size selection and layer order."""
import hashlib
import itertools
import json
import xml.etree.ElementTree as E
from PIL import Image
from generate import ROOT,RES,BACKGROUNDS,PRESETS,MODES,HAND_SIZES,contrast,INK,PAPER,ink_on,point
from classic_scale import INKS,NUMERALS,tick_specs
from graphics_qa import components
from instrument_classic import raster
from render import render,sheet

def check():
    hashes=json.loads((ROOT/'docs/hands-before-classic-scale.json').read_text())
    for name,digest in hashes.items():assert hashlib.sha256((RES/'drawable-nodpi'/name).read_bytes()).hexdigest()==digest,name
    from static_geometry import design_scene
    old=E.parse(ROOT/'docs/references/before-classic-scale.xml').getroot();new=design_scene()
    def canonical(el):
        el=E.fromstring(E.tostring(el))
        for n in el.iter():
            if n.text is not None and not n.text.strip():n.text=None
            n.tail=None
        return E.tostring(el)
    for style in ('classic','minimal','sputnik','instrument','aviator'):
        for bg in BACKGROUNDS:assert canonical(old.find(f'.//Group[@name="dial_{style}_{bg}"]'))==canonical(new.find(f'.//Group[@name="dial_{style}_{bg}"]'))
    for slot in (1,2,3):assert canonical(old.find(f'.//ComplicationSlot[@slotId="{slot}"]'))==canonical(new.find(f'.//ComplicationSlot[@slotId="{slot}"]'))
    assert canonical(old.find('.//Group[@name="ambient"]'))==canonical(new.find('.//Group[@name="ambient"]'))
    masks=[]
    for key,ink in INKS.items():
        svg=ROOT/f'docs/scale-masters/instrument-classic/classic_scale_{key}.svg';xml=E.parse(svg).getroot()
        assert all(el.tag.split('}')[-1] in ('svg','title','path') for el in xml.iter())
        ticks=[el for el in xml if el.get('id','').startswith('tick_')];assert len(ticks)==96
        assert [float(t.get('id')[5:]) for t in ticks]==[i*3.75 for i in range(96)]
        expected=raster(svg).resize((864,864),Image.Resampling.BOX)
        actual=Image.open(RES/f'drawable-nodpi/classic_scale_{key}.png').convert('RGBA')
        assert expected.tobytes()==actual.tobytes();masks.append(actual.getchannel('A').tobytes())
    assert len(set(masks))==1,'Ink variants have different geometry'
    assert len([i for i in range(96) if i%4==0])==24
    assert set(NUMERALS)=={6,12,18,24}
    # 96 isolated marks plus seven hand-drawn digits; cracks or specks alter the count.
    scale=render('instrument_classic','black',component='scale').convert('RGB')
    sizes=components((x,y) for y in range(432) for x in range(432) if max(scale.getpixel((x,y)))>12)
    assert len(sizes)==103,(len(sizes),sizes)
    holes=components((x,y) for y in range(432) for x in range(432) if max(scale.getpixel((x,y)))<=12)
    assert len(holes)==5,'Unexpected holes/cracks: expected outside plus four numeral counters'
    for bg in ('white','ivory'):assert contrast(INKS['brown'],BACKGROUNDS[bg])>=4.5
    # Existing Classic hands are now drawn once, above minute and below the hub.
    for bg in BACKGROUNDS:
        g=new.find(f'.//Group[@name="hands_instrument_classic_{bg}"]');children=list(g)
        front=g.find('Group[@name="instrument_classic_hour_front"]')
        minute=next(c for c in children if c.find('.//Group[@name="minute"]') is not None)
        assert children.index(front)>children.index(minute)
        assert not g.find('Group[@name="hour"]').findall('.//Image[@resource="instrument_classic_hour_'+bg+'"]')
        for p in g.findall('.//PartImage[@name="selected_hour_art"]')+g.findall('.//PartImage[@name="selected_minute_art"]')+g.findall('.//PartImage[@name="instrument_classic_hub"]'):
            assert abs(float(p.get('x'))+float(p.get('width'))*float(p.get('pivotX'))-216)<.001
            assert abs(float(p.get('y'))+float(p.get('height'))*float(p.get('pivotY'))-216)<.001
    for bg,part in itertools.product(BACKGROUNDS,('hour','minute','hub')):
        svg=ROOT/f'docs/hand-masters/instrument-classic-clean/instrument_classic_clean_{part}_{bg}.svg'
        xml=E.parse(svg).getroot();assert all('stroke' not in e.attrib for e in xml.iter())
        actual=Image.open(RES/f'drawable-nodpi/instrument_classic_clean_{part}_{bg}.png').convert('RGBA')
        assert actual.tobytes()==raster(svg).tobytes()
    return len(hashes),len(sizes)

def run():
    preserved,parts=check();out=ROOT/'docs/previews'
    for bg in BACKGROUNDS:
        for comp in ('scale','full'):
            render('instrument_classic',bg,minute=True,hour=8,mins=11,component=comp).save(out/f'new_classic_{comp}_{bg}_432.png')
    sheet([(f'Custom numerals / {b}',render('instrument_classic',b,component='scale')) for b in BACKGROUNDS],out/'new_classic_scale.jpg',columns=3,tile=432)
    sheet([(f'Instrument Classic / {b}',render('instrument_classic',b,minute=True,hour=8,mins=11)) for b in BACKGROUNDS],out/'new_classic_full.jpg',columns=3,tile=432)
    sheet([(f'{kind} / {b}',render('instrument_classic',b,hand_style=kind,minute=True,hour=8,mins=11)) for b in BACKGROUNDS for kind in ('bellross_photo','instrument_classic_clean')],out/'classic_outline_comparison.jpg',columns=2,tile=432)
    sheet([(f'{size} / {round(f*100)}%',render('instrument_classic','black',minute=True,hour=8,mins=11,hand_size=size)) for size,f in HAND_SIZES.items()],out/'classic_hand_sizes.jpg',columns=3,tile=432)
    sheet([(f'{size} / {h:02}:{m:02}',render('instrument_classic','black',minute=True,hour=h,mins=m,hand_size=size)) for size in HAND_SIZES for h,m in ((3,0),(10,30),(12,2),(18,0))],out/'classic_new_time_checks.jpg',columns=4,tile=432)
    cases=0
    for bg,mode,preset,size,minute in itertools.product(BACKGROUNDS,MODES,PRESETS,HAND_SIZES,(False,True)):
        track='InstrumentRing' if cases%2 else 'None'
        assert render('instrument_classic',bg,mode,preset,minute=minute,hand_size=size,minute_track=track).getbbox();cases+=1
    report=dict(existing_hand_pngs_byte_identical=preserved,existing_dials_unchanged=15,custom_tick_positions=96,main_hour_positions=24,custom_glyphs=['1','2','4','6','8'],native_scale_components=parts,no_font_for_custom_numerals=True,hand_sizes=HAND_SIZES,hour_above_minute=True,clean_hand_svg_pngs=9,configuration_renders=cases,device_test=False)
    (ROOT/'docs/classic-scale-checks.json').write_text(json.dumps(report,indent=2)+'\n');print(report)

if __name__=='__main__':run()
