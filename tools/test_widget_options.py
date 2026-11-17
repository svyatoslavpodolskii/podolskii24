"""Safety contracts for the expanded controls and shared surface binding."""
import unittest
import xml.etree.ElementTree as E
from generate import RES
from render import evaluate,render

class WidgetOptionsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.root=E.parse(RES/'raw/watchface.xml').getroot()

    def test_one_surface_binding_on_existing_background(self):
        references=self.root.findall('.//Reference[@name="themeSurface"]')
        self.assertEqual(len(references),1)
        source=self.root.find('.//Group[@name="shared_backgrounds"]')
        drawing=source.find('PartDraw')
        self.assertIs(drawing.find('Reference'),references[0])
        self.assertIsNone(source.find('Transform[@target="tintColor"]'))
        expression=drawing.find('Transform[@target="tintColor"]').get('value')
        self.assertNotIn('REFERENCE',expression)
        self.assertEqual(evaluate(expression,dict(background='ivory',DialTone='original'),10,8),'#E9E2CE')
        self.assertEqual(evaluate(expression,dict(background='black',DialTone='charcoal'),10,8),'#303128')
        self.assertEqual(evaluate(expression,dict(background='black',DialTone='brown'),10,8),'#35302B')

    def test_largest_spread_subdials_fit_native_slot(self):
        for sid,center in (('1',106),('2',326)):
            slot=self.root.find(f'Scene/ComplicationSlot[@slotId="{sid}"]')
            group=slot.find('Complication/Group')
            cfg=dict(style='instrument_classic',Layout='br_round',ComplicationSize='huge_wide',MinuteTrackStyle='None')
            val=lambda target:evaluate(group.find(f'Transform[@target="{target}"]').get('value'),cfg,10,8)
            self.assertEqual(56*val('scaleX'),168)
            self.assertEqual(float(slot.get('x'))+val('x')+28,center)
            for pos,limit in ((val('x'),float(slot.get('width'))),(val('y'),float(slot.get('height')))):
                self.assertGreaterEqual(pos+28-84,0)
                self.assertLessEqual(pos+28+84,limit)
        self.assertGreaterEqual(326-106-168,52)

    def test_trio_equal_diameters_clearance_and_native_bounds(self):
        import math,itertools
        from generate import STYLES
        for style,track in itertools.product(STYLES,('None','TicksOnly')):
            for size,diameter in (('compact',72),('normal',80),('large',88),('huge',96)):
                if style in ('instrument_classic','aviator'):diameter-=8
                centers=[]
                cfg=dict(style=style,Layout='trio',ComplicationSize=size,MinuteTrackStyle=track)
                for slot in self.root.findall('Scene/ComplicationSlot'):
                    group=slot.find('Complication/Group')
                    def val(axis):
                        t=group.find(f'Transform[@target="{axis}"]')
                        return evaluate(t.get('value'),cfg,10,8) if t is not None else float(group.get(axis,0))
                    self.assertAlmostEqual(56*val('scaleX'),diameter,places=5)
                    self.assertAlmostEqual(val('scaleX'),val('scaleY'))
                    x,y=val('x')+28,val('y')+28
                    for center,limit in ((x,float(slot.get('width'))),(y,float(slot.get('height')))):
                        self.assertGreaterEqual(center-diameter/2,0)
                        self.assertLessEqual(center+diameter/2,limit)
                    centers.append((float(slot.get('x'))+x,float(slot.get('y'))+y))
                distances=[math.dist(centers[a],centers[b]) for a,b in ((0,1),(0,2),(1,2))]
                self.assertEqual(centers[0][0]+centers[1][0],432)
                self.assertEqual(centers[0][1],centers[1][1])
                self.assertEqual(centers[2][0],216)
                radii=[math.dist(c,(216,216)) for c in centers]
                self.assertLess(max(radii)-min(radii),.0001)
                self.assertEqual(radii[0],68 if style=='instrument_classic' else 76 if style=='aviator' else 84)
                self.assertGreater(min(distances)-diameter,8)

    def test_frame_does_not_outline_glyphs(self):
        cfg=dict(DigitalSize='c_frame')
        for rim in self.root.findall('.//Group[@name="digital_readout"]//Outline'):
            expression=rim.find('Transform').get('value')
            self.assertEqual(evaluate(expression,cfg,10,8),'#00000000')

    def test_sector_widget_palette_and_dimmed_text_remain_readable(self):
        from complication_theme import complication_surface,complication_ink
        from generate import palette,contrast
        for bg in ('white','ivory','black'):
            for boundaries in ('quarter','shifted_back_1_hour'):
                cfg=dict(style='sputnik',background=bg,sectors='color',boundaries=boundaries,
                    HandColor='white',DialTone='original')
                for slot in ('1','2','3'):
                    surface=evaluate(complication_surface(slot),cfg,10,8)
                    ink=evaluate(complication_ink(slot),cfg,10,8)
                    self.assertIn(surface,palette('sputnik',bg))
                    a=(205 if bg=='black' else 230)/255
                    rgb=[round(int(ink[i:i+2],16)*a+int(surface[i:i+2],16)*(1-a)) for i in (1,3,5)]
                    effective='#'+''.join(f'{v:02X}' for v in rgb)
                    self.assertGreaterEqual(contrast(surface,effective),4.5)

    def test_quarter_time_uses_exact_light_dark_halves_without_outline(self):
        clock=self.root.find('.//Group[@name="digital_time"]')
        im=render(style='sputnik',background='ivory',sectors='color',boundaries='quarter',
            minute_track='SputnikRing',digital_size='c_plain',subtree=clock,transparent=True)
        for box,pale in (((0,0,216,432),True),((216,0,432,432),False)):
            ink=[p for p in im.crop(box).getdata() if p[3]>230]
            self.assertTrue(ink)
            self.assertTrue(all(p[0]>200 if pale else p[0]<70 for p in ink))

    def test_four_clock_decorations_are_real_distinct_xml_variants(self):
        images=[render(style='sputnik',background='black',sectors='color',digital_size='n_'+mode,
            component='full',output_size=216).tobytes() for mode in ('plain','outline','frame','box')]
        self.assertEqual(len(set(images)),4)
        self.assertFalse(self.root.findall('.//TimeText/Font/Outline'))
        for readout in self.root.findall('.//Group[@name="digital_readout"]'):
            self.assertEqual(len(readout.findall('PartText')),1)
            self.assertEqual(len(readout.findall('.//Parameter')),2)

    def test_no_extra_configuration_or_raster_for_decoration(self):
        self.assertEqual(len(self.root.find('UserConfigurations')),20)
        clock=self.root.find('.//Group[@name="digital_time"]')
        self.assertFalse(clock.findall('.//Image'))
        windows=self.root.findall('.//Group[@name="br_date_window"]')
        self.assertTrue(windows)
        for window in windows:
            self.assertEqual(window.find('Transform[@target="x"]').get('value'),'-10')
            self.assertEqual(window.find('Transform[@target="y"]').get('value'),'4')
            for stroke in window.iter('Stroke'):self.assertEqual(stroke.get('thickness'),'1.2')

if __name__=='__main__':unittest.main()
