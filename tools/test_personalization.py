"""Behavioral regression checks on the shipped native scene and its resources."""
import itertools
import unittest
import xml.etree.ElementTree as E
from PIL import ImageChops
from generate import RES,STYLES,BACKGROUNDS,PRESETS,MODES
from render import render,evaluate
from runtime_scene import compact_guards

class PersonalizationTest(unittest.TestCase):
    def test_factored_guards_truth_table(self):
        guards=[f'([CONFIGURATION.style] == "{s}" && [CONFIGURATION.background] == "{b}") && ([CONFIGURATION.boundaries] == "{p}" && [CONFIGURATION.sectors] == "{m}")'
            for s,b,p,m in itertools.product(STYLES,('white','ivory'),PRESETS,('lines','labels'))]
        compact=compact_guards(guards)
        self.assertLess(len(compact),len(' || '.join(guards))/5)
        for s,b,p,m in itertools.product(STYLES,BACKGROUNDS,PRESETS,MODES):
            config=dict(style=s,background=b,boundaries=p,sectors=m)
            expected=b in ('white','ivory') and m in ('lines','labels')
            self.assertEqual(evaluate(compact,config,10,8),expected)

    def test_seconds_are_optional_and_absent_from_aod(self):
        options=dict(background='black',digital_time=False,output_size=216)
        a=render(seconds=False,**options)
        b=render(seconds=True,second=15,**options)
        c=render(seconds=True,second=30,**options)
        self.assertNotEqual(a.tobytes(),b.tobytes())
        self.assertNotEqual(b.tobytes(),c.tobytes())
        self.assertEqual(render(ambient=True,seconds=True,**options).tobytes(),render(ambient=True,seconds=False,**options).tobytes())

    def test_aod_minutes_independent_of_active_minutes(self):
        options=dict(background='black',digital_time=False,output_size=216,mins=17)
        a=render(ambient=True,minute=False,aod_minute=True,**options)
        b=render(ambient=True,minute=True,aod_minute=True,**options)
        c=render(ambient=True,minute=True,aod_minute=False,**options)
        self.assertEqual(a.tobytes(),b.tobytes())
        self.assertNotEqual(a.tobytes(),c.tobytes())
        self.assertEqual(render(minute=False,aod_minute=True,**options).tobytes(),render(minute=False,aod_minute=False,**options).tobytes())

    def test_flat_palettes_keep_opposite_contours(self):
        root=E.parse(RES/'raw/watchface.xml').getroot()
        group=root.find('.//Group[@name="flat_hands"]')
        self.assertIsNone(group.find('Transform[@target="tintColor"]'))
        blades=group.findall('.//Group[@name="flat_blade"]')
        self.assertTrue(blades)
        for blade in blades:
            edge,inside=blade.findall('PartImage')
            for choice in ('white','black'):
                colors=[evaluate(p.find('Transform[@target="tintColor"]').get('value'),{'HandColor':choice},10,8) for p in (edge,inside)]
                self.assertEqual(set(colors),{'#222A29','#F0F0E7'})
        for bg in BACKGROUNDS:
            outputs=[render('sputnik',bg,hand_style='legacy_sputnik',minute=True,hand_color=c,component='hands',output_size=216).tobytes() for c in ('original','white','black','orange','green')]
            self.assertEqual(len(set(outputs)),5)

    def test_sizes_and_insets_have_visible_effect(self):
        for parameter,values in (('complication_size',('compact','normal','large')),('digital_size',('compact','normal','large')),('minute_inset',('wide','inset')),('scale_inset',('original','wide'))):
            outputs=[render('instrument_classic','black',minute_track='InstrumentRing',complications=True,**{parameter:v},output_size=216).tobytes() for v in values]
            self.assertEqual(len(set(outputs)),len(values),parameter)

if __name__=='__main__':unittest.main()
