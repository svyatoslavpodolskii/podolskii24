"""One shared foreground tint per complication, preserving provider photos."""
import xml.etree.ElementTree as E

INK='[CONFIGURATION.DialTone] == "amber_dial" && [CONFIGURATION.background] == "black" ? #FFC027 : [CONFIGURATION.DialTone] == "amber_dial" ? #805600 : [CONFIGURATION.DialTone] == "brown" && [CONFIGURATION.background] == "black" ? #ED923F : [CONFIGURATION.DialTone] == "mono_dial" && [CONFIGURATION.background] == "black" ? #F0F2E9 : [CONFIGURATION.background] == "black" && ([CONFIGURATION.style] == "instrument_classic" || [CONFIGURATION.style] == "aviator") ? #EE923E : [CONFIGURATION.background] == "black" ? #F0F0E7 : [CONFIGURATION.background] == "ivory" ? #403A2C : #222A29'
DATE_INK='[CONFIGURATION.DialTone] == "amber_dial" ? #FFC027 : [CONFIGURATION.DialTone] == "brown" ? #ED923F : [CONFIGURATION.DialTone] == "mono_dial" ? #F0F2E9 : [CONFIGURATION.style] == "instrument_classic" ? #EE923E : #F0F0E7'

def background_expression():
    pairs={'charcoal':('#303128','#E6E4D9'),'navy':('#142331','#E2EBEE'),
           'forest':('#182B22','#E3EADD'),'brown':('#35302B','#E9DFCF'),
           'amber_dial':('#101212','#ECE8DB'),'mono_dial':('#101212','#F0F0E9')}
    return ''.join(f'[CONFIGURATION.DialTone] == "{key}" && [CONFIGURATION.background] == "black" ? {dark} : [CONFIGURATION.DialTone] == "{key}" ? {light} : ' for key,(dark,light) in pairs.items())+'[CONFIGURATION.background] == "black" ? #000000 : [CONFIGURATION.background] == "ivory" ? #E9E2CE : #FAFAF7'

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
