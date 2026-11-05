<div align="center">

# 🎧 LIA AudioMaker

### De manuscritos a experiencias sonoras

**Estudio local de producción de audiolibros asistido por IA**

![Estado](https://img.shields.io/badge/ESTADO-MVP_FUNCIONAL-20252B?style=for-the-badge&labelColor=11151C)
![Versión](https://img.shields.io/badge/VERSI%C3%93N-v0.1.9--mvp-FF8A00?style=for-the-badge&labelColor=11151C)
![Plataforma](https://img.shields.io/badge/PLATAFORMA-Windows-2D3642?style=for-the-badge&labelColor=11151C)
![Licencia](https://img.shields.io/badge/LICENCIA-Consultar_repositorio-667085?style=for-the-badge&labelColor=11151C)

**🟠 Producción · 🟢 Progreso · 🔴 Revisión · ⚫ Estudio oscuro**

[**Repositorio**](https://github.com/sagadeangelo/LIA-AudioMaker) · [**Versión MVP**](https://github.com/sagadeangelo/LIA-AudioMaker/tree/v0.1.9-mvp) · [**Documentación**](docs/)

</div>

---

## ✨ ¿Qué es LIA AudioMaker?

**LIA AudioMaker** es una aplicación de escritorio de uso local, con interfaz web, para transformar manuscritos en audiolibros. Reúne la preparación del texto, la asignación de voces, la generación de fragmentos de audio, la revisión y la exportación del libro en un mismo entorno.

Su propósito es evolucionar hacia un **estudio de producción integral**, en el que las personas puedan crear, corregir y publicar narraciones sin tener que trabajar manualmente con cientos de archivos de sonido.

> **Estado real:** existe un MVP funcional de producción y exportación. **No** significa que estén completados la dirección automática de diálogos, la actuación emocional, la corrección inteligente de pronunciación, la mezcla de efectos ni la generación de videos para YouTube.

## 🎛️ El estudio de un vistazo

| Área | Qué permite hacer | Estado |
|:--|:--|:--|
| 📚 **Proyectos y manuscritos** | Organizar libros y trabajar por capítulos y fragmentos | Implementado en el proyecto |
| 🎭 **Casting de voces** | Configurar voces para narrador y personajes | Implementado; requiere revisión humana |
| 🗣️ **Síntesis de voz** | Generar audio mediante los proveedores integrados, incluido Azure y Kokoro | Integrado; depende de la configuración local y del proveedor |
| 🎧 **Biblioteca de audio** | Consultar y administrar material de audio del proyecto | Implementado |
| 🔄 **Generación por fragmentos** | Trabajar con fragmentos y revisar resultados | Implementado |
| 📦 **Exportación de audiolibro** | Exportar el libro en MP3 o WAV y seguir el progreso | **Validado con exportación MP3 parcial** |
| 🧠 **Director de diálogos IA** | Detectar y atribuir voces con contexto y confianza | Planeado |
| ✍️ **Voice Editor** | Corregir pronunciaciones y regenerar sin perder el original | Planeado |
| 🎚️ **Sound Studio** | Incorporar ambientes, música y efectos en pistas separadas | Planeado |
| 🎬 **Visual Story** | Crear videos narrados con imágenes cinematográficas para YouTube | Planeado |

### 🎙️ Flujo de producción

```mermaid
flowchart LR
    A[📖 Manuscrito] --> B[🧩 Capítulos y fragmentos]
    B --> C[🎭 Voces y revisión]
    C --> D[🎙️ Generación de audio]
    D --> E[🎧 Biblioteca y control]
    E --> F[📦 MP3 / WAV]
    F -. Evolución futura .-> G[🎬 Video para YouTube]
```

## 🏁 Hito del primer MVP

El primer flujo de exportación se probó con la novela **«Ángelo, el Proyecto Ditóx»**, organizada en **21 capítulos**. Se obtuvo y escuchó un archivo MP3 de aproximadamente **4 horas, 11 minutos y 13 segundos**.

Esta prueba demuestra que la exportación parcial funciona en ese escenario. **No equivale a una auditoría completa** de continuidad narrativa, pronunciación, voces o calidad de todos los fragmentos.

## 🧰 Tecnologías

| Componente | Tecnología |
|:--|:--|
| Interfaz | React, TypeScript y Vite |
| API | Python y FastAPI |
| Persistencia | PostgreSQL mediante Docker; SQLAlchemy en la implementación inicial |
| Audio | FFmpeg y archivos WAV/MP3 |
| Síntesis | Integraciones de Azure y Kokoro; componentes iniciales de eSpeak NG según la configuración |
| Entorno de desarrollo | Windows y PowerShell |

## 🚀 Inicio rápido en Windows

**Ruta de trabajo prevista:**

```text
C:\LIA_RECUPERACION\REPOS_GITHUB\lia_audiomaker
```

### 1. Preparar el proyecto

Abre PowerShell:

```powershell
Set-Location 'C:\LIA_RECUPERACION\REPOS_GITHUB\lia_audiomaker'
```

Si es una instalación nueva y todavía no existe `.env`, crea uno a partir del ejemplo:

```powershell
Copy-Item .env.example .env
notepad .env
```

> **No sobrescribas un `.env` existente.** Contiene ajustes locales y puede contener credenciales. Nunca lo publiques en GitHub.

### 2. Iniciar todo con un solo comando

El repositorio incluye el iniciador de Windows:

```powershell
powershell.exe -ExecutionPolicy Bypass -File '.\Iniciar-LIA-AudioMaker.ps1'
```

Este script intenta comprobar/iniciar Docker Desktop, levantar los servicios con Docker Compose, iniciar el frontend si hace falta y abrir el navegador.

**Direcciones utilizadas en el entorno MVP:**

- **Aplicación:** http://127.0.0.1:5174
- **Documentación de la API:** http://127.0.0.1:8000/docs

> El puerto **5174** corresponde al entorno de desarrollo utilizado para el MVP. Documentación o scripts anteriores pueden mencionar **5173**; comprueba el puerto mostrado por Vite si modificas la configuración.

### 3. Inicio manual alternativo

En la raíz del proyecto:

```powershell
docker compose up -d
```

En otra terminal:

```powershell
Set-Location 'C:\LIA_RECUPERACION\REPOS_GITHUB\lia_audiomaker\frontend'
npm.cmd run dev -- --host 127.0.0.1 --port 5174 --strictPort
```

Para revisar los servicios:

```powershell
docker compose ps
docker compose logs --tail 50 backend
```

Para detener los contenedores **sin borrar volúmenes**:

```powershell
docker compose stop
```

> ⚠️ Evita `docker compose down -v`, `docker volume prune` y comandos de limpieza masiva: podrían eliminar datos persistentes.

## 🧪 Comprobaciones

**Frontend:**

```powershell
Set-Location 'C:\LIA_RECUPERACION\REPOS_GITHUB\lia_audiomaker\frontend'
npm.cmd run build
```

**Backend:** ejecuta las pruebas desde el entorno Python correspondiente a tu instalación. Si existe el entorno virtual de la implementación inicial:

```powershell
Set-Location 'C:\LIA_RECUPERACION\REPOS_GITHUB\lia_audiomaker\backend'
..\.venv\Scripts\python.exe -m pytest -q
```

Estos comandos son instrucciones de verificación; no implican que todas las pruebas se hayan ejecutado en cada configuración.

## 🛡️ Tus audios y datos primero

El proyecto puede almacenar **manuscritos, metadatos, fragmentos WAV, exportaciones y registros en base de datos**. Una actualización del código no reemplaza una copia de seguridad de esos datos.

1. **Conserva los WAV originales.** No los sobrescribas al corregir o regenerar una voz.
2. **Respalda base de datos y archivos de audio juntos.** Ambos son necesarios para recuperar proyectos completos.
3. **Mantén fuera de GitHub** `.env`, `backups/`, `data/`, archivos de audio generados y modelos locales.
4. **No expongas la API a Internet** sin autenticación, límites de uso y revisión de seguridad.
5. **Comprueba las licencias y condiciones** de los servicios de voz y de los recursos multimedia antes de distribuir contenido.

## 🗺️ Hoja de ruta

```text
v0.1.9-mvp   ● Base funcional: voces, biblioteca y exportación
             │
Próxima fase ○ LIA Voice Editor: pronunciación y regeneración segura
             │
Siguiente    ○ Director de Diálogos IA y revisión de atribuciones
             │
Siguiente    ○ LIA Sound Studio: ambientes y efectos
             │
Objetivo     ○ LIA AutoProducer + LIA Visual Story para YouTube
```

La secuencia puede cambiar según las pruebas y las prioridades del proyecto. Las funciones futuras **no se presentan como ya implementadas**.

## 📂 Estructura principal

```text
lia_audiomaker/
├── backend/                 # API y lógica de audio
│   └── app/
├── frontend/                # Interfaz React / TypeScript
│   └── src/
├── engines/                 # Configuraciones de motores locales
├── docs/                    # Documentación
├── scripts/                 # Herramientas auxiliares
├── docker-compose.yml       # Servicios locales
├── .env.example             # Ejemplo de configuración
└── Iniciar-LIA-AudioMaker.ps1
```

## 📌 Versión y alcance

**Versión de referencia:** [`v0.1.9-mvp`](https://github.com/sagadeangelo/LIA-AudioMaker/tree/v0.1.9-mvp) · **Rama principal:** `main`.

La documentación original describía una **implementación 0.1.0** con análisis heurístico y síntesis básica. Desde entonces se añadieron integraciones de voz, biblioteca de audio y exportación del libro. Este README refleja ese avance, sin afirmar que el producto esté terminado o listo para producción pública.

---

<div align="center">

### 🟠 LIA AudioMaker

**Imagina la historia. Dirige las voces. Produce el audiolibro.**

*Desarrollo local · Evolución continua · Control sobre los archivos originales*

</div>


## Voice Editor — 0.2.0 (rama de trabajo, validación local pendiente)

El botón **LIA Voice Editor** permite guardar un diccionario por proyecto y
personaje, revisar coincidencias por fragmento/capítulo/libro y generar propuestas
con Kokoro o Azure. El texto del manuscrito no cambia. Puedes reproducir el audio
actual y cada propuesta, aprobar, descartar o restaurar versiones anteriores.
Las exportaciones de capítulo y libro utilizan el audio aprobado activo.

Los lotes requieren vista previa y confirmación. Los nuevos trabajos se guardan
en la tabla `jobs`, muestran progreso y se pueden cancelar entre fragmentos.
Un reinicio los marca interrumpidos; no reintenta ni consume Azure automáticamente.
Los WAV anteriores y las propuestas descartadas se conservan.

Pruebas: 34 backend, 11 frontend, compilación TypeScript/Vite y flujo Chromium
con audio PCM de laboratorio. No se ha validado esta fase con el Kokoro/Azure
del usuario ni ejecutado Docker en este entorno. No se declara corregida la
pronunciación de una palabra hasta escucharla con el motor elegido.

Detalles: [Voice Editor](docs/VOICE_EDITOR.md),
[auditoría y plan de las cuatro fases](docs/AUDITORIA_MODULOS.md).


### 0.2.1: probar pronunciaciones antes de guardar

Voice Editor incorpora el catálogo de voces existente, velocidad y frase de
prueba opcional. Puedes escuchar original y variantes, ajustar letras/acentos y
comparar muestras antes de guardar una regla, sin modificar el casting ni los
fragmentos del libro. Ver el [flujo y límites](docs/VOICE_EDITOR.md).


### 0.2.2: eliminar muestras del laboratorio

Cada audio de prueba incluye **Eliminar muestra** con confirmación. El backend
protege cualquier archivo utilizado por proyectos o versiones. Las pruebas no
eliminadas se pueden recuperar al reabrir el laboratorio. No modifica el libro.


### 0.2.3: menciones y pronunciación uniforme

El panel **Quiénes dicen este nombre** localiza menciones y muestra hablante, voz,
capítulo, escena y fragmento. Permite probar una escritura con todas las voces
identificadas y guardar una regla uniforme para todos los hablantes y motores,
incluido el narrador. Las reglas incompatibles se desactivan conservando historial.
Guardar no modifica audios existentes: requieren propuestas y aprobación.

### 0.3.0: revisión del manuscrito con evidencia

**Analizar manuscrito** genera un informe local de candidatos de nombres, lugares,
escenas, emociones y posibles sonidos. Puedes confirmar perfiles, anotar sugerencias
y dividir/deshacer escenas sin cambiar textos, casting o WAV. El importador reconoce
etiquetas mixtas como `Lindsay:` y `Gibrán:`. Es un sistema de reglas revisable, no
una garantía de identificación semántica completa. No inserta efectos automáticamente.
Ver [funcionamiento y límites](docs/MANUSCRIPT_ANALYSIS.md).

### 0.3.1: ajustar una voz e incorporar correcciones

En las menciones de un nombre puedes editar la pronunciación para una voz concreta
sin cambiar las demás. **Revisar incorporación → Incorporar en el audio** genera y
activa versiones nuevas de los fragmentos afectados, previa confirmación, conservando
los WAV anteriores y permitiendo restaurar el lote. Se regeneran los fragmentos
completos; no se recorta ni inserta la muestra aislada del nombre. Las exportaciones
anteriores se conservan. Ver [flujo y límites](docs/VOICE_EDITOR.md).
