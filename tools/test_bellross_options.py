"""Native configuration and resource regressions for the optional layouts."""
import itertools
import unittest
import xml.etree.ElementTree as E
from generate import RES,ROOT,STYLES
from render import render,evaluate

class BellrossOptionsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.root=E.parse(RES/'raw/watchface.xml').getroot()

    def test_no_additional_configuration_keys_or_slots(self):
        self.assertEqual(len(self.root.find('UserConfigurations')),20)
        self.assertEqual([s.get('slotId') for s in self.root.findall('Scene/ComplicationSlot')],['1','2','3'])
        for key,values in (('Layout',('bottom','top','br_round','br_square')),
                           ('HandColor',('original','br_orange','br_amber','br_mono'))):
            ids={p.get('id') for p in self.root.findall(f'UserConfigurations/ListConfiguration[@id="{key}"]/ListOption')}
            self.assertTrue(set(values)<=ids)

    def test_large_circles_are_centered_separate_and_inside_slot(self):
        for style,layout,size in itertools.product(STYLES,('br_round','br_square'),('compact','normal','large')):
            diameter={'compact':120,'normal':136,'large':152}[size]
            cfg={'style':style,'Layout':layout,'ComplicationSize':size}
            for sid,xcenter in (('1',114),('2',318)):
                slot=self.root.find(f'Scene/ComplicationSlot[@slotId="{sid}"]')
                g=slot.find('Complication/Group')
                value=lambda axis:evaluate(g.find(f'Transform[@target="{axis}"]').get('value'),cfg,10,8)
                self.assertAlmostEqual(56*value('scaleX'),diameter,places=5)
                self.assertEqual(float(slot.get('x'))+value('x')+28,xcenter)
                self.assertEqual(float(slot.get('y'))+value('y')+28,216)
                self.assertLessEqual(value('y')+28+diameter/2,float(slot.get('height')))
            self.assertGreaterEqual(204-diameter,52)

    def test_three_hand_palettes_share_only_eleven_vector_assets(self):
        from PIL import Image
        assets={p.get('resource') for p in self.root.iter('Image') if p.get('resource','').startswith('br_shared_')}
        self.assertEqual(len(assets),11)
        decoded=0
        for name in assets:
            with Image.open(RES/'drawable-nodpi'/(name+'.png')) as im:decoded+=im.width*im.height*4
            self.assertTrue((ROOT/'docs/hand-masters/bellross-palettes'/(name+'.svg')).is_file())
        self.assertLess(decoded,950000)
        outputs=[render('instrument_classic','black',minute=True,hand_color=p,component='hands').tobytes() for p in ('original','br_orange','br_amber','br_mono')]
        self.assertEqual(len(set(outputs)),4)

    def test_adaptive_palette_uses_warm_light_background_ink(self):
        blades=self.root.findall('.//Group[@name="flat_blade"]')
        self.assertTrue(blades)
        for blade in blades:
            color=blade.findall('PartImage')[1].find('Transform[@target="tintColor"]').get('value')
            for bg,expected in (('white','#FAFAF7'),('ivory','#E9E2CE'),('black','#EEEBD9')):
                self.assertEqual(evaluate(color,{'HandColor':'adaptive','background':bg},10,8),expected)
        for palette in ('br_orange','br_amber','br_mono'):
            a=render('instrument_classic','white',minute=True,hand_color=palette,component='hands')
            b=render('instrument_classic','black',minute=True,hand_color=palette,component='hands')
            self.assertNotEqual(a.tobytes(),b.tobytes())

    def test_small_date_uses_actual_provider_and_has_no_icon_or_title(self):
        for window in self.root.findall('.//Group[@name="br_date_window"]'):
            for parameter in window.iter('Parameter'):
                self.assertIn(parameter.get('expression'),('[COMPLICATION.TEXT]','[COMPLICATION.RANGED_VALUE_VALUE]'))
            self.assertFalse(window.findall('.//PartImage[@name="provider_icon"]'))
        for layout in ('br_round','br_square'):
            a=render('sputnik','ivory',complications=True,layout=layout,output_size=216)
            b=render('sputnik','ivory',complications=True,layout='bottom',output_size=216)
            self.assertNotEqual(a.tobytes(),b.tobytes())

    def test_side_numerals_hidden_only_in_new_layout(self):
        for name,mode in (('shared_regular_scales','none'),('shared_colored_scales','color')):
            subtree=self.root.find(f'.//Group[@name="{name}"]')
            images=[render('instrument_classic','black',sectors=mode,subtree=subtree,
                layout=layout,transparent=True) for layout in ('bottom','br_round')]
            old,new=[p.crop((40,174,114,258)).getchannel('A') for p in images]
            self.assertIsNotNone(old.getbbox())
            self.assertIsNone(new.getbbox())

    def test_complication_theme_uses_shared_ink_and_preserves_photos(self):
        from complication_theme import INK, background_expression
        for tone,expected in [('amber_dial','#FFC027'),('brown','#F08A35'),('mono_dial','#F0F2E9')]:
            config={'DialTone':tone,'background':'black','style':'instrument_classic','HandColor':'original'}
            self.assertEqual(evaluate(INK,config,10,8),expected)
        self.assertEqual(evaluate(background_expression(),{'DialTone':'brown','background':'black'},10,8),'#35302B')
        groups=self.root.findall('.//Group[@name="provider_foreground"]')
        self.assertTrue(groups)
        for group in groups:
            self.assertEqual(group.find('Transform[@target="tintColor"]').get('value'),INK)
            self.assertFalse(group.findall('.//Image[@resource="[COMPLICATION.SMALL_IMAGE]"]'))

    def test_instrument_sets_use_identical_accent_across_all_foregrounds(self):
        from design_palette import ACCENT, INK as SCALE_INK
        from complication_theme import INK, DATE_INK
        for selection,color in (('br_orange','#F08A35'),('br_amber','#FFC027'),('br_mono','#F0F2E9')):
            for tone in ('original','brown','amber_dial','mono_dial'):
                config={'HandColor':selection,'DialTone':tone,'background':'black','style':'instrument_classic'}
                for expression in (ACCENT,SCALE_INK,INK,DATE_INK):
                    self.assertEqual(evaluate(expression,config,10,8),color)

    def test_brand_variants_only_change_top_label(self):
        from PIL import ImageChops
        base=render('instrument_classic','black',layout='br_round')
        for name in ('br_round_belorus','br_round_podolskii'):
            branded=render('instrument_classic','black',layout=name)
            box=ImageChops.difference(base,branded).convert('RGB').getbbox()
            self.assertIsNotNone(box)
            self.assertGreaterEqual(box[1],130)
            self.assertLessEqual(box[3],165)

    def test_wordmarks_are_vector_derived_and_below_hands(self):
        scene=self.root.find('Scene')
        layers=list(scene)
        brand=next(layer for layer in layers if layer.find('.//Group[@name="dial_brand"]') is not None)
        self.assertLess(layers.index(brand),layers.index(scene.find('Group[@name="interactive_hands"]')))
        self.assertFalse(brand.findall('.//PartText'))
        self.assertFalse(brand.findall('.//Ellipse'))
        for word in ('belorus','podolskii'):
            source=ROOT/'docs/hand-masters/wordmarks'/('dial_wordmark_'+word+'.svg')
            vector=E.parse(source).getroot()
            self.assertFalse(vector.findall('.//{*}text'))
            self.assertTrue(vector.findall('{*}path'))

    def test_bases_and_date_windows_match_actual_theme_background(self):
        from complication_theme import background_expression
        for bg,tone,color in (('black','brown','#35302B'),('black','navy','#142331'),('white','original','#FAFAF7'),('ivory','original','#E9E2CE')):
            image=render('instrument_classic',bg,dial_tone=tone,hand_color='br_orange',
                         component='hands',hour=18,mins=0,transparent=True)
            self.assertEqual(image.getpixel((240,216))[:3],tuple(bytes.fromhex(color[1:])))
        for window in self.root.findall('.//Group[@name="br_date_window"]'):
            fills=window.findall('.//Fill/Transform[@target="color"]')
            self.assertEqual(len(fills),2)
            self.assertTrue(all(f.get('value')=='[REFERENCE.themeSurface]' for f in fills))

if __name__=='__main__':unittest.main()
