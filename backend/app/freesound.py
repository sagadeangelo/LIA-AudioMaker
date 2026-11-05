"""Local Freesound connection and project SFX library. Never alters narration."""
import hashlib
import json
import os
import secrets
import subprocess
import tempfile
import threading
import time
import uuid
import wave
from pathlib import Path
from urllib.parse import urlencode, urlsplit

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix='/api')
BASE = 'https://freesound.org/apiv2/'
FIELDS = 'id,name,username,url,license,duration,previews,filesize,type'
MAX_BYTES = 50 * 1024 * 1024
MAX_SECONDS = 600
_guard = threading.RLock()
_pending = {}
_cache = {}


def main():
    from . import main as m
    return m


def credentials():
    cid, key = os.getenv('FREESOUND_CLIENT_ID', '').strip(), os.getenv('FREESOUND_API_KEY', '').strip()
    if not key:
        raise HTTPException(503, 'Falta FREESOUND_API_KEY en el backend. Actualiza el servicio después de guardar .env.')
    return cid, key


def namespace():
    cid, key = credentials()
    return hashlib.sha256((cid + ':' + key).encode()).hexdigest()


def token_path():
    return main().DATA / 'private' / 'freesound.json'


def read_token():
    try:
        value = json.loads(token_path().read_text())
        return value if value.get('credentials') == namespace() else {}
    except (OSError, ValueError, HTTPException):
        return {}


def write_token(value):
    path = token_path()
    path.parent.mkdir(mode=0o700, exist_ok=True)
    os.chmod(path.parent, 0o700)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix='.freesound-')
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(value, f)
        os.replace(tmp, path)
    finally:
        Path(tmp).unlink(missing_ok=True)


def safe_url(url, preview=False):
    try:
        u = urlsplit(url)
        hosts = {'freesound.org', 'www.freesound.org', 'cdn.freesound.org'}
        if u.scheme == 'https' and u.hostname in hosts and not u.username and not u.password and u.port in (None, 443):
            return url
    except (ValueError, TypeError):
        pass
    return ''


def remote_error(status):
    messages = {400: 'Freesound rechazó la solicitud o el código. Inicia otra autorización.',
                401: 'Freesound rechazó la credencial o la sesión. Comprueba .env o vuelve a conectar la cuenta.',
                403: 'Freesound no permite esta operación con la autorización actual.',
                404: 'El sonido ya no está disponible en Freesound.',
                429: 'Freesound alcanzó su límite de solicitudes. Espera antes de reintentar.'}
    raise HTTPException(429 if status == 429 else 502, messages.get(status, 'Freesound no está disponible. Reintenta más tarde.'))


def request_json(path, *, params=None, form=None):
    _, key = credentials()
    try:
        with httpx.Client(timeout=25, follow_redirects=False) as client:
            r = client.post(BASE + path, data=form) if form is not None else client.get(BASE + path, params=params, headers={'Authorization': 'Token ' + key})
            if r.status_code != 200:
                remote_error(r.status_code)
            result = r.json()
            if not isinstance(result, dict):
                raise ValueError()
            return result
    except (httpx.HTTPError, ValueError):
        raise HTTPException(502, 'No se pudo leer la respuesta de Freesound. Comprueba tu conexión.') from None


def store_grant(grant, previous=None):
    if not isinstance(grant.get('access_token'), str) or not grant['access_token']:
        raise HTTPException(502, 'Freesound no devolvió una autorización válida.')
    try:
        expiry = min(max(int(grant.get('expires_in', 86400)), 1), 86400)
    except (TypeError, ValueError):
        raise HTTPException(502, 'Freesound devolvió una caducidad inválida.') from None
    value = {'credentials': namespace(), 'access_token': grant['access_token'],
             'refresh_token': grant.get('refresh_token') or (previous or {}).get('refresh_token'),
             'expires_at': time.time() + expiry}
    write_token(value)
    return value


def access_token():
    with _guard:
        value = read_token()
        if not value.get('access_token'):
            raise HTTPException(409, 'Conecta tu cuenta de Freesound para descargar originales.')
        if value.get('expires_at', 0) < time.time() + 60:
            if not value.get('refresh_token'):
                raise HTTPException(409, 'La sesión caducó. Conecta de nuevo tu cuenta.')
            cid, key = credentials()
            value = store_grant(request_json('oauth2/access_token/', form={
                'client_id': cid, 'client_secret': key, 'grant_type': 'refresh_token',
                'refresh_token': value['refresh_token']}), value)
        return value['access_token']


def license_name(value):
    value = str(value or '')
    u = urlsplit(value)
    if u.hostname in {'creativecommons.org', 'www.creativecommons.org'}:
        if u.path.rstrip('/') == '/publicdomain/zero/1.0': return 'CC0'
        if u.path.rstrip('/') in {'/licenses/by/3.0', '/licenses/by/4.0'}: return 'CC BY'
    return {'Creative Commons 0': 'CC0', 'Attribution': 'CC BY'}.get(value, 'No admitida')


def sound_info(raw):
    try:
        sid = int(raw['id'])
        duration = float(raw.get('duration') or 0)
        size = int(raw.get('filesize') or 0)
    except (TypeError, KeyError, ValueError):
        raise HTTPException(502, 'Metadatos de sonido inválidos.') from None
    previews = raw.get('previews') or {}
    preview = safe_url(previews.get('preview-hq-mp3', '') or previews.get('preview-lq-mp3', ''), preview=True)
    license_value = str(raw.get('license', ''))
    return {'freesound_id': sid, 'name': str(raw.get('name', 'Sonido'))[:300],
            'author': str(raw.get('username', ''))[:150], 'source_url': safe_url(raw.get('url', '')),
            'license': license_name(license_value), 'license_url': license_value if license_value.startswith(('https://creativecommons.org/', 'http://creativecommons.org/')) else '',
            'license_original': license_value, 'duration': duration, 'filesize': size,
            'preview_url': preview, 'importable': license_name(license_value) in {'CC0', 'CC BY'} and 0 < duration <= MAX_SECONDS and 0 < size <= MAX_BYTES}


@router.get('/freesound/status')
def status():
    cid, key = os.getenv('FREESOUND_CLIENT_ID', '').strip(), os.getenv('FREESOUND_API_KEY', '').strip()
    with _guard:
        value = read_token()
    return {'configured': bool(key), 'oauth_available': bool(cid and key),
            'connected': bool(value.get('access_token')), 'max_seconds': MAX_SECONDS, 'max_mb': 50}


@router.get('/freesound/search')
def search(q: str = Query(min_length=2, max_length=150), license: str = Query(default='cc0', pattern='^(cc0|by)$'), page: int = Query(default=1, ge=1, le=100)):
    q = q.strip()
    if len(q) < 2: raise HTTPException(422, 'Escribe al menos dos caracteres.')
    cache_key = (namespace(), q, license, page)
    with _guard:
        cached = _cache.get(cache_key)
        if cached and cached[0] > time.time(): return cached[1]
    label = 'Creative Commons 0' if license == 'cc0' else 'Attribution'
    raw = request_json('search/', params={'query': q, 'fields': FIELDS, 'page': page, 'page_size': 12,
        'filter': f'license:"{label}" duration:[0 TO {MAX_SECONDS}] filesize:[0 TO {MAX_BYTES}]'})
    result = {'count': raw.get('count', 0), 'page': page, 'has_next': bool(raw.get('next')),
              'results': [sound_info(r) for r in raw.get('results', [])[:12]]}
    with _guard:
        if len(_cache) > 100: _cache.clear()
        _cache[cache_key] = (time.time() + 300, result)
    return result


@router.post('/freesound/oauth/start')
def oauth_start():
    cid, _ = credentials()
    if not cid: raise HTTPException(503, 'Falta FREESOUND_CLIENT_ID en el backend.')
    state = secrets.token_urlsafe(32)
    with _guard:
        for old in list(_pending):
            if _pending[old][0] < time.time(): _pending.pop(old)
        if len(_pending) > 50: _pending.clear()
        _pending[state] = (time.time() + 600, namespace())
    return {'state': state, 'url': BASE + 'oauth2/authorize/?' + urlencode({'client_id': cid, 'response_type': 'code', 'state': state})}


class OAuthCode(BaseModel):
    state: str = Field(min_length=20, max_length=200)
    code: str = Field(min_length=1, max_length=1000)


@router.post('/freesound/oauth/finish')
def oauth_finish(body: OAuthCode):
    with _guard:
        pending = _pending.pop(body.state, None)
        if not pending or pending[0] < time.time() or pending[1] != namespace():
            raise HTTPException(409, 'La autorización caducó o cambió. Vuelve a iniciarla desde este panel.')
        cid, key = credentials()
        store_grant(request_json('oauth2/access_token/', form={'client_id': cid, 'client_secret': key,
            'grant_type': 'authorization_code', 'code': body.code.strip()}))
    return status()


@router.delete('/freesound/oauth')
def disconnect():
    with _guard:
        token_path().unlink(missing_ok=True)
        _pending.clear()
    return status()


def download_original(sid, target, token):
    """Follow only Freesound redirects, stripping credentials on host changes."""
    url = BASE + f'sounds/{sid}/download/'
    headers = {'Authorization': 'Bearer ' + token}
    try:
        with httpx.Client(timeout=45, follow_redirects=False) as client:
            for _ in range(6):
                if not safe_url(url): raise HTTPException(502, 'Freesound indicó un destino de descarga no admitido.')
                with client.stream('GET', url, headers=headers) as r:
                    if r.status_code in (301, 302, 303, 307, 308):
                        next_url = str(r.url.join(r.headers.get('location', '')))
                        if urlsplit(next_url).hostname != urlsplit(url).hostname: headers = {}
                        url = next_url
                        continue
                    if r.status_code != 200: remote_error(r.status_code)
                    size = 0
                    with target.open('wb') as f:
                        for block in r.iter_bytes(65536):
                            size += len(block)
                            if size > MAX_BYTES: raise HTTPException(413, 'El original supera 50 MB.')
                            f.write(block)
                    if not size: raise HTTPException(502, 'El sonido descargado está vacío.')
                    return
            raise HTTPException(502, 'Demasiadas redirecciones al descargar el sonido.')
    except httpx.HTTPError:
        raise HTTPException(502, 'La descarga se interrumpió. Reintenta cuando haya conexión.') from None


@router.get('/projects/{pid}/sound-effects')
def library(pid: str):
    with main().lock:
        return {'sounds': main().get(pid).get('sound_effects', [])}


class ImportSound(BaseModel):
    sound_id: int = Field(gt=0)


@router.post('/projects/{pid}/sound-effects/freesound')
def import_sound(pid: str, body: ImportSound):
    m = main()
    with m.lock:
        p = m.get(pid)
        existing = next((s for s in p.get('sound_effects', []) if s.get('freesound_id') == body.sound_id), None)
        if existing: return {'sound': existing, 'already_saved': True}
    info = sound_info(request_json(f'sounds/{body.sound_id}/', params={'fields': FIELDS}))
    if info['freesound_id'] != body.sound_id: raise HTTPException(502, 'Freesound devolvió otro sonido.')
    if not info['importable']: raise HTTPException(422, 'Solo se admiten CC0 o CC BY, hasta 10 minutos y 50 MB por original.')
    token = access_token()
    name = 'sfx_' + uuid.uuid4().hex + '.wav'
    output = m.DATA / name
    try:
        with tempfile.TemporaryDirectory(prefix='lia-sfx-') as tmp:
            original = Path(tmp) / 'original'
            download_original(body.sound_id, original, token)
            try:
                result = subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-protocol_whitelist', 'file,pipe',
                    '-i', str(original), '-map', '0:a:0', '-vn', '-t', str(MAX_SECONDS + 1), '-ar', '48000', '-ac', '2', '-c:a', 'pcm_s16le', str(output)],
                    capture_output=True, timeout=60)
            except (OSError, subprocess.TimeoutExpired):
                raise HTTPException(503, 'No se pudo convertir el sonido. Comprueba FFmpeg en el backend.') from None
            if result.returncode or not output.is_file(): raise HTTPException(422, 'El archivo de Freesound no contiene audio compatible.')
            with wave.open(str(output), 'rb') as w:
                duration = w.getnframes() / w.getframerate()
            if duration <= 0 or duration > MAX_SECONDS: raise HTTPException(422, 'La duración real del sonido excede el límite de 10 minutos.')
        item = {k: v for k, v in info.items() if k not in ('preview_url', 'importable')}
        item.update(id=uuid.uuid4().hex, file=name, duration=round(duration, 3), source='freesound',
                    imported_at=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), conversion='WAV PCM 48 kHz estéreo')
        with m.lock:
            p = m.get(pid)  # merge with current project, never an old detached copy
            existing = next((s for s in p.get('sound_effects', []) if s.get('freesound_id') == body.sound_id), None)
            if existing:
                output.unlink(missing_ok=True)
                return {'sound': existing, 'already_saved': True}
            p.setdefault('sound_effects', []).append(item)
            m.save(p)
        return {'sound': item, 'already_saved': False}
    except BaseException:
        output.unlink(missing_ok=True)
        raise
