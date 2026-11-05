"""Preservation audit; compatibility command for the vector replacement."""
import hashlib
import json
import xml.etree.ElementTree as E
from generate import ROOT,RES

def preservation():
    manifest=json.loads((ROOT/'docs/hands-before-photo.json').read_text())
    for name,digest in manifest.items():
        assert hashlib.sha256((RES/'drawable-nodpi'/name).read_bytes()).hexdigest()==digest,name
    old=E.parse(ROOT/'docs/references/before-photo-watchface.xml').getroot()
    from static_geometry import design_scene
    current=design_scene()
    def strip(el):
        for ch in list(el):
            own=ch.findall('Expressions/Expression')
            if (ch.tag=='Group' and ch.get('name')=='instrument_classic_hour_front') or (ch.tag=='ListConfiguration' and ch.get('id')=='HandSize') or (ch.tag=='ListOption' and ch.get('id') in ('bellross_photo','instrument_classic','instrument_classic_clean')) or (ch.tag=='Condition' and any('"bellross_photo"' in (e.text or '') or '"instrument_classic_clean"' in (e.text or '') or '[CONFIGURATION.style] == "instrument_classic"' in (e.text or '') for e in own)):
                el.remove(ch)
            else:strip(ch)
        if el.text is not None and not el.text.strip():el.text=None
        el.tail=None
    strip(old);strip(current)
    assert E.tostring(old)==E.tostring(current),'Non-photo WFF content changed'
    return len(manifest)


if __name__=="__main__":
    from check_instrument_classic import run
    run()
