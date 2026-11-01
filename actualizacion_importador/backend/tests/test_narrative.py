from collections import Counter
from app.narrative import analyze

def test_book_sections_subtitles_and_explicit_names():
    text='Título\nISBN: 123\nDedicatoria\nA mi familia.\nPREFACIO\nIntroducción.\nCAPÍTULO I\nLA VIDA DE ÁNGELO\nANGELO: Hola.\nÁNGELO: Adiós.\nCAPITULO II\nEl SÓTANO\nNarración.\nEPILOGO\nCierre.'
    chapters=analyze(text)
    assert [c['kind'] for c in chapters]==['front_matter','dedication','preface','chapter','chapter','epilogue']
    assert chapters[0]['segments'][1]['speaker']=='Narrador'
    assert chapters[3]['title']=='CAPÍTULO I — LA VIDA DE ÁNGELO'
    assert chapters[4]['title']=='CAPITULO II — El SÓTANO'
    segments=chapters[3]['segments']
    assert [s['speaker'] for s in segments]==['Ángelo','Ángelo']
    assert segments[0]['text']=='Hola.' and segments[0]['source_text']=='ANGELO: Hola.'
    assert not segments[0]['review']

def test_continuations_quotes_and_asides_require_review():
    ch=analyze('CAPITULO I\nPRUEBA\nAUGUSTO: ¿Qué? “El padre le miró.\n¡No lo creo!\n«Me preguntaba por qué».\nANGELO ¡Basta!\nANGELO: Sí, respondió con tristeza.')[0]
    s=ch['segments']
    assert s[0]['speaker']=='Augusto' and s[0]['review']
    assert s[1]['kind']=='aside_candidate' and s[1]['review']
    assert s[0]['source_text']+s[1]['source_text']=='AUGUSTO: ¿Qué? “El padre le miró.'
    assert s[2]['speaker']=='Sin atribuir' and s[2]['suggested_speaker']=='Augusto'
    assert s[3]['kind']=='thought_or_quote' and s[3]['speaker']=='Sin atribuir'
    assert s[4]['review'] and s[4]['speaker']=='Sin atribuir'
    assert s[5]['speaker']=='Angelo' and s[5]['review']

def test_do_not_merge_different_names_or_roles():
    s=analyze('ANDRE: Uno.\nANDRES: Dos.\nEL DOCTOR: Tres.\nDR. DITOX: Cuatro.')[0]['segments']
    assert len({x['speaker'] for x in s})==4

def test_title_punctuation_and_embedded_title():
    c=analyze('CAPITULO I\nLA ANTITOXINA.\nNarración.\nCapítulo 2 — El tren\nTexto.')
    assert c[0]['title']=='CAPITULO I — LA ANTITOXINA.'
    assert c[1]['title']=='Capítulo 2 — El tren'
    assert c[1]['segments'][0]['text']=='Texto.'

def test_back_matter_proposal_does_not_drop_author_name():
    c=analyze('CAPITULO I\nTexto.\nEPILOGO\nFin.\n'+'\n'*12+'Obra A & Obra B\n'+'\n'*12+'AUTOR EJEMPLO\n\nNacido en una ciudad.')
    assert c[-2]['kind']=='back_matter' and c[-2]['review']
    assert c[-1]['kind']=='author' and c[-1]['review']
    assert c[-1]['segments'][0]['text']=='AUTOR EJEMPLO'

def test_scene_resets_continuation_context():
    s=analyze('ANA: Hola.\n***\n¡Qué noche!')[0]['segments']
    assert s[1]['scene']==2
    assert s[1].get('suggested_speaker','')==''
