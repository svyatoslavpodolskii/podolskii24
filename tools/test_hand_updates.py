"""Native bindings, genuine alpha cutout, useful minute blade and optional icons."""
import unittest
import xml.etree.ElementTree as E
from PIL import Image,ImageChops
from generate import RES
from render import render,evaluate

class HandUpdatesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.root=E.parse(RES/'raw/watchface.xml').getroot()

    def test_cutout_is_transparent_and_centers_are_exact(self):
        selected=[]
        for part in self.root.iter('PartImage'):
            resource=part.find('Image').get('resource','')
            if not resource.startswith(('updated_sputnik_','updated_instrument_slot_')):continue
            selected.append(part)
            for pos,dim,pivot in (('x','width','pivotX'),('y','height','pivotY')):
                self.assertAlmostEqual(float(part.get(pos))+float(part.get(dim))*float(part.get(pivot)),216,places=6)
            if not resource.startswith('updated_instrument_slot_'):continue
            image=Image.open(RES/'drawable-nodpi'/(resource+'.png')).convert('RGBA')
            scale=image.width/int(part.get('width'))
            def alpha(x,y):return image.getpixel((round((x-int(part.get('x')))*scale),round((y-int(part.get('y')))*scale)))[3]
            self.assertEqual(alpha(216,120),0)
            self.assertGreater(alpha(214,120),240)
            self.assertGreater(alpha(218,120),240)
        self.assertTrue(selected)

    def test_sputnik_minute_has_a_blade_and_separate_tip(self):
        parts={}
        for p in self.root.iter('PartImage'):
            name=p.find('Image').get('resource','')
            if name.startswith('updated_sputnik_'):parts[name]=p
        self.assertEqual(len(parts),4)
        for tone in ('light','dark'):
            hour=parts[f'updated_sputnik_hour_{tone}'];minute=parts[f'updated_sputnik_minute_{tone}']
            self.assertLess(int(minute.get('y')),int(hour.get('y'))-35)
            image=Image.open(RES/'drawable-nodpi'/f'updated_sputnik_minute_{tone}.png').convert('RGBA')
            scale=image.width/int(minute.get('width'));y=round((120-int(minute.get('y')))*scale)
            row=image.getchannel('A').crop((0,y,image.width,y+1))
            box=row.getbbox();self.assertGreaterEqual((box[2]-box[0])/scale,8)

    def test_optional_icons_and_digital_switch(self):
        slot=self.root.find('.//Group[@name="slot1_SHORT_TEXT_black"]')
        icon_condition=next(c for c in slot.findall('Condition') if c.find('.//PartImage[@name="provider_icon"]') is not None)
        expression=icon_condition.find('Expressions/Expression').text
        for icon,expected in ((None,False),('',False),('provider_icon',True)):
            self.assertEqual(evaluate(expression,{},10,8,{'MONOCHROMATIC_IMAGE':icon}),expected)
        for ambient in (False,True):
            on=render(background='black',ambient=ambient,digital_time=True)
            off=render(background='black',ambient=ambient,digital_time=False)
            box=ImageChops.difference(on,off).convert('RGB').getbbox()
            self.assertIsNotNone(box)
            # Final output filtering may add a faint fringe of up to 3 pixels.
            self.assertGreaterEqual(box[0],177);self.assertGreaterEqual(box[1],283)
            self.assertLessEqual(box[2],255);self.assertLessEqual(box[3],311)

if __name__=='__main__':unittest.main()
