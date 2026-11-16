"""Closed, supersampled minute contours replacing the old stacked thin lines."""
import xml.etree.ElementTree as E
from generate import ROOT,RES
from instrument_classic import NS,raster
from hand_updates import cropped_asset

def apply(root):
    records={}
    for part in root.iter('PartImage'):
        image=part.find('Image');name=image.get('resource','')
        if not name.startswith(('trimmed_precision_minute_needle_',
                'trimmed_precision_minute_vintage_','trimmed_precision_minute_instrument_',
                'trimmed_minute_classic_','trimmed_minute_minimal_','trimmed_minute_instrument_')):continue
        dark=name.endswith('_dark')
        family='instrument' if 'instrument' in name else ('vintage' if 'vintage' in name else 'neutral')
        key=family+('_dark' if dark else '_light')
        if key not in records:
            # All coordinates local to (210,26,12,214); exact pivot (6,190).
            svg=E.Element('{'+NS+'}svg',viewBox='0 0 12 214')
            E.SubElement(svg,'{'+NS+'}title').text='Closed minute blade / '+key+'; pivot 6,190'
            body='#CDD2C8' if dark else '#29312B'
            rim='#202820' if dark else '#D9DCD1'
            front={'neutral':body,'vintage':'#B94A38','instrument':'#E58B35'}[family]
            E.SubElement(svg,'{'+NS+'}path',d='M6 8 L7.8 18 L8.1 174 L7.5 209 L4.5 209 L3.9 174 L4.2 18 Z',fill=body,stroke=rim,**{'stroke-width':'.45','stroke-linecap':'round','stroke-linejoin':'round'})
            E.SubElement(svg,'{'+NS+'}path',d='M6 8 L7.5 18 L7.8 92 L4.2 92 L4.5 18 Z',fill=front)
            folder=ROOT/'docs/hand-masters/minute-blades';folder.mkdir(exist_ok=True)
            path=folder/(key+'.svg');E.indent(svg);E.ElementTree(svg).write(path,encoding='utf-8',xml_declaration=True)
            resource='minute_blade_'+key
            records[key]=(resource,cropped_asset(raster(path),(210,26,12,214),resource))
        resource,(x,y,w,h)=records[key]
        part.attrib.update(x=str(x),y=str(y),width=str(w),height=str(h),pivotX=str((216-x)/w),pivotY=str((216-y)/h))
        image.set('resource',resource)
