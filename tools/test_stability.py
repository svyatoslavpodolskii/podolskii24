"""5.2 runtime contracts: editor footprint and usability are tested natively."""
import json
import unittest
import xml.etree.ElementTree as E
from PIL import Image
from generate import RES,ROOT
from render import evaluate,render

class StabilityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=E.parse(RES/'raw/watchface.xml').getroot()
        cls.manifest=json.loads((ROOT/'docs/optimization/geometry-sources.json').read_text(encoding='utf-8'))
    def test_parse_and_editor_budgets(self):
        self.assertLessEqual(len(list(self.root.iter())),20000)
        self.assertLessEqual((RES/'raw/watchface.xml').stat().st_size,1_500_000)
        self.assertLessEqual(self.manifest['runtime_png_rgba_bytes'],28_000_000)
        for option in self.root.find('UserConfigurations').iter():
            if not option.get('icon'):continue
            with Image.open(RES/'drawable-nodpi'/(option.get('icon')+'.png')) as image:self.assertLessEqual(max(image.size),144)
        self.assertGreaterEqual(len(self.manifest['asset_aliases']),10)
    def test_universal_size_and_hour_layer(self):
        hands=self.root.find('.//Group[@name="interactive_hands"]')
        transforms=hands.findall('Transform');self.assertEqual({t.get('target') for t in transforms},{'scaleX','scaleY'})
        for choice,factor in (('Compact',.92),('Original',1),('Large',1.06)):
            for t in transforms:self.assertAlmostEqual(evaluate(t.get('value'),{'HandSize':choice},12,0),factor)
        bodies=hands.findall('Condition/Compare/Group');self.assertEqual(len(bodies),6)
        for body in bodies:
            minute=next(c for c in body if c.find('.//Group[@name="minute"]') is not None)
            self.assertGreater(list(body).index(body.find('Group[@name="hour"]')),list(body).index(minute))
            for expr in body.findall('.//Expressions/Expression'):self.assertNotIn('CONFIGURATION.HandSize',expr.text or '')
    def test_readable_complications_and_inner_labels(self):
        for slot in self.root.findall('Scene/ComplicationSlot'):
            self.assertEqual((slot.get('width'),slot.get('height')),('96','96'))
            self.assertEqual(slot.get('isCustomizable'),'TRUE')
            for group in slot.findall('.//Group'):
                if group.get('name','').startswith('slot'):
                    self.assertEqual((group.get('x'),group.get('y')),('20','20'))
                    self.assertEqual(float(group.get('scaleX',1)),1)
            self.assertTrue(slot.findall('.//Ellipse'))
            self.assertFalse(slot.findall('.//RoundRectangle'))
            self.assertFalse([p for p in slot.iter('Parameter') if 'COMPLICATION.TITLE' in p.get('expression','')])
        labels=[e for e in self.root.iter('PartText') if e.get('name','').startswith('period_label_')]
        self.assertTrue(labels)
        for label in labels:self.assertEqual({t.get('target') for t in label.findall('Transform')},{'x','y'})
    def test_size_changes_legacy_needle_visibly(self):
        images=[render('classic','black',hand_style='auto',hand_size=s,component='hands').tobytes() for s in ('Compact','Original','Large')]
        self.assertEqual(len(set(images)),3)

if __name__=='__main__':unittest.main()
