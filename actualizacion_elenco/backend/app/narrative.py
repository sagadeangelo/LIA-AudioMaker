"""Conservative structural analysis: never guesses the speaker."""
import re
from io import BytesIO
from zipfile import ZipFile
from xml.etree import ElementTree as ET

def extract(data: bytes, suffix: str) -> str:
    if suffix == '.txt': return data.decode('utf-8-sig')
    if suffix == '.docx':
        from docx import Document
        return '\n'.join(p.text for p in Document(BytesIO(data)).paragraphs)
    if suffix == '.pdf':
        from pypdf import PdfReader
        return '\n'.join(p.extract_text() or '' for p in PdfReader(BytesIO(data)).pages)
    if suffix == '.epub':
        with ZipFile(BytesIO(data)) as z:
            if sum(i.file_size for i in z.infolist()) > 50_000_000: raise ValueError('EPUB demasiado grande')
            container = ET.fromstring(z.read('META-INF/container.xml'))
            rootfile = next(e.attrib['full-path'] for e in container.iter() if e.tag.endswith('rootfile'))
            package = ET.fromstring(z.read(rootfile))
            manifest = {e.attrib['id']: e.attrib['href'] for e in package.iter() if e.tag.endswith('item')}
            from posixpath import dirname, join, normpath
            chapters = []
            for e in package.iter():
                if e.tag.endswith('itemref'):
                    path = normpath(join(dirname(rootfile), manifest[e.attrib['idref']]))
                    if path.startswith('../'): raise ValueError('Ruta EPUB inválida')
                    html = ET.fromstring(z.read(path))
                    chapters.append('\n'.join(''.join(n.itertext()) for n in html.iter() if n.tag.split('}')[-1] in ('p','h1','h2','h3')))
            return '\n'.join(chapters)
    raise ValueError('Formato no admitido')

# Structural rules only: confidence is a heuristic score, not a probability.
import unicodedata

CHAPTER = re.compile(r'^\s*(?:cap[ií]tulo|chapter)\s+(?:[IVXLCDM]+|\d+)(?:\b.*)?$', re.I)
SPEAKER = re.compile(r'^\s*([A-ZÁÉÍÓÚÜÑ][A-ZÁÉÍÓÚÜÑ .]{1,44}):\s*(\S.*)$')
SEPARATOR = re.compile(r'\s*(?:(?:\*\s*){3,}|#{3,})\s*')
NON_SPEAKERS = {'ISBN', 'NOTA', 'NOTAS', 'COPYRIGHT', 'URL', 'HTTP', 'HTTPS', 'ADVERTENCIA'}
SECTIONS = {'dedicatoria':('Dedicatoria','dedication'), 'prefacio':('Prefacio','preface'),
            'prologo':('Prólogo','preface'), 'epilogo':('Epílogo','epilogue'),
            'agradecimientos':('Agradecimientos','acknowledgements'),
            'sobre el autor':('Sobre el autor','author'), 'acerca del autor':('Sobre el autor','author'),
            'otras obras':('Otras obras','back_matter'), 'obras del autor':('Otras obras','back_matter')}

def key(value):
    return ''.join(c for c in unicodedata.normalize('NFD',value) if not unicodedata.combining(c)).casefold().strip()

def speaker_match(line):
    match=SPEAKER.match(line)
    if not match or match[1].strip() in NON_SPEAKERS or len(match[1].split())>6: return None
    return match

def section(line):
    return SECTIONS.get(key(line.strip().rstrip(':')))

def subtitle(line):
    # Only an all-caps short line after a standalone chapter number is absorbed.
    stripped=line.strip()
    return (bool(stripped) and (stripped.isupper() or stripped.startswith(('El ', 'La ', 'Los ', 'Las ')) and stripped[3:].isupper()) and len(stripped)<=100
            and not re.search(r'[!?¡¿:«»“”]',stripped)
            and '.' not in stripped.rstrip('.')
            and not CHAPTER.match(stripped) and section(stripped) is None)

def analyze(text: str):
    lines=text.replace('\r\n','\n').replace('\r','\n').split('\n')
    # Merge only accent/case variants of explicit labels. Do not equate roles
    # (EL DOCTOR / DR. DITOX) or different names (ANDRE / ANDRES).
    labels={}
    for line in lines:
        m=speaker_match(line)
        if m:
            name=m[1].strip(); normalized=key(name)
            prior=labels.get(normalized)
            if prior is None or sum(ord(c)>127 for c in name)>sum(ord(c)>127 for c in prior): labels[normalized]=name
    chapters=[]; current=None; scene=1; prior_speaker=None; blank_count=0; i=0

    def start(title,kind,source_title='',review=False):
        nonlocal current,scene,prior_speaker
        current={'title':title,'kind':kind,'source_title':source_title,'review':review,'segments':[]}
        chapters.append(current); scene=1; prior_speaker=None

    def add(source,spoken,speaker,kind,confidence,review,reason,**extra):
        current['segments'].append({'text':spoken,'source_text':source,'source_line':i,
            'scene':scene,'speaker':speaker,'kind':kind,'confidence':confidence,
            'review':review,'review_reason':reason,**extra})

    has_chapters=any(CHAPTER.match(line) for line in lines)
    while i<len(lines):
        line=lines[i]; stripped=line.strip()
        if not stripped:
            blank_count+=1;i+=1;continue
        previous_blanks=blank_count;blank_count=0
        heading=section(stripped)
        if CHAPTER.match(stripped):
            title=stripped; source_title=line
            # A title embedded after the numeral is already complete.
            standalone=re.fullmatch(r'(?:cap[ií]tulo|chapter)\s+(?:[IVXLCDM]+|\d+)',stripped,re.I)
            j=i+1
            while j<len(lines) and not lines[j].strip(): j+=1
            if standalone and j<len(lines) and subtitle(lines[j]):
                title+=' — '+lines[j].strip();source_title+='\n'+lines[j];i=j
            start(title,'chapter',source_title);i+=1;continue
        if heading:
            start(heading[0],heading[1],line);i+=1;continue
        if current is None:
            start('Páginas iniciales' if has_chapters else 'Capítulo 1','front_matter' if has_chapters else 'chapter')
        # Back matter without headings is only proposed after a large layout gap.
        if current['kind'] in ('epilogue','back_matter') and previous_blanks>=10:
            j=i+1
            while j<len(lines) and not lines[j].strip(): j+=1
            author=(j<len(lines) and re.match(r'\s*Nacid[oa]\b',lines[j],re.I))
            start('Sobre el autor — revisar' if author else 'Material final — revisar',
                  'author' if author else 'back_matter',review=True)
        if SEPARATOR.fullmatch(line):
            scene+=1;prior_speaker=None;i+=1;continue
        m=speaker_match(line) if current['kind']=='chapter' else None
        if m:
            raw=m[1].strip(); name=' '.join(word if re.fullmatch(r'[IVXLCDM]+',word) else word.title() for word in labels[key(raw)].split()); spoken=m[2]
            # A curly quote often introduces an acting/narrator aside in this
            # manuscript. Split on it but require review rather than guessing.
            cut=spoken.find('“')
            if cut>0:
                prefix=line[:m.start(2)]
                add(prefix+spoken[:cut],spoken[:cut],name,'dialogue',0.98,True,
                    'Hablante explícito; confirmar el corte de la acotación.',speaker_label=raw)
                add(spoken[cut:],spoken[cut:],'Sin atribuir','aside_candidate',0.0,True,
                    'Posible acotación o cita: confirmar si corresponde al narrador.')
            else:
                mixed=bool(re.search(r'\b(?:dijo|replicó|preguntó|respondió|exclamó|gritando|con un tono|con una cara)\b',spoken,re.I))
                add(line,spoken,name,'dialogue',0.98,mixed,
                    'Posible acotación dentro del diálogo; revisar antes de producir.' if mixed else '',speaker_label=raw)
            prior_speaker=name;i+=1;continue
        quoted=stripped.startswith(('«','“','"'))
        dash=stripped.startswith(('—','–'))
        # Also flag a name without colon if it matches a known explicit label.
        missing_colon=next((name for name in labels.values() if re.match(r'^'+re.escape(name)+r'\s+[¡¿]',stripped)),None)
        continuation=prior_speaker is not None and (stripped.startswith(('¡','¿')) or missing_colon is not None)
        if quoted:
            add(line,line,'Sin atribuir','thought_or_quote',0.0,True,
                'Puede ser pensamiento, cita o diálogo; las comillas no identifican al hablante.')
        elif dash or continuation or missing_colon:
            add(line,line,'Sin atribuir','dialogue_candidate',0.0,True,
                'Posible continuación o diálogo sin atribución explícita.',suggested_speaker=prior_speaker or '')
        else:
            add(line,line,'Narrador','narration',1.0,False,'')
        # Continuity is a suggestion only; never assign a speaker by proximity.
        if not continuation: prior_speaker=None
        i+=1
    return chapters
