"""Raster/layout QA using the same bundled fonts; not an on-watch test."""
import itertools
import math
import json
from PIL import Image,ImageDraw,ImageChops
from generate import ROOT,STYLES,BACKGROUNDS,PRESETS,MODES,DIVIDERS,number_specs,angle,point,SLOTS,SLOT_SIZE,palette,period_index,ink_on
from render import render,font_file

def check_text_layout():
    # Ink footprints, not large container rectangles, govern glyph clearance.
    min_gap=999
    for style in STYLES:
        boxes=[]
        for hour,r,size,family in number_specs(style):
            f=font_file(family,size*3);box=f.getbbox(str(hour))
            w=(box[2]-box[0])/3*(.78 if style=='aviator' else 1);h=(box[3]-box[1])/3;x,y=point(angle(hour),r)
            boxes.append((x-w/2,y-h/2,x+w/2,y+h/2))
            assert math.hypot(abs(x-216)+w/2,abs(y-216)+h/2)<(214 if style=='aviator' else 200),(style,hour,'safe field')
        for a,b in itertools.combinations(boxes,2):
            dx=max(a[0]-b[2],b[0]-a[2],0);dy=max(a[1]-b[3],b[1]-a[3],0)
            assert dx or dy,(style,'numeral collision')
            min_gap=min(min_gap,math.hypot(dx,dy))
        for preset,bounds in PRESETS.items():
            for hour,label in zip(bounds,('УТРО','ДЕНЬ','ВЕЧЕР','НОЧЬ')):
                a=angle(hour+3);cx,cy=point(a,149)
                # Rotated label bounds in watch coordinates, tested against slot disks.
                f=font_file('roboto_condensed',48);bb=f.getbbox(label)
                w=(bb[2]-bb[0])/3;h=(bb[3]-bb[1])/3
                for x,y in SLOTS:
                    sx,sy=x+SLOT_SIZE/2,y+SLOT_SIZE/2
                    ar=math.radians(a);dx=sx-cx;dy=sy-cy
                    tx=dx*math.cos(ar)+dy*math.sin(ar);ty=-dx*math.sin(ar)+dy*math.cos(ar)
                    dist=math.hypot(max(abs(tx)-w/2,0),max(abs(ty)-h/2,0))
                    assert dist>SLOT_SIZE/2+7,(preset,label,'slot collision')
                # Period labels retain their agreed band; longer optional hands may sweep over it.
                assert 149-h/2>137,(label,'period label band')
    return round(min_gap,2)

def main():
    min_gap=check_text_layout();baseline=render(ambient=True).convert('RGB');total=0;color_images={}
    for style,bg,mode,preset,minute in itertools.product(STYLES,BACKGROUNDS,MODES,PRESETS,(False,True)):
        im=render(style,bg,mode,preset,minute)
        assert im.getbbox() is not None
        if mode=='none' and preset=='quarter':
            aod=render(style,bg,mode,preset,minute,ambient=True).convert('RGB')
            assert ImageChops.difference(aod,baseline).getbbox() is None
        if mode=='color' and not minute:color_images[(style,bg,preset)]=im.convert('RGB')
        total+=1
    divider_renders=0
    for preset,kind,mode in itertools.product(PRESETS,DIVIDERS,('lines','labels','color')):
        im=render('sputnik','ivory',mode,preset,dividers=kind)
        assert im.getbbox() is not None
        divider_renders+=1
    for preset,kind in itertools.product(PRESETS,DIVIDERS):
        assert render('instrument','black','color',preset,dividers=kind).getbbox() is not None
        divider_renders+=1
    # Explicit empty/populated comparison; demo values exist only in the preview tool.
    for style,bg,preset in itertools.product(STYLES,BACKGROUNDS,PRESETS):
        a=render(style,bg,'color',preset);b=render(style,bg,'color',preset,complications=True)
        assert ImageChops.difference(a.convert('RGB'),b.convert('RGB')).getbbox() is not None
    lit=sum(max(p)>20 for p in baseline.get_flattened_data())/(432*432)
    pixels=check_numeral_pixels(color_images)
    report={'micro_configurations_rendered':total,'additional_divider_cases_rendered':divider_renders,'populated_slot_combinations':len(STYLES)*len(BACKGROUNDS)*len(PRESETS),'minimum_numeral_gap_px':min_gap,'contrasting_numeral_pixels_checked':pixels,'aod_lit_pixel_ratio':round(lit,5),'device_test':False}
    (ROOT/'docs/preview-checks.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(report)

def check_numeral_pixels(images):
    checked=0
    for style in STYLES:
        mask=Image.new('L',(432*3,432*3));d=ImageDraw.Draw(mask)
        for hour,r,size,family in number_specs(style):
            x,y=point(angle(hour),r);f=font_file(family,size*3);bb=d.textbbox((0,0),str(hour),font=f)
            # Identical container placement and ink alignment to the preview renderer.
            tw,th=(128,70) if style=='aviator' else (44,40)
            patch=Image.new('L',(tw*3,th*3));pd=ImageDraw.Draw(patch)
            pd.text(((tw*3-bb[2]-bb[0])/2,(th*3-bb[3]-bb[1])/2),str(hour),font=f,fill=255)
            if style=='aviator':patch=patch.resize((round(tw*3*.78),th*3),Image.Resampling.LANCZOS)
            cx=(round(x-tw/2)+tw/2)*3;cy=(round(y-th/2)+th/2)*3
            mask.paste(patch,(round(cx-patch.width/2),round(cy-patch.height/2)))
        mask=mask.resize((432,432),Image.Resampling.LANCZOS)
        points=[(x,y) for y in range(432) for x in range(432) if mask.getpixel((x,y))>=235]
        for bg,preset in itertools.product(BACKGROUNDS,PRESETS):
            im=images[(style,bg,preset)];colors=palette(style,bg)
            for x,y in points:
                a=math.degrees(math.atan2(x-216,216-y))%360
                # Boundary antialiasing naturally blends both inks within ~1 pixel.
                distance=min(abs((a-angle(h)+180)%360-180) for h in PRESETS[preset])*math.pi/180*180
                if distance<1.8:continue
                color=ink_on(colors[period_index((a/15+12)%24,preset)])
                expected=tuple(int(color[i:i+2],16) for i in (1,3,5));actual=im.getpixel((x,y))
                # Lanczos can overshoot dark stroke edges; opposite-polarity ink differs by >190.
                assert max(abs(a-b) for a,b in zip(expected,actual))<64,(style,bg,preset,x,y,expected,actual)
                checked+=1
    return checked
if __name__=='__main__':main()
