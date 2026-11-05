"""Reference-drawn Sputnik set and true transparent Instrument slot.

Earlier masters remain unchanged. Only the two requested runtime choices change.
"""
from functools import lru_cache
import math
import xml.etree.ElementTree as E
from PIL import Image
from generate import ROOT,RES
from instrument_classic import NS,raster

def sputnik(part,tone):
    rect=(196,76,40,164) if part=='hour' else (204,26,24,216)
    x,y,w,h=rect
    root=E.Element('{'+NS+'}svg',viewBox=f'0 0 {w} {h}')
    E.SubElement(root,'{'+NS+'}title').text=f'Sputnik reference / {part} / {tone}; pivot {216-x},{216-y}'
    dark=tone=='dark';body='#342B27';rim='#AF9C7B' if dark else '#1B2220'
    def path(commands,fill,stroke=None,width=.65):
        tokens=[]
        for cmd,*values in commands:
            tokens.append(cmd+' '.join(str(v-(x if i%2==0 else y)) for i,v in enumerate(values)))
        a=dict(d=' '.join(tokens),fill=fill)
        if stroke:a.update(stroke=stroke,**{'stroke-width':str(width),'stroke-linejoin':'round'})
        E.SubElement(root,'{'+NS+'}path',a)
    if part=='hour':
        path([('M',216,78),('C',218,91,224.5,126,225,146),('C',225.5,167,221,194,218,210),('L',218,231),('L',214,231),('L',214,210),('C',211,193,206.5,167,207,146),('C',207.5,126,214,91,216,78),('Z',)],body,rim)
        path([('M',216,80),('C',219,101,224,129,224.5,148),('C',224,171,220,194,217.5,209),('L',216,209),('Z',)],'#71513E')
        path([('M',216,96),('C',218,111,220.5,134,220.5,149),('C',220,168,218,187,216,201),('C',214,187,212,168,211.5,149),('C',211.5,134,214,111,216,96),('Z',)],'#EEEBD3','#1C2420',.45)
        E.SubElement(root,'{'+NS+'}circle',cx=str(216-x),cy=str(216-y),r='4.8',fill=body,stroke=rim,**{'stroke-width':'.65'})
        E.SubElement(root,'{'+NS+'}circle',cx=str(216-x),cy=str(216-y),r='1.3',fill='#B9B39B')
    else:
        path([('M',216,28),('C',217.5,46,221,84,221.5,137),('C',221.5,165,219,193,218,211),('L',218,234),('L',214,234),('L',214,211),('C',213,193,210.5,165,210.5,137),('C',211,84,214.5,46,216,28),('Z',)],body,rim)
        path([('M',216,30),('C',218,57,220.5,91,221,139),('C',220.5,169,218.5,196,217,211),('L',216,211),('Z',)],'#71513E')
        path([('M',216,54),('C',217.3,77,218,111,218,143),('C',218,167,217,190,216,204),('C',215,190,214,167,214,143),('C',214,111,214.7,77,216,54),('Z',)],'#EEEBD3','#1C2420',.4)
    return root,rect

def cropped_asset(image,rect,name):
    x,y,w,h=rect;sx=image.width/w;sy=image.height/h
    assert sx==sy and sx==int(sx)
    scale=int(sx);l,t,r,b=image.getbbox()
    l=max(0,(l//scale-1)*scale);t=max(0,(t//scale-1)*scale)
    r=min(image.width,(math.ceil(r/scale)+1)*scale);b=min(image.height,(math.ceil(b/scale)+1)*scale)
    image.crop((l,t,r,b)).save(RES/'drawable-nodpi'/f'{name}.png',optimize=True)
    return (x+l//scale,y+t//scale,(r-l)//scale,(b-t)//scale)

@lru_cache(maxsize=1)
def build():
    out=ROOT/'docs/hand-masters/sputnik-reference';out.mkdir(parents=True,exist_ok=True)
    records={}
    for tone in ('light','dark'):
        for part in ('hour','minute'):
            svg,rect=sputnik(part,tone);name=f'updated_sputnik_{part}_{tone}'
            path=out/(name+'.svg');E.indent(svg,space='  ');E.ElementTree(svg).write(path,encoding='utf8',xml_declaration=True)
            image=raster(path)
            # 2x native resolution is ample for the narrow watch hands.
            image=image.resize((rect[2]*2,rect[3]*2),Image.Resampling.LANCZOS)
            records[('legacy_sputnik',part,tone)]=(name,cropped_asset(image,rect,name))
        from hand_art import make
        name=f'updated_instrument_slot_{tone}'
        image=make('instrument_white',tone,master=True,cutout=True)
        records[('instrument_white','hour',tone)]=(name,cropped_asset(image,(192,40,48,208),name))
    return records

def apply(root):
    records=build()
    for part in root.iter('PartImage'):
        image=part.find('Image');name=image.get('resource','')
        key=None
        for tone in ('light','dark'):
            for hand in ('hour','minute'):
                legacy=('hand_' if hand=='hour' else 'minute_')+'sputnik_'+tone
                if name in (legacy,'trimmed_'+legacy):key=('legacy_sputnik',hand,tone)
            if name in (f'precision_hour_instrument_white_{tone}',f'trimmed_precision_hour_instrument_white_{tone}'):
                key=('instrument_white','hour',tone)
        if key is None:continue
        resource,(x,y,w,h)=records[key]
        part.attrib.update(x=str(x),y=str(y),width=str(w),height=str(h),pivotX=str((216-x)/w),pivotY=str((216-y)/h))
        image.set('resource',resource)
    from render import render
    for kind in ('legacy_sputnik','instrument_white'):
        icon='editor_updated_'+kind
        option=root.find(f'UserConfigurations/ListConfiguration[@id="HandStyle"]/ListOption[@id="{kind}"]')
        option.set('icon',icon)
        render(background='black',hand_style=kind,minute=True,component='hands',output_size=144,subtree=root,digital_time=False).save(RES/'drawable-nodpi'/f'{icon}.png',optimize=True)
