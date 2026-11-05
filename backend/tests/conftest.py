import os
import sys
import tempfile
from pathlib import Path

# Production Compose passes DATABASE_URL. Override BOTH settings before any app import.
# Never accept an inherited database for this unit-test suite.
if 'app.main' in sys.modules:
    raise RuntimeError('Test isolation must run before importing app.main; aborting tests.')
_TEST_ROOT = Path(tempfile.mkdtemp(prefix='lia-test-suite-')).resolve()
os.environ['DATA_DIR'] = str(_TEST_ROOT / 'audio')
os.environ['DATABASE_URL'] = 'sqlite:///' + str(_TEST_ROOT / 'tests.sqlite')

import math, struct, wave
import pytest

@pytest.fixture
def fake_tts(monkeypatch):
    """Deterministic PCM fixture; no paid or external voice service."""
    calls=[]
    def generate(text, voice, speed, output_path):
        calls.append((text,voice,speed))
        frequency = .04 + sum(map(ord, text)) % 90 / 1000
        with wave.open(str(output_path),'wb') as w:
            w.setparams((1,2,24000,0,'NONE','not compressed'))
            w.writeframes(b''.join(struct.pack('<h',int(5000*math.sin(i*frequency))) for i in range(12000)))
        return {'provider':'azure' if voice.startswith('es-') else 'kokoro','duration':.5}
    monkeypatch.setattr('app.tts_provider.generate',generate)
    return calls
