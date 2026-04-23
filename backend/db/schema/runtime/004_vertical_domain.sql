CREATE TABLE IF NOT EXISTS dental_patients (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    account_id TEXT NOT NULL UNIQUE,
    contact_id TEXT,
    full_name TEXT,
    patient_status TEXT NOT NULL DEFAULT 'prospect',
    chief_complaint TEXT,
    risk_flags_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS dental_cases (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    account_id TEXT NOT NULL UNIQUE,
    patient_id TEXT NOT NULL,
    case_status TEXT NOT NULL DEFAULT 'intake',
    triage_type TEXT,
    diagnosis_summary TEXT,
    phase_count INTEGER NOT NULL DEFAULT 0,
    accepted_phase_count INTEGER NOT NULL DEFAULT 0,
    next_recall_due_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS dental_treatment_plans (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    case_id TEXT NOT NULL,
    plan_name TEXT NOT NULL,
    plan_status TEXT NOT NULL DEFAULT 'draft',
    total_amount REAL NOT NULL DEFAULT 0,
    phases_json TEXT NOT NULL DEFAULT '[]',
    financing_allowed INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(account_id, plan_name)
);
CREATE TABLE IF NOT EXISTS dental_case_documents (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    case_id TEXT NOT NULL,
    document_name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    document_kind TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(account_id, document_name)
);
CREATE TABLE IF NOT EXISTS dental_recalls (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    account_id TEXT NOT NULL UNIQUE,
    case_id TEXT NOT NULL,
    recall_type TEXT NOT NULL DEFAULT 'followup',
    status TEXT NOT NULL DEFAULT 'pending',
    due_at TEXT,
    last_completed_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS fitness_members (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    account_id TEXT NOT NULL UNIQUE,
    contact_id TEXT,
    member_status TEXT NOT NULL DEFAULT 'lead',
    suggested_program TEXT,
    coach_match TEXT,
    weekly_attendance_target INTEGER NOT NULL DEFAULT 3,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS fitness_goal_profiles (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    account_id TEXT NOT NULL UNIQUE,
    member_id TEXT NOT NULL,
    primary_goal TEXT NOT NULL DEFAULT 'recomposition',
    level_band TEXT NOT NULL DEFAULT 'beginner',
    preferred_modality TEXT,
    restrictions_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS fitness_program_recommendations (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    member_id TEXT NOT NULL,
    program_name TEXT NOT NULL,
    recommendation_status TEXT NOT NULL DEFAULT 'draft',
    sessions_per_week INTEGER NOT NULL DEFAULT 3,
    package_type TEXT,
    notes_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(account_id, program_name)
);
CREATE TABLE IF NOT EXISTS fitness_attendance_risk (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    account_id TEXT NOT NULL UNIQUE,
    member_id TEXT NOT NULL,
    attendance_last_7d INTEGER NOT NULL DEFAULT 0,
    attendance_last_30d INTEGER NOT NULL DEFAULT 0,
    risk_level TEXT NOT NULL DEFAULT 'low',
    churn_signals_json TEXT NOT NULL DEFAULT '[]',
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS fitness_freezes (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    member_id TEXT NOT NULL,
    freeze_status TEXT NOT NULL DEFAULT 'active',
    reason TEXT,
    start_at TEXT,
    end_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS auto_service_vehicles (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    account_id TEXT NOT NULL UNIQUE,
    contact_id TEXT,
    vin TEXT,
    plate TEXT,
    make_model TEXT,
    vehicle_year INTEGER,
    odometer_km INTEGER NOT NULL DEFAULT 0,
    vehicle_status TEXT NOT NULL DEFAULT 'intake',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS auto_service_orders (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    account_id TEXT NOT NULL UNIQUE,
    vehicle_id TEXT NOT NULL,
    order_status TEXT NOT NULL DEFAULT 'diagnostic',
    service_reason TEXT,
    quoted_amount REAL NOT NULL DEFAULT 0,
    approved_amount REAL NOT NULL DEFAULT 0,
    promised_delivery_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS auto_service_inspections (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    order_id TEXT NOT NULL,
    inspection_status TEXT NOT NULL DEFAULT 'open',
    findings_json TEXT NOT NULL DEFAULT '[]',
    diagnostic_summary TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(account_id, order_id)
);
CREATE TABLE IF NOT EXISTS auto_service_maintenance_cycles (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    account_id TEXT NOT NULL UNIQUE,
    vehicle_id TEXT NOT NULL,
    cycle_status TEXT NOT NULL DEFAULT 'pending',
    next_service_at TEXT,
    trigger_kind TEXT,
    trigger_value TEXT,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS auto_service_approvals (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    order_id TEXT NOT NULL,
    approval_status TEXT NOT NULL DEFAULT 'pending',
    approved_by TEXT,
    amount REAL NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(account_id, order_id, approval_status)
);

CREATE TABLE IF NOT EXISTS vet_guardians (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    account_id TEXT NOT NULL UNIQUE,
    contact_id TEXT,
    guardian_name TEXT,
    household_size INTEGER NOT NULL DEFAULT 1,
    preferred_channel TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS vet_pets (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    account_id TEXT NOT NULL UNIQUE,
    guardian_id TEXT NOT NULL,
    pet_name TEXT NOT NULL DEFAULT 'Mascota',
    species TEXT NOT NULL DEFAULT 'canine',
    breed TEXT,
    age_months INTEGER NOT NULL DEFAULT 12,
    weight_kg REAL NOT NULL DEFAULT 10,
    pet_status TEXT NOT NULL DEFAULT 'registered',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS vet_preventive_plans (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    account_id TEXT NOT NULL UNIQUE,
    pet_id TEXT NOT NULL,
    plan_status TEXT NOT NULL DEFAULT 'draft',
    plan_name TEXT NOT NULL DEFAULT 'preventive-care',
    next_review_at TEXT,
    grooming_frequency_days INTEGER,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS vet_vaccine_schedules (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    pet_id TEXT NOT NULL,
    vaccine_name TEXT NOT NULL,
    schedule_status TEXT NOT NULL DEFAULT 'pending',
    due_at TEXT,
    completed_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(account_id, vaccine_name)
);
CREATE TABLE IF NOT EXISTS vet_service_history (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    pet_id TEXT NOT NULL,
    service_type TEXT NOT NULL,
    service_status TEXT NOT NULL DEFAULT 'completed',
    performed_at TEXT,
    notes_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    UNIQUE(account_id, service_type, performed_at)
);

CREATE TABLE IF NOT EXISTS aesthetic_patients (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    account_id TEXT NOT NULL UNIQUE,
    contact_id TEXT,
    patient_status TEXT NOT NULL DEFAULT 'lead',
    primary_goal TEXT,
    eligibility_status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS aesthetic_treatment_plans (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    account_id TEXT NOT NULL UNIQUE,
    patient_id TEXT NOT NULL,
    treatment_name TEXT NOT NULL,
    plan_status TEXT NOT NULL DEFAULT 'draft',
    contraindications_json TEXT NOT NULL DEFAULT '[]',
    maintenance_interval_days INTEGER,
    total_amount REAL NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS aesthetic_session_packages (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    account_id TEXT NOT NULL UNIQUE,
    patient_id TEXT NOT NULL,
    package_status TEXT NOT NULL DEFAULT 'proposed',
    session_count INTEGER NOT NULL DEFAULT 1,
    sessions_completed INTEGER NOT NULL DEFAULT 0,
    total_amount REAL NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS aesthetic_aftercare_cycles (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    account_id TEXT NOT NULL UNIQUE,
    patient_id TEXT NOT NULL,
    cycle_status TEXT NOT NULL DEFAULT 'pending',
    aftercare_notes_json TEXT NOT NULL DEFAULT '[]',
    next_maintenance_at TEXT,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS aesthetic_consents (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    patient_id TEXT NOT NULL,
    consent_name TEXT NOT NULL,
    consent_status TEXT NOT NULL DEFAULT 'pending',
    signed_at TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(account_id, consent_name)
);
