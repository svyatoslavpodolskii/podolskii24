"""Native scene/time/contrast contracts. Does not replace a Wear OS device test."""
import itertools
import math
import re
import unittest
import xml.etree.ElementTree as E
from generate import ROOT,RES,STYLES,BACKGROUNDS,PRESETS,MODES,DIVIDERS,HAND_STYLES,DEFAULT_HANDS,INK,PAPER,angle,point,period,palette,ink_on,contrast

def value(expr,h,m):return eval(expr.replace('[HOUR_0_23]',str(h)).replace('[MINUTE]',str(m)),{'__builtins__':{}},{})
class WatchFaceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Geometry contracts inspect the exact inverse of the baked native tree.
        # test_optimization separately checks the deployed tree and bitmaps.
        from static_geometry import design_scene
        cls.xml=design_scene()
    def test_native_source_size_budget(self):
        self.assertLessEqual((RES/'raw/watchface.xml').stat().st_size,10_000_000)
    def test_user_style_strings_and_resource_links(self):
        strings={}
        for path in RES.glob('values*/strings.xml'):
            for item in E.parse(path).getroot().iter():
                if item.tag in ('string','item') and item.text:
                    # Current labels have literal percents only, no placeholders.
                    self.assertNotIn('%',item.text.replace('%%',''),str(path)+': '+str(item.get('name')))
                if item.tag=='string':strings[item.get('name')]=''.join(item.itertext())
        self.assertEqual(strings['Compact'] % (), 'Compact — 92%')
        self.assertEqual(strings['Large'] % (), 'Large — 106%')
        for item in self.xml.iter():
            for attr in ('displayName','screenReaderText'):
                if attr in item.attrib:self.assertIn(item.get(attr),strings)
            for attr in ('icon','resource','family'):
                if attr not in item.attrib:continue
                value=item.get(attr)
                self.assertTrue(value and value.strip(),(item.tag,attr))
                if value.startswith('['):continue  # dynamic complication image
                folder='font' if attr=='family' else 'drawable*'
                self.assertTrue(list(RES.glob(folder+'/'+value+'.*')),(item.tag,attr,value))
    def test_hour_math_in_all_styles_backgrounds_and_aod(self):
        ts=self.xml.findall('.//Group[@name="hour"]/Transform')+self.xml.findall('.//Group[@name="instrument_classic_hour_front"]/Transform')+self.xml.findall('.//Group[@name="hour_aod"]/Transform')
        self.assertEqual(len(ts),len(STYLES)*6+1)
        for t in ts:
            for h,expected in ((0,180),(3,225),(6,270),(9,315),(12,0),(15,45),(18,90),(21,135)):
                self.assertAlmostEqual(value(t.get('value'),h,0)%360,expected)
            self.assertAlmostEqual(value(t.get('value'),12,30)%360,7.5)
            for h,m in itertools.product(range(24),range(60)):self.assertAlmostEqual(value(t.get('value'),h,m)%360,angle(h,m))
    def test_minute_math_and_pivots(self):
        ts=self.xml.findall('.//Group[@name="minute"]/Transform');self.assertEqual(len(ts),len(STYLES)*3)
        for t in ts:
            for m in range(60):self.assertEqual(value(t.get('value'),17,m),m*6)
        for g in self.xml.findall('.//Group[@name="hour"]')+self.xml.findall('.//Group[@name="minute"]'):
            self.assertEqual((float(g.get('pivotX')),float(g.get('pivotY'))),(.5,.5))
    def test_boundaries_and_every_minute_period(self):
        # Explicit quadrant contract: midnight is down, not up.
        self.assertEqual([period(h,0,'quarter') for h in (3,9,15,21)],['night','morning','day','evening'])
        for h,signs in ((3,(-1,1)),(9,(-1,-1)),(15,(1,-1)),(21,(1,1))):
            x,y=point(angle(h),100)
            self.assertEqual((1 if x>216 else -1,1 if y>216 else -1),signs)
        for preset,bounds in PRESETS.items():
            for i,h in enumerate(bounds):
                self.assertEqual(period(h%24,0,preset),('morning','day','evening','night')[i])
                self.assertEqual(period((h-1)%24,59,preset),('morning','day','evening','night')[(i-1)%4])
            counts={p:0 for p in ('morning','day','evening','night')}
            for h,m in itertools.product(range(24),range(60)):counts[period(h,m,preset)]+=1
            self.assertEqual(set(counts.values()),{360})
        self.assertEqual(period(23,0,'shifted_back_1_hour'),'night')
        self.assertEqual(period(0,0,'quarter'),'night')
    def test_sector_geometry_and_non_hand_dividers(self):
        for style,bg,preset,mode in itertools.product(STYLES,BACKGROUNDS,PRESETS,('lines','labels','color')):
            g=self.xml.find(f'.//Group[@name="{style}_{bg}_{preset}_{mode}"]');self.assertIsNotNone(g)
            if mode=='color':
                arcs=g.findall('PartDraw[@name="sector_fills"]/Arc');self.assertEqual(len(arcs),4)
                for a,h in zip(arcs,PRESETS[preset]):
                    self.assertEqual(float(a.get('startAngle')),angle(h))
                    self.assertEqual(float(a.get('endAngle'))-float(a.get('startAngle')),90)
                    self.assertEqual(float(a.get('width')),216)
                    self.assertEqual(float(a.find('Stroke').get('thickness')),216)
            else:
                lines=g.findall('.//PartDraw[@name="divider_micro"]/Line');self.assertEqual(len(lines),4)
                for l,h in zip(lines,PRESETS[preset]):
                    a=(float(l.get('startX'))-216,float(l.get('startY'))-216)
                    b=(float(l.get('endX'))-216,float(l.get('endY'))-216)
                    self.assertAlmostEqual(math.hypot(*a),138,places=3)
                    self.assertAlmostEqual(math.hypot(*b),157,places=3)
                    self.assertAlmostEqual(math.degrees(math.atan2(b[0],-b[1]))%360,angle(h),places=4)
    def test_adaptive_contrast_and_masks(self):
        for style,bg in itertools.product(STYLES,BACKGROUNDS):
            for color in palette(style,bg):self.assertGreaterEqual(contrast(ink_on(color),color),4.5)
            self.assertGreaterEqual(contrast(ink_on(BACKGROUNDS[bg]),BACKGROUNDS[bg]),4.5)
            for preset in PRESETS:
                g=self.xml.find(f'.//Group[@name="{style}_{bg}_{preset}_color"]')
                masks=g.findall('Group/PartDraw[@renderMode="MASK"]');self.assertIn(len(masks),(1,2))
                coverage=[]
                for mask in masks:
                    for a in mask.findall('Arc'):coverage.append(float(a.get('startAngle')))
                    # Both glyphs and marks are inside the same masked source group.
                self.assertEqual(sorted(coverage),sorted(angle(h) for h in PRESETS[preset]))
                labels=g.findall('PartText')
                for t,color in zip(labels,palette(style,bg)):
                    self.assertGreaterEqual(contrast(t.find('Text/Font').get('color'),color),4.5)
    def test_independent_native_settings(self):
        configs=self.xml.find('UserConfigurations')
        self.assertEqual({c.get('id'):c.get('defaultValue') for c in configs},{'style':'classic','background':'white','sectors':'none','boundaries':'quarter','dividers':'micro','HandStyle':'auto','MinuteTrackStyle':'None','HandSize':'Original','minute':'FALSE'})
        for id,values in (('style',STYLES),('background',BACKGROUNDS),('sectors',MODES),('boundaries',PRESETS),('dividers',DIVIDERS),('HandStyle',HAND_STYLES)):
            self.assertEqual([o.get('id') for o in configs.find(f'ListConfiguration[@id="{id}"]')],list(values))
        self.assertEqual(self.xml.findall('.//Scene//ListConfiguration'),[])
        for style,bg in itertools.product(STYLES,BACKGROUNDS):self.assertIsNotNone(self.xml.find(f'.//Group[@name="dial_{style}_{bg}"]'))
    def test_five_native_divider_geometries(self):
        for style,bg,preset in itertools.product(STYLES,BACKGROUNDS,PRESETS):
            g=self.xml.find(f'.//Group[@name="{style}_{bg}_{preset}_lines"]')
            for kind in DIVIDERS:
                d=g.find(f'.//PartDraw[@name="divider_{kind}"]');self.assertIsNotNone(d)
                if kind=='arc':
                    arcs=d.findall('Arc');self.assertEqual(len(arcs),4)
                    for a,h in zip(arcs,PRESETS[preset]):
                        self.assertEqual(float(a.get('startAngle')),angle(h)+3)
                        self.assertEqual(float(a.get('endAngle')),angle(h)+87)
                        self.assertEqual(float(a.get('width')),244)
                else:
                    inner={'micro':138,'radial':42,'full':0,'classic':119}[kind]
                    outer=157 if kind in ('micro','classic') else 158
                    for l,h in zip(d.findall('Line'),PRESETS[preset]):
                        for prefix,radius in (('start',inner),('end',outer)):
                            x=float(l.get(prefix+'X'))-216;y=float(l.get(prefix+'Y'))-216
                            self.assertAlmostEqual(math.hypot(x,y),radius,places=3)
                        x=float(l.get('endX'))-216;y=216-float(l.get('endY'))
                        self.assertAlmostEqual(math.degrees(math.atan2(x,y))%360,angle(h),places=4)
                    if kind=='full':self.assertLessEqual(int(d.get('alpha')),75)
    def test_all_native_configuration_selections_with_independent_hands(self):
        def active(el,config,names):
            if el.tag=='ComplicationSlot' or el.get('alpha')=='0':return
            if el.tag=='Condition':
                expressions={e.get('name'):e.text for e in el.findall('Expressions/Expression')}
                for cmp in el.findall('Compare'):
                    expr=re.sub(r'\[CONFIGURATION\.([^]]+)\]',lambda m:repr(config[m[1]]),expressions[cmp.get('expression')]).replace('&&',' and ').replace('||',' or ')
                    if eval(expr,{'__builtins__':{}},{}):
                        for child in cmp:active(child,config,names)
                        break
                return
            if el.get('name'):names.append(el.get('name'))
            if el.get('name')=='selected_hour_art':names.append('hour_resource:'+el.find('Image').get('resource'))
            if el.get('name','').startswith('original_hour_'):names.append('hour_resource:'+el.get('name'))
            for child in el:
                if child.tag not in ('Expressions','Expression','Variant','Transform','UserConfigurations'):active(child,config,names)
        for s,b,m,p,d,minute,hs in itertools.product(STYLES,BACKGROUNDS,MODES,PRESETS,DIVIDERS,('FALSE','TRUE'),HAND_STYLES):
            config=dict(style=s,background=b,sectors=m,boundaries=p,dividers=d,minute=minute,HandStyle=hs,MinuteTrackStyle='None',HandSize='Original');names=[]
            active(self.xml.find('Scene'),config,names)
            self.assertEqual([n for n in names if n.startswith('dial_')],[f'dial_{s}_{b}'])
            self.assertEqual('minute' in names,minute=='TRUE')
            found=[n for n in names if n in {'divider_'+v for v in DIVIDERS}]
            self.assertEqual(set(found),set() if m=='none' else {'divider_'+d})
            if m!='none':self.assertIn(f'{s}_{b}_{p}_{m}',names)
            chosen=DEFAULT_HANDS[s] if hs=='auto' else hs;tone='dark' if b=='black' else 'light'
            expected=f'hand_{chosen[7:]}_{tone}' if chosen.startswith('legacy_') else f'precision_hour_{chosen}_{tone}'
            if chosen.startswith('original_'):expected='original_hour_'+chosen[9:]
            if chosen=='bellross_photo':expected=f'instrument_classic_hour_{b}'
            if chosen=='instrument_classic_clean':expected=f'instrument_classic_clean_hour_{b}'
            self.assertEqual([n for n in names if n.startswith('hour_resource:')],['hour_resource:'+expected])
    def test_hand_defaults_and_artwork_pivots(self):
        self.assertEqual({k:DEFAULT_HANDS[k] for k in ('classic','minimal','sputnik','instrument')},{'classic':'needle','minimal':'sword','sputnik':'vintage','instrument':'instrument_refined'})
        for p in self.xml.findall('.//PartImage[@name="selected_hour_art"]')+self.xml.findall('.//PartImage[@name="selected_minute_art"]'):
            self.assertAlmostEqual(float(p.get('x'))+float(p.get('width'))*float(p.get('pivotX')),216,places=4)
            self.assertAlmostEqual(float(p.get('y'))+float(p.get('height'))*float(p.get('pivotY')),216,places=4)
    def test_aviator_has_all_four_cardinal_ticks(self):
        ticks=self.xml.find('.//Group[@name="dial_aviator_black"]//Group[@name="hour_and_subhour_ticks"]')
        self.assertIsNotNone(ticks)
        groups=ticks.findall('Group')
        self.assertEqual(len(groups),96)
        for angle_ in (0,90,180,270):
            self.assertTrue(any(float(g.get('angle'))==angle_ for g in groups))
    def test_minute_track_configuration_and_geometry(self):
        from generate import MINUTE_TRACKS,minute_track_art,instrument_tick_specs
        cfg=self.xml.find('UserConfigurations/ListConfiguration[@id="MinuteTrackStyle"]')
        self.assertEqual(cfg.get('defaultValue'),'None')
        self.assertEqual(tuple(o.get('id') for o in cfg),MINUTE_TRACKS)
        ticks=list(instrument_tick_specs())
        self.assertEqual(len(ticks),96)
        self.assertEqual(sum(i%4==0 for i in range(96)),24)
        for i,(a,inner,outer,w) in enumerate(ticks):
            self.assertEqual(a,i*3.75);self.assertEqual(outer,207);self.assertGreater(outer,inner);self.assertGreater(w,0)
        for kind in MINUTE_TRACKS[1:]:
            p=E.Element('Group');minute_track_art(p,kind,'#FFFFFF')
            lines=p.findall('PartDraw/Line');self.assertEqual(len(lines),60)
            for i,l in enumerate(lines):
                x,y=point(i*6,211)
                self.assertAlmostEqual(float(l.get('endX')),x,places=3);self.assertAlmostEqual(float(l.get('endY')),y,places=3)
            labels=p.findall('PartText');self.assertEqual(len(labels),0 if kind=='TicksOnly' else 12)
            for minute in (15,30,45,60):
                if kind=='TicksOnly':continue
                el=p.find(f'PartText[@name="minute_label_{minute}"]');x,y=point(minute*6,196)
                self.assertLessEqual(abs(float(el.get('x'))+12-x),.5)
                self.assertLessEqual(abs(float(el.get('y'))+8-y),.5)
        for s,b in itertools.product(STYLES,BACKGROUNDS):
            dial=self.xml.find(f'.//Group[@name="dial_{s}_{b}"]')
            tracks=[g for g in dial.findall('.//Group') if g.get('name','').startswith('minute_track_') and g.get('name')!='minute_track_contrast']
            self.assertEqual(len(tracks),4)
            for track in tracks:
                self.assertNotIn('CONFIGURATION.minute]',E.tostring(track,encoding='unicode'))
    def test_minute_track_visibility_across_settings(self):
        from generate import MINUTE_TRACKS
        from render import evaluate
        def active(el,config,found):
            if el.get('alpha')=='0':return
            if el.tag=='Condition':
                exprs={e.get('name'):e.text for e in el.findall('Expressions/Expression')}
                for cmp in el.findall('Compare'):
                    if evaluate(exprs[cmp.get('expression')],config,10,30):
                        for ch in cmp:active(ch,config,found)
                        return
                return
            name=el.get('name','')
            if name.startswith('minute_track_') and name!='minute_track_contrast':found.append(name);return
            if name=='selected_hour_art':found.append('hour');return
            if el.tag in ('PartDraw','PartText','PartImage','UserConfigurations','ComplicationSlot'):return
            for ch in el:active(ch,config,found)
        for s,b,mode,preset,minute,track in itertools.product(STYLES,BACKGROUNDS,MODES,PRESETS,('FALSE','TRUE'),MINUTE_TRACKS):
            config=dict(style=s,background=b,sectors=mode,boundaries=preset,minute=minute,MinuteTrackStyle=track,HandStyle='auto',dividers='micro',HandSize='Original')
            found=[];active(self.xml.find('Scene'),config,found)
            self.assertEqual(found.count('hour'),1)
            self.assertEqual([n for n in found if n.startswith('minute_track_')],[] if track=='None' else ['minute_track_'+track])
    def test_original_v1_draw_commands_are_preserved(self):
        from original_hands import artwork
        old=E.parse(ROOT/'docs/references/hands/original-v1-watchface.xml').getroot()
        for theme in ('white','black','sputnik','orange'):
            for minute in (False,True):
                p=E.Element('Group');artwork(p,theme,minute)
                source=old.find(f'.//Group[@name="hands_{theme}"]//Group[@name="{"minute" if minute else "hour"}"]')
                def commands(el):
                    return [(n.tag,dict(n.attrib)) for n in el.iter() if n.tag in ('Line','Stroke')]
                self.assertEqual(commands(source),commands(p))
    def test_instrument_classic_preserves_other_hands(self):
        from check_photo_hands import preservation
        self.assertEqual(preservation(),60)
    def test_instrument_classic_has_nine_vector_only_static_resources(self):
        from check_instrument_classic import check_vectors
        self.assertEqual(len(check_vectors()),9)
        for bg in BACKGROUNDS:
            branch=self.xml.find(f'.//Group[@name="hands_aviator_{bg}"]')
            for part in ('hour','minute','hub'):
                image=branch.find(f'.//Image[@resource="instrument_classic_{part}_{bg}"]')
                self.assertIsNotNone(image)
            self.assertNotIn('tintColor',E.tostring(branch,encoding='unicode'))
    def test_custom_classic_scale_and_immutable_hands(self):
        from check_classic_scale import check
        self.assertEqual(check(),(69,103))
    def test_classic_hand_sizes_share_exact_rotation_center(self):
        from generate import HAND_SIZES
        cfg=self.xml.find('UserConfigurations/ListConfiguration[@id="HandSize"]')
        self.assertEqual(cfg.get('defaultValue'),'Original')
        self.assertEqual(tuple(o.get('id') for o in cfg),tuple(HAND_SIZES))
        for style,bg in itertools.product(STYLES,BACKGROUNDS):
            g=self.xml.find(f'.//Group[@name="hands_{style}_{bg}"]')
            for prefix in ('instrument_classic','instrument_classic_clean'):
                for part in ('hour','minute','hub'):
                    resource=f'{prefix}_{part}_{bg}'
                    images=[p for p in g.findall('.//PartImage') if p.find(f'Image[@resource="{resource}"]') is not None]
                    self.assertEqual(len(images),3)
                    self.assertEqual({float(p.get('scaleX')) for p in images},set(HAND_SIZES.values()))
                    for p in images:self.assertEqual(p.get('scaleX'),p.get('scaleY'))
    def test_complications_empty_and_bounds(self):
        slots=self.xml.findall('Scene/ComplicationSlot');self.assertEqual(len(slots),3)
        for s in slots:
            self.assertIsNotNone(s.find('BoundingOval'));self.assertEqual(list(s.find('Complication[@type="EMPTY"]')),[])
            self.assertEqual(s.find('DefaultProviderPolicy').get('defaultSystemProvider'),'EMPTY')
            self.assertEqual(set(s.get('supportedTypes').split()),{c.get('type') for c in s.findall('Complication')})
            r=float(s.get('width'))/2;cx=float(s.get('x'))+r;cy=float(s.get('y'))+r
            self.assertLess(math.hypot(cx-216,cy-216)+r,120)
        for a,b in itertools.combinations(slots,2):self.assertGreater(math.hypot(float(a.get('x'))-float(b.get('x')),float(a.get('y'))-float(b.get('y'))),56)
    def test_resources_and_data_sources(self):
        strings={s.get('name') for s in E.parse(RES/'values/strings.xml').getroot()}
        for el in self.xml.iter():
            for attr in ('displayName','screenReaderText'):
                if el.get(attr):self.assertIn(el.get(attr),strings)
            resource=el.get('icon') or (el.get('resource') if el.tag=='Image' else None)
            if resource and not resource.startswith('['):self.assertTrue((RES/'drawable-nodpi'/f'{resource}.png').exists(),resource)
            if el.tag=='Font':self.assertTrue((RES/'font'/f'{el.get("family")}.ttf').exists())
            expr=el.text if el.tag=='Expression' else el.get('value','')
            for src in re.findall(r'\[([^]]+)\]',expr or ''):self.assertTrue(src in ('HOUR_0_23','MINUTE') or src.startswith(('CONFIGURATION.','COMPLICATION.')))
    def test_ambient_and_manifest(self):
        aod=self.xml.find('.//Group[@name="ambient"]')
        self.assertEqual(aod.get('alpha'),'0');self.assertEqual(aod.find('Variant').get('value'),'255')
        self.assertEqual(aod.findall('.//PartImage'),[]);self.assertEqual(aod.findall('.//Arc'),[])
        for s in self.xml.findall('Scene/ComplicationSlot'):self.assertEqual(s.find('Variant').get('value'),'0')
        ns='{http://schemas.android.com/apk/res/android}'
        m=E.parse(ROOT/'watchface/src/main/AndroidManifest.xml').getroot()
        self.assertEqual(m.find('application').get(ns+'hasCode'),'false');self.assertEqual(m.find('application/property').get(ns+'value'),'4')
        self.assertEqual(m.findall('uses-permission'),[]);self.assertEqual(m.findall('application/service'),[])
if __name__=='__main__':unittest.main(verbosity=2)
