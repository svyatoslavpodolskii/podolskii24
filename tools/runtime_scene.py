"""Native layer sharing, compact value-first complications, persistent AOD."""
import copy
import xml.etree.ElementTree as E

def share_classic_scale(root):
    from generate import RES
    from PIL import Image,ImageChops
    colors=dict(ink='#222A29',orange='#E47D38',brown='#A34B24',paper='#F0F0E7')
    alpha=None
    for key,color in colors.items():
        with Image.open(RES/'drawable-nodpi'/f'trimmed_classic_scale_{key}.png') as opened:
            image=opened.convert('RGBA')
        if alpha is None:alpha=image.getchannel('A')
        assert image.getchannel('A').tobytes()==alpha.tobytes(), 'Scale contours differ'
        flat=Image.new('RGBA',image.size,color);flat.putalpha(alpha)
        for background in ('black','white'):
            a=Image.new('RGBA',image.size,background);a.alpha_composite(image)
            b=Image.new('RGBA',image.size,background);b.alpha_composite(flat)
            assert max(high for low,high in ImageChops.difference(a,b).getextrema())<=3
    white=Image.new('RGBA',alpha.size,'white');white.putalpha(alpha)
    white.save(RES/'drawable-nodpi/runtime_classic_scale_alpha.png',optimize=True)
    for part in root.iter('PartImage'):
        image=part.find('Image');name=image.get('resource','')
        if not name.startswith('trimmed_classic_scale_'):continue
        part.set('tintColor',colors[name.removeprefix('trimmed_classic_scale_')])
        image.set('resource','runtime_classic_scale_alpha')

def factor_layers(root, canonical):
    from generate import condition
    active=root.find('.//Group[@name="interactive"]')
    layers={name:{} for name in ('backgrounds','period_fills','period_details_under','period_details')}
    def add(layer, el, guard):
        normalized=copy.deepcopy(el)
        for n in normalized.iter():
            if not n.get('name','').startswith('period_label_'):n.attrib.pop('name',None)
        key=canonical(normalized)
        layers[layer].setdefault(key,[el,[]])[1].append(guard)
    for outer in list(active):
        dial=outer.find('Compare/Group') if outer.tag=='Condition' else None
        if dial is None or not dial.get('name','').startswith('dial_'):continue
        guard=outer.find('Expressions/Expression').text
        background=list(dial)[0]
        assert background.tag=='PartDraw' and background.find('Ellipse') is not None
        dial.remove(background);add('backgrounds',background,guard)
        for branch in list(dial):
            if branch.tag!='Condition':continue
            period=branch.find('Compare/Group')
            if period is None or period.get('name','').startswith('regular_scale'):continue
            expr=branch.find('Expressions/Expression').text
            for el in list(period):
                if el.get('name','').startswith('scale_on_'):continue
                period.remove(el)
                layer='period_fills' if el.get('name')=='sector_fills' else ('period_details_under' if '[CONFIGURATION.sectors] == "color"' in expr else 'period_details')
                add(layer,el,f'({guard}) && ({expr})')
    def emit(name):
        container=E.Element('Group',name='shared_'+name,x='0',y='0',width='432',height='432')
        for el,guards in layers[name].values():
            condition(container,' || '.join('('+g+')' for g in guards)).append(el)
        return container
    active.insert(0,emit('backgrounds'));active.insert(1,emit('period_fills'))
    active.insert(2,emit('period_details_under'))
    minute=active.find('Group[@name="shared_minute_tracks"]')
    active.insert(list(active).index(minute),emit('period_details'))

def compact_complications(root):
    from generate import template, arc, BACKGROUNDS
    for slot in root.findall('Scene/ComplicationSlot'):
        slot_id=slot.get('slotId')
        if slot_id=='1':slot.set('x','106')
        if slot_id=='2':slot.set('x','230')
        for g in slot.findall('.//Group'):
            if not g.get('name','').startswith('slot'):continue
            g.set('x','20');g.set('y','8' if slot_id=='3' else '20')
            g.attrib.pop('scaleX',None);g.attrib.pop('scaleY',None)
            kind=next(k for k in ('SHORT_TEXT','RANGED_VALUE','MONOCHROMATIC_IMAGE','SMALL_IMAGE') if k in g.get('name'))
            if kind in ('MONOCHROMATIC_IMAGE','SMALL_IMAGE'):
                g.remove(g.find('PartDraw'));continue
            fg=g.find('.//Font').get('color')
            for child in list(g):g.remove(child)
            if kind=='RANGED_VALUE':
                d=E.SubElement(g,'PartDraw',x='0',y='0',width='56',height='56')
                arc(d,28,28,53,210,510,fg,.45)
                a=arc(d,28,28,53,210,210,fg,1.7)
                E.SubElement(a,'Transform',target='endAngle',value='210 + 300 * clamp(([COMPLICATION.RANGED_VALUE_VALUE] - [COMPLICATION.RANGED_VALUE_MIN]) / clamp([COMPLICATION.RANGED_VALUE_MAX] - [COMPLICATION.RANGED_VALUE_MIN], 0.001, 1000000000), 0, 1)')
                template(g,28,27,50,32,'[COMPLICATION.RANGED_VALUE_VALUE]',fg,25,'%.0f')
            else:template(g,28,28,56,32,'[COMPLICATION.TEXT]',fg,23)
            # A small value backing stays legible over a light/dark sector
            # boundary without reinstating the former 96px opaque circles.
            backing=E.Element('PartDraw',x='0',y='0',width='56',height='56')
            rect=E.SubElement(backing,'RoundRectangle',x='1',y='12',width='54',height='32',cornerRadiusX='5',cornerRadiusY='5')
            E.SubElement(rect,'Fill',color=BACKGROUNDS[g.get('name').rsplit('_',1)[1]])
            g.insert(0,backing)

def ambient_base(root):
    from generate import node
    scene=root.find('Scene');ambient=scene.find('Group[@name="ambient"]')
    scene.remove(ambient);scene.insert(0,ambient)
    ambient.set('alpha','255')
    clock=node(ambient,'DigitalClock',x=158,y=268,width=116,height=32)
    text=node(clock,'TimeText',x=0,y=0,width=116,height=32,format='hh:mm',hourFormat='24',align='CENTER')
    node(text,'Font',family='barlow_regular',size=25,color='#B9C0BA')

def prune_hands(root):
    from generate import REMOVED_HAND_STYLES,DEFAULT_HANDS,selection
    import re
    cfg=root.find('UserConfigurations/ListConfiguration[@id="HandStyle"]')
    for option in list(cfg):
        if option.get('id') in REMOVED_HAND_STYLES:cfg.remove(option)
    hands=root.find('.//Group[@name="interactive_hands"]')
    for parent in list(hands.iter()):
        for child in list(parent):
            if child.tag!='Condition':continue
            expression=child.find('Expressions/Expression')
            if expression is None:continue
            match=re.match(r'^\[CONFIGURATION.HandStyle\] == "([^"]+)"',expression.text or '')
            if not match or match[1] not in REMOVED_HAND_STYLES:continue
            defaults=[s for s,k in DEFAULT_HANDS.items() if k==match[1]]
            if defaults:expression.text=selection(HandStyle='auto')+' && ('+' || '.join(selection(style=s) for s in defaults)+')'
            else:parent.remove(child)

def apply(root, canonical):
    source=canonical(root.find('Scene'))
    share_classic_scale(root)
    factor_layers(root,canonical)
    compact_complications(root)
    ambient_base(root)
    prune_hands(root)
    return source
