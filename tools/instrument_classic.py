"""Original vector artwork. SVG primitives are the only rasterization input.

Dimensions were measured against the reference, but no photo pixels, texture,
embedded images, gradients, or external resources enter these assets.
"""
import xml.etree.ElementTree as E
import re
import math
from PIL import Image,ImageDraw
from generate import ROOT,RES

PALETTES={
    'white':dict(body='#34362F',edge='#74766A',orange='#DB7635',orange_edge='#97502C',ring='#55574C',disk='#34362F',pin='#9B9C8C'),
    'ivory':dict(body='#393A31',edge='#77776A',orange='#D87937',orange_edge='#93512D',ring='#58594C',disk='#393A31',pin='#A1A18D'),
    'black':dict(body='#484A3F',edge='#7B7E6E',orange='#E5813F',orange_edge='#AD6235',ring='#626556',disk='#3C3E34',pin='#B7B8A3'),
}
HOUR=((216,94),(231.7,132.2),(228.1,165.1),(223.2,203.4),(222.1,218.3),(211.1,222.5),(203.9,200.3),(200.1,163.1),(195.3,137))
HOUR_LUME=((216,94),(231.7,132.2),(228.1,165.1),(200.1,163.1),(195.3,137))
MINUTE=((216,29.4),(223.7,43.6),(225.1,160),(225.8,206.5),(227.6,284.6),(206.1,284.7),(206.6,224.4),(207.4,160.4),(211.6,44.4))
MINUTE_LUME=((216,29.4),(223.7,43.6),(225.1,160),(207.4,160.4),(211.6,44.4))
MINUTE_PATH=(('M',216,29.4),('L',223.7,43.6),('L',225.1,160),('L',225.8,206.5),('L',227.3,275),('C',227.366,278,229.1,280.5,229.1,284.8),('C',229.1,291.4,223.8,296.7,217.2,296.7),('C',210.6,296.7,205.3,291.4,205.3,284.8),('C',205.3,280.5,206.388,278,206.4,275),('L',206.6,224.4),('L',207.4,160.4),('L',211.6,44.4),('Z',))
NS='http://www.w3.org/2000/svg'
E.register_namespace('',NS)

def rectangle(part):
    return {'hour':(192,40,48,208),'minute':(200,20,32,300),'hub':(202,202,28,28)}[part]

def svg(part,background,outlined=True):
    x0,y0,w,h=rectangle(part);p=PALETTES[background]
    root=E.Element('{'+NS+'}svg',viewBox=f'0 0 {w} {h}',width=str(w),height=str(h))
    E.SubElement(root,'{'+NS+'}title').text=f'Instrument Classic / {part} / {background}; pivot {216-x0},{216-y0}'
    def polygon(points,fill,stroke=None,width=.6):
        attrs=dict(points=' '.join(f'{x-x0},{y-y0}' for x,y in points),fill=fill)
        if stroke:attrs.update(stroke=stroke,**{'stroke-width':str(width),'stroke-linejoin':'round'})
        E.SubElement(root,'{'+NS+'}polygon',attrs)
    def circle(cx,cy,r,fill,stroke=None,width=.6):
        attrs=dict(cx=str(cx-x0),cy=str(cy-y0),r=str(r),fill=fill)
        if stroke:attrs.update(stroke=stroke,**{'stroke-width':str(width)})
        E.SubElement(root,'{'+NS+'}circle',attrs)
    if part=='hour':
        polygon(HOUR,p['body'],p['edge'],.65)
        polygon(HOUR_LUME,p['orange'],p['orange_edge'],.4)
    elif part=='minute':
        # One closed Bezier contour, including the rounded counterweight: no join seams.
        commands=[]
        for cmd,*coords in MINUTE_PATH:
            commands.append(cmd+' '.join(str(v-(x0 if i%2==0 else y0)) for i,v in enumerate(coords)))
        E.SubElement(root,'{'+NS+'}path',d=' '.join(commands),fill=p['body'],stroke=p['edge'],**{'stroke-width':'.65','stroke-linejoin':'round'})
        polygon(MINUTE_LUME,p['orange'],p['orange_edge'],.4)
    else:
        circle(216,216,12.6,p['disk'],p['edge'],.65)
        circle(216,216,10.5,p['ring'])
        circle(216,216,8.9,p['disk'])
        circle(216,216,1.5,p['pin'])
        circle(216.25,216.25,.65,p['body'])
    if not outlined:
        root.find('{'+NS+'}title').text=f'Instrument Classic Clean / {part} / {background}; pivot {216-x0},{216-y0}'
        for el in root.iter():
            for attr in ('stroke','stroke-width','stroke-linejoin'):el.attrib.pop(attr,None)
    return root

def raster(path):
    root=E.parse(path).getroot();_,_,w,h=map(float,root.get('viewBox').split());s=12
    im=Image.new('RGBA',(round(w*s),round(h*s)));d=ImageDraw.Draw(im)
    for el in root:
        tag=el.tag.split('}')[-1];fill=el.get('fill');edge=el.get('stroke');width=max(1,round(float(el.get('stroke-width',.6))*s))
        if fill=='none':fill=None
        if tag in ('polygon','path'):
            if tag=='polygon':pts=[tuple(float(v)*s for v in pair.split(',')) for pair in el.get('points').split()]
            else:
                tokens=re.findall(r'[MLCZ]|-?\d+(?:\.\d+)?',el.get('d'));pts=[];i=0
                while i<len(tokens):
                    cmd=tokens[i];i+=1
                    if cmd=='Z':break
                    count=6 if cmd=='C' else 2
                    vals=[float(v)*s for v in tokens[i:i+count]];i+=count
                    if cmd in ('M','L'):pts.append(tuple(vals))
                    else:
                        x0_,y0_=pts[-1];x1,y1,x2,y2,x3,y3=vals
                        for n in range(1,33):
                            t=n/32;u=1-t;pts.append((u**3*x0_+3*u*u*t*x1+3*u*t*t*x2+t**3*x3,u**3*y0_+3*u*u*t*y1+3*u*t*t*y2+t**3*y3))
            if fill:d.polygon(pts,fill=fill)
            closed=tag=='polygon' or el.get('d','').rstrip().endswith('Z')
            if edge:
                if el.get('stroke-linecap')=='round':
                    # Fill the stroke union directly. Pillow's curve joins on dense
                    # Bezier samples can leave radial cracks inside broad strokes.
                    points=pts+[pts[0]] if closed else pts;r=width/2
                    for (x0_,y0_),(x1,y1) in zip(points,points[1:]):
                        length=math.hypot(x1-x0_,y1-y0_)
                        if length:
                            nx,ny=-(y1-y0_)*r/length,(x1-x0_)*r/length
                            d.polygon(((x0_+nx,y0_+ny),(x1+nx,y1+ny),(x1-nx,y1-ny),(x0_-nx,y0_-ny)),fill=edge)
                    for x,y in pts:d.ellipse((x-r,y-r,x+r,y+r),fill=edge)
                else:d.line(pts+[pts[0]] if closed else pts,fill=edge,width=width,joint='curve')
        elif tag=='circle':
            cx,cy,r=(float(el.get(a))*s for a in ('cx','cy','r'))
            d.ellipse((cx-r,cy-r,cx+r,cy+r),fill=fill,outline=edge,width=width)
        else:assert tag=='title',f'Unsupported/non-vector SVG input: {tag}'
    return im.resize((round(w*3),round(h*3)),Image.Resampling.BOX)

def main():
    out=ROOT/'docs/hand-masters/instrument-classic';out.mkdir(parents=True,exist_ok=True)
    for bg in PALETTES:
        for part in ('hour','minute','hub'):
            name=f'instrument_classic_{part}_{bg}';path=out/f'{name}.svg'
            E.indent(tree:=svg(part,bg),space='  ');E.ElementTree(tree).write(path,encoding='utf-8',xml_declaration=True)
            raster(path).save(RES/'drawable-nodpi'/f'{name}.png')
    out=ROOT/'docs/hand-masters/instrument-classic-clean';out.mkdir(parents=True,exist_ok=True)
    for bg in PALETTES:
        for part in ('hour','minute','hub'):
            name=f'instrument_classic_clean_{part}_{bg}';path=out/f'{name}.svg'
            E.indent(tree:=svg(part,bg,False),space='  ');E.ElementTree(tree).write(path,encoding='utf-8',xml_declaration=True)
            raster(path).save(RES/'drawable-nodpi'/f'{name}.png')

def make(background,minute=False,clean=False):
    part='minute' if minute else 'hour'
    folder='instrument-classic-clean' if clean else 'instrument-classic';prefix='instrument_classic_clean' if clean else 'instrument_classic'
    return raster(ROOT/f'docs/hand-masters/{folder}'/f'{prefix}_{part}_{background}.svg')

if __name__=='__main__':main()
