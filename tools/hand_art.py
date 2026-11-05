"""Supersampled precision hands, with editable SVG masters and explicit pivot (216,216)."""
from PIL import Image,ImageDraw
from generate import ROOT,RES,HAND_STYLES

S=8
CORE=('needle','sword','vintage','instrument')
def make(kind,tone,minute=False,master=False,cutout=False):
    if kind in ('bellross_photo','instrument_classic_clean'):
        from instrument_classic import make as vector_art
        return vector_art('black' if tone=='dark' else 'white',minute,kind=='instrument_classic_clean')
    x0,y0,w,h=(208,26,16,216) if minute else (192,40,48,208)
    if minute and kind.startswith('bellross'):x0,y0,w,h=200,26,32,260
    im=Image.new('RGBA',(w*S,h*S));d=ImageDraw.Draw(im)
    dark=tone=='dark';body='#E3E8DF' if dark else '#25312F'
    edge='#18241F' if dark else '#EEEFE5';silver='#C1CBC3';steel='#687A72'
    orange='#EC8A32' if dark else '#AE4D12';red='#CA3D30';white='#F1EEDC';gray='#686F64'
    svg=[]
    def p(x,y):return ((x-x0)*S,(y-y0)*S)
    def polygon(points,fill,outline=None,width=.7):
        pts=[p(*v) for v in points];d.polygon(pts,fill=fill)
        if outline:d.line(pts+[pts[0]],fill=outline,width=round(width*S),joint='curve')
        svg.append('<polygon points="'+ ' '.join(f'{x-x0},{y-y0}' for x,y in points)+f'" fill="{fill}" stroke="{outline or "none"}" stroke-width="{width}" stroke-linejoin="round"/>')
    def line(a,b,color,width):
        d.line([p(*a),p(*b)],fill=color,width=max(1,round(width*S)))
        svg.append(f'<line x1="{a[0]-x0}" y1="{a[1]-y0}" x2="{b[0]-x0}" y2="{b[1]-y0}" stroke="{color}" stroke-width="{width}"/>')
    def circle(x,y,r,color,outline=None,width=.6):
        d.ellipse((*p(x-r,y-r),*p(x+r,y+r)),fill=color,outline=outline,width=max(1,round(width*S)))
        svg.append(f'<circle cx="{x-x0}" cy="{y-y0}" r="{r}" fill="{color}" stroke="{outline or "none"}" stroke-width="{width}"/>')
    if kind=='instrument_refined':
        # No circles in either bitmap: one fixed WFF hub covers both aligned stems.
        charcoal='#687266' if dark else '#3B453C'
        rim='#DADCCB' if dark else '#E9E4D5'
        if minute:
            polygon([(216,34),(218.1,44),(218.1,205),(217.5,228),(214.5,228),(213.9,205),(213.9,44)],charcoal,rim,.65)
            polygon([(216,34),(218.1,44),(218.1,161),(213.9,161),(213.9,44)],orange)
        else:
            polygon([(216,84),(223,117),(221,174),(219,205),(218.5,230),(213.5,230),(213,205),(211,174),(209,117)],charcoal,rim,.7)
            polygon([(216,84),(223,117),(221,163),(211,163),(209,117)],orange)
    elif kind.startswith('bellross'):
        # Trace of the supplied silhouettes, preserving their mechanical proportions.
        # Hour source: 48x136, pivot (24,116). Minute source: 60x400, pivot (30,294).
        # Neutral charcoal is deliberate: the reference has no white or gray insert.
        charcoal='#303128'; orange='#EB7D20'
        rim='#A3A394' if dark else '#E5E3D7'
        if minute:
            if kind=='bellross_needle':
                polygon([(216,33),(216.7,35),(217,214),(219.5,254),(220.2,275),(211.8,275),(212.5,254),(215,214),(215.3,35)],charcoal,rim,.35)
                line((216,34),(216,57),orange,1.2)
                circle(216,216,4.4,charcoal,rim,.35);circle(216,216,.8,'#171B16')
            else:
                # Uniform 0.60 scale of the long orange minute silhouette.
                polygon([(216,43.2),(222,56.4),(222,206),(221.4,228),(221.4,267),(210.6,267),(210.6,228),(210,206),(210,56.4)],charcoal,rim,.45)
                polygon([(216,43.2),(222,56.4),(222,177),(210,177),(210,56.4)],orange)
                circle(216,216,12,charcoal,rim,.4)
                circle(216,267,8.4,charcoal,rim,.4)
        else:
            polygon([(207,160),(225,160),(222,201),(233,216),(216,233),(199,216),(210,201)],charcoal,rim,.45)
            polygon([(216,104),(235,146),(230,176),(202,176),(197,146)],orange,charcoal,.6)
            circle(216,216,17,charcoal,rim,.45)
    elif minute:
        # Narrow, longer and simpler than the hour hand; modest counterweight.
        front=orange if kind.startswith(('instrument','aviation')) else (red if kind.startswith('vintage') else body)
        width=2.2 if kind.startswith('aviation') else (1.5 if kind.startswith('instrument') else 1.1)
        line((216,234),(216,33),edge,width+1.4)
        line((216,234),(216,33),body,width)
        line((216,112),(216,33),front,width)
        if kind.startswith('aviation'):
            polygon([(216,32),(218.3,39),(218.3,126),(213.7,126),(213.7,39)],orange,edge,.55)
        circle(216,216,2.5,body,edge,.5)
    elif kind=='needle':
        polygon([(216,59),(217.25,65),(217.65,207),(217.15,234),(214.85,234),(214.35,207),(214.75,65)],body,edge,.7)
        line((216,59),(216,65),body,.85)
        # A light steel ridge defines the last millimetres of the pointer on either polarity.
        line((216,64),(216,126),silver if not dark else white,.55)
        circle(216,216,3.8,body,edge,.65);circle(216,216,1.1,silver)
    elif kind=='sword':
        polygon([(216,59),(219.4,112),(220,206),(217.3,234),(214.7,234),(212,206),(212.6,112)],steel,edge,.85)
        polygon([(216,62),(216,230),(214.5,225),(212.85,204),(213.4,112)],silver)
        polygon([(216,62),(219,112),(219.4,204),(217.1,230),(216,230)],'#85958D' if dark else '#65756E')
        line((216,69),(216,205),white if dark else '#D5DCD3',.55)
        # Dark precision tip on pale faces; the pale perimeter still defines it on night sectors.
        line((216,59),(216,73),'#D9E1D7' if dark else '#31433A',.9)
        circle(216,216,4.4,steel,edge,.7);circle(216,216,2.9,silver)
    elif kind.startswith('vintage'):
        polygon([(216,59),(220.5,112),(220,199),(217,235),(215,235),(212,199),(211.5,112)],'#24312C',white,.7)
        # White luminous insert per Sputnik reference; previous red insert remains selectable.
        polygon([(216,63),(219.7,112),(217.5,162),(214.5,162),(212.3,112)],red,'#202C27',.5)
        if kind=='vintage':polygon([(216,68),(218.25,113),(216.8,153),(215.2,153),(213.75,113)],white)
        circle(216,216,4.6,red,edge,.65);circle(216,216,2.4,'#25312C')
    elif kind.startswith('instrument'):
        polygon([(216,59),(220.5,73),(220.1,197),(217.4,235),(214.6,235),(211.9,197),(211.5,73)],orange,edge,.9)
        # Gray is the principal version; the old white inlay is retained as another option.
        if cutout:
            assert kind=='instrument_white'
            d.line([p(216,83),p(216,177)],fill=(0,0,0,0),width=round(2*S))
        else:line((216,83),(216,177),white if kind=='instrument_white' else gray,2)
        circle(216,216,4.8,'#30372D',edge,.6);circle(216,216,2.8,orange)
    elif kind.startswith('aviation'):
        # Broad orange pointer and charcoal counterweight follow the supplied mechanical reference.
        rim='#858E7F' if dark else '#EEEFE5'
        polygon([(213.2,118),(218.8,118),(219.5,234),(212.5,234)],'#34372D',rim,.6)
        polygon([(216,59),(231.3,99),(226.7,134),(205.3,134),(200.7,99)],orange,'#30352B',.8)
        if kind=='aviation_gray':polygon([(216,68),(226.7,100),(223.4,126),(208.6,126),(205.3,100)],'#74796D')
        circle(216,216,6,'#34372D',rim,.55);circle(216,234,4.4,'#34372D',rim,.5)
    else:raise ValueError(kind)
    if master:
        name=f'{"minute" if minute else "hour"}_{kind}_{tone}'
        if cutout:name=f'hour_instrument_cutout_{tone}'
        out=ROOT/'docs/hand-masters';out.mkdir(exist_ok=True)
        shapes=''.join(svg)
        if cutout:
            defs=f'<defs><mask id="slot" maskUnits="userSpaceOnUse" x="0" y="0" width="{w}" height="{h}"><rect width="{w}" height="{h}" fill="white"/><line x1="24" y1="43" x2="24" y2="137" stroke="black" stroke-width="2"/></mask></defs>'
            shapes=defs+'<g mask="url(#slot)">'+shapes+'</g>'
        (out/f'{name}.svg').write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}"><title>{name}; pivot {216-x0},{216-y0}</title>'+shapes+'</svg>\n',encoding='utf-8')
    return im.resize((w*3,h*3),Image.Resampling.BOX if kind=='instrument_refined' else Image.Resampling.LANCZOS)

def main():
    out=RES/'drawable-nodpi';out.mkdir(exist_ok=True)
    for kind in HAND_STYLES[1:]:
        if kind.startswith(('legacy_','original_')) or kind in ('bellross_photo','instrument_classic_clean'):continue
        for tone in ('light','dark'):
            for minute in (False,True):
                make(kind,tone,minute,True).save(out/f'precision_{"minute" if minute else "hour"}_{kind}_{tone}.png')
    from instrument_classic import main as classic_assets
    classic_assets()
    from classic_scale import main as scale_assets
    scale_assets()
if __name__=='__main__':main()
