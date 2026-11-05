"""Native WFF v4 generator; development tooling only."""
from pathlib import Path
import math
import xml.etree.ElementTree as E

ROOT=Path(__file__).resolve().parents[1]
RES=ROOT/'watchface/src/main/res'
SIZE=432
C=216
STYLES=('classic','minimal','sputnik','instrument','aviator','instrument_classic')
LEGACY_STYLES=('classic','minimal','sputnik','instrument')
HAND_STYLES=('auto','needle','sword','vintage','instrument','vintage_red','instrument_white','aviation','aviation_gray','legacy_classic','legacy_minimal','legacy_sputnik','legacy_instrument','bellross','bellross_needle','original_white','original_black','original_sputnik','original_orange','instrument_refined','bellross_photo','instrument_classic_clean')
DEFAULT_HANDS=dict(classic='needle',minimal='sword',sputnik='vintage',instrument='instrument_refined',aviator='instrument_refined',instrument_classic='bellross_photo')
REMOVED_HAND_STYLES={'needle','instrument','aviation','aviation_gray','bellross_needle','original_white','original_black','original_orange'}
VISIBLE_HAND_STYLES=tuple(k for k in HAND_STYLES if k not in REMOVED_HAND_STYLES)
HAND_SIZES={'Compact':.92,'Original':1.0,'Large':1.06}
MINUTE_TRACKS=('None','TicksOnly','FiveMinuteLabels','SputnikRing','InstrumentRing')
BACKGROUNDS={'white':'#FAFAF7','ivory':'#E9E2CE','black':'#000000'}
# Ordered morning/day/evening/night, including wraparound past midnight.
PRESETS={'quarter':(6,12,18,24),'shifted_back_1_hour':(5,11,17,23)}
MODES=('none','lines','labels','color')
DIVIDERS=('micro','radial','full','arc','classic')
INK='#222A29'
PAPER='#F0F0E7'
LABEL_RADIUS=149
SLOTS=((104,188),(272,188),(188,264))
SLOT_SIZE=56

def angle(hour,minute=0):return (15*(hour+minute/60-12))%360
def point(a,radius,center=C):
    a=math.radians(a)
    return center+radius*math.sin(a),center-radius*math.cos(a)
def period_index(hour,preset='quarter'):
    return int(((hour-PRESETS[preset][0])%24)//6)
def period(hour,minute=0,preset='quarter'):
    return ('morning','day','evening','night')[period_index(hour+minute/60,preset)]
def palette(style,background):
    if background=='black':
        return ('#202723','#151C20','#292522','#080D11') if style!='instrument' else ('#30281F','#1E2222','#2C211D','#090E12')
    if background=='white':return ('#EBEAD9','#FAFAF7','#C6C5BD','#253230')
    return ('#DDDCBC','#E9E2CE','#B9B3A5','#26332F')
def luminance(color):
    channels=[int(color[i:i+2],16)/255 for i in (1,3,5)]
    r,g,b=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in channels]
    return .2126*r+.7152*g+.0722*b
def contrast(a,b):
    x,y=sorted((luminance(a),luminance(b)))
    return (y+.05)/(x+.05)
def ink_on(color):return INK if contrast(INK,color)>contrast(PAPER,color) else PAPER
def node(parent,tag,**attrs):return E.SubElement(parent,tag,{k:str(v) for k,v in attrs.items()})
def full(parent,tag,**attrs):return node(parent,tag,x=0,y=0,width=SIZE,height=SIZE,**attrs)
def group(parent,name,ambient=None):
    g=full(parent,'Group',name=name,pivotX=.5,pivotY=.5)
    if ambient is not None:
        if ambient:g.set('alpha','0')
        node(g,'Variant',mode='AMBIENT',target='alpha',value=255 if ambient else 0)
    return g
def condition(parent,expr):
    c=node(parent,'Condition');es=node(c,'Expressions')
    node(es,'Expression',name='enabled').text=expr
    return node(c,'Compare',expression='enabled')
def selection(**values):return ' && '.join(f'[CONFIGURATION.{k}] == "{v}"' for k,v in values.items())
def draw(parent,**attrs):return full(parent,'PartDraw',**attrs)
def line(parent,a,b,color,thickness=1,cap='BUTT'):
    el=node(parent,'Line',startX=round(a[0],4),startY=round(a[1],4),endX=round(b[0],4),endY=round(b[1],4))
    node(el,'Stroke',color=color,thickness=thickness,cap=cap)
    return el
def ellipse(parent,x,y,w,h,color):node(node(parent,'Ellipse',x=x,y=y,width=w,height=h),'Fill',color=color)
def arc(parent,cx,cy,diameter,start,end,color,thickness):
    el=node(parent,'Arc',centerX=cx,centerY=cy,width=diameter,height=diameter,startAngle=start,endAngle=end)
    node(el,'Stroke',color=color,thickness=thickness,cap='BUTT')
    return el
def wedge(parent,start,end,color):
    return arc(parent,C,C,C,angle(start),angle(start)+(end-start)*15,color,C)
def text(parent,cx,cy,value,color,size,family='roboto_condensed',w=44,h=40,name=None,rotation=0):
    attrs={'x':round(cx-w/2),'y':round(cy-h/2),'width':w,'height':h,'pivotX':.5,'pivotY':.5}
    if name:attrs['name']=name
    if rotation:attrs['angle']=rotation
    p=node(parent,'PartText',**attrs)
    t=node(p,'Text',align='CENTER',ellipsis='TRUE',maxLines=1)
    node(t,'Font',family=family,size=size,color=color).text=value
    return p
def template(parent,cx,cy,w,h,expr,color,size,fmt='%s'):
    p=text(parent,cx,cy,None,color,size,w=w,h=h)
    t=node(p.find('Text/Font'),'Template');t.text=fmt;node(t,'Parameter',expression=expr)

def number_specs(style):
    if style=='instrument_classic':return []  # custom vector glyphs, never font text
    if style=='aviator':return [(h,164,34,'michroma') for h in (6,12,18,24)]
    if style=='classic':return [(h,179,30,'abel') for h in range(2,25,2)]
    if style=='minimal':return [(h,181,24,'barlow_regular') for h in range(1,25)]
    if style=='sputnik':return [(h,180,25,'roboto_condensed') for h in range(1,25)]
    return [(h,176,30 if h in (6,12,18,24) else 24,'barlow_semibold') for h in range(2,25,2)]
def scale(parent,style,fg,ambient=False):
    if ambient:return scale_art(parent,style,fg,True)
    for compact in (False,True):
        p=condition(parent,'[CONFIGURATION.MinuteTrackStyle] '+('!=' if compact else '==')+' "None"')
        scale_art(p,style,fg,compact=compact)

def instrument_tick_specs():
    # One source for both instrument faces: 24 hours, three quarter-hour marks each.
    for i in range(96):
        length,width=(15,3) if i%24==0 else ((12,2.3) if i%4==0 else ((6.5,1.1) if i%2==0 else (4.5,.9)))
        yield i*3.75,207-length,207,width

def solid_tick(parent,a,inner,outer,width,color):
    g=group(parent,'tick_'+str(a));g.set('angle',str(a))
    shape=node(draw(g),'RoundRectangle',x=C-width/2,y=C-outer,width=width,height=outer-inner,cornerRadiusX=width/2,cornerRadiusY=width/2)
    node(shape,'Fill',color=color)

def scale_art(parent,style,fg,ambient=False,compact=False):
    factor=.84 if compact else 1
    if style=='instrument_classic' and not ambient:
        from classic_scale import resource
        p=full(parent,'PartImage',name='instrument_classic_custom_scale',pivotX=.5,pivotY=.5,scaleX=factor,scaleY=factor)
        node(p,'Image',resource=resource(fg));return
    if style in ('instrument','aviator') and not ambient:
        d=group(parent,'hour_and_subhour_ticks')
        for a,inner,outer,width in instrument_tick_specs():solid_tick(d,a,inner*factor,outer*factor,width*factor,fg)
    else:
        legacy_scale_ticks(parent,style,fg,ambient,factor)
    specs=[(h,180,25,'barlow_regular') for h in range(2,25,2)] if ambient else number_specs(style)
    for h,r,size,font in specs:
        x,y=point(angle(h),r*factor)
        p=text(parent,x,y,str(h),fg,size*factor,font,w=128 if style=='aviator' and not ambient else 44,h=70 if style=='aviator' and not ambient else 40,name=f'hour_number_{h}')
        if style=='aviator' and not ambient:p.set('scaleX','.78')

def legacy_scale_ticks(parent,style,fg,ambient,factor):
    d=draw(parent,name='hour_and_subhour_ticks')
    count=24 if ambient or style=='minimal' else (144 if style=='sputnik' else (60 if style=='aviator' else 120))
    for i in range(count):
        a=i*360/count;major=ambient or style=='minimal' or i%(5 if style=='aviator' else count//24)==0
        if ambient:length,width=8,1.3
        elif style=='classic':length,width=(11,1.4) if major else (4.5,.65)
        elif style=='minimal':length,width=(10,1.5)
        elif style=='sputnik':length,width=(13,1.6) if major else ((7,1) if i%3==0 else (4,.7))
        elif style=='aviator':length,width=(8,4.5) if i%15==0 else ((21,5.5) if major else (7,1.1))
        else:length,width=(16,3) if major and i%10==0 else ((9,1.8) if major else (4,.75))
        line(d,point(a,(207-length)*factor),point(a,207*factor),fg,width*factor,'BUTT')
    if style=='sputnik' and not ambient:arc(d,C,C,394*factor,0,360,fg,.55)

def minute_track_art(parent,kind,fg):
    d=draw(parent,name='minute_track_ticks')
    for i in range(60):
        a=i*6;major=i%5==0
        inner=(203 if major else 207) if kind=='TicksOnly' else (205 if major else 208)
        line(d,point(a,inner),point(a,211),fg,1 if major else .65)
    if kind=='SputnikRing':
        arc(d,C,C,410,0,360,fg,.5);arc(d,C,C,423,0,360,fg,.5)
    elif kind=='InstrumentRing':arc(d,C,C,374,0,360,fg,.45)
    if kind!='TicksOnly':
        for minute in range(5,61,5):
            x,y=point(minute*6,196)
            text(parent,x,y,str(minute),fg,11,'roboto_condensed',w=24,h=16,name=f'minute_label_{minute}')

def minute_tracks(parent,style,background):
    for kind in MINUTE_TRACKS[1:]:
        g=group(condition(parent,selection(MinuteTrackStyle=kind)),'minute_track_'+kind)
        p=condition(g,'[CONFIGURATION.sectors] != "color"')
        ink=('#F29883' if background=='black' else '#8C332A') if kind=='SputnikRing' else ink_on(BACKGROUNDS[background])
        minute_track_art(p,kind,ink)
        for preset in PRESETS:
            p=condition(g,selection(sectors='color',boundaries=preset))
            for ink in dict.fromkeys(ink_on(c) for c in palette(style,background)):
                m=group(p,'minute_track_contrast');minute_track_art(m,kind,ink)
                mask=draw(m,renderMode='MASK')
                for start,color in zip(PRESETS[preset],palette(style,background)):
                    if ink_on(color)==ink:wedge(mask,start,start+6,'#FFFFFF')
def colored_scale(parent,style,background,preset):
    colors=palette(style,background);bounds=PRESETS[preset]
    # Exact clipping at boundaries, including glyphs that straddle two sectors.
    for ink in dict.fromkeys(ink_on(c) for c in colors):
        g=group(parent,'scale_on_'+('light' if ink==INK else 'dark'))
        scale(g,style,ink)
        m=draw(g,renderMode='MASK',name='sector_contrast_mask')
        for start,color in zip(bounds,colors):
            if ink_on(color)==ink:wedge(m,start,start+6,'#FFFFFF')
def divider_geometry(parent,preset,divider,fg):
    opacity={'micro':150,'radial':110,'full':75,'arc':160,'classic':150}[divider]
    d=draw(parent,name='divider_'+divider,alpha=opacity)
    for h in PRESETS[preset]:
        a=angle(h)
        if divider=='arc':
            # Each arc follows a complete six-hour period, with a 3-degree inset at both ends.
            arc(d,C,C,244,a+3,a+87,fg,1.2)
        else:
            inner,outer,width={'micro':(138,157,1.1),'radial':(42,158,.8),'full':(0,158,.65),'classic':(119,157,.8)}[divider]
            line(d,point(a,inner),point(a,outer),fg,width)
            if divider=='classic':arc(d,C,C,238,a-1.6,a+1.6,fg,.8)
def dividers(parent,style,background,preset,mode):
    for divider in DIVIDERS:
        g=group(condition(parent,selection(dividers=divider)),f'period_dividers_{divider}')
        if mode!='color':divider_geometry(g,preset,divider,ink_on(BACKGROUNDS[background]))
        else:
            colors=palette(style,background)
            for ink in dict.fromkeys(ink_on(c) for c in colors):
                clipped=group(g,'divider_contrast_'+('light' if ink==INK else 'dark'))
                divider_geometry(clipped,preset,divider,ink)
                mask=draw(clipped,renderMode='MASK',name='divider_contrast_mask')
                for start,color in zip(PRESETS[preset],colors):
                    if ink_on(color)==ink:wedge(mask,start,start+6,'#FFFFFF')
def sectors(parent,style,background,preset,mode):
    colors=palette(style,background);bounds=PRESETS[preset]
    if mode=='color':
        d=draw(parent,name='sector_fills')
        for start,color in zip(bounds,colors):wedge(d,start,start+6,color)
    if mode!='none':dividers(parent,style,background,preset,mode)
    if mode in ('labels','color'):
        for start,label,color in zip(bounds,('УТРО','ДЕНЬ','ВЕЧЕР','НОЧЬ'),colors):
            a=angle(start+3);x,y=point(a,LABEL_RADIUS)
            rotation=a if a<=90 or a>=270 else a-180
            fg=ink_on(color if mode=='color' else BACKGROUNDS[background])
            if style=='instrument_classic':
                for compact,r in ((False,128),(True,116)):
                    x,y=point(a,r)
                    p=condition(parent,'[CONFIGURATION.MinuteTrackStyle] '+('!=' if compact else '==')+' "None"')
                    text(p,x,y,label,fg,16,w=54,h=20,name='period_label_'+label,rotation=rotation)
            else:text(parent,x,y,label,fg,16,w=54,h=20,name='period_label_'+label,rotation=rotation)
def hands(parent,style,background,ambient=False):
    tone='dark' if background=='black' else 'light'
    g=group(parent,'hour_aod' if ambient else 'hour')
    node(g,'Transform',target='angle',value='15 * ([HOUR_0_23] + [MINUTE] / 60.0 - 12)')
    if ambient:
        line(draw(g),(C,C+16),(C,79),'#B9C0BA',1.8,'ROUND');return
    def artwork(parent,kind,minute=False):
        if kind.startswith('original_'):
            from original_hands import artwork as original_art
            original_art(parent,kind[9:],minute)
            return
        if kind in ('bellross_photo','instrument_classic_clean'):
            from instrument_classic import rectangle
            part='minute' if minute else 'hour'
            prefix='instrument_classic' if kind=='bellross_photo' else 'instrument_classic_clean'
            rect=rectangle(part);resource=f'{prefix}_{part}_{background}'
        elif kind.startswith('legacy_'):
            rect=(208,34,16,204) if minute else (200,72,32,176)
            resource=f'{"minute" if minute else "hand"}_{kind[7:]}_{tone}'
        else:
            rect=(208,26,16,216) if minute else (192,40,48,208)
            if minute and kind.startswith('bellross'):rect=(200,26,32,260)
            resource=f'precision_{"minute" if minute else "hour"}_{kind}_{tone}'
        x,y,w,h=rect
        if kind in ('bellross_photo','instrument_classic_clean'):
            for size,factor in HAND_SIZES.items():
                p=condition(parent,selection(HandSize=size))
                pi=node(p,'PartImage',x=x,y=y,width=w,height=h,pivotX=(C-x)/w,pivotY=(C-y)/h,name='selected_minute_art' if minute else 'selected_hour_art',scaleX=factor,scaleY=factor)
                node(pi,'Image',resource=resource)
            return
        if kind=='instrument_refined' and not minute:
            for compact in (False,True):
                p=condition(parent,'[CONFIGURATION.MinuteTrackStyle] '+('!=' if compact else '==')+' "None"')
                pi=node(p,'PartImage',x=x,y=y,width=w,height=h,pivotX=(C-x)/w,pivotY=(C-y)/h,name='selected_hour_art',scaleX=.84 if compact else 1,scaleY=.84 if compact else 1)
                node(pi,'Image',resource=resource)
            return
        pi=node(parent,'PartImage',x=x,y=y,width=w,height=h,pivotX=(C-x)/w,pivotY=(C-y)/h,name='selected_minute_art' if minute else 'selected_hour_art')
        # The added large-numeral face follows the shorter mechanical hour-hand proportions.
        if style=='aviator' and not kind.startswith(('bellross','instrument_refined')):pi.set('scaleY','.70' if minute else '.75')
        node(pi,'Image',resource=resource)
    def options(parent,minute=False,classic_only=False):
        for kind in HAND_STYLES[1:]:
            if not minute and (kind in ('bellross_photo','instrument_classic_clean'))!=classic_only:continue
            expr=selection(HandStyle=kind)
            if kind==DEFAULT_HANDS[style]:expr+=' || '+selection(HandStyle='auto')
            artwork(condition(parent,expr),kind,minute)
    options(g)
    g=group(condition(parent,selection(minute='TRUE')),'minute')
    node(g,'Transform',target='angle',value='[MINUTE] * 6');options(g,True)
    front=group(parent,'instrument_classic_hour_front')
    node(front,'Transform',target='angle',value='15 * ([HOUR_0_23] + [MINUTE] / 60.0 - 12)')
    options(front,classic_only=True)
    cap_expr=selection(HandStyle='instrument_refined')
    if DEFAULT_HANDS[style]=='instrument_refined':cap_expr+=' || '+selection(HandStyle='auto')
    cap=condition(parent,cap_expr)
    ellipse(draw(cap,name='instrument_refined_hub'),C-4.2,C-4.2,8.4,8.4,'#9DA395' if tone=='dark' else '#515C53')
    for kind,prefix in (('bellross_photo','instrument_classic'),('instrument_classic_clean','instrument_classic_clean')):
        cap_expr=selection(HandStyle=kind)
        if DEFAULT_HANDS[style]==kind:cap_expr+=' || '+selection(HandStyle='auto')
        cap=condition(parent,cap_expr)
        for size,factor in HAND_SIZES.items():
            p=node(condition(cap,selection(HandSize=size)),'PartImage',x=202,y=202,width=28,height=28,pivotX=.5,pivotY=.5,name='instrument_classic_hub',scaleX=factor,scaleY=factor)
            node(p,'Image',resource=f'{prefix}_hub_{background}')
def complication(parent,slot,x,y):
    s=node(parent,'ComplicationSlot',slotId=slot,displayName=f'slot_{slot}',x=x,y=y,width=SLOT_SIZE,height=SLOT_SIZE,
        supportedTypes='SHORT_TEXT MONOCHROMATIC_IMAGE SMALL_IMAGE RANGED_VALUE EMPTY',isCustomizable='TRUE')
    node(s,'Variant',mode='AMBIENT',target='alpha',value=0)
    node(s,'BoundingOval',x=0,y=0,width=SLOT_SIZE,height=SLOT_SIZE)
    node(s,'DefaultProviderPolicy',defaultSystemProvider='EMPTY',defaultSystemProviderType='EMPTY')
    node(s,'Complication',type='EMPTY')
    for kind in ('SHORT_TEXT','MONOCHROMATIC_IMAGE','SMALL_IMAGE','RANGED_VALUE'):
        c=node(s,'Complication',type=kind)
        for background,bg in BACKGROUNDS.items():
            fg=ink_on(bg);p=condition(c,selection(background=background))
            g=node(p,'Group',name=f'slot{slot}_{kind}_{background}',x=0,y=0,width=56,height=56)
            d=node(g,'PartDraw',x=0,y=0,width=56,height=56);ellipse(d,0,0,56,56,bg)
            if kind in ('MONOCHROMATIC_IMAGE','SMALL_IMAGE'):
                pi=node(g,'PartImage',x=10,y=10,width=36,height=36)
                if kind=='MONOCHROMATIC_IMAGE':pi.set('tintColor',fg)
                node(pi,'Image',resource=f'[COMPLICATION.{kind}]')
            elif kind=='SHORT_TEXT':
                template(g,28,23,50,25,'[COMPLICATION.TEXT]',fg,20)
                template(g,28,42,46,15,'[COMPLICATION.TITLE]',fg,12)
            else:
                arc(d,28,28,51,210,510,fg,.45)
                a=arc(d,28,28,51,210,210,fg,1.7)
                node(a,'Transform',target='endAngle',value='210 + 300 * clamp(([COMPLICATION.RANGED_VALUE_VALUE] - [COMPLICATION.RANGED_VALUE_MIN]) / clamp([COMPLICATION.RANGED_VALUE_MAX] - [COMPLICATION.RANGED_VALUE_MIN], 0.001, 1000000000), 0, 1)')
                cond=node(g,'Condition');es=node(cond,'Expressions')
                node(es,'Expression',name='has_text').text='textLength([COMPLICATION.TEXT]) > 0'
                template(node(cond,'Compare',expression='has_text'),28,25,46,25,'[COMPLICATION.TEXT]',fg,18)
                template(node(cond,'Default'),28,25,46,25,'[COMPLICATION.RANGED_VALUE_VALUE]',fg,18,'%.0f')
                template(g,28,43,42,14,'[COMPLICATION.TITLE]',fg,11)
def generate():
    w=E.Element('WatchFace',width=str(SIZE),height=str(SIZE),clipShape='CIRCLE')
    node(w,'Metadata',key='PREVIEW_TIME',value='10:08:00');node(w,'Metadata',key='CLOCK_TYPE',value='ANALOG')
    uc=node(w,'UserConfigurations')
    strings={'app_name':'Podolskii24','style':'Стиль','background':'Фон','sectors':'Периоды суток','boundaries':'Границы периодов','dividers':'Стиль разделителей суток','HandStyle':'Стиль стрелок','minute':'Минутная стрелка',
        'classic':'Classic — классический','minimal':'Minimal — минимализм','sputnik':'Sputnik — винтажный','instrument':'Instrument — приборный',
        'aviator':'Aviator — крупная авиационная шкала','auto':'По стилю циферблата',
        'needle':'Needle — прецизионная игла','sword':'Sword — гранёная сталь','vintage':'Vintage — белая вставка','vintage_red':'Vintage Red — красная вставка',
        'hand_instrument':'Instrument — серая вставка','instrument_white':'Instrument White — белая вставка','aviation':'Aviation — оранжевая лопатка','aviation_gray':'Aviation Grey — серая вставка',
        'legacy_classic':'Прежняя Classic','legacy_minimal':'Прежняя Minimal','legacy_sputnik':'Прежняя Sputnik','legacy_instrument':'Прежняя Instrument',
        'white':'White — белый','ivory':'Ivory — слоновая кость','black':'Black — чёрный',
        'none':'None — без секторов','lines':'Lines — разделители','labels':'Labels — разделители и подписи','color':'Color — цветные сектора',
        'quarter':'Quarter — 00 / 06 / 12 / 18','shifted_back_1_hour':'На час назад — 23 / 05 / 11 / 17',
        'micro':'Micro — короткие засечки','radial':'Radial — радиальные линии','full':'Full — линии от центра','arc':'Arc — дуги периодов','classic_dividers':'Classic — винтажные разделители',
        'slot_1':'Дополнение №1 — слева','slot_2':'Дополнение №2 — справа','slot_3':'Дополнение №3 — снизу'}
    strings.update(bellross='Bell & Ross — по референсу',bellross_needle='Bell & Ross — тонкая минутная',original_white='Original 1.0 — White',original_black='Original 1.0 — Black',original_sputnik='Original 1.0 — Sputnik',original_orange='Original 1.0 — Orange')
    strings.update(MinuteTrackStyle='Минутная дорожка',minute_track_None='None — без минутной шкалы',TicksOnly='TicksOnly — только деления',FiveMinuteLabels='FiveMinuteLabels — подписи через 5 минут',SputnikRing='SputnikRing — винтажный пояс',InstrumentRing='InstrumentRing — технический пояс',instrument_refined='Instrument Refined — цельный приборный комплект')
    strings['bellross_photo']='Instrument Classic — векторные стрелки'
    strings['instrument_classic_clean']='Instrument Classic — без обводки'
    # The system style editor formats these resource strings with String.format.
    # Escape literal percentages; formatted="false" does not protect that call.
    strings.update(instrument_classic='Instrument Classic — цифры и индексы по референсу',HandSize='Размер стрелок',Compact='Compact — 92%%',Original='Original — исходные пропорции',Large='Large — 106%%')
    strings['style']='Дизайн шкалы'
    for id,default,opts in [('style','classic',STYLES),('background','white',BACKGROUNDS),('sectors','none',MODES),('boundaries','quarter',PRESETS),('dividers','micro',DIVIDERS),('HandStyle','auto',HAND_STYLES),('MinuteTrackStyle','None',MINUTE_TRACKS),('HandSize','Original',HAND_SIZES)]:
        cfg=node(uc,'ListConfiguration',id=id,displayName=id,screenReaderText=id,defaultValue=default)
        for opt in opts:
            label='classic_dividers' if id=='dividers' and opt=='classic' else opt
            if id=='HandStyle' and opt=='instrument':label='hand_instrument'
            if id=='MinuteTrackStyle' and opt=='None':label='minute_track_None'
            attrs={'id':opt,'displayName':label,'screenReaderText':label}
            if id in ('style','background'):attrs['icon']='preview_'+opt
            if id=='HandStyle' and opt!='auto':attrs['icon']='preview_hand_'+opt
            node(cfg,'ListOption',**attrs)
    node(uc,'BooleanConfiguration',id='minute',displayName='minute',screenReaderText='minute',defaultValue='FALSE')
    sc=node(w,'Scene',backgroundColor='#000000');active=group(sc,'interactive',False)
    for style in STYLES:
        for background,bg in BACKGROUNDS.items():
            g=group(condition(active,selection(style=style,background=background)),f'dial_{style}_{background}')
            ellipse(draw(g),0,0,SIZE,SIZE,bg)
            fg=('#E47D38' if background=='black' else '#A34B24') if style=='instrument_classic' else (('#F08A35' if background=='black' else '#A34B16') if style=='aviator' else ink_on(bg))
            scale(group(condition(g,'[CONFIGURATION.sectors] != "color"'),'regular_scale'),style,fg)
            for preset in PRESETS:
                for mode in ('lines','labels','color'):
                    sg=group(condition(g,selection(boundaries=preset,sectors=mode)),f'{style}_{background}_{preset}_{mode}')
                    sectors(sg,style,background,preset,mode)
                    if mode=='color':colored_scale(sg,style,background,preset)
            minute_tracks(g,style,background)
    for slot,(x,y) in enumerate(SLOTS,1):complication(sc,slot,x,y)
    hg=group(sc,'interactive_hands',False)
    for style in STYLES:
        for background in BACKGROUNDS:
            hands(group(condition(hg,selection(style=style,background=background)),f'hands_{style}_{background}'),style,background)
    aod=group(sc,'ambient',True);scale(aod,'minimal','#7D8781',True);hands(aod,'minimal','black',True)
    ellipse(draw(aod),C-2.5,C-2.5,5,5,'#B9C0BA')
    root=E.Element('resources')
    for key,value in strings.items():node(root,'string',name=key).text=value
    from static_geometry import optimize
    optimize(w)
    from minute_palette import apply as apply_minute_palette
    apply_minute_palette(w, root)
    for path,el in ((RES/'raw/watchface.xml',w),(RES/'values/strings.xml',root)):
        path.parent.mkdir(parents=True,exist_ok=True)
        # WFF source has a 10 MB limit. Indentation alone added over 5 MB
        # to 5.0; keep the native scene compact without changing its tree.
        if path.name!='watchface.xml':E.indent(el,space='  ')
        else:
            # Keep short lines for Android XML tooling, without deep indentation.
            for item in el.iter():item.tail='\n'
        E.ElementTree(el).write(path,encoding='utf-8',xml_declaration=True)
        if path.name=='watchface.xml':
            assert path.stat().st_size<=800_000, 'Optimized WFF source budget exceeded'
            assert sum(1 for _ in w.iter())<=8000, 'WFF object budget exceeded'
if __name__=='__main__':generate()
