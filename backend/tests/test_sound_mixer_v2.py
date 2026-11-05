"""v2 regression: role-aware voice priority and non-destructive loudness."""
import math
import subprocess
from app.voice_priority import smooth_profile, measure_loudness

def test_music_ducks_more_than_effects():
    for strength in ('gentle','balanced','strong'):
        music = smooth_profile(strength, 'music')
        effect = smooth_profile(strength, 'effect')
        assert music[2] > effect[2]
        assert effect[0] < music[0]
        assert music[1] > effect[1]

def test_existing_music_profile_call_remains_supported():
    assert smooth_profile('balanced') == smooth_profile('balanced', 'music')

def test_ebu_loudness_report_on_generated_wav(tmp_path):
    path = tmp_path / 'tone.wav'
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-f','lavfi',
       '-i','sine=frequency=440:duration=4:sample_rate=48000',
       '-c:a','pcm_s16le',str(path)],check=True)
    before = path.read_bytes()
    result = measure_loudness(path)
    assert result is not None
    assert -70 < result['integrated_lufs'] < 0
    assert -70 < result['true_peak_dbtp'] < 0
    assert path.read_bytes() == before
