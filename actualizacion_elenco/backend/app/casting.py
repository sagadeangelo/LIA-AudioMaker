"""Persistent character profiles and reversible, per-segment assignments."""
import copy
import uuid
from .narrative import key

FIELDS=('speaker','character_id','speaker_confirmed','voice','speed','color','audio','duration',
        'review','content_review','review_reason')

def needs_content_review(s):
    if 'content_review' in s: return bool(s['content_review'])
    return bool(s.get('review') and (s.get('kind') in ('thought_or_quote','aside_candidate')
        or 'acotaci' in s.get('review_reason','').lower()))

def ensure_cast(p):
    cast=p.setdefault('characters',[])
    known={key(c['name']) for c in cast}
    # Narrator remains available even for an empty project.
    segments=[s for ch in p['chapters'] for s in ch['segments']]
    narrator=next((s for s in segments if key(s.get('speaker',''))=='narrador'),
                  {'speaker':'Narrador','voice':'es','speed':160,'color':'#00D9CE'})
    seeds=[narrator]+segments
    for s in seeds:
        name=s.get('speaker','').strip()
        if not name or key(name) in ('sin atribuir','sin asignar') or key(name) in known: continue
        known.add(key(name))
        cast.append({'id':str(uuid.uuid5(uuid.NAMESPACE_URL,p['id']+':'+key(name))),
            'name':name,'voice':s.get('voice','es'),'speed':s.get('speed',160),
            'color':s.get('color','#F018A8')})
    return cast

def assign(p,s,character):
    token=str(uuid.uuid4())
    before={k:copy.deepcopy(s[k]) for k in FIELDS if k in s}
    revision=s.get('revision',0)+1
    pending=needs_content_review(s)
    changed=any(s.get(k)!=character[k] for k in ('voice','speed')) or key(s.get('speaker',''))!=key(character['name'])
    s.update(speaker=character['name'],character_id=character['id'],speaker_confirmed=True,
        voice=character['voice'],speed=character['speed'],color=character['color'],
        content_review=pending,review=pending,revision=revision)
    if changed: s.update(audio=None,duration=0)
    if not pending: s['review_reason']=''
    history=p.setdefault('assignment_undo',{})
    history[token]={'segment_id':s['id'],'revision':revision,'before':before}
    while len(history)>30: del history[next(iter(history))]
    return token

def undo(p,s,token):
    entry=p.get('assignment_undo',{}).get(token)
    if not entry or entry['segment_id']!=s['id']: raise ValueError('La asignación ya no está disponible para deshacer.')
    if s.get('revision',0)!=entry['revision']: raise ValueError('El fragmento cambió después de asignarlo. No se sobrescribieron esos cambios.')
    for k in FIELDS:
        if k in entry['before']: s[k]=copy.deepcopy(entry['before'][k])
        else: s.pop(k,None)
    s['revision']=entry['revision']+1
    del p['assignment_undo'][token]
