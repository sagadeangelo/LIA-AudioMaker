# Producción automática de un capítulo · 0.6.21

Exporta un capítulo completo desde Revisión del manuscrito → Exportar paquete para IA. Un modelo externo prepara el JSON conforme al esquema exportado. Importar y guardar solo registra el plan. En el plan guardado aparece Producción automática de capítulo: comprobar, resolver pendientes y confirmar iniciar.

El ejecutor exige todas las escenas y todos los fragmentos del capítulo. Reutiliza WAV aprobados cuando personaje, voz y velocidad coinciden. Las partes explícitas del JSON permiten separar diálogo y narración conservando exactamente el texto concatenado. No interpreta instrucciones libres de las respuestas editoriales. Las emociones y delivery describen la intención pero no agregan capacidades al motor TTS.

Los recursos nuevos deben estar ya en biblioteca. Las pistas existentes se conservan; no deben repetirse en el JSON. Las entradas por citas se estiman proporcionalmente al texto y requieren aceptación explícita: no son alineación por palabra. No descarga automáticamente recursos faltantes ni decide licencias. Mezcla escenas, concatena y entrega WAV, MP3 128 kbps y créditos. No aprueba automáticamente la calidad.

Se guarda un punto de recuperación tras cada fragmento y escena. Pausar termina la operación en curso; reanudar evita repetir pasos completados. Un reinicio deja el trabajo interrumpido hasta reanudar manualmente. Una edición externa del proyecto bloquea la reanudación para evitar aplicar un plan obsoleto. Una caída entre respuesta del proveedor y guardado podría repetir ese único fragmento: no se promete facturación exactamente una vez.

Una producción activa bloquea otras mezclas. No edites ni generes manualmente durante la prueba. Se conservan archivos anteriores y copias de metadatos originales dentro del registro de producción; esta versión no incorpora un botón de reversión integral del capítulo. Hasta 20 producciones por proyecto. Límites del mezclador: 30 minutos, 200 fragmentos y 16 pistas por escena.

El instalador no produce el libro ni cambia datos del usuario. Ejecuta pruebas aisladas, compila frontend y reconstruye/reinicia backend. Tras instalar, Ctrl+F5. La prueba del capítulo real requiere una exportación actual del proyecto después de las divisiones ya aplicadas. El paquete antiguo de escena 1 no contiene el capítulo completo ni los identificadores actuales.
