# WAOS Hard Vertical Domains

This release adds persistent niche-domain storage for five priority verticals on top of the shared transactional engine:

- dental
- fitness
- aesthetic
- vet
- auto-service

## What changed

The transactional account is still the common orchestration root, but these five verticals now materialize domain-specific persistent records with their own tables, lifecycle states, and read snapshots.

### Dental
- dental_patients
- dental_cases
- dental_treatment_plans
- dental_case_documents
- dental_recalls

### Fitness
- fitness_members
- fitness_goal_profiles
- fitness_program_recommendations
- fitness_attendance_risk
- fitness_freezes

### Aesthetic
- aesthetic_patients
- aesthetic_treatment_plans
- aesthetic_session_packages
- aesthetic_aftercare_cycles
- aesthetic_consents

### Vet
- vet_guardians
- vet_pets
- vet_preventive_plans
- vet_vaccine_schedules
- vet_service_history

### Auto-service
- auto_service_vehicles
- auto_service_orders
- auto_service_inspections
- auto_service_maintenance_cycles
- auto_service_approvals

## Runtime behavior

On account creation:
- the engine bootstraps the vertical-specific aggregate records

On command execution:
- transactional commands update the shared account timeline, ledger, documents, and resources
- vertical-specific command handlers update niche tables with domain semantics

On reads:
- `GET /api/v1/vertical-transactions/accounts/{account_id}` now includes `domain_snapshot`
- `GET /api/v1/vertical-domains/accounts/{account_id}` returns the standalone hard-domain snapshot

## Test coverage

- `backend/tests/test_vertical_hard_domains.py`
- full backend suite remains green
