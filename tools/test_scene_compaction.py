"""Global changes must preserve actual paint, not just pass schema validation."""
import copy
import itertools
import json
import unittest
import xml.etree.ElementTree as E
from PIL import ImageChops,ImageStat
from generate import RES,ROOT,STYLES,BACKGROUNDS,PRESETS,MINUTE_TRACKS
from render import render,evaluate
from scene_compaction import coalesce,selector

class GlobalCompactionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=E.parse(RES/'raw/watchface.xml').getroot()
        cls.manifest=json.loads((ROOT/'docs/optimization/geometry-sources.json').read_text(encoding='utf-8'))
        cls.before=E.fromstring(cls.manifest['global_scene_source'])

    def test_real_structural_reduction(self):
        before=len(list(self.before.iter()));after=len(list(self.root.find('Scene').iter()))
        self.assertLess(after,before*.78)
        self.assertLess(len(list(self.root.iter())),4500)
        self.assertLess((RES/'raw/watchface.xml').stat().st_size,470000)
        self.assertLess(len(self.root.findall('.//PartDraw[@renderMode="MASK"]')),80)
        self.assertEqual(self.manifest['global_compaction']['complication_copies_removed'],24)
        self.assertGreaterEqual(self.manifest['global_compaction']['redundant_masks_removed'],18)
        for slot in self.root.findall('Scene/ComplicationSlot'):
            for kind in ('SHORT_TEXT','RANGED_VALUE','MONOCHROMATIC_IMAGE','SMALL_IMAGE'):
                groups=[g for g in slot.findall(f'Complication[@type="{kind}"]/Group') if g.get('name','').startswith('slot')]
                self.assertEqual(len(groups),1)

    def test_pixel_equivalence_across_modes(self):
        for i,(style,bg,mode) in enumerate(itertools.product(STYLES,('white','ivory','black'),('lines','color'))):
            options=dict(style=style,background=bg,sectors=mode,boundaries=('quarter','shifted_back_1_hour')[i%2],
                minute=True,minute_track=('None','SputnikRing','InstrumentRing')[i%3],
                dividers=('micro','radial','full','arc','classic')[i%5],complications=True,
                hand_color=('original','white','black')[i%3],output_size=432,minute_color='original')
            expected=copy.deepcopy(self.before)
            # 5.7 deliberately tones down sector complication surfaces. Compare
            # compaction against the same paint, keeping this change explicit.
            from complication_theme import complication_surface
            for comp in expected.findall('ComplicationSlot/Complication'):
                for group in comp.iter('Group'):
                    if not group.get('name','').startswith('slot'):continue
                    draw=group.find('PartDraw')
                    if draw is None:continue
                    backing=draw.find('Transform[@target="tintColor"]')
                    if backing is None:backing=E.SubElement(draw,'Transform',target='tintColor')
                    slot=next(s for s in expected.findall('ComplicationSlot') if comp in list(s))
                    backing.set('value',complication_surface(slot.get('slotId')))
            if style=='instrument_classic' and mode!='color':
                # 5.6.1 intentionally replaces the regular pale-dial rust ink.
                # Compare optimization against that explicit design change.
                for scale in expected.findall('.//PartImage[@name="instrument_classic_custom_scale"]'):
                    for tint in scale.findall('Transform[@target="tintColor"]'):scale.remove(tint)
                    scale.set('tintColor','#F08A35' if bg=='black' else '#222A29')
            a=render(subtree=expected,**options);b=render(subtree=self.root,**options)
            diff=ImageChops.difference(a,b)
            # Exact at native size: no new clipping, resampling or raster assets.
            self.assertEqual(max(v for lo,v in diff.getextrema()),0,options)

    def test_overlapping_selectors_are_never_merged(self):
        root=E.fromstring('<WatchFace><UserConfigurations><ListConfiguration id="a"><ListOption id="0"/><ListOption id="1"/></ListConfiguration></UserConfigurations><Scene><Group name="x" x="0" y="0" width="432" height="432"/></Scene></WatchFace>')
        from generate import condition
        parent=root.find('Scene/Group')
        for _ in range(2):
            E.SubElement(condition(parent,'[CONFIGURATION.a] == "0"'),'PartImage',x='0',y='0',width='4',height='4')
        self.assertEqual(coalesce(root),0)
        self.assertEqual(len(parent),2)

    def test_all_period_label_coordinates_and_inks(self):
        def labels(scene,config):
            found={}
            def visit(n):
                if not any(p.get('name','').startswith('period_label_') for p in n.iter('PartText')):return
                selected=selector(n)
                if selected:
                    guard,payload=selected
                    if evaluate(guard,config,12,0):visit(payload)
                    return
                if n.tag=='PartText' and n.get('name','').startswith('period_label_'):
                    attrs=dict(n.attrib)
                    for t in n.findall('Transform'):attrs[t.get('target')]=evaluate(t.get('value'),config,12,0)
                    font=n.find('Text/Font');color=font.get('color')
                    for t in font.findall('Transform'):
                        if t.get('target')=='color':color=evaluate(t.get('value'),config,12,0)
                    self.assertNotIn(n.get('name'),found)
                    found[n.get('name')]=(tuple(float(attrs.get(k,0)) for k in ('x','y','angle')),color,font.text)
                    return
                for child in n:visit(child)
            for name in ('shared_period_details_under','shared_period_details'):
                visit(scene.find(f'.//Group[@name="{name}"]'))
            return found
        for style,bg,preset,mode,track in itertools.product(STYLES,BACKGROUNDS,PRESETS,('color','labels'),MINUTE_TRACKS):
            config=dict(style=style,background=bg,boundaries=preset,sectors=mode,MinuteTrackStyle=track)
            before=labels(self.before,config);after=labels(self.root.find('Scene'),config)
            self.assertEqual(len(before),4,config)
            self.assertEqual(before,after,config)

if __name__=='__main__':unittest.main()
