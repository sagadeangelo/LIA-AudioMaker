import { useEffect, useRef, useState } from 'react';

type Format = 'mp3' | 'wav';

type ExportStats = {
  chapters: number;
  generated: number;
  pending: number;
};

type ExportJob = {
  id: string;
  status: 'preparing' | 'processing' | 'ready' | 'downloaded' | 'error';
  percent: number;
  message: string;
  format: Format;
  segments: number;
};

export default function BookExportButton({
  projectId,
}: {
  projectId: string | null;
}) {
  const [open, setOpen] = useState(false);
  const [format, setFormat] = useState<Format>('mp3');
  const [partial, setPartial] = useState(true);
  const [stats, setStats] = useState<ExportStats | null>(null);
  const [error, setError] = useState('');
  const [job, setJob] = useState<ExportJob | null>(null);
  const [downloading, setDownloading] = useState(false);

  const polling = useRef<ReturnType<typeof setInterval> | null>(null);
  const downloadedId = useRef<string | null>(null);

  function stopPolling() {
    if (polling.current !== null) {
      clearInterval(polling.current);
      polling.current = null;
    }
  }

  useEffect(() => {
    return () => stopPolling();
  }, []);

  async function readError(response: Response) {
    try {
      const body = await response.json();
      return String(body.detail || response.statusText);
    } catch {
      return `Error HTTP ${response.status}`;
    }
  }

  async function openPanel() {
    if (!projectId) return;

    setOpen(true);
    setError('');
    setStats(null);

    try {
      const response = await fetch(
        `/api/projects/${projectId}/audio-library`
      );

      if (!response.ok) throw new Error(await readError(response));

      const data = await response.json();

      const chapters = data.chapters ?? [];

      const segments = chapters.flatMap(
        (chapter: {
          segments?: Array<{
            excluded?: boolean;
            is_separator?: boolean;
            status?: string;
            audio?: string | null;
          }>;
        }) => chapter.segments ?? []
      );

      const active = segments.filter(
        (segment: {
          excluded?: boolean;
          is_separator?: boolean;
          status?: string;
        }) =>
          !segment.excluded &&
          !segment.is_separator &&
          segment.status !== 'excluded'
      );

      const generated = active.filter(
        (segment: { audio?: string | null }) =>
          Boolean(segment.audio)
      ).length;

      setStats({
        chapters: chapters.length,
        generated,
        pending: active.length - generated,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  function triggerDownload(id: string) {
    if (downloadedId.current === id) return;
    downloadedId.current = id;

    const link = document.createElement('a');
    link.href = `/api/export-book/jobs/${id}/download`;
    link.download = `LIA_AudioMaker_Audiolibro.${format}`;
    document.body.appendChild(link);
    link.click();
    link.remove();

    setDownloading(true);
  }

  async function checkJob(id: string) {
    try {
      const response = await fetch(`/api/export-book/jobs/${id}`);

      if (!response.ok) throw new Error(await readError(response));

      const current = (await response.json()) as ExportJob;
      setJob(current);

      if (current.status === 'ready') {
        stopPolling();
        triggerDownload(current.id);
      }

      if (current.status === 'error') {
        stopPolling();
        setError(current.message);
      }
    } catch (err) {
      stopPolling();
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  async function startExport() {
    if (!projectId || !stats) return;
    if (!partial && stats.pending > 0) return;

    stopPolling();
    downloadedId.current = null;
    setDownloading(false);
    setError('');
    setJob(null);

    try {
      const response = await fetch(
        `/api/projects/${projectId}/export-book/jobs` +
        `?format=${format}&partial=${partial}`,
        { method: 'POST' }
      );

      if (!response.ok) throw new Error(await readError(response));

      const created = (await response.json()) as ExportJob;
      setJob(created);

      polling.current = setInterval(() => {
        void checkJob(created.id);
      }, 1500);

      await checkJob(created.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  if (!projectId) return null;

  const working =
    job?.status === 'preparing' || job?.status === 'processing';

  const canExport =
    !!stats &&
    stats.generated > 0 &&
    (partial || stats.pending === 0) &&
    !working;

  return (
    <>
      <button
        type="button"
        onClick={openPanel}
        style={{
          background: '#e98b32',
          color: '#111',
          padding: '12px 16px',
          whiteSpace: 'nowrap',
          border: 0,
          borderRadius: 10,
          fontWeight: 700,
          cursor: 'pointer',
        }}
      >
        Exportar libro completo
      </button>

      {open && (
        <div style={{
          position: 'fixed',
          inset: 0,
          zIndex: 100010,
          background: '#000c',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          padding: 16,
        }}>
          <div style={{
            width: 'min(500px, 100%)',
            background: '#172331',
            color: '#f2f5fa',
            border: '1px solid #e98b32',
            borderRadius: 14,
            padding: 24,
            boxShadow: '0 20px 55px #0009',
          }}>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}>
              <h2 style={{ margin: 0, fontSize: 21 }}>
                Exportar audiolibro completo
              </h2>
              <button
                type="button"
                onClick={() => setOpen(false)}
                style={{
                  background: 'transparent',
                  color: 'white',
                  border: 0,
                  fontSize: 24,
                  cursor: 'pointer',
                }}
              >
                {'\u00d7'}
              </button>
            </div>

            {stats && (
              <p style={{ lineHeight: 1.8 }}>
                Capítulos: <strong>{stats.chapters}</strong>
                <br />
                Fragmentos con audio: <strong>{stats.generated}</strong>
                <br />
                Fragmentos pendientes: <strong>{stats.pending}</strong>
              </p>
            )}

            {!job && (
              <>
                <p>Selecciona el formato del audiolibro:</p>
                <div style={{
                  display: 'flex',
                  gap: 18,
                  marginBottom: 16,
                }}>
                  {(['mp3', 'wav'] as const).map(value => (
                    <label key={value}>
                      <input
                        type="radio"
                        name="lia-export-format"
                        checked={format === value}
                        onChange={() => setFormat(value)}
                      />
                      {' '}{value.toUpperCase()}
                    </label>
                  ))}
                </div>

                <label style={{ display: 'block', marginBottom: 14 }}>
                  <input
                    type="checkbox"
                    checked={partial}
                    onChange={e => setPartial(e.target.checked)}
                  />
                  {' '}Exportar vista previa parcial
                </label>

                {stats && stats.pending > 0 && (
                  <p style={{ color: '#f5bd72', fontSize: 13 }}>
                    {partial
                      ? 'Se omitir?n los fragmentos sin audio.'
                      : 'Genera los fragmentos pendientes para exportar el libro completo.'}
                  </p>
                )}

                <button
                  type="button"
                  onClick={() => void startExport()}
                  disabled={!canExport}
                  style={{
                    width: '100%',
                    background: '#e98b32',
                    color: '#111',
                    border: 0,
                    padding: 13,
                    borderRadius: 8,
                    fontWeight: 700,
                    cursor: canExport ? 'pointer' : 'not-allowed',
                    opacity: canExport ? 1 : 0.5,
                  }}
                >
                  Preparar y descargar {format.toUpperCase()}
                </button>
              </>
            )}

            {job && (
              <div style={{ marginTop: 24 }}>
                <p style={{ fontWeight: 700 }}>
                  {job.status === 'ready'
                    ? 'Archivo preparado'
                    : job.status === 'error'
                      ? 'Error de exportaci?n'
                      : 'Preparando audiolibro...'}
                </p>

                <div
                  role="progressbar"
                  aria-valuenow={job.percent}
                  aria-valuemin={0}
                  aria-valuemax={100}
                  style={{
                    height: 16,
                    borderRadius: 12,
                    background: '#344052',
                    overflow: 'hidden',
                  }}
                >
                  <div style={{
                    height: '100%',
                    width: `${job.percent}%`,
                    background: '#e98b32',
                    transition: 'width 0.3s ease',
                  }} />
                </div>

                <p style={{
                  textAlign: 'center',
                  fontSize: 25,
                  fontWeight: 700,
                  margin: '12px 0',
                }}>
                  {job.percent}%
                </p>

                <p style={{ color: '#bac8d7' }}>
                  {job.message}
                </p>

                {downloading && (
                  <p style={{ color: '#8de6a8' }}>
                    Descarga solicitada al navegador.
                    Revisa la carpeta Descargas.
                  </p>
                )}

                {job.status === 'ready' && (
                  <a
                    href={`/api/export-book/jobs/${job.id}/download`}
                    download
                    style={{ color: '#e98b32' }}
                  >
                    Descargar nuevamente
                  </a>
                )}
              </div>
            )}

            {error && (
              <p style={{ color: '#ff9999' }}>{error}</p>
            )}

            <p style={{
              fontSize: 12,
              color: '#9fb0c3',
              marginBottom: 0,
            }}>
              Los archivos WAV originales no se modifican.
            </p>
          </div>
        </div>
      )}
    </>
  );
}
