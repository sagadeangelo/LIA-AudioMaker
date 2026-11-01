import os, tempfile, shutil, subprocess, sys
from fastapi.testclient import TestClient
from app.main import app, DATA
from app.narrative import analyze, extract
client=TestClient(app)

def test_full_flow():
    p=client.post('/api/projects',json={'title':'Prueba'}).json(); pid=p['id']
    original='Capítulo 1\nEl reloj marcó las nueve.\n—Hola, Ana.\n***\nEl tren partió.\nCapítulo 2\nFin.'
    r=client.post(f'/api/projects/{pid}/manuscript',files={'file':('book.txt',original.encode())}); assert r.status_code==200
    p=r.json(); assert p['original']==original; assert len(p['chapters'])==2
    assert p['chapters'][0]['segments'][1]['review']; assert p['chapters'][0]['segments'][2]['scene']==2
    assert client.post(f'/api/projects/{pid}/manuscript',files={'file':('book.txt',b'overwrite')}).status_code==409
    ch=p['chapters'][0]
    for i,s in enumerate(ch['segments']):
        r=client.patch(f'/api/projects/{pid}/segments/{s["id"]}',json={'speaker':'Ana' if i==1 else 'Narrador','voice':'es+f2' if i==1 else 'es+m3','speed':160,'color':'#00D9CE'}); assert r.status_code==200
        r=client.post(f'/api/projects/{pid}/segments/{s["id"]}/generate')
        if shutil.which('espeak-ng') or shutil.which('espeak'): assert r.status_code==200
        else: assert r.status_code==503
    p=client.get(f'/api/projects/{pid}').json()
    if not shutil.which('espeak-ng'): return
    first=p['chapters'][0]['segments'][0]; second=p['chapters'][0]['segments'][1]
    assert client.get('/api/audio/'+first['audio']).status_code==200
    assert max(client.get('/api/audio/'+first['audio']+'/waveform').json())>0
    p=client.post(f'/api/projects/{pid}/segments/{first["id"]}/generate').json()
    assert len(p['chapters'][0]['segments'][0]['versions'])==2
    assert p['chapters'][0]['segments'][1]['audio']==second['audio']
    for fmt in ['wav','mp3']:
        r=client.get(f'/api/projects/{pid}/chapters/{ch["id"]}/export?format={fmt}'); assert r.status_code==200; assert len(r.content)>1000
    # New interpreter proves persistence beyond module memory.
    code=f"from app.main import get; assert get('{pid}')['original']=={original!r}"
    subprocess.run([sys.executable,'-c',code],check=True)

def test_validation():
    assert client.post('/api/projects',json={'title':''}).status_code==422
    assert client.get('/api/projects/missing').status_code==404
    p=client.post('/api/projects',json={'title':'Invalid'}).json()
    assert client.post(f'/api/projects/{p["id"]}/manuscript',files={'file':('book.exe',b'bad')}).status_code==422
    assert client.get(f'/api/projects/{p["id"]}/chapters/missing/export?format=ogg').status_code==422

def test_analysis_does_not_invent():
    s=analyze('—Hola —dijo Ana.')[0]['segments'][0]
    assert s['speaker']=='Sin atribuir' and s['confidence']==0 and s['review']

def test_docx_and_epub():
    from io import BytesIO
    from docx import Document
    from zipfile import ZipFile
    doc=Document(); doc.add_paragraph('Hola mundo'); b=BytesIO(); doc.save(b)
    assert extract(b.getvalue(),'.docx')=='Hola mundo'
    b=BytesIO()
    with ZipFile(b,'w') as z:
        z.writestr('META-INF/container.xml','<container><rootfile full-path="OEBPS/book.opf"/></container>')
        z.writestr('OEBPS/book.opf','<package><manifest><item id="b" href="b.xhtml"/><item id="a" href="a.xhtml"/></manifest><spine><itemref idref="a"/><itemref idref="b"/></spine></package>')
        z.writestr('OEBPS/a.xhtml','<html><body><p>Primero</p></body></html>'); z.writestr('OEBPS/b.xhtml','<html><body><p>Segundo</p></body></html>')
    assert extract(b.getvalue(),'.epub')=='Primero\nSegundo'
