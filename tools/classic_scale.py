"""Drawn numeral skeletons and reference-inspired chapter marks. No font/image input."""
import math
import xml.etree.ElementTree as E
from PIL import Image
from generate import ROOT,RES
from instrument_classic import raster,NS

INKS={'orange':'#E47D38','brown':'#A34B24','ink':'#222A29','paper':'#F0F0E7'}
GLYPHS={
 '1':(('M',4,2),('L',4,55)),
 '2':(('M',4,8),('C',15,1,31,0,41,6),('C',51,12,49,23,40,28),('C',31,33,14,29,7,42),('C',4,47,4,51,4,55),('L',48,55)),
 '4':(('M',40,2),('L',5,37),('L',49,37),('M',40,2),('L',40,56)),
 '6':(('M',43,6),('C',27,-2,6,2,4,24),('C',2,43,12,55,28,55),('C',43,55,49,48,49,38),('C',49,26,37,22,24,24),('C',14,25,7,28,5,30)),
 '8':(('M',26,28),('C',12,28,4,23,4,15),('C',4,5,14,1,26,1),('C',40,1,49,6,49,15),('C',49,23,41,28,26,28),('C',12,28,3,34,3,43),('C',3,53,14,57,26,57),('C',41,57,50,53,50,43),('C',50,34,41,28,26,28)),
}
# Each value is an optical composition, rather than four equal text boxes.
NUMERALS={12:(216,84,'12',1.0),6:(78,216,'6',1.0),18:(352,216,'18',.83),24:(216,354,'24',.69)}

def tick_specs():
    for i in range(96):
        if i%24==0:length,width=22,7.4
        elif i%8==0:length,width=42,7.2
        elif i%4==0:length,width=19,2.3
        elif i%2==0:length,width=11,1.2
        else:length,width=7.5,.95
        yield i*3.75,195-length,195,width

def path(root,commands,color,stroke=False,width=8):
    data=' '.join(cmd+' '.join(f'{v:.5f}' for v in values) for cmd,*values in commands)
    attrs=dict(d=data,fill='none' if stroke else color)
    if stroke:attrs.update(stroke=color,**{'stroke-width':str(width),'stroke-linecap':'round','stroke-linejoin':'round'})
    return E.SubElement(root,'{'+NS+'}path',attrs)

def plate(ink):
    root=E.Element('{'+NS+'}svg',viewBox='0 0 432 432',width='432',height='432')
    E.SubElement(root,'{'+NS+'}title').text='Instrument Classic / custom 24-hour numerals and 96 marks'
    for a,inner,outer,w in tick_specs():
        r=w/2;y0=216-outer;y1=216-inner;k=.55228475
        cmds=(('M',216,y0),('C',216+r*k,y0,216+r,y0+r*(1-k),216+r,y0+r),('L',216+r,y1-r),('C',216+r,y1-r*(1-k),216+r*k,y1,216,y1),('C',216-r*k,y1,216-r,y1-r*(1-k),216-r,y1-r),('L',216-r,y0+r),('C',216-r,y0+r*(1-k),216-r*k,y0,216,y0),('Z',))
        ca,sa=math.cos(math.radians(a)),math.sin(math.radians(a));rotated=[]
        for cmd,*vals in cmds:
            points=[]
            for x,y in zip(vals[::2],vals[1::2]):points.extend((216+(x-216)*ca-(y-216)*sa,216+(x-216)*sa+(y-216)*ca))
            rotated.append((cmd,*points))
        el=path(root,rotated,ink);el.set('id',f'tick_{a}')
    for hour,(cx,cy,word,sx) in NUMERALS.items():
        widths=[8 if d=='1' else 52 for d in word];gap=11
        total=(sum(widths)+gap*(len(word)-1))*sx;xbase=cx-total/2
        for digit,dw in zip(word,widths):
            # Split pen lifts so no artificial connector crosses the open 4.
            sub=[]
            for cmd,*vals in GLYPHS[digit]:
                if cmd=='M' and sub:
                    path(root,sub,ink,True).set('id',f'number_{hour}_{digit}_part');sub=[]
                out=[]
                for x,y in zip(vals[::2],vals[1::2]):out.extend((xbase+x*sx,cy-28+y))
                sub.append((cmd,*out))
            if sub:el=path(root,sub,ink,True);el.set('id',f'number_{hour}_{digit}')
            xbase+=(dw+gap)*sx
    return root

def resource(color):
    return 'classic_scale_'+next(key for key,value in INKS.items() if value==color)

def main():
    out=ROOT/'docs/scale-masters/instrument-classic';out.mkdir(parents=True,exist_ok=True)
    for key,ink in INKS.items():
        svg=plate(ink);E.indent(svg,space='  ');path_=out/f'classic_scale_{key}.svg'
        E.ElementTree(svg).write(path_,encoding='utf-8',xml_declaration=True)
        raster(path_).resize((864,864),Image.Resampling.BOX).save(RES/'drawable-nodpi'/f'classic_scale_{key}.png')

if __name__=='__main__':main()
