"""Inspect the actual WFF tree and its hand PNGs, not independent mockup artwork."""
import itertools
import json
import math
from collections import deque
from PIL import Image,ImageDraw
from generate import ROOT,RES,STYLES,BACKGROUNDS,MINUTE_TRACKS,PRESETS,MODES,number_specs
from render import render,sheet,scene,font_file

def components(points):
    points=set(points);sizes=[]
    while points:
        p=points.pop();q=deque([p]);size=0
        while q:
            x,y=q.popleft();size+=1
            for dx,dy in itertools.product((-1,0,1),repeat=2):
                p=x+dx,y+dy
                if p in points:points.remove(p);q.append(p)
        sizes.append(size)
    return sorted(sizes)

def run():
    out=ROOT/'docs/previews';out.mkdir(exist_ok=True)
    # Actual renderer consumes the same XML nodes and PNGs shipped in the APK.
    for style in ('instrument','aviator'):
        for component in ('scale','hour','minute','hands','full'):
            im=render(style,'black',minute=True,component=component,output_size=432)
            im.save(out/f'{style}_{component}_432.png')
            im.resize((1296,1296),Image.Resampling.NEAREST).save(out/f'{style}_{component}_pixels.png')
        full=render(style,'black',minute=True,output_size=1296)
        full.crop((528,528,768,768)).resize((720,720),Image.Resampling.NEAREST).save(out/f'{style}_hub_closeup.png')
        render(style,'ivory',minute=True,component='hands').save(out/f'{style}_hands_ivory_432.png')
    sheet([(s.title()+' / '+label,render(s,'black',minute=True,component=component)) for s in ('instrument','aviator') for label,component in (('Scale / 96 positions','scale'),('Hands / single hub','hands'),('Full / 432 x 432','full'))],out/'instrument_graphics_review.jpg',columns=3,tile=432)
    # Scale candidates modify the parsed scene only for this comparison; 34 is shipped.
    candidates=[];xml=scene()
    for style,selected,sizes in (('instrument',30,(26,30,34)),('aviator',34,(28,34,40))):
        fonts=[el.find('Text/Font') for el in xml.findall(f'.//Group[@name="dial_{style}_black"]//PartText') if el.get('name','').startswith('hour_number_')]
        saved=[f.get('size') for f in fonts]
        for size in sizes:
            for f,original in zip(fonts,saved):f.set('size',str(float(original)*size/selected))
            candidates.append((f'{style.title()} / {size}px'+(' / selected' if size==selected else ''),render(style,'black',component='scale')))
        for f,original in zip(fonts,saved):f.set('size',original)
    sheet(candidates,out/'instrument_numeral_sizes.jpg',columns=3,tile=432)
    examples=(('sputnik','ivory','SputnikRing'),('instrument','black','InstrumentRing'),('classic','white','FiveMinuteLabels'),('minimal','black','TicksOnly'))
    sheet([(f'{s.title()} / {t}',render(s,b,minute=True,minute_track=t)) for s,b,t in examples],out/'minute_track_examples.jpg',columns=2,tile=432)
    for s,b,t in examples:render(s,b,minute=True,minute_track=t).save(out/f'{s}_{t}_432.png')
    sheet([(t,render('aviator','black',minute=True,minute_track=t)) for t in MINUTE_TRACKS],out/'minute_track_styles.jpg',columns=3,tile=432)
    import sys
    if '--previews-only' in sys.argv:return
    # Standalone WFF hour scale must contain exactly 96 connected marks at screen size.
    scale_components={}
    for style in ('instrument','aviator'):
        im=render(style,'black',component='ticks').convert('RGB')
        sizes=components((x,y) for y in range(432) for x in range(432) if max(im.getpixel((x,y)))>8)
        assert len(sizes)==96,(style,len(sizes),sizes)
        scale_components[style]=dict(count=len(sizes),minimum_pixels=min(sizes))
    hand_components={}
    for tone,part in itertools.product(('light','dark'),('hour','minute')):
        im=Image.open(RES/'drawable-nodpi'/f'precision_{part}_instrument_refined_{tone}.png').convert('RGBA')
        sizes=components((x,y) for y in range(im.height) for x in range(im.width) if im.getpixel((x,y))[3]>0)
        assert len(sizes)==1,(part,tone,sizes)
        assert im.getchannel('A').getbbox()[0]>0
        hand_components[f'{part}_{tone}']=len(sizes)
    # Exhaustive new-setting coverage, with minute hand both off and on.
    cases=0
    for s,b,t,mode,minute in itertools.product(STYLES,BACKGROUNDS,MINUTE_TRACKS,('none','color'),(False,True)):
        p=tuple(PRESETS)[(STYLES.index(s)+MINUTE_TRACKS.index(t)+int(minute))%2]
        assert render(s,b,mode,p,minute=minute,minute_track=t).getbbox()
        cases+=1
    report=dict(screen_pixels=[432,432],scale_components=scale_components,hand_components=hand_components,minute_track_renders=cases,numeral_size_selected=34,device_test=False)
    (ROOT/'docs/graphics-checks.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(report)

if __name__=='__main__':run()
