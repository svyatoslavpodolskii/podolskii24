"""Small native-only usability fixes, with inverse records for legacy contracts."""
import hashlib
import math
import xml.etree.ElementTree as E

SIZE_EXPR='[CONFIGURATION.HandSize] == "Compact" ? 0.92 : [CONFIGURATION.HandSize] == "Large" ? 1.06 : 1.0'

def apply(root,canonical):
    hands=root.find('.//Group[@name="interactive_hands"]')
    for axis in ('scaleX','scaleY'):E.SubElement(hands,'Transform',target=axis,value=SIZE_EXPR)
    for body in hands.findall('Condition/Compare/Group'):
        hour=body.find('Group[@name="hour"]')
        minute=next(c for c in body if c.find('.//Group[@name="minute"]') is not None)
        body.remove(hour);body.insert(list(body).index(minute)+1,hour)
        for parent in list(body.iter()):
            for child in list(parent):
                if child.tag!='Condition':continue
                expression=child.find('Expressions/Expression')
                if expression is None or not (expression.text or '').startswith('[CONFIGURATION.HandSize]'):continue
                index=list(parent).index(child);parent.remove(child)
                if '"Original"' in expression.text:
                    for i,item in enumerate(list(child.find('Compare'))):parent.insert(index+i,item)
    slots=[]
    for slot in root.findall('Scene/ComplicationSlot'):
        slots.append(canonical(slot))
        slot.set('x',str(int(slot.get('x'))-20));slot.set('y',str(int(slot.get('y'))-20))
        slot.set('width','96');slot.set('height','96')
        bounds=slot.find('BoundingOval');bounds.set('width','96');bounds.set('height','96')
        for group in slot.findall('.//Group'):
            if group.get('name','').startswith('slot'):
                group.set('pivotX','0');group.set('pivotY','0');group.set('scaleX',str(96/56));group.set('scaleY',str(96/56))
    labels={}
    for label in root.findall('.//PartText'):
        if not label.get('name','').startswith('period_label_'):continue
        original=canonical(label)
        w,h=float(label.get('width')),float(label.get('height'))
        cx,cy=float(label.get('x'))+w/2,float(label.get('y'))+h/2
        radius=math.hypot(cx-216,cy-216)
        for attr,center,dim in (('x',cx,w),('y',cy,h)):
            target=round(216+(center-216)*110/radius-dim/2)
            E.SubElement(label,'Transform',target=attr,value=f'[CONFIGURATION.MinuteTrackStyle] == "None" ? {label.get(attr)} : {target}')
        labels[hashlib.sha256(canonical(label).encode()).hexdigest()]=original
    return dict(slot_design_sources=slots,label_design_sources=labels)
