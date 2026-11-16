"""Small native controls; no new bitmap variants or renderer services."""
import xml.etree.ElementTree as E
import copy
import re

LISTS = {
    'DialTone': ('original', ('original','charcoal','navy','forest','brown','amber_dial','mono_dial')),
    'HandColor': ('adaptive', ('adaptive','original','white','black','orange','green','br_orange','br_amber','br_mono')),
    'ScaleInset': ('wide', ('original','wide')),
    'MinuteInset': ('wide', ('wide','inset')),
    'ComplicationSize': ('normal', ('compact','normal','large','huge','compact_wide','normal_wide','large_wide','huge_wide')),
    'DigitalSize': ('n_plain', ('compact','normal','large')+tuple(f'{size}_{mode}' for size in ('c','n','l') for mode in ('plain','outline','frame','box'))),
    'Layout': ('bottom', ('bottom','top','trio','br_round','br_square','br_round_belorus','br_round_podolskii','br_square_belorus','br_square_podolskii')),
}
LABELS = {
    'adaptive':'Авто — тёплые тёмные / светлые',
    'br_round_belorus':'Два круга / круглая дата / BelOrus', 'br_round_podolskii':'Два круга / круглая дата / Podolskii',
    'br_square_belorus':'Два круга / окно даты / BelOrus', 'br_square_podolskii':'Два круга / окно даты / Podolskii',
    'brown':'Тёплый графит / коричневый', 'amber_dial':'Bell & Ross — янтарная шкала', 'mono_dial':'Bell & Ross — белая шкала',
    'br_orange':'Bell & Ross — чёрный / яркий оранжевый', 'br_amber':'Bell & Ross — чёрный / янтарный', 'br_mono':'Bell & Ross — чёрный / белый',
    'br_round':'Два крупных круга и круглая дата', 'br_square':'Два крупных круга и прямоугольная дата',
    'Layout':'Компоновка и надпись', 'bottom':'Время снизу — три дополнения', 'top':'Время сверху — три дополнения',
    'AodMinute':'Минутная стрелка в AOD', 'Seconds':'Секундная стрелка',
    'DialTone':'Оттенок фона', 'HandColor':'Цвет стрелок',
    'ScaleInset':'Отступ шкалы Instrument Classic', 'MinuteInset':'Отступ минутной дорожки',
    'ComplicationSize':'Размер дополнений', 'DigitalSize':'Размер цифрового времени',
    'original':'Исходный', 'charcoal':'Графит Bell & Ross', 'navy':'Синий',
    'forest':'Хвойный', 'white':'Белый / тёмный контур', 'black':'Тёмный / светлый контур',
    'orange':'Оранжевый', 'green':'Зелёный', 'wide':'Шире', 'inset':'С отступом',
    'compact':'Компактный', 'normal':'Средний', 'large':'Крупный',
}

LABELS.update({'DigitalSize':'Размер и оформление времени','ComplicationSize':'Размер и расстояние дополнений',
 'trio':'Три равных круга — время сверху или выключено',
 'huge':'Очень крупные','compact_wide':'Малые — дальше от центра','normal_wide':'Средние — дальше от центра',
 'large_wide':'Крупные — дальше от центра','huge_wide':'Очень крупные — дальше от центра'})
for code,size in (('c','Малое'),('n','Среднее'),('l','Крупное')):
    for mode,name in (('plain','без оформления'),('outline','контур текста'),('frame','рамка без заливки'),('box','заливка и рамка')):
        LABELS[f'{code}_{mode}']=f'{size} — {name}'

def controls(root, strings):
    from generate import node
    uc=root.find('UserConfigurations')
    for key,(default,options) in LISTS.items():
        cfg=node(uc,'ListConfiguration',id=key,displayName='p_'+key,screenReaderText='p_'+key,defaultValue=default)
        for option in options:
            node(cfg,'ListOption',id=option,displayName='p_'+option,screenReaderText='p_'+option)
    for key in ('AodMinute','Seconds'):
        node(uc,'BooleanConfiguration',id=key,displayName='p_'+key,screenReaderText='p_'+key,defaultValue='FALSE')
    for key,value in LABELS.items():node(strings,'string',name='p_'+key).text=value

def apply(root):
    from generate import node,condition,group,draw,line,ellipse
    scene=root.find('Scene');active=scene.find('Group[@name="interactive"]')
    from design_palette import ACCENT
    for dial in active.findall('.//Group'):
        if not dial.get('name','').startswith('dial_aviator_'):continue
        for regular in dial.findall('.//Group[@name="regular_scale"]'):
            node(regular,'Transform',target='tintColor',value='[CONFIGURATION.background] != "black" ? #222A29 : [CONFIGURATION.HandColor] == "white" ? #F0F0E7 : '+ACCENT)
    # Keep the three original luminance families so existing contrast logic stays
    # valid. New tones only change the base, never the independently colored sectors.
    backgrounds=active.find('Group[@name="shared_backgrounds"]')
    dark='[CONFIGURATION.background] == "black"'
    for paint in backgrounds.findall('Condition/Compare/PartDraw'):
        base=paint.find('Ellipse/Fill').get('color')
        expr=''.join(f'[CONFIGURATION.DialTone] == "{key}" ? {color} : ' for key,color in {
            'charcoal':'#303128' if base=='#000000' else '#E6E4D9',
            'navy':'#142331' if base=='#000000' else '#E2EBEE',
            'forest':'#182B22' if base=='#000000' else '#E3EADD',
            'brown':'#35302B' if base=='#000000' else '#E9DFCF',
            'amber_dial':'#101212' if base=='#000000' else '#ECE8DB',
            'mono_dial':'#101212' if base=='#000000' else '#F0F0E9',
        }.items())+base
        node(paint,'Transform',target='tintColor',value=expr)
    hands=scene.find('Group[@name="interactive_hands"]')
    # Share the common/Aviator trees: their only difference is the original
    # vertical scale of selected sprites. Preserve that difference as transforms.
    for background in ('white','ivory','black'):
        a=hands.find(f'Condition/Compare/Group[@name="hands_shared_common_{background}"]')
        b=hands.find(f'Condition/Compare/Group[@name="hands_shared_aviator_{background}"]')
        ac=next(c for c in hands if a in list(c.iter()))
        bc=next(c for c in hands if b in list(c.iter()))
        for x,y in zip(list(a.iter()),list(b.iter())):
            if x is a:continue
            assert x.tag==y.tag and x.text==y.text
            differences={key for key in set(x.attrib)|set(y.attrib) if x.get(key)!=y.get(key)}
            assert differences <= {'scaleY'}, (x.attrib,y.attrib)
            if differences:
                node(x,'Transform',target='scaleY',value=f'[CONFIGURATION.style] == "aviator" ? {y.get("scaleY")} : {x.get("scaleY","1")}')
        ac.find('Expressions/Expression').text=f'[CONFIGURATION.background] == "{background}"'
        hands.remove(bc)
    for minute in hands.findall('.//Group[@name="minute"]'):
        minute.find('Variant[@mode="AMBIENT"][@target="alpha"]').set('value','[CONFIGURATION.AodMinute] == "TRUE" ? 255 : 0')
    # Independent active/AOD switches, without duplicating minute artwork.
    for parent in list(hands.iter()):
        for child in list(parent):
            if child.tag!='Condition':continue
            expression=child.find('Expressions/Expression')
            if expression is None or expression.text!='[CONFIGURATION.minute] == "TRUE"':continue
            wrapper=E.Element('Group',name='minute_visibility',x='0',y='0',width='432',height='432')
            node(wrapper,'Transform',target='alpha',value='[CONFIGURATION.minute] == "TRUE" ? 255 : 0')
            node(wrapper,'Variant',mode='AMBIENT',target='alpha',value='[CONFIGURATION.AodMinute] == "TRUE" ? 255 : 0')
            wrapper.extend(list(child.find('Compare')))
            index=list(parent).index(child);parent.remove(child);parent.insert(index,wrapper)
    payload=list(hands.findall('Condition'))
    original=group(condition(hands,'[CONFIGURATION.HandColor] == "original" || [CONFIGURATION.HandColor] == "br_orange" || [CONFIGURATION.HandColor] == "br_amber" || [CONFIGURATION.HandColor] == "br_mono"'),'original_hands')
    flat=group(condition(hands,'[CONFIGURATION.HandColor] != "original" && [CONFIGURATION.HandColor] != "br_orange" && [CONFIGURATION.HandColor] != "br_amber" && [CONFIGURATION.HandColor] != "br_mono"'),'flat_hands')
    for item in payload:
        hands.remove(item);original.append(item)
    # A flat palette has no background-specific source colors. One silhouette
    # tree serves all three backgrounds, instead of three copies of the same set.
    flat.append(copy.deepcopy(payload[0].find('Compare/Group')))
    flat_palettes(flat)
    # One shared seconds layer, outside the scaled hand tree. Its time source
    # exists only in the optional branch and it is unconditionally absent in AOD.
    seconds=group(condition(scene,'[CONFIGURATION.Seconds] == "TRUE"'),'seconds')
    node(seconds,'Variant',mode='AMBIENT',target='alpha',value=0)
    node(seconds,'Transform',target='angle',value='[SECOND] * 6')
    d=draw(seconds)
    line(d,(216,40),(216,235),'#E3654A',1.1,'ROUND')
    ellipse(d,213.2,213.2,5.6,5.6,'#E3654A')
    # Scale around the true dial center, retaining the existing compact profile
    # when an outer minutes ring is selected.
    for part in active.findall('.//PartImage[@name="instrument_classic_custom_scale"]'):
        for axis in ('scaleX','scaleY'):
            base=part.get(axis,'1')
            node(part,'Transform',target=axis,value=f'[CONFIGURATION.ScaleInset] == "wide" ? {float(base)*1.075:.6f} : {base}')
    track=active.find('Group[@name="shared_minute_tracks"]')
    for axis in ('scaleX','scaleY'):
        node(track,'Transform',target=axis,value='[CONFIGURATION.MinuteInset] == "inset" ? 0.965 : 1.0')
    for slot in scene.findall('ComplicationSlot'):
        if slot.get('slotId')=='1':slot.set('x','116');slot.set('y','168')
        if slot.get('slotId')=='2':slot.set('x','220');slot.set('y','168')
        if slot.get('slotId')=='3':
            slot.set('y','220')
        slot.find('BoundingOval').attrib.update(x='4',y='4',width='88',height='88')
        if slot.get('slotId')=='3':
            slot.find('BoundingOval').attrib.update(y='4',height='92')
        for g in slot.findall('.//Group'):
            if not g.get('name','').startswith('slot'):continue
            if slot.get('slotId')=='3':
                node(g,'Transform',target='y',value='[CONFIGURATION.Layout] == "top" ? 30 : [CONFIGURATION.style] == "instrument_classic" ? 16 : 34')
            else:
                offset=10 if slot.get('slotId')=='1' else 30
                node(g,'Transform',target='x',value=f'[CONFIGURATION.style] == "instrument_classic" ? 20 : {offset}')
            for axis in ('scaleX','scaleY'):
                huge='subText([CONFIGURATION.ComplicationSize], 0, 1) == "h"'
                prefix=f'[CONFIGURATION.Layout] == "bottom" && [CONFIGURATION.MinuteTrackStyle] != "None" ? 0.857142857 : {huge} && [CONFIGURATION.style] == "instrument_classic" ? 1 : ' if slot.get('slotId')=='3' else ''
                node(g,'Transform',target=axis,value=prefix+f'{huge} ? 1.285714286 : '+'subText([CONFIGURATION.ComplicationSize], 0, 1) == "c" ? 0.857142857 : [CONFIGURATION.style] != "instrument_classic" && subText([CONFIGURATION.ComplicationSize], 0, 1) == "l" ? 1.142857143 : [CONFIGURATION.style] != "instrument_classic" ? 1.0 : [CONFIGURATION.Layout] == "top" && subText([CONFIGURATION.ComplicationSize], 0, 1) == "l" ? 1.035714286 : [CONFIGURATION.Layout] == "top" ? 0.964285714 : subText([CONFIGURATION.ComplicationSize], 0, 1) == "l" ? 0.928571429 : 0.892857143')
    clock=scene.find('.//Group[@name="digital_time"]')
    from widget_options import digital_decoration
    digital_decoration(clock)
    # The lower arc otherwise passes directly through bottom digital time.
    # Keep the angle geometry and move the ring inside that text's clear space.
    for ring in active.findall('.//Group[@name="period_dividers_arc"]'):
        for axis in ('scaleX','scaleY'):
            node(ring,'Transform',target=axis,value='[CONFIGURATION.DigitalTime] == "TRUE" ? 0.80 : 1')
    clock.set('y','299')
    node(clock,'Transform',target='y',value='[CONFIGURATION.Layout] == "top" ? 154 : [CONFIGURATION.style] == "instrument_classic" ? 299 : [CONFIGURATION.MinuteTrackStyle] != "None" ? 312 : 326')
    for axis in ('scaleX','scaleY'):
        node(clock,'Transform',target=axis,value='subText([CONFIGURATION.DigitalSize], 0, 1) == "c" ? 1.0 : subText([CONFIGURATION.DigitalSize], 0, 1) == "l" ? 1.65 : 1.35')
    from complication_theme import apply as theme_complications
    theme_complications(root)
    native_selectors(root)

def flat_palettes(flat):
    """Reuse the high resolution perimeter, add only a tiny coverage inset.

    Both pale-on-dark and dark-on-pale combinations retain a contrasting rim.
    The inset is at native resolution; the outer alpha remains the original
    supersampled contour. No repeated color PNGs are generated.
    """
    from PIL import Image,ImageFilter
    from generate import RES,node
    for parent in list(flat.iter()):
        for part in list(parent):
            if part.tag!='PartImage':continue
            resource=part.find('Image').get('resource')
            name='flat_inset_'+resource
            with Image.open(RES/'drawable-nodpi'/(resource+'.png')) as source:
                bitmap=source.convert('RGBA')
            width,height=int(part.get('width')),int(part.get('height'))
            ratio=bitmap.width/width
            radius=max(1,round(.65*ratio))
            alpha=bitmap.getchannel('A').filter(ImageFilter.MinFilter(2*radius+1))
            alpha=alpha.resize((width,height),Image.Resampling.BOX)
            inset=Image.new('RGBA',(width,height),'white');inset.putalpha(alpha)
            inset.save(RES/'drawable-nodpi'/(name+'.png'),optimize=True)
            inner=copy.deepcopy(part);inner.find('Image').set('resource',name)
            # Flat color replaces every pixel, so the source RGB never matters.
            node(part,'Transform',target='tintColor',value='[CONFIGURATION.HandColor] == "black" ? #F0F0E7 : #222A29')
            node(inner,'Transform',target='tintColor',value='[CONFIGURATION.HandColor] == "adaptive" && [CONFIGURATION.background] == "white" ? #FAFAF7 : [CONFIGURATION.HandColor] == "adaptive" && [CONFIGURATION.background] == "ivory" ? #E9E2CE : [CONFIGURATION.HandColor] == "adaptive" ? #EEEBD9 : [CONFIGURATION.HandColor] == "white" ? #F0F0E7 : [CONFIGURATION.HandColor] == "black" ? #222A29 : [CONFIGURATION.HandColor] == "orange" ? #F08A35 : #91DB9B')
            wrapper=E.Element('Group',name='flat_blade',x='0',y='0',width='432',height='432')
            index=list(parent).index(part);parent.remove(part)
            wrapper.append(part);wrapper.append(inner);parent.insert(index,wrapper)

def native_selectors(root):
    """A single list equality needs two native nodes, not a five-node condition.

    Compound expressions keep their existing exact semantics. This conversion
    only touches scene selectors, never the user schema or geometry.
    """
    bools={'minute','DigitalTime','AodMinute','Seconds'}
    for parent in list(root.find('Scene').iter()):
        for child in list(parent):
            if child.tag!='Condition' or child.find('Default') is not None:continue
            expressions=child.findall('Expressions/Expression')
            compares=child.findall('Compare')
            if len(expressions)!=1 or len(compares)!=1:continue
            match=re.fullmatch(r'\[CONFIGURATION\.(\w+)\] == "([^\"]+)"',expressions[0].text or '')
            if not match or match[1] in bools:continue
            native=E.Element('ListConfiguration',id=match[1])
            option=E.SubElement(native,'ListOption',id=match[2])
            option.extend(list(compares[0]))
            if parent.tag not in ('Group','Scene'):
                wrapper=E.Element('Group',name='native_selector',x='0',y='0',width='432',height='432')
                wrapper.append(native);native=wrapper
            index=list(parent).index(child);parent.remove(child);parent.insert(index,native)
