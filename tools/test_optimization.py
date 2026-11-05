"""Contracts on the deployed optimized WFF, not only the design expansion."""
import gzip
import itertools
import json
import unittest
import xml.etree.ElementTree as E
from PIL import Image
from generate import ROOT,RES,STYLES,BACKGROUNDS,MODES,PRESETS,MINUTE_TRACKS
from static_geometry import expanded,canonical,MANIFEST
from render import evaluate

class OptimizedRuntimeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.native=E.parse(RES/'raw/watchface.xml').getroot()
        cls.manifest=json.loads(MANIFEST.read_text(encoding='utf-8'))
    def test_inverse_is_exact_original_tree(self):
        before=E.fromstring(gzip.decompress((ROOT/'docs/optimization/baseline.xml.gz').read_bytes()))
        self.assertEqual(canonical(before),canonical(expanded(self.native)))
    def test_runtime_budgets(self):
        self.assertLessEqual((RES/'raw/watchface.xml').stat().st_size,2_500_000)
        self.assertLessEqual(sum(1 for _ in self.native.iter()),36000)
        self.assertLessEqual(sum(a['rgba_bytes'] for a in self.manifest['assets'].values()),13_000_000)
        total=0
        for name in self.manifest['runtime_png_names']:
            p=RES/'drawable-nodpi'/f'{name}.png'
            with Image.open(p) as im:total+=im.width*im.height*4
        before=json.loads((ROOT/'docs/optimization/baseline.json').read_text())
        self.assertLessEqual(total,before['all_png_decoded_rgba_bytes'])
    def test_assets_and_native_font_aod_contracts(self):
        import hashlib
        for name,info in self.manifest['assets'].items():
            p=RES/'drawable-nodpi'/f'{name}.png'
            self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),info['sha256'])
            with Image.open(p) as im:self.assertEqual(list(im.size),info['size'])
        for name,info in self.manifest['trimmed_assets'].items():
            original=Image.open(RES/'drawable-nodpi'/f"{info['original']}.png").convert('RGBA')
            cropped=Image.open(RES/'drawable-nodpi'/f'{name}.png').convert('RGBA')
            self.assertEqual(original.crop(info['box']).tobytes(),cropped.tobytes())
            self.assertEqual(hashlib.sha256((RES/'drawable-nodpi'/f'{name}.png').read_bytes()).hexdigest(),info['sha256'])
        for p in self.native.iter('PartImage'):
            if not p.find('Image').get('resource','').startswith('trimmed_'):continue
            for axis in ('X','Y'):
                attr='x' if axis=='X' else 'y';dim='width' if axis=='X' else 'height'
                # Original hand pivots must still be exactly the watch center.
                if p.get('name','').startswith('selected_') or p.get('name')=='instrument_classic_hub':
                    self.assertAlmostEqual(float(p.get(attr))+float(p.get(dim))*float(p.get('pivot'+axis)),216,places=6)
        before=E.fromstring(gzip.decompress((ROOT/'docs/optimization/baseline.xml.gz').read_bytes()))
        self.assertEqual(canonical(before.find('.//Group[@name="ambient"]')),canonical(expanded(self.native).find('.//Group[@name="ambient"]')))
        self.assertIsNone(self.native.find('.//Group[@name="ambient"]'))
        # Factoring never bakes fonts or dynamic complication/time data.
        self.assertTrue(self.native.findall('.//PartText'))
        for e in self.native.iter('PartImage'):
            if e.get('name','').startswith('baked_'):
                source=E.fromstring(self.manifest['sources'][e.get('name')[6:]])
                self.assertFalse(source.findall('.//Transform'))
                self.assertFalse(source.findall('.//PartText'))
    def test_shared_tracks_native_visibility(self):
        shared=self.native.find('.//Group[@name="shared_minute_tracks"]')
        def visit(el,config,names):
            if el.tag=='Condition':
                expr={e.get('name'):e.text for e in el.findall('Expressions/Expression')}
                for cmp in el.findall('Compare'):
                    if evaluate(expr[cmp.get('expression')],config,10,30):
                        for child in cmp:visit(child,config,names)
                        return
                return
            if el.get('name','').startswith('minute_track_') and el.get('name')!='minute_track_contrast':names.append(el.get('name'));return
            for child in el:visit(child,config,names)
        for s,b,m,p,t,minute in itertools.product(STYLES,BACKGROUNDS,MODES,PRESETS,MINUTE_TRACKS,('FALSE','TRUE')):
            config=dict(style=s,background=b,sectors=m,boundaries=p,MinuteTrackStyle=t,minute=minute)
            names=[];visit(shared,config,names)
            self.assertEqual(names,[] if t=='None' else ['minute_track_'+t])

if __name__=='__main__':unittest.main()
