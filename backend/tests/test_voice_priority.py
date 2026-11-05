import copy,hashlib,math,struct,tempfile,wave
from pathlib import Path
import pytest
from app import main as m,sound_mixer as sm
from app.voice_priority import resolved
from test_sound_mixer import setup,c

def tone(name,frequency,amplitude,voice=False):
 rate=24000
 with wave.open(str(m.DATA/name),'wb') as w:
  w.setparams((1,2,rate,0,'NONE','not compressed'));w.writeframes(b''.join(struct.pack('<h',int(amplitude*math.sin(2*math.pi*frequency*i/rate)) if not voice or .2<=i/rate<1 or 2<=i/rate<2.8 else 0) for i in range(rate*3)))

@pytest.mark.parametrize('role',['effect','music'])
def test_loud_background_reduced_during_voice_recovers_in_pause_preserves_sources(role,tmp_path):
 p=setup();pid=p['id']
 with m.lock:
  pp=m.get(pid);s=pp['chapters'][0]['segments'][0];pp['chapters'][0]['segments']=[s];tone(s['audio'],150,6000,True);fx=pp['sound_effects'][0];tone(fx['file'],800,20000)
  pp['sound_cues']=[dict(id='rain',role=role,sound_id=fx['id'],segment_id=s['id'],offset=0,source_start=0,duration=3,volume_db=0,fade_in=0,fade_out=0,loop=False,active=True)]
  pp['voice_priority']={'chapters':{pp['chapters'][0]['id']:dict(enabled=True,strength='balanced')}};m.save(pp)
 before=copy.deepcopy(pp);hashes={n:hashlib.sha256((m.DATA/n).read_bytes()).hexdigest() for n in (s['audio'],fx['file'])}
 scene=sm.scene_by_id(pp,s['id']);out=tmp_path/'on.wav'
 with tempfile.TemporaryDirectory() as f:sm.render_scene(pp,scene,Path(f),out)
 with wave.open(str(out)) as w:rate=w.getframerate();channels=w.getnchannels();samples=struct.unpack('<'+'h'*(w.getnframes()*channels),w.readframes(w.getnframes()))
 def amplitude(start,end,frequency=800):
  indices=range(int(start*rate),int(end*rate));n=int(end*rate)-int(start*rate)
  a=sum(samples[i*channels]*math.sin(2*math.pi*frequency*i/rate) for i in indices)*2/n
  return abs(a)
 # Gentle recovery between phrases, bounded to 4 dB of speech-driven reduction.
 assert 1.01<amplitude(1.7,1.9)/amplitude(.6,.9)<10**(4/20)+.03
 assert amplitude(.6,.9)<4000
 assert 5800/math.sqrt(2)<amplitude(.6,.9,150)<6200/math.sqrt(2)
 assert m.get(pid)==before
 assert all(hashlib.sha256((m.DATA/n).read_bytes()).hexdigest()==h for n,h in hashes.items())


def test_chapter_and_scene_override_inheritance_and_stale():
 p=setup();pid=p['id'];ch=p['chapters'][0]['id'];sid=p['chapters'][0]['segments'][0]['id'];base=f'/api/projects/{pid}/sound-mixer/voice-priority';before=copy.deepcopy(m.get(pid));old=sm.fingerprint(before,sid)
 assert c.get(base).json()['scenes'][0]['settings']==dict(enabled=True,strength='balanced')
 assert c.put(base,json=dict(scope='chapter',target_id=ch,enabled=True,strength='strong')).status_code==200
 assert c.put(base,json=dict(scope='scene',target_id=sid,enabled=False,strength='gentle')).status_code==200
 assert c.put(base,json=dict(scope='chapter',target_id=ch,enabled=True,strength='gentle')).status_code==200
 p=m.get(pid);assert resolved(p,sm.scene_by_id(p,sid))['enabled'] is False
 assert sm.fingerprint(p,sid)!=old
 assert p['chapters']==before['chapters'] and p['sound_effects']==before['sound_effects']
 assert c.put(base,json=dict(scope='scene',target_id=sid,inherit=True)).status_code==200
 assert resolved(m.get(pid),sm.scene_by_id(p,sid))==dict(enabled=True,strength='gentle')
 assert c.put(base,json=dict(scope='chapter',target_id='foreign')).status_code==404
 assert c.put(base,json=dict(scope='chapter',target_id=ch,strength='bad')).status_code==422


def test_smooth_profiles_keep_bounded_speech_attenuation():
 from app.voice_priority import smooth_profile
 assert smooth_profile('gentle')==(220,1600,2)
 assert smooth_profile('balanced')==(180,1400,4)
 assert smooth_profile('strong')==(140,1200,6)
