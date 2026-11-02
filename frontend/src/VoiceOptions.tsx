import {voiceGroup, voiceLabel} from './voiceConfig';

type Props = {
  voices: string[];
  selected?: string;
};

const GROUPS = [
  'Kokoro — Local',
  'Azure — Español México',
  'Azure — Español España',
  'Voces anteriores',
];

export function VoiceOptions({voices, selected}: Props) {
  const all = [...new Set([
    ...voices,
    ...(selected ? [selected] : []),
  ])];

  return (
    <>
      {GROUPS.map(group => {
        const entries = all.filter(v => voiceGroup(v) === group);

        if (!entries.length) return null;

        return (
          <optgroup key={group} label={group}>
            {entries.map(v => (
              <option key={v} value={v}>
                {voiceLabel(v)}
              </option>
            ))}
          </optgroup>
        );
      })}
    </>
  );
}
