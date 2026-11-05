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
            if not list(period):dial.remove(branch)
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
    from generate import template, arc, BACKGROUNDS,ellipse,condition,node
    for slot in root.findall('Scene/ComplicationSlot'):
        slot_id=slot.get('slotId')
        if slot_id=='1':slot.set('x','106')
        if slot_id=='2':slot.set('x','230')
        if slot_id=='3':slot.set('y','212')
        for g in slot.findall('.//Group'):
            if not g.get('name','').startswith('slot'):continue
            g.set('x','20');g.set('y','20')
            g.attrib.pop('scaleX',None);g.attrib.pop('scaleY',None)
            kind=next(k for k in ('SHORT_TEXT','RANGED_VALUE','MONOCHROMATIC_IMAGE','SMALL_IMAGE') if k in g.get('name'))
            bg=BACKGROUNDS[g.get('name').rsplit('_',1)[1]]
            from generate import ink_on
            fg=ink_on(bg)
            for child in list(g):g.remove(child)
            backing=node(g,'PartDraw',x=0,y=0,width=56,height=56)
            ellipse(backing,0,0,56,56,bg)
            arc(backing,28,28,55,0,360,'#68746C' if bg!='#000000' else '#56635A',.6)
            if kind in ('MONOCHROMATIC_IMAGE','SMALL_IMAGE'):
                image_parent=g
                if kind=='SMALL_IMAGE':
                    image_parent=node(g,'Group',name='round_small_image',x=0,y=0,width=56,height=56)
                    mask=node(image_parent,'PartDraw',x=0,y=0,width=56,height=56,renderMode='MASK')
                    ellipse(mask,5,5,46,46,'#FFFFFF')
                image=node(image_parent,'PartImage',x=10 if kind=='MONOCHROMATIC_IMAGE' else 5,y=10 if kind=='MONOCHROMATIC_IMAGE' else 5,width=36 if kind=='MONOCHROMATIC_IMAGE' else 46,height=36 if kind=='MONOCHROMATIC_IMAGE' else 46)
                if kind=='MONOCHROMATIC_IMAGE':image.set('tintColor',fg)
                node(image,'Image',resource=f'[COMPLICATION.{kind}]')
                continue
            has_icon='[COMPLICATION.MONOCHROMATIC_IMAGE] != null && [COMPLICATION.MONOCHROMATIC_IMAGE] != ""'
            image=node(condition(g,has_icon),'PartImage',name='provider_icon',x=20,y=6,width=16,height=16,tintColor=fg)
            node(image,'Image',resource='[COMPLICATION.MONOCHROMATIC_IMAGE]')
            if kind=='RANGED_VALUE':
                d=E.SubElement(g,'PartDraw',x='0',y='0',width='56',height='56')
                arc(d,28,28,53,210,510,fg,.45)
                a=arc(d,28,28,53,210,210,fg,1.7)
                E.SubElement(a,'Transform',target='endAngle',value='210 + 300 * clamp(([COMPLICATION.RANGED_VALUE_VALUE] - [COMPLICATION.RANGED_VALUE_MIN]) / clamp([COMPLICATION.RANGED_VALUE_MAX] - [COMPLICATION.RANGED_VALUE_MIN], 0.001, 1000000000), 0, 1)')
                template(g,28,28,48,26,'[COMPLICATION.RANGED_VALUE_VALUE]',fg,21,'%.0f')
            else:template(g,28,28,48,26,'[COMPLICATION.TEXT]',fg,20)
            value=g.findall('PartText')[-1]
            node(value,'Transform',target='y',value=f'({has_icon}) ? 24 : 15')

def ambient_base(root):
    from generate import node,condition
    scene=root.find('Scene');ambient=scene.find('Group[@name="ambient"]')
    scene.remove(ambient)
    for name,tint in (('interactive','#87998D'),('interactive_hands','#B7C2B7')):
        g=scene.find(f'Group[@name="{name}"]')
        for variant in list(g.findall('Variant')):g.remove(variant)
        node(g,'Variant',mode='AMBIENT',target='tintColor',value=tint)
        if name=='interactive_hands':node(g,'Variant',mode='AMBIENT',target='alpha',value=170)
    active=scene.find('Group[@name="interactive"]')
    for name in ('shared_backgrounds','shared_period_fills','shared_period_details_under','shared_period_details','shared_minute_tracks'):
        node(active.find(f'Group[@name="{name}"]'),'Variant',mode='AMBIENT',target='alpha',value=0)
    for minute in scene.findall('Group[@name="interactive_hands"]//Group[@name="minute"]'):
        node(minute,'Variant',mode='AMBIENT',target='alpha',value=0)
    # One native clock serves both modes; default on, independently switchable.
    parent=node(condition(scene,'[CONFIGURATION.DigitalTime] == "TRUE"'),'Group',name='digital_time',x=180,y=286,width=72,height=22)
    node(parent,'Variant',mode='AMBIENT',target='alpha',value=170)
    node(parent,'Variant',mode='AMBIENT',target='tintColor',value='#B7C2B7')
    for expr,fg in (('[CONFIGURATION.background] == "black"','#F0F0E7'),('[CONFIGURATION.background] != "black"','#222A29')):
        clock=node(condition(parent,expr),'DigitalClock',x=0,y=0,width=72,height=22)
        # Native TimeText has no outline attribute in WFF v4. Four one-pixel
        # offsets provide a quiet contour, hidden in AOD; no opaque backing.
        for dx,dy in ((-1,0),(1,0),(0,-1),(0,1),(0,0)):
            text=node(clock,'TimeText',x=1+dx,y=1+dy,width=70,height=20,format='hh:mm',hourFormat='24',align='CENTER')
            outlined=bool(dx or dy)
            if outlined:node(text,'Variant',mode='AMBIENT',target='alpha',value=0)
            color=('#222A29' if fg=='#F0F0E7' else '#F0F0E7') if outlined else fg
            node(text,'Font',family='barlow_regular',size=17,color=color)

def digital_configuration(root,strings):
    from generate import node
    node(root.find('UserConfigurations'),'BooleanConfiguration',id='DigitalTime',displayName='digital_time',screenReaderText='digital_time',defaultValue='TRUE')
    node(strings,'string',name='digital_time').text='Цифровое время'

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
    from hand_updates import apply as update_requested_hands
    update_requested_hands(root)
    return source
