"""Offline before/after QA against the checkpoint; never a device screenshot."""
import gzip
import itertools
import json
import xml.etree.ElementTree as E
from PIL import ImageChops,ImageStat
from generate import ROOT,RES,STYLES,BACKGROUNDS,MINUTE_TRACKS,DIVIDERS
import render as renderer

def main():
    baseline=E.fromstring(gzip.decompress((ROOT/'docs/optimization/baseline.xml.gz').read_bytes()))
    native=E.parse(RES/'raw/watchface.xml').getroot()
    modes=[('none','quarter','None','micro',3,0),('color','quarter','SputnikRing','classic',10,30),('color','shifted_back_1_hour','InstrumentRing','arc',18,0)]
    cases=[dict(style=s,background=b,sectors=m,boundaries=p,minute=True,minute_track=t,dividers=d,hour=h,mins=mi) for (s,b),(m,p,t,d,h,mi) in itertools.product(itertools.product(STYLES,BACKGROUNDS),modes)]
    cases += [dict(style=s,background='ivory',minute_track=t) for s,t in itertools.product(STYLES,MINUTE_TRACKS)]
    cases += [dict(style='sputnik',background='ivory',sectors='color',boundaries=p,dividers=d) for p,d in itertools.product(('quarter','shifted_back_1_hour'),DIVIDERS)]
    cases += [dict(style='classic',background='black',ambient=True,hour=h,mins=m) for h,m in ((3,0),(10,30),(18,0))]
    rows=[];panels=[];previous=renderer.scene
    try:
        for i,kw in enumerate(cases):
            renderer.scene=lambda:baseline;before=renderer.render(**kw)
            renderer.scene=lambda:native;after=renderer.render(**kw)
            diff=ImageChops.difference(before.convert('RGB'),after.convert('RGB'))
            mae=sum(ImageStat.Stat(diff).mean)/3
            rows.append(dict(case=kw,mean_absolute_channel_error=mae,max_error=max(hi for lo,hi in diff.getextrema())))
            # Native-size edges can differ slightly after pre-antialiasing; reject
            # large changes while exposing every measured error in the report.
            assert mae<=1.6,(kw,mae)
            if i<54 and kw['background']=='black':panels.extend([(kw['style']+' BEFORE',before),(kw['style']+' AFTER',after)])
        path=ROOT/'docs/optimization'
        (path/'visual-diff.json').write_text(json.dumps(rows,indent=2))
        renderer.sheet(panels,path/'visual-comparison.jpg',columns=6,tile=216)
        print('Visual cases:',len(rows),'maximum channel MAE:',max(r['mean_absolute_channel_error'] for r in rows))
    finally:renderer.scene=previous

if __name__=='__main__':main()
