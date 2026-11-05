"""Reject non-resource WFF packages and missing/mismatched native scenes."""
import os
import re
import subprocess
from io import BytesIO
from PIL import Image
import hashlib
import sys
import zipfile
import xml.etree.ElementTree as E
from pathlib import Path
from generate import RES, ROOT, STYLES, VISIBLE_HAND_STYLES as HAND_STYLES, MINUTE_TRACKS, BACKGROUNDS, HAND_SIZES

def verify(path):
    with zipfile.ZipFile(path) as archive:
        aliases={n:n for n in archive.namelist()}
        if 'res/raw/watchface.xml' not in aliases:
            sdk=Path(os.environ.get('ANDROID_HOME', ROOT.parent/'.tools/android-sdk'))
            executable=next(iter(sorted((sdk/'build-tools').glob('*/aapt.exe'))),None) or next(iter(sorted((sdk/'build-tools').glob('*/aapt'))))
            table=subprocess.check_output([str(executable),'dump','--values','resources',str(path)],text=True,encoding='utf-8')
            for kind,name,packed in re.findall(r'(?m)^\s+resource 0x[0-9a-f]+ [^:]+:(\w+)/(\w+):[^\n]*\n\s+\(string8\) "([^"\n]+)"',table):
                aliases[f'res/{kind}/{name}{Path(packed).suffix}']=packed
        class Resources:
            def read(self,name):return archive.read(aliases[name])
        z=Resources()
        def graphic_name(filename):
            # A lossless crop can replace a master in the actual APK.
            for candidate in (filename,'trimmed_'+filename):
                match=next((n for n in aliases if n.endswith('/'+candidate)),None)
                if match:return match,candidate
            raise AssertionError('Packaged graphic missing: '+filename)
        def same_graphic(packed,source):
            data=z.read(packed)
            expected=source.read_bytes()
            if data==expected:return True
            actual=Image.open(BytesIO(data)).convert('RGBA')
            original=Image.open(BytesIO(expected)).convert('RGBA')
            if actual.size!=original.size or actual.getchannel('A').tobytes()!=original.getchannel('A').tobytes():return False
            # AAPT legitimately clears RGB under fully transparent pixels.
            backdrop=Image.new('RGBA',actual.size,'black')
            return Image.alpha_composite(backdrop,actual).tobytes()==Image.alpha_composite(backdrop,original).tobytes()
        names=list(aliases)
        assert not any(n.endswith(('.dex','.class','.jar','.so')) for n in names), 'Executable code found in WFF APK'
        assert 'res/raw/watchface.xml' in names, 'Native WFF scene missing'
        assert len(z.read('res/raw/watchface.xml'))<=10_000_000, 'Packaged WFF exceeds the 10 MB source limit'
        assert z.read('res/raw/watchface.xml') == (RES/'raw/watchface.xml').read_bytes(), 'Packaged scene differs from validated XML'
        xml=E.fromstring(z.read('res/raw/watchface.xml'))
        assert len(list(xml.iter()))<=8000,'Native object budget exceeded'
        for item in xml.iter():
            for attr in ('icon','resource','family'):
                if attr not in item.attrib:continue
                resource=item.get(attr)
                assert resource and resource.strip(),f'Empty {attr}'
                if resource.startswith('[COMPLICATION.'):continue
                suffix='.ttf' if attr=='family' else '.png'
                assert any(n.endswith('/'+resource+suffix) for n in names),f'Packaged reference missing: {resource}'
        if any(i.get('resource','').startswith('trimmed_') for i in xml.iter('Image')):
            import json
            manifest=json.loads((ROOT/'docs/optimization/geometry-sources.json').read_text(encoding='utf-8'))
            decoded=0
            for filename in manifest['runtime_png_names']:
                packed,actual=graphic_name(filename+'.png')
                assert same_graphic(packed,RES/'drawable-nodpi'/actual),filename
                with Image.open(BytesIO(z.read(packed))) as bitmap:decoded+=bitmap.width*bitmap.height*4
            baseline=json.loads((ROOT/'docs/optimization/baseline.json').read_text())
            assert decoded<=baseline['all_png_decoded_rgba_bytes'],'Decoded PNG memory grew'
        cfg=xml.find('UserConfigurations/ListConfiguration[@id="HandSize"]')
        assert cfg is not None and cfg.get('defaultValue')=='Original' and tuple(o.get('id') for o in cfg)==tuple(HAND_SIZES)
        filename='runtime_classic_scale_alpha.png';packed,actual=graphic_name(filename)
        assert same_graphic(packed,RES/'drawable-nodpi'/actual),filename
        scales=xml.findall('.//PartImage[@name="instrument_classic_custom_scale"]')
        assert scales and {p.get('tintColor') for p in scales}=={'#E47D38','#A34B24','#222A29','#F0F0E7'}
        for bg in BACKGROUNDS:
            face=xml.find(f'.//Group[@name="dial_instrument_classic_{bg}"]')
            assert face is not None and not face.findall('.//PartText[@name="hour_number_12"]')
            assert face.findall('.//PartImage[@name="instrument_classic_custom_scale"]')
        cfg=xml.find('UserConfigurations/ListConfiguration[@id="MinuteTrackStyle"]')
        assert cfg is not None and cfg.get('defaultValue')=='None' and tuple(o.get('id') for o in cfg)==MINUTE_TRACKS
        for part in ('hour','minute'):
            for tone in ('light','dark'):
                for kind in ('instrument_refined',):
                    filename=f'precision_{part}_{kind}_{tone}.png'
                    packed,actual=graphic_name(filename)
                    assert same_graphic(packed,RES/'drawable-nodpi'/actual),f'Packaged graphic differs: {filename}'
        assert not any('/precision_hour_bellross_photo_' in n or '/precision_minute_bellross_photo_' in n or n.endswith('/photo_bellross_hub.png') for n in names),'Photographic hand resources remain in APK'
        for bg in BACKGROUNDS:
            for part in ('hour','minute','hub'):
                for prefix in ('instrument_classic','instrument_classic_clean'):
                    filename=f'{prefix}_{part}_{bg}.png'
                    packed,actual=graphic_name(filename)
                    assert same_graphic(packed,RES/'drawable-nodpi'/actual),filename
            branch=xml.find(f'.//Group[@name="hands_aviator_{bg}"]')
            if branch is None:branch=xml.find(f'.//Group[@name="hands_shared_aviator_{bg}"]')
            images=[i.get('resource') for i in branch.findall('.//Image')]
            for part in ('hour','minute','hub'):assert any(n in images for n in (f'instrument_classic_{part}_{bg}',f'trimmed_instrument_classic_{part}_{bg}'))
        for style in ('instrument','aviator'):
            ticks=xml.findall(f'.//Group[@name="dial_{style}_black"]//Group[@name="hour_and_subhour_ticks"]')
            if not ticks:
                assert xml.findall(f'.//Group[@name="dial_{style}_black"]//Image')
            else:assert all(len(g.findall('Group/PartDraw/RoundRectangle'))==96 for g in ticks)
        for id,options in {'style':STYLES,'HandStyle':HAND_STYLES,'background':('white','ivory','black'),'sectors':('none','lines','labels','color'),'boundaries':('quarter','shifted_back_1_hour'),'dividers':('micro','radial','full','arc','classic')}.items():
            cfg=xml.find(f'UserConfigurations/ListConfiguration[@id="{id}"]')
            assert cfg is not None and tuple(o.get('id') for o in cfg)==options, f'Packaged native setting missing: {id}'
        assert 'assets/font-licenses.txt' in names, 'Font licenses missing'
        assert len([n for n in names if n.startswith('res/font/') and n.endswith('.ttf')])==5, 'Bundled typography incomplete'
        assert any(n.endswith('/watch_face_info.xml') for n in names), 'WatchFaceInfo missing'
        assert 'AndroidManifest.xml' in names
        assert any(n.endswith('/preview.png') for n in names), 'Picker preview missing'
    print(f'PASS: {path.name}; resource-only APK, validated scene and picker resources present.')
    print(f'Size: {path.stat().st_size} bytes')
    print(f'SHA-256: {hashlib.sha256(path.read_bytes()).hexdigest()}')

if __name__=='__main__':verify(Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'dist/Podolskii24-debug.apk')
