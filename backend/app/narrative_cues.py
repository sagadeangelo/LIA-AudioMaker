"""Local, explainable sound spotting; suggestions only, never audio mixing."""
import re

# label, kind, occurrence, non-literal exclusions
CUES = [
 ('mar', 'ambiente', r'\b(?:mar|océano|oleaje|olas|playa|costa)\b', r'\b(?:mar de (?:dudas|lágrimas|problemas)|ola de (?:calor|violencia)|olas de (?:calor|violencia))\b'),
 ('gaviotas', 'efecto', r'\b(?:gaviotas?|graznidos? de gaviotas?)\b', r''),
 ('claxon', 'efecto', r'\b(?:cl[aá]xon(?:es)?|bocinazos?|bocinas?|toc[oó] el claxon|pitidos? del (?:auto|coche))\b', r''),
 ('vehículo pasando', 'efecto', r'\b(?:autos?|coches?|carros?|automóviles?|camiones?|motocicletas?)\b[^.!?;\n]{0,70}\b(?:pas[aó]|pasaban?|pasando|cruz[aó]|aceler[aó]|circulaban?|circulando)\b|\b(?:pas[aó]|pasaban?|pasando|cruz[aó]|aceler[aó])\b[^.!?;\n]{0,70}\b(?:auto|coche|carro|automóvil|camión|motocicleta)s?\b', r''),
 ('tráfico', 'ambiente', r'\b(?:tráfico|tránsito|atasco|embotellamiento)\b', r'tráfico de (?:drogas|influencias|personas)'),
 ('lluvia', 'ambiente', r'\b(?:llovía|lloviendo|llover|lluvia)\b', r'lluvia de (?:ideas|críticas|elogios|besos|preguntas)'),
 ('viento', 'ambiente', r'\b(?:viento|ventarrón|ventisca)\b', r'vientos? de cambio'),
 ('río', 'ambiente', r'\b(?:río|arroyo|cascada)\b', r'río de (?:gente|lágrimas)'),
 ('aves', 'ambiente', r'\b(?:pájaros?|canto de aves|trinos?)\b', r''),
 ('grillos', 'ambiente', r'\bgrillos?\b', r''),
 ('perro', 'efecto', r'\b(?:ladridos?|ladr[aó]|ladraba)\b', r''),
 ('trueno', 'efecto', r'\b(?:truenos?|tron[oó]|relámpagos?)\b', r''),
 ('puerta', 'efecto', r'\b(?:portazo|chirrido de la puerta)\b|\bpuerta\b[^.!?;\n]{0,55}\b(?:cerr[oó]|abri[oó]|golpe[oó])\b|\b(?:cerr[oó]|abri[oó]|golpe[oó])\b[^.!?;\n]{0,55}\bpuerta\b', r'puerta (?:del|al) (?:corazón|alma|éxito)'),
 ('pasos', 'efecto', r'\b(?:pasos|pisadas)\b', r'pasos? (?:a seguir|hacia el éxito|del proceso)'),
 ('disparo', 'efecto', r'\b(?:disparos?|dispar[oó]|detonaciones?|detonación)\b', r''),
 ('teléfono', 'efecto', r'\b(?:teléfono|móvil|celular)\b[^.!?;\n]{0,40}\b(?:son[oó]|sonaba|vibr[oó])\b|\b(?:son[oó]|sonaba|vibr[oó])\b[^.!?;\n]{0,40}\b(?:teléfono|móvil|celular)\b', r''),
 ('motor', 'efecto', r'\b(?:motor)\b[^.!?;\n]{0,40}\b(?:rug[ií][aó]|encendi[oó]|arranc[oó]|ronroneaba)\b|\b(?:arranc[oó]|encendi[oó])\b[^.!?;\n]{0,40}\bmotor\b', r'motor de (?:la historia|la vida|cambio)'),
]
# Action-level cues complement the original environment vocabulary.
CUES += [
 ('latidos del corazón','efecto',r'\b(?:coraz[oó]n\b[^.!?;\n]{0,90}\b(?:lat(?:ía|ían|e|ir|ió|iendo)|palpit(?:aba|ar|ó))|latidos?(?:[^.!?;\n]{0,35}coraz[oó]n)?|palpitaciones)\b',r'corazón de (?:la ciudad|la empresa|la historia)|latido de la ciudad'),
 ('respiración agitada','efecto',r'\b(?:jade(?:aba|ó|os?)|respir(?:aba|ó|ación)\s+(?:con dificultad|agitad(?:[oa]|amente)|entrecortad[oa]|profundamente)|boqueaba)\b',r''),
 ('suspiro','efecto',r'\b(?:suspiros?|suspir(?:ó|aba))\b',r''),
 ('llanto','efecto',r'\b(?:solloz(?:ó|aba|os?)|llor(?:ó|aba|ando)|conten(?:ía|iendo|er) el llanto)\b',r''),
 ('risa','efecto',r'\b(?:carcajadas?|risas?|reía|rieron|rió)\b',r'muerto de risa'),
 ('susurros','efecto',r'\b(?:cuchicheos?|murmullos?|susurr(?:ó|aban|aba))\b',r''),
 ('gritos','efecto',r'\b(?:grit(?:ó|aban|aba|os?)|alaridos?)\b',r''),
 ('beso','efecto',r'\b(?:bes(?:ó|aron|aba)|besos?)\b',r'lluvia de besos|besos al aire'),
 ('ropa y movimiento','efecto',r'\b(?:roz(?:ó|aba)|cruj(?:ió|ía))\b[^.!?;\n]{0,35}\b(?:ropa|tela|chaqueta|vestido)\b',r''),
 ('golpe','efecto',r'\b(?:puñetazos?|bofetadas?|golpeó|golpearon|golpeando|impactos?)\b',r'golpe de suerte|golpe de estado'),
 ('caída','efecto',r'\b(?:cayó al (?:suelo|piso)|caí al (?:suelo|piso)|se desplomó|tropezó)\b',r''),
 ('cristal roto','efecto',r'\b(?:romp(?:ió|í)|quebr(?:ó|é)|estall(?:ó|aron))\b[^.!?;\n]{0,45}\b(?:vidrio|cristal|ventana)s?\b|\b(?:vidrios|cristales) rotos\b',r''),
 ('rechinido','efecto',r'\b(?:rechin(?:ó|aba|idos?)|chirr(?:ió|idos?))\b',r''),
 ('pasos corriendo','efecto',r'\b(?:corr(?:ió|í|ían|iendo)|estampida|trotaba)\b',r'corría el tiempo|corría el rumor|corría por sus venas'),
 ('escaleras','efecto',r'\b(?:sub(?:ió|í)|baj(?:ó|é))\b[^.!?;\n]{0,35}\bescal(?:era|ones)\b',r''),
 ('excavación','efecto',r'\b(?:excav(?:ar|ando|aban|ación)|cav(?:aban|ando|ó)|pic(?:os? y palas))\b',r''),
 ('radio comunicador','efecto',r'\b(?:radio de frecuencia|radiocomunicador|walkie.?talkie|estática de la radio|por (?:la )?radio)\b',r''),
 ('agua de tubería','efecto',r'\b(?:grifo|llave del agua|tubería|agua corriendo|llen(?:ó|é) (?:una |la )?cubeta)\b',r''),
 ('aspersores','ambiente',r'\b(?:aspersores|riego del jardín)\b',r''),
 ('herramientas de corte','efecto',r'\b(?:pinzas de corte|cortó el alambre|corté el alambre|cizallas?)\b',r''),
 ('poda','ambiente',r'\b(?:podadora|perfiladora|cortadora de césped)\b',r''),
 ('fuego','ambiente',r'\b(?:crepit(?:aba|ar)|fuego de la chimenea|leña ardiendo|llamas)\b',r'llamas de amor|llamas de la pasión'),
 ('cerradura','efecto',r'\b(?:cerrojo|pasador|giró la llave|giré la llave|abrió el seguro)\b',r''),
 ('mueble arrastrado','efecto',r'\b(?:mov(?:ió|í|er|iendo)|arrastr(?:ó|é|ar|ando))\b[^.!?;\n]{0,40}\b(?:ropero|estante|mueble|silla)\b',r''),
 ('aceleración','efecto',r'\b(?:aceler(?:ó|aba|ación)|rugió el motor|arrancó el auto)\b',r'aceleró el corazón|aceleración del crecimiento'),
 ('aplausos','efecto',r'\b(?:aplausos?|aplaud(?:ieron|ía|ió))\b',r''),
 ('multitud','ambiente',r'\b(?:bullicio|murmullo de (?:la )?gente|multitud|discoteca|club nocturno)\b',r''),
]

CONTEXT = re.compile(r'\b(?:antes de|a punto de|intent(?:ó|aba)|record[oó]|recordaba|recuerdo|imagin[oó]|imaginaba|soñ[oó]|soñaba|soñar|si hubiera|como si|ojalá|habl[oó] de|hablaban de|mañana|algún día)\b', re.I)
NEGATION = re.compile(r'\b(?:no|sin|nunca|jamás|ni)\b(?:\W+\w+){0,5}\W*$', re.I)
SILENT = re.compile(r'\b(?:estacionad[oa]s?|aparcad[oa]s?|apagado|inmóvil|silencios[oa]s?|en (?:una |la )?(?:foto|fotografía|pintura|pantalla)|pintad[oa]s?)\b', re.I)


def sound_cues(text):
 """Offsets refer to Python character positions in the segment's original text."""
 result=[]
 for sentence in re.finditer(r'[^.!?;\n]+', text):
  value=sentence.group()
  for label,kind,pattern,figurative in CUES:
   excluded=list(re.finditer(figurative,value,re.I)) if figurative else []
   for match in re.finditer(pattern,value,re.I):
    if any(a.start()<=match.start()<a.end() for a in excluded):continue
    prefix=value[:match.start()]
    suffix=value[match.end():]
    if re.match(r'\s+(?:no|nunca|jamás)\s+(?:se\s+)?(?:o[ií][aó]|escuch|son)',suffix,re.I):continue
    if NEGATION.search(re.split(r'[,]|\bpero\b|\bsino\b',prefix,flags=re.I)[-1]):continue
    contextual=bool(CONTEXT.search(value) or SILENT.search(value))
    # Generic river noun must not match the past-tense verb "rió" (regex is accent sensitive).
    start=sentence.start()+match.start();end=sentence.start()+match.end()
    result.append({'label':label,'kind':kind,'cue':text[start:end], 'start':start,'end':end,
      'context_text':value.strip(),'context_status':'revisar contexto' if contextual else 'posible sonido presente',
      'reason':'Recuerdo, hipótesis, objeto silencioso o representación: decidir si debe sonar' if contextual else ('Ambiente sugerido por el lugar; confirmar que la escena transcurre allí' if kind=='ambiente' else 'Indicio puntual; confirmar si la acción es audible'),
      'requires_context_review':True,'placement':'escena' if kind=='ambiente' else 'fragmento',
      'timing':'sin sincronización temporal; no insertado'})
 return result


def build_scene_plan(report):
 plans={(s['chapter_id'],s['scene']):{**s,'characters':[], 'places':[], 'emotions':[], 'ambience':[], 'effects':[], 'context_review':[]} for s in report['scenes']}
 for name in report['names']:
  if name['evidence_level']=='débil':continue
  for e in name['evidence']:
   plan=plans.get((e['chapter_id'],e['scene']))
   if plan is not None and not e['excluded'] and name['name'] not in plan['characters']:plan['characters'].append(name['name'])
 for place in report['places']:
  for e in place['evidence']:
   plan=plans.get((e['chapter_id'],e['scene']))
   if plan is not None and not e['excluded'] and place['name'] not in plan['places']:plan['places'].append(place['name'])
 for e in report['emotions']:
  plan=plans.get((e['chapter_id'],e['scene']))
  if plan is not None and not e['excluded'] and e['label'] not in plan['emotions']:plan['emotions'].append(e['label'])
 for i,e in enumerate(report['sound_suggestions']):
  plan=plans.get((e['chapter_id'],e['scene']))
  if plan is None or e['excluded']:continue
  bucket='context_review' if e['context_status']=='revisar contexto' else ('ambience' if e['kind']=='ambiente' else 'effects')
  plan[bucket].append({**e,'item_id':str(i)})
 return list(plans.values())
