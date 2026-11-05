"""Regression: sequential effects should not be attenuated as simultaneous."""
from app.sound_mixer import max_simultaneous_cues


def test_sequential_effects_do_not_accumulate_headroom():
    scene = {'segments': [{'id': 's', 'offset': 0.0}]}
    cues = [dict(role='effect', segment_id='s', offset=float(i), duration=1.0) for i in range(4)]
    assert max_simultaneous_cues(cues, scene, 'effect') == 1


def test_overlapping_effects_accumulate_headroom():
    scene = {'segments': [{'id': 's', 'offset': 0.0}]}
    cues = [dict(role='effect', segment_id='s', offset=i * .2, duration=1.0) for i in range(4)]
    assert max_simultaneous_cues(cues, scene, 'effect') == 4


def test_music_and_effects_are_counted_separately():
    scene = {'segments': [{'id': 's', 'offset': 3.0}]}
    cues = [dict(role='effect', segment_id='s', offset=0, duration=.3),
            dict(role='music', segment_id='s', offset=0, duration=5),
            dict(role='music', segment_id='s', offset=1, duration=5)]
    assert max_simultaneous_cues(cues, scene, 'effect') == 1
    assert max_simultaneous_cues(cues, scene, 'music') == 2
