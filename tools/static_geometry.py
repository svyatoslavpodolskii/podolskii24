"""Build-time baking of repeated monochrome geometry; no runtime Python.

Fonts, sector masks, conditions, hands, complications and AOD remain native.
Shared white masks are tinted by WFF, avoiding one bitmap per color/preset.
The development manifest permits exact expansion for geometry contract tests.
"""
import copy
import hashlib
import json
import math
import re
import xml.etree.ElementTree as E
from pathlib import Path
from PIL import Image
from generate import ROOT, RES

MANIFEST=ROOT/'docs/optimization/geometry-sources.json'

def canonical(el):
    el=copy.deepcopy(el)
    for n in el.iter():
        if n.text is not None and not n.text.strip():n.text=None
        n.tail=None
    return E.tostring(el,encoding='unicode')

def optimize(root):
    from render import render
    sources={};bundles={};assets={};cache={};replaced=0
    # Manual hand selection is independent of the dial. Store one identical
    # body per background (plus Aviator's distinct proportions), rather than
    # parsing the same 21 choices separately for every dial.
    from generate import DEFAULT_HANDS,selection
    hand_root=root.find('.//Group[@name="interactive_hands"]')
    hands_design_source=canonical(hand_root)
    bodies={}
    for compare in hand_root.findall('Condition/Compare'):
        body=compare.find('Group');name=body.get('name')
        style,bg=name[6:].rsplit('_',1)
        for expression in body.findall('.//Expressions/Expression'):
            value=expression.text or ''
            match=re.match(r'^\[CONFIGURATION.HandStyle\] == "([^"]+)"',value)
            if not match:continue
            kind=match[1];defaults=[s for s,k in DEFAULT_HANDS.items() if k==kind]
            expression.text=selection(HandStyle=kind)
            if defaults:expression.text+=' || ('+selection(HandStyle='auto')+' && ('+' || '.join(selection(style=s) for s in defaults)+'))'
        body.set('name','hands_shared_'+('aviator_' if style=='aviator' else 'common_')+bg)
        key=('aviator' if style=='aviator' else 'common',bg)
        value=canonical(body)
        if key in bodies:assert bodies[key]['source']==value,'Different hand geometry cannot be merged'
        bodies.setdefault(key,{'source':value,'styles':[]})['styles'].append(style)
    for child in list(hand_root):
        if child.tag=='Condition':hand_root.remove(child)
    from generate import condition
    for (_,bg),item in bodies.items():
        expr='('+selection(background=bg)+') && ('+' || '.join(selection(style=s) for s in item['styles'])+')'
        condition(hand_root,expr).append(E.fromstring(item['source']))
    from usability import apply
    usability=apply(root,canonical)
    # Smaller editor thumbnails have no effect on the actual dial artwork.
    uc=root.find('UserConfigurations');config_design_source=canonical(uc)
    for option in uc.iter():
        name=option.get('icon')
        if not name:continue
        source=RES/'drawable-nodpi'/f'{name}.png'
        target='editor_'+name
        with Image.open(source) as im:im.resize((144,144),Image.Resampling.LANCZOS).save(source.with_name(target+'.png'),optimize=True)
        option.set('icon',target)
    def bake_bundle(parent):
        selected=[c for c in parent if c.get('renderMode')!='MASK']
        if not any(e.tag=='PartText' and e.get('name','').startswith(('hour_number_','minute_label_')) for e in selected):return False
        if any(e.tag=='Condition' for c in selected for e in c.iter()):return False
        original=E.Element('Group',x='0',y='0',width='432',height='432')
        for child in selected:original.append(copy.deepcopy(child))
        colors={n.get('color') for n in original.iter() if n.get('color')}
        if len(colors)!=1:return False
        assert not original.findall('.//Transform')
        mono=copy.deepcopy(original)
        for n in mono.iter():
            n.attrib.pop('name',None)
            if 'color' in n.attrib:n.set('color','#FFFFFF')
        key='bundle_'+hashlib.sha256(canonical(mono).encode()).hexdigest()[:20]
        if key not in cache:
            picture=render('instrument','white',subtree=mono,transparent=True)
            box=picture.getbbox();assert box
            l,t,r,b=box;box=(max(0,l-1),max(0,t-1),min(432,r+1),min(432,b+1))
            picture=picture.crop(box);name='geometry_'+hashlib.sha256(str(picture.size).encode()+picture.tobytes()).hexdigest()[:20]
            path=RES/'drawable-nodpi'/f'{name}.png';picture.save(path,optimize=True)
            assets[name]={'size':list(picture.size),'rgba_bytes':picture.width*picture.height*4,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
            cache[key]=(name,box)
        name,(l,t,r,b)=cache[key]
        source=canonical(original);sid=hashlib.sha256(source.encode()).hexdigest()[:20];bundles[sid]=source
        index=list(parent).index(selected[0])
        for child in selected:parent.remove(child)
        image=E.Element('PartImage',name='bundle_'+sid,x=str(l),y=str(t),width=str(r-l),height=str(b-t),tintColor=next(iter(colors)))
        E.SubElement(image,'Image',resource=name);parent.insert(index,image)
        return True
    def walk(parent,ambient=False):
        nonlocal replaced
        for original in list(parent):
            name=original.get('name','')
            if ambient or name=='ambient':continue
            if original.tag in ('Compare','Group') and bake_bundle(original):continue
            # Four divider lines/arcs are cheaper as native geometry than a
            # nearly empty full-dial texture; bake only dense repeated tracks.
            target=name=='hour_and_subhour_ticks' or name=='minute_track_ticks' or (name.startswith('divider_') and original.tag=='PartDraw' and not original.get('renderMode'))
            if not target:walk(original);continue
            assert not original.findall('.//Transform')
            assert not original.findall('.//PartText')
            colors={e.get('color') for e in original.iter() if e.get('color')}
            assert len(colors)==1,(name,colors)
            color=next(iter(colors));mono=copy.deepcopy(original)
            alpha=mono.attrib.pop('alpha',None)
            for el in mono.iter():
                el.attrib.pop('name',None)
                if 'color' in el.attrib:el.set('color','#FFFFFF')
            key=hashlib.sha256(canonical(mono).encode()).hexdigest()[:20]
            if key not in cache:
                # BOX at 3x preserves thin strokes and does not introduce ringing.
                image=render('instrument','white',subtree=mono,transparent=True)
                bounds=image.getbbox();assert bounds is not None
                x0,y0,x1,y1=bounds
                bounds=(max(0,x0-1),max(0,y0-1),min(432,x1+1),min(432,y1+1))
                crop=image.crop(bounds)
                pixelkey=hashlib.sha256(str(crop.size).encode()+crop.tobytes()).hexdigest()[:20]
                resource='geometry_'+pixelkey
                path=RES/'drawable-nodpi'/f'{resource}.png'
                crop.save(path,optimize=True)
                assets[resource]={'size':list(crop.size),'rgba_bytes':crop.width*crop.height*4,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
                cache[key]=(resource,bounds)
            resource,(x0,y0,x1,y1)=cache[key]
            source=canonical(original);sid=hashlib.sha256(source.encode()).hexdigest()[:20]
            sources[sid]=source
            attrs=dict(name='baked_'+sid,x=str(x0),y=str(y0),width=str(x1-x0),height=str(y1-y0),tintColor=color)
            if alpha is not None:attrs['alpha']=alpha
            replacement=E.Element('PartImage',attrs);E.SubElement(replacement,'Image',resource=resource)
            index=list(parent).index(original);parent.remove(original);parent.insert(index,replacement);replaced+=1
    walk(root)
    # Delete only generator-owned stale assets within drawable-nodpi.
    for path in (RES/'drawable-nodpi').glob('geometry_*.png'):
        if path.stem not in assets:path.unlink()
    # Hoist byte-identical minute tracks out of the 18 dial branches. All native
    # text is retained, but parsed only once for each genuinely distinct track.
    active=root.find('.//Group[@name="interactive"]')
    shared={};lifted=[]
    for dial in list(active.iter('Group')):
        name=dial.get('name','')
        if not name.startswith('dial_'):continue
        for index,child in reversed(list(enumerate(list(dial)))):
            if child.tag!='Condition':continue
            if not any(g.get('name','') in ('minute_track_TicksOnly','minute_track_FiveMinuteLabels','minute_track_SputnikRing','minute_track_InstrumentRing') for g in child.iter('Group')):continue
            source=canonical(child);key=hashlib.sha256(source.encode()).hexdigest()[:20]
            shared.setdefault(key,{'source':source,'dials':[]})['dials'].append(name)
            lifted.append({'dial':name,'index':index,'key':key});dial.remove(child)
    container=E.SubElement(active,'Group',name='shared_minute_tracks',x='0',y='0',width='432',height='432',pivotX='.5',pivotY='.5')
    from generate import selection
    for item in shared.values():
        expr=[]
        for name in item['dials']:
            style,bg=name[5:].rsplit('_',1);expr.append('('+selection(style=style,background=bg)+')')
        condition=E.SubElement(container,'Condition');expressions=E.SubElement(condition,'Expressions')
        E.SubElement(expressions,'Expression',name='enabled').text=' || '.join(expr)
        E.SubElement(condition,'Compare',expression='enabled').append(E.fromstring(item['source']))
    trimmed_sources={};trimmed_assets={};trim_cache={}
    for part in list(root.iter('PartImage')):
        image=part.find('Image')
        if image is None:continue
        resource=image.get('resource','')
        if resource.startswith(('geometry_','[')):continue
        path=RES/'drawable-nodpi'/f'{resource}.png'
        if not path.is_file():continue
        if resource not in trim_cache:
            with Image.open(path) as opened:
                bitmap=opened.convert('RGBA');bbox=bitmap.getbbox()
                assert bbox is not None,resource
                l,t,r,b=bbox
                # WFF PartImage coordinates and sizes are integers. Align source
                # crops to complete logical pixels instead of rounding geometry.
                ux=bitmap.width//math.gcd(bitmap.width,int(part.get('width')))
                uy=bitmap.height//math.gcd(bitmap.height,int(part.get('height')))
                box=(max(0,(l-1)//ux*ux),max(0,(t-1)//uy*uy),min(bitmap.width,math.ceil((r+1)/ux)*ux),min(bitmap.height,math.ceil((b+1)/uy)*uy))
                trim_cache[resource]=(box,bitmap.size)
                if box==(0,0,*bitmap.size):continue
                cropped=bitmap.crop(box);new_name='trimmed_'+resource
                new_path=path.with_name(new_name+'.png');cropped.save(new_path,optimize=True)
                trimmed_assets[new_name]={'original':resource,'box':list(box),'size':list(cropped.size),'rgba_bytes':cropped.width*cropped.height*4,'sha256':hashlib.sha256(new_path.read_bytes()).hexdigest()}
        (l,t,r,b),(iw,ih)=trim_cache[resource]
        if (l,t,r,b)==(0,0,iw,ih):continue
        source=canonical(part)
        x,y=float(part.get('x',0)),float(part.get('y',0));w,h=float(part.get('width')),float(part.get('height'))
        px=x+w*float(part.get('pivotX','.5'));py=y+h*float(part.get('pivotY','.5'))
        nx,ny=x+l*w/iw,y+t*h/ih;nw,nh=(r-l)*w/iw,(b-t)*h/ih
        for key,value in dict(x=nx,y=ny,width=nw,height=nh).items():
            assert abs(value-round(value))<1e-8
            part.set(key,str(round(value)))
        part.set('pivotX',str((px-nx)/nw));part.set('pivotY',str((py-ny)/nh))
        image.set('resource','trimmed_'+resource)
        sid=hashlib.sha256(canonical(part).encode()).hexdigest();trimmed_sources[sid]=source
    # Annular masks have a large completely transparent center. Four disjoint
    # rectangles retain every pixel but avoid decoding that empty rectangle.
    tiles={};tile_records=[]
    for part in list(root.iter('PartImage')):
        image=part.find('Image')
        if image is None or not image.get('resource','').startswith('geometry_'):continue
        name=image.get('resource')
        if name not in tiles:
            with Image.open(RES/'drawable-nodpi'/f'{name}.png') as source:
                source=source.convert('RGBA');cx,cy=source.width//2,source.height//2
                lo,hi=0,min(cx,cy)
                while lo<hi:
                    radius=(lo+hi+1)//2
                    if source.getchannel('A').crop((cx-radius,cy-radius,cx+radius,cy+radius)).getbbox() is None:lo=radius
                    else:hi=radius-1
                if lo<40:tiles[name]=None;continue
                l,t,r,b=cx-lo,cy-lo,cx+lo,cy+lo
                rectangles=[(0,0,source.width,t),(0,b,source.width,source.height),(0,t,l,b),(r,t,source.width,b)]
                pieces=[]
                for box in rectangles:
                    crop=source.crop(box)
                    if crop.getbbox() is None:continue
                    piece='geometry_'+hashlib.sha256(str(crop.size).encode()+crop.tobytes()).hexdigest()[:20]
                    path=RES/'drawable-nodpi'/f'{piece}.png';crop.save(path,optimize=True)
                    assets[piece]={'size':list(crop.size),'rgba_bytes':crop.width*crop.height*4,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
                    pieces.append((piece,box))
                rebuilt=Image.new('RGBA',source.size)
                for piece,box in pieces:
                    with Image.open(RES/'drawable-nodpi'/f'{piece}.png') as crop:rebuilt.paste(crop,(box[0],box[1]))
                assert rebuilt.tobytes()==source.tobytes(),'Static mask tiling lost pixels'
                tiles[name]=pieces
        if not tiles[name]:continue
        parent=next(p for p in root.iter() if part in list(p));index=list(parent).index(part)
        group=E.Element('Group',name=part.get('name',''),x='0',y='0',width='432',height='432')
        if part.get('alpha'):group.set('alpha',part.get('alpha'))
        for piece,box in tiles[name]:
            l,t,r,b=box
            child=E.SubElement(group,'PartImage',x=str(int(part.get('x'))+l),y=str(int(part.get('y'))+t),width=str(r-l),height=str(b-t),tintColor=part.get('tintColor'))
            E.SubElement(child,'Image',resource=piece)
        parent.remove(part);parent.insert(index,group);tile_records.append(name)
    aliases={};seen={}
    for name in sorted({e.get(a) for e in root.iter() for a in ('resource','icon') if e.get(a)}):
        path=RES/'drawable-nodpi'/f'{name}.png'
        if not path.is_file():continue
        with Image.open(path) as bitmap:
            bitmap=bitmap.convert('RGBA');key=(bitmap.size,hashlib.sha256(bitmap.tobytes()).hexdigest())
        if key in seen:aliases[name]=seen[key]
        else:seen[key]=name
    for el in root.iter():
        for attr in ('resource','icon'):
            if el.get(attr) in aliases:el.set(attr,aliases[el.get(attr)])
    from runtime_scene import apply as improve_runtime_scene
    usability['runtime_scene_source']=improve_runtime_scene(root,canonical)
    used={e.get(a) for e in root.iter() for a in ('resource','icon') if e.get(a)}|{'preview'}
    assets={name:info for name,info in assets.items() if name in used}
    for path in (RES/'drawable-nodpi').glob('trimmed_*.png'):
        if path.stem not in trimmed_assets:path.unlink()
    runtime_assets={p.stem:p for p in (RES/'drawable-nodpi').glob('*.png') if p.stem in used}
    decoded=sum(Image.open(p).width*Image.open(p).height*4 for p in runtime_assets.values())
    assert decoded<=40_211_072,'Decoded runtime PNG memory exceeds the original project'
    MANIFEST.parent.mkdir(exist_ok=True)
    MANIFEST.write_text(json.dumps({**usability,'asset_aliases':aliases,'hands_design_source':hands_design_source,'config_design_source':config_design_source,'bundles':bundles,'sources':sources,'assets':assets,'replaced':replaced,'lifted':lifted,'shared':shared,'trimmed_sources':trimmed_sources,'trimmed_assets':trimmed_assets,'runtime_png_names':sorted(runtime_assets),'runtime_png_rgba_bytes':decoded},ensure_ascii=False,indent=2),encoding='utf-8')
    print('Runtime PNG decoded upper bound:',decoded,'bytes; losslessly cropped assets:',len(trimmed_assets))
    print('Static geometry:',replaced,'subtrees;',len(assets),'shared masks;',sum(a['rgba_bytes'] for a in assets.values()),'decoded RGBA bytes')
    return root

def expanded(root):
    """Development-only inversion; never included in the APK."""
    manifest=json.loads(MANIFEST.read_text(encoding='utf-8'))
    root=copy.deepcopy(root)
    if manifest.get('runtime_scene_source'):
        current=root.find('Scene');index=list(root).index(current)
        root.remove(current);root.insert(index,E.fromstring(manifest['runtime_scene_source']))
    if manifest.get('hands_design_source'):
        scene=root.find('Scene');current=scene.find('Group[@name="interactive_hands"]')
        index=list(scene).index(current);scene.remove(current);scene.insert(index,E.fromstring(manifest['hands_design_source']))
        current=root.find('UserConfigurations');index=list(root).index(current);root.remove(current);root.insert(index,E.fromstring(manifest['config_design_source']))
        for original in manifest.get('slot_design_sources',[]):
            source=E.fromstring(original);current=scene.find('ComplicationSlot[@slotId="'+source.get('slotId')+'"]')
            index=list(scene).index(current);scene.remove(current);scene.insert(index,source)
    for parent in root.iter():
        for child in list(parent):
            if child.tag not in ('PartImage','PartText'):continue
            sid=hashlib.sha256(canonical(child).encode()).hexdigest()
            source=manifest.get('label_design_sources',{}).get(sid) or manifest.get('trimmed_sources',{}).get(sid)
            if source:
                index=list(parent).index(child);parent.remove(child);parent.insert(index,E.fromstring(source))
    active=root.find('.//Group[@name="interactive"]')
    container=active.find('Group[@name="shared_minute_tracks"]')
    if container is not None:
        active.remove(container)
        for item in sorted(manifest['lifted'],key=lambda i:(i['dial'],i['index'])):
            dial=active.find('.//Group[@name="'+item['dial']+'"]')
            dial.insert(item['index'],E.fromstring(manifest['shared'][item['key']]['source']))
    def walk(parent):
        for child in list(parent):
            if child.get('name','').startswith('bundle_'):
                source=E.fromstring(manifest['bundles'][child.get('name')[7:]])
                index=list(parent).index(child);parent.remove(child)
                for i,item in enumerate(list(source)):parent.insert(index+i,item)
            elif child.get('name','').startswith('baked_'):
                source=E.fromstring(manifest['sources'][child.get('name')[6:]])
                index=list(parent).index(child);parent.remove(child);parent.insert(index,source)
            else:walk(child)
    walk(root);return root

def design_scene():
    root=E.parse(RES/'raw/watchface.xml').getroot()
    return expanded(root) if root.find('.//PartImage[@name]') is not None and any(e.get('name','').startswith('baked_') for e in root.iter('PartImage')) else root

if __name__=='__main__':
    path=RES/'raw/watchface.xml';root=optimize(E.parse(path).getroot())
    for el in root.iter():el.tail='\n'
    E.ElementTree(root).write(path,encoding='utf-8',xml_declaration=True)
