# WAOS Vertical Hardening Model

Este release endurece los 11 verticales para moverlos de **preset inteligente** a **sistema especialista**.

## Patrón base

- Core común
- Dominio por vertical
- Playbooks por subvertical
- KPIs por vertical
- Pricing por vertical
- Journeys por vertical

## Contrato estándar que ahora vive en cada vertical

- `vertical_entity_types`
- `vertical_pipeline_stages`
- `vertical_quote_types`
- `vertical_resource_types`
- `vertical_followup_policies`
- `vertical_kpi_definitions`
- `vertical_playbooks`
- `vertical_document_types`

## 8 capas de vertical duro

1. Entidades persistentes propias del nicho
2. Pipeline del negocio específico
3. Pricing y cotización del nicho
4. Agenda y recursos del nicho
5. Postventa / continuidad / recurrencia
6. Documentos / compliance / consentimientos
7. KPIs que importan en ese negocio
8. Automatizaciones que mueven dinero o retención

## Mínimo exigible por vertical

- 1 entidad reina
- 1 pipeline propio
- 1 cotización propia
- 1 recurrencia propia
- 1 dashboard propio

## Olas recomendadas

### Ola 1
- dental
- aesthetic
- fitness
- auto-service

### Ola 2
- vet
- beauty
- field-services
- real-estate

### Ola 3
- education
- professional-intake
- commerce


## Vertical runtime ejecutable

Cada vertical ahora expone un bloque `vertical_runtime` con ocho motores: `pipeline_machine`, `pricing_engine`, `resource_capacity`, `recurrence_engine`, `kpi_engine`, `automation_engine`, `document_flow` y `matching_engine`. Esta capa convierte la vertical de preset narrativo a sistema especialista reusable.


## Motor v12 full transaccional

La versión v12 endurece el portafolio más allá del runtime declarativo. Cada vertical ahora expone `transactional_motor_v12` con ocho bloques: sistema de registro, primitivas transaccionales, aggregates, orquestación, finanzas, operación, compliance/auditoría y vistas transaccionales.

### Qué añade
- comandos e idempotencia
- eventos de dominio y ledger
- aggregate root por vertical
- quote / booking / execution / payment account / continuity como aggregates base
- sagas y guards de dinero
- resource locking y board operativo
- consent gates y evidencia obligatoria
- command catalog y event catalog visibles en frontend

### Objetivo
Que WAOS no solo modele el nicho, sino que también tenga un contrato común para ejecutar cobro, reserva, cumplimiento, entrega, cierre y recompra con semántica vertical.
