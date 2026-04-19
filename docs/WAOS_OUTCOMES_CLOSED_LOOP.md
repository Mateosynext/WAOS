# WAOS Outcomes Closed-Loop Learning

## Idea central

WAOS ya tiene piezas valiosas de aprendizaje:

- experiments
- reviews
- QA/coaching loops
- analytics operativos
- ownership / takeover / routing
- template lifecycle analytics
- pipeline comercial
- pagos, agenda y follow-ups

Pero hoy esas piezas siguen demasiado separadas.

El salto importante no es solamente mejorar prompts. El salto es construir una capa que aprenda de **outcomes reales de negocio y operación** y que use ese aprendizaje para ajustar automáticamente el sistema.

En una frase:

> WAOS no debe optimizar solo generación de mensajes; debe optimizar resultados reales por conversación, flujo, operador, template y bot.

## Qué problema existe hoy

Hoy el sistema puede medir experimentos, revisar calidad y observar eventos.

Lo que todavía falta cerrar es el loop completo:

1. el sistema ejecuta
2. se observan outcomes productivos reales
3. esos outcomes se atribuyen a prompts / flows / routing / templates / timing / operador
4. el sistema aprende qué funcionó y qué dañó conversión o experiencia
5. esa evidencia ajusta configuración futura

Sin ese loop, WAOS corre el riesgo de optimizar métricas intermedias y no resultados finales.

## Outcomes que deben ser first-class citizens

La capa de aprendizaje debe soportarse sobre señales como:

- reply rate
- booking rate
- payment rate
- show rate
- refund rate
- escalation rate
- CSAT / NPS
- operator edits
- takeover frequency
- template performance
- delivery / read data
- lost reasons
- no-response decay
- cancellation / reschedule outcomes
- time-to-resolution
- revenue per conversation
- recovery rate after failed payment or failed booking

No todas las verticales usarán todas las señales con el mismo peso, pero el modelo de producto debe permitir combinarlas.

## Principio de diseño

El sistema no debe aprender únicamente de prompts A/B.

Debe aprender de la cadena completa:

- **qué se dijo**
- **cuándo se dijo**
- **en qué contexto se dijo**
- **qué hizo después el usuario**
- **qué corrigió el operador**
- **si hubo takeover o escalación**
- **si terminó en ingreso, asistencia, devolución, satisfacción o pérdida**

## Closed loop propuesto

### 1. Outcome event ledger

Crear una capa de eventos normalizados que capture outcomes por conversación, lead, cita, pago y operador.

Ejemplos de eventos:

- `message_replied`
- `template_delivered`
- `template_read`
- `appointment_booked`
- `appointment_rescheduled`
- `appointment_showed`
- `payment_link_opened`
- `payment_completed`
- `payment_refunded`
- `human_takeover_started`
- `human_takeover_failed`
- `operator_reply_edited`
- `conversation_escalated`
- `conversation_resolved`
- `csat_recorded`
- `lead_marked_lost`

Cada evento debe quedar ligado a:

- organization
- bot
- conversation
- contact / lead
- channel
- flow / playbook / prompt artifact / template version
- assigned operator o team
- timestamp
- attributable context

### 2. Attribution layer

No basta con guardar eventos. Hay que atribuir resultados.

La atribución debe responder preguntas como:

- qué prompt empujó más reply rate sin disparar más takeovers
- qué template genera lectura, respuesta y pago, no solo delivery
- qué timing mejora booking show rate y reduce cancelaciones
- qué operador corrige sistemáticamente salidas del bot y en qué temas
- qué playbook o routing genera más revenue neto y menos refund
- qué secuencias terminan con lost reasons repetidos

La atribución debe operar con ventanas configurables por vertical:

- reply window
- booking window
- payment window
- show window
- refund window

### 3. Learning datasets operativos

Sobre ese ledger se deben construir datasets de aprendizaje listos para producto:

- performance por prompt
- performance por flow
- performance por template y versión
- performance por routing rule
- performance por next-best-action
- performance por operador vs AI-only
- performance por timing / send window
- performance por tono / style family
- performance por vertical / branch / location / source

### 4. Decision surfaces que consumen el aprendizaje

La evidencia aprendida debe poder ajustar:

- prompts
- flows
- policies
- routing
- playbooks
- templates
- timing
- tone
- next-best-action
- escalation thresholds
- takeover guardrails
- follow-up cadences

## Qué debe cambiar en WAOS con este loop

### Prompts

No solo versión A vs versión B, sino ranking por outcome compuesto:

- reply
- booking
- pago
- satisfacción
- baja intervención humana

### Flows

Despromover ramas que generan silencios, cancelaciones o perdida comercial.

Promover ramas que sostienen conversión real y baja fricción operativa.

### Policies

Endurecer políticas donde el sistema ve correlación con refund, escalación o edición humana intensiva.

Relajar donde hay evidencia de fricción innecesaria.

### Routing

Mandar conversaciones a humano antes cuando el histórico muestra alta probabilidad de takeover tardío, mala experiencia o pérdida.

Mantener AI-first cuando el histórico muestra cierre limpio y buen resultado.

### Playbooks y templates

Subir o bajar prioridad según:

- lectura real
- respuesta real
- booking real
- pago real
- tasa de reclamo o refund

### Timing

Aprender ventanas reales por vertical, intención, origen y tipo de contacto.

### Tone

Adaptar estilo no por intuición, sino por efectividad observada por segmento.

### Next-best-action

El sistema debe sugerir la acción con mayor expected value contextual, no solo la más común.

## Outcome score compuesto

WAOS debe soportar un `outcome_score` configurable por vertical u objetivo.

Ejemplo conceptual:

- +reply
- +booking
- +payment
- +show
- +CSAT
- -refund
- -escalation
- -operator edit intensity
- -late takeover
- -lost outcome

Eso permite que un experimento “ganador” no sea el que obtiene más respuestas vacías, sino el que genera mejor resultado total.

## Uso de señales humanas

La edición humana y el takeover no deben verse solo como fallback operativo.

También son señal de aprendizaje.

### Operator edits

Cuando el humano reescribe:

- tono
- claim
- CTA
- orden del mensaje
- política aplicada
- timing sugerido

...eso debe registrarse como diferencia útil para mejorar el sistema.

### Takeover frequency

Una alta frecuencia de takeover por intención, vertical o flujo indica:

- hueco de política
- mala clasificación
- mala detección de riesgo
- bot incapaz de cerrar el caso
- experiencia demasiado rígida

### Lost reasons

Los motivos de pérdida deben retroalimentar:

- playbooks
- pricing narratives
- objection handling
- qualification
- routing
- follow-up strategy

## Arquitectura sugerida

### Nuevos bloques lógicos

1. **Outcome Ledger**
   - eventos normalizados y trazables

2. **Attribution Engine**
   - asigna crédito y blame a componentes del sistema

3. **Learning Aggregator**
   - produce scorecards por prompt / flow / template / routing / operator / timing

4. **Optimization Control Layer**
   - recomienda o aplica cambios de configuración con guardrails

5. **Experiment + Rollout Governor**
   - mueve tráfico hacia variantes ganadoras sin perder auditabilidad

## Guardrails

El closed loop no debe auto-optimizar ciegamente.

Necesita:

- mínimos de muestra
- ventanas de estabilidad
- segmentación por vertical
- protection contra Simpson's paradox
- revisión humana para cambios sensibles
- rollbacks
- auditoría de por qué se cambió algo
- separación entre métricas leading y lagging

## Fases recomendadas

### Fase 1: observabilidad de outcomes

- ledger unificado
- scorecards básicas
- dashboards por prompt / template / operator / flow
- captura de delivery, read, reply, booking, payment, refund, takeover, lost reason

### Fase 2: atribución y ranking

- outcome attribution
- outcome score configurable
- ranking de variantes
- recomendador de next-best-action entrenado con outcomes

### Fase 3: optimization control

- promociones automáticas con guardrails
- demotion automática de variantes dañinas
- routing adaptativo
- timing optimization
- template selection por expected outcome

### Fase 4: self-improving operating system

- learning loop multicapas entre CRM, inbox, agenda, pagos y soporte
- optimization continua con revisión humana donde el riesgo lo amerite

## Qué gana el producto

Con este loop, WAOS deja de ser solo un sistema con componentes inteligentes sueltos y pasa a ser:

- un sistema que aprende de resultados reales
- un sistema que entiende costo operativo además de conversión
- un sistema que mejora prompts, flows y operaciones con evidencia
- un sistema que acerca automation quality a business quality

## Definición ejecutiva

La brecha no es “tener experiments”.

La brecha es tener un **closed loop de aprendizaje por outcomes** que una:

- experiments
- reviews
- operator behavior
- delivery telemetry
- CRM outcomes
- agenda outcomes
- payment outcomes
- support outcomes

...y convierta eso en mejoras concretas sobre el runtime.

Ese closed loop es una de las piezas más estratégicas para que WAOS evolucione de automation stack a operating system verdaderamente adaptativo.

## Backend blueprint aterrizado

Este ZIP ya incluye una bajada más concreta para implementación backend:

- `docs/WAOS_OUTCOMES_CONTROL_PLANE.md`
- `backend/db/migrations/004_outcomes_closed_loop.sql`

Ahí queda definido:

- modelo de datos base para exposures, events, attribution, scorecards y decisions
- API mínima de ingesta, consulta y control
- jobs de normalización, attribution, recompute y guardrail enforcement
- scorecards iniciales por prompt, flow, template, routing y operator assist
- promotion / demotion / rollback con auditoría

