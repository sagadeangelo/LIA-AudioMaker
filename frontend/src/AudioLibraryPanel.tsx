import { useEffect, useState } from 'react';

type AudioItem = {
  id: string;
  number: number;
  speaker?: string;
  voice?: string;
  speed?: number;
  text: string;
  audio?: string | null;
  duration?: number;
  status: string;
  versions: Array<{
    file?: string;
    exists: boolean;
    voice?: string;
    provider?: string;
  }>;
};

type AudioChapter = {
  id: string;
  number: number;
  title: string;
  included: number;
  generated: number;
  ready: boolean;
  segments: AudioItem[];
};

type AudioLibraryData = {
  title: string;
  totals: Record<string, number>;
  chapters: AudioChapter[];
};

export default function AudioLibraryPanel({
  projectId,
}: {
  projectId: string | null;
}) {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState<AudioLibraryData | null>(null);
  const [chapterId, setChapterId] = useState('');
  const [filter, setFilter] = useState('all');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [repairing, setRepairing] = useState<string | null>(null);
  const [repairVoice, setRepairVoice] = useState('em_santa');
  const [repairSpeed, setRepairSpeed] = useState(1);
  const [repairSpeaker, setRepairSpeaker] = useState('Narrador');
  const [repairError, setRepairError] = useState('');
  const [availableRepairVoices, setAvailableRepairVoices] =
    useState<string[]>([]);

  async function refresh() {
    if (!projectId) return;
    setLoading(true);
    setError('');

    try {
      const response = await fetch(
        `/api/projects/${encodeURIComponent(projectId)}/audio-library`
      );

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const result: AudioLibraryData = await response.json();
      setData(result);
      setChapterId(current =>
        result.chapters.some(ch => ch.id === current)
          ? current
          : (result.chapters[0]?.id || '')
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    setData(null);
    setChapterId('');
    setOpen(false);
  }, [projectId]);

  useEffect(() => {
    if (open && projectId) {
      void refresh();
    }
  }, [open, projectId]);


  useEffect(() => {
    if (!open || !projectId) return;

    fetch('/api/voices')
      .then(async response => {
        if (!response.ok) throw new Error('Catalogo no disponible');
        return response.json();
      })
      .then(result => {
        const values = Array.isArray(result.voices)
          ? result.voices
              .map((v: unknown) =>
                typeof v === 'string'
                  ? v
                  : v && typeof v === 'object' && 'id' in v
                    ? String(v.id)
                    : null
              )
              .filter((v: string | null): v is string => Boolean(v))
          : [];

        setAvailableRepairVoices(values);
      })
      .catch(() => setAvailableRepairVoices([]));
  }, [open, projectId]);

  function openRepair(s: AudioItem) {
    if (s.audio || s.status === 'generated') return;
    setRepairing(s.id);
    setRepairVoice(s.voice || 'em_santa');
    setRepairSpeed(s.speed ?? 1);
    setRepairSpeaker(s.speaker || 'Narrador');
    setRepairError('');
  }

  async function generateOne(s: AudioItem) {
    if (!projectId || s.audio || loading) return;

    setLoading(true);
    setRepairError('');

    try {
      const patch = await fetch(
        `/api/projects/${projectId}/segments/${s.id}`,
        {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            speaker: repairSpeaker,
            voice: repairVoice,
            speed: repairSpeed,
            color: '#00D9CE',
            reviewed: true,
          }),
        }
      );

      if (!patch.ok) {
        const detail = await patch.text();
        throw new Error(`No se pudo guardar: ${detail}`);
      }

      const response = await fetch(
        `/api/projects/${projectId}/segments/${s.id}/generate?compact=true`,
        { method: 'POST' }
      );

      if (!response.ok) {
        const detail = await response.text();
        throw new Error(`No se pudo generar: ${detail}`);
      }

      setRepairing(null);
      await refresh();
    } catch (e) {
      setRepairError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  if (!projectId) return null;

  const chapter = data?.chapters.find(ch => ch.id === chapterId);
  const segments = (chapter?.segments || []).filter(s =>
    filter === 'all' ||
    (filter === 'attention'
      ? s.status !== 'generated' && s.status !== 'excluded'
      : s.status === filter)
  );

  const buttonStyle = {
    padding: '9px 13px',
    borderRadius: 8,
    cursor: 'pointer',
    border: '1px solid #596577',
    background: '#263346',
    color: '#ffffff',
  };

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        style={{
          ...buttonStyle,




          background: '#d17b23',
          border: 'none',
          fontWeight: 700,
          whiteSpace: 'nowrap',
          boxShadow: '0 4px 18px #0007',
        }}
      >
        Biblioteca de Audios
      </button>

      {open && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="Biblioteca de Audios"
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 9999,
            background: '#000b',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: 16,
          }}
        >
          <div style={{
            background: '#17202c',
            color: '#f5f7fa',
            width: 'min(1100px, 100%)',
            maxHeight: '92vh',
            overflowY: 'auto',
            padding: 22,
            borderRadius: 14,
            boxSizing: 'border-box',
          }}>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              gap: 12,
              flexWrap: 'wrap',
            }}>
              <div>
                <h2 style={{ margin: 0 }}>Biblioteca de Audios</h2>
                <p style={{ color: '#acb8c8' }}>
                  Historial permanente del proyecto
                </p>
              </div>

              <div style={{ display: 'flex', gap: 8 }}>
                <button
                  type="button"
                  style={buttonStyle}
                  onClick={() => void refresh()}
                  disabled={loading}
                >
                  Actualizar
                </button>
                <button
                  type="button"
                  style={buttonStyle}
                  onClick={() => setOpen(false)}
                >
                  Cerrar
                </button>
              </div>
            </div>

            {error && (
              <p role="alert" style={{ color: '#ff9999' }}>
                Error al consultar biblioteca: {error}
              </p>
            )}

            {loading && <p>Consultando audios guardados...</p>}

            {data && (
              <>
                <div style={{
                  display: 'flex',
                  gap: 12,
                  flexWrap: 'wrap',
                  marginBottom: 18,
                }}>
                  {[
                    ['Generados', data.totals.generated],
                    ['Pendientes', data.totals.pending],
                    ['En revisión', data.totals.review],
                    ['Archivos faltantes', data.totals.missing],
                    ['Capítulos con audio completo', data.totals.chapters_ready],
                  ].map(([label, value]) => (
                    <div key={String(label)} style={{
                      background: '#263346',
                      padding: 14,
                      borderRadius: 10,
                      minWidth: 130,
                    }}>
                      <div style={{ color: '#aebdd0', fontSize: 12 }}>
                        {label}
                      </div>
                      <strong style={{ fontSize: 24 }}>{value}</strong>
                    </div>
                  ))}
                </div>

                <div style={{
                  display: 'flex',
                  gap: 12,
                  flexWrap: 'wrap',
                  alignItems: 'center',
                  marginBottom: 18,
                }}>
                  <label>
                    Capítulo{' '}
                    <select
                      value={chapterId}
                      onChange={e => setChapterId(e.target.value)}
                    >
                      {data.chapters.map(ch => (
                        <option key={ch.id} value={ch.id}>
                          {ch.number}. {ch.title} — {ch.generated}/{ch.included}
                        </option>
                      ))}
                    </select>
                  </label>

                  <label>
                    Mostrar{' '}
                    <select
                      value={filter}
                      onChange={e => setFilter(e.target.value)}
                    >
                      <option value="all">Todos</option>
                      <option value="generated">Generados</option>
                      <option value="attention">Requieren atención</option>
                      <option value="pending">Pendientes</option>
                      <option value="review">En revisión</option>
                      <option value="missing">Archivo faltante</option>
                    </select>
                  </label>
                </div>

                {chapter && (
                  <>
                    <div style={{
                      background: '#263346',
                      padding: 14,
                      borderRadius: 10,
                      marginBottom: 12,
                    }}>
                      <strong>{chapter.title}</strong>
                      <p>
                        {chapter.generated} de {chapter.included} fragmentos
                        incluidos tienen audio.
                      </p>

                      {chapter.ready ? (
                        <div style={{
                          display: 'flex',
                          gap: 8,
                          flexWrap: 'wrap',
                        }}>
                          <a
                            style={buttonStyle}
                            href={`/api/projects/${projectId}/chapters/${chapter.id}/export?format=wav`}
                            target="_blank"
                            rel="noreferrer"
                          >
                            Descargar WAV
                          </a>
                          <a
                            style={buttonStyle}
                            href={`/api/projects/${projectId}/chapters/${chapter.id}/export?format=mp3`}
                            target="_blank"
                            rel="noreferrer"
                          >
                            Descargar MP3
                          </a>
                        </div>
                      ) : (
                        <p style={{ color: '#f5bd72' }}>
                          Capítulo incompleto: revisa o genera los fragmentos
                          pendientes antes de exportarlo.
                        </p>
                      )}
                    </div>

                    <p>Mostrando {segments.length} fragmentos</p>

                    {segments.map(s => (
                      <details
                        key={s.id}
                        style={{
                          borderBottom: '1px solid #354253',
                          padding: '11px 0',
                        }}
                      >
                        <summary style={{ cursor: 'pointer' }}>
                          <strong>Fragmento {s.number}</strong>
                          {' — '}
                          {s.speaker || 'Sin personaje'}
                          {' — '}
                          <span style={{
                            color: s.status === 'generated'
                              ? '#79d9a4'
                              : '#ffca84',
                          }}>
                            {s.status === 'generated' ? 'Generado' :
                             s.status === 'review' ? 'En revisión' :
                             s.status === 'pending' ? 'Pendiente' :
                             s.status === 'missing' ? 'Archivo faltante' :
                             'Excluido'}
                          </span>
                        </summary>

                        <p style={{
                          whiteSpace: 'pre-wrap',
                          overflowWrap: 'anywhere',
                        }}>
                          {s.text}
                        </p>

                        {!s.audio && s.status !== 'excluded' && (
                          <div style={{
                            background: '#263346',
                            padding: 12,
                            borderRadius: 8,
                            marginBottom: 12,
                          }}>
                            {repairing !== s.id ? (
                              <button
                                type="button"
                                style={buttonStyle}
                                onClick={() => openRepair(s)}
                              >
                                Reparar fragmento
                              </button>
                            ) : (
                              <div style={{
                                display: 'grid',
                                gap: 10,
                              }}>
                                <strong>Reparaci?n individual</strong>

                                <label>
                                  Personaje
                                  <input
                                    value={repairSpeaker}
                                    onChange={e =>
                                      setRepairSpeaker(e.target.value)
                                    }
                                  />
                                </label>

                                <label>
                                  Voz
                                  <select
                                    value={repairVoice}
                                    onChange={e =>
                                      setRepairVoice(e.target.value)
                                    }
                                  >
                                    {[
                                      ...new Set([
                                        repairVoice,
                                        ...availableRepairVoices,
                                      ]),
                                    ].map(voice => (
                                      <option key={voice} value={voice}>
                                        {voice}
                                      </option>
                                    ))}
                                  </select>
                                </label>

                                <label>
                                  Velocidad: {repairSpeed}
                                  <input
                                    type="number"
                                    min="0.5"
                                    max="2"
                                    step="0.05"
                                    value={repairSpeed}
                                    onChange={e =>
                                      setRepairSpeed(Number(e.target.value))
                                    }
                                  />
                                </label>

                                <p>
                                  Se confirmar? la revisi?n y se generar?
                                  solamente este fragmento.
                                </p>

                                {repairError && (
                                  <p role="alert" style={{ color: '#ff9999' }}>
                                    {repairError}
                                  </p>
                                )}

                                <div style={{
                                  display: 'flex',
                                  gap: 8,
                                }}>
                                  <button
                                    type="button"
                                    style={buttonStyle}
                                    disabled={loading}
                                    onClick={() => void generateOne(s)}
                                  >
                                    {loading
                                      ? 'Generando...'
                                      : 'Guardar y generar'}
                                  </button>

                                  <button
                                    type="button"
                                    style={buttonStyle}
                                    disabled={loading}
                                    onClick={() => setRepairing(null)}
                                  >
                                    Cancelar
                                  </button>
                                </div>
                              </div>
                            )}
                          </div>
                        )}

                        {s.audio && s.status === 'generated' && (
                          <div>
                            <audio
                              controls
                              preload="none"
                              src={`/api/audio/${encodeURIComponent(s.audio)}`}
                              style={{ maxWidth: '100%' }}
                            />
                            <p>
                              <a
                                href={`/api/audio/${encodeURIComponent(s.audio)}`}
                                download={s.audio}
                                style={{ color: '#9fd0ff' }}
                              >
                                Descargar audio individual
                              </a>
                            </p>
                          </div>
                        )}

                        {s.versions.length > 0 && (
                          <details>
                            <summary>
                              Historial de versiones ({s.versions.length})
                            </summary>
                            {s.versions.map((v, i) => (
                              <div key={`${v.file}-${i}`} style={{
                                margin: '9px 0',
                              }}>
                                {v.file || 'Sin nombre'}
                                {' — '}
                                {v.exists ? 'Disponible' : 'No encontrado'}
                                {v.voice ? ` — ${v.voice}` : ''}
                                {v.exists && v.file && (
                                  <audio
                                    controls
                                    preload="none"
                                    src={`/api/audio/${encodeURIComponent(v.file)}`}
                                    style={{
                                      display: 'block',
                                      maxWidth: '100%',
                                    }}
                                  />
                                )}
                              </div>
                            ))}
                          </details>
                        )}
                      </details>
                    ))}
                  </>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </>
  );
}
