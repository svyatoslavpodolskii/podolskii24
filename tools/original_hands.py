"""Original 1.0 native geometry recovered verbatim from its delivery archive.
Rotation is supplied by the existing parent; all draw commands are unchanged.
"""
from generate import group,draw,condition,line,C
THEMES = {
    'white': ('#F5F2EA', '#202321', '#202321', ('#E6DFC7', '#F1EDDF', '#B8B3A7', '#303735')),
    'black': ('#000000', '#EEEEEA', '#EEEEEA', ('#202420', '#171B1C', '#252321', '#090B0D')),
    'sputnik': ('#E5DFCA', '#252E2B', '#A5382C', ('#D4D4B2', '#E8DFC7', '#ABA698', '#293431')),
    'orange': ('#000000', '#EF842E', '#EF842E', ('#30271B', '#211E18', '#30221A', '#0B0C0B')),
}

def artwork(parent,theme,minute=False):
    ambient=False
    fg= '#BCC1BE' if ambient else THEMES[theme][2 if not minute else 1]
    g=group(parent,('minute' if minute else 'hour')+('_aod' if ambient else ''))
    g.set('name',('original_minute_' if minute else 'original_hour_')+theme)
    d=draw(g)
    if minute:
        if not ambient and theme in ('white','sputnik'):
            outline=draw(condition(g,'[CONFIGURATION.sectors] == "color"'))
            line(outline,(C,C+21),(C,44),'#E5E5DA',3.4,'ROUND')
            g.remove(d);g.append(d)
        line(d,(C,C+21),(C,44),fg,1.4,'ROUND')
    else:
        widths={'white':3.6,'black':2.5,'sputnik':3.8,'orange':6}
        if not ambient and theme in ('white','sputnik'):
            outline=draw(condition(g,'[CONFIGURATION.sectors] == "color"'))
            line(outline,(C,C+24),(C,72),'#E5E5DA',8 if theme=='sputnik' else 6,'ROUND')
            # Keep the contrasting outline below the foreground stroke.
            g.remove(d);g.append(d)
        line(d,(C,C+24),(C,72),fg,2 if ambient else widths[theme],'ROUND')
        if theme=='orange' and not ambient:
            line(d,(C,130),(C,88),fg,9,'BUTT')
        if theme=='sputnik' and not ambient:
            line(d,(C,C+22),(C,80),'#252E2B',6,'ROUND')
            line(d,(C,145),(C,85),fg,2.8,'ROUND')
    return g