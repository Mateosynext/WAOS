# WAOS Tool Execution Outcomes Flywheel

Esta mejora conecta la capa de ejecución operativa con la capa de resultados reales para que WAOS no solo ejecute, sino que aprenda automáticamente qué acciones generan citas, asistencia, cobros y avance comercial.

## Qué cambia

- cada `tool_execution_run` exitoso crea una exposición en `outcome_exposures`
- la exposición persiste `tool_execution_run_id`, `tool_action`, `tool_adapter_key` y `tool_provider`
- el runtime emite eventos operativos inmediatos según la acción ejecutada
- los outcomes reales posteriores se atribuyen de vuelta al run por conversación, contacto, cita, pago o lead
- se recalculan scorecards automáticos para `tool_action`, `tool_adapter`, `tool_provider` y `tool_execution_run`

## Outcomes automáticos por acción

- `book_appointment` → `appointment_scheduled`
- `reschedule` → `appointment_rescheduled`
- `create_payment_link` → `payment_started`
- `update_contact_stage` → `lead_stage_progressed`
- `send_receipt` → `receipt_sent`

## Resultado

Con esto, un link de pago ya no se mide solo por haber sido generado. También se puede medir por cuánto revenue terminó cerrando después. Lo mismo aplica para agenda, asistencia y progreso de etapa.
