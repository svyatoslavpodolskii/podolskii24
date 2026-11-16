"""Small original vector lettering, independent of system/font substitution."""
import re
import xml.etree.ElementTree as E
from generate import ROOT, RES

# Broad humanist sans strokes, x-height 10, cap height 15. Separate contours
# keep counters open at watch size. O is the emblem itself, not a framed glyph.
GLYPHS={
 'B':(10,['M 1 16 L 1 1 L 5.5 1 C 10 1 10 8 5.5 8 L 1 8','M 5.5 8 C 11 8 11 16 5.5 16 L 1 16']),
 'e':(9,['M 1 11 L 8 11 C 8 4 1 4 1 11 C 1 16 5 17 8 14']),
 'l':(3,['M 1 1 L 1 16']),
 'O':(19,['M 9.5 0 C 0 0 0 18 9.5 18 C 19 18 19 0 9.5 0 Z']),
 'r':(7,['M 1 16 L 1 6','M 1 9 C 3 5 5 5 6 6']),
 'u':(9,['M 1 6 L 1 12 C 1 18 8 17 8 12 L 8 6','M 8 12 L 8 16']),
 's':(8,['M 7 7 C 1 3 0 10 4 11 C 10 13 6 19 1 15']),
 'P':(10,['M 1 16 L 1 1 L 5.5 1 C 11 1 11 9 5.5 9 L 1 9']),
 'o':(9,['M 4.5 6 C -1 6 -1 16 4.5 16 C 10 16 10 6 4.5 6 Z']),
 'd':(9,['M 8 1 L 8 16','M 8 8 C -2 0 -2 23 8 14']),
 'k':(8,['M 1 1 L 1 16','M 7 6 L 1 12','M 3.5 10 L 8 16']),
 'i':(3,['M 1 6 L 1 16','M 1 1 L 1 2']),
}

def artwork():
    from instrument_classic import raster,NS
    out=ROOT/'docs/hand-masters/wordmarks';out.mkdir(parents=True,exist_ok=True)
    records={}
    for word in ('BelOrus','Podolskii'):
        widths=[GLYPHS[c][0] for c in word]
        width=sum(widths)+1.8*(len(word)-1)+4
        svg=E.Element('{'+NS+'}svg',viewBox=f'0 0 {width} 24')
        x=2
        for char in word:
            for contour in GLYPHS[char][1]:
                axis=0
                def shift(match):
                    nonlocal axis
                    value=float(match[0])+(x if axis%2==0 else 3)
                    axis+=1
                    return f'{value:.3f}'
                path=re.sub(r'-?\d+(?:\.\d+)?',shift,contour)
                E.SubElement(svg,'{'+NS+'}path',d=path,fill='none',stroke='#FFFFFF',
                    **{'stroke-width':'1.35','stroke-linecap':'round','stroke-linejoin':'round'})
            x+=GLYPHS[char][0]+1.8
        name='dial_wordmark_'+word.lower();path=out/(name+'.svg')
        E.indent(svg,space='  ');E.ElementTree(svg).write(path,encoding='utf-8',xml_declaration=True)
        raster(path).save(RES/'drawable-nodpi'/(name+'.png'))
        records[word]=(name,width)
    return records
