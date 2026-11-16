"""Native text decoration and shared theme references; no new raster assets."""
from complication_theme import background_expression

STYLE='subText([CONFIGURATION.DigitalSize], 2, textLength([CONFIGURATION.DigitalSize]))'
FRAME=f'{STYLE} == "frame"'
BOX=f'{STYLE} == "box"'
OUTLINE=f'{STYLE} == "outline"'
LEGACY='([CONFIGURATION.DigitalSize] == "compact" || [CONFIGURATION.DigitalSize] == "normal" || [CONFIGURATION.DigitalSize] == "large") && [CONFIGURATION.sectors] == "color"'
SPLIT='[CONFIGURATION.Layout] == "bottom" && [CONFIGURATION.sectors] == "color" && [CONFIGURATION.boundaries] == "quarter" && [CONFIGURATION.background] != "black" && !('+BOX+') && !('+LEGACY+')'

def digital_decoration(clock):
    from generate import node
    for native in list(clock.iter('DigitalClock')):
        pale=native.find('TimeText[last()]/Font').get('color')=='#F0F0E7'
        # Both existing contrast branches participate only at the Quarter edge.
        for compare in clock.findall('.//Compare'):
            if native in list(compare):
                condition=next(c for c in clock.iter('Condition') if compare in list(c))
                expression=condition.find('Expressions/Expression')
                expression.text=f'({SPLIT}) || ({expression.text})'
        texts=native.findall('TimeText')
        for old in texts[:-1]:native.remove(old)
        # TimeText's restricted Font cannot contain decorations in v4.
        # PartText uses the same system hour/minute sources, once per minute.
        native.tag='Group';native.set('name','digital_readout')
        text=texts[-1];font=text.find('Font');text.remove(font)
        text.tag='PartText';text.attrib.pop('format');text.attrib.pop('hourFormat')
        align=text.attrib.pop('align','CENTER');content=node(text,'Text',align=align);content.append(font)
        rim=node(font,'Outline',color='#222A29' if font.get('color')=='#F0F0E7' else '#F0F0E7',width=.35)
        # Read the actual sector under the lower clock, not the base background.
        from design_palette import DIGITAL_DARK_INK
        fallback=DIGITAL_DARK_INK if pale else font.get('color')
        node(font,'Transform',target='color',value=f'({SPLIT}) ? '+('#F0F0E7' if pale else '#222A29')+' : [CONFIGURATION.sectors] == "color" && [CONFIGURATION.Layout] == "bottom" ? #F0F0E7 : '+fallback)
        template=node(rim,'Template');template.text='%02d:%02d'
        node(template,'Parameter',expression='[HOUR_0_23]')
        node(template,'Parameter',expression='[MINUTE]')
        visible=OUTLINE
        node(rim,'Transform',target='color',value=f'({visible}) ? '+rim.get('color')+' : #00000000')
        clip=node(native,'PartDraw',name='quarter_time_contrast',x=0,y=0,width=72,height=22,renderMode='MASK')
        rect=node(clip,'Rectangle',x=0,y=0,width=72,height=22)
        node(rect,'Fill',color='#FFFFFF')
        node(rect,'Transform',target='x',value=f'({SPLIT}) ? {0 if pale else 36} : 0')
        node(rect,'Transform',target='width',value=f'({SPLIT}) ? 36 : 72')
    backing=node(clock,'PartDraw',name='digital_sector_backing',x=10,y=1,width=52,height=20)
    clock.remove(backing);clock.insert(0,backing)
    node(backing,'Variant',mode='AMBIENT',target='alpha',value=0)
    node(backing,'Transform',target='alpha',value=f'({FRAME} || {BOX} || ({LEGACY})) ? 255 : 0')
    for inset,width,color in ((0,1.5,'#222A29'),(.5,.75,'#C5CDC0')):
        rect=node(backing,'RoundRectangle',x=inset,y=inset,width=52-2*inset,height=20-2*inset,cornerRadiusX=4,cornerRadiusY=4)
        if inset==0:
            fill=node(rect,'Fill',color='#FFFFFF')
            node(fill,'Transform',target='color',value=f'({BOX} || ({LEGACY})) && [CONFIGURATION.sectors] == "color" ? #18221E : ({BOX} || ({LEGACY})) ? '+background_expression()+' : #00000000')
        node(rect,'Stroke',color=color,thickness=width)

def theme_reference(root):
    """Resolve the surface expression once on the visible background layer."""
    from generate import node
    source=root.find('.//Group[@name="shared_backgrounds"]')
    expression=background_expression()
    # All three background silhouettes are the same circle. Its tint already
    # resolves every background/tone; retain one white coverage silhouette.
    import copy
    shape=copy.deepcopy(next(source.iter('PartDraw')))
    for t in list(shape.findall('Transform[@target="tintColor"]')):shape.remove(t)
    shape.find('Ellipse/Fill').set('color','#FFFFFF')
    for child in list(source):
        if child.tag=='Condition':source.remove(child)
    source.insert(0,shape)
    binding=node(source,'Transform',target='tintColor',value=expression)
    node(source,'Reference',name='themeSurface',source='tintColor',defaultValue='#000000')
    for t in root.iter('Transform'):
        if t is not binding and expression in t.get('value',''):
            t.set('value',t.get('value').replace(expression,'[REFERENCE.themeSurface]'))
