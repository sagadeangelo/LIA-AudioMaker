import { useEffect, useState } from 'react';
import {VoiceOptions} from './VoiceOptions';
import {voiceLabel,voiceGroup,validSpeed} from './voiceConfig';
type RepairCharacter={id:string;name:string;voice:string;speed:number;color:string};
const nameKey=(value:string)=>value.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().trim();

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
  onUpdate,
}: {
  projectId: string | null;
  onUpdate?: (project:any)=>void;
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
  const [repairCharacterId,setRepairCharacterId]=useState('');
  const [characters,setCharacters]=useState<RepairCharacter[]>([]);
  const repairCharacter=characters.find(c=>c.id===repairCharacterId);
  const [repairError, setRepairError] = useState('');
  const [availableRepairVoices, setAvailableRepairVoices] =
    useState<string[]>([]);

  async function refresh() {
    if (!projectId) return;
    setLoading(true);
    setError('');

    try {
      const [response,castResponse] = await Promise.all([
        fetch(`/api/projects/${encodeURIComponent(projectId)}/audio-library`),
        fetch(`/api/projects/${encodeURIComponent(projectId)}`),
      ]);
      if (!response.ok || !castResponse.ok) {
        throw new Error(`No se pudo cargar la biblioteca o el elenco (HTTP ${!response.ok?response.status:castResponse.status})`);
      }
      const result: AudioLibraryData = await response.json();
      const project = await castResponse.json();
      setCharacters(project.characters || []);
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
    setCharacters([]);
    setRepairing(null);
    setRepairCharacterId('');
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
    const profile=characters.find(c=>nameKey(c.name)===nameKey(s.speaker||''));
    setRepairCharacterId(profile?.id||'');
    setRepairVoice(profile?.voice||s.voice||'em_santa');
    setRepairSpeed(profile?.speed??s.speed??1);
    setRepairError('');
  }

  async function generateOne(s: AudioItem) {
    if (!projectId || s.audio || loading || !repairCharacter) return;

    setLoading(true);
    setRepairError('');

    try {
      const castResponse=await fetch(`/api/projects/${projectId}`);
      if(!castResponse.ok)throw new Error('No se pudo verificar el elenco actual');
      const current=await castResponse.json();
      const profile:RepairCharacter|undefined=current.characters?.find((c:RepairCharacter)=>c.id===repairCharacterId);
      if(!profile||['name','voice','speed','color'].some(k=>profile[k as keyof RepairCharacter]!==repairCharacter[k as keyof RepairCharacter])){
        setCharacters(current.characters||[]);setRepairCharacterId('');
        throw new Error('El perfil del personaje cambió. Vuelve a seleccionarlo para cargar su voz actual.');
      }
      if(!validSpeed(repairVoice,repairSpeed))throw new Error('Elige una voz compatible y una velocidad entre 0.5 y 2.0');
      const patch = await fetch(
        `/api/projects/${projectId}/segments/${s.id}`,
        {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            speaker: profile.name,
            voice: repairVoice,
            speed: repairSpeed,
            color: profile.color,
            reviewed: true,
          }),
        }
      );

      if (!patch.ok) {
        const detail = await patch.text();
        throw new Error(`No se pudo guardar: ${detail}`);
      }

      const patched=await patch.json();
      onUpdate?.(patched);
      const response = await fetch(
        `/api/projects/${projectId}/segments/${s.id}/generate?compact=true`,
        { method: 'POST' }
      );

      if (!response.ok) {
        const detail = await response.text();
        throw new Error(`No se pudo generar: ${detail}`);
      }

      const generated=await response.json();
      onUpdate?.({...patched,chapters:patched.chapters.map((ch:any)=>({...ch,segments:ch.segments.map((item:any)=>item.id===s.id?generated.segment:item)}))});
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
                  Archivos guardados del proyecto · Generado no significa pronunciación actualizada
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

            <button type="button" onClick={()=>window.dispatchEvent(new Event("lia-open-project-status"))}>Ver estado del libro y aplicar correcciones</button>
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
                                <strong>Reparación individual</strong>

                                <label>
                                  Personaje
                                  <select aria-label="Personaje del fragmento" style={{display:"block",width:"100%",maxWidth:"100%",boxSizing:"border-box"}} disabled={loading} value={repairCharacterId} onChange={e=>{
                                    const character=characters.find(c=>c.id===e.target.value);
                                    setRepairCharacterId(character?.id||'');
                                    if(character){setRepairVoice(character.voice);setRepairSpeed(character.speed)}
                                    setRepairError('');
                                  }}>
                                    <option value="">{s.speaker&&nameKey(s.speaker)!=='sin atribuir'?s.speaker+' — selecciona su perfil':'Selecciona un personaje del elenco'}</option>
                                    {characters.map(character=><option key={character.id} value={character.id}>{character.name} — {voiceLabel(character.voice)} · {character.speed}x</option>)}
                                  </select>
                                </label>
                                {repairCharacter&&<p role="status">Perfil guardado de <b>{repairCharacter.name}</b>: {voiceLabel(repairCharacter.voice)} · {voiceGroup(repairCharacter.voice)} · {repairCharacter.speed}x</p>}
                                {!characters.length&&<p>No hay perfiles disponibles. Configura el elenco y actualiza la biblioteca.</p>}
                                <label>
                                  Voz para este fragmento
                                  <select aria-label="Voz del fragmento" style={{display:"block",width:"100%",maxWidth:"100%",boxSizing:"border-box"}} disabled={loading||!repairCharacter} value={repairVoice} onChange={e=>setRepairVoice(e.target.value)}>
                                    <VoiceOptions voices={availableRepairVoices} selected={repairVoice}/>
                                  </select>
                                </label>
                                {repairCharacter&&(repairVoice!==repairCharacter.voice||repairSpeed!==repairCharacter.speed)&&<small>El cambio manual se guardará solo en este fragmento. El perfil del personaje conserva {voiceLabel(repairCharacter.voice)} · {repairCharacter.speed}x.</small>}

                                <label>
                                  Velocidad · {repairSpeed}x
                                  <input
                                    style={{display:"block",marginTop:6,maxWidth:"100%"}}
                                    aria-label="Velocidad del fragmento"
                                    disabled={loading||!repairCharacter}
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
                                  Al guardar confirmas el hablante y la revisión del contenido. Se generará solamente este fragmento.
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
                                    disabled={loading||!repairCharacter||!validSpeed(repairVoice,repairSpeed)}
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
