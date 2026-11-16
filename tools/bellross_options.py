"""Shared vector-derived hands and optional two-subdial composition.

No photo input, additional user-configuration key or per-color bitmap copies.
"""
import copy
import xml.etree.ElementTree as E
from PIL import Image,ImageFilter
from generate import ROOT,RES

NEW='[CONFIGURATION.HandColor] == "br_orange" || [CONFIGURATION.HandColor] == "br_amber" || [CONFIGURATION.HandColor] == "br_mono"'
LAYOUT='subText([CONFIGURATION.Layout], 0, 3) == "br_"'
from design_palette import ACCENT

def artwork():
    import instrument_classic as master
    from hand_updates import cropped_asset
    out=ROOT/'docs/hand-masters/bellross-palettes';out.mkdir(parents=True,exist_ok=True)
    records={}
    master.PALETTES['custom']=dict(body='#101414',edge='#8A9086',orange='#FF992B',orange_edge='#FF992B',ring='#333B38',disk='#101414',pin='#A9B0A5')
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
                    for background,fill in (('white','#FAFAF7'),('ivory','#E9E2CE')):
                        light=copy.deepcopy(svg)
                        for child in light:
                            for attr in ('fill','stroke'):
                                if child.get(attr) in ('#101414','#333B38'):child.set(attr,fill)
                                elif child.get(attr)=='#8A9086':child.set(attr,'#535950')
                        name=f'br_shared_{part}_light' if background=='white' else f'br_shared_{part}_ivory'
                        path=out/(name+'.svg')
                        E.ElementTree(light).write(path,encoding='utf-8',xml_declaration=True)
                        im=master.raster(path)
                        im=im.resize((im.width//3*2,im.height//3*2),Image.Resampling.BOX)
                        records[part,background]=(name,cropped_asset(im,master.rectangle(part),name))
    finally:del master.PALETTES['custom']
    return records

def apply(root):
    from generate import node,condition,ellipse,template
    from complication_theme import background_expression,complication_surface,DATE_INK
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
                name,(x,y,w,h)=records[kind,('white' if resource.endswith('_white') else 'ivory') if layer=='base' and light else layer]
                attrs={k:v for k,v in part.attrib.items() if k not in ('x','y','width','height','pivotX','pivotY','name')}
                p=node(branch,'PartImage',x=x,y=y,width=w,height=h,pivotX=(216-x)/w,pivotY=(216-y)/h,name=f'br_{kind}_{layer}',**attrs)
                for t in part.findall('Transform'):
                    if t.get('target')!='alpha':p.append(copy.deepcopy(t))
                node(p,'Image',resource=name)
                if layer=='accent':node(p,'Transform',target='tintColor',value=ACCENT)
                elif kind!='hub':
                    # Reuse the existing coverage inset. Only the perimeter
                    # remains visible; the actual body matches the whole theme.
                    fill=copy.deepcopy(part)
                    fill.set('name',f'br_{kind}_theme_body')
                    for t in list(fill.findall('Transform')):
                        if t.get('target') in ('alpha','tintColor'):fill.remove(t)
                    mask=resource.rsplit('_',1)[0]+'_white'
                    mask='flat_inset_'+mask
                    assert (RES/'drawable-nodpi'/(mask+'.png')).is_file(),mask
                    fill.find('Image').set('resource',mask)
                    node(fill,'Transform',target='tintColor',value=background_expression())
                    branch.append(fill)
    scene=root.find('Scene')
    for sid in ('1','2'):
        container=scene.find(f'ComplicationSlot[@slotId="{sid}"]')
        container.attrib.update(x='14' if sid=='1' else '210',y='124',width='208',height='184')
        container.find('BoundingOval').attrib.update(x='0',y='0',width='208',height='184')
        for group in scene.findall(f'ComplicationSlot[@slotId="{sid}"]/Complication/Group'):
            tx=group.find('Transform[@target="x"]')
            wide='subText([CONFIGURATION.ComplicationSize], textLength([CONFIGURATION.ComplicationSize])-4, textLength([CONFIGURATION.ComplicationSize])) == "wide"'
            offset=f'({wide}) ? {-8 if sid=="1" else 8} : 0'
            base=f'({LAYOUT}) ? {72 if sid=="1" else 80} : [CONFIGURATION.style] == "instrument_classic" ? {122 if sid=="1" else 30} : {112 if sid=="1" else 40}'
            # Keep one fixed-width suffix check, independent of the size prefix.
            tx.set('value',f'({base}) + ({offset})')
            node(group,'Transform',target='y',value='64')
            for axis in ('scaleX','scaleY'):
                t=group.find(f'Transform[@target="{axis}"]')
                # Two subdials can be slightly larger than the three-dial layout.
                t.set('value',f'({LAYOUT}) && subText([CONFIGURATION.ComplicationSize], 0, 1) == "h" ? 3 : ({LAYOUT}) && subText([CONFIGURATION.ComplicationSize], 0, 1) == "c" ? 2.142857143 : ({LAYOUT}) && subText([CONFIGURATION.ComplicationSize], 0, 1) == "l" ? 2.714285714 : ({LAYOUT}) ? 2.428571429 : '+t.get('value'))
    for group in scene.findall('ComplicationSlot/Complication/Group'):
        backdrop=group.find('PartDraw/Transform[@target="tintColor"]')
        if backdrop is not None:backdrop.set('value',complication_surface())
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
        node(small,'Transform',target='x',value=-10)
        node(small,'Transform',target='y',value=4)
        d=node(small,'PartDraw',x=135,y=83,width=30,height=30)
        ellipse(d,0,0,30,30,'#101414');circle=d.find('Ellipse')
        node(circle.find('Fill'),'Transform',target='color',value=background_expression())
        # A thin frame is independent of the selected provider's artwork.
        edge=node(d,'Ellipse',x=.5,y=.5,width=29,height=29)
        node(edge,'Stroke',color='#A7AFA5',thickness=1.2)
        node(edge.find('Stroke'),'Transform',target='color',value=DATE_INK)
        node(d,'Transform',target='alpha',value='subText([CONFIGURATION.Layout], 3, 4) == "s" ? 0 : 255')
        box=node(small,'PartDraw',x=133,y=85,width=34,height=26)
        shape=node(box,'Rectangle',x=0,y=0,width=34,height=26)
        node(shape,'Fill',color='#101414');node(shape,'Stroke',color='#FFC027',thickness=1.2)
        node(shape.find('Fill'),'Transform',target='color',value=background_expression())
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
    t=clock.find('Transform[@target="y"]');t.set('value',f'({LAYOUT}) ? 274 : '+t.get('value'))
    brand=condition(scene,LAYOUT)
    brand_layer=list(scene)[-1]
    # Scene order is painter order: dial lettering belongs below moving hands.
    scene.remove(brand_layer)
    scene.insert(list(scene).index(scene.find('Group[@name="interactive_hands"]')),brand_layer)
    parent=node(brand,'Group',name='dial_brand',x=0,y=0,width=432,height=432)
    node(parent,'Variant',mode='AMBIENT',target='alpha',value=0)
    from complication_theme import INK
    from dial_wordmark import artwork as wordmarks
    lettering=wordmarks()
    ink=INK
    for text,ids in (('Podolskii',('br_round_podolskii','br_square_podolskii')),('BelOrus',('br_round_belorus','br_square_belorus'))):
        g=condition(parent,' || '.join(f'[CONFIGURATION.Layout] == "{v}"' for v in ids))
        resource,width=lettering[text]
        width=2*round(width/2)
        p=node(g,'PartImage',x=216-width//2,y=134,width=width,height=24)
        node(p,'Image',resource=resource)
        node(p,'Transform',target='tintColor',value=ink)

def scale_palette(root):
    """Called after sharing scales. Original and sector palettes are preserved."""
    from generate import node,condition
    scales=root.find('.//Group[@name="shared_regular_scales"]')
    for p in scales.iter('PartImage'):
        if p.get('name')!='instrument_classic_custom_scale':continue
        old=p.find('Transform[@target="tintColor"]')
        fallback=old.get('value') if old is not None else p.get('tintColor','#E47D38')
        from design_palette import INK
        expr=INK
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
        # Clear the adjacent 8/16 and 4/20 positions as well: wide subdials
        # otherwise graze these numerals, particularly with an outer minute ring.
        for x,y,w,h in ((0,0,432,110),(0,322,432,110),
                (0,110,26,90),(0,232,26,90),(406,110,26,90),(406,232,26,90),
                (0,200,8,32),(424,200,8,32),(130,110,172,212)):
            shape=node(mask,'Rectangle',x=x,y=y,width=w,height=h);node(shape,'Fill',color='#FFFFFF')
