"""Small, transparent hand assets drawn from explicit paths. No runtime code."""
from PIL import Image, ImageDraw
from generate import RES, LEGACY_STYLES

S=6
def make(style,tone,minute=False):
    x0,y0,w,h=(208,34,16,204) if minute else (200,72,32,176)
    im=Image.new('RGBA',(w*S,h*S));d=ImageDraw.Draw(im)
    dark=tone=='dark';ink='#E9EEE8' if dark else '#202B2A';edge='#172321' if dark else '#F7F6EE'
    accent=('#EAA05C' if dark else '#A34D19') if style=='instrument' else ('#E16F58' if dark else '#A02F28')
    def p(pt):return ((pt[0]-x0)*S,(pt[1]-y0)*S)
    def polygon(points,fill,outline=edge,width=.7):
        pts=[p(v) for v in points];d.polygon(pts,fill=fill)
        d.line(pts+[pts[0]],fill=outline,width=round(width*S),joint='curve')
    def line(a,b,fill,width):d.line([p(a),p(b)],fill=fill,width=max(1,round(width*S)))
    def circle(cx,cy,r,fill):
        a=p((cx-r,cy-r));b=p((cx+r,cy+r));d.ellipse((*a,*b),fill=fill)
    if minute:
        width={'classic':1.2,'minimal':1,'sputnik':1.5,'instrument':2}[style]
        line((216,236),(216,40),edge,width+1.1)
        line((216,236),(216,40),accent if style in ('sputnik','instrument') else ink,width)
        if style=='instrument':line((216,43),(216,89),ink,1)
    elif style=='classic':
        polygon([(216,80),(218.8,204),(217.5,237),(214.5,237),(213.2,204)],ink)
        circle(216,216,4.3,ink)
    elif style=='minimal':
        line((216,235),(216,79),edge,4.1);line((216,235),(216,79),ink,2.3)
        circle(216,216,3.4,ink);circle(216,235,2,ink)
    elif style=='sputnik':
        polygon([(216,80),(221,123),(218.6,204),(216,240),(213.4,204),(211,123)],ink)
        polygon([(216,88),(219.4,125),(216,163),(212.6,125)],accent,ink,.6)
        circle(216,216,5.2,accent);circle(216,216,2.2,ink)
    else:
        polygon([(216,79),(222,105),(220.3,205),(218,238),(214,238),(211.7,205),(210,105)],accent,edge,1)
        line((216,112),(216,164),ink,2.5)
        circle(216,216,5.5,edge);circle(216,216,3.8,accent)
    return im.resize((w*2,h*2),Image.Resampling.LANCZOS)

def main():
    out=RES/'drawable-nodpi';out.mkdir(exist_ok=True)
    for style in LEGACY_STYLES:
        for tone in ('light','dark'):
            for minute in (False,True):
                make(style,tone,minute).save(out/f'{"minute" if minute else "hand"}_{style}_{tone}.png')
    from hand_art import main as precision_assets
    precision_assets()
if __name__=='__main__':main()
