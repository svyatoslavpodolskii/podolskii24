"""Forum artwork composed exclusively from final native-WFF local renders."""
from PIL import Image,ImageDraw,ImageFilter
from generate import ROOT
from render import render,font_file

OUT=ROOT/'dist/forum'

def clock(target,pic,x,y,size):
    pic=pic.resize((size,size),Image.Resampling.LANCZOS)
    shadow=Image.new('RGBA',target.size);d=ImageDraw.Draw(shadow)
    d.ellipse((x-4,y+8,x+size+4,y+size+18),fill=(0,0,0,150))
    target.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(16)))
    ImageDraw.Draw(target).ellipse((x-2,y-2,x+size+2,y+size+2),outline='#353C34',width=2)
    target.alpha_composite(pic,(x,y))

def face(style='instrument_classic',background='black',**kw):
    return render(style,background,output_size=864,**kw)

def cover():
    im=Image.new('RGBA',(2400,1350),'#111611');d=ImageDraw.Draw(im)
    d.text((112,112),'Podolskii24',font=font_file('barlow_semibold',190),fill='#F2F1E7')
    d.text((120,342),'24 ЧАСА · ОДИН ОБОРОТ',font=font_file('roboto_condensed',52),fill='#EA8847')
    d.text((120,430),'Нативный циферблат для Wear OS 6',font=font_file('roboto_condensed',36),fill='#ADB6A9')
    d.line((120,514,230,514),fill='#EA8847',width=4)
    d.text((120,565),'6 стилей · 21 вариант стрелок',font=font_file('roboto_condensed',40),fill='#E2E5DA')
    d.text((120,625),'Фоны, периоды суток и минутные дорожки',font=font_file('roboto_condensed',30),fill='#A6B09F')
    clock(im,face(hand_style='instrument_classic_clean',minute=True,hour=8,mins=11),1210,150,1060)
    for x,label,kw in ((120,'Sputnik',dict(style='sputnik',background='ivory',sectors='color',hand_style='vintage',hour=10,mins=30)),(432,'Classic',dict(style='classic',background='white',hand_style='needle',hour=16,mins=10)),(744,'Minimal',dict(style='minimal',background='black',hand_style='sword',minute=True,minute_track='TicksOnly',hour=10,mins=30))):
        clock(im,face(**kw),x,852,240)
        ImageDraw.Draw(im).text((x+4,1120),label,font=font_file('barlow_regular',32),fill='#D4DBCB')
    d=ImageDraw.Draw(im)
    d.text((120,1265),'WEAR OS 6+   /   WFF v4   /   PODOLSKII24 5.0',font=font_file('barlow_regular',26),fill='#8C9985')
    d.text((1410,1245),'Instrument Classic · без обводки',font=font_file('roboto_condensed',30),fill='#C2CBB9')
    im.convert('RGB').save(OUT/'01-cover.jpg',quality=96,subsampling=0)

def combinations():
    C=[]
    def add(title,caption,style,bg,**kw):C.append((title,caption,dict(style=style,background=bg,**kw)))
    add('Instrument Classic','Black · без обводки','instrument_classic','black',hand_style='instrument_classic_clean',minute=True,hour=8,mins=11)
    add('Instrument Classic','Black · Large · с обводкой','instrument_classic','black',hand_size='Large',minute=True,hour=8,mins=11)
    add('Instrument Classic','Ivory · Original','instrument_classic','ivory',hand_style='instrument_classic_clean',minute=True,hour=10,mins=30)
    add('Instrument Classic','White · Compact','instrument_classic','white',hand_size='Compact',minute=False,hour=3,mins=0)
    add('Instrument Classic','Ivory · Quarter · Color','instrument_classic','ivory',hand_style='instrument_classic_clean',sectors='color',minute=True,hour=15,mins=42)
    add('Instrument Classic','Black · Shifted · Color','instrument_classic','black',hand_style='instrument_classic_clean',sectors='color',boundaries='shifted_back_1_hour',hour=20,mins=0)
    add('Sputnik','Ivory · Quarter · Vintage','sputnik','ivory',sectors='color',hand_style='vintage',hour=10,mins=30)
    add('Sputnik','White · Shifted · Vintage Red','sputnik','white',sectors='color',boundaries='shifted_back_1_hour',hand_style='vintage_red',hour=3,mins=0)
    add('Sputnik','Ivory · Radial · SputnikRing','sputnik','ivory',sectors='lines',dividers='radial',minute_track='SputnikRing',hand_style='vintage',minute=True,hour=10,mins=30)
    add('Sputnik','Black · Sword','sputnik','black',hand_style='sword',minute=True,hour=14,mins=45)
    add('Classic','White · Needle · минуты','classic','white',hand_style='needle',minute_track='FiveMinuteLabels',minute=True,hour=9,mins=41)
    add('Classic','Ivory · Full · Sword','classic','ivory',sectors='lines',dividers='full',hand_style='sword',hour=16,mins=10)
    add('Classic','Black · Shifted · Color','classic','black',sectors='color',boundaries='shifted_back_1_hour',hand_style='needle',hour=22,mins=0)
    add('Minimal','Black · Sword · TicksOnly','minimal','black',hand_style='sword',minute_track='TicksOnly',minute=True,hour=10,mins=30)
    add('Minimal','White · Quarter · Labels','minimal','white',sectors='labels',hand_style='needle',hour=3,mins=0)
    add('Minimal','Ivory · прежняя Minimal','minimal','ivory',hand_style='legacy_minimal',minute=True,hour=19,mins=15)
    add('Instrument','Black · InstrumentRing','instrument','black',minute_track='InstrumentRing',minute=True,hour=10,mins=30)
    add('Instrument','Ivory · Color · Arc','instrument','ivory',sectors='color',dividers='arc',hand_style='instrument_white',hour=17,mins=25)
    add('Aviator','Black · Aviation','aviator','black',hand_style='aviation',minute=True,hour=8,mins=11)
    add('Aviator','Black · тонкая минутная','aviator','black',hand_style='bellross_needle',minute=True,hour=14,mins=20)
    return C

def gallery():
    im=Image.new('RGBA',(2400,2280),'#121812');d=ImageDraw.Draw(im)
    d.text((56,38),'Podolskii24 / 20 сочетаний',font=font_file('roboto_condensed',72),fill='#E8EDDF')
    d.text((60,128),'Оформления, стрелки, фоны и периоды суток',font=font_file('roboto_condensed',30),fill='#AEBDA3')
    for i,(title,caption,kw) in enumerate(combinations()):
        x=50+i%5*460;y=218+i//5*490
        clock(im,face(**kw),x,y,420)
        d=ImageDraw.Draw(im);d.text((x+8,y+430),f'{i+1:02}  {title}',font=font_file('roboto_condensed',25),fill='#E1E8D7')
        d.text((x+8,y+463),caption,font=font_file('roboto_condensed',21),fill='#9EAD94')
    ImageDraw.Draw(im).text((60,2222),'PODOLSKII24 5.0   /   24-ЧАСОВАЯ МЕХАНИКА   /   WEAR OS 6+',font=font_file('roboto_condensed',25),fill='#84967A')
    im.convert('RGB').save(OUT/'02-variants.jpg',quality=96,subsampling=0)

def main():
    OUT.mkdir(parents=True,exist_ok=True);cover();gallery()
    print('Forum artwork:',OUT)

if __name__=='__main__':main()
