"""Non-destructive scene migration and production inclusion."""
from .narrative import SEPARATOR

def is_separator(s):
    return bool(s.get('is_separator') or SEPARATOR.fullmatch(s.get('source_text',s['text'])))

def included(s):
    return not s.get('excluded',False) and not is_separator(s)

def detect_scenes(p):
    # No original text, speaker, voice or audio is rewritten. Legacy dot-only
    # paragraphs remain as excluded structural records, with the same IDs.
    if p.get('scene_rules_version')==1:return
    for ch in p['chapters']:
        scene=1;previous_old=None;pending=False;has_content=False
        for s in ch['segments']:
            old=s.get('scene',1)
            if is_separator(s):
                s.update(is_separator=True,excluded=True)
                pending=True
            else:
                if has_content and (pending or previous_old is not None and old!=previous_old):scene+=1
                pending=False;has_content=True
            if s.get('scene')!=scene or s.get('is_separator'):
                s['revision']=s.get('revision',0)+1
            s['scene']=scene
            previous_old=old
    p['scene_rules_version']=1
