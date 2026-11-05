"""Verify native runtime palette changes without duplicating bitmap resources."""
import unittest
import xml.etree.ElementTree as E
from generate import RES
from minute_palette import COLORS, PALETTES
from render import evaluate

class MinutePaletteTest(unittest.TestCase):
    def test_runtime_palette(self):
        root=E.parse(RES/'raw/watchface.xml').getroot()
        cfg=root.find('UserConfigurations/ListConfiguration[@id="MinuteColor"]')
        self.assertEqual(cfg.get('defaultValue'),'original')
        self.assertEqual([n.get('id') for n in cfg],list(PALETTES))
        track=root.find('.//Group[@name="shared_minute_tracks"]')
        transforms=track.findall('.//Transform')
        self.assertTrue(transforms)
        for parent in track.iter():
            for transform in parent.findall('Transform'):
                expr=transform.get('value')
                if 'MinuteColor' not in expr: continue
                target=transform.get('target')
                index=COLORS.index(parent.get(target))
                for key, colors in PALETTES.items():
                    self.assertEqual(evaluate(expr,{'MinuteColor':key},10,8),colors[index])
        outside=[t for t in root.iter('Transform') if 'MinuteColor' in t.get('value','') and t not in transforms]
        self.assertEqual(outside,[])

if __name__=='__main__':unittest.main()
