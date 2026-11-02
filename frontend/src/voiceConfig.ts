export const KOKORO_VOICES = [
  'em_santa',
  'em_alex',
  'ef_dora',
] as const;

export function isKokoroVoice(voice: string): boolean {
  return (KOKORO_VOICES as readonly string[]).includes(voice);
}

export function isAzureVoice(voice: string): boolean {
  return /^es-(MX|ES)-[A-Za-z0-9]+Neural$/.test(voice);
}

export function isSupportedVoice(voice: string): boolean {
  return isKokoroVoice(voice) || isAzureVoice(voice);
}

export function voiceLabel(voice: string): string {
  const labels: Record<string, string> = {
    em_santa: 'Narrador masculino — Santa',
    em_alex: 'Voz masculina — Alex',
    ef_dora: 'Voz femenina — Dora',
  };

  if (labels[voice]) return labels[voice];

  if (isAzureVoice(voice)) {
    return voice
      .replace(/^es-(MX|ES)-/, '')
      .replace(/Neural$/, '')
      .replace(/Multilingual$/, ' Multilingual');
  }

  return `Voz anterior no disponible (${voice})`;
}

export function voiceGroup(voice: string): string {
  if (isKokoroVoice(voice)) return 'Kokoro — Local';
  if (voice.startsWith('es-MX-')) return 'Azure — Español México';
  if (voice.startsWith('es-ES-')) return 'Azure — Español España';
  return 'Voces anteriores';
}

export function defaultSpeed(_voice: string): number {
  return 1.0;
}

export function validSpeed(voice: string, speed: number): boolean {
  return isSupportedVoice(voice)
    && Number.isFinite(speed)
    && speed >= 0.5
    && speed <= 2.0;
}

export function speedSettings(_voice: string) {
  return {
    min: 0.5,
    max: 2,
    step: 0.05,
    unit: 'x',
  };
}

export function speedForVoice(
  _previousVoice: string,
  nextVoice: string,
  currentSpeed: number,
): number {
  return validSpeed(nextVoice, currentSpeed)
    ? currentSpeed
    : defaultSpeed(nextVoice);
}

export function normalizeCastVoice(voice: string): string {
  return isSupportedVoice(voice) ? voice : 'em_santa';
}

export function normalizeCastSpeed(
  voice: string,
  speed: number,
): number {
  return validSpeed(voice, speed) ? speed : 1.0;
}
