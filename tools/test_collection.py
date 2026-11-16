"""Recipes must use actual shipped configuration options, not preview-only art."""
import unittest
import xml.etree.ElementTree as E
from generate import RES,STYLES,luminance
from preview_collection import RECIPES,options
from render import evaluate,render
from design_palette import ACCENT,INK
from complication_theme import INK as WIDGET_INK

class CollectionTest(unittest.TestCase):
    def test_reviewed_recipes_keep_time_below_and_sector_hands_contrasting(self):
        for _,recipe in RECIPES:
            self.assertNotEqual(recipe.get('layout'),'top')
            if recipe.get('sectors')=='color':self.assertEqual(recipe.get('hand_color'),'white')
        self.assertEqual(options(RECIPES[8][1])['digital_size'],'compact')

    def test_ninth_recipe_time_has_clearance_from_lower_arc(self):
        root=E.parse(RES/'raw/watchface.xml').getroot()
        cfg=options(RECIPES[8][1])
        ring=root.find('.//Group[@name="period_dividers_arc"]')
        clock=root.find('.//Group[@name="digital_time"]')
        arc_box=render(subtree=ring,transparent=True,**cfg).getchannel('A').getbbox()
        time_box=render(subtree=clock,transparent=True,**cfg).getchannel('A').getbbox()
        self.assertGreaterEqual(time_box[1]-arc_box[3],6)
        for native in clock.iter('DigitalClock'):self.assertEqual(len(native.findall('TimeText')),1)

    def test_all_six_styles_have_three_unique_native_recipes(self):
        root=E.parse(RES/'raw/watchface.xml').getroot()
        self.assertEqual(len(RECIPES),18)
        for style in STYLES:self.assertEqual(sum(r['style']==style for _,r in RECIPES),3)
        mapping={'style':'style','background':'background','hand_style':'HandStyle',
            'hand_color':'HandColor','dial_tone':'DialTone','layout':'Layout',
            'sectors':'sectors','boundaries':'boundaries','dividers':'dividers',
            'minute_track':'MinuteTrackStyle','minute_color':'MinuteColor','complication_size':'ComplicationSize'}
        for title,recipe in RECIPES:
            for key,value in options(recipe).items():
                if key not in mapping:continue
                cfg=root.find(f'UserConfigurations/ListConfiguration[@id="{mapping[key]}"]')
                self.assertIsNotNone(cfg.find(f'ListOption[@id="{value}"]'),(title,key,value))

    def test_instrument_featured_sets_match_and_have_contrast(self):
        for _,r in RECIPES[:3]:
            cfg=dict(HandColor=r['hand_color'],DialTone=r['dial_tone'],background=r['background'],style=r['style'])
            colors={evaluate(e,cfg,10,8) for e in (ACCENT,INK,WIDGET_INK)}
            self.assertEqual(len(colors),1)
            color=next(iter(colors));background='#35302B' if r['dial_tone']=='brown' else '#101212'
            self.assertGreater((luminance(color)+.05)/(luminance(background)+.05),4.5)

if __name__=='__main__':unittest.main()
