# Mejoras implementadas en el portal WAOS

Se actualizó la consola estática en `backend/app/static/` para que el portal se sienta más claro, más premium, más fácil de usar y más útil para vender.

## Pantalla principal
- Resumen del día más claro con métricas visibles al entrar.
- Bloque de "lo más importante hoy" con prioridades operativas.
- Metas visibles del mes con barras de avance.
- Comparación simple contra la semana pasada.
- Alertas redactadas en lenguaje claro.
- Acciones rápidas visibles para navegar a conversación, agenda, cobro, bots y clientes.
- Inicio personalizado con saludo y nombre del negocio.
- Jerarquía visual renovada con hero, tarjetas premium y mejor contraste.
- Estados vacíos explicativos.
- Indicadores de salud del negocio para atención, citas, cobros y seguimiento.

## Bandeja de conversaciones
- Filtros por sin respuesta, quiere cita, quiere pagar, seguimiento y humano.
- Prioridad visual por conversación.
- Resumen corto antes de abrir cada conversación.
- Siguiente mejor paso sugerido.
- Botones rápidos para agendar, cobrar, recordar, marcar seguimiento y pasar a humano.
- Historial de contacto más claro con línea de tiempo.
- Notas internas más visibles.
- Etiquetas humanas editables con sugerencias rápidas.
- Búsqueda más útil por nombre, teléfono, resumen y contexto.
- Espacio de resumen para audios y mensajes largos.

## Clientes
- Vista más completa de clientes y oportunidades.
- Línea de tiempo simple dentro del contexto del cliente seleccionado.
- Lista de clientes que se están enfriando.
- Lista de clientes frecuentes.
- Indicadores de clientes nuevos del día y de la semana.
- Sugerencia de recordatorios / seguimiento por cliente.
- Motivos de pérdida simplificados en seguimiento.
- Segmentos sencillos visibles.
- Datos de contacto más ordenados.
- Espacio de reactivación dedicado.

## Citas y agenda
- Calendario más visual por día.
- Confirmaciones más visibles.
- Lista de no asistencia y cancelaciones.
- Reagendar en un clic desde la vista de agenda.
- Preferencias de recordatorio más simples (persistidas por organización en backend).
- Resumen diario de agenda.
- Seguimiento post-cita desde acciones rápidas.
- Bloqueo de horarios simple (guardado en el portal).
- Vista agrupada por bot/equipo.
- Motivos de cancelación visibles cuando existen en notas.

## Pagos y ventas
- Pantalla de pagos más clara.
- Cobro rápido desde la conversación.
- Recordatorios de pago con tono más elegante.
- Confirmación / estado de pago visible.
- Vista de ventas del día.
- Recuperación de pagos pendientes.
- Motivos de no compra resumidos.
- Promociones y servicios visibles para apoyar venta.
- Resumen por producto / servicio cuando hay datos de insights.
- Reporte simple descargable desde la sección Reportes.

## Notas
- Las preferencias de recordatorios y los bloqueos de horario ya se guardan en backend por organización, con endpoints dedicados y persistencia real fuera del navegador.
- El resto de acciones principales se conecta a los endpoints existentes del backend del paquete.
