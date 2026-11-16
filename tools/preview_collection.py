"""Curated native-WFF recipes; no extra runtime images or configurations."""
import json
from PIL import Image
from generate import ROOT
from render import render,sheet

RECIPES=[
 ('01 Copper / Instrument Classic',dict(style='instrument_classic',background='black',dial_tone='brown',hand_color='br_orange',layout='br_round_podolskii',complication_size='large')),
 ('02 Porcelain / Instrument Classic',dict(style='instrument_classic',background='black',dial_tone='mono_dial',hand_color='br_mono',layout='br_square',complication_size='normal')),
 ('03 Amber / Instrument Classic',dict(style='instrument_classic',background='black',dial_tone='amber_dial',hand_color='br_amber',layout='br_round',complication_size='normal')),
 ('04 Ivory / Classic',dict(style='classic',background='ivory',hand_color='black',hand_style='legacy_classic',layout='trio',complication_size='normal',dividers='classic',sectors='none',minute_track='None')),
 ('05 Silver / Classic',dict(style='classic',background='white',hand_color='black',hand_style='sword',layout='trio',digital_time=False,minute_track='FiveMinuteLabels',complication_size='large')),
 ('06 Midnight / Classic',dict(style='classic',background='black',dial_tone='navy',hand_color='white',hand_style='legacy_classic',layout='br_round',complication_size='huge_wide',minute_track='TicksOnly')),
 ('07 Paper / Minimal',dict(style='minimal',background='white',hand_color='black',hand_style='legacy_minimal',complications=False,digital_time=False,minute_track='None')),
 ('08 Obsidian / Minimal',dict(style='minimal',background='black',dial_tone='original',hand_color='white',hand_style='sword',layout='trio',complication_size='normal',minute_track='TicksOnly')),
 ('09 Quiet hours / Minimal',dict(style='minimal',background='ivory',hand_color='black',hand_style='sword',layout='bottom',complication_size='compact',sectors='lines',dividers='arc',minute_track='None')),
 ('10 Quarter / Sputnik',dict(style='sputnik',background='ivory',hand_style='legacy_sputnik',hand_color='white',sectors='color',boundaries='quarter',dividers='classic',minute_track='SputnikRing',layout='bottom',complication_size='compact',digital_size='n_plain')),
 ('11 Expedition / Sputnik',dict(style='sputnik',background='white',hand_style='legacy_sputnik',hand_color='white',sectors='color',boundaries='shifted_back_1_hour',dividers='radial',minute_track='SputnikRing',layout='bottom',complication_size='large_wide',digital_size='n_plain')),
 ('12 Polar night / Sputnik',dict(style='sputnik',background='black',hand_style='legacy_sputnik',hand_color='white',sectors='color',dividers='micro',minute_track='SputnikRing',layout='bottom',complication_size='huge_wide',digital_size='n_plain')),
 ('13 Flight / Instrument',dict(style='instrument',background='black',hand_style='instrument_refined',hand_color='white',minute_track='InstrumentRing',minute_color='neutral',layout='br_round',complication_size='compact')),
 ('14 Technical / Instrument',dict(style='instrument',background='white',hand_style='instrument_white',hand_color='black',minute_track='InstrumentRing',minute_color='neutral',layout='br_square',complication_size='large_wide')),
 ('15 Field / Instrument',dict(style='instrument',background='black',dial_tone='forest',hand_style='instrument_white',hand_color='white',minute_track='TicksOnly',layout='br_round',complication_size='compact')),
 ('16 Cockpit / Aviator',dict(style='aviator',background='black',hand_style='instrument_refined',hand_color='orange',minute_track='InstrumentRing',minute_color='orange',layout='trio',digital_time=False,complication_size='normal')),
 ('17 Silver / Aviator',dict(style='aviator',background='white',hand_style='instrument_white',hand_color='black',sectors='none',layout='trio',complication_size='large',digital_time=False)),
 ('18 Night panel / Aviator',dict(style='aviator',background='black',dial_tone='navy',hand_style='instrument_white',hand_color='orange',minute_track='TicksOnly',minute_color='orange',layout='br_square',complication_size='huge_wide')),
]

def options(overrides):
    return dict(dict(minute=True,complications=True,digital_time=True,hand_color='original',
                     seconds=False,second=40,aod_minute=True,digital_size='l_plain'),**overrides)

if __name__=='__main__':
    out=ROOT/'docs/previews';panels=[];records=[]
    for title,recipe in RECIPES:
        config=options(recipe)
        image=render(**config)
        image.save(out/(title[:2]+'-collection-5.7.2.png'))
        panels.append((title,image));records.append(dict(name=title,settings=config))
    sheet(panels,out/'collection-18-5.7.2.jpg',columns=3,tile=432)
    for i in range(0,18,3):
        sheet(panels[i:i+3],out/f'collection-{i+1:02}-{i+3:02}-5.7.2.jpg',columns=3,tile=432)
    selected=[0,3,7,9,12,15]
    sheet([panels[i] for i in selected],out/'collection-selected-5.7.2.jpg',columns=3,tile=432)
    sheet([(RECIPES[i][0],render(**dict(options(RECIPES[i][1]),ambient=True))) for i in selected],
          out/'collection-aod-5.7.2.jpg',columns=3,tile=432)
    (out/'collection-settings-5.7.2.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
    comparison=[]
    for number in (1,9,10):
        for version,label in (('5.6.2','Before'),('5.7.2','After')):
            comparison.append((f'{number:02} / {label}',Image.open(out/f'{number:02}-collection-{version}.png').convert('RGBA')))
    sheet(comparison,out/'layout-corrections-5.7.2.jpg',columns=2,tile=432)
