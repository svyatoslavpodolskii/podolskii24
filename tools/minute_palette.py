"""Native WFF minute-track palettes, sharing all existing geometry and PNGs."""
import xml.etree.ElementTree as E

COLORS = ('#222A29', '#F0F0E7', '#8C332A', '#F29883', '#A34B16', '#F08A35')
PALETTES = {
    'original': COLORS,
    'neutral': ('#222A29', '#F0F0E7') * 3,
    'orange': ('#A34B16', '#F08A35') * 3,
    'green': ('#205B39', '#83D79B') * 3,
    'blue': ('#244E78', '#9BCBF0') * 3,
}

def apply(root, strings):
    track = root.find('.//Group[@name="shared_minute_tracks"]')
    assert track is not None
    masks = {n for mask in track.findall('.//PartDraw[@renderMode="MASK"]') for n in mask.iter()}
    actual = {n.get(a) for n in track.iter() if n not in masks for a in ('color', 'tintColor')
              if n.get(a, '').startswith('#')}
    assert actual <= set(COLORS), actual - set(COLORS)
    cfg = E.SubElement(root.find('UserConfigurations'), 'ListConfiguration',
        id='MinuteColor', displayName='minute_color', screenReaderText='minute_color', defaultValue='neutral')
    for key, colors in PALETTES.items():
        E.SubElement(cfg, 'ListOption', id=key, displayName='minute_color_'+key,
                     screenReaderText='minute_color_'+key)
    for n in list(track.iter()):
        if n in masks: continue
        for a in ('color', 'tintColor'):
            if n.get(a) in COLORS:
                index = COLORS.index(n.get(a))
                expr = ''.join(f'[CONFIGURATION.MinuteColor] == "{key}" ? {colors[index]} : '
                               for key, colors in PALETTES.items() if key != 'original') + n.get(a)
                E.SubElement(n, 'Transform', target=a, value=expr)
    labels = {'minute_color': 'Цвет минутной дорожки',
        'original': 'Исходный', 'neutral': 'Белый / тёмный',
        'orange': 'Оранжевый', 'green': 'Зелёный', 'blue': 'Голубой'}
    for key, value in labels.items():
        E.SubElement(strings, 'string', name=key if key=='minute_color' else 'minute_color_'+key).text=value
