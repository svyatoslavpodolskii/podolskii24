"""Offline XML visual QA, using the bundled fonts/assets; NOT a Wear OS renderer."""
import math
import re
import xml.etree.ElementTree as E
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFont, ImageChops
from generate import ROOT, RES, STYLES, BACKGROUNDS, SIZE

S=3
@lru_cache(maxsize=1)
def scene():return E.parse(RES/'raw/watchface.xml').getroot()
@lru_cache(maxsize=64)
def font_file(family,size):return ImageFont.truetype(str(RES/'font'/f'{family}.ttf'),size)
@lru_cache(maxsize=128)
def bitmap(name):return Image.open(RES/'drawable-nodpi'/f'{name}.png').convert('RGBA')

@lru_cache(maxsize=3)
def sample_icon(name):
    """QA-only stand-ins; the watch receives actual provider images."""
    im=Image.new('RGBA',(64,64));d=ImageDraw.Draw(im)
    if name=='qa_weather':
        d.ellipse((19,19,45,45),outline='white',width=5)
        for a in range(0,360,45):
            rad=math.radians(a);d.line([(32+22*math.cos(rad),32+22*math.sin(rad)),(32+29*math.cos(rad),32+29*math.sin(rad))],fill='white',width=4)
    elif name=='qa_stress':d.line([(3,35),(15,35),(23,18),(33,47),(43,26),(49,35),(61,35)],fill='white',width=5)
    elif name=='qa_calendar':
        d.rounded_rectangle((9,13,55,56),radius=5,outline='white',width=5)
        d.line((10,27,54,27),fill='white',width=4)
        for x in (23,42):d.line((x,6,x,21),fill='white',width=5)
    else:raise ValueError(name)
    return im
def evaluate(expr,config,hour,minute,data=None):
    values={'HOUR_0_23':hour,'MINUTE':minute}
    values.update({'CONFIGURATION.'+k:v for k,v in config.items()})
    if data:values.update({'COMPLICATION.'+k:v for k,v in data.items()})
    expr=re.sub(r'\[([^]]+)\]',lambda m:repr(values[m[1]]),expr)
    expr=expr.replace('&&',' and ').replace('||',' or ')
    def ternary(value):
        if '?' not in value:return value
        test,rest=value.split('?',1);yes,no=rest.split(':',1)
        return '('+yes+' if '+test+' else '+ternary(no)+')'
    expr=ternary(expr)
    expr=re.sub(r'#[0-9A-Fa-f]{6,8}\b',lambda m:repr(m[0]),expr)
    return eval(expr,{'__builtins__':{},'null':None,'clamp':lambda x,a,b:max(a,min(b,x)),'textLength':lambda x:len(x or '')},{})

def render(style='classic',background='white',sectors='none',boundaries='quarter',minute=False,ambient=False,hour=10,mins=8,complications=False,output_size=432,dividers='micro',hand_style='auto',minute_track='None',component='full',hand_size='Original',subtree=None,transparent=False,minute_color='neutral',digital_time=True):
    config={'style':style,'background':background,'sectors':sectors,'boundaries':boundaries,'dividers':dividers,'HandStyle':hand_style,'MinuteTrackStyle':minute_track,'HandSize':hand_size,'minute':'TRUE' if minute else 'FALSE'}
    config['MinuteColor']=minute_color
    config['DigitalTime']='TRUE' if digital_time else 'FALSE'
    im=Image.new('RGBA',(SIZE*S,SIZE*S),(0,0,0,0) if transparent else (BACKGROUNDS[background] if component in ('hands','hour','minute') else 'black'))
    def walk(el,ox=0,oy=0,rotation=0,data=None,ignore_alpha=False,ignore_scale=False,ignore_tint=False):
        nonlocal im
        attrs=dict(el.attrib)
        if attrs.get('name')=='ambient' and not ambient and component in ('hands','hour','minute'):return
        if attrs.get('name')=='digital_time' and component in ('hands','hour','minute','scale','ticks'):return
        if component=='scale' and attrs.get('name')=='interactive_hands':return
        if component=='ticks' and (attrs.get('name')=='interactive_hands' or el.tag=='PartText'):return
        if component in ('hands','hour','minute') and (attrs.get('name')=='interactive' or el.tag=='ComplicationSlot'):return
        if component=='hour' and attrs.get('name')=='minute':return
        if component=='minute' and attrs.get('name') in ('hour','instrument_classic_hour_front'):return
        if ambient:
            for v in el.findall('Variant'):attrs[v.get('target')]=v.get('value')
        alpha=int(attrs.get('alpha',255))
        if alpha==0:return
        if alpha<255 and not ignore_alpha:
            target=im;im=Image.new('RGBA',target.size)
            walk(el,ox,oy,rotation,data,True,ignore_scale,ignore_tint)
            im.putalpha(im.getchannel('A').point(lambda p:round(p*alpha/255)))
            target.alpha_composite(im);im=target;return
        for t in el.findall('Transform'):attrs[t.get('target')]=evaluate(t.get('value'),config,hour,mins,data)
        tag=el.tag
        if tag=='TimeText':
            p=E.Element('PartText',{k:v for k,v in attrs.items() if k not in ('format','hourFormat')})
            text=E.SubElement(p,'Text',align=attrs.get('align','CENTER'))
            import copy
            font=copy.deepcopy(el.find('Font'));font.text=f'{hour:02}:{mins:02}'
            text.append(font);walk(p,ox,oy,rotation,data);return
        if tag=='Group' and not ignore_scale and (float(attrs.get('scaleX',1))!=1 or float(attrs.get('scaleY',1))!=1):
            target=im;im=Image.new('RGBA',target.size)
            walk(el,ox,oy,rotation,data,ignore_alpha,True,ignore_tint)
            sx,sy=float(attrs.get('scaleX',1)),float(attrs.get('scaleY',1))
            px=(ox+float(attrs.get('x',0))+float(attrs['width'])*float(attrs.get('pivotX',.5)))*S
            py=(oy+float(attrs.get('y',0))+float(attrs['height'])*float(attrs.get('pivotY',.5)))*S
            scaled=im.transform(target.size,Image.Transform.AFFINE,(1/sx,0,px*(1-1/sx),0,1/sy,py*(1-1/sy)),resample=Image.Resampling.BICUBIC)
            target.alpha_composite(scaled);im=target;return
        if tag in ('Group','DigitalClock') and attrs.get('tintColor') and not ignore_tint:
            target=im;im=Image.new('RGBA',target.size)
            walk(el,ox,oy,rotation,data,ignore_alpha,ignore_scale,True)
            alpha=im.getchannel('A');im=Image.new('RGBA',im.size,attrs['tintColor']);im.putalpha(alpha)
            target.alpha_composite(im);im=target;return
        if tag=='Condition':
            exprs={e.get('name'):e.text for e in el.findall('Expressions/Expression')}
            selected=el.find('Default')
            for c in el.findall('Compare'):
                if evaluate(exprs[c.get('expression')],config,hour,mins,data):selected=c;break
            if selected is not None:
                for ch in selected:walk(ch,ox,oy,rotation,data)
            return
        if tag=='ComplicationSlot':
            if ambient or not complications:return
            slot=int(attrs['slotId']);kind={1:'SHORT_TEXT',2:'RANGED_VALUE',3:'SHORT_TEXT'}[slot]
            sample={1:{'TEXT':'12°','TITLE':'ПОГОДА'},2:{'TEXT':'76%','RANGED_VALUE_VALUE':76,'RANGED_VALUE_MIN':0,'RANGED_VALUE_MAX':100,'TITLE':'ЗАРЯД'},3:{'TEXT':'Ср, 4','TITLE':'НОЯБРЬ'}}[slot]
            sample['MONOCHROMATIC_IMAGE']={1:'qa_weather',2:'qa_stress',3:'qa_calendar'}[slot]
            walk(el.find(f'Complication[@type="{kind}"]'),ox+float(attrs['x']),oy+float(attrs['y']),rotation,sample);return
        if tag in ('Group','PartDraw','PartText','PartImage','DigitalClock'):
            ox+=float(attrs.get('x',0));oy+=float(attrs.get('y',0))
            if tag=='Group':rotation+=float(attrs.get('angle',0))
        def pt(x,y):
            x=float(x)+ox;y=float(y)+oy
            if rotation:
                a=math.radians(rotation);x,y=216+(x-216)*math.cos(a)-(y-216)*math.sin(a),216+(x-216)*math.sin(a)+(y-216)*math.cos(a)
            return x*S,y*S
        d=ImageDraw.Draw(im)
        if tag=='Line':
            st=el.find('Stroke');a=pt(attrs['startX'],attrs['startY']);b=pt(attrs['endX'],attrs['endY'])
            width=float(st.get('thickness'))*S;color=st.get('color');d.line([a,b],fill=color,width=max(1,round(width)))
            if st.get('cap')=='ROUND':
                for x,y in (a,b):d.ellipse((x-width/2,y-width/2,x+width/2,y+width/2),fill=color)
            return
        if tag=='Ellipse':
            x,y=pt(attrs['x'],attrs['y']);w=float(attrs['width'])*S;h=float(attrs['height'])*S
            d.ellipse((x,y,x+w,y+h),fill=el.find('Fill').get('color'));return
        if tag=='RoundRectangle':
            # One closed contour, transformed as a whole: no separately rasterized end dots.
            x=float(attrs['x']);y=float(attrs['y']);w=float(attrs['width']);h=float(attrs['height']);r=float(attrs['cornerRadiusX'])
            points=[]
            for cx,cy,start in ((x+w-r,y+r,-90),(x+w-r,y+h-r,0),(x+r,y+h-r,90),(x+r,y+r,180)):
                for i in range(13):
                    a=math.radians(start+i*90/12);points.append(pt(cx+r*math.cos(a),cy+r*math.sin(a)))
            fill=el.find('Fill');color=fill.get('color')
            for t in fill.findall('Transform'):color=evaluate(t.get('value'),config,hour,mins,data)
            d.polygon(points,fill=color);return
        if tag=='Arc':
            cx=float(attrs['centerX'])+ox;cy=float(attrs['centerY'])+oy
            radius=float(attrs['width'])/2;st=el.find('Stroke');width=float(st.get('thickness'))
            a=float(attrs['startAngle']);b=float(attrs['endAngle'])
            def p(deg,r):return ((cx+r*math.sin(math.radians(deg)))*S,(cy-r*math.cos(math.radians(deg)))*S)
            n=max(2,math.ceil(abs(b-a)*2));angles=[a+(b-a)*i/n for i in range(n+1)]
            poly=[p(t,radius+width/2) for t in angles]+[p(t,max(0,radius-width/2)) for t in reversed(angles)]
            d.polygon(poly,fill=st.get('color'));return
        if tag in ('PartText','PartImage'):
            layer=Image.new('RGBA',im.size)
            if tag=='PartText':
                font=el.find('Text/Font');fa=dict(font.attrib)
                for t in font.findall('Transform'):fa[t.get('target')]=evaluate(t.get('value'),config,hour,mins,data)
                f=font_file(fa['family'],round(float(fa['size'])*S))
                value=font.text or '';t=font.find('Template')
                if t is not None:value=(t.text or '%s')%evaluate(t.find('Parameter').get('expression'),config,hour,mins,data)
                w=round(float(attrs['width'])*S);h=round(float(attrs['height'])*S)
                # Center the visible ink for the contact sheet; renderer/device metrics may differ.
                patch=Image.new('RGBA',(w,h));pd=ImageDraw.Draw(patch)
                bbox=pd.textbbox((0,0),value,font=f)
                pd.text(((w-bbox[2]-bbox[0])/2,(h-bbox[3]-bbox[1])/2),value,font=f,fill=fa['color'])
                if 'scaleX' in attrs or 'scaleY' in attrs:
                    patch=patch.resize((round(w*float(attrs.get('scaleX',1))),round(h*float(attrs.get('scaleY',1)))),Image.Resampling.LANCZOS)
                if float(attrs.get('angle',0)):patch=patch.rotate(-float(attrs['angle']),resample=Image.Resampling.BICUBIC,expand=True)
                cx=(ox+float(attrs['width'])/2)*S;cy=(oy+float(attrs['height'])/2)*S
                layer.alpha_composite(patch,(round(cx-patch.width/2),round(cy-patch.height/2)))
            else:
                resource=el.find('Image').get('resource')
                if resource.startswith('[COMPLICATION.'):
                    resource=(data or {}).get(resource[14:-1])
                    if not resource:return
                w=float(attrs['width']);h=float(attrs['height']);sx=float(attrs.get('scaleX',1));sy=float(attrs.get('scaleY',1))
                source=sample_icon(resource) if resource.startswith('qa_') else bitmap(resource)
                patch=source.resize((round(w*S*sx),round(h*S*sy)),Image.Resampling.BICUBIC if resource.startswith('classic_scale_') else Image.Resampling.LANCZOS)
                if attrs.get('tintColor'):
                    alpha=patch.getchannel('A');patch=Image.new('RGBA',patch.size,attrs['tintColor']);patch.putalpha(alpha)
                px=ox+w*float(attrs.get('pivotX',.5))*(1-sx);py=oy+h*float(attrs.get('pivotY',.5))*(1-sy)
                layer.alpha_composite(patch,(round(px*S),round(py*S)))
            if rotation:layer=layer.rotate(-rotation,resample=Image.Resampling.BICUBIC,center=(216*S,216*S))
            im.alpha_composite(layer);return
        children=[c for c in el if c.tag not in ('Variant','Transform','UserConfigurations','Metadata')]
        masks=[c for c in children if c.get('renderMode')=='MASK']
        if masks:
            target=im;im=Image.new('RGBA',target.size)
            for ch in children:
                if ch not in masks:walk(ch,ox,oy,rotation,data)
            source=im;im=Image.new('RGBA',target.size)
            for ch in masks:walk(ch,ox,oy,rotation,data)
            source.putalpha(ImageChops.multiply(source.getchannel('A'),im.getchannel('A')))
            target.alpha_composite(source);im=target
        else:
            for ch in children:walk(ch,ox,oy,rotation,data)
    walk(scene() if subtree is None else subtree)
    im=im.resize((output_size,output_size),Image.Resampling.BOX if style in ('instrument','aviator','instrument_classic') and not ambient else Image.Resampling.LANCZOS)
    if not transparent:
        mask=Image.new('L',im.size);ImageDraw.Draw(mask).ellipse((0,0,output_size-1,output_size-1),fill=255);im.putalpha(mask)
    return im

def sheet(panels,path,columns=4,tile=432):
    rows=math.ceil(len(panels)/columns);stride=tile+24
    im=Image.new('RGB',(columns*stride,rows*(stride+26)+45),'#171C1C');d=ImageDraw.Draw(im)
    f=font_file('barlow_regular',18)
    for i,(label,pic) in enumerate(panels):
        x=i%columns*stride+12;y=i//columns*(stride+26)+12
        pic=pic.resize((tile,tile),Image.Resampling.LANCZOS);im.paste(pic,(x,y),pic)
        d.text((x+4,y+tile+5),label,font=f,fill='#D3D9D4')
    d.text((16,im.height-31),'LOCAL XML PREVIEWS / NOT EMULATOR SCREENSHOTS',font=f,fill='#929E98')
    im.save(path,quality=94)

def main():
    from assets import main as assets
    from generate import DIVIDERS
    assets();out=ROOT/'docs/previews';out.mkdir(parents=True,exist_ok=True);dr=RES/'drawable-nodpi'
    defaults={'classic':'white','minimal':'black','sputnik':'ivory','instrument':'black','aviator':'black','instrument_classic':'black'}
    base=[];grid=[];modes={p:[] for p in ('quarter','shifted_back_1_hour')};comparison=[]
    for style in STYLES:
        pic=render(style,defaults[style]);large=render(style,defaults[style],output_size=864);large.save(out/f'{style}_large.png')
        pic.save(dr/f'preview_{style}.png');base.append((style.title(),large))
        for bg in BACKGROUNDS:
            im=render(style,bg);im.save(out/f'{style}_{bg}.png');grid.append((f'{style} / {bg}',im))
        for preset in modes:
            title='Quarter' if preset=='quarter' else 'ShiftedBack1Hour'
            for mode in ('none','lines','labels','color'):
                im=render(style,defaults[style],mode,preset)
                im.save(out/f'{style}_{preset}_{mode}.png')
                modes[preset].append((f'{style.title()} / {title} / {mode}',im))
                if mode in ('lines','color'):comparison.append((f'{style.title()} / {title} / {mode}',im))
    for bg in BACKGROUNDS:render('classic',bg).save(dr/f'preview_{bg}.png')
    render().save(dr/'preview.png');render(ambient=True).save(out/'aod.png')
    for preset in ('quarter','shifted_back_1_hour'):
        render('sputnik','ivory','color',preset,output_size=864).save(out/f'{preset}_color_large.png')
        for comps in (False,True):
            render('sputnik','ivory','color',preset,minute=True,complications=comps).save(out/f'sputnik_{preset}_{"with" if comps else "without"}_complications.png')
    sheet(base[:4],out/'four_styles.jpg',columns=2,tile=640)
    sheet(base[:5],out/'five_styles.jpg',columns=2,tile=540)
    sheet(base,out/'styles_all.jpg',columns=3,tile=432)
    sheet(grid,out/'backgrounds.jpg',columns=3)
    # Main sheet deliberately shows BOTH presets; neither can disappear from review.
    sheet(comparison,out/'contact_sheet.jpg')
    for preset,panels in modes.items():sheet(panels,out/f'contact_sheet_{preset}.jpg')
    for preset in modes:
        title='Quarter' if preset=='quarter' else 'ShiftedBack1Hour'
        sheet([(f'{s.title()} / {title} / Color',render(s,defaults[s],'color',preset)) for s in STYLES],out/f'color_{preset}.jpg',columns=2,tile=540)
    # Same style, background and time in every tile: only dividers change.
    sheet([(f'Sputnik / Ivory / Quarter / {v.title()}',render('sputnik','ivory','lines','quarter',dividers=v)) for v in DIVIDERS],out/'divider_styles.jpg',columns=3)
    sheet([(f'{p} / {v}',render('sputnik','ivory','color',p,dividers=v)) for p in modes for v in DIVIDERS],out/'divider_styles_color.jpg',columns=5)
    sheet([(p,render('sputnik','ivory','color',p)) for p in ('quarter','shifted_back_1_hour')],out/'boundaries.jpg',columns=2)
    hand_previews()

def hand_previews():
    from generate import HAND_STYLES
    from hand_art import make,CORE
    out=ROOT/'docs/previews';out.mkdir(exist_ok=True)
    for kind in HAND_STYLES[1:]:render('classic','black' if kind in ('original_black','original_orange') else 'ivory',hand_style=kind,output_size=216).save(RES/'drawable-nodpi'/f'preview_hand_{kind}.png')
    # Straight vertical artwork at 3x physical watch size, without a dial hiding its shape.
    gallery=Image.new('RGB',(4*288,760),'#DCDDD4');d=ImageDraw.Draw(gallery)
    for i,kind in enumerate(CORE):
        hand=make(kind,'light');x=i*288+72;y=38
        gallery.paste(hand,(x,y),hand)
        f=font_file('barlow_regular',26);d.text((i*288+40,680),kind.title(),font=f,fill='#26312D')
        d.line((i*288+144,548,i*288+144,584),fill='#ADADA3',width=1)
    gallery.save(out/'hands_enlarged.png')
    for bg in BACKGROUNDS:
        panels=[(f'{kind.title()} / {bg}',render('classic',bg,hand_style=kind,hour=10,mins=30,output_size=648)) for kind in CORE]
        sheet(panels,out/f'hands_on_dial_{bg}.jpg',columns=2,tile=540)
    sheet([(f'{kind.title()} / {h:02}:{m:02}',render('classic','ivory',hand_style=kind,hour=h,mins=m)) for kind in CORE for h,m in ((3,0),(10,30),(18,0))],out/'hands_time_checks.jpg',columns=3)
    sheet([(f'{"Instrument Classic" if kind=="bellross_photo" else kind} / Quarter',render('sputnik','black' if kind in ('original_black','original_orange') else 'ivory','color','quarter',hand_style=kind,hour=3,mins=0)) for kind in HAND_STYLES[1:]],out/'all_hand_variants.jpg',columns=4)
    sheet([(f'{s.title()} / {kind}',render(s,'black',hand_style=kind,minute=True,hour=10,mins=30)) for s in ('instrument','aviator') for kind in ('instrument','instrument_white','aviation','aviation_gray')],out/'aviation_variants.jpg',columns=4)
    sheet([(f'{kind} / {h:02}:{m:02}',render('aviator','black',hand_style=kind,minute=True,hour=h,mins=m)) for kind in ('bellross','bellross_needle') for h,m in ((3,0),(10,30),(18,0))],out/'bellross_time_checks.jpg',columns=3,tile=540)
    sheet([(f'{kind} / original geometry',render('classic','black' if kind in ('original_black','original_orange') else 'ivory','color',hand_style=kind,hour=10,mins=30,minute=True)) for kind in HAND_STYLES if kind.startswith(('original_','legacy_'))],out/'original_hands_restored.jpg',columns=4)
    gallery=Image.new('RGB',(900,900),'#171B18')
    for i,(kind,minute) in enumerate((('bellross',False),('bellross',True),('bellross_needle',True))):
        hand=make(kind,'dark',minute)
        gallery.paste(hand,(i*300+150-hand.width//2,35),hand)
        ImageDraw.Draw(gallery).text((i*300+25,840),('Hour','Minute','Thin minute')[i],font=font_file('barlow_regular',26),fill='#E5E3D7')
    gallery.save(out/'bellross_hands_enlarged.png')
    for h,m in ((3,0),(10,30),(18,0)):
        render('aviator','black',minute=True,hour=h,mins=m,output_size=864).save(out/f'aviator_{h:02}{m:02}_large.png')
if __name__=='__main__':main()
