"""Shared vector-derived hands and optional two-subdial composition.

No photo input, additional user-configuration key or per-color bitmap copies.
"""
import copy
import xml.etree.ElementTree as E
from PIL import Image,ImageFilter
from generate import ROOT,RES

NEW='[CONFIGURATION.HandColor] == "br_orange" || [CONFIGURATION.HandColor] == "br_amber" || [CONFIGURATION.HandColor] == "br_mono"'
LAYOUT='subText([CONFIGURATION.Layout], 0, 3) == "br_"'
ACCENT='[CONFIGURATION.HandColor] == "br_mono" ? #F0F2E9 : [CONFIGURATION.HandColor] == "br_amber" ? #FFC027 : #FF992B'

def artwork():
    import instrument_classic as master
    from hand_updates import cropped_asset
    out=ROOT/'docs/hand-masters/bellross-palettes';out.mkdir(parents=True,exist_ok=True)
    records={}
    master.PALETTES['custom']=dict(body='#101414',edge='#C5CCC4',orange='#FF992B',orange_edge='#FF992B',ring='#333B38',disk='#101414',pin='#D0D5CA')
    try:
        for part in ('hour','minute','hub'):
            source=master.svg(part,'custom')
            for layer in ('base','accent') if part!='hub' else ('base',):
                svg=copy.deepcopy(source)
                if layer=='accent':
                    for child in list(svg):
                        if child.tag.endswith('title'):continue
                        if child.get('fill')!='#FF992B':svg.remove(child)
                        else:child.set('fill','#FFFFFF');child.set('stroke','#FFFFFF')
                else:
                    for child in svg:
                        if child.get('fill')=='#FF992B':child.set('fill','#101414');child.set('stroke','#101414')
                name=f'br_shared_{part}_{layer}';path=out/(name+'.svg')
                E.indent(svg,space='  ');E.ElementTree(svg).write(path,encoding='utf-8',xml_declaration=True)
                # Two coverage samples per physical pixel, from a clean vector master.
                im=master.raster(path);im=im.resize((im.width//3*2,im.height//3*2),Image.Resampling.BOX)
                if layer=='accent':im.putalpha(im.getchannel('A').filter(ImageFilter.MinFilter(3)))
                records[part,layer]=(name,cropped_asset(im,master.rectangle(part),name))
                if layer=='base':
                    light=copy.deepcopy(svg)
                    for child in light:
                        for attr in ('fill','stroke'):
                            if child.get(attr) in ('#101414','#333B38'):child.set(attr,'#4B4333')
                            elif child.get(attr)=='#C5CCC4':child.set(attr,'#272D25')
                    name=f'br_shared_{part}_light';path=out/(name+'.svg')
                    E.ElementTree(light).write(path,encoding='utf-8',xml_declaration=True)
                    im=master.raster(path);im=im.resize((im.width//3*2,im.height//3*2),Image.Resampling.BOX)
                    records[part,'light']=(name,cropped_asset(im,master.rectangle(part),name))
    finally:del master.PALETTES['custom']
    return records

def apply(root):
    from generate import node,condition,ellipse,template
    from complication_theme import background_expression,DATE_INK
    records=artwork()
    original=root.find('.//Group[@name="original_hands"]')
    for parent in list(original.iter()):
        for part in list(parent):
            if part.tag!='PartImage':continue
            image=part.find('Image');resource=image.get('resource','')
            if 'instrument_classic_' not in resource:continue
            kind=next((k for k in ('hour','minute','hub') if '_'+k+'_' in resource),None)
            if kind is None:continue
            wrapper=node(parent,'Group',name='br_choice',x=0,y=0,width=432,height=432)
            parent.remove(wrapper);index=list(parent).index(part);parent.remove(part);parent.insert(index,wrapper);wrapper.append(part)
            node(part,'Transform',target='alpha',value='[CONFIGURATION.HandColor] == "original" ? 255 : 0')
            branch=node(wrapper,'Group',name='br_ink',x=0,y=0,width=432,height=432)
            node(branch,'Transform',target='alpha',value='[CONFIGURATION.HandColor] == "original" ? 0 : 255')
            for layer in ('base','accent') if kind!='hub' else ('base',):
                light=resource.endswith(('_white','_ivory'))
                name,(x,y,w,h)=records[kind,'light' if layer=='base' and light else layer]
                attrs={k:v for k,v in part.attrib.items() if k not in ('x','y','width','height','pivotX','pivotY','name')}
                p=node(branch,'PartImage',x=x,y=y,width=w,height=h,pivotX=(216-x)/w,pivotY=(216-y)/h,name=f'br_{kind}_{layer}',**attrs)
                for t in part.findall('Transform'):
                    if t.get('target')!='alpha':p.append(copy.deepcopy(t))
                node(p,'Image',resource=name)
                if layer=='accent':node(p,'Transform',target='tintColor',value=ACCENT)
                elif light and kind!='hub':node(p,'Transform',target='tintColor',value='[CONFIGURATION.background] == "white" ? #655333 : #40331F')
    scene=root.find('Scene')
    for sid in ('1','2'):
        container=scene.find(f'ComplicationSlot[@slotId="{sid}"]')
        container.attrib.update(x='38' if sid=='1' else '218',y='140',width='176',height='152')
        container.find('BoundingOval').attrib.update(x='0',y='0',width='176',height='152')
        for group in scene.findall(f'ComplicationSlot[@slotId="{sid}"]/Complication/Group'):
            tx=group.find('Transform[@target="x"]')
            tx.set('value',f'({LAYOUT}) ? {48 if sid=="1" else 72} : [CONFIGURATION.style] == "instrument_classic" ? {98 if sid=="1" else 22} : {88 if sid=="1" else 32}')
            node(group,'Transform',target='y',value='48')
            for axis in ('scaleX','scaleY'):
                t=group.find(f'Transform[@target="{axis}"]')
                # Two subdials can be slightly larger than the three-dial layout.
                t.set('value',f'({LAYOUT}) && [CONFIGURATION.ComplicationSize] == "compact" ? 2.142857143 : ({LAYOUT}) && [CONFIGURATION.ComplicationSize] == "large" ? 2.714285714 : ({LAYOUT}) ? 2.428571429 : '+t.get('value'))
    for group in scene.findall('ComplicationSlot/Complication/Group'):
        backdrop=group.find('PartDraw/Transform[@target="tintColor"]')
        if backdrop is not None:backdrop.set('value',background_expression())
    # The provider remains slot 3, so an existing user selection survives.
    slot=scene.find('ComplicationSlot[@slotId="3"]')
    slot.set('width','176');slot.set('height','128')
    bounds=slot.find('BoundingOval');bounds.tag='BoundingBox'
    bounds.attrib.update(x='14',y='40',width='158',height='86')
    # WFF v4 bounds cannot move with configuration: this fixed lower strip
    # includes both valid locations without overlapping the upper two slots.
    for comp in slot.findall('Complication'):
        if comp.get('type')=='EMPTY':continue
        for group in comp.findall('Group'):
            node(group,'Transform',target='alpha',value=f'({LAYOUT}) ? 0 : 255')
        small=node(condition(comp,LAYOUT),'Group',name='br_date_window',x=0,y=0,width=176,height=128)
        d=node(small,'PartDraw',x=135,y=83,width=30,height=30)
        circle=ellipse(d,0,0,30,30,'#101414')
        # A thin frame is independent of the selected provider's artwork.
        edge=node(d,'Ellipse',x=.5,y=.5,width=29,height=29)
        node(edge,'Stroke',color='#A7AFA5',thickness=.7)
        node(edge.find('Stroke'),'Transform',target='color',value=DATE_INK)
        node(d,'Transform',target='alpha',value='subText([CONFIGURATION.Layout], 3, 4) == "s" ? 0 : 255')
        box=node(small,'PartDraw',x=133,y=85,width=34,height=26)
        shape=node(box,'Rectangle',x=0,y=0,width=34,height=26)
        node(shape,'Fill',color='#101414');node(shape,'Stroke',color='#FFC027',thickness=.8)
        node(shape.find('Stroke'),'Transform',target='color',value=DATE_INK)
        node(box,'Transform',target='alpha',value='subText([CONFIGURATION.Layout], 3, 4) == "s" ? 255 : 0')
        if comp.get('type') in ('SHORT_TEXT','RANGED_VALUE'):
            expr='[COMPLICATION.TEXT]' if comp.get('type')=='SHORT_TEXT' else '[COMPLICATION.RANGED_VALUE_VALUE]'
            template(small,150,98,28,24,expr,'#F1F1E6',16)
            text=small.find('PartText/Text');text.set('isAutoSize','TRUE')
            node(text.find('Font'),'Transform',target='color',value=DATE_INK)
        else:
            key=comp.get('type')
            image=node(small,'PartImage',x=140,y=88,width=20,height=20)
            if key=='MONOCHROMATIC_IMAGE':
                image.set('tintColor','#F1F1E6');node(image,'Transform',target='tintColor',value=DATE_INK)
            node(image,'Image',resource=f'[COMPLICATION.{key}]')
    clock=scene.find('.//Group[@name="digital_time"]')
    t=clock.find('Transform[@target="y"]');t.set('value',f'({LAYOUT}) ? 260 : '+t.get('value'))
    brand=condition(scene,LAYOUT)
    parent=node(brand,'Group',name='dial_brand',x=0,y=0,width=432,height=432)
    node(parent,'Variant',mode='AMBIENT',target='alpha',value=0)
    ink='[CONFIGURATION.background] == "black" ? #E8E9DC : #403A2C'
    for text,ids in (('Podolskii',('br_round_podolskii','br_square_podolskii')),('BelOrus',('br_round_belorus','br_square_belorus'))):
        g=condition(parent,' || '.join(f'[CONFIGURATION.Layout] == "{v}"' for v in ids))
        from generate import text as label
        for cx,word,width in ((191,'Bel',36),(216,'O',16),(241,'rus',36)) if text=='BelOrus' else ((216,text,110),):
            p=label(g,cx,132,word,'#E8E9DC',17,family='barlow_regular',w=width,h=24)
            node(p.find('Text/Font'),'Transform',target='color',value=ink)
        if text=='BelOrus':
            d=node(g,'PartDraw',x=206,y=122,width=20,height=20)
            e=node(d,'Ellipse',x=1,y=1,width=18,height=18)
            node(e,'Stroke',color='#E8E9DC',thickness=.6)
            node(d,'Transform',target='tintColor',value=ink)

def scale_palette(root):
    """Called after sharing scales. Original and sector palettes are preserved."""
    from generate import node,condition
    scales=root.find('.//Group[@name="shared_regular_scales"]')
    for p in scales.iter('PartImage'):
        if p.get('name')!='instrument_classic_custom_scale':continue
        old=p.find('Transform[@target="tintColor"]')
        fallback=old.get('value') if old is not None else p.get('tintColor','#E47D38')
        expr='[CONFIGURATION.DialTone] == "mono_dial" && [CONFIGURATION.background] == "black" ? #F0F2E9 : [CONFIGURATION.DialTone] == "mono_dial" ? #202824 : [CONFIGURATION.DialTone] == "amber_dial" && [CONFIGURATION.background] == "black" ? #FFC027 : [CONFIGURATION.DialTone] == "amber_dial" ? #805600 : '+fallback
        if old is None:node(p,'Transform',target='tintColor',value=expr)
        else:old.set('value',expr)
    # All these branches contain only colored hour scales; backgrounds, sector
    # fills, period labels and minute rings were already factored separately.
    active=root.find('Scene/Group[@name="interactive"]')
    branches=[c for c in active if any(g.get('name','').startswith('dial_') for g in c.iter('Group'))]
    colored=node(active,'Group',name='shared_colored_scales',x=0,y=0,width=432,height=432)
    active.remove(colored)
    if branches:
        active.insert(list(active).index(branches[0]),colored)
        for b in branches:active.remove(b);colored.append(b)
    else:active.append(colored)
    # One small mathematical mask per scale layer, not per design/background.
    # The two side-number holes only open in the new chronograph composition.
    for group in (scales,colored):
        mask=node(condition(group,LAYOUT),'PartDraw',x=0,y=0,width=432,height=432,renderMode='MASK',name='subdial_number_mask')
        for x,y,w,h in ((0,0,432,174),(0,258,432,174),(0,174,26,84),(114,174,200,84),(406,174,26,84)):
            shape=node(mask,'Rectangle',x=x,y=y,width=w,height=h);node(shape,'Fill',color='#FFFFFF')
