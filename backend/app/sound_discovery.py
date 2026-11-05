"""Refresh sound spotting without replacing saved analyses or user decisions."""
import hashlib
from fastapi import APIRouter,HTTPException
from pydantic import BaseModel,Field
from .narrative import key
from .narrative_cues import sound_cues
from .sound_direction import editorial
from .scenes import included
from .voice_editor import now

router=APIRouter(prefix='/discovery',tags=['Expanded sound discovery'])


def main():
    from . import main as m
    return m


def discover(p):
    from .manuscript_analysis import document_token
    from .sound_checklist import ALIASES
    prior={}
    for a in p.get('manuscript_reviews',[]):
        if a.get('category')!='sound' or a.get('undone_at'):continue
        e=a.get('evidence',{});label=ALIASES.get(key(e.get('label','')),key(e.get('label','')))
        prior[(e.get('segment_id'),label,key(e.get('cue','')))]=a.get('decision')
    chapters=[];items=[]
    for ch in p['chapters']:
        skipped=editorial(ch['title']);count=0
        if not skipped:
            for index,s in enumerate(ch['segments'],1):
                if not included(s) or editorial(ch['title'],s['text']):continue
                for cue in sound_cues(s['text']):
                    label=ALIASES.get(key(cue['label']),key(cue['label']))
                    identity=f'{s["id"]}:{label}:{cue["start"]}:{cue["end"]}:{cue["cue"]}'
                    item={**cue,'id':hashlib.sha256(identity.encode()).hexdigest()[:24],'chapter_id':ch['id'],'chapter':ch['title'],
                        'segment_id':s['id'],'scene':s.get('scene',1),'fragment':index,'text':s['text'][:800],'excluded':False}
                    item['decision']=prior.get((s['id'],label,key(cue['cue'])))
                    items.append(item);count+=1
        chapters.append({'id':ch['id'],'title':ch['title'],'excluded_editorial':skipped,'suggestions':count,
            'needs_manual_review':not skipped and count==0})
    return {'document_token':document_token(p),'chapters':chapters,'items':items,'pending':sum(not x['decision'] for x in items),
        'method':'Detección local ampliada por acciones y contexto. Las inferencias requieren revisión humana.'}


@router.get('')
def scan(pid:str):
    with main().lock:p=main().get(pid)
    return discover(p)


class Decisions(BaseModel):
    document_token:str
    ids:list[str]=Field(min_length=1,max_length=5000)
    decision:str=Field(pattern=r'^(confirm|reject)$')


@router.post('/review')
def review(pid:str,body:Decisions):
    m=main()
    with m.lock:
        p=m.get(pid);report=discover(p)
        if body.document_token!=report['document_token']:raise HTTPException(409,'El manuscrito cambió. Vuelve a buscar indicios antes de autorizar.')
        by_id={x['id']:x for x in report['items']}
        if not all(i in by_id for i in body.ids):raise HTTPException(409,'Una sugerencia ya no está vigente. Actualiza la búsqueda.')
        added=0
        for identity in dict.fromkeys(body.ids):
            item=by_id[identity]
            if item['decision']:continue
            p.setdefault('manuscript_reviews',[]).append({'at':now(),'job_id':'expanded-sound-discovery-v1','category':'sound',
                'item_id':identity,'decision':body.decision,'evidence':item})
            added+=1
        if added:m.save(p)
    return {'added':added,'report':discover(p)}
