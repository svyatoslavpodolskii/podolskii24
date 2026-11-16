"""Structural sharing and provably redundant clipping removal.

No rasterization or lower resolution assets. Complex predicates and necessary
light/dark clipping are retained. Only disjoint branches may be coalesced.
"""
import copy
import itertools
import re
import xml.etree.ElementTree as E
from functools import lru_cache

def paint_key(element):
    from static_geometry import canonical
    element=copy.deepcopy(element)
    for n in element.iter():n.attrib.pop('name',None)
    return canonical(element)

def selector(element):
    if element.tag=='Group' and element.get('name')=='native_selector' and len(element)==1:
        return selector(element[0])
    if element.tag=='Condition':
        expressions=element.findall('Expressions/Expression');compares=element.findall('Compare')
        if len(expressions)!=1 or len(compares)!=1 or element.find('Default') is not None:return None
        payload=list(compares[0])
        if len(payload)==1:return expressions[0].text,payload[0]
    if element.tag=='ListConfiguration' and len(element)==1:
        option=element[0]
        if len(option)==1:return f'[CONFIGURATION.{element.get("id")}] == "{option.get("id")}"',option[0]
    return None

def coalesce(root):
    """Merge identical paint only inside runs of mutually exclusive selectors.

    Checking the whole run protects painter order, including intervening items.
    Predicates are evaluated over their complete finite configuration domains.
    """
    domains={c.get('id'):tuple(o.get('id') for o in c) for c in root.find('UserConfigurations') if c.tag=='ListConfiguration'}
    # These controls are appended to the user schema after scene optimization.
    from personalization import LISTS
    domains.update({k:tuple(options) for k,(_,options) in LISTS.items()})
    domains.update({key:('FALSE','TRUE') for key in ('minute','DigitalTime','AodMinute','Seconds')})
    def compile_guard(expression):
        refs=re.findall(r'\[([^]]+)\]',expression)
        if any(not r.startswith('CONFIGURATION.') or r[14:] not in domains for r in refs):return None
        keys=tuple(sorted(set(r[14:] for r in refs)))
        code=re.sub(r'\[CONFIGURATION\.(\w+)\]',lambda m:f'c[{m[1]!r}]',expression)
        code=code.replace('&&',' and ').replace('||',' or ')
        if '?' in code:return None
        try:return keys,compile(code,'<WFF finite selection>','eval')
        except SyntaxError:return None
    @lru_cache(maxsize=None)
    def disjoint(a,b):
        ga,gb=compile_guard(a),compile_guard(b)
        if ga is None or gb is None:return False
        keys=tuple(sorted(set(ga[0])|set(gb[0])))
        count=1
        for k in keys:count*=len(domains[k])
        if count>5000:return False
        for values in itertools.product(*(domains[k] for k in keys)):
            c=dict(zip(keys,values))
            if eval(ga[1],{'__builtins__':{}},{'c':c}) and eval(gb[1],{'__builtins__':{}},{'c':c}):return False
        return True
    removed=0
    from generate import condition
    for parent in list(root.find('Scene').iter()):
        children=list(parent);runs=[];run=[]
        for child in children+[None]:
            found=selector(child) if child is not None else None
            if found:run.append((child,*found))
            else:
                if len(run)>1:runs.append(run)
                run=[]
        for run in runs:
            if not all(disjoint(a[1],b[1]) for a,b in itertools.combinations(run,2)):continue
            groups={}
            for child,guard,payload in run:groups.setdefault(paint_key(payload),[]).append((child,guard,payload))
            for cases in groups.values():
                if len(cases)<2:continue
                container=E.Element('temporary')
                branch=condition(container,' || '.join('('+g+')' for _,g,_ in cases))
                branch.append(cases[0][2])
                index=list(parent).index(cases[0][0])
                for child,_,_ in cases:parent.remove(child)
                parent.insert(index,container[0]);removed+=len(cases)-1
    return removed

def complication_templates(root):
    """One native template per slot/type, rather than three background copies."""
    from generate import node
    merged=0
    for complication in root.findall('Scene/ComplicationSlot/Complication'):
        cases=[]
        for branch in list(complication):
            found=selector(branch)
            if found and found[1].tag=='Group':cases.append((branch,found[1]))
        if len(cases)!=3:continue
        groups=[g for _,g in cases]
        # Match white/ivory/black by their original stable names.
        groups.sort(key=lambda g:('white','ivory','black').index(g.get('name').rsplit('_',1)[1]))
        first=groups[0];triples=list(zip(*(list(g.iter()) for g in groups)))
        assert all(len(list(g.iter()))==len(triples) for g in groups)
        for a,b,c in triples:
            assert a.tag==b.tag==c.tag and a.text==b.text==c.text
            keys=set(a.attrib)|set(b.attrib)|set(c.attrib)
            assert all(a.get(k)==b.get(k)==c.get(k) for k in keys-{'name','color','tintColor'})
        # The circle fill needs its own tintable PartDraw: Fill itself does not
        # accept transforms in WFF v4. Leave the border in the original draw.
        backing=first.find('PartDraw');circle=backing.find('Ellipse')
        background=node(first,'PartDraw',x=0,y=0,width=56,height=56)
        backing.remove(circle);background.append(circle)
        if not len(backing):first.remove(backing)
        first.remove(background);first.insert(0,background)
        for nodes in triples:
            a=nodes[0]
            for attribute in ('color','tintColor'):
                colors=[n.get(attribute) for n in nodes]
                if colors[0] is None or len(set(colors))==1:continue
                expr=f'[CONFIGURATION.background] == "white" ? {colors[0]} : [CONFIGURATION.background] == "ivory" ? {colors[1]} : {colors[2]}'
                target=background if a is circle.find('Fill') else a
                node(target,'Transform',target='tintColor' if a is circle.find('Fill') else attribute,value=expr)
        index=min(list(complication).index(branch) for branch,_ in cases)
        for branch,_ in cases:complication.remove(branch)
        first.set('name',first.get('name').rsplit('_',1)[0]+'_shared')
        complication.insert(index,first);merged+=2
    return merged

def shared_regular_scales(root):
    """Store each style's uncolored scale once, with a native ink palette."""
    from generate import node,condition,STYLES
    active=root.find('Scene/Group[@name="interactive"]')
    shared=E.Element('Group',name='shared_regular_scales',x='0',y='0',width='432',height='432')
    enabled=E.SubElement(condition(shared,'[CONFIGURATION.sectors] != "color"'),'Group',name='regular_scales',x='0',y='0',width='432',height='432')
    for style in STYLES:
        faces=[active.find(f'.//Group[@name="dial_{style}_{b}"]') for b in ('white','black')]
        regular=[face.find('.//Group[@name="regular_scale"]') for face in faces]
        a,b=regular
        pairs=list(zip(list(a.iter()),list(b.iter())))
        assert len(list(a.iter()))==len(list(b.iter()))
        for x,y in pairs:
            assert x.tag==y.tag and x.text==y.text
            assert all(x.get(k)==y.get(k) for k in (set(x.attrib)|set(y.attrib))-{'name','color','tintColor'})
            for attr in ('color','tintColor'):
                if x.get(attr)==y.get(attr):continue
                assert x.tag in ('PartImage','Stroke','Font'),(x.tag,attr)
                node(x,'Transform',target=attr,value=f'[CONFIGURATION.background] == "black" ? {y.get(attr)} : {x.get(attr)}')
        condition(enabled,f'[CONFIGURATION.style] == "{style}"').append(a)
        for face in faces:
            branch=next(child for child in face if any(g.get('name')=='regular_scale' for g in child.iter('Group')))
            face.remove(branch)
    index=list(active).index(active.find('Group[@name="shared_period_details_under"]'))+1
    active.insert(index,shared)
    return len(STYLES)

def remove_redundant_masks(root):
    """Drop full-disk masks only when every painted pixel is safely inside.

    Restrict proof to static image-only bodies with no translation or scaling.
    Preserve all actual sector clipping, small-image circles and text clipping.
    """
    from generate import RES
    from PIL import Image
    from personalization import LISTS
    from render import evaluate
    @lru_cache(maxsize=None)
    def inside(resource,x,y,w,h,sx=1,sy=1,px=.5,py=.5):
        with Image.open(RES/'drawable-nodpi'/(resource+'.png')) as im:
            alpha=im.getchannel('A');unit_x=w/im.width;unit_y=h/im.height
            pivot_x=x+w*px;pivot_y=y+h*py
            for py in range(im.height):
                row=alpha.crop((0,py,im.width,py+1)).getbbox()
                if row is None:continue
                yy=pivot_y+(y+(py+.5)*unit_y-pivot_y)*sy-216
                for column in (row[0],row[2]-1):
                    xx=pivot_x+(x+(column+.5)*unit_x-pivot_x)*sx-216
                    if xx*xx+yy*yy>214**2:return False
        return True
    removed=0
    for group in root.findall('.//Group'):
        for mask in list(group.findall('PartDraw[@renderMode="MASK"]')):
            arcs=mask.findall('Arc')
            if len(arcs)!=4 or len(list(mask))!=4:continue
            if any(a.get('centerX')!='216' or a.get('centerY')!='216' or a.get('width')!='216' or a.find('Stroke').get('thickness')!='216' for a in arcs):continue
            spans=sorted((float(a.get('startAngle'))%360,(float(a.get('endAngle'))-float(a.get('startAngle')))) for a in arcs)
            starts=sorted(a for a,b in spans)
            if any(b!=90 for a,b in spans) or any(abs((starts[(i+1)%4]-starts[i])%360-90)>.001 for i in range(4)):continue
            paint=[n for child in group if child is not mask for n in child.iter()]
            if any(n.tag not in ('Group','PartImage','Image','ListConfiguration','ListOption','Condition','Expressions','Expression','Compare','Transform') for n in paint):continue
            if any(n.tag=='Group' and any(float(n.get(k,default))!=float(default) for k,default in (('x',0),('y',0),('angle',0),('scaleX',1),('scaleY',1))) for n in paint):continue
            images=[n for n in paint if n.tag=='PartImage']
            if not images:continue
            if any(n.tag=='Group' and n.findall('Transform') for n in paint):continue
            safe=True
            for n in images:
                scales={k:float(n.get(k,1)) for k in ('scaleX','scaleY')}
                for transform in n.findall('Transform'):
                    target=transform.get('target')
                    if target=='tintColor':continue
                    expr=transform.get('value');keys=tuple(sorted(set(re.findall(r'\[CONFIGURATION\.(\w+)\]',expr))))
                    if target not in scales or not keys or any(k not in LISTS for k in keys):safe=False;break
                    values=[float(evaluate(expr,dict(zip(keys,combination)),12,0)) for combination in itertools.product(*(LISTS[k][1] for k in keys))]
                    if min(values)<=0:safe=False;break
                    scales[target]=max(values)
                if not safe:break
                safe=inside(n.find('Image').get('resource'),*(float(n.get(k)) for k in ('x','y','width','height')),scales['scaleX'],scales['scaleY'],float(n.get('pivotX',.5)),float(n.get('pivotY',.5)))
                if not safe:break
            if safe:
                group.remove(mask);removed+=1
    return removed

def parameterized_periods(root):
    """Four sector paints and eight labels serve all style/background presets.

    The two label layers keep their original position in painter order: below
    colored scales, above uncolored scales. Coordinates reproduce the generator's
    rounding, including its optical inward correction with minute tracks.
    """
    import math
    from generate import node,condition,draw,wedge,PRESETS,STYLES,BACKGROUNDS,palette,ink_on,INK,PAPER,angle,point,text
    active=root.find('Scene/Group[@name="interactive"]')
    fills=active.find('Group[@name="shared_period_fills"]')
    for child in list(fills):
        if child.tag!='Variant':fills.remove(child)
    paint=draw(condition(fills,'[CONFIGURATION.sectors] == "color"'),name='parameterized_period_fills')
    for i,start in enumerate(PRESETS['quarter']):
        arc=wedge(paint,start,start+6,palette('classic','white')[i])
        for attr,value in (('startAngle',angle(PRESETS['shifted_back_1_hour'][i])),('endAngle',angle(PRESETS['shifted_back_1_hour'][i])+90)):
            node(arc,'Transform',target=attr,value=f'[CONFIGURATION.boundaries] == "shifted_back_1_hour" ? {value} : {arc.get(attr)}')
        colors=[palette('classic',b)[i] for b in ('white','ivory','black')]
        special=palette('instrument','black')[i]
        node(arc.find('Stroke'),'Transform',target='color',value=f'[CONFIGURATION.background] == "white" ? {colors[0]} : [CONFIGURATION.background] == "ivory" ? {colors[1]} : [CONFIGURATION.style] == "instrument" ? {special} : {colors[2]}')
    removed=0
    for mode,layer in (('color','shared_period_details_under'),('labels','shared_period_details')):
        container=active.find(f'Group[@name="{layer}"]')
        for parent in list(container.iter()):
            for child in list(parent):
                if child.tag=='PartText' and child.get('name','').startswith('period_label_'):
                    parent.remove(child);removed+=1
        graphical={'PartText','PartImage','PartDraw','PartAnimatedImage','AnalogClock','DigitalClock'}
        for parent in reversed(list(container.iter())):
            for child in list(parent):
                if child.tag in ('Group','Condition','ListConfiguration') and not any(n.tag in graphical for n in child.iter()):parent.remove(child)
        labels=node(condition(container,f'[CONFIGURATION.sectors] == "{mode}"'),'Group',name='parameterized_period_labels_'+mode,x=0,y=0,width=432,height=432)
        for i,label in enumerate(('УТРО','ДЕНЬ','ВЕЧЕР','НОЧЬ')):
            coordinates={}
            for preset,bounds in PRESETS.items():
                a=angle(bounds[i]+3)
                for classic in (False,True):
                    for minutes in (False,True):
                        radius=(116 if minutes else 128) if classic else 149
                        cx,cy=point(a,radius);x,y=round(cx-27),round(cy-10)
                        if minutes:
                            old_radius=math.hypot(x+27-216,y+10-216)
                            x=round(216+(x+27-216)*110/old_radius-27)
                            y=round(216+(y+10-216)*110/old_radius-10)
                        coordinates[(preset,classic,minutes)]=(x,y,a if a<=90 or a>=270 else a-180)
            p=text(labels,216,216,label,INK,16,w=54,h=20,name='period_label_'+label)
            for j,axis in enumerate(('x','y','angle')):
                cases=[]
                for (preset,classic,minutes),values in coordinates.items():
                    guard=f'[CONFIGURATION.boundaries] == "{preset}" && [CONFIGURATION.style] '+('==' if classic else '!=')+' "instrument_classic" && [CONFIGURATION.MinuteTrackStyle] '+('!=' if minutes else '==')+' "None"'
                    cases.append((guard,values[j]))
                expr=''.join(guard+' ? '+str(value)+' : ' for guard,value in cases[:-1])+str(cases[-1][1])
                # Angle does not depend on radius or minute-track settings.
                if axis=='angle':expr=f'[CONFIGURATION.boundaries] == "quarter" ? {coordinates[("quarter",False,False)][2]} : {coordinates[("shifted_back_1_hour",False,False)][2]}'
                node(p,'Transform',target=axis,value=expr)
            # Prove the compact luminance rule against every original palette.
            for style,bg in itertools.product(STYLES,BACKGROUNDS):
                expected=PAPER if bg=='black' or (mode=='color' and i==3) else INK
                assert ink_on(palette(style,bg)[i] if mode=='color' else BACKGROUNDS[bg])==expected
            color=f'[CONFIGURATION.background] == "black" ? {PAPER} : '+(PAPER if mode=='color' and i==3 else INK)
            node(p.find('Text/Font'),'Transform',target='color',value=color)
    return removed

def apply(root):
    labels=parameterized_periods(root)
    # Share identical light-background branches first, then detach the common
    # uncolored scale. A second pass can merge newly identical colored branches.
    before=coalesce(root)
    scales=shared_regular_scales(root)
    return dict(period_labels_removed=labels,regular_scale_templates=scales,
                complication_copies_removed=complication_templates(root),
                redundant_masks_removed=remove_redundant_masks(root),
                equivalent_branches_removed=before+coalesce(root))
