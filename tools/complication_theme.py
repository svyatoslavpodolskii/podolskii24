"""One shared foreground tint per complication, preserving provider photos."""
import xml.etree.ElementTree as E

from design_palette import ACCENT, INK as INSTRUMENT_INK
INK='[CONFIGURATION.background] != "black" ? #222A29 : [CONFIGURATION.style] != "instrument_classic" && [CONFIGURATION.HandColor] != "orange" ? #F0F0E7 : '+ACCENT
DATE_INK=INK

def background_expression():
    pairs={'charcoal':('#303128','#E6E4D9'),'navy':('#142331','#E2EBEE'),
           'forest':('#182B22','#E3EADD'),'brown':('#35302B','#E9DFCF'),
           'amber_dial':('#101212','#ECE8DB'),'mono_dial':('#101212','#F0F0E9')}
    return ''.join(f'[CONFIGURATION.DialTone] == "{key}" && [CONFIGURATION.background] == "black" ? {dark} : [CONFIGURATION.DialTone] == "{key}" ? {light} : ' for key,(dark,light) in pairs.items())+'[CONFIGURATION.background] == "black" ? #000000 : [CONFIGURATION.background] == "ivory" ? #E9E2CE : #FAFAF7'

def complication_surface():
    return '[CONFIGURATION.sectors] == "color" && [CONFIGURATION.background] == "black" ? #18221E : [CONFIGURATION.sectors] == "color" && [CONFIGURATION.background] == "ivory" ? #B8BAAC : [CONFIGURATION.sectors] == "color" ? #C2C6BE : '+background_expression()

def apply(root):
    from generate import node
    for slot in root.findall('Scene/ComplicationSlot'):
        for comp in slot.findall('Complication'):
            kind=comp.get('type')
            if kind=='EMPTY':continue
            for group in comp.findall('Condition/Compare/Group'):
                backing=group.find('PartDraw')
                foreground=node(group,'Group',name='provider_foreground',x=0,y=0,width=56,height=56)
                node(foreground,'Transform',target='tintColor',value=INK)
                node(foreground,'Transform',target='alpha',value='[CONFIGURATION.background] == "black" && [CONFIGURATION.style] != "instrument_classic" ? 205 : 230')
                border=node(foreground,'PartDraw',x=0,y=0,width=56,height=56)
                for shape in list(backing):
                    if shape.tag!='Ellipse':backing.remove(shape);border.append(shape)
                if not len(border):foreground.remove(border)
                for child in list(group):
                    if child in (backing,foreground) or child.tag in ('Transform','Variant'):continue
                    if kind=='SMALL_IMAGE':continue
                    group.remove(child);foreground.append(child)
                # Preserve the visual hierarchy after unifying RGB inks.
                for draw in list(foreground.findall('PartDraw')):
                    arcs=draw.findall('Arc')
                    if len(arcs)==2:
                        track=node(foreground,'PartDraw',x=0,y=0,width=56,height=56,alpha=65)
                        foreground.remove(track);foreground.insert(list(foreground).index(draw),track)
                        draw.remove(arcs[0]);track.append(arcs[0])
                for element in foreground.iter():
                    for attr in ('color','tintColor'):
                        if element.get(attr):element.set(attr,'#FFFFFF')
