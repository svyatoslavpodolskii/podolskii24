"""Contracts on the actual shipped tree, independent of legacy expansion."""
import json
import unittest
import copy
import xml.etree.ElementTree as E
from PIL import ImageChops,ImageStat
from generate import RES,ROOT,VISIBLE_HAND_STYLES,STYLES
from render import render

class RuntimeSceneTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=E.parse(RES/'raw/watchface.xml').getroot()
        cls.manifest=json.loads((ROOT/'docs/optimization/geometry-sources.json').read_text(encoding='utf8'))

    def test_stronger_budgets_and_pruned_hands(self):
        self.assertLess(len(list(self.root.iter())),4500)
        self.assertLess((RES/'raw/watchface.xml').stat().st_size,470000)
        self.assertLess(self.manifest['runtime_png_rgba_bytes'],19300000)
        self.assertLess(len(self.root.findall('.//PartDraw[@renderMode="MASK"]')),150)
        cfg=self.root.find('UserConfigurations/ListConfiguration[@id="HandStyle"]')
        self.assertEqual(tuple(n.get('id') for n in cfg),VISIBLE_HAND_STYLES)
        self.assertEqual(len(VISIBLE_HAND_STYLES),14)
        resources={n.get('resource') for n in self.root.iter('Image')}
        self.assertFalse(any(n.startswith('trimmed_classic_scale_') for n in resources))
        self.assertIn('runtime_classic_scale_alpha',resources)

    def test_ambient_and_complication_runtime(self):
        scene=self.root.find('Scene')
        self.assertIsNone(scene.find('Group[@name="ambient"]'))
        for name in ('interactive','interactive_hands'):
            group=scene.find(f'Group[@name="{name}"]')
            self.assertTrue(group.findall('Variant[@target="tintColor"]'))
            self.assertFalse(group.findall('Variant[@target="alpha"][@value="0"]'))
        for minute in scene.findall('Group[@name="interactive_hands"]//Group[@name="minute"]'):
            self.assertIn('CONFIGURATION.AodMinute',minute.find('Variant[@mode="AMBIENT"][@target="alpha"]').get('value'))
        cfg=self.root.find('UserConfigurations/BooleanConfiguration[@id="DigitalTime"]')
        self.assertEqual(cfg.get('defaultValue'),'TRUE')
        for time in scene.findall('.//DigitalClock/TimeText'):
            self.assertEqual((time.get('format'),time.get('hourFormat')),('hh:mm','24'))
        for slot in scene.findall('ComplicationSlot'):
            self.assertEqual(slot.get('width'),'176')
            self.assertTrue(slot.findall('.//Ellipse'))
            self.assertTrue(slot.findall('.//PartImage[@name="provider_icon"]'))
            for part in slot.findall('Complication[@type="RANGED_VALUE"]//PartText'):
                parameters=part.findall('.//Parameter')
                self.assertEqual([p.get('expression') for p in parameters],['[COMPLICATION.RANGED_VALUE_VALUE]'])
        images=[render(ambient=True,hour=h,mins=m,output_size=216).tobytes() for h,m in ((0,0),(3,0),(10,30),(18,0))]
        self.assertEqual(len(set(images)),4)

    def test_visual_layer_order_and_scale_contours(self):
        before=E.fromstring(self.manifest['runtime_scene_source'])
        # Every style and background, both boundary presets, with/without outer
        # minutes; all sector modes and divider shapes appear across this matrix.
        for i,style in enumerate(STYLES):
            for j,background in enumerate(('white','ivory','black')):
                options=dict(style=style,background=background,sectors=('none','lines','labels','color')[(i+j)%4],
                    boundaries=('quarter','shifted_back_1_hour')[j%2],dividers=('micro','radial','full','arc','classic')[(i+j)%5],
                    minute_track='InstrumentRing' if j%2 else 'None',minute=True,output_size=216,digital_time=False,minute_color='original',component='scale',scale_inset='original')
                expected=before
                if style=='aviator' and options['sectors']!='color':
                    expected=copy.deepcopy(before)
                    for dial in expected.findall('.//Group'):
                        if not dial.get('name','').startswith('dial_aviator_'):continue
                        for scale in dial.findall('.//Group[@name="regular_scale"]'):
                            scale.set('tintColor','#F08A35' if background=='black' else '#222A29')
                if style=='instrument_classic' and options['sectors']!='color':
                    expected=copy.deepcopy(before)
                    # The pale regular scale intentionally changed ink in 5.6.1;
                    # retain the old geometry while comparing the new paint.
                    for scale in expected.findall('.//PartImage[@name="instrument_classic_custom_scale"]'):
                        resource=scale.find('Image').get('resource','')
                        scale.set('tintColor','#F08A35' if background=='black' else '#222A29')
                old=render(subtree=expected,**options)
                new=render(subtree=self.root,**options)
                diff=ImageChops.difference(old,new)
                maximum=max(high for low,high in diff.getextrema())
                # The shared scale keeps exact alpha; filtering formerly colored
                # antialiased edges vs tinting the shared alpha can differ slightly.
                self.assertLessEqual(maximum,8 if style=='instrument_classic' else 1,(options,maximum))
                self.assertLess(max(ImageStat.Stat(diff).mean),.1,(options,maximum))

if __name__=='__main__':unittest.main()
