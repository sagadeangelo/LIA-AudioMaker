"""Explainable story music direction and front-matter exclusion. No generated music."""
import re
from .narrative import key


def editorial(title,text=''):
    heading=key(title).strip()
    if re.match(r'^(?:\d+\s*[-—–.:]?\s*)?(?:paginas? iniciales|dedicatoria|prefacio|preambulo|indice|tabla de contenido|contenido|isbn|copyright|creditos|derechos reservados|acerca del autor|sobre el autor|biografia)\b',heading):return True
    return bool(re.match(r'^\s*(?:isbn\s*[:\d-]|copyright\b|todos los derechos reservados|©)',text,re.I))

MOODS=[
 ('euforia',r'\b(?:euforia|eufóric[oa]s?|júbilo|festejaban|celebraban|salt(?:ó|aban) de alegría)\b','uplifting cinematic celebration instrumental'),
 ('ira',r'\b(?:ira|rabia|cólera|enoj[oa]|enojad[oa]s?|furios[oa]s?|furia|indignad[oa]s?)\b','dramatic tension percussion instrumental'),
 ('suspenso',r'\b(?:miedo|terror|pánico|amenaza|peligro|acechaba|perseguían|escopeta|disparos?|corazón[^.!?]{0,50}lat\w*)\b','suspense cinematic pulse instrumental'),
 ('tristeza',r'\b(?:tristeza|triste|lloraba|lloró|solloz\w*|soledad|desolación|melancolía|duelo|nostalgia)\b','sad cinematic piano instrumental'),
 ('alegría',r'\b(?:alegría|feliz|felices|sonrió|reía|entusiasmo|esperanza|gozo)\b','hopeful cinematic storytelling instrumental'),
 ('ternura',r'\b(?:ternura|amor|enamorad[oa]|besó|abrazó|caricia)\b','warm gentle piano instrumental'),
 ('asombro',r'\b(?:asombr|maravill|sorprendid|extraordinari|mágic)\w*\b','wonder cinematic ambient instrumental'),
]
NEG=re.compile(r'\b(?:no|sin|nunca|jamás)\b(?:\W+\w+){0,3}\W*$',re.I)


def music_direction(title,text,approved_emotions=()):
    if editorial(title):return None
    hits=[]
    for label,pattern,query in MOODS:
        evidence=[]
        for match in re.finditer(pattern,text,re.I):
            prefix=re.split(r'[.!?;:,]',text[max(0,match.start()-50):match.start()])[-1]
            if not NEG.search(prefix):evidence.append(text[max(0,match.start()-40):min(len(text),match.end()+60)])
        if key(label) in {key(e) for e in approved_emotions}:evidence.append('Emoción autorizada en la revisión editorial: '+label)
        if evidence:hits.append(dict(mood=label,query=query,evidence=evidence[:3],score=len(evidence)))
    if not hits:return {'mood':'narrativo suave','query':'subtle cinematic storytelling instrumental','evidence':[], 'alternatives':[], 'reason':'Sin emoción dominante detectada: opción instrumental para revisar, no selección automática.'}
    hits.sort(key=lambda x:-x['score']);best=hits[0]
    return {**best,'alternatives':[h['mood'] for h in hits[1:]],'reason':'Dirección musical sugerida por indicios del texto y emociones autorizadas; revisa cambios de tono dentro de la escena.'}
