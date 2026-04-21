import "server-only";
import { normalizeCollection } from "./contracts/shared";
import { normalizeVerticalProfile, type VerticalProfileContract } from "./contracts/verticals";

const RAW_FALLBACK_VERTICALS: unknown[] = [
  {
    "id": "fitness",
    "name": "WAOS Fitness",
    "short_name": "Fitness & entrenamiento",
    "description": "Sistema operativo conversacional para gimnasios, estudios y academias deportivas.",
    "problem": "Los negocios fitness pierden dinero porque demasiados leads preguntan pero no prueban, demasiadas pruebas no se convierten y demasiados alumnos se enfrían por falta de seguimiento, asistencia y reactivación.",
    "subverticals": [
      "gym tradicional",
      "gimnasio boutique",
      "entrenamiento funcional",
      "cross training",
      "spinning",
      "personal training",
      "boxeo",
      "MMA",
      "jiu-jitsu",
      "taekwondo",
      "pilates",
      "yoga",
      "running club",
      "academias deportivas"
    ],
    "objects": [
      "sede",
      "disciplina",
      "coach",
      "clase",
      "horario",
      "cupo",
      "nivel",
      "membresía",
      "pase",
      "paquete",
      "clase muestra",
      "evaluación inicial",
      "asistencia",
      "freeze",
      "reactivación",
      "programa premium",
      "alumno fitness",
      "objetivo del alumno",
      "nivel real",
      "programa sugerido",
      "coach matching"
    ],
    "flows": [
      "lead nuevo -> clase muestra",
      "prueba -> inscripción",
      "alumno nuevo -> asistencia",
      "asistencia baja -> reactivación",
      "membresía -> renovación"
    ],
    "kpis": [
      "lead a prueba",
      "prueba a membresía",
      "asistencia 30 días",
      "churn temprano",
      "reactivación",
      "ocupación por coach/sede",
      "trial to signup",
      "asistencia por franja",
      "churn por coach",
      "freeze rate"
    ],
    "recommended_integrations": [
      "whatsapp",
      "google_calendar",
      "payments",
      "crm",
      "promotions",
      "insights"
    ],
    "default_services": [
      "clase muestra",
      "evaluacion inicial",
      "membresia mensual",
      "personal training",
      "nutricion"
    ],
    "default_faqs": [
      {
        "q": "¿Que plan me conviene?",
        "a": "Te guiamos segun tu objetivo, nivel y frecuencia ideal."
      },
      {
        "q": "¿Tienen horarios y sedes?",
        "a": "Si, podemos compartir horarios, sedes y coaches disponibles."
      },
      {
        "q": "¿Puedo agendar una clase muestra?",
        "a": "Si, el bot puede proponerte horario y dejar apartada tu clase muestra."
      },
      {
        "q": "¿Manejan congelamiento o renovacion?",
        "a": "Si, podemos explicarte condiciones de freeze, renovacion y asistencia."
      }
    ],
    "behavior": {
      "tone": "enfocado y motivador",
      "response_length": "media",
      "use_emojis": false,
      "sales_intensity": "alta",
      "offer_promotions_when": "after_goal_detected",
      "escalate_when": [
        "lesion",
        "reclamo",
        "cambio de coach",
        "tema medico"
      ],
      "insistence_policy": "respectful",
      "can_share_price_directly": true,
      "can_negotiate": false,
      "can_mention_stock": false,
      "auto_send_images": true,
      "bot_mode": "captacion_y_reactivacion",
      "active_channels": [
        "whatsapp",
        "webchat",
        "instagram_dm"
      ],
      "forbidden_topics": [
        "diagnosticos medicos",
        "promesas fisicas garantizadas"
      ],
      "required_phrases": [
        "te recomiendo el plan segun tu objetivo",
        "puedo ayudarte a agendar tu clase muestra",
        "te sigo",
        "si la pregunta viene rara, igual te la aterrizo",
        "te lo aterrizo a tu caso"
      ],
      "fallback_message": "Te ayudo a elegir plan, ver horarios o apartar clase muestra. ¿Que objetivo tienes hoy? Si la pregunta viene rara, en broma o medio fuera de tema, igual te sigo y la aterrizamos al negocio.",
      "humor_policy": "light_contextual",
      "strange_question_policy": "respond_validate_reframe_sell_move"
    },
    "followup_rules": [
      {
        "type": "no_response",
        "delay_minutes": 90,
        "max_attempts": 2,
        "message_template": "Solo dando seguimiento. ¿Quieres que te recomiende plan u horario segun tu objetivo?"
      },
      {
        "type": "post_quote",
        "delay_minutes": 720,
        "max_attempts": 2,
        "message_template": "¿Quieres que te reserve tu clase muestra o te comparta el plan que mejor encaja contigo?"
      },
      {
        "type": "reactivation",
        "delay_minutes": 10080,
        "max_attempts": 2,
        "message_template": "Te extrañamos. Si quieres retomar, te ayudo con horario, coach o plan de regreso."
      }
    ],
    "templates": [
      {
        "template_key": "lead_capture",
        "title": "Captacion fitness",
        "content": "¡Hola! Soy {{bot_name}} de {{business_name}}. Te ayudo a encontrar el mejor plan segun tu objetivo, nivel y horario ideal.",
        "variables": [
          "bot_name",
          "business_name"
        ]
      },
      {
        "template_key": "class_reminder",
        "title": "Recordatorio de clase",
        "content": "Te recuerdo tu clase de {{service_name}} el {{date}} a las {{time}}. Si necesitas moverla, te ayudo.",
        "variables": [
          "service_name",
          "date",
          "time"
        ]
      },
      {
        "template_key": "post_trial_followup",
        "title": "Seguimiento post trial",
        "content": "¿Como te sentiste en tu clase muestra? Si quieres, hoy mismo te recomiendo el plan ideal y te ayudo a inscribirte.",
        "variables": []
      },
      {
        "template_key": "absence_recovery",
        "title": "Recuperacion de ausencia",
        "content": "Notamos que no pudiste venir. ¿Quieres que te proponga nuevo horario para no perder ritmo?",
        "variables": []
      },
      {
        "template_key": "reactivation_offer",
        "title": "Reactivacion",
        "content": "Tenemos opciones para que regreses con buen ritmo. ¿Prefieres horario matutino, vespertino o fin de semana?",
        "variables": []
      }
    ],
    "config_overrides": {
      "objective_secondary": [
        "agendar",
        "reactivar",
        "upsell"
      ],
      "policies": [
        "No prometer resultados fisicos garantizados",
        "Escalar lesiones o temas medicos a humano"
      ],
      "can_say": [
        "planes",
        "horarios",
        "sedes",
        "coaches",
        "promociones",
        "agendar"
      ],
      "cannot_say": [
        "diagnosticos medicos",
        "rutinas clinicas",
        "promesas de transformacion"
      ],
      "whatsapp_flows": [
        "clase_muestra",
        "recomendacion_plan",
        "reactivacion_alumno",
        "renovacion_membresia"
      ],
      "appointment_duration_minutes": 45,
      "handoff_keywords": [
        "lesion",
        "molestia",
        "reclamo",
        "cancelacion"
      ],
      "high_score_threshold": 75
    },
    "portfolio_tier": "tier_1",
    "master_thesis": "Sistema operativo conversacional para gimnasios, estudios y academias deportivas que convierte captación, prueba, inscripción, asistencia y retención en un flujo operable desde WhatsApp.",
    "buyer": {
      "primary": "Dueño de gimnasio o director comercial/operativo",
      "secondary": [
        "gerente de sede",
        "coordinador de coaches",
        "equipo de ventas"
      ]
    },
    "one_pager": {
      "headline": "WAOS Fitness",
      "thesis": "WhatsApp deja de ser un inbox de horarios y se convierte en un sistema de captación, inscripción, asistencia, retención y reactivación.",
      "problem": "Mucho volumen conversacional, poca prueba agendada, mala asistencia inicial y poca reactivación estructurada.",
      "promise": "Cada conversación termina en una acción clara: clase muestra, evaluación, inscripción, renovación o retorno.",
      "monetizes": [
        "inscripción",
        "primer mes",
        "paquetes",
        "membresías",
        "personal training",
        "nutrición",
        "upgrades"
      ],
      "packaging": [
        "setup vertical fitness",
        "playbooks por disciplina",
        "agenda + pagos + reactivación",
        "operación mensual gestionada"
      ],
      "strategic_care": "Gran vertical madre para WAOS por volumen, recurrencia, agenda y pagos; conviene venderla como sistema de asistencia y revenue, no solo de respuestas."
    },
    "demo_flow": [
      "El lead entra preguntando por costo, horario, sede o promoción.",
      "WAOS detecta objetivo, nivel, disponibilidad y disciplina de interés.",
      "Recomienda plan, sede, coach y clase muestra o evaluación.",
      "Agenda, confirma y manda recordatorios previos.",
      "Después de la prueba, cierra inscripción o activa recuperación de no-show.",
      "Tras el alta, monitorea asistencia temprana y dispara reactivación si baja la frecuencia."
    ],
    "native_objects": {
      "core": [
        "lead",
        "alumno",
        "sede",
        "disciplina",
        "coach",
        "clase",
        "horario",
        "nivel",
        "alumno fitness"
      ],
      "commercial": [
        "clase muestra",
        "evaluación",
        "membresía",
        "pase",
        "paquete",
        "promoción",
        "upgrade"
      ],
      "operations": [
        "cupo",
        "asistencia",
        "freeze",
        "renovación",
        "reactivación"
      ]
    },
    "pipeline": {
      "primary": {
        "name": "Captación e inscripción",
        "states": [
          "lead nuevo",
          "lead calificado",
          "prueba ofrecida",
          "prueba agendada",
          "prueba confirmada",
          "prueba asistida",
          "oferta enviada",
          "inscripción pendiente",
          "inscrito",
          "perdido"
        ]
      },
      "secondary": [
        {
          "name": "Retención",
          "states": [
            "alumno nuevo",
            "alumno activo",
            "asistencia baja",
            "riesgo de abandono",
            "freeze",
            "en reactivación",
            "reactivado",
            "cancelado"
          ]
        }
      ]
    },
    "bot_playbook": {
      "must_do": [
        "responder horarios, sedes y costos",
        "recomendar disciplina",
        "agendar prueba o evaluación",
        "cobrar inscripción cuando aplique",
        "recordar asistencia",
        "reactivar abandono",
        "vender upsells",
        "nunca quedarse seco ante bromas, preguntas raras o cambios bruscos de tema",
        "usar humor ligero cuando sume, sin sonar payaso ni poco serio",
        "validar el momento y luego reencauzar la conversacion al negocio",
        "cerrar siempre con una pregunta util o siguiente paso"
      ],
      "must_ask": [
        "objetivo",
        "experiencia previa",
        "horario preferido",
        "sede",
        "disciplina de interés",
        "si busca prueba o inscripción directa",
        "que parte del negocio se esta atorando mas",
        "si quiere que se lo aterrice a su caso"
      ],
      "objections": [
        "precio",
        "no sé cuál me conviene",
        "no tengo tiempo",
        "me queda lejos",
        "quiero ver si me gusta"
      ],
      "escalate_when": [
        "lesión",
        "tema médico",
        "reclamo",
        "negociación especial",
        "paquete corporativo"
      ],
      "forbidden": [
        "diagnósticos médicos",
        "promesas físicas garantizadas"
      ],
      "success_signals": [
        "quiero clase muestra",
        "mándame horarios",
        "quiero empezar",
        "¿cómo pago?",
        "me interesa ese plan"
      ],
      "style": [
        "humor ligero",
        "manejo de preguntas raras",
        "reencuadre comercial"
      ]
    },
    "automation_sequences": [
      {
        "key": "fitness_lead_welcome",
        "name": "Bienvenida a lead nuevo",
        "trigger": "entra lead nuevo",
        "goal": "calificar y proponer clase muestra",
        "steps": [
          "saludo + objetivo",
          "detectar horario y sede",
          "proponer prueba o evaluación"
        ]
      },
      {
        "key": "fitness_trial_followup",
        "name": "Seguimiento post prueba",
        "trigger": "prueba asistida",
        "goal": "cerrar membresía",
        "steps": [
          "pedir feedback",
          "recomendar plan",
          "enviar cierre y pago"
        ]
      },
      {
        "key": "fitness_no_show",
        "name": "Recuperación de no-show",
        "trigger": "prueba no asistida",
        "goal": "reagendar rápido",
        "steps": [
          "recordar valor de prueba",
          "ofrecer nuevo horario",
          "cerrar nueva fecha"
        ]
      },
      {
        "key": "fitness_reactivation",
        "name": "Reactivación por baja asistencia",
        "trigger": "7/14/30 días sin asistir",
        "goal": "recuperar hábito y plan activo",
        "steps": [
          "detectar fricción",
          "proponer horario/coaches",
          "ofrecer plan de retorno"
        ]
      }
    ],
    "dashboard": {
      "north_star": "Conversión de prueba a membresía con asistencia saludable en los primeros 30 días.",
      "sections": [
        {
          "name": "Adquisición",
          "metrics": [
            "leads nuevos",
            "tiempo de primera respuesta",
            "lead a prueba",
            "prueba agendada"
          ]
        },
        {
          "name": "Conversión",
          "metrics": [
            "prueba asistida",
            "prueba a membresía",
            "inscripción por coach/sede/disciplina",
            "primer pago cobrado"
          ]
        },
        {
          "name": "Retención",
          "metrics": [
            "asistencia 30 días",
            "churn temprano",
            "freeze",
            "reactivación"
          ]
        },
        {
          "name": "Revenue",
          "metrics": [
            "ingreso por nuevas altas",
            "renovaciones",
            "upsells",
            "ARPU por miembro"
          ]
        }
      ]
    },
    "hardening_model": {
      "goal": "Pasar de preset inteligente a sistema especialista",
      "wave": "ola_1",
      "entity_queen": "alumno fitness",
      "core_common": true,
      "domain_by_vertical": true,
      "playbooks_by_subvertical": true,
      "kpis_by_vertical": true,
      "pricing_by_vertical": true,
      "journeys_by_vertical": true,
      "reusable_modules": [
        "intake / calificación",
        "agenda / recursos",
        "cotización / propuesta",
        "pago / anticipo / membresía",
        "seguimiento / recurrencia",
        "reporting vertical"
      ],
      "minimum_viable_hardening": [
        "1 entidad reina",
        "1 pipeline propio",
        "1 cotización propia",
        "1 recurrencia propia",
        "1 dashboard propio"
      ],
      "hard_checklist": [
        "tiene entidad principal propia",
        "tiene pipeline específico",
        "tiene cotización o pricing del nicho",
        "tiene agenda o recursos del nicho",
        "tiene postventa o recurrencia del nicho",
        "tiene documentos o compliance del nicho",
        "tiene KPIs del nicho",
        "tiene 3 automatizaciones que mueven dinero",
        "tiene 2 pruebas e2e de negocio",
        "tiene subplaybooks por subvertical",
        "entidad principal propia",
        "pipeline específico",
        "pricing del nicho",
        "agenda y recursos del nicho",
        "postventa o recurrencia del nicho",
        "documentos o compliance del nicho",
        "KPIs del nicho",
        "3 automatizaciones que mueven dinero",
        "2 pruebas e2e de negocio",
        "subplaybooks por subvertical",
        "runtime ejecutable por vertical"
      ]
    },
    "specialist_layers": {
      "persistent_entities": [
        "alumno fitness",
        "objetivo del alumno",
        "nivel real",
        "programa sugerido",
        "clase muestra",
        "freeze",
        "reactivación",
        "coach matching"
      ],
      "business_pipeline": {
        "primary_entity": "alumno fitness",
        "primary_pipeline": {
          "name": "Captación e inscripción",
          "states": [
            "lead nuevo",
            "lead calificado",
            "prueba ofrecida",
            "prueba agendada",
            "prueba confirmada",
            "prueba asistida",
            "oferta enviada",
            "inscripción pendiente",
            "inscrito",
            "perdido"
          ]
        },
        "secondary_pipelines": [
          {
            "name": "Retención",
            "states": [
              "alumno nuevo",
              "alumno activo",
              "asistencia baja",
              "riesgo de abandono",
              "freeze",
              "en reactivación",
              "reactivado",
              "cancelado"
            ]
          }
        ]
      },
      "pricing_and_quotes": [
        "cotización por plan según objetivo y frecuencia",
        "upgrade sugerido por patrón de uso",
        "freeze con política estructurada"
      ],
      "agenda_and_resources": [
        "coach",
        "sede",
        "salón",
        "franja horaria",
        "cupo por clase"
      ],
      "post_sale_and_recurrence": [
        "renovación por patrón de asistencia",
        "alerta de churn por baja asistencia + no respuesta + vencimiento",
        "reactivación por pausa o freeze"
      ],
      "documents_compliance": [
        "waiver de salud",
        "onboarding inicial",
        "reglas de freeze",
        "autorización de cargos recurrentes"
      ],
      "kpis_that_matter": [
        "lead a prueba",
        "prueba a membresía",
        "asistencia 30 días",
        "churn temprano",
        "reactivación",
        "ocupación por coach/sede",
        "trial to signup",
        "asistencia por franja",
        "churn por coach",
        "freeze rate"
      ],
      "money_automations": [
        "seguimiento post trial con cierre de plan",
        "renovación inteligente por uso",
        "winback por churn temprano"
      ]
    },
    "domain_contract": {
      "vertical_entity_types": [
        "alumno fitness",
        "objetivo del alumno",
        "nivel real",
        "programa sugerido",
        "clase muestra",
        "freeze",
        "reactivación",
        "coach matching"
      ],
      "vertical_pipeline_stages": {
        "primary": [
          "lead nuevo",
          "lead calificado",
          "prueba ofrecida",
          "prueba agendada",
          "prueba confirmada",
          "prueba asistida",
          "oferta enviada",
          "inscripción pendiente",
          "inscrito",
          "perdido"
        ],
        "secondary": [
          [
            "alumno nuevo",
            "alumno activo",
            "asistencia baja",
            "riesgo de abandono",
            "freeze",
            "en reactivación",
            "reactivado",
            "cancelado"
          ]
        ]
      },
      "vertical_quote_types": [
        "membresía",
        "paquete de clases",
        "personal training",
        "nutrición",
        "upgrade premium"
      ],
      "vertical_resource_types": [
        "coach",
        "sede",
        "salón",
        "franja horaria",
        "cupo por clase"
      ],
      "vertical_followup_policies": [
        "renovación por patrón de asistencia",
        "alerta de churn por baja asistencia + no respuesta + vencimiento",
        "reactivación por pausa o freeze"
      ],
      "vertical_kpi_definitions": [
        "lead a prueba",
        "prueba a membresía",
        "asistencia 30 días",
        "churn temprano",
        "reactivación",
        "ocupación por coach/sede",
        "trial to signup",
        "asistencia por franja",
        "churn por coach",
        "freeze rate"
      ],
      "vertical_playbooks": [
        "boxeo",
        "yoga",
        "pilates",
        "cross training",
        "personal training"
      ],
      "vertical_document_types": [
        "waiver de salud",
        "onboarding inicial",
        "reglas de freeze",
        "autorización de cargos recurrentes"
      ]
    },
    "subvertical_playbooks": [
      {
        "name": "boxeo",
        "focus": "Playbook operativo y comercial para boxeo"
      },
      {
        "name": "yoga",
        "focus": "Playbook operativo y comercial para yoga"
      },
      {
        "name": "pilates",
        "focus": "Playbook operativo y comercial para pilates"
      },
      {
        "name": "cross training",
        "focus": "Playbook operativo y comercial para cross training"
      },
      {
        "name": "personal training",
        "focus": "Playbook operativo y comercial para personal training"
      }
    ],
    "business_e2e_tests": [
      {
        "name": "lead de boxeo agenda trial, asiste y compra membresía",
        "status": "designed"
      },
      {
        "name": "alumno con baja asistencia entra en riesgo, recibe winback y renueva",
        "status": "designed"
      }
    ],
    "vertical_runtime": {
      "pipeline_machine": {
        "primary_pipeline": "Captación e inscripción",
        "entity": "alumno",
        "states": [
          "lead nuevo",
          "lead calificado",
          "prueba ofrecida",
          "prueba agendada",
          "prueba confirmada",
          "prueba asistida",
          "oferta enviada",
          "inscripción pendiente",
          "inscrito",
          "perdido"
        ],
        "transitions": [
          {
            "from": "lead nuevo",
            "to": "lead calificado",
            "trigger": "qualification_complete",
            "business_effect": "advance opportunity"
          },
          {
            "from": "lead calificado",
            "to": "prueba ofrecida",
            "trigger": "trial_attended",
            "business_effect": "open commercial step"
          },
          {
            "from": "inscrito",
            "to": "perdido",
            "trigger": "successful_outcome",
            "business_effect": "realize revenue or continuity"
          },
          {
            "from": "inscrito",
            "to": "at_risk",
            "trigger": "low_attendance",
            "business_effect": "activate retention sequence"
          }
        ],
        "at_risk_state": "at_risk",
        "closed_states": [
          "perdido"
        ]
      },
      "pricing_engine": {
        "quote_types": [
          "membresia mensual",
          "membresia trimestral",
          "paquete personal training",
          "upgrade nutricion"
        ],
        "pricing_basis": "plan_type + frequency + branch + extras",
        "rules": [
          {
            "rule": "base price by programa type",
            "effect": "set base_price"
          },
          {
            "rule": "premium or urgent add-ons increase quote",
            "effect": "add surcharge"
          },
          {
            "rule": "bundle, membership or financing can lower immediate friction",
            "effect": "recommend package or installments"
          }
        ],
        "deposit_policy": "request advance when capacity, specialist time or inventory must be secured"
      },
      "resource_capacity": {
        "resource_types": [
          "coach",
          "salon",
          "cupo de clase",
          "franja horaria",
          "sede"
        ],
        "capacity_basis": "coach, class_capacity, room, branch and session duration",
        "constraints": [
          "avoid double booking of critical resources",
          "respect service duration and cleanup/buffer time",
          "prioritize higher urgency and higher close probability cases"
        ],
        "priority_queue": "coach matching y cupos"
      },
      "recurrence_engine": {
        "policies": [
          {
            "type": "attendance_review",
            "interval_days": 7,
            "anchor": "alumno"
          },
          {
            "type": "renewal_check",
            "interval_days": 30,
            "anchor": "alumno"
          },
          {
            "type": "reactivation_window",
            "interval_days": 21,
            "anchor": "alumno"
          }
        ],
        "reactivation_window_days": 30,
        "goal": "protect retention, repeat revenue and continuity"
      },
      "kpi_engine": {
        "north_star": "Conversión de prueba a membresía con asistencia saludable en los primeros 30 días.",
        "definitions": [
          {
            "name": "trial_to_signup",
            "formula": "trial_attended / trial_booked"
          },
          {
            "name": "churn_risk",
            "formula": "low_attendance AND no_response_7d"
          },
          {
            "name": "coach_utilization",
            "formula": "occupied_slots / available_slots"
          }
        ],
        "leading_indicators": [
          "low_attendance",
          "plan_expiring",
          "no_response_7d"
        ]
      },
      "automation_engine": {
        "money_automation_policies": [
          {
            "trigger": "low_attendance",
            "actions": [
              "send_followup",
              "escalate_owner",
              "offer_relevant_next_step"
            ],
            "goal": "save conversion or retention"
          },
          {
            "trigger": "plan_expiring",
            "actions": [
              "send_quote_or_payment_link",
              "remind_deadline",
              "notify_human"
            ],
            "goal": "move revenue forward"
          },
          {
            "trigger": "freeze_requested",
            "actions": [
              "schedule_recurrence",
              "cross_sell_next_best_offer",
              "create_task"
            ],
            "goal": "increase LTV"
          }
        ],
        "quiet_hours": "21:00-08:00"
      },
      "document_flow": {
        "required_documents": [
          "waiver inicial",
          "fitness assessment",
          "freeze request",
          "consentimiento basico"
        ],
        "lifecycle_rules": [
          {
            "document": "waiver inicial",
            "required_before": "first committed step",
            "signature_required": true
          },
          {
            "document": "consentimiento basico",
            "required_before": "handoff or continuity step",
            "signature_required": false
          }
        ]
      },
      "matching_engine": {
        "entity": "alumno",
        "rules": [
          "goal == coach.specialty",
          "level in coach.accepted_levels",
          "schedule_overlap",
          "branch_match"
        ],
        "next_best_match_outputs": [
          "best_owner",
          "best_resource_slot",
          "best_offer"
        ]
      }
    },
    "transactional_motor_v12": {
      "version": "v12_full_transactional",
      "aggregate_root": "fitness_member_journey",
      "main_business_entity": "programa sugerido",
      "transaction_unit": "attendance_cycle",
      "system_of_record": {
        "write_model": [
          "commands",
          "events",
          "ledger",
          "aggregate_snapshots"
        ],
        "read_models": [
          "commercial_board",
          "operations_board",
          "finance_board",
          "continuity_board",
          "resource_load_board",
          "document_readiness_board",
          "revenue_levers_board"
        ],
        "idempotency_scope": [
          "organization_id",
          "vertical_id",
          "external_reference",
          "command_key"
        ],
        "audit_mode": "append_only_with_snapshots"
      },
      "transaction_primitives": {
        "commands": [
          "capture_intent",
          "qualify_record",
          "create_quote",
          "request_deposit",
          "reserve_capacity",
          "confirm_booking",
          "start_case",
          "approve_quote",
          "collect_payment",
          "start_fulfillment",
          "close_fulfillment",
          "schedule_recurrence",
          "issue_refund",
          "reactivate_customer",
          "assign_program",
          "freeze_membership",
          "renew_membership",
          "offer_upsell"
        ],
        "events": [
          "intent_captured",
          "record_qualified",
          "quote_created",
          "deposit_requested",
          "capacity_reserved",
          "booking_confirmed",
          "case_started",
          "quote_approved",
          "payment_collected",
          "fulfillment_started",
          "fulfillment_closed",
          "recurrence_scheduled",
          "refund_issued",
          "customer_reactivated",
          "program_assigned",
          "membership_frozen",
          "membership_renewed",
          "upsell_accepted"
        ],
        "ledger_event_types": [
          "charge_opened",
          "deposit_collected",
          "installment_due",
          "payment_applied",
          "credit_issued",
          "refund_issued",
          "write_off_registered"
        ],
        "invariants": [
          "no activar membresia sin pago inicial",
          "no confirmar clase sin cupo",
          "no freeze sin motivo y fecha",
          "todo pago debe referenciar quote, order o case activo",
          "todo cambio crítico debe emitir evento y renglón de auditoría",
          "ningún recurso se confirma dos veces en la misma ventana"
        ],
        "idempotency_keys": [
          "command_key",
          "payment_reference",
          "booking_reference",
          "external_message_id"
        ]
      },
      "aggregates": {
        "primary_record": {
          "name": "programa sugerido",
          "status_axis": [
            "commercial",
            "operations",
            "finance",
            "continuity"
          ]
        },
        "quote": {
          "name": "membership_quote",
          "states": [
            "draft",
            "sent",
            "accepted",
            "expired",
            "lost"
          ]
        },
        "booking": {
          "name": "trial_booking",
          "states": [
            "proposed",
            "reserved",
            "confirmed",
            "attended_or_executed",
            "missed_or_canceled"
          ]
        },
        "execution": {
          "name": "membership_activation",
          "states": [
            "pending",
            "ready",
            "in_progress",
            "blocked",
            "completed",
            "closed"
          ]
        },
        "payment_account": {
          "name": "payment_account",
          "states": [
            "open",
            "partially_paid",
            "paid",
            "overdue",
            "refunded"
          ]
        },
        "continuity": {
          "name": "renewal_and_reactivation_plan",
          "states": [
            "not_started",
            "active",
            "at_risk",
            "recovered",
            "closed"
          ]
        }
      },
      "orchestration": {
        "command_handlers": [
          "handle_capture_intent",
          "handle_qualify_record",
          "handle_create_quote",
          "handle_request_deposit",
          "handle_reserve_capacity",
          "handle_confirm_booking",
          "handle_start_case",
          "handle_approve_quote",
          "handle_assign_program",
          "handle_freeze_membership",
          "handle_renew_membership",
          "handle_offer_upsell"
        ],
        "sagas": [
          "trial_to_signup",
          "attendance_drop_recovery",
          "freeze_to_reactivation"
        ],
        "money_guards": [
          "quote_before_payment",
          "capacity_before_confirmation",
          "documents_before_execution",
          "balance_before_close"
        ],
        "read_model_refresh": [
          "on_every_event",
          "nightly_reconciliation",
          "pre_dashboard_cache"
        ]
      },
      "finance": {
        "money_objects": [
          "inscription_fee",
          "membership_charge",
          "freeze_credit",
          "upgrade_charge"
        ],
        "collection_modes": [
          "mensualidad",
          "pago adelantado",
          "upgrade en chat"
        ],
        "refund_modes": [
          "freeze_credit",
          "class_compensation"
        ],
        "reconciliation_views": [
          "expected_vs_collected",
          "aging_balance",
          "refund_exposure",
          "cash_by_stage"
        ]
      },
      "operations": {
        "fulfillment_unit": "attendance_cycle",
        "resource_locking": [
          "coach",
          "class_spot",
          "studio_capacity"
        ],
        "dispatch_or_schedule_board": [
          "queued",
          "ready",
          "assigned",
          "in_progress",
          "blocked",
          "done"
        ],
        "handoff_rules": [
          "human_handoff_on_exception",
          "supervisor_handoff_on_money_risk",
          "operator_handoff_on_compliance_gap"
        ]
      },
      "audit_compliance": {
        "timeline_entities": [
          "programa sugerido",
          "membership_quote",
          "trial_booking",
          "membership_activation",
          "payment_account"
        ],
        "consent_gates": [
          "health_disclosure",
          "gym_rules_acceptance",
          "freeze_request"
        ],
        "required_evidence": [
          "timeline_event",
          "actor",
          "timestamp",
          "before_after_snapshot"
        ],
        "retention_rules": [
          "audit_log_append_only",
          "documents_linked_to_primary_record",
          "payment_trace_non_destructive"
        ]
      },
      "transaction_views": {
        "commercial": [
          "lead",
          "trial",
          "conversion"
        ],
        "operations": [
          "attendance",
          "coach_load",
          "freeze"
        ],
        "finance": [
          "mrr",
          "renewals",
          "arrears"
        ],
        "continuity": [
          "churn_risk",
          "reactivation",
          "upsell"
        ]
      },
      "command_catalog": [
        {
          "command": "capture_intent",
          "writes": "programa sugerido",
          "emits": "intent_captured",
          "guard": "no activar membresia sin pago inicial"
        },
        {
          "command": "qualify_record",
          "writes": "programa sugerido",
          "emits": "record_qualified",
          "guard": "no confirmar clase sin cupo"
        },
        {
          "command": "create_quote",
          "writes": "programa sugerido",
          "emits": "quote_created",
          "guard": "no freeze sin motivo y fecha"
        },
        {
          "command": "request_deposit",
          "writes": "programa sugerido",
          "emits": "deposit_requested",
          "guard": "no activar membresia sin pago inicial"
        },
        {
          "command": "reserve_capacity",
          "writes": "programa sugerido",
          "emits": "capacity_reserved",
          "guard": "no confirmar clase sin cupo"
        },
        {
          "command": "confirm_booking",
          "writes": "programa sugerido",
          "emits": "booking_confirmed",
          "guard": "no freeze sin motivo y fecha"
        },
        {
          "command": "start_case",
          "writes": "programa sugerido",
          "emits": "case_started",
          "guard": "no activar membresia sin pago inicial"
        },
        {
          "command": "approve_quote",
          "writes": "programa sugerido",
          "emits": "quote_approved",
          "guard": "no confirmar clase sin cupo"
        },
        {
          "command": "assign_program",
          "writes": "programa sugerido",
          "emits": "payment_collected",
          "guard": "no freeze sin motivo y fecha"
        },
        {
          "command": "freeze_membership",
          "writes": "programa sugerido",
          "emits": "fulfillment_started",
          "guard": "no activar membresia sin pago inicial"
        },
        {
          "command": "renew_membership",
          "writes": "programa sugerido",
          "emits": "fulfillment_closed",
          "guard": "no confirmar clase sin cupo"
        },
        {
          "command": "offer_upsell",
          "writes": "programa sugerido",
          "emits": "recurrence_scheduled",
          "guard": "no freeze sin motivo y fecha"
        }
      ],
      "event_catalog": [
        {
          "event": "intent_captured",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "trial_to_signup"
        },
        {
          "event": "record_qualified",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "attendance_drop_recovery"
        },
        {
          "event": "quote_created",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "freeze_to_reactivation"
        },
        {
          "event": "deposit_requested",
          "updates": [
            "timeline",
            "boards",
            "ledger"
          ],
          "next_action": "trial_to_signup"
        },
        {
          "event": "capacity_reserved",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "attendance_drop_recovery"
        },
        {
          "event": "booking_confirmed",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "freeze_to_reactivation"
        },
        {
          "event": "case_started",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "trial_to_signup"
        },
        {
          "event": "quote_approved",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "attendance_drop_recovery"
        },
        {
          "event": "program_assigned",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "freeze_to_reactivation"
        },
        {
          "event": "membership_frozen",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "trial_to_signup"
        },
        {
          "event": "membership_renewed",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "attendance_drop_recovery"
        },
        {
          "event": "upsell_accepted",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "freeze_to_reactivation"
        }
      ]
    },
    "is_strongest_vertical": true,
    "strongest_rank": 1,
    "ten_x_score": 100,
    "ten_x_narrative": "WAOS Fitness gana cuando controla captacion, trial, asistencia, freeze, renovacion y reactivacion desde WhatsApp.",
    "ten_x_growth_loops": [
      "trial a membresia",
      "ausencia a reactivacion",
      "renovacion a upgrade",
      "coach match a permanencia"
    ],
    "recommended_subverticals": [
      "gym tradicional",
      "gimnasio boutique",
      "entrenamiento funcional",
      "cross training"
    ],
    "subvertical_profiles": [
      {
        "id": "gym-tradicional",
        "name": "gym tradicional",
        "strength_score": 100,
        "promise": "Llenar pruebas, convertirlas en membresias y sostener asistencia semanal.",
        "growth_motion": "trial_conversion",
        "buyer": "Dueño de gimnasio o director comercial/operativo",
        "monetizes": [
          "inscripción",
          "primer mes",
          "paquetes",
          "membresías"
        ],
        "service_bundle": [
          "clase muestra",
          "evaluacion inicial",
          "membresia mensual",
          "freeze controlado"
        ],
        "qualification_questions": [
          "cual es tu objetivo principal",
          "en que horario puedes venir",
          "has entrenado antes",
          "quieres clase muestra o plan directo"
        ],
        "objections": [
          "precio",
          "me da pena empezar",
          "no tengo horario",
          "ya he fallado antes"
        ],
        "automation_priorities": [
          "seguimiento gym tradicional",
          "recordatorios",
          "winback",
          "upsell"
        ],
        "kpi_pack": [
          "lead a prueba",
          "prueba a membresía",
          "asistencia 30 días",
          "churn temprano",
          "conversion gym tradicional",
          "revenue gym tradicional"
        ],
        "recommended_commands": [
          "pausar reactivaciones",
          "abrir cupo extraordinario",
          "avisar clase de hoy",
          "solo humano en lesiones"
        ],
        "launch_assets": [
          "guion whatsapp",
          "playbook de handoff",
          "servicios seed",
          "templates seed"
        ],
        "templates": [
          {
            "key": "gym-tradicional-lead",
            "title": "Captacion gym tradicional",
            "content": "Hola, te ayudo con gym tradicional. Si quieres, te hago 3 preguntas y te propongo el siguiente paso ideal."
          },
          {
            "key": "gym-tradicional-followup",
            "title": "Seguimiento gym tradicional",
            "content": "Te sigo con gym tradicional. Si quieres, hoy mismo te propongo horario, paquete o siguiente accion."
          },
          {
            "key": "gym-tradicional-reactivation",
            "title": "Reactivacion gym tradicional",
            "content": "Te escribo porque todavia podemos mover gym tradicional a una accion concreta esta semana. ¿Quieres que te lo aterrice a tu caso?"
          }
        ],
        "behavior_overrides": {
          "tone": "enfocado y motivador",
          "sales_intensity": "alta",
          "required_phrases": [
            "te lo aterrizo a tu caso de gym tradicional",
            "te sigo para moverlo al siguiente paso"
          ],
          "fallback_message": "Te ayudo con gym tradicional. Si quieres, te hago unas preguntas rapidas y te recomiendo el siguiente paso."
        }
      },
      {
        "id": "gimnasio-boutique",
        "name": "gimnasio boutique",
        "strength_score": 98,
        "promise": "Convertir conversaciones de gimnasio boutique en siguiente paso claro, cobro y recurrencia.",
        "growth_motion": "capture_followup_close",
        "buyer": "Dueño de gimnasio o director comercial/operativo",
        "monetizes": [
          "inscripción",
          "primer mes",
          "paquetes",
          "membresías"
        ],
        "service_bundle": [
          "valoracion gimnasio boutique",
          "clase muestra gimnasio boutique",
          "paquete gimnasio boutique",
          "seguimiento de asistencia"
        ],
        "qualification_questions": [
          "cual es tu objetivo principal",
          "en que horario puedes venir",
          "has entrenado antes",
          "quieres clase muestra o plan directo"
        ],
        "objections": [
          "precio",
          "no sé cuál me conviene",
          "no tengo tiempo",
          "me queda lejos"
        ],
        "automation_priorities": [
          "seguimiento gimnasio boutique",
          "recordatorios",
          "winback",
          "upsell"
        ],
        "kpi_pack": [
          "lead a prueba",
          "prueba a membresía",
          "asistencia 30 días",
          "churn temprano",
          "conversion gimnasio boutique",
          "revenue gimnasio boutique"
        ],
        "recommended_commands": [
          "pausar reactivaciones",
          "abrir cupo extraordinario",
          "avisar clase de hoy",
          "solo humano en lesiones"
        ],
        "launch_assets": [
          "guion whatsapp",
          "playbook de handoff",
          "servicios seed",
          "templates seed"
        ],
        "templates": [
          {
            "key": "gimnasio-boutique-lead",
            "title": "Captacion gimnasio boutique",
            "content": "Hola, te ayudo con gimnasio boutique. Si quieres, te hago 3 preguntas y te propongo el siguiente paso ideal."
          },
          {
            "key": "gimnasio-boutique-followup",
            "title": "Seguimiento gimnasio boutique",
            "content": "Te sigo con gimnasio boutique. Si quieres, hoy mismo te propongo horario, paquete o siguiente accion."
          },
          {
            "key": "gimnasio-boutique-reactivation",
            "title": "Reactivacion gimnasio boutique",
            "content": "Te escribo porque todavia podemos mover gimnasio boutique a una accion concreta esta semana. ¿Quieres que te lo aterrice a tu caso?"
          }
        ],
        "behavior_overrides": {
          "tone": "enfocado y motivador",
          "sales_intensity": "alta",
          "required_phrases": [
            "te lo aterrizo a tu caso de gimnasio boutique",
            "te sigo para moverlo al siguiente paso"
          ],
          "fallback_message": "Te ayudo con gimnasio boutique. Si quieres, te hago unas preguntas rapidas y te recomiendo el siguiente paso."
        }
      },
      {
        "id": "entrenamiento-funcional",
        "name": "entrenamiento funcional",
        "strength_score": 96,
        "promise": "Convertir conversaciones de entrenamiento funcional en siguiente paso claro, cobro y recurrencia.",
        "growth_motion": "capture_followup_close",
        "buyer": "Dueño de gimnasio o director comercial/operativo",
        "monetizes": [
          "inscripción",
          "primer mes",
          "paquetes",
          "membresías"
        ],
        "service_bundle": [
          "valoracion entrenamiento funcional",
          "clase muestra entrenamiento funcional",
          "paquete entrenamiento funcional",
          "seguimiento de asistencia"
        ],
        "qualification_questions": [
          "cual es tu objetivo principal",
          "en que horario puedes venir",
          "has entrenado antes",
          "quieres clase muestra o plan directo"
        ],
        "objections": [
          "precio",
          "no sé cuál me conviene",
          "no tengo tiempo",
          "me queda lejos"
        ],
        "automation_priorities": [
          "seguimiento entrenamiento funcional",
          "recordatorios",
          "winback",
          "upsell"
        ],
        "kpi_pack": [
          "lead a prueba",
          "prueba a membresía",
          "asistencia 30 días",
          "churn temprano",
          "conversion entrenamiento funcional",
          "revenue entrenamiento funcional"
        ],
        "recommended_commands": [
          "pausar reactivaciones",
          "abrir cupo extraordinario",
          "avisar clase de hoy",
          "solo humano en lesiones"
        ],
        "launch_assets": [
          "guion whatsapp",
          "playbook de handoff",
          "servicios seed",
          "templates seed"
        ],
        "templates": [
          {
            "key": "entrenamiento-funcional-lead",
            "title": "Captacion entrenamiento funcional",
            "content": "Hola, te ayudo con entrenamiento funcional. Si quieres, te hago 3 preguntas y te propongo el siguiente paso ideal."
          },
          {
            "key": "entrenamiento-funcional-followup",
            "title": "Seguimiento entrenamiento funcional",
            "content": "Te sigo con entrenamiento funcional. Si quieres, hoy mismo te propongo horario, paquete o siguiente accion."
          },
          {
            "key": "entrenamiento-funcional-reactivation",
            "title": "Reactivacion entrenamiento funcional",
            "content": "Te escribo porque todavia podemos mover entrenamiento funcional a una accion concreta esta semana. ¿Quieres que te lo aterrice a tu caso?"
          }
        ],
        "behavior_overrides": {
          "tone": "enfocado y motivador",
          "sales_intensity": "alta",
          "required_phrases": [
            "te lo aterrizo a tu caso de entrenamiento funcional",
            "te sigo para moverlo al siguiente paso"
          ],
          "fallback_message": "Te ayudo con entrenamiento funcional. Si quieres, te hago unas preguntas rapidas y te recomiendo el siguiente paso."
        }
      },
      {
        "id": "cross-training",
        "name": "cross training",
        "strength_score": 94,
        "promise": "Convertir conversaciones de cross training en siguiente paso claro, cobro y recurrencia.",
        "growth_motion": "capture_followup_close",
        "buyer": "Dueño de gimnasio o director comercial/operativo",
        "monetizes": [
          "inscripción",
          "primer mes",
          "paquetes",
          "membresías"
        ],
        "service_bundle": [
          "valoracion cross training",
          "clase muestra cross training",
          "paquete cross training",
          "seguimiento de asistencia"
        ],
        "qualification_questions": [
          "cual es tu objetivo principal",
          "en que horario puedes venir",
          "has entrenado antes",
          "quieres clase muestra o plan directo"
        ],
        "objections": [
          "precio",
          "no sé cuál me conviene",
          "no tengo tiempo",
          "me queda lejos"
        ],
        "automation_priorities": [
          "seguimiento cross training",
          "recordatorios",
          "winback",
          "upsell"
        ],
        "kpi_pack": [
          "lead a prueba",
          "prueba a membresía",
          "asistencia 30 días",
          "churn temprano",
          "conversion cross training",
          "revenue cross training"
        ],
        "recommended_commands": [
          "pausar reactivaciones",
          "abrir cupo extraordinario",
          "avisar clase de hoy",
          "solo humano en lesiones"
        ],
        "launch_assets": [
          "guion whatsapp",
          "playbook de handoff",
          "servicios seed",
          "templates seed"
        ],
        "templates": [
          {
            "key": "cross-training-lead",
            "title": "Captacion cross training",
            "content": "Hola, te ayudo con cross training. Si quieres, te hago 3 preguntas y te propongo el siguiente paso ideal."
          },
          {
            "key": "cross-training-followup",
            "title": "Seguimiento cross training",
            "content": "Te sigo con cross training. Si quieres, hoy mismo te propongo horario, paquete o siguiente accion."
          },
          {
            "key": "cross-training-reactivation",
            "title": "Reactivacion cross training",
            "content": "Te escribo porque todavia podemos mover cross training a una accion concreta esta semana. ¿Quieres que te lo aterrice a tu caso?"
          }
        ],
        "behavior_overrides": {
          "tone": "enfocado y motivador",
          "sales_intensity": "alta",
          "required_phrases": [
            "te lo aterrizo a tu caso de cross training",
            "te sigo para moverlo al siguiente paso"
          ],
          "fallback_message": "Te ayudo con cross training. Si quieres, te hago unas preguntas rapidas y te recomiendo el siguiente paso."
        }
      },
      {
        "id": "spinning",
        "name": "spinning",
        "strength_score": 92,
        "promise": "Convertir conversaciones de spinning en siguiente paso claro, cobro y recurrencia.",
        "growth_motion": "capture_followup_close",
        "buyer": "Dueño de gimnasio o director comercial/operativo",
        "monetizes": [
          "inscripción",
          "primer mes",
          "paquetes",
          "membresías"
        ],
        "service_bundle": [
          "valoracion spinning",
          "clase muestra spinning",
          "paquete spinning",
          "seguimiento de asistencia"
        ],
        "qualification_questions": [
          "cual es tu objetivo principal",
          "en que horario puedes venir",
          "has entrenado antes",
          "quieres clase muestra o plan directo"
        ],
        "objections": [
          "precio",
          "no sé cuál me conviene",
          "no tengo tiempo",
          "me queda lejos"
        ],
        "automation_priorities": [
          "seguimiento spinning",
          "recordatorios",
          "winback",
          "upsell"
        ],
        "kpi_pack": [
          "lead a prueba",
          "prueba a membresía",
          "asistencia 30 días",
          "churn temprano",
          "conversion spinning",
          "revenue spinning"
        ],
        "recommended_commands": [
          "pausar reactivaciones",
          "abrir cupo extraordinario",
          "avisar clase de hoy",
          "solo humano en lesiones"
        ],
        "launch_assets": [
          "guion whatsapp",
          "playbook de handoff",
          "servicios seed",
          "templates seed"
        ],
        "templates": [
          {
            "key": "spinning-lead",
            "title": "Captacion spinning",
            "content": "Hola, te ayudo con spinning. Si quieres, te hago 3 preguntas y te propongo el siguiente paso ideal."
          },
          {
            "key": "spinning-followup",
            "title": "Seguimiento spinning",
            "content": "Te sigo con spinning. Si quieres, hoy mismo te propongo horario, paquete o siguiente accion."
          },
          {
            "key": "spinning-reactivation",
            "title": "Reactivacion spinning",
            "content": "Te escribo porque todavia podemos mover spinning a una accion concreta esta semana. ¿Quieres que te lo aterrice a tu caso?"
          }
        ],
        "behavior_overrides": {
          "tone": "enfocado y motivador",
          "sales_intensity": "alta",
          "required_phrases": [
            "te lo aterrizo a tu caso de spinning",
            "te sigo para moverlo al siguiente paso"
          ],
          "fallback_message": "Te ayudo con spinning. Si quieres, te hago unas preguntas rapidas y te recomiendo el siguiente paso."
        }
      },
      {
        "id": "personal-training",
        "name": "personal training",
        "strength_score": 90,
        "promise": "Vender evaluacion, plan y continuidad de sesiones con ticket alto.",
        "growth_motion": "high_ticket_package",
        "buyer": "Dueño de gimnasio o director comercial/operativo",
        "monetizes": [
          "inscripción",
          "primer mes",
          "paquetes",
          "membresías"
        ],
        "service_bundle": [
          "assessment",
          "plan inicial",
          "bloque 8 sesiones",
          "nutricion complementaria"
        ],
        "qualification_questions": [
          "cual es tu objetivo principal",
          "en que horario puedes venir",
          "has entrenado antes",
          "quieres clase muestra o plan directo"
        ],
        "objections": [
          "quiero pensarlo",
          "es caro",
          "no se si tendre constancia",
          "prefiero empezar despues"
        ],
        "automation_priorities": [
          "seguimiento personal training",
          "recordatorios",
          "winback",
          "upsell"
        ],
        "kpi_pack": [
          "lead a prueba",
          "prueba a membresía",
          "asistencia 30 días",
          "churn temprano",
          "conversion personal training",
          "revenue personal training"
        ],
        "recommended_commands": [
          "pausar reactivaciones",
          "abrir cupo extraordinario",
          "avisar clase de hoy",
          "solo humano en lesiones"
        ],
        "launch_assets": [
          "guion whatsapp",
          "playbook de handoff",
          "servicios seed",
          "templates seed"
        ],
        "templates": [
          {
            "key": "personal-training-lead",
            "title": "Captacion personal training",
            "content": "Hola, te ayudo con personal training. Si quieres, te hago 3 preguntas y te propongo el siguiente paso ideal."
          },
          {
            "key": "personal-training-followup",
            "title": "Seguimiento personal training",
            "content": "Te sigo con personal training. Si quieres, hoy mismo te propongo horario, paquete o siguiente accion."
          },
          {
            "key": "personal-training-reactivation",
            "title": "Reactivacion personal training",
            "content": "Te escribo porque todavia podemos mover personal training a una accion concreta esta semana. ¿Quieres que te lo aterrice a tu caso?"
          }
        ],
        "behavior_overrides": {
          "tone": "enfocado y motivador",
          "sales_intensity": "alta",
          "required_phrases": [
            "te lo aterrizo a tu caso de personal training",
            "te sigo para moverlo al siguiente paso"
          ],
          "fallback_message": "Te ayudo con personal training. Si quieres, te hago unas preguntas rapidas y te recomiendo el siguiente paso."
        }
      },
      {
        "id": "boxeo",
        "name": "boxeo",
        "strength_score": 88,
        "promise": "Convertir energia de primer contacto en prueba inmediata y permanencia por coach/horario.",
        "growth_motion": "show_up_and_upgrade",
        "buyer": "Dueño de gimnasio o director comercial/operativo",
        "monetizes": [
          "inscripción",
          "primer mes",
          "paquetes",
          "membresías"
        ],
        "service_bundle": [
          "clase de prueba",
          "inscripcion",
          "membresia combate",
          "personal boxing"
        ],
        "qualification_questions": [
          "cual es tu objetivo principal",
          "en que horario puedes venir",
          "has entrenado antes",
          "quieres clase muestra o plan directo"
        ],
        "objections": [
          "nunca he boxeado",
          "me da miedo lesionarme",
          "quiero bajar peso",
          "solo puedo noches"
        ],
        "automation_priorities": [
          "seguimiento boxeo",
          "recordatorios",
          "winback",
          "upsell"
        ],
        "kpi_pack": [
          "lead a prueba",
          "prueba a membresía",
          "asistencia 30 días",
          "churn temprano",
          "conversion boxeo",
          "revenue boxeo"
        ],
        "recommended_commands": [
          "pausar reactivaciones",
          "abrir cupo extraordinario",
          "avisar clase de hoy",
          "solo humano en lesiones"
        ],
        "launch_assets": [
          "guion whatsapp",
          "playbook de handoff",
          "servicios seed",
          "templates seed"
        ],
        "templates": [
          {
            "key": "boxeo-lead",
            "title": "Captacion boxeo",
            "content": "Hola, te ayudo con boxeo. Si quieres, te hago 3 preguntas y te propongo el siguiente paso ideal."
          },
          {
            "key": "boxeo-followup",
            "title": "Seguimiento boxeo",
            "content": "Te sigo con boxeo. Si quieres, hoy mismo te propongo horario, paquete o siguiente accion."
          },
          {
            "key": "boxeo-reactivation",
            "title": "Reactivacion boxeo",
            "content": "Te escribo porque todavia podemos mover boxeo a una accion concreta esta semana. ¿Quieres que te lo aterrice a tu caso?"
          }
        ],
        "behavior_overrides": {
          "tone": "enfocado y motivador",
          "sales_intensity": "alta",
          "required_phrases": [
            "te lo aterrizo a tu caso de boxeo",
            "te sigo para moverlo al siguiente paso"
          ],
          "fallback_message": "Te ayudo con boxeo. Si quieres, te hago unas preguntas rapidas y te recomiendo el siguiente paso."
        }
      },
      {
        "id": "mma",
        "name": "MMA",
        "strength_score": 86,
        "promise": "Convertir conversaciones de MMA en siguiente paso claro, cobro y recurrencia.",
        "growth_motion": "capture_followup_close",
        "buyer": "Dueño de gimnasio o director comercial/operativo",
        "monetizes": [
          "inscripción",
          "primer mes",
          "paquetes",
          "membresías"
        ],
        "service_bundle": [
          "valoracion MMA",
          "clase muestra MMA",
          "paquete MMA",
          "seguimiento de asistencia"
        ],
        "qualification_questions": [
          "cual es tu objetivo principal",
          "en que horario puedes venir",
          "has entrenado antes",
          "quieres clase muestra o plan directo"
        ],
        "objections": [
          "precio",
          "no sé cuál me conviene",
          "no tengo tiempo",
          "me queda lejos"
        ],
        "automation_priorities": [
          "seguimiento MMA",
          "recordatorios",
          "winback",
          "upsell"
        ],
        "kpi_pack": [
          "lead a prueba",
          "prueba a membresía",
          "asistencia 30 días",
          "churn temprano",
          "conversion MMA",
          "revenue MMA"
        ],
        "recommended_commands": [
          "pausar reactivaciones",
          "abrir cupo extraordinario",
          "avisar clase de hoy",
          "solo humano en lesiones"
        ],
        "launch_assets": [
          "guion whatsapp",
          "playbook de handoff",
          "servicios seed",
          "templates seed"
        ],
        "templates": [
          {
            "key": "mma-lead",
            "title": "Captacion MMA",
            "content": "Hola, te ayudo con MMA. Si quieres, te hago 3 preguntas y te propongo el siguiente paso ideal."
          },
          {
            "key": "mma-followup",
            "title": "Seguimiento MMA",
            "content": "Te sigo con MMA. Si quieres, hoy mismo te propongo horario, paquete o siguiente accion."
          },
          {
            "key": "mma-reactivation",
            "title": "Reactivacion MMA",
            "content": "Te escribo porque todavia podemos mover MMA a una accion concreta esta semana. ¿Quieres que te lo aterrice a tu caso?"
          }
        ],
        "behavior_overrides": {
          "tone": "enfocado y motivador",
          "sales_intensity": "alta",
          "required_phrases": [
            "te lo aterrizo a tu caso de MMA",
            "te sigo para moverlo al siguiente paso"
          ],
          "fallback_message": "Te ayudo con MMA. Si quieres, te hago unas preguntas rapidas y te recomiendo el siguiente paso."
        }
      },
      {
        "id": "jiu-jitsu",
        "name": "jiu-jitsu",
        "strength_score": 84,
        "promise": "Convertir conversaciones de jiu-jitsu en siguiente paso claro, cobro y recurrencia.",
        "growth_motion": "capture_followup_close",
        "buyer": "Dueño de gimnasio o director comercial/operativo",
        "monetizes": [
          "inscripción",
          "primer mes",
          "paquetes",
          "membresías"
        ],
        "service_bundle": [
          "valoracion jiu-jitsu",
          "clase muestra jiu-jitsu",
          "paquete jiu-jitsu",
          "seguimiento de asistencia"
        ],
        "qualification_questions": [
          "cual es tu objetivo principal",
          "en que horario puedes venir",
          "has entrenado antes",
          "quieres clase muestra o plan directo"
        ],
        "objections": [
          "precio",
          "no sé cuál me conviene",
          "no tengo tiempo",
          "me queda lejos"
        ],
        "automation_priorities": [
          "seguimiento jiu-jitsu",
          "recordatorios",
          "winback",
          "upsell"
        ],
        "kpi_pack": [
          "lead a prueba",
          "prueba a membresía",
          "asistencia 30 días",
          "churn temprano",
          "conversion jiu-jitsu",
          "revenue jiu-jitsu"
        ],
        "recommended_commands": [
          "pausar reactivaciones",
          "abrir cupo extraordinario",
          "avisar clase de hoy",
          "solo humano en lesiones"
        ],
        "launch_assets": [
          "guion whatsapp",
          "playbook de handoff",
          "servicios seed",
          "templates seed"
        ],
        "templates": [
          {
            "key": "jiu-jitsu-lead",
            "title": "Captacion jiu-jitsu",
            "content": "Hola, te ayudo con jiu-jitsu. Si quieres, te hago 3 preguntas y te propongo el siguiente paso ideal."
          },
          {
            "key": "jiu-jitsu-followup",
            "title": "Seguimiento jiu-jitsu",
            "content": "Te sigo con jiu-jitsu. Si quieres, hoy mismo te propongo horario, paquete o siguiente accion."
          },
          {
            "key": "jiu-jitsu-reactivation",
            "title": "Reactivacion jiu-jitsu",
            "content": "Te escribo porque todavia podemos mover jiu-jitsu a una accion concreta esta semana. ¿Quieres que te lo aterrice a tu caso?"
          }
        ],
        "behavior_overrides": {
          "tone": "enfocado y motivador",
          "sales_intensity": "alta",
          "required_phrases": [
            "te lo aterrizo a tu caso de jiu-jitsu",
            "te sigo para moverlo al siguiente paso"
          ],
          "fallback_message": "Te ayudo con jiu-jitsu. Si quieres, te hago unas preguntas rapidas y te recomiendo el siguiente paso."
        }
      },
      {
        "id": "taekwondo",
        "name": "taekwondo",
        "strength_score": 82,
        "promise": "Convertir conversaciones de taekwondo en siguiente paso claro, cobro y recurrencia.",
        "growth_motion": "capture_followup_close",
        "buyer": "Dueño de gimnasio o director comercial/operativo",
        "monetizes": [
          "inscripción",
          "primer mes",
          "paquetes",
          "membresías"
        ],
        "service_bundle": [
          "valoracion taekwondo",
          "clase muestra taekwondo",
          "paquete taekwondo",
          "seguimiento de asistencia"
        ],
        "qualification_questions": [
          "cual es tu objetivo principal",
          "en que horario puedes venir",
          "has entrenado antes",
          "quieres clase muestra o plan directo"
        ],
        "objections": [
          "precio",
          "no sé cuál me conviene",
          "no tengo tiempo",
          "me queda lejos"
        ],
        "automation_priorities": [
          "seguimiento taekwondo",
          "recordatorios",
          "winback",
          "upsell"
        ],
        "kpi_pack": [
          "lead a prueba",
          "prueba a membresía",
          "asistencia 30 días",
          "churn temprano",
          "conversion taekwondo",
          "revenue taekwondo"
        ],
        "recommended_commands": [
          "pausar reactivaciones",
          "abrir cupo extraordinario",
          "avisar clase de hoy",
          "solo humano en lesiones"
        ],
        "launch_assets": [
          "guion whatsapp",
          "playbook de handoff",
          "servicios seed",
          "templates seed"
        ],
        "templates": [
          {
            "key": "taekwondo-lead",
            "title": "Captacion taekwondo",
            "content": "Hola, te ayudo con taekwondo. Si quieres, te hago 3 preguntas y te propongo el siguiente paso ideal."
          },
          {
            "key": "taekwondo-followup",
            "title": "Seguimiento taekwondo",
            "content": "Te sigo con taekwondo. Si quieres, hoy mismo te propongo horario, paquete o siguiente accion."
          },
          {
            "key": "taekwondo-reactivation",
            "title": "Reactivacion taekwondo",
            "content": "Te escribo porque todavia podemos mover taekwondo a una accion concreta esta semana. ¿Quieres que te lo aterrice a tu caso?"
          }
        ],
        "behavior_overrides": {
          "tone": "enfocado y motivador",
          "sales_intensity": "alta",
          "required_phrases": [
            "te lo aterrizo a tu caso de taekwondo",
            "te sigo para moverlo al siguiente paso"
          ],
          "fallback_message": "Te ayudo con taekwondo. Si quieres, te hago unas preguntas rapidas y te recomiendo el siguiente paso."
        }
      },
      {
        "id": "pilates",
        "name": "pilates",
        "strength_score": 80,
        "promise": "Vender cupos premium y continuidad por bloques de sesiones.",
        "growth_motion": "package_retention",
        "buyer": "Dueño de gimnasio o director comercial/operativo",
        "monetizes": [
          "inscripción",
          "primer mes",
          "paquetes",
          "membresías"
        ],
        "service_bundle": [
          "clase muestra pilates",
          "paquete 4 sesiones",
          "paquete 8 sesiones",
          "seguimiento post clase"
        ],
        "qualification_questions": [
          "cual es tu objetivo principal",
          "en que horario puedes venir",
          "has entrenado antes",
          "quieres clase muestra o plan directo"
        ],
        "objections": [
          "es caro",
          "soy principiante",
          "no se si me sirva",
          "solo puedo ciertos horarios"
        ],
        "automation_priorities": [
          "seguimiento pilates",
          "recordatorios",
          "winback",
          "upsell"
        ],
        "kpi_pack": [
          "lead a prueba",
          "prueba a membresía",
          "asistencia 30 días",
          "churn temprano",
          "conversion pilates",
          "revenue pilates"
        ],
        "recommended_commands": [
          "pausar reactivaciones",
          "abrir cupo extraordinario",
          "avisar clase de hoy",
          "solo humano en lesiones"
        ],
        "launch_assets": [
          "guion whatsapp",
          "playbook de handoff",
          "servicios seed",
          "templates seed"
        ],
        "templates": [
          {
            "key": "pilates-lead",
            "title": "Captacion pilates",
            "content": "Hola, te ayudo con pilates. Si quieres, te hago 3 preguntas y te propongo el siguiente paso ideal."
          },
          {
            "key": "pilates-followup",
            "title": "Seguimiento pilates",
            "content": "Te sigo con pilates. Si quieres, hoy mismo te propongo horario, paquete o siguiente accion."
          },
          {
            "key": "pilates-reactivation",
            "title": "Reactivacion pilates",
            "content": "Te escribo porque todavia podemos mover pilates a una accion concreta esta semana. ¿Quieres que te lo aterrice a tu caso?"
          }
        ],
        "behavior_overrides": {
          "tone": "enfocado y motivador",
          "sales_intensity": "alta",
          "required_phrases": [
            "te lo aterrizo a tu caso de pilates",
            "te sigo para moverlo al siguiente paso"
          ],
          "fallback_message": "Te ayudo con pilates. Si quieres, te hago unas preguntas rapidas y te recomiendo el siguiente paso."
        }
      },
      {
        "id": "yoga",
        "name": "yoga",
        "strength_score": 78,
        "promise": "Convertir conversaciones de yoga en siguiente paso claro, cobro y recurrencia.",
        "growth_motion": "capture_followup_close",
        "buyer": "Dueño de gimnasio o director comercial/operativo",
        "monetizes": [
          "inscripción",
          "primer mes",
          "paquetes",
          "membresías"
        ],
        "service_bundle": [
          "valoracion yoga",
          "clase muestra yoga",
          "paquete yoga",
          "seguimiento de asistencia"
        ],
        "qualification_questions": [
          "cual es tu objetivo principal",
          "en que horario puedes venir",
          "has entrenado antes",
          "quieres clase muestra o plan directo"
        ],
        "objections": [
          "precio",
          "no sé cuál me conviene",
          "no tengo tiempo",
          "me queda lejos"
        ],
        "automation_priorities": [
          "seguimiento yoga",
          "recordatorios",
          "winback",
          "upsell"
        ],
        "kpi_pack": [
          "lead a prueba",
          "prueba a membresía",
          "asistencia 30 días",
          "churn temprano",
          "conversion yoga",
          "revenue yoga"
        ],
        "recommended_commands": [
          "pausar reactivaciones",
          "abrir cupo extraordinario",
          "avisar clase de hoy",
          "solo humano en lesiones"
        ],
        "launch_assets": [
          "guion whatsapp",
          "playbook de handoff",
          "servicios seed",
          "templates seed"
        ],
        "templates": [
          {
            "key": "yoga-lead",
            "title": "Captacion yoga",
            "content": "Hola, te ayudo con yoga. Si quieres, te hago 3 preguntas y te propongo el siguiente paso ideal."
          },
          {
            "key": "yoga-followup",
            "title": "Seguimiento yoga",
            "content": "Te sigo con yoga. Si quieres, hoy mismo te propongo horario, paquete o siguiente accion."
          },
          {
            "key": "yoga-reactivation",
            "title": "Reactivacion yoga",
            "content": "Te escribo porque todavia podemos mover yoga a una accion concreta esta semana. ¿Quieres que te lo aterrice a tu caso?"
          }
        ],
        "behavior_overrides": {
          "tone": "enfocado y motivador",
          "sales_intensity": "alta",
          "required_phrases": [
            "te lo aterrizo a tu caso de yoga",
            "te sigo para moverlo al siguiente paso"
          ],
          "fallback_message": "Te ayudo con yoga. Si quieres, te hago unas preguntas rapidas y te recomiendo el siguiente paso."
        }
      },
      {
        "id": "running-club",
        "name": "running club",
        "strength_score": 76,
        "promise": "Convertir conversaciones de running club en siguiente paso claro, cobro y recurrencia.",
        "growth_motion": "capture_followup_close",
        "buyer": "Dueño de gimnasio o director comercial/operativo",
        "monetizes": [
          "inscripción",
          "primer mes",
          "paquetes",
          "membresías"
        ],
        "service_bundle": [
          "valoracion running club",
          "clase muestra running club",
          "paquete running club",
          "seguimiento de asistencia"
        ],
        "qualification_questions": [
          "cual es tu objetivo principal",
          "en que horario puedes venir",
          "has entrenado antes",
          "quieres clase muestra o plan directo"
        ],
        "objections": [
          "precio",
          "no sé cuál me conviene",
          "no tengo tiempo",
          "me queda lejos"
        ],
        "automation_priorities": [
          "seguimiento running club",
          "recordatorios",
          "winback",
          "upsell"
        ],
        "kpi_pack": [
          "lead a prueba",
          "prueba a membresía",
          "asistencia 30 días",
          "churn temprano",
          "conversion running club",
          "revenue running club"
        ],
        "recommended_commands": [
          "pausar reactivaciones",
          "abrir cupo extraordinario",
          "avisar clase de hoy",
          "solo humano en lesiones"
        ],
        "launch_assets": [
          "guion whatsapp",
          "playbook de handoff",
          "servicios seed",
          "templates seed"
        ],
        "templates": [
          {
            "key": "running-club-lead",
            "title": "Captacion running club",
            "content": "Hola, te ayudo con running club. Si quieres, te hago 3 preguntas y te propongo el siguiente paso ideal."
          },
          {
            "key": "running-club-followup",
            "title": "Seguimiento running club",
            "content": "Te sigo con running club. Si quieres, hoy mismo te propongo horario, paquete o siguiente accion."
          },
          {
            "key": "running-club-reactivation",
            "title": "Reactivacion running club",
            "content": "Te escribo porque todavia podemos mover running club a una accion concreta esta semana. ¿Quieres que te lo aterrice a tu caso?"
          }
        ],
        "behavior_overrides": {
          "tone": "enfocado y motivador",
          "sales_intensity": "alta",
          "required_phrases": [
            "te lo aterrizo a tu caso de running club",
            "te sigo para moverlo al siguiente paso"
          ],
          "fallback_message": "Te ayudo con running club. Si quieres, te hago unas preguntas rapidas y te recomiendo el siguiente paso."
        }
      },
      {
        "id": "academias-deportivas",
        "name": "academias deportivas",
        "strength_score": 74,
        "promise": "Convertir conversaciones de academias deportivas en siguiente paso claro, cobro y recurrencia.",
        "growth_motion": "capture_followup_close",
        "buyer": "Dueño de gimnasio o director comercial/operativo",
        "monetizes": [
          "inscripción",
          "primer mes",
          "paquetes",
          "membresías"
        ],
        "service_bundle": [
          "valoracion academias deportivas",
          "clase muestra academias deportivas",
          "paquete academias deportivas",
          "seguimiento de asistencia"
        ],
        "qualification_questions": [
          "cual es tu objetivo principal",
          "en que horario puedes venir",
          "has entrenado antes",
          "quieres clase muestra o plan directo"
        ],
        "objections": [
          "precio",
          "no sé cuál me conviene",
          "no tengo tiempo",
          "me queda lejos"
        ],
        "automation_priorities": [
          "seguimiento academias deportivas",
          "recordatorios",
          "winback",
          "upsell"
        ],
        "kpi_pack": [
          "lead a prueba",
          "prueba a membresía",
          "asistencia 30 días",
          "churn temprano",
          "conversion academias deportivas",
          "revenue academias deportivas"
        ],
        "recommended_commands": [
          "pausar reactivaciones",
          "abrir cupo extraordinario",
          "avisar clase de hoy",
          "solo humano en lesiones"
        ],
        "launch_assets": [
          "guion whatsapp",
          "playbook de handoff",
          "servicios seed",
          "templates seed"
        ],
        "templates": [
          {
            "key": "academias-deportivas-lead",
            "title": "Captacion academias deportivas",
            "content": "Hola, te ayudo con academias deportivas. Si quieres, te hago 3 preguntas y te propongo el siguiente paso ideal."
          },
          {
            "key": "academias-deportivas-followup",
            "title": "Seguimiento academias deportivas",
            "content": "Te sigo con academias deportivas. Si quieres, hoy mismo te propongo horario, paquete o siguiente accion."
          },
          {
            "key": "academias-deportivas-reactivation",
            "title": "Reactivacion academias deportivas",
            "content": "Te escribo porque todavia podemos mover academias deportivas a una accion concreta esta semana. ¿Quieres que te lo aterrice a tu caso?"
          }
        ],
        "behavior_overrides": {
          "tone": "enfocado y motivador",
          "sales_intensity": "alta",
          "required_phrases": [
            "te lo aterrizo a tu caso de academias deportivas",
            "te sigo para moverlo al siguiente paso"
          ],
          "fallback_message": "Te ayudo con academias deportivas. Si quieres, te hago unas preguntas rapidas y te recomiendo el siguiente paso."
        }
      }
    ],
    "ten_x_operational_pack": {
      "recommended_commands": [
        "pausar reactivaciones",
        "abrir cupo extraordinario",
        "avisar clase de hoy",
        "solo humano en lesiones"
      ],
      "launch_sequence": [
        "escoger subvertical",
        "aplicar pack",
        "simular conversaciones",
        "publicar y medir"
      ],
      "why_this_vertical": "WAOS Fitness gana cuando controla captacion, trial, asistencia, freeze, renovacion y reactivacion desde WhatsApp."
    }
  },
  {
    "id": "dental",
    "name": "WAOS Dental",
    "short_name": "Clinicas dentales",
    "description": "Sistema operativo conversacional para clínicas dentales.",
    "problem": "Las clínicas dentales pierden dinero porque no separan urgencia de valoración, no persiguen presupuestos no aceptados, no sostienen tratamientos por fases y no activan recall suficiente.",
    "subverticals": [
      "odontología general",
      "ortodoncia",
      "alineadores",
      "implantología",
      "periodoncia",
      "endodoncia",
      "estética dental",
      "odontopediatría",
      "rehabilitación oral",
      "cirugía dental"
    ],
    "objects": [
      "sucursal",
      "odontólogo",
      "especialidad",
      "urgencia",
      "valoración",
      "diagnóstico",
      "plan de tratamiento",
      "presupuesto",
      "anticipo",
      "financiamiento",
      "cita de control",
      "recall",
      "paciente",
      "odontólogo / especialista",
      "caso clínico",
      "motivo de consulta",
      "plan de tratamiento por fases",
      "presupuesto por caso",
      "anticipo por fase",
      "recall dental"
    ],
    "flows": [
      "entrada -> urgencia o valoración",
      "valoración -> propuesta",
      "propuesta -> tratamiento",
      "tratamiento -> controles",
      "control -> recall"
    ],
    "kpis": [
      "valoración agendada",
      "valoración asistida",
      "aceptación de tratamiento",
      "ticket por tratamiento",
      "fases completadas",
      "recall",
      "ticket por caso",
      "recall reactivado",
      "no-show a valoración"
    ],
    "recommended_integrations": [
      "whatsapp",
      "google_calendar",
      "payments",
      "crm",
      "reporting"
    ],
    "default_services": [
      "valoracion inicial",
      "limpieza",
      "radiografia",
      "ortodoncia",
      "implantes"
    ],
    "default_faqs": [
      {
        "q": "¿Es urgencia o valoracion?",
        "a": "Podemos clasificar si necesitas atencion inmediata o una valoracion programada."
      },
      {
        "q": "¿Pueden darme rango de precio?",
        "a": "Si, el bot puede compartir un rango orientativo y explicarte que el cierre depende de la valoracion."
      },
      {
        "q": "¿Se puede financiar?",
        "a": "Podemos explicarte opciones de anticipo, fases y financiamiento si aplica."
      },
      {
        "q": "¿Dan seguimiento al tratamiento?",
        "a": "Si, recordamos citas, controles y seguimientos por fases."
      }
    ],
    "behavior": {
      "tone": "claro y tranquilizador",
      "response_length": "media",
      "use_emojis": false,
      "sales_intensity": "media",
      "offer_promotions_when": "after_assessment_booked",
      "escalate_when": [
        "dolor fuerte",
        "sangrado",
        "urgencia",
        "contraindicacion"
      ],
      "insistence_policy": "respectful",
      "can_share_price_directly": true,
      "can_negotiate": false,
      "can_mention_stock": false,
      "auto_send_images": false,
      "bot_mode": "valoracion_y_cierre",
      "active_channels": [
        "whatsapp",
        "webchat"
      ],
      "forbidden_topics": [
        "diagnostico clinico definitivo por chat",
        "prescripciones"
      ],
      "required_phrases": [
        "la valoracion define el plan ideal",
        "si es una urgencia te canalizo de inmediato",
        "te sigo",
        "si la pregunta viene rara, igual te la aterrizo",
        "te lo aterrizo a tu caso"
      ],
      "fallback_message": "Te ayudo a distinguir si es urgencia o valoracion y a agendar con el especialista correcto. Si la pregunta viene rara, en broma o medio fuera de tema, igual te sigo y la aterrizamos al negocio.",
      "humor_policy": "light_contextual",
      "strange_question_policy": "respond_validate_reframe_sell_move"
    },
    "followup_rules": [
      {
        "type": "no_response",
        "delay_minutes": 120,
        "max_attempts": 2,
        "message_template": "¿Quieres que te ayude a apartar tu valoracion o a resolver si tu caso es urgencia?"
      },
      {
        "type": "post_quote",
        "delay_minutes": 1440,
        "max_attempts": 2,
        "message_template": "Quedo pendiente por si quieres retomar tu plan de tratamiento o resolver dudas antes de avanzar."
      },
      {
        "type": "reactivation",
        "delay_minutes": 43200,
        "max_attempts": 1,
        "message_template": "Te recordamos tu siguiente limpieza o control. Si quieres, te ayudo a agendar."
      }
    ],
    "templates": [
      {
        "template_key": "assessment_booking",
        "title": "Agendar valoracion",
        "content": "Te ayudo a apartar tu valoracion con {{specialist}}. ¿Prefieres {{date_option_1}} o {{date_option_2}}?",
        "variables": [
          "specialist",
          "date_option_1",
          "date_option_2"
        ]
      },
      {
        "template_key": "urgency_triage",
        "title": "Triage dental",
        "content": "Para orientarte mejor, dime si hay dolor fuerte, inflamacion, sangrado o trauma reciente.",
        "variables": []
      },
      {
        "template_key": "treatment_followup",
        "title": "Seguimiento tratamiento",
        "content": "Te escribimos para dar continuidad a tu tratamiento. ¿Quieres que retomemos tu siguiente fase o control?",
        "variables": []
      },
      {
        "template_key": "recall_cleaning",
        "title": "Recall limpieza",
        "content": "Ya toca tu siguiente limpieza y control. Si quieres, te comparto horarios disponibles.",
        "variables": []
      },
      {
        "template_key": "deposit_request",
        "title": "Solicitud de anticipo",
        "content": "Para asegurar tu cita o fase de tratamiento, puedo enviarte el link de anticipo ahora mismo.",
        "variables": []
      }
    ],
    "config_overrides": {
      "objective_secondary": [
        "agendar",
        "calificar",
        "reactivar"
      ],
      "policies": [
        "No emitir diagnosticos definitivos por chat",
        "Escalar urgencias dentales y contraindicaciones"
      ],
      "can_say": [
        "valoracion",
        "especialista",
        "rango orientativo",
        "financiamiento",
        "agendar"
      ],
      "cannot_say": [
        "diagnostico definitivo",
        "promesas clinicas absolutas",
        "medicacion"
      ],
      "whatsapp_flows": [
        "triage_dental",
        "agenda_valoracion",
        "seguimiento_tratamiento",
        "recall_limpieza"
      ],
      "appointment_duration_minutes": 40,
      "handoff_keywords": [
        "urgencia",
        "sangrado",
        "dolor",
        "infeccion"
      ],
      "high_score_threshold": 85
    },
    "portfolio_tier": "tier_1",
    "master_thesis": "Sistema operativo conversacional para clínicas dentales que mueve al paciente desde urgencia o valoración hasta tratamiento por fases, control y recall.",
    "buyer": {
      "primary": "Director de clínica dental o gerente comercial",
      "secondary": [
        "coordinación de recepción",
        "especialistas",
        "equipo de seguimiento"
      ]
    },
    "one_pager": {
      "headline": "WAOS Dental",
      "thesis": "WhatsApp se vuelve el frente comercial y operativo del tratamiento: valoración, propuesta, anticipo, fases y recall.",
      "problem": "La clínica responde, pero no opera el tratamiento como proceso comercial completo.",
      "promise": "Cada paciente avanza con un siguiente paso claro: urgencia, valoración, aceptación, siguiente fase o control.",
      "monetizes": [
        "valoración",
        "anticipo",
        "tratamiento por fases",
        "financiamiento",
        "controles",
        "recalls"
      ],
      "packaging": [
        "setup dental por especialidad",
        "triage + agenda + seguimiento",
        "presupuesto pendiente + recall",
        "operación mensual con cierres"
      ],
      "strategic_care": "Es una de las verticales más naturales para WAOS por agenda, seguimiento, cobro y recall; debe venderse como control del tratamiento, no como agenda aislada."
    },
    "demo_flow": [
      "El paciente entra por dolor, limpieza, brackets, implantes o precio.",
      "WAOS separa urgencia de valoración y asigna especialista correcto.",
      "Agenda valoración, confirma y comparte instrucciones previas.",
      "Tras la visita, sigue presupuesto, objeciones de precio y opciones por fases o financiamiento.",
      "Si acepta, agenda tratamiento y cobra anticipo.",
      "Después sostiene controles, recall de limpieza y reactivación de tratamientos pausados."
    ],
    "native_objects": {
      "core": [
        "paciente",
        "sucursal",
        "especialista",
        "motivo de consulta",
        "urgencia",
        "caso clínico dental"
      ],
      "commercial": [
        "valoración",
        "diagnóstico",
        "presupuesto",
        "plan por fases",
        "anticipo",
        "financiamiento"
      ],
      "operations": [
        "tratamiento activo",
        "tratamiento pausado",
        "cita de control",
        "recall",
        "paciente reactivable"
      ]
    },
    "pipeline": {
      "primary": {
        "name": "Valoración y cierre",
        "states": [
          "lead nuevo",
          "urgencia detectada o valoración solicitada",
          "valoración agendada",
          "valoración confirmada",
          "valoración asistida",
          "diagnóstico emitido",
          "propuesta enviada",
          "presupuesto pendiente",
          "tratamiento aceptado",
          "anticipo pagado",
          "tratamiento en progreso",
          "tratamiento terminado",
          "recall programado"
        ]
      },
      "secondary": [
        {
          "name": "Reactivación clínica",
          "states": [
            "presupuesto no aceptado",
            "tratamiento pausado",
            "seguimiento activo",
            "reactivado",
            "cerrado"
          ]
        }
      ]
    },
    "bot_playbook": {
      "must_do": [
        "separar urgencia de consulta normal",
        "asignar especialista",
        "agendar valoración",
        "explicar proceso",
        "seguir presupuesto",
        "cobrar valoración o anticipo",
        "activar recall",
        "nunca quedarse seco ante bromas, preguntas raras o cambios bruscos de tema",
        "usar humor ligero cuando sume, sin sonar payaso ni poco serio",
        "validar el momento y luego reencauzar la conversacion al negocio",
        "cerrar siempre con una pregunta util o siguiente paso"
      ],
      "must_ask": [
        "motivo principal",
        "si hay dolor o sangrado",
        "tipo de tratamiento buscado",
        "sucursal",
        "disponibilidad",
        "si ya es paciente",
        "que parte del negocio se esta atorando mas",
        "si quiere que se lo aterrice a su caso"
      ],
      "objections": [
        "precio",
        "miedo al dolor",
        "quiero pensarlo",
        "no puedo pagarlo completo",
        "no sé si lo necesito ya"
      ],
      "escalate_when": [
        "urgencia médica real",
        "dolor fuerte",
        "discusión clínica específica",
        "retrabajo",
        "queja"
      ],
      "forbidden": [
        "diagnóstico clínico definitivo por chat",
        "prescripciones",
        "promesas clínicas absolutas"
      ],
      "success_signals": [
        "quiero valoración",
        "¿con quién me atiendo?",
        "mándame opciones",
        "quiero apartar",
        "¿aceptan financiamiento?"
      ],
      "style": [
        "humor ligero",
        "manejo de preguntas raras",
        "reencuadre comercial"
      ]
    },
    "automation_sequences": [
      {
        "key": "dental_assessment",
        "name": "Confirmación de valoración",
        "trigger": "valoración agendada",
        "goal": "reducir no-show",
        "steps": [
          "confirmación inmediata",
          "recordatorio 24h",
          "recordatorio 2h"
        ]
      },
      {
        "key": "dental_budget_followup",
        "name": "Seguimiento a presupuesto",
        "trigger": "propuesta enviada",
        "goal": "recuperar tratamientos no cerrados",
        "steps": [
          "resolver dudas",
          "manejar objeción",
          "ofrecer fases o financiamiento"
        ]
      },
      {
        "key": "dental_treatment_active",
        "name": "Tratamiento activo",
        "trigger": "tratamiento aceptado",
        "goal": "sostener continuidad por fases",
        "steps": [
          "recordar siguiente fase",
          "recordar control",
          "cerrar fase pendiente"
        ]
      },
      {
        "key": "dental_recall",
        "name": "Recall de limpieza y revisión",
        "trigger": "paciente sin visita periódica",
        "goal": "recurrencia",
        "steps": [
          "recordatorio",
          "agendar control",
          "cerrar visita"
        ]
      }
    ],
    "dashboard": {
      "north_star": "Aceptación de tratamiento sobre valoraciones asistidas.",
      "sections": [
        {
          "name": "Conversión",
          "metrics": [
            "valoración agendada",
            "valoración asistida",
            "diagnóstico a aceptación",
            "anticipo cobrado"
          ]
        },
        {
          "name": "Revenue",
          "metrics": [
            "ticket por tratamiento",
            "revenue por especialidad",
            "financiamiento aceptado",
            "fases cobradas"
          ]
        },
        {
          "name": "Operación",
          "metrics": [
            "no-show valoración",
            "tiempo a seguimiento",
            "tratamientos activos vs pausados",
            "fases completadas"
          ]
        },
        {
          "name": "Retención",
          "metrics": [
            "recall rate",
            "limpieza recurrente",
            "pacientes reactivados",
            "ingreso por paciente recurrente"
          ]
        }
      ]
    },
    "hardening_model": {
      "goal": "Pasar de preset inteligente a sistema especialista",
      "wave": "ola_1",
      "entity_queen": "caso clínico dental",
      "core_common": true,
      "domain_by_vertical": true,
      "playbooks_by_subvertical": true,
      "kpis_by_vertical": true,
      "pricing_by_vertical": true,
      "journeys_by_vertical": true,
      "reusable_modules": [
        "intake / calificación",
        "agenda / recursos",
        "cotización / propuesta",
        "pago / anticipo / membresía",
        "seguimiento / recurrencia",
        "reporting vertical"
      ],
      "minimum_viable_hardening": [
        "1 entidad reina",
        "1 pipeline propio",
        "1 cotización propia",
        "1 recurrencia propia",
        "1 dashboard propio"
      ],
      "hard_checklist": [
        "tiene entidad principal propia",
        "tiene pipeline específico",
        "tiene cotización o pricing del nicho",
        "tiene agenda o recursos del nicho",
        "tiene postventa o recurrencia del nicho",
        "tiene documentos o compliance del nicho",
        "tiene KPIs del nicho",
        "tiene 3 automatizaciones que mueven dinero",
        "tiene 2 pruebas e2e de negocio",
        "tiene subplaybooks por subvertical",
        "entidad principal propia",
        "pipeline específico",
        "pricing del nicho",
        "agenda y recursos del nicho",
        "postventa o recurrencia del nicho",
        "documentos o compliance del nicho",
        "KPIs del nicho",
        "3 automatizaciones que mueven dinero",
        "2 pruebas e2e de negocio",
        "subplaybooks por subvertical",
        "runtime ejecutable por vertical"
      ]
    },
    "specialist_layers": {
      "persistent_entities": [
        "paciente",
        "odontólogo / especialista",
        "caso clínico",
        "motivo de consulta",
        "plan de tratamiento por fases",
        "presupuesto por caso",
        "anticipo por fase",
        "recall dental"
      ],
      "business_pipeline": {
        "primary_entity": "caso clínico dental",
        "primary_pipeline": {
          "name": "Valoración y cierre",
          "states": [
            "lead nuevo",
            "urgencia detectada o valoración solicitada",
            "valoración agendada",
            "valoración confirmada",
            "valoración asistida",
            "diagnóstico emitido",
            "propuesta enviada",
            "presupuesto pendiente",
            "tratamiento aceptado",
            "anticipo pagado",
            "tratamiento en progreso",
            "tratamiento terminado",
            "recall programado"
          ]
        },
        "secondary_pipelines": [
          {
            "name": "Reactivación clínica",
            "states": [
              "presupuesto no aceptado",
              "tratamiento pausado",
              "seguimiento activo",
              "reactivado",
              "cerrado"
            ]
          }
        ]
      },
      "pricing_and_quotes": [
        "cotización por fases",
        "anticipo por fase",
        "financiamiento de tratamiento"
      ],
      "agenda_and_resources": [
        "odontólogo",
        "especialista",
        "sillón",
        "gabinete",
        "slot de urgencia"
      ],
      "post_sale_and_recurrence": [
        "recall de limpieza",
        "control de ajuste / retenedores",
        "reactivación de tratamiento no cerrado"
      ],
      "documents_compliance": [
        "consentimiento informado",
        "radiografías / estudios",
        "plan de tratamiento",
        "expediente clínico"
      ],
      "kpis_that_matter": [
        "valoración agendada",
        "valoración asistida",
        "aceptación de tratamiento",
        "ticket por tratamiento",
        "fases completadas",
        "recall",
        "ticket por caso",
        "recall reactivado",
        "no-show a valoración"
      ],
      "money_automations": [
        "seguimiento de plan enviado",
        "recuperación de valoración no-show",
        "recall clínico anual/semestral"
      ]
    },
    "domain_contract": {
      "vertical_entity_types": [
        "paciente",
        "odontólogo / especialista",
        "caso clínico",
        "motivo de consulta",
        "plan de tratamiento por fases",
        "presupuesto por caso",
        "anticipo por fase",
        "recall dental"
      ],
      "vertical_pipeline_stages": {
        "primary": [
          "lead nuevo",
          "urgencia detectada o valoración solicitada",
          "valoración agendada",
          "valoración confirmada",
          "valoración asistida",
          "diagnóstico emitido",
          "propuesta enviada",
          "presupuesto pendiente",
          "tratamiento aceptado",
          "anticipo pagado",
          "tratamiento en progreso",
          "tratamiento terminado",
          "recall programado"
        ],
        "secondary": [
          [
            "presupuesto no aceptado",
            "tratamiento pausado",
            "seguimiento activo",
            "reactivado",
            "cerrado"
          ]
        ]
      },
      "vertical_quote_types": [
        "presupuesto por fase",
        "tratamiento integral",
        "financiamiento / mensualidades",
        "anticipo inicial"
      ],
      "vertical_resource_types": [
        "odontólogo",
        "especialista",
        "sillón",
        "gabinete",
        "slot de urgencia"
      ],
      "vertical_followup_policies": [
        "recall de limpieza",
        "control de ajuste / retenedores",
        "reactivación de tratamiento no cerrado"
      ],
      "vertical_kpi_definitions": [
        "valoración agendada",
        "valoración asistida",
        "aceptación de tratamiento",
        "ticket por tratamiento",
        "fases completadas",
        "recall",
        "ticket por caso",
        "recall reactivado",
        "no-show a valoración"
      ],
      "vertical_playbooks": [
        "ortodoncia",
        "implantes",
        "estética dental",
        "endodoncia",
        "odontopediatría"
      ],
      "vertical_document_types": [
        "consentimiento informado",
        "radiografías / estudios",
        "plan de tratamiento",
        "expediente clínico"
      ]
    },
    "subvertical_playbooks": [
      {
        "name": "ortodoncia",
        "focus": "Playbook operativo y comercial para ortodoncia"
      },
      {
        "name": "implantes",
        "focus": "Playbook operativo y comercial para implantes"
      },
      {
        "name": "estética dental",
        "focus": "Playbook operativo y comercial para estética dental"
      },
      {
        "name": "endodoncia",
        "focus": "Playbook operativo y comercial para endodoncia"
      },
      {
        "name": "odontopediatría",
        "focus": "Playbook operativo y comercial para odontopediatría"
      }
    ],
    "business_e2e_tests": [
      {
        "name": "lead de ortodoncia agenda valoración, acepta plan y paga anticipo",
        "status": "designed"
      },
      {
        "name": "paciente en recall recibe seguimiento y agenda limpieza",
        "status": "designed"
      }
    ],
    "vertical_runtime": {
      "pipeline_machine": {
        "primary_pipeline": "Valoración y cierre",
        "entity": "caso clínico dental",
        "states": [
          "lead nuevo",
          "urgencia detectada o valoración solicitada",
          "valoración agendada",
          "valoración confirmada",
          "valoración asistida",
          "diagnóstico emitido",
          "propuesta enviada",
          "presupuesto pendiente",
          "tratamiento aceptado",
          "anticipo pagado",
          "tratamiento en progreso",
          "tratamiento terminado",
          "recall programado"
        ],
        "transitions": [
          {
            "from": "lead nuevo",
            "to": "urgencia detectada o valoración solicitada",
            "trigger": "qualification_complete",
            "business_effect": "advance opportunity"
          },
          {
            "from": "urgencia detectada o valoración solicitada",
            "to": "valoración agendada",
            "trigger": "deposit_unpaid",
            "business_effect": "open commercial step"
          },
          {
            "from": "tratamiento terminado",
            "to": "recall programado",
            "trigger": "successful_outcome",
            "business_effect": "realize revenue or continuity"
          },
          {
            "from": "tratamiento terminado",
            "to": "at_risk",
            "trigger": "treatment_pending",
            "business_effect": "activate retention sequence"
          }
        ],
        "at_risk_state": "at_risk",
        "closed_states": [
          "recall programado"
        ]
      },
      "pricing_engine": {
        "quote_types": [
          "valoracion",
          "plan por fases",
          "anticipo",
          "financiamiento"
        ],
        "pricing_basis": "treatment_type + phases + specialist + financing",
        "rules": [
          {
            "rule": "base price by tratamiento type",
            "effect": "set base_price"
          },
          {
            "rule": "premium or urgent add-ons increase quote",
            "effect": "add surcharge"
          },
          {
            "rule": "bundle, membership or financing can lower immediate friction",
            "effect": "recommend package or installments"
          }
        ],
        "deposit_policy": "request advance when capacity, specialist time or inventory must be secured"
      },
      "resource_capacity": {
        "resource_types": [
          "odontologo",
          "especialista",
          "gabinete",
          "radiografia",
          "quirófano menor"
        ],
        "capacity_basis": "specialist chair time, room type and clinical block duration",
        "constraints": [
          "avoid double booking of critical resources",
          "respect service duration and cleanup/buffer time",
          "prioritize higher urgency and higher close probability cases"
        ],
        "priority_queue": "especialista, gabinete y fase"
      },
      "recurrence_engine": {
        "policies": [
          {
            "type": "cleaning_recall",
            "interval_days": 180,
            "anchor": "caso clínico dental"
          },
          {
            "type": "orthodontic_control",
            "interval_days": 30,
            "anchor": "caso clínico dental"
          },
          {
            "type": "retainer_review",
            "interval_days": 180,
            "anchor": "caso clínico dental"
          }
        ],
        "reactivation_window_days": 180,
        "goal": "protect retention, repeat revenue and continuity"
      },
      "kpi_engine": {
        "north_star": "Aceptación de tratamiento sobre valoraciones asistidas.",
        "definitions": [
          {
            "name": "treatment_acceptance",
            "formula": "accepted_treatments / proposed_treatments"
          },
          {
            "name": "ticket_per_case",
            "formula": "treatment_revenue / closed_cases"
          },
          {
            "name": "recall_reactivation",
            "formula": "recalled_cases_booked / recall_due"
          }
        ],
        "leading_indicators": [
          "treatment_pending",
          "control_due",
          "no_response_7d"
        ]
      },
      "automation_engine": {
        "money_automation_policies": [
          {
            "trigger": "treatment_pending",
            "actions": [
              "send_followup",
              "escalate_owner",
              "offer_relevant_next_step"
            ],
            "goal": "save conversion or retention"
          },
          {
            "trigger": "control_due",
            "actions": [
              "send_quote_or_payment_link",
              "remind_deadline",
              "notify_human"
            ],
            "goal": "move revenue forward"
          },
          {
            "trigger": "phase_completed",
            "actions": [
              "schedule_recurrence",
              "cross_sell_next_best_offer",
              "create_task"
            ],
            "goal": "increase LTV"
          }
        ],
        "quiet_hours": "21:00-08:00"
      },
      "document_flow": {
        "required_documents": [
          "consentimiento informado",
          "radiografias",
          "plan de tratamiento",
          "pagare o financiamiento"
        ],
        "lifecycle_rules": [
          {
            "document": "consentimiento informado",
            "required_before": "first committed step",
            "signature_required": true
          },
          {
            "document": "pagare o financiamiento",
            "required_before": "handoff or continuity step",
            "signature_required": false
          }
        ]
      },
      "matching_engine": {
        "entity": "caso clínico dental",
        "rules": [
          "reason_for_visit -> specialty",
          "urgency_level -> priority_queue",
          "budget_fit",
          "branch_match"
        ],
        "next_best_match_outputs": [
          "best_owner",
          "best_resource_slot",
          "best_offer"
        ]
      }
    },
    "transactional_motor_v12": {
      "version": "v12_full_transactional",
      "aggregate_root": "dental_case_account",
      "main_business_entity": "caso clínico dental",
      "transaction_unit": "treatment_phase",
      "system_of_record": {
        "write_model": [
          "commands",
          "events",
          "ledger",
          "aggregate_snapshots"
        ],
        "read_models": [
          "commercial_board",
          "operations_board",
          "finance_board",
          "continuity_board",
          "resource_load_board",
          "document_readiness_board",
          "revenue_levers_board"
        ],
        "idempotency_scope": [
          "organization_id",
          "vertical_id",
          "external_reference",
          "command_key"
        ],
        "audit_mode": "append_only_with_snapshots"
      },
      "transaction_primitives": {
        "commands": [
          "capture_intent",
          "qualify_record",
          "create_quote",
          "request_deposit",
          "reserve_capacity",
          "confirm_booking",
          "start_case",
          "approve_quote",
          "collect_payment",
          "start_fulfillment",
          "close_fulfillment",
          "schedule_recurrence",
          "issue_refund",
          "reactivate_customer",
          "approve_treatment_plan",
          "collect_phase_deposit",
          "start_treatment_phase",
          "schedule_recall"
        ],
        "events": [
          "intent_captured",
          "record_qualified",
          "quote_created",
          "deposit_requested",
          "capacity_reserved",
          "booking_confirmed",
          "case_started",
          "quote_approved",
          "payment_collected",
          "fulfillment_started",
          "fulfillment_closed",
          "recurrence_scheduled",
          "refund_issued",
          "customer_reactivated",
          "treatment_plan_approved",
          "phase_deposit_collected",
          "treatment_phase_started",
          "recall_due"
        ],
        "ledger_event_types": [
          "charge_opened",
          "deposit_collected",
          "installment_due",
          "payment_applied",
          "credit_issued",
          "refund_issued",
          "write_off_registered"
        ],
        "invariants": [
          "no iniciar fase sin consentimiento",
          "no agendar procedimiento sin estudios requeridos",
          "no cerrar caso con saldo pendiente",
          "todo pago debe referenciar quote, order o case activo",
          "todo cambio crítico debe emitir evento y renglón de auditoría",
          "ningún recurso se confirma dos veces en la misma ventana"
        ],
        "idempotency_keys": [
          "command_key",
          "payment_reference",
          "booking_reference",
          "external_message_id"
        ]
      },
      "aggregates": {
        "primary_record": {
          "name": "caso clínico dental",
          "status_axis": [
            "commercial",
            "operations",
            "finance",
            "continuity"
          ]
        },
        "quote": {
          "name": "treatment_plan_quote",
          "states": [
            "draft",
            "sent",
            "accepted",
            "expired",
            "lost"
          ]
        },
        "booking": {
          "name": "valuation_booking",
          "states": [
            "proposed",
            "reserved",
            "confirmed",
            "attended_or_executed",
            "missed_or_canceled"
          ]
        },
        "execution": {
          "name": "treatment_phase_execution",
          "states": [
            "pending",
            "ready",
            "in_progress",
            "blocked",
            "completed",
            "closed"
          ]
        },
        "payment_account": {
          "name": "payment_account",
          "states": [
            "open",
            "partially_paid",
            "paid",
            "overdue",
            "refunded"
          ]
        },
        "continuity": {
          "name": "recall_plan",
          "states": [
            "not_started",
            "active",
            "at_risk",
            "recovered",
            "closed"
          ]
        }
      },
      "orchestration": {
        "command_handlers": [
          "handle_capture_intent",
          "handle_qualify_record",
          "handle_create_quote",
          "handle_request_deposit",
          "handle_reserve_capacity",
          "handle_confirm_booking",
          "handle_start_case",
          "handle_approve_quote",
          "handle_approve_treatment_plan",
          "handle_collect_phase_deposit",
          "handle_start_treatment_phase",
          "handle_schedule_recall"
        ],
        "sagas": [
          "valuation_to_acceptance",
          "phase_financing_collection",
          "recall_reactivation"
        ],
        "money_guards": [
          "quote_before_payment",
          "capacity_before_confirmation",
          "documents_before_execution",
          "balance_before_close"
        ],
        "read_model_refresh": [
          "on_every_event",
          "nightly_reconciliation",
          "pre_dashboard_cache"
        ]
      },
      "finance": {
        "money_objects": [
          "valuation_charge",
          "phase_deposit",
          "monthly_installment",
          "balance_collection"
        ],
        "collection_modes": [
          "anticipo por fase",
          "mensualidades",
          "liquidación final"
        ],
        "refund_modes": [
          "clinical_credit",
          "phase_reversal"
        ],
        "reconciliation_views": [
          "expected_vs_collected",
          "aging_balance",
          "refund_exposure",
          "cash_by_stage"
        ]
      },
      "operations": {
        "fulfillment_unit": "treatment_phase",
        "resource_locking": [
          "specialist",
          "chair",
          "operatory_time"
        ],
        "dispatch_or_schedule_board": [
          "queued",
          "ready",
          "assigned",
          "in_progress",
          "blocked",
          "done"
        ],
        "handoff_rules": [
          "human_handoff_on_exception",
          "supervisor_handoff_on_money_risk",
          "operator_handoff_on_compliance_gap"
        ]
      },
      "audit_compliance": {
        "timeline_entities": [
          "caso clínico dental",
          "treatment_plan_quote",
          "valuation_booking",
          "treatment_phase_execution",
          "payment_account"
        ],
        "consent_gates": [
          "informed_consent",
          "clinical_study",
          "treatment_plan_signature"
        ],
        "required_evidence": [
          "timeline_event",
          "actor",
          "timestamp",
          "before_after_snapshot"
        ],
        "retention_rules": [
          "audit_log_append_only",
          "documents_linked_to_primary_record",
          "payment_trace_non_destructive"
        ]
      },
      "transaction_views": {
        "commercial": [
          "valuation",
          "acceptance",
          "phase_conversion"
        ],
        "operations": [
          "chair_load",
          "phase_progress",
          "followups"
        ],
        "finance": [
          "ticket_per_case",
          "installments",
          "outstanding_balance"
        ],
        "continuity": [
          "recall",
          "retention",
          "reactivation"
        ]
      },
      "command_catalog": [
        {
          "command": "capture_intent",
          "writes": "caso clínico dental",
          "emits": "intent_captured",
          "guard": "no iniciar fase sin consentimiento"
        },
        {
          "command": "qualify_record",
          "writes": "caso clínico dental",
          "emits": "record_qualified",
          "guard": "no agendar procedimiento sin estudios requeridos"
        },
        {
          "command": "create_quote",
          "writes": "caso clínico dental",
          "emits": "quote_created",
          "guard": "no cerrar caso con saldo pendiente"
        },
        {
          "command": "request_deposit",
          "writes": "caso clínico dental",
          "emits": "deposit_requested",
          "guard": "no iniciar fase sin consentimiento"
        },
        {
          "command": "reserve_capacity",
          "writes": "caso clínico dental",
          "emits": "capacity_reserved",
          "guard": "no agendar procedimiento sin estudios requeridos"
        },
        {
          "command": "confirm_booking",
          "writes": "caso clínico dental",
          "emits": "booking_confirmed",
          "guard": "no cerrar caso con saldo pendiente"
        },
        {
          "command": "start_case",
          "writes": "caso clínico dental",
          "emits": "case_started",
          "guard": "no iniciar fase sin consentimiento"
        },
        {
          "command": "approve_quote",
          "writes": "caso clínico dental",
          "emits": "quote_approved",
          "guard": "no agendar procedimiento sin estudios requeridos"
        },
        {
          "command": "approve_treatment_plan",
          "writes": "caso clínico dental",
          "emits": "payment_collected",
          "guard": "no cerrar caso con saldo pendiente"
        },
        {
          "command": "collect_phase_deposit",
          "writes": "caso clínico dental",
          "emits": "fulfillment_started",
          "guard": "no iniciar fase sin consentimiento"
        },
        {
          "command": "start_treatment_phase",
          "writes": "caso clínico dental",
          "emits": "fulfillment_closed",
          "guard": "no agendar procedimiento sin estudios requeridos"
        },
        {
          "command": "schedule_recall",
          "writes": "caso clínico dental",
          "emits": "recurrence_scheduled",
          "guard": "no cerrar caso con saldo pendiente"
        }
      ],
      "event_catalog": [
        {
          "event": "intent_captured",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "valuation_to_acceptance"
        },
        {
          "event": "record_qualified",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "phase_financing_collection"
        },
        {
          "event": "quote_created",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "recall_reactivation"
        },
        {
          "event": "deposit_requested",
          "updates": [
            "timeline",
            "boards",
            "ledger"
          ],
          "next_action": "valuation_to_acceptance"
        },
        {
          "event": "capacity_reserved",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "phase_financing_collection"
        },
        {
          "event": "booking_confirmed",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "recall_reactivation"
        },
        {
          "event": "case_started",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "valuation_to_acceptance"
        },
        {
          "event": "quote_approved",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "phase_financing_collection"
        },
        {
          "event": "treatment_plan_approved",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "recall_reactivation"
        },
        {
          "event": "phase_deposit_collected",
          "updates": [
            "timeline",
            "boards",
            "ledger"
          ],
          "next_action": "valuation_to_acceptance"
        },
        {
          "event": "treatment_phase_started",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "phase_financing_collection"
        },
        {
          "event": "recall_due",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "recall_reactivation"
        }
      ]
    },
    "is_strongest_vertical": true,
    "strongest_rank": 2,
    "ten_x_score": 99,
    "ten_x_narrative": "WAOS Dental gana cuando convierte valoracion en tratamiento por fases, anticipo, documentos y recall.",
    "ten_x_growth_loops": [
      "urgencia a valoracion",
      "valoracion a plan",
      "plan a anticipo",
      "fase cerrada a recall"
    ],
    "recommended_subverticals": [
      "odontología general",
      "ortodoncia",
      "alineadores",
      "implantología"
    ],
    "subvertical_profiles": [
      {
        "id": "odontología-general",
        "name": "odontología general",
        "strength_score": 99,
        "promise": "Convertir conversaciones de odontología general en siguiente paso claro, cobro y recurrencia.",
        "growth_motion": "capture_followup_close",
        "buyer": "Director de clínica dental o gerente comercial",
        "monetizes": [
          "valoración",
          "anticipo",
          "tratamiento por fases",
          "financiamiento"
        ],
        "service_bundle": [
          "valoracion odontología general",
          "plan odontología general",
          "control odontología general",
          "recall"
        ],
        "qualification_questions": [
          "es urgencia o valoracion",
          "que te preocupa mas",
          "cuando te gustaria venir",
          "necesitas facilidades de pago"
        ],
        "objections": [
          "precio",
          "miedo al dolor",
          "quiero pensarlo",
          "no puedo pagarlo completo"
        ],
        "automation_priorities": [
          "seguimiento odontología general",
          "recordatorios",
          "winback",
          "upsell"
        ],
        "kpi_pack": [
          "valoración agendada",
          "valoración asistida",
          "aceptación de tratamiento",
          "ticket por tratamiento",
          "conversion odontología general",
          "revenue odontología general"
        ],
        "recommended_commands": [
          "avisar recalls vencidos",
          "bloquear agenda de cirugia",
          "modo solo humano por urgencia",
          "reactivar seguimiento de presupuestos"
        ],
        "launch_assets": [
          "guion whatsapp",
          "playbook de handoff",
          "servicios seed",
          "templates seed"
        ],
        "templates": [
          {
            "key": "odontología-general-lead",
            "title": "Captacion odontología general",
            "content": "Hola, te ayudo con odontología general. Si quieres, te hago 3 preguntas y te propongo el siguiente paso ideal."
          },
          {
            "key": "odontología-general-followup",
            "title": "Seguimiento odontología general",
            "content": "Te sigo con odontología general. Si quieres, hoy mismo te propongo horario, paquete o siguiente accion."
          },
          {
            "key": "odontología-general-reactivation",
            "title": "Reactivacion odontología general",
            "content": "Te escribo porque todavia podemos mover odontología general a una accion concreta esta semana. ¿Quieres que te lo aterrice a tu caso?"
          }
        ],
        "behavior_overrides": {
          "tone": "claro y tranquilizador",
          "sales_intensity": "media",
          "required_phrases": [
            "te lo aterrizo a tu caso de odontología general",
            "te sigo para moverlo al siguiente paso"
          ],
          "fallback_message": "Te ayudo con odontología general. Si quieres, te hago unas preguntas rapidas y te recomiendo el siguiente paso."
        }
      },
      {
        "id": "ortodoncia",
        "name": "ortodoncia",
        "strength_score": 97,
        "promise": "Mover valoracion a diagnostico, plan y anticipo con seguimiento disciplinado.",
        "growth_motion": "diagnosis_to_advance",
        "buyer": "Director de clínica dental o gerente comercial",
        "monetizes": [
          "valoración",
          "anticipo",
          "tratamiento por fases",
          "financiamiento"
        ],
        "service_bundle": [
          "valoracion ortodoncia",
          "diagnostico digital",
          "plan por fases",
          "control mensual"
        ],
        "qualification_questions": [
          "es urgencia o valoracion",
          "que te preocupa mas",
          "cuando te gustaria venir",
          "necesitas facilidades de pago"
        ],
        "objections": [
          "quiero comparar",
          "esta caro",
          "me da miedo el tiempo de tratamiento",
          "necesito hablarlo"
        ],
        "automation_priorities": [
          "seguimiento ortodoncia",
          "recordatorios",
          "winback",
          "upsell"
        ],
        "kpi_pack": [
          "valoración agendada",
          "valoración asistida",
          "aceptación de tratamiento",
          "ticket por tratamiento",
          "conversion ortodoncia",
          "revenue ortodoncia"
        ],
        "recommended_commands": [
          "avisar recalls vencidos",
          "bloquear agenda de cirugia",
          "modo solo humano por urgencia",
          "reactivar seguimiento de presupuestos"
        ],
        "launch_assets": [
          "guion whatsapp",
          "playbook de handoff",
          "servicios seed",
          "templates seed"
        ],
        "templates": [
          {
            "key": "ortodoncia-lead",
            "title": "Captacion ortodoncia",
            "content": "Hola, te ayudo con ortodoncia. Si quieres, te hago 3 preguntas y te propongo el siguiente paso ideal."
          },
          {
            "key": "ortodoncia-followup",
            "title": "Seguimiento ortodoncia",
            "content": "Te sigo con ortodoncia. Si quieres, hoy mismo te propongo horario, paquete o siguiente accion."
          },
          {
            "key": "ortodoncia-reactivation",
            "title": "Reactivacion ortodoncia",
            "content": "Te escribo porque todavia podemos mover ortodoncia a una accion concreta esta semana. ¿Quieres que te lo aterrice a tu caso?"
          }
        ],
        "behavior_overrides": {
          "tone": "claro y tranquilizador",
          "sales_intensity": "media",
          "required_phrases": [
            "te lo aterrizo a tu caso de ortodoncia",
            "te sigo para moverlo al siguiente paso"
          ],
          "fallback_message": "Te ayudo con ortodoncia. Si quieres, te hago unas preguntas rapidas y te recomiendo el siguiente paso."
        }
      },
      {
        "id": "alineadores",
        "name": "alineadores",
        "strength_score": 95,
        "promise": "Convertir conversaciones de alineadores en siguiente paso claro, cobro y recurrencia.",
        "growth_motion": "capture_followup_close",
        "buyer": "Director de clínica dental o gerente comercial",
        "monetizes": [
          "valoración",
          "anticipo",
          "tratamiento por fases",
          "financiamiento"
        ],
        "service_bundle": [
          "valoracion alineadores",
          "plan alineadores",
          "control alineadores",
          "recall"
        ],
        "qualification_questions": [
          "es urgencia o valoracion",
          "que te preocupa mas",
          "cuando te gustaria venir",
          "necesitas facilidades de pago"
        ],
        "objections": [
          "precio",
          "miedo al dolor",
          "quiero pensarlo",
          "no puedo pagarlo completo"
        ],
        "automation_priorities": [
          "seguimiento alineadores",
          "recordatorios",
          "winback",
          "upsell"
        ],
        "kpi_pack": [
          "valoración agendada",
          "valoración asistida",
          "aceptación de tratamiento",
          "ticket por tratamiento",
          "conversion alineadores",
          "revenue alineadores"
        ],
        "recommended_commands": [
          "avisar recalls vencidos",
          "bloquear agenda de cirugia",
          "modo solo humano por urgencia",
          "reactivar seguimiento de presupuestos"
        ],
        "launch_assets": [
          "guion whatsapp",
          "playbook de handoff",
          "servicios seed",
          "templates seed"
        ],
        "templates": [
          {
            "key": "alineadores-lead",
            "title": "Captacion alineadores",
            "content": "Hola, te ayudo con alineadores. Si quieres, te hago 3 preguntas y te propongo el siguiente paso ideal."
          },
          {
            "key": "alineadores-followup",
            "title": "Seguimiento alineadores",
            "content": "Te sigo con alineadores. Si quieres, hoy mismo te propongo horario, paquete o siguiente accion."
          },
          {
            "key": "alineadores-reactivation",
            "title": "Reactivacion alineadores",
            "content": "Te escribo porque todavia podemos mover alineadores a una accion concreta esta semana. ¿Quieres que te lo aterrice a tu caso?"
          }
        ],
        "behavior_overrides": {
          "tone": "claro y tranquilizador",
          "sales_intensity": "media",
          "required_phrases": [
            "te lo aterrizo a tu caso de alineadores",
            "te sigo para moverlo al siguiente paso"
          ],
          "fallback_message": "Te ayudo con alineadores. Si quieres, te hago unas preguntas rapidas y te recomiendo el siguiente paso."
        }
      },
      {
        "id": "implantología",
        "name": "implantología",
        "strength_score": 93,
        "promise": "Convertir conversaciones de implantología en siguiente paso claro, cobro y recurrencia.",
        "growth_motion": "capture_followup_close",
        "buyer": "Director de clínica dental o gerente comercial",
        "monetizes": [
          "valoración",
          "anticipo",
          "tratamiento por fases",
          "financiamiento"
        ],
        "service_bundle": [
          "valoracion implantología",
          "plan implantología",
          "control implantología",
          "recall"
        ],
        "qualification_questions": [
          "es urgencia o valoracion",
          "que te preocupa mas",
          "cuando te gustaria venir",
          "necesitas facilidades de pago"
        ],
        "objections": [
          "precio",
          "miedo al dolor",
          "quiero pensarlo",
          "no puedo pagarlo completo"
        ],
        "automation_priorities": [
          "seguimiento implantología",
          "recordatorios",
          "winback",
          "upsell"
        ],
        "kpi_pack": [
          "valoración agendada",
          "valoración asistida",
          "aceptación de tratamiento",
          "ticket por tratamiento",
          "conversion implantología",
          "revenue implantología"
        ],
        "recommended_commands": [
          "avisar recalls vencidos",
          "bloquear agenda de cirugia",
          "modo solo humano por urgencia",
          "reactivar seguimiento de presupuestos"
        ],
        "launch_assets": [
          "guion whatsapp",
          "playbook de handoff",
          "servicios seed",
          "templates seed"
        ],
        "templates": [
          {
            "key": "implantología-lead",
            "title": "Captacion implantología",
            "content": "Hola, te ayudo con implantología. Si quieres, te hago 3 preguntas y te propongo el siguiente paso ideal."
          },
          {
            "key": "implantología-followup",
            "title": "Seguimiento implantología",
            "content": "Te sigo con implantología. Si quieres, hoy mismo te propongo horario, paquete o siguiente accion."
          },
          {
            "key": "implantología-reactivation",
            "title": "Reactivacion implantología",
            "content": "Te escribo porque todavia podemos mover implantología a una accion concreta esta semana. ¿Quieres que te lo aterrice a tu caso?"
          }
        ],
        "behavior_overrides": {
          "tone": "claro y tranquilizador",
          "sales_intensity": "media",
          "required_phrases": [
            "te lo aterrizo a tu caso de implantología",
            "te sigo para moverlo al siguiente paso"
          ],
          "fallback_message": "Te ayudo con implantología. Si quieres, te hago unas preguntas rapidas y te recomiendo el siguiente paso."
        }
      },
      {
        "id": "periodoncia",
        "name": "periodoncia",
        "strength_score": 91,
        "promise": "Convertir conversaciones de periodoncia en siguiente paso claro, cobro y recurrencia.",
        "growth_motion": "capture_followup_close",
        "buyer": "Director de clínica dental o gerente comercial",
        "monetizes": [
          "valoración",
          "anticipo",
          "tratamiento por fases",
          "financiamiento"
        ],
        "service_bundle": [
          "valoracion periodoncia",
          "plan periodoncia",
          "control periodoncia",
          "recall"
        ],
        "qualification_questions": [
          "es urgencia o valoracion",
          "que te preocupa mas",
          "cuando te gustaria venir",
          "necesitas facilidades de pago"
        ],
        "objections": [
          "precio",
          "miedo al dolor",
          "quiero pensarlo",
          "no puedo pagarlo completo"
        ],
        "automation_priorities": [
          "seguimiento periodoncia",
          "recordatorios",
          "winback",
          "upsell"
        ],
        "kpi_pack": [
          "valoración agendada",
          "valoración asistida",
          "aceptación de tratamiento",
          "ticket por tratamiento",
          "conversion periodoncia",
          "revenue periodoncia"
        ],
        "recommended_commands": [
          "avisar recalls vencidos",
          "bloquear agenda de cirugia",
          "modo solo humano por urgencia",
          "reactivar seguimiento de presupuestos"
        ],
        "launch_assets": [
          "guion whatsapp",
          "playbook de handoff",
          "servicios seed",
          "templates seed"
        ],
        "templates": [
          {
            "key": "periodoncia-lead",
            "title": "Captacion periodoncia",
            "content": "Hola, te ayudo con periodoncia. Si quieres, te hago 3 preguntas y te propongo el siguiente paso ideal."
          },
          {
            "key": "periodoncia-followup",
            "title": "Seguimiento periodoncia",
            "content": "Te sigo con periodoncia. Si quieres, hoy mismo te propongo horario, paquete o siguiente accion."
          },
          {
            "key": "periodoncia-reactivation",
            "title": "Reactivacion periodoncia",
            "content": "Te escribo porque todavia podemos mover periodoncia a una accion concreta esta semana. ¿Quieres que te lo aterrice a tu caso?"
          }
        ],
        "behavior_overrides": {
          "tone": "claro y tranquilizador",
          "sales_intensity": "media",
          "required_phrases": [
            "te lo aterrizo a tu caso de periodoncia",
            "te sigo para moverlo al siguiente paso"
          ],
          "fallback_message": "Te ayudo con periodoncia. Si quieres, te hago unas preguntas rapidas y te recomiendo el siguiente paso."
        }
      },
      {
        "id": "endodoncia",
        "name": "endodoncia",
        "strength_score": 89,
        "promise": "Convertir conversaciones de endodoncia en siguiente paso claro, cobro y recurrencia.",
        "growth_motion": "capture_followup_close",
        "buyer": "Director de clínica dental o gerente comercial",
        "monetizes": [
          "valoración",
          "anticipo",
          "tratamiento por fases",
          "financiamiento"
        ],
        "service_bundle": [
          "valoracion endodoncia",
          "plan endodoncia",
          "control endodoncia",
          "recall"
        ],
        "qualification_questions": [
          "es urgencia o valoracion",
          "que te preocupa mas",
          "cuando te gustaria venir",
          "necesitas facilidades de pago"
        ],
        "objections": [
          "precio",
          "miedo al dolor",
          "quiero pensarlo",
          "no puedo pagarlo completo"
        ],
        "automation_priorities": [
          "seguimiento endodoncia",
          "recordatorios",
          "winback",
          "upsell"
        ],
        "kpi_pack": [
          "valoración agendada",
          "valoración asistida",
          "aceptación de tratamiento",
          "ticket por tratamiento",
          "conversion endodoncia",
          "revenue endodoncia"
        ],
        "recommended_commands": [
          "avisar recalls vencidos",
          "bloquear agenda de cirugia",
          "modo solo humano por urgencia",
          "reactivar seguimiento de presupuestos"
        ],
        "launch_assets": [
          "guion whatsapp",
          "playbook de handoff",
          "servicios seed",
          "templates seed"
        ],
        "templates": [
          {
            "key": "endodoncia-lead",
            "title": "Captacion endodoncia",
            "content": "Hola, te ayudo con endodoncia. Si quieres, te hago 3 preguntas y te propongo el siguiente paso ideal."
          },
          {
            "key": "endodoncia-followup",
            "title": "Seguimiento endodoncia",
            "content": "Te sigo con endodoncia. Si quieres, hoy mismo te propongo horario, paquete o siguiente accion."
          },
          {
            "key": "endodoncia-reactivation",
            "title": "Reactivacion endodoncia",
            "content": "Te escribo porque todavia podemos mover endodoncia a una accion concreta esta semana. ¿Quieres que te lo aterrice a tu caso?"
          }
        ],
        "behavior_overrides": {
          "tone": "claro y tranquilizador",
          "sales_intensity": "media",
          "required_phrases": [
            "te lo aterrizo a tu caso de endodoncia",
            "te sigo para moverlo al siguiente paso"
          ],
          "fallback_message": "Te ayudo con endodoncia. Si quieres, te hago unas preguntas rapidas y te recomiendo el siguiente paso."
        }
      },
      {
        "id": "estética-dental",
        "name": "estética dental",
        "strength_score": 87,
        "promise": "Convertir conversaciones de estética dental en siguiente paso claro, cobro y recurrencia.",
        "growth_motion": "capture_followup_close",
        "buyer": "Director de clínica dental o gerente comercial",
        "monetizes": [
          "valoración",
          "anticipo",
          "tratamiento por fases",
          "financiamiento"
        ],
        "service_bundle": [
          "valoracion estética dental",
          "plan estética dental",
          "control estética dental",
          "recall"
        ],
        "qualification_questions": [
          "es urgencia o valoracion",
          "que te preocupa mas",
          "cuando te gustaria venir",
          "necesitas facilidades de pago"
        ],
        "objections": [
          "precio",
          "miedo al dolor",
          "quiero pensarlo",
          "no puedo pagarlo completo"
        ],
        "automation_priorities": [
          "seguimiento estética dental",
          "recordatorios",
          "winback",
          "upsell"
        ],
        "kpi_pack": [
          "valoración agendada",
          "valoración asistida",
          "aceptación de tratamiento",
          "ticket por tratamiento",
          "conversion estética dental",
          "revenue estética dental"
        ],
        "recommended_commands": [
          "avisar recalls vencidos",
          "bloquear agenda de cirugia",
          "modo solo humano por urgencia",
          "reactivar seguimiento de presupuestos"
        ],
        "launch_assets": [
          "guion whatsapp",
          "playbook de handoff",
          "servicios seed",
          "templates seed"
        ],
        "templates": [
          {
            "key": "estética-dental-lead",
            "title": "Captacion estética dental",
            "content": "Hola, te ayudo con estética dental. Si quieres, te hago 3 preguntas y te propongo el siguiente paso ideal."
          },
          {
            "key": "estética-dental-followup",
            "title": "Seguimiento estética dental",
            "content": "Te sigo con estética dental. Si quieres, hoy mismo te propongo horario, paquete o siguiente accion."
          },
          {
            "key": "estética-dental-reactivation",
            "title": "Reactivacion estética dental",
            "content": "Te escribo porque todavia podemos mover estética dental a una accion concreta esta semana. ¿Quieres que te lo aterrice a tu caso?"
          }
        ],
        "behavior_overrides": {
          "tone": "claro y tranquilizador",
          "sales_intensity": "media",
          "required_phrases": [
            "te lo aterrizo a tu caso de estética dental",
            "te sigo para moverlo al siguiente paso"
          ],
          "fallback_message": "Te ayudo con estética dental. Si quieres, te hago unas preguntas rapidas y te recomiendo el siguiente paso."
        }
      },
      {
        "id": "odontopediatría",
        "name": "odontopediatría",
        "strength_score": 85,
        "promise": "Convertir conversaciones de odontopediatría en siguiente paso claro, cobro y recurrencia.",
        "growth_motion": "capture_followup_close",
        "buyer": "Director de clínica dental o gerente comercial",
        "monetizes": [
          "valoración",
          "anticipo",
          "tratamiento por fases",
          "financiamiento"
        ],
        "service_bundle": [
          "valoracion odontopediatría",
          "plan odontopediatría",
          "control odontopediatría",
          "recall"
        ],
        "qualification_questions": [
          "es urgencia o valoracion",
          "que te preocupa mas",
          "cuando te gustaria venir",
          "necesitas facilidades de pago"
        ],
        "objections": [
          "precio",
          "miedo al dolor",
          "quiero pensarlo",
          "no puedo pagarlo completo"
        ],
        "automation_priorities": [
          "seguimiento odontopediatría",
          "recordatorios",
          "winback",
          "upsell"
        ],
        "kpi_pack": [
          "valoración agendada",
          "valoración asistida",
          "aceptación de tratamiento",
          "ticket por tratamiento",
          "conversion odontopediatría",
          "revenue odontopediatría"
        ],
        "recommended_commands": [
          "avisar recalls vencidos",
          "bloquear agenda de cirugia",
          "modo solo humano por urgencia",
          "reactivar seguimiento de presupuestos"
        ],
        "launch_assets": [
          "guion whatsapp",
          "playbook de handoff",
          "servicios seed",
          "templates seed"
        ],
        "templates": [
          {
            "key": "odontopediatría-lead",
            "title": "Captacion odontopediatría",
            "content": "Hola, te ayudo con odontopediatría. Si quieres, te hago 3 preguntas y te propongo el siguiente paso ideal."
          },
          {
            "key": "odontopediatría-followup",
            "title": "Seguimiento odontopediatría",
            "content": "Te sigo con odontopediatría. Si quieres, hoy mismo te propongo horario, paquete o siguiente accion."
          },
          {
            "key": "odontopediatría-reactivation",
            "title": "Reactivacion odontopediatría",
            "content": "Te escribo porque todavia podemos mover odontopediatría a una accion concreta esta semana. ¿Quieres que te lo aterrice a tu caso?"
          }
        ],
        "behavior_overrides": {
          "tone": "claro y tranquilizador",
          "sales_intensity": "media",
          "required_phrases": [
            "te lo aterrizo a tu caso de odontopediatría",
            "te sigo para moverlo al siguiente paso"
          ],
          "fallback_message": "Te ayudo con odontopediatría. Si quieres, te hago unas preguntas rapidas y te recomiendo el siguiente paso."
        }
      },
      {
        "id": "rehabilitación-oral",
        "name": "rehabilitación oral",
        "strength_score": 83,
        "promise": "Convertir conversaciones de rehabilitación oral en siguiente paso claro, cobro y recurrencia.",
        "growth_motion": "capture_followup_close",
        "buyer": "Director de clínica dental o gerente comercial",
        "monetizes": [
          "valoración",
          "anticipo",
          "tratamiento por fases",
          "financiamiento"
        ],
        "service_bundle": [
          "valoracion rehabilitación oral",
          "plan rehabilitación oral",
          "control rehabilitación oral",
          "recall"
        ],
        "qualification_questions": [
          "es urgencia o valoracion",
          "que te preocupa mas",
          "cuando te gustaria venir",
          "necesitas facilidades de pago"
        ],
        "objections": [
          "precio",
          "miedo al dolor",
          "quiero pensarlo",
          "no puedo pagarlo completo"
        ],
        "automation_priorities": [
          "seguimiento rehabilitación oral",
          "recordatorios",
          "winback",
          "upsell"
        ],
        "kpi_pack": [
          "valoración agendada",
          "valoración asistida",
          "aceptación de tratamiento",
          "ticket por tratamiento",
          "conversion rehabilitación oral",
          "revenue rehabilitación oral"
        ],
        "recommended_commands": [
          "avisar recalls vencidos",
          "bloquear agenda de cirugia",
          "modo solo humano por urgencia",
          "reactivar seguimiento de presupuestos"
        ],
        "launch_assets": [
          "guion whatsapp",
          "playbook de handoff",
          "servicios seed",
          "templates seed"
        ],
        "templates": [
          {
            "key": "rehabilitación-oral-lead",
            "title": "Captacion rehabilitación oral",
            "content": "Hola, te ayudo con rehabilitación oral. Si quieres, te hago 3 preguntas y te propongo el siguiente paso ideal."
          },
          {
            "key": "rehabilitación-oral-followup",
            "title": "Seguimiento rehabilitación oral",
            "content": "Te sigo con rehabilitación oral. Si quieres, hoy mismo te propongo horario, paquete o siguiente accion."
          },
          {
            "key": "rehabilitación-oral-reactivation",
            "title": "Reactivacion rehabilitación oral",
            "content": "Te escribo porque todavia podemos mover rehabilitación oral a una accion concreta esta semana. ¿Quieres que te lo aterrice a tu caso?"
          }
        ],
        "behavior_overrides": {
          "tone": "claro y tranquilizador",
          "sales_intensity": "media",
          "required_phrases": [
            "te lo aterrizo a tu caso de rehabilitación oral",
            "te sigo para moverlo al siguiente paso"
          ],
          "fallback_message": "Te ayudo con rehabilitación oral. Si quieres, te hago unas preguntas rapidas y te recomiendo el siguiente paso."
        }
      },
      {
        "id": "cirugía-dental",
        "name": "cirugía dental",
        "strength_score": 81,
        "promise": "Convertir conversaciones de cirugía dental en siguiente paso claro, cobro y recurrencia.",
        "growth_motion": "capture_followup_close",
        "buyer": "Director de clínica dental o gerente comercial",
        "monetizes": [
          "valoración",
          "anticipo",
          "tratamiento por fases",
          "financiamiento"
        ],
        "service_bundle": [
          "valoracion cirugía dental",
          "plan cirugía dental",
          "control cirugía dental",
          "recall"
        ],
        "qualification_questions": [
          "es urgencia o valoracion",
          "que te preocupa mas",
          "cuando te gustaria venir",
          "necesitas facilidades de pago"
        ],
        "objections": [
          "precio",
          "miedo al dolor",
          "quiero pensarlo",
          "no puedo pagarlo completo"
        ],
        "automation_priorities": [
          "seguimiento cirugía dental",
          "recordatorios",
          "winback",
          "upsell"
        ],
        "kpi_pack": [
          "valoración agendada",
          "valoración asistida",
          "aceptación de tratamiento",
          "ticket por tratamiento",
          "conversion cirugía dental",
          "revenue cirugía dental"
        ],
        "recommended_commands": [
          "avisar recalls vencidos",
          "bloquear agenda de cirugia",
          "modo solo humano por urgencia",
          "reactivar seguimiento de presupuestos"
        ],
        "launch_assets": [
          "guion whatsapp",
          "playbook de handoff",
          "servicios seed",
          "templates seed"
        ],
        "templates": [
          {
            "key": "cirugía-dental-lead",
            "title": "Captacion cirugía dental",
            "content": "Hola, te ayudo con cirugía dental. Si quieres, te hago 3 preguntas y te propongo el siguiente paso ideal."
          },
          {
            "key": "cirugía-dental-followup",
            "title": "Seguimiento cirugía dental",
            "content": "Te sigo con cirugía dental. Si quieres, hoy mismo te propongo horario, paquete o siguiente accion."
          },
          {
            "key": "cirugía-dental-reactivation",
            "title": "Reactivacion cirugía dental",
            "content": "Te escribo porque todavia podemos mover cirugía dental a una accion concreta esta semana. ¿Quieres que te lo aterrice a tu caso?"
          }
        ],
        "behavior_overrides": {
          "tone": "claro y tranquilizador",
          "sales_intensity": "media",
          "required_phrases": [
            "te lo aterrizo a tu caso de cirugía dental",
            "te sigo para moverlo al siguiente paso"
          ],
          "fallback_message": "Te ayudo con cirugía dental. Si quieres, te hago unas preguntas rapidas y te recomiendo el siguiente paso."
        }
      }
    ],
    "ten_x_operational_pack": {
      "recommended_commands": [
        "avisar recalls vencidos",
        "bloquear agenda de cirugia",
        "modo solo humano por urgencia",
        "reactivar seguimiento de presupuestos"
      ],
      "launch_sequence": [
        "escoger subvertical",
        "aplicar pack",
        "simular conversaciones",
        "publicar y medir"
      ],
      "why_this_vertical": "WAOS Dental gana cuando convierte valoracion en tratamiento por fases, anticipo, documentos y recall."
    }
  },
  {
    "id": "aesthetic",
    "name": "WAOS Aesthetic",
    "short_name": "Medicina estetica & wellness premium",
    "description": "Sistema operativo conversacional para medicina estética y wellness premium.",
    "problem": "Estética pierde valor por mala respuesta inicial, poca confianza, poco seguimiento, baja venta de paquete y casi nada de mantenimiento sistemático.",
    "subverticals": [
      "medicina estética",
      "med spa",
      "depilación láser",
      "faciales avanzados",
      "contouring corporal",
      "skin clinic",
      "anti-aging",
      "rejuvenecimiento",
      "aparatología estética",
      "wellness premium"
    ],
    "objects": [
      "sede",
      "especialista",
      "valoración",
      "tratamiento",
      "zona corporal/facial",
      "contraindicaciones básicas",
      "sesión",
      "paquete",
      "anticipo",
      "aftercare",
      "mantenimiento",
      "paciente estético",
      "objetivo estético",
      "elegibilidad",
      "contraindicaciones",
      "tratamiento recomendado",
      "paquete de sesiones"
    ],
    "flows": [
      "interés -> valoración",
      "valoración -> paquete",
      "sesión -> aftercare",
      "mantenimiento -> recompra"
    ],
    "kpis": [
      "lead a valoración",
      "valoración a paquete",
      "anticipo cobrado",
      "rebook",
      "mantenimiento",
      "recompra",
      "booking a valoración",
      "aceptación de paquete",
      "valor de mantenimiento",
      "recompra a 30/60/90 días"
    ],
    "recommended_integrations": [
      "whatsapp",
      "google_calendar",
      "payments",
      "crm",
      "media",
      "promotions"
    ],
    "default_services": [
      "valoracion estetica",
      "facial avanzado",
      "depilacion laser",
      "paquete de sesiones",
      "mantenimiento mensual"
    ],
    "default_faqs": [
      {
        "q": "¿Que tratamiento me conviene?",
        "a": "Podemos orientarte segun objetivo y agendar valoracion para definir elegibilidad."
      },
      {
        "q": "¿Cuantas sesiones se necesitan?",
        "a": "Depende del caso; el bot puede explicarte el flujo general y ayudarte a reservar valoracion."
      },
      {
        "q": "¿Tienen paquetes?",
        "a": "Si, podemos sugerir paquetes y mantenimiento cuando encajan contigo."
      },
      {
        "q": "¿Dan cuidados posteriores?",
        "a": "Si, enviamos instrucciones previas y aftercare despues de cada sesion."
      }
    ],
    "behavior": {
      "tone": "premium y consultivo",
      "response_length": "media",
      "use_emojis": false,
      "sales_intensity": "alta",
      "offer_promotions_when": "after_interest_confirmed",
      "escalate_when": [
        "contraindicacion",
        "reaccion adversa",
        "inconformidad"
      ],
      "insistence_policy": "respectful",
      "can_share_price_directly": true,
      "can_negotiate": false,
      "can_mention_stock": false,
      "auto_send_images": true,
      "bot_mode": "consultivo_premium",
      "active_channels": [
        "whatsapp",
        "instagram_dm",
        "webchat"
      ],
      "forbidden_topics": [
        "promesas medicas absolutas",
        "diagnostico clinico definitivo"
      ],
      "required_phrases": [
        "primero validamos elegibilidad",
        "puedo ayudarte a reservar tu valoracion",
        "te sigo",
        "si la pregunta viene rara, igual te la aterrizo",
        "te lo aterrizo a tu caso"
      ],
      "fallback_message": "Te ayudo a identificar el tratamiento o paquete que mejor encaja contigo y a reservar tu valoracion. Si la pregunta viene rara, en broma o medio fuera de tema, igual te sigo y la aterrizamos al negocio.",
      "humor_policy": "light_contextual",
      "strange_question_policy": "respond_validate_reframe_sell_move"
    },
    "followup_rules": [
      {
        "type": "no_response",
        "delay_minutes": 90,
        "max_attempts": 2,
        "message_template": "¿Quieres que te recomiende el tratamiento adecuado o que apartemos tu valoracion?"
      },
      {
        "type": "post_quote",
        "delay_minutes": 1440,
        "max_attempts": 2,
        "message_template": "Sigo pendiente para ayudarte a elegir tu paquete o resolver dudas antes de reservar."
      },
      {
        "type": "reactivation",
        "delay_minutes": 20160,
        "max_attempts": 1,
        "message_template": "Ya toca mantenimiento o siguiente sesion. ¿Quieres que te comparta horarios disponibles?"
      }
    ],
    "templates": [
      {
        "template_key": "valuation_premium",
        "title": "Valoracion premium",
        "content": "Gracias por escribir a {{business_name}}. Te ayudo a revisar objetivo, elegibilidad y la mejor opcion para tu valoracion.",
        "variables": [
          "business_name"
        ]
      },
      {
        "template_key": "package_offer",
        "title": "Oferta de paquete",
        "content": "Con base en tu objetivo, el paquete {{package_name}} suele dar mejor seguimiento que una sola sesion. ¿Quieres que te comparta detalles?",
        "variables": [
          "package_name"
        ]
      },
      {
        "template_key": "precare",
        "title": "Instrucciones previas",
        "content": "Antes de tu cita, te comparto estas recomendaciones previas para que llegues lista/o al tratamiento.",
        "variables": []
      },
      {
        "template_key": "aftercare",
        "title": "Aftercare",
        "content": "Te comparto los cuidados posteriores recomendados para tu tratamiento de hoy. Si notas algo fuera de lo esperado, te canalizo con el especialista.",
        "variables": []
      },
      {
        "template_key": "maintenance",
        "title": "Mantenimiento",
        "content": "Tu mantenimiento recomendado ya esta cerca. ¿Quieres que te comparta horarios o el paquete vigente?",
        "variables": []
      }
    ],
    "config_overrides": {
      "objective_secondary": [
        "agendar",
        "upsell",
        "reactivar"
      ],
      "policies": [
        "No prometer resultados garantizados",
        "Escalar contraindicaciones y reacciones"
      ],
      "can_say": [
        "tratamientos",
        "sesiones",
        "paquetes",
        "aftercare",
        "mantenimiento"
      ],
      "cannot_say": [
        "diagnostico definitivo",
        "promesas clinicas",
        "indicaciones medicas complejas"
      ],
      "whatsapp_flows": [
        "valoracion_estetica",
        "venta_paquete",
        "aftercare",
        "mantenimiento"
      ],
      "appointment_duration_minutes": 35,
      "handoff_keywords": [
        "contraindicacion",
        "alergia",
        "reaccion",
        "queja"
      ],
      "high_score_threshold": 82
    },
    "portfolio_tier": "tier_1",
    "master_thesis": "Sistema operativo conversacional para medicina estética y wellness premium que convierte leads aspiracionales en valoración, paquete, sesiones, mantenimiento y recompra.",
    "buyer": {
      "primary": "Dueño o gerente comercial de clínica estética / med spa",
      "secondary": [
        "coordinación comercial",
        "recepción premium",
        "especialistas"
      ]
    },
    "one_pager": {
      "headline": "WAOS Aesthetic",
      "thesis": "WhatsApp se vuelve un proceso consultivo premium que conduce al lead desde curiosidad hasta paquete, sesión y mantenimiento.",
      "problem": "Mucho lead pregunta antes de comprar y se enfría si no hay seguimiento, confianza y estructura comercial.",
      "promise": "Cada conversación termina en una siguiente acción clara: valoración, anticipo, sesión, paquete o mantenimiento.",
      "monetizes": [
        "valoración",
        "sesión individual",
        "paquete",
        "anticipo",
        "planes de mantenimiento",
        "cross-sell"
      ],
      "packaging": [
        "setup aesthetic premium",
        "playbook por tratamiento",
        "valoración + paquetes + aftercare",
        "operación mensual de recompra"
      ],
      "strategic_care": "Vertical muy natural para WAOS; conviene venderla como revenue engine consultivo, cuidando mucho promesas y elegibilidad."
    },
    "demo_flow": [
      "El lead entra por precio, resultados, dolor, sesiones o si es candidato.",
      "WAOS identifica objetivo estético, ticket potencial y necesidad de valoración.",
      "Recomienda valoración o tratamiento inicial y cobra anticipo.",
      "Confirma cita y comparte preparación previa.",
      "Después de la sesión envía aftercare y propone siguiente paso.",
      "Activa mantenimiento, recompra y winback si la paciente desaparece."
    ],
    "native_objects": {
      "core": [
        "paciente",
        "especialista",
        "tratamiento",
        "zona tratada",
        "valoración",
        "paciente estético"
      ],
      "commercial": [
        "elegibilidad",
        "paquete",
        "sesión",
        "anticipo",
        "financiamiento"
      ],
      "operations": [
        "progreso",
        "aftercare",
        "mantenimiento",
        "paciente fría",
        "cross-sell"
      ]
    },
    "pipeline": {
      "primary": {
        "name": "Valoración y paquete",
        "states": [
          "lead nuevo",
          "interés detectado",
          "valoración recomendada",
          "valoración agendada",
          "valoración asistida",
          "elegible",
          "propuesta enviada",
          "paquete pendiente",
          "anticipo pagado",
          "sesión agendada",
          "tratamiento en curso",
          "mantenimiento pendiente",
          "recompra"
        ]
      },
      "secondary": [
        {
          "name": "Recurrencia estética",
          "states": [
            "post sesión",
            "rebook pendiente",
            "mantenimiento activo",
            "winback",
            "reactivada"
          ]
        }
      ]
    },
    "bot_playbook": {
      "must_do": [
        "orientar tratamiento",
        "filtrar elegibilidad básica",
        "recomendar valoración",
        "presentar paquete",
        "cobrar anticipo",
        "recordar preparación",
        "dar aftercare",
        "reactivar mantenimiento",
        "nunca quedarse seco ante bromas, preguntas raras o cambios bruscos de tema",
        "usar humor ligero cuando sume, sin sonar payaso ni poco serio",
        "validar el momento y luego reencauzar la conversacion al negocio",
        "cerrar siempre con una pregunta util o siguiente paso"
      ],
      "must_ask": [
        "objetivo estético",
        "zona de interés",
        "experiencia previa",
        "sede",
        "disponibilidad",
        "si busca valoración o cita directa",
        "que parte del negocio se esta atorando mas",
        "si quiere que se lo aterrice a su caso"
      ],
      "objections": [
        "precio",
        "miedo o dolor",
        "resultados",
        "duración",
        "número de sesiones",
        "quiero pensarlo"
      ],
      "escalate_when": [
        "contraindicaciones",
        "reacción adversa",
        "inconformidad",
        "plan premium complejo"
      ],
      "forbidden": [
        "promesas médicas absolutas",
        "diagnóstico clínico definitivo"
      ],
      "success_signals": [
        "quiero valoración",
        "soy candidata",
        "mándame paquete",
        "quiero apartar",
        "¿cómo pago?"
      ],
      "style": [
        "humor ligero",
        "manejo de preguntas raras",
        "reencuadre comercial"
      ]
    },
    "automation_sequences": [
      {
        "key": "aesthetic_valuation",
        "name": "Valoración pendiente",
        "trigger": "lead con interés confirmado",
        "goal": "cerrar valoración",
        "steps": [
          "resolver dudas",
          "ofrecer horario",
          "enviar anticipo"
        ]
      },
      {
        "key": "aesthetic_pre_session",
        "name": "Preparación previa",
        "trigger": "sesión confirmada",
        "goal": "reducir cancelaciones",
        "steps": [
          "instrucciones previas",
          "recordatorio",
          "confirmación final"
        ]
      },
      {
        "key": "aesthetic_aftercare",
        "name": "Aftercare y siguiente sesión",
        "trigger": "sesión realizada",
        "goal": "mejorar experiencia y continuidad",
        "steps": [
          "aftercare",
          "detectar molestias",
          "proponer siguiente sesión"
        ]
      },
      {
        "key": "aesthetic_maintenance",
        "name": "Mantenimiento",
        "trigger": "30/60/90 días sin sesión",
        "goal": "recompra y winback",
        "steps": [
          "recordar mantenimiento",
          "ofrecer paquete",
          "cerrar agenda"
        ]
      }
    ],
    "dashboard": {
      "north_star": "Valoración a paquete con recompra de mantenimiento.",
      "sections": [
        {
          "name": "Conversión",
          "metrics": [
            "lead a valoración",
            "valoración a paquete",
            "anticipo cobrado",
            "paquete a primera sesión"
          ]
        },
        {
          "name": "Operación",
          "metrics": [
            "asistencia a sesiones",
            "no-show",
            "tiempo entre sesiones",
            "cumplimiento de plan"
          ]
        },
        {
          "name": "Revenue",
          "metrics": [
            "revenue por tratamiento",
            "revenue por paquete",
            "mantenimiento vendido",
            "LTV por paciente"
          ]
        },
        {
          "name": "Retención",
          "metrics": [
            "rebook rate",
            "recompra",
            "inactivas reactivadas",
            "cross-sell rate"
          ]
        }
      ]
    },
    "hardening_model": {
      "goal": "Pasar de preset inteligente a sistema especialista",
      "wave": "ola_1",
      "entity_queen": "paciente estético",
      "core_common": true,
      "domain_by_vertical": true,
      "playbooks_by_subvertical": true,
      "kpis_by_vertical": true,
      "pricing_by_vertical": true,
      "journeys_by_vertical": true,
      "reusable_modules": [
        "intake / calificación",
        "agenda / recursos",
        "cotización / propuesta",
        "pago / anticipo / membresía",
        "seguimiento / recurrencia",
        "reporting vertical"
      ],
      "minimum_viable_hardening": [
        "1 entidad reina",
        "1 pipeline propio",
        "1 cotización propia",
        "1 recurrencia propia",
        "1 dashboard propio"
      ],
      "hard_checklist": [
        "tiene entidad principal propia",
        "tiene pipeline específico",
        "tiene cotización o pricing del nicho",
        "tiene agenda o recursos del nicho",
        "tiene postventa o recurrencia del nicho",
        "tiene documentos o compliance del nicho",
        "tiene KPIs del nicho",
        "tiene 3 automatizaciones que mueven dinero",
        "tiene 2 pruebas e2e de negocio",
        "tiene subplaybooks por subvertical",
        "entidad principal propia",
        "pipeline específico",
        "pricing del nicho",
        "agenda y recursos del nicho",
        "postventa o recurrencia del nicho",
        "documentos o compliance del nicho",
        "KPIs del nicho",
        "3 automatizaciones que mueven dinero",
        "2 pruebas e2e de negocio",
        "subplaybooks por subvertical",
        "runtime ejecutable por vertical"
      ]
    },
    "specialist_layers": {
      "persistent_entities": [
        "paciente estético",
        "objetivo estético",
        "elegibilidad",
        "contraindicaciones",
        "tratamiento recomendado",
        "paquete de sesiones",
        "mantenimiento",
        "aftercare"
      ],
      "business_pipeline": {
        "primary_entity": "paciente estético",
        "primary_pipeline": {
          "name": "Valoración y paquete",
          "states": [
            "lead nuevo",
            "interés detectado",
            "valoración recomendada",
            "valoración agendada",
            "valoración asistida",
            "elegible",
            "propuesta enviada",
            "paquete pendiente",
            "anticipo pagado",
            "sesión agendada",
            "tratamiento en curso",
            "mantenimiento pendiente",
            "recompra"
          ]
        },
        "secondary_pipelines": [
          {
            "name": "Recurrencia estética",
            "states": [
              "post sesión",
              "rebook pendiente",
              "mantenimiento activo",
              "winback",
              "reactivada"
            ]
          }
        ]
      },
      "pricing_and_quotes": [
        "cotización por paquete",
        "bundle con upsell",
        "mantenimiento estructurado"
      ],
      "agenda_and_resources": [
        "cabina",
        "especialista",
        "equipo",
        "agenda premium",
        "slot de seguimiento"
      ],
      "post_sale_and_recurrence": [
        "mantenimiento a 30/60/90 días",
        "seguimiento aftercare",
        "reactivación de paquete incompleto"
      ],
      "documents_compliance": [
        "consentimiento",
        "fotos de seguimiento",
        "precare",
        "aftercare"
      ],
      "kpis_that_matter": [
        "lead a valoración",
        "valoración a paquete",
        "anticipo cobrado",
        "rebook",
        "mantenimiento",
        "recompra",
        "booking a valoración",
        "aceptación de paquete",
        "valor de mantenimiento",
        "recompra a 30/60/90 días"
      ],
      "money_automations": [
        "seguimiento post valoración con paquete",
        "aftercare con recompra",
        "mantenimiento premium programado"
      ]
    },
    "domain_contract": {
      "vertical_entity_types": [
        "paciente estético",
        "objetivo estético",
        "elegibilidad",
        "contraindicaciones",
        "tratamiento recomendado",
        "paquete de sesiones",
        "mantenimiento",
        "aftercare"
      ],
      "vertical_pipeline_stages": {
        "primary": [
          "lead nuevo",
          "interés detectado",
          "valoración recomendada",
          "valoración agendada",
          "valoración asistida",
          "elegible",
          "propuesta enviada",
          "paquete pendiente",
          "anticipo pagado",
          "sesión agendada",
          "tratamiento en curso",
          "mantenimiento pendiente",
          "recompra"
        ],
        "secondary": [
          [
            "post sesión",
            "rebook pendiente",
            "mantenimiento activo",
            "winback",
            "reactivada"
          ]
        ]
      },
      "vertical_quote_types": [
        "paquete de sesiones",
        "bundle premium",
        "mantenimiento",
        "anticipo de procedimiento"
      ],
      "vertical_resource_types": [
        "cabina",
        "especialista",
        "equipo",
        "agenda premium",
        "slot de seguimiento"
      ],
      "vertical_followup_policies": [
        "mantenimiento a 30/60/90 días",
        "seguimiento aftercare",
        "reactivación de paquete incompleto"
      ],
      "vertical_kpi_definitions": [
        "lead a valoración",
        "valoración a paquete",
        "anticipo cobrado",
        "rebook",
        "mantenimiento",
        "recompra",
        "booking a valoración",
        "aceptación de paquete",
        "valor de mantenimiento",
        "recompra a 30/60/90 días"
      ],
      "vertical_playbooks": [
        "depilación",
        "facial",
        "injectables",
        "body contouring",
        "wellness premium"
      ],
      "vertical_document_types": [
        "consentimiento",
        "fotos de seguimiento",
        "precare",
        "aftercare"
      ]
    },
    "subvertical_playbooks": [
      {
        "name": "depilación",
        "focus": "Playbook operativo y comercial para depilación"
      },
      {
        "name": "facial",
        "focus": "Playbook operativo y comercial para facial"
      },
      {
        "name": "injectables",
        "focus": "Playbook operativo y comercial para injectables"
      },
      {
        "name": "body contouring",
        "focus": "Playbook operativo y comercial para body contouring"
      },
      {
        "name": "wellness premium",
        "focus": "Playbook operativo y comercial para wellness premium"
      }
    ],
    "business_e2e_tests": [
      {
        "name": "lead elegible compra paquete de sesiones tras valoración",
        "status": "designed"
      },
      {
        "name": "paciente activa mantenimiento después de aftercare",
        "status": "designed"
      }
    ],
    "vertical_runtime": {
      "pipeline_machine": {
        "primary_pipeline": "Valoración y paquete",
        "entity": "paciente estético",
        "states": [
          "lead nuevo",
          "interés detectado",
          "valoración recomendada",
          "valoración agendada",
          "valoración asistida",
          "elegible",
          "propuesta enviada",
          "paquete pendiente",
          "anticipo pagado",
          "sesión agendada",
          "tratamiento en curso",
          "mantenimiento pendiente",
          "recompra"
        ],
        "transitions": [
          {
            "from": "lead nuevo",
            "to": "interés detectado",
            "trigger": "qualification_complete",
            "business_effect": "advance opportunity"
          },
          {
            "from": "interés detectado",
            "to": "valoración recomendada",
            "trigger": "maintenance_due",
            "business_effect": "open commercial step"
          },
          {
            "from": "mantenimiento pendiente",
            "to": "recompra",
            "trigger": "successful_outcome",
            "business_effect": "realize revenue or continuity"
          },
          {
            "from": "mantenimiento pendiente",
            "to": "at_risk",
            "trigger": "eligible_confirmed",
            "business_effect": "activate retention sequence"
          }
        ],
        "at_risk_state": "at_risk",
        "closed_states": [
          "recompra"
        ]
      },
      "pricing_engine": {
        "quote_types": [
          "valoracion",
          "paquete de sesiones",
          "bundle premium",
          "mantenimiento"
        ],
        "pricing_basis": "treatment + session_count + premium add-ons + maintenance",
        "rules": [
          {
            "rule": "base price by tratamiento type",
            "effect": "set base_price"
          },
          {
            "rule": "premium or urgent add-ons increase quote",
            "effect": "add surcharge"
          },
          {
            "rule": "bundle, membership or financing can lower immediate friction",
            "effect": "recommend package or installments"
          }
        ],
        "deposit_policy": "request advance when capacity, specialist time or inventory must be secured"
      },
      "resource_capacity": {
        "resource_types": [
          "especialista",
          "cabina",
          "equipo estetico",
          "slot premium"
        ],
        "capacity_basis": "specialist, cabin, device cooldown and session duration",
        "constraints": [
          "avoid double booking of critical resources",
          "respect service duration and cleanup/buffer time",
          "prioritize higher urgency and higher close probability cases"
        ],
        "priority_queue": "cabina, elegibilidad y mantenimiento"
      },
      "recurrence_engine": {
        "policies": [
          {
            "type": "maintenance_cycle",
            "interval_days": 45,
            "anchor": "paciente estético"
          },
          {
            "type": "package_session_followup",
            "interval_days": 21,
            "anchor": "paciente estético"
          },
          {
            "type": "aftercare_review",
            "interval_days": 3,
            "anchor": "paciente estético"
          }
        ],
        "reactivation_window_days": 45,
        "goal": "protect retention, repeat revenue and continuity"
      },
      "kpi_engine": {
        "north_star": "Valoración a paquete con recompra de mantenimiento.",
        "definitions": [
          {
            "name": "valuation_to_package",
            "formula": "packages_sold / valuations_completed"
          },
          {
            "name": "maintenance_value",
            "formula": "maintenance_revenue / active_patients"
          },
          {
            "name": "repurchase_60d",
            "formula": "repurchases_60d / treated_patients"
          }
        ],
        "leading_indicators": [
          "eligible_confirmed",
          "package_pending",
          "no_response_7d"
        ]
      },
      "automation_engine": {
        "money_automation_policies": [
          {
            "trigger": "eligible_confirmed",
            "actions": [
              "send_followup",
              "escalate_owner",
              "offer_relevant_next_step"
            ],
            "goal": "save conversion or retention"
          },
          {
            "trigger": "package_pending",
            "actions": [
              "send_quote_or_payment_link",
              "remind_deadline",
              "notify_human"
            ],
            "goal": "move revenue forward"
          },
          {
            "trigger": "post_session_check",
            "actions": [
              "schedule_recurrence",
              "cross_sell_next_best_offer",
              "create_task"
            ],
            "goal": "increase LTV"
          }
        ],
        "quiet_hours": "21:00-08:00"
      },
      "document_flow": {
        "required_documents": [
          "consentimiento estetico",
          "fotos before/after",
          "contraindicaciones",
          "aftercare"
        ],
        "lifecycle_rules": [
          {
            "document": "consentimiento estetico",
            "required_before": "first committed step",
            "signature_required": true
          },
          {
            "document": "aftercare",
            "required_before": "handoff or continuity step",
            "signature_required": false
          }
        ]
      },
      "matching_engine": {
        "entity": "paciente estético",
        "rules": [
          "goal == treatment.indication",
          "contraindications == false",
          "budget_fit",
          "preferred_schedule_match"
        ],
        "next_best_match_outputs": [
          "best_owner",
          "best_resource_slot",
          "best_offer"
        ]
      }
    },
    "transactional_motor_v12": {
      "version": "v12_full_transactional",
      "aggregate_root": "aesthetic_case_account",
      "main_business_entity": "tratamiento recomendado",
      "transaction_unit": "session_cycle",
      "system_of_record": {
        "write_model": [
          "commands",
          "events",
          "ledger",
          "aggregate_snapshots"
        ],
        "read_models": [
          "commercial_board",
          "operations_board",
          "finance_board",
          "continuity_board",
          "resource_load_board",
          "document_readiness_board",
          "revenue_levers_board"
        ],
        "idempotency_scope": [
          "organization_id",
          "vertical_id",
          "external_reference",
          "command_key"
        ],
        "audit_mode": "append_only_with_snapshots"
      },
      "transaction_primitives": {
        "commands": [
          "capture_intent",
          "qualify_record",
          "create_quote",
          "request_deposit",
          "reserve_capacity",
          "confirm_booking",
          "start_case",
          "approve_quote",
          "collect_payment",
          "start_fulfillment",
          "close_fulfillment",
          "schedule_recurrence",
          "issue_refund",
          "reactivate_customer",
          "mark_eligibility",
          "sell_session_package",
          "deliver_aftercare",
          "schedule_maintenance"
        ],
        "events": [
          "intent_captured",
          "record_qualified",
          "quote_created",
          "deposit_requested",
          "capacity_reserved",
          "booking_confirmed",
          "case_started",
          "quote_approved",
          "payment_collected",
          "fulfillment_started",
          "fulfillment_closed",
          "recurrence_scheduled",
          "refund_issued",
          "customer_reactivated",
          "eligibility_confirmed",
          "package_sold",
          "aftercare_delivered",
          "maintenance_scheduled"
        ],
        "ledger_event_types": [
          "charge_opened",
          "deposit_collected",
          "installment_due",
          "payment_applied",
          "credit_issued",
          "refund_issued",
          "write_off_registered"
        ],
        "invariants": [
          "no iniciar sesión sin consentimiento",
          "no vender tratamiento contra contraindicación",
          "no cerrar paquete sin aftercare programado",
          "todo pago debe referenciar quote, order o case activo",
          "todo cambio crítico debe emitir evento y renglón de auditoría",
          "ningún recurso se confirma dos veces en la misma ventana"
        ],
        "idempotency_keys": [
          "command_key",
          "payment_reference",
          "booking_reference",
          "external_message_id"
        ]
      },
      "aggregates": {
        "primary_record": {
          "name": "tratamiento recomendado",
          "status_axis": [
            "commercial",
            "operations",
            "finance",
            "continuity"
          ]
        },
        "quote": {
          "name": "package_quote",
          "states": [
            "draft",
            "sent",
            "accepted",
            "expired",
            "lost"
          ]
        },
        "booking": {
          "name": "valuation_booking",
          "states": [
            "proposed",
            "reserved",
            "confirmed",
            "attended_or_executed",
            "missed_or_canceled"
          ]
        },
        "execution": {
          "name": "session_delivery",
          "states": [
            "pending",
            "ready",
            "in_progress",
            "blocked",
            "completed",
            "closed"
          ]
        },
        "payment_account": {
          "name": "payment_account",
          "states": [
            "open",
            "partially_paid",
            "paid",
            "overdue",
            "refunded"
          ]
        },
        "continuity": {
          "name": "maintenance_plan",
          "states": [
            "not_started",
            "active",
            "at_risk",
            "recovered",
            "closed"
          ]
        }
      },
      "orchestration": {
        "command_handlers": [
          "handle_capture_intent",
          "handle_qualify_record",
          "handle_create_quote",
          "handle_request_deposit",
          "handle_reserve_capacity",
          "handle_confirm_booking",
          "handle_start_case",
          "handle_approve_quote",
          "handle_mark_eligibility",
          "handle_sell_session_package",
          "handle_deliver_aftercare",
          "handle_schedule_maintenance"
        ],
        "sagas": [
          "eligibility_to_package",
          "aftercare_to_maintenance",
          "incident_recovery"
        ],
        "money_guards": [
          "quote_before_payment",
          "capacity_before_confirmation",
          "documents_before_execution",
          "balance_before_close"
        ],
        "read_model_refresh": [
          "on_every_event",
          "nightly_reconciliation",
          "pre_dashboard_cache"
        ]
      },
      "finance": {
        "money_objects": [
          "valuation_charge",
          "package_deposit",
          "session_collection",
          "maintenance_charge"
        ],
        "collection_modes": [
          "anticipo",
          "paquete",
          "mantenimiento"
        ],
        "refund_modes": [
          "session_credit",
          "service_recovery_credit"
        ],
        "reconciliation_views": [
          "expected_vs_collected",
          "aging_balance",
          "refund_exposure",
          "cash_by_stage"
        ]
      },
      "operations": {
        "fulfillment_unit": "session_cycle",
        "resource_locking": [
          "specialist",
          "cabina",
          "equipment_slot"
        ],
        "dispatch_or_schedule_board": [
          "queued",
          "ready",
          "assigned",
          "in_progress",
          "blocked",
          "done"
        ],
        "handoff_rules": [
          "human_handoff_on_exception",
          "supervisor_handoff_on_money_risk",
          "operator_handoff_on_compliance_gap"
        ]
      },
      "audit_compliance": {
        "timeline_entities": [
          "tratamiento recomendado",
          "package_quote",
          "valuation_booking",
          "session_delivery",
          "payment_account"
        ],
        "consent_gates": [
          "contraindication_form",
          "consentimiento_estetico",
          "photo_authorization"
        ],
        "required_evidence": [
          "timeline_event",
          "actor",
          "timestamp",
          "before_after_snapshot"
        ],
        "retention_rules": [
          "audit_log_append_only",
          "documents_linked_to_primary_record",
          "payment_trace_non_destructive"
        ]
      },
      "transaction_views": {
        "commercial": [
          "eligibility",
          "package_acceptance",
          "upsell"
        ],
        "operations": [
          "session_timeline",
          "aftercare",
          "incident_log"
        ],
        "finance": [
          "package_value",
          "maintenance_mrr",
          "balance_due"
        ],
        "continuity": [
          "rebooking",
          "maintenance",
          "recompra"
        ]
      },
      "command_catalog": [
        {
          "command": "capture_intent",
          "writes": "tratamiento recomendado",
          "emits": "intent_captured",
          "guard": "no iniciar sesión sin consentimiento"
        },
        {
          "command": "qualify_record",
          "writes": "tratamiento recomendado",
          "emits": "record_qualified",
          "guard": "no vender tratamiento contra contraindicación"
        },
        {
          "command": "create_quote",
          "writes": "tratamiento recomendado",
          "emits": "quote_created",
          "guard": "no cerrar paquete sin aftercare programado"
        },
        {
          "command": "request_deposit",
          "writes": "tratamiento recomendado",
          "emits": "deposit_requested",
          "guard": "no iniciar sesión sin consentimiento"
        },
        {
          "command": "reserve_capacity",
          "writes": "tratamiento recomendado",
          "emits": "capacity_reserved",
          "guard": "no vender tratamiento contra contraindicación"
        },
        {
          "command": "confirm_booking",
          "writes": "tratamiento recomendado",
          "emits": "booking_confirmed",
          "guard": "no cerrar paquete sin aftercare programado"
        },
        {
          "command": "start_case",
          "writes": "tratamiento recomendado",
          "emits": "case_started",
          "guard": "no iniciar sesión sin consentimiento"
        },
        {
          "command": "approve_quote",
          "writes": "tratamiento recomendado",
          "emits": "quote_approved",
          "guard": "no vender tratamiento contra contraindicación"
        },
        {
          "command": "mark_eligibility",
          "writes": "tratamiento recomendado",
          "emits": "payment_collected",
          "guard": "no cerrar paquete sin aftercare programado"
        },
        {
          "command": "sell_session_package",
          "writes": "tratamiento recomendado",
          "emits": "fulfillment_started",
          "guard": "no iniciar sesión sin consentimiento"
        },
        {
          "command": "deliver_aftercare",
          "writes": "tratamiento recomendado",
          "emits": "fulfillment_closed",
          "guard": "no vender tratamiento contra contraindicación"
        },
        {
          "command": "schedule_maintenance",
          "writes": "tratamiento recomendado",
          "emits": "recurrence_scheduled",
          "guard": "no cerrar paquete sin aftercare programado"
        }
      ],
      "event_catalog": [
        {
          "event": "intent_captured",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "eligibility_to_package"
        },
        {
          "event": "record_qualified",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "aftercare_to_maintenance"
        },
        {
          "event": "quote_created",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "incident_recovery"
        },
        {
          "event": "deposit_requested",
          "updates": [
            "timeline",
            "boards",
            "ledger"
          ],
          "next_action": "eligibility_to_package"
        },
        {
          "event": "capacity_reserved",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "aftercare_to_maintenance"
        },
        {
          "event": "booking_confirmed",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "incident_recovery"
        },
        {
          "event": "case_started",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "eligibility_to_package"
        },
        {
          "event": "quote_approved",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "aftercare_to_maintenance"
        },
        {
          "event": "eligibility_confirmed",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "incident_recovery"
        },
        {
          "event": "package_sold",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "eligibility_to_package"
        },
        {
          "event": "aftercare_delivered",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "aftercare_to_maintenance"
        },
        {
          "event": "maintenance_scheduled",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "incident_recovery"
        }
      ]
    },
    "is_strongest_vertical": true,
    "strongest_rank": 3,
    "ten_x_score": 97,
    "ten_x_narrative": "WAOS Aesthetic gana cuando sube valor percibido, vende paquete, sostiene aftercare y crea mantenimiento.",
    "ten_x_growth_loops": [
      "lead aspiracional a valoracion",
      "valoracion a paquete",
      "sesion a recompras",
      "aftercare a mantenimiento"
    ],
    "recommended_subverticals": [
      "medicina estética",
      "med spa",
      "depilación láser",
      "faciales avanzados"
    ],
    "subvertical_profiles": [
      {
        "id": "medicina-estética",
        "name": "medicina estética",
        "strength_score": 97,
        "promise": "Convertir conversaciones de medicina estética en siguiente paso claro, cobro y recurrencia.",
        "growth_motion": "capture_followup_close",
        "buyer": "Dueño o gerente comercial de clínica estética / med spa",
        "monetizes": [
          "valoración",
          "sesión individual",
          "paquete",
          "anticipo"
        ],
        "service_bundle": [
          "valoracion medicina estética",
          "sesion medicina estética",
          "paquete medicina estética",
          "mantenimiento"
        ],
        "qualification_questions": [
          "que objetivo buscas",
          "ya te has hecho algo parecido",
          "cuando quieres empezar",
          "prefieres sesion o paquete"
        ],
        "objections": [
          "precio",
          "miedo o dolor",
          "resultados",
          "duración"
        ],
        "automation_priorities": [
          "seguimiento medicina estética",
          "recordatorios",
          "winback",
          "upsell"
        ],
        "kpi_pack": [
          "lead a valoración",
          "valoración a paquete",
          "anticipo cobrado",
          "rebook",
          "conversion medicina estética",
          "revenue medicina estética"
        ],
        "recommended_commands": [
          "abrir bloque premium",
          "avisar sesiones de mantenimiento",
          "pausar promo especifica",
          "solo humano por contraindicacion"
        ],
        "launch_assets": [
          "guion whatsapp",
          "playbook de handoff",
          "servicios seed",
          "templates seed"
        ],
        "templates": [
          {
            "key": "medicina-estética-lead",
            "title": "Captacion medicina estética",
            "content": "Hola, te ayudo con medicina estética. Si quieres, te hago 3 preguntas y te propongo el siguiente paso ideal."
          },
          {
            "key": "medicina-estética-followup",
            "title": "Seguimiento medicina estética",
            "content": "Te sigo con medicina estética. Si quieres, hoy mismo te propongo horario, paquete o siguiente accion."
          },
          {
            "key": "medicina-estética-reactivation",
            "title": "Reactivacion medicina estética",
            "content": "Te escribo porque todavia podemos mover medicina estética a una accion concreta esta semana. ¿Quieres que te lo aterrice a tu caso?"
          }
        ],
        "behavior_overrides": {
          "tone": "premium y consultivo",
          "sales_intensity": "alta",
          "required_phrases": [
            "te lo aterrizo a tu caso de medicina estética",
            "te sigo para moverlo al siguiente paso"
          ],
          "fallback_message": "Te ayudo con medicina estética. Si quieres, te hago unas preguntas rapidas y te recomiendo el siguiente paso."
        }
      },
      {
        "id": "med-spa",
        "name": "med spa",
        "strength_score": 95,
        "promise": "Vender valoracion premium y paquetes de mayor margen con seguimiento elegante.",
        "growth_motion": "premium_package",
        "buyer": "Dueño o gerente comercial de clínica estética / med spa",
        "monetizes": [
          "valoración",
          "sesión individual",
          "paquete",
          "anticipo"
        ],
        "service_bundle": [
          "valoracion premium",
          "paquete body",
          "paquete facial",
          "mantenimiento"
        ],
        "qualification_questions": [
          "que objetivo buscas",
          "ya te has hecho algo parecido",
          "cuando quieres empezar",
          "prefieres sesion o paquete"
        ],
        "objections": [
          "quiero saber si soy candidata",
          "esta caro",
          "me da miedo un mal resultado",
          "quiero verlo despues"
        ],
        "automation_priorities": [
          "seguimiento med spa",
          "recordatorios",
          "winback",
          "upsell"
        ],
        "kpi_pack": [
          "lead a valoración",
          "valoración a paquete",
          "anticipo cobrado",
          "rebook",
          "conversion med spa",
          "revenue med spa"
        ],
        "recommended_commands": [
          "abrir bloque premium",
          "avisar sesiones de mantenimiento",
          "pausar promo especifica",
          "solo humano por contraindicacion"
        ],
        "launch_assets": [
          "guion whatsapp",
          "playbook de handoff",
          "servicios seed",
          "templates seed"
        ],
        "templates": [
          {
            "key": "med-spa-lead",
            "title": "Captacion med spa",
            "content": "Hola, te ayudo con med spa. Si quieres, te hago 3 preguntas y te propongo el siguiente paso ideal."
          },
          {
            "key": "med-spa-followup",
            "title": "Seguimiento med spa",
            "content": "Te sigo con med spa. Si quieres, hoy mismo te propongo horario, paquete o siguiente accion."
          },
          {
            "key": "med-spa-reactivation",
            "title": "Reactivacion med spa",
            "content": "Te escribo porque todavia podemos mover med spa a una accion concreta esta semana. ¿Quieres que te lo aterrice a tu caso?"
          }
        ],
        "behavior_overrides": {
          "tone": "premium y consultivo",
          "sales_intensity": "alta",
          "required_phrases": [
            "te lo aterrizo a tu caso de med spa",
            "te sigo para moverlo al siguiente paso"
          ],
          "fallback_message": "Te ayudo con med spa. Si quieres, te hago unas preguntas rapidas y te recomiendo el siguiente paso."
        }
      },
      {
        "id": "depilación-láser",
        "name": "depilación láser",
        "strength_score": 93,
        "promise": "Convertir conversaciones de depilación láser en siguiente paso claro, cobro y recurrencia.",
        "growth_motion": "capture_followup_close",
        "buyer": "Dueño o gerente comercial de clínica estética / med spa",
        "monetizes": [
          "valoración",
          "sesión individual",
          "paquete",
          "anticipo"
        ],
        "service_bundle": [
          "valoracion depilación láser",
          "sesion depilación láser",
          "paquete depilación láser",
          "mantenimiento"
        ],
        "qualification_questions": [
          "que objetivo buscas",
          "ya te has hecho algo parecido",
          "cuando quieres empezar",
          "prefieres sesion o paquete"
        ],
        "objections": [
          "precio",
          "miedo o dolor",
          "resultados",
          "duración"
        ],
        "automation_priorities": [
          "seguimiento depilación láser",
          "recordatorios",
          "winback",
          "upsell"
        ],
        "kpi_pack": [
          "lead a valoración",
          "valoración a paquete",
          "anticipo cobrado",
          "rebook",
          "conversion depilación láser",
          "revenue depilación láser"
        ],
        "recommended_commands": [
          "abrir bloque premium",
          "avisar sesiones de mantenimiento",
          "pausar promo especifica",
          "solo humano por contraindicacion"
        ],
        "launch_assets": [
          "guion whatsapp",
          "playbook de handoff",
          "servicios seed",
          "templates seed"
        ],
        "templates": [
          {
            "key": "depilación-láser-lead",
            "title": "Captacion depilación láser",
            "content": "Hola, te ayudo con depilación láser. Si quieres, te hago 3 preguntas y te propongo el siguiente paso ideal."
          },
          {
            "key": "depilación-láser-followup",
            "title": "Seguimiento depilación láser",
            "content": "Te sigo con depilación láser. Si quieres, hoy mismo te propongo horario, paquete o siguiente accion."
          },
          {
            "key": "depilación-láser-reactivation",
            "title": "Reactivacion depilación láser",
            "content": "Te escribo porque todavia podemos mover depilación láser a una accion concreta esta semana. ¿Quieres que te lo aterrice a tu caso?"
          }
        ],
        "behavior_overrides": {
          "tone": "premium y consultivo",
          "sales_intensity": "alta",
          "required_phrases": [
            "te lo aterrizo a tu caso de depilación láser",
            "te sigo para moverlo al siguiente paso"
          ],
          "fallback_message": "Te ayudo con depilación láser. Si quieres, te hago unas preguntas rapidas y te recomiendo el siguiente paso."
        }
      },
      {
        "id": "faciales-avanzados",
        "name": "faciales avanzados",
        "strength_score": 91,
        "promise": "Convertir conversaciones de faciales avanzados en siguiente paso claro, cobro y recurrencia.",
        "growth_motion": "capture_followup_close",
        "buyer": "Dueño o gerente comercial de clínica estética / med spa",
        "monetizes": [
          "valoración",
          "sesión individual",
          "paquete",
          "anticipo"
        ],
        "service_bundle": [
          "valoracion faciales avanzados",
          "sesion faciales avanzados",
          "paquete faciales avanzados",
          "mantenimiento"
        ],
        "qualification_questions": [
          "que objetivo buscas",
          "ya te has hecho algo parecido",
          "cuando quieres empezar",
          "prefieres sesion o paquete"
        ],
        "objections": [
          "precio",
          "miedo o dolor",
          "resultados",
          "duración"
        ],
        "automation_priorities": [
          "seguimiento faciales avanzados",
          "recordatorios",
          "winback",
          "upsell"
        ],
        "kpi_pack": [
          "lead a valoración",
          "valoración a paquete",
          "anticipo cobrado",
          "rebook",
          "conversion faciales avanzados",
          "revenue faciales avanzados"
        ],
        "recommended_commands": [
          "abrir bloque premium",
          "avisar sesiones de mantenimiento",
          "pausar promo especifica",
          "solo humano por contraindicacion"
        ],
        "launch_assets": [
          "guion whatsapp",
          "playbook de handoff",
          "servicios seed",
          "templates seed"
        ],
        "templates": [
          {
            "key": "faciales-avanzados-lead",
            "title": "Captacion faciales avanzados",
            "content": "Hola, te ayudo con faciales avanzados. Si quieres, te hago 3 preguntas y te propongo el siguiente paso ideal."
          },
          {
            "key": "faciales-avanzados-followup",
            "title": "Seguimiento faciales avanzados",
            "content": "Te sigo con faciales avanzados. Si quieres, hoy mismo te propongo horario, paquete o siguiente accion."
          },
          {
            "key": "faciales-avanzados-reactivation",
            "title": "Reactivacion faciales avanzados",
            "content": "Te escribo porque todavia podemos mover faciales avanzados a una accion concreta esta semana. ¿Quieres que te lo aterrice a tu caso?"
          }
        ],
        "behavior_overrides": {
          "tone": "premium y consultivo",
          "sales_intensity": "alta",
          "required_phrases": [
            "te lo aterrizo a tu caso de faciales avanzados",
            "te sigo para moverlo al siguiente paso"
          ],
          "fallback_message": "Te ayudo con faciales avanzados. Si quieres, te hago unas preguntas rapidas y te recomiendo el siguiente paso."
        }
      },
      {
        "id": "contouring-corporal",
        "name": "contouring corporal",
        "strength_score": 89,
        "promise": "Llevar una expectativa aspiracional a un plan realista y mantenible.",
        "growth_motion": "expectation_to_plan",
        "buyer": "Dueño o gerente comercial de clínica estética / med spa",
        "monetizes": [
          "valoración",
          "sesión individual",
          "paquete",
          "anticipo"
        ],
        "service_bundle": [
          "valoracion corporal",
          "paquete contouring",
          "seguimiento fotografico",
          "mantenimiento"
        ],
        "qualification_questions": [
          "que objetivo buscas",
          "ya te has hecho algo parecido",
          "cuando quieres empezar",
          "prefieres sesion o paquete"
        ],
        "objections": [
          "quiero resultados rapidos",
          "no se si funcione",
          "esta caro",
          "solo quiero informacion"
        ],
        "automation_priorities": [
          "seguimiento contouring corporal",
          "recordatorios",
          "winback",
          "upsell"
        ],
        "kpi_pack": [
          "lead a valoración",
          "valoración a paquete",
          "anticipo cobrado",
          "rebook",
          "conversion contouring corporal",
          "revenue contouring corporal"
        ],
        "recommended_commands": [
          "abrir bloque premium",
          "avisar sesiones de mantenimiento",
          "pausar promo especifica",
          "solo humano por contraindicacion"
        ],
        "launch_assets": [
          "guion whatsapp",
          "playbook de handoff",
          "servicios seed",
          "templates seed"
        ],
        "templates": [
          {
            "key": "contouring-corporal-lead",
            "title": "Captacion contouring corporal",
            "content": "Hola, te ayudo con contouring corporal. Si quieres, te hago 3 preguntas y te propongo el siguiente paso ideal."
          },
          {
            "key": "contouring-corporal-followup",
            "title": "Seguimiento contouring corporal",
            "content": "Te sigo con contouring corporal. Si quieres, hoy mismo te propongo horario, paquete o siguiente accion."
          },
          {
            "key": "contouring-corporal-reactivation",
            "title": "Reactivacion contouring corporal",
            "content": "Te escribo porque todavia podemos mover contouring corporal a una accion concreta esta semana. ¿Quieres que te lo aterrice a tu caso?"
          }
        ],
        "behavior_overrides": {
          "tone": "premium y consultivo",
          "sales_intensity": "alta",
          "required_phrases": [
            "te lo aterrizo a tu caso de contouring corporal",
            "te sigo para moverlo al siguiente paso"
          ],
          "fallback_message": "Te ayudo con contouring corporal. Si quieres, te hago unas preguntas rapidas y te recomiendo el siguiente paso."
        }
      },
      {
        "id": "skin-clinic",
        "name": "skin clinic",
        "strength_score": 87,
        "promise": "Convertir conversaciones de skin clinic en siguiente paso claro, cobro y recurrencia.",
        "growth_motion": "capture_followup_close",
        "buyer": "Dueño o gerente comercial de clínica estética / med spa",
        "monetizes": [
          "valoración",
          "sesión individual",
          "paquete",
          "anticipo"
        ],
        "service_bundle": [
          "valoracion skin clinic",
          "sesion skin clinic",
          "paquete skin clinic",
          "mantenimiento"
        ],
        "qualification_questions": [
          "que objetivo buscas",
          "ya te has hecho algo parecido",
          "cuando quieres empezar",
          "prefieres sesion o paquete"
        ],
        "objections": [
          "precio",
          "miedo o dolor",
          "resultados",
          "duración"
        ],
        "automation_priorities": [
          "seguimiento skin clinic",
          "recordatorios",
          "winback",
          "upsell"
        ],
        "kpi_pack": [
          "lead a valoración",
          "valoración a paquete",
          "anticipo cobrado",
          "rebook",
          "conversion skin clinic",
          "revenue skin clinic"
        ],
        "recommended_commands": [
          "abrir bloque premium",
          "avisar sesiones de mantenimiento",
          "pausar promo especifica",
          "solo humano por contraindicacion"
        ],
        "launch_assets": [
          "guion whatsapp",
          "playbook de handoff",
          "servicios seed",
          "templates seed"
        ],
        "templates": [
          {
            "key": "skin-clinic-lead",
            "title": "Captacion skin clinic",
            "content": "Hola, te ayudo con skin clinic. Si quieres, te hago 3 preguntas y te propongo el siguiente paso ideal."
          },
          {
            "key": "skin-clinic-followup",
            "title": "Seguimiento skin clinic",
            "content": "Te sigo con skin clinic. Si quieres, hoy mismo te propongo horario, paquete o siguiente accion."
          },
          {
            "key": "skin-clinic-reactivation",
            "title": "Reactivacion skin clinic",
            "content": "Te escribo porque todavia podemos mover skin clinic a una accion concreta esta semana. ¿Quieres que te lo aterrice a tu caso?"
          }
        ],
        "behavior_overrides": {
          "tone": "premium y consultivo",
          "sales_intensity": "alta",
          "required_phrases": [
            "te lo aterrizo a tu caso de skin clinic",
            "te sigo para moverlo al siguiente paso"
          ],
          "fallback_message": "Te ayudo con skin clinic. Si quieres, te hago unas preguntas rapidas y te recomiendo el siguiente paso."
        }
      },
      {
        "id": "anti-aging",
        "name": "anti-aging",
        "strength_score": 85,
        "promise": "Convertir conversaciones de anti-aging en siguiente paso claro, cobro y recurrencia.",
        "growth_motion": "capture_followup_close",
        "buyer": "Dueño o gerente comercial de clínica estética / med spa",
        "monetizes": [
          "valoración",
          "sesión individual",
          "paquete",
          "anticipo"
        ],
        "service_bundle": [
          "valoracion anti-aging",
          "sesion anti-aging",
          "paquete anti-aging",
          "mantenimiento"
        ],
        "qualification_questions": [
          "que objetivo buscas",
          "ya te has hecho algo parecido",
          "cuando quieres empezar",
          "prefieres sesion o paquete"
        ],
        "objections": [
          "precio",
          "miedo o dolor",
          "resultados",
          "duración"
        ],
        "automation_priorities": [
          "seguimiento anti-aging",
          "recordatorios",
          "winback",
          "upsell"
        ],
        "kpi_pack": [
          "lead a valoración",
          "valoración a paquete",
          "anticipo cobrado",
          "rebook",
          "conversion anti-aging",
          "revenue anti-aging"
        ],
        "recommended_commands": [
          "abrir bloque premium",
          "avisar sesiones de mantenimiento",
          "pausar promo especifica",
          "solo humano por contraindicacion"
        ],
        "launch_assets": [
          "guion whatsapp",
          "playbook de handoff",
          "servicios seed",
          "templates seed"
        ],
        "templates": [
          {
            "key": "anti-aging-lead",
            "title": "Captacion anti-aging",
            "content": "Hola, te ayudo con anti-aging. Si quieres, te hago 3 preguntas y te propongo el siguiente paso ideal."
          },
          {
            "key": "anti-aging-followup",
            "title": "Seguimiento anti-aging",
            "content": "Te sigo con anti-aging. Si quieres, hoy mismo te propongo horario, paquete o siguiente accion."
          },
          {
            "key": "anti-aging-reactivation",
            "title": "Reactivacion anti-aging",
            "content": "Te escribo porque todavia podemos mover anti-aging a una accion concreta esta semana. ¿Quieres que te lo aterrice a tu caso?"
          }
        ],
        "behavior_overrides": {
          "tone": "premium y consultivo",
          "sales_intensity": "alta",
          "required_phrases": [
            "te lo aterrizo a tu caso de anti-aging",
            "te sigo para moverlo al siguiente paso"
          ],
          "fallback_message": "Te ayudo con anti-aging. Si quieres, te hago unas preguntas rapidas y te recomiendo el siguiente paso."
        }
      },
      {
        "id": "rejuvenecimiento",
        "name": "rejuvenecimiento",
        "strength_score": 83,
        "promise": "Convertir conversaciones de rejuvenecimiento en siguiente paso claro, cobro y recurrencia.",
        "growth_motion": "capture_followup_close",
        "buyer": "Dueño o gerente comercial de clínica estética / med spa",
        "monetizes": [
          "valoración",
          "sesión individual",
          "paquete",
          "anticipo"
        ],
        "service_bundle": [
          "valoracion rejuvenecimiento",
          "sesion rejuvenecimiento",
          "paquete rejuvenecimiento",
          "mantenimiento"
        ],
        "qualification_questions": [
          "que objetivo buscas",
          "ya te has hecho algo parecido",
          "cuando quieres empezar",
          "prefieres sesion o paquete"
        ],
        "objections": [
          "precio",
          "miedo o dolor",
          "resultados",
          "duración"
        ],
        "automation_priorities": [
          "seguimiento rejuvenecimiento",
          "recordatorios",
          "winback",
          "upsell"
        ],
        "kpi_pack": [
          "lead a valoración",
          "valoración a paquete",
          "anticipo cobrado",
          "rebook",
          "conversion rejuvenecimiento",
          "revenue rejuvenecimiento"
        ],
        "recommended_commands": [
          "abrir bloque premium",
          "avisar sesiones de mantenimiento",
          "pausar promo especifica",
          "solo humano por contraindicacion"
        ],
        "launch_assets": [
          "guion whatsapp",
          "playbook de handoff",
          "servicios seed",
          "templates seed"
        ],
        "templates": [
          {
            "key": "rejuvenecimiento-lead",
            "title": "Captacion rejuvenecimiento",
            "content": "Hola, te ayudo con rejuvenecimiento. Si quieres, te hago 3 preguntas y te propongo el siguiente paso ideal."
          },
          {
            "key": "rejuvenecimiento-followup",
            "title": "Seguimiento rejuvenecimiento",
            "content": "Te sigo con rejuvenecimiento. Si quieres, hoy mismo te propongo horario, paquete o siguiente accion."
          },
          {
            "key": "rejuvenecimiento-reactivation",
            "title": "Reactivacion rejuvenecimiento",
            "content": "Te escribo porque todavia podemos mover rejuvenecimiento a una accion concreta esta semana. ¿Quieres que te lo aterrice a tu caso?"
          }
        ],
        "behavior_overrides": {
          "tone": "premium y consultivo",
          "sales_intensity": "alta",
          "required_phrases": [
            "te lo aterrizo a tu caso de rejuvenecimiento",
            "te sigo para moverlo al siguiente paso"
          ],
          "fallback_message": "Te ayudo con rejuvenecimiento. Si quieres, te hago unas preguntas rapidas y te recomiendo el siguiente paso."
        }
      },
      {
        "id": "aparatología-estética",
        "name": "aparatología estética",
        "strength_score": 81,
        "promise": "Convertir conversaciones de aparatología estética en siguiente paso claro, cobro y recurrencia.",
        "growth_motion": "capture_followup_close",
        "buyer": "Dueño o gerente comercial de clínica estética / med spa",
        "monetizes": [
          "valoración",
          "sesión individual",
          "paquete",
          "anticipo"
        ],
        "service_bundle": [
          "valoracion aparatología estética",
          "sesion aparatología estética",
          "paquete aparatología estética",
          "mantenimiento"
        ],
        "qualification_questions": [
          "que objetivo buscas",
          "ya te has hecho algo parecido",
          "cuando quieres empezar",
          "prefieres sesion o paquete"
        ],
        "objections": [
          "precio",
          "miedo o dolor",
          "resultados",
          "duración"
        ],
        "automation_priorities": [
          "seguimiento aparatología estética",
          "recordatorios",
          "winback",
          "upsell"
        ],
        "kpi_pack": [
          "lead a valoración",
          "valoración a paquete",
          "anticipo cobrado",
          "rebook",
          "conversion aparatología estética",
          "revenue aparatología estética"
        ],
        "recommended_commands": [
          "abrir bloque premium",
          "avisar sesiones de mantenimiento",
          "pausar promo especifica",
          "solo humano por contraindicacion"
        ],
        "launch_assets": [
          "guion whatsapp",
          "playbook de handoff",
          "servicios seed",
          "templates seed"
        ],
        "templates": [
          {
            "key": "aparatología-estética-lead",
            "title": "Captacion aparatología estética",
            "content": "Hola, te ayudo con aparatología estética. Si quieres, te hago 3 preguntas y te propongo el siguiente paso ideal."
          },
          {
            "key": "aparatología-estética-followup",
            "title": "Seguimiento aparatología estética",
            "content": "Te sigo con aparatología estética. Si quieres, hoy mismo te propongo horario, paquete o siguiente accion."
          },
          {
            "key": "aparatología-estética-reactivation",
            "title": "Reactivacion aparatología estética",
            "content": "Te escribo porque todavia podemos mover aparatología estética a una accion concreta esta semana. ¿Quieres que te lo aterrice a tu caso?"
          }
        ],
        "behavior_overrides": {
          "tone": "premium y consultivo",
          "sales_intensity": "alta",
          "required_phrases": [
            "te lo aterrizo a tu caso de aparatología estética",
            "te sigo para moverlo al siguiente paso"
          ],
          "fallback_message": "Te ayudo con aparatología estética. Si quieres, te hago unas preguntas rapidas y te recomiendo el siguiente paso."
        }
      },
      {
        "id": "wellness-premium",
        "name": "wellness premium",
        "strength_score": 79,
        "promise": "Convertir tratamientos premium en membresia o frecuencia ideal.",
        "growth_motion": "membership_frequency",
        "buyer": "Dueño o gerente comercial de clínica estética / med spa",
        "monetizes": [
          "valoración",
          "sesión individual",
          "paquete",
          "anticipo"
        ],
        "service_bundle": [
          "diagnostico wellness",
          "experiencia premium",
          "membresia mensual",
          "mantenimiento"
        ],
        "qualification_questions": [
          "que objetivo buscas",
          "ya te has hecho algo parecido",
          "cuando quieres empezar",
          "prefieres sesion o paquete"
        ],
        "objections": [
          "quiero pensarlo",
          "es lujo",
          "no tengo tiempo",
          "que incluye exactamente"
        ],
        "automation_priorities": [
          "seguimiento wellness premium",
          "recordatorios",
          "winback",
          "upsell"
        ],
        "kpi_pack": [
          "lead a valoración",
          "valoración a paquete",
          "anticipo cobrado",
          "rebook",
          "conversion wellness premium",
          "revenue wellness premium"
        ],
        "recommended_commands": [
          "abrir bloque premium",
          "avisar sesiones de mantenimiento",
          "pausar promo especifica",
          "solo humano por contraindicacion"
        ],
        "launch_assets": [
          "guion whatsapp",
          "playbook de handoff",
          "servicios seed",
          "templates seed"
        ],
        "templates": [
          {
            "key": "wellness-premium-lead",
            "title": "Captacion wellness premium",
            "content": "Hola, te ayudo con wellness premium. Si quieres, te hago 3 preguntas y te propongo el siguiente paso ideal."
          },
          {
            "key": "wellness-premium-followup",
            "title": "Seguimiento wellness premium",
            "content": "Te sigo con wellness premium. Si quieres, hoy mismo te propongo horario, paquete o siguiente accion."
          },
          {
            "key": "wellness-premium-reactivation",
            "title": "Reactivacion wellness premium",
            "content": "Te escribo porque todavia podemos mover wellness premium a una accion concreta esta semana. ¿Quieres que te lo aterrice a tu caso?"
          }
        ],
        "behavior_overrides": {
          "tone": "premium y consultivo",
          "sales_intensity": "alta",
          "required_phrases": [
            "te lo aterrizo a tu caso de wellness premium",
            "te sigo para moverlo al siguiente paso"
          ],
          "fallback_message": "Te ayudo con wellness premium. Si quieres, te hago unas preguntas rapidas y te recomiendo el siguiente paso."
        }
      }
    ],
    "ten_x_operational_pack": {
      "recommended_commands": [
        "abrir bloque premium",
        "avisar sesiones de mantenimiento",
        "pausar promo especifica",
        "solo humano por contraindicacion"
      ],
      "launch_sequence": [
        "escoger subvertical",
        "aplicar pack",
        "simular conversaciones",
        "publicar y medir"
      ],
      "why_this_vertical": "WAOS Aesthetic gana cuando sube valor percibido, vende paquete, sostiene aftercare y crea mantenimiento."
    }
  },
  {
    "id": "vet",
    "name": "WAOS Vet",
    "short_name": "Veterinaria & pet care",
    "description": "Sistema operativo conversacional para veterinarias y pet care.",
    "problem": "Veterinarias y pet care suelen mezclar salud, grooming y prevención en conversaciones separadas, perdiendo historial, recordatorios y servicios recurrentes.",
    "subverticals": [
      "clínica veterinaria",
      "hospital veterinario",
      "vacunación",
      "grooming",
      "hotel",
      "daycare",
      "rehabilitación",
      "nutrición veterinaria",
      "planes preventivos"
    ],
    "objects": [
      "mascota",
      "tutor",
      "especie",
      "raza",
      "edad",
      "vacunas",
      "plan preventivo",
      "consulta",
      "grooming",
      "próxima fecha",
      "servicio recurrente",
      "tutor / familia",
      "peso"
    ],
    "flows": [
      "registro mascota",
      "consulta o servicio",
      "seguimiento post visita",
      "plan preventivo -> renovación"
    ],
    "kpis": [
      "citas por mascota",
      "recurrencia por tutor",
      "vacunas al día",
      "grooming repetido",
      "plan preventivo",
      "reactivación",
      "renovación de plan",
      "recompra grooming",
      "ausencias"
    ],
    "recommended_integrations": [
      "whatsapp",
      "google_calendar",
      "payments",
      "crm"
    ],
    "default_services": [
      "consulta general",
      "vacunacion",
      "grooming",
      "daycare",
      "plan preventivo"
    ],
    "default_faqs": [
      {
        "q": "¿Pueden registrar a mi mascota?",
        "a": "Si, podemos registrar mascota, especie, raza y datos del tutor para dar mejor seguimiento."
      },
      {
        "q": "¿Manejan vacunas y recordatorios?",
        "a": "Si, enviamos recordatorios de vacunas, controles y servicios recurrentes."
      },
      {
        "q": "¿Puedo agendar grooming o consulta?",
        "a": "Si, el bot clasifica el motivo y te ayuda a reservar servicio o consulta."
      },
      {
        "q": "¿Tienen planes preventivos?",
        "a": "Si, podemos explicarte opciones y ayudarte a renovarlas."
      }
    ],
    "behavior": {
      "tone": "cercano y responsable",
      "response_length": "media",
      "use_emojis": false,
      "sales_intensity": "media",
      "offer_promotions_when": "after_pet_profile_completed",
      "escalate_when": [
        "urgencia",
        "accidente",
        "vomito continuo",
        "dificultad respiratoria"
      ],
      "insistence_policy": "respectful",
      "can_share_price_directly": true,
      "can_negotiate": false,
      "can_mention_stock": false,
      "auto_send_images": false,
      "bot_mode": "seguimiento_de_cuidado",
      "active_channels": [
        "whatsapp",
        "webchat"
      ],
      "forbidden_topics": [
        "diagnostico veterinario definitivo por chat"
      ],
      "required_phrases": [
        "te ayudo a registrar a tu mascota",
        "si es urgencia te canalizo con prioridad",
        "te sigo",
        "si la pregunta viene rara, igual te la aterrizo",
        "te lo aterrizo a tu caso"
      ],
      "fallback_message": "Te ayudo con consulta, grooming, vacunas o plan preventivo para tu mascota. Si la pregunta viene rara, en broma o medio fuera de tema, igual te sigo y la aterrizamos al negocio.",
      "humor_policy": "light_contextual",
      "strange_question_policy": "respond_validate_reframe_sell_move"
    },
    "followup_rules": [
      {
        "type": "no_response",
        "delay_minutes": 120,
        "max_attempts": 2,
        "message_template": "¿Quieres que agendemos consulta, grooming o revisemos la siguiente vacuna?"
      },
      {
        "type": "post_quote",
        "delay_minutes": 1440,
        "max_attempts": 1,
        "message_template": "Quedo pendiente para ayudarte con la siguiente visita o plan preventivo de tu mascota."
      },
      {
        "type": "reactivation",
        "delay_minutes": 43200,
        "max_attempts": 1,
        "message_template": "Vemos que tu mascota ya podria requerir su siguiente servicio o control. ¿Quieres que te comparta horarios?"
      }
    ],
    "templates": [
      {
        "template_key": "pet_registration",
        "title": "Registro mascota",
        "content": "Para ayudarte mejor, comparteme nombre de tu mascota, especie, raza y el motivo de consulta o servicio.",
        "variables": []
      },
      {
        "template_key": "vaccine_reminder",
        "title": "Recordatorio de vacuna",
        "content": "Tu mascota ya esta cerca de su siguiente vacuna o control. ¿Quieres que lo agendemos?",
        "variables": []
      },
      {
        "template_key": "grooming_rebook",
        "title": "Rebook grooming",
        "content": "Ya toca el siguiente grooming recomendado. Si quieres, te comparto horarios disponibles.",
        "variables": []
      },
      {
        "template_key": "post_visit",
        "title": "Seguimiento post visita",
        "content": "¿Como siguio tu mascota despues de la visita? Si notas algo fuera de lo normal, te canalizo con el equipo.",
        "variables": []
      },
      {
        "template_key": "plan_renewal",
        "title": "Renovacion plan",
        "content": "Tu plan preventivo esta por vencer. ¿Quieres que te ayude a renovarlo hoy?",
        "variables": []
      }
    ],
    "config_overrides": {
      "objective_secondary": [
        "agendar",
        "reactivar",
        "renovar"
      ],
      "policies": [
        "No emitir diagnosticos definitivos por chat",
        "Escalar urgencias veterinarias"
      ],
      "can_say": [
        "consulta",
        "vacunas",
        "grooming",
        "planes preventivos",
        "agendar"
      ],
      "cannot_say": [
        "diagnostico definitivo",
        "promesas clinicas absolutas"
      ],
      "whatsapp_flows": [
        "registro_mascota",
        "agenda_vacuna",
        "grooming_rebook",
        "renovacion_plan"
      ],
      "appointment_duration_minutes": 30,
      "handoff_keywords": [
        "urgencia",
        "respira mal",
        "accidente",
        "convulsiona"
      ],
      "high_score_threshold": 88
    },
    "portfolio_tier": "tier_2",
    "master_thesis": "Sistema operativo conversacional para veterinarias y pet care que conecta consulta, prevención, grooming, planes y recurrencia alrededor de la mascota.",
    "buyer": {
      "primary": "Dueño de clínica veterinaria o pet care",
      "secondary": [
        "recepción",
        "médicos veterinarios",
        "grooming manager"
      ]
    },
    "one_pager": {
      "headline": "WAOS Vet",
      "thesis": "WhatsApp deja de ser solo atención y se convierte en una relación continua con la mascota y su tutor.",
      "problem": "Se pierden recordatorios, continuidad clínica y recompras de grooming o planes preventivos.",
      "promise": "Cada mascota se gestiona como cuenta recurrente con próxima acción clara.",
      "monetizes": [
        "consulta",
        "vacunas",
        "grooming",
        "hotel/daycare",
        "planes preventivos",
        "nutrición"
      ],
      "packaging": [
        "setup vet + grooming",
        "historial de mascota",
        "recordatorios preventivos",
        "operación mensual de recurrencia"
      ],
      "strategic_care": "Muy buena vertical por recurrencia y conversación natural en WhatsApp, pero el diseño del bot debe escalar bien cualquier urgencia clínica."
    },
    "demo_flow": [
      "El tutor entra por síntoma, vacuna, grooming u hotel.",
      "WAOS registra mascota y clasifica el tipo de servicio.",
      "Agenda consulta o servicio y confirma.",
      "Da seguimiento post consulta o post grooming.",
      "Programa próxima fecha clave preventiva.",
      "Sugiere plan preventivo o servicio complementario y reactiva por frecuencia recomendada."
    ],
    "native_objects": {
      "core": [
        "tutor",
        "mascota",
        "especie",
        "raza",
        "edad"
      ],
      "commercial": [
        "consulta",
        "vacuna",
        "grooming",
        "hotel/daycare",
        "plan preventivo"
      ],
      "operations": [
        "historial",
        "condición especial",
        "próxima fecha",
        "recordatorio estacional",
        "renovación"
      ]
    },
    "pipeline": {
      "primary": {
        "name": "Atención y recurrencia",
        "states": [
          "lead nuevo",
          "mascota registrada",
          "servicio identificado",
          "consulta/servicio agendado",
          "confirmado",
          "asistido",
          "seguimiento post servicio",
          "plan preventivo ofrecido",
          "plan activo",
          "próxima fecha pendiente",
          "inactivo",
          "reactivado"
        ]
      },
      "secondary": [
        {
          "name": "Preventivo",
          "states": [
            "sin plan",
            "plan ofrecido",
            "plan activo",
            "renovación pendiente",
            "renovado"
          ]
        }
      ]
    },
    "bot_playbook": {
      "must_do": [
        "registrar tutor y mascota",
        "orientar tipo de servicio",
        "clasificar urgencia básica",
        "agendar",
        "recordar vacunas y controles",
        "vender plan preventivo",
        "seguir recuperación",
        "nunca quedarse seco ante bromas, preguntas raras o cambios bruscos de tema",
        "usar humor ligero cuando sume, sin sonar payaso ni poco serio",
        "validar el momento y luego reencauzar la conversacion al negocio",
        "cerrar siempre con una pregunta util o siguiente paso"
      ],
      "must_ask": [
        "especie",
        "edad",
        "motivo",
        "síntomas o servicio solicitado",
        "si ya es paciente",
        "disponibilidad",
        "que parte del negocio se esta atorando mas",
        "si quiere que se lo aterrice a su caso"
      ],
      "objections": [
        "precio",
        "solo quiero preguntar",
        "no sé si urge",
        "luego la llevo",
        "solo quiero grooming"
      ],
      "escalate_when": [
        "urgencia clínica seria",
        "hospitalización",
        "decisión médica",
        "queja fuerte"
      ],
      "forbidden": [
        "diagnóstico veterinario definitivo por chat"
      ],
      "success_signals": [
        "quiero agendar",
        "mi mascota necesita",
        "¿qué vacunas tocan?",
        "quiero grooming",
        "mándame horarios"
      ],
      "style": [
        "humor ligero",
        "manejo de preguntas raras",
        "reencuadre comercial"
      ]
    },
    "automation_sequences": [
      {
        "key": "vet_visit_confirmation",
        "name": "Confirmación de visita",
        "trigger": "consulta o servicio agendado",
        "goal": "reducir no-show",
        "steps": [
          "confirmar fecha",
          "recordatorio 24h",
          "recordatorio 2h"
        ]
      },
      {
        "key": "vet_preventive",
        "name": "Preventivo periódico",
        "trigger": "próxima vacuna o desparasitación",
        "goal": "cumplimiento preventivo",
        "steps": [
          "recordar fecha",
          "ofrecer agenda",
          "cerrar visita"
        ]
      },
      {
        "key": "vet_post_visit",
        "name": "Seguimiento post visita",
        "trigger": "consulta realizada",
        "goal": "calidad y continuidad",
        "steps": [
          "preguntar evolución",
          "escalar anomalía",
          "proponer control"
        ]
      },
      {
        "key": "vet_rebook",
        "name": "Rebook de grooming o plan",
        "trigger": "frecuencia ideal alcanzada",
        "goal": "recurrencia",
        "steps": [
          "recordatorio",
          "proponer horario",
          "cerrar servicio"
        ]
      }
    ],
    "dashboard": {
      "north_star": "Recurrencia por mascota y plan preventivo activo.",
      "sections": [
        {
          "name": "Conversión",
          "metrics": [
            "consulta agendada",
            "grooming agendado",
            "plan preventivo vendido",
            "mascota registrada"
          ]
        },
        {
          "name": "Retención",
          "metrics": [
            "vacunas al día",
            "grooming repetido",
            "plan renovado",
            "mascotas reactivadas"
          ]
        },
        {
          "name": "Revenue",
          "metrics": [
            "ticket por mascota",
            "revenue clínico",
            "revenue grooming",
            "revenue preventivo"
          ]
        },
        {
          "name": "Operación",
          "metrics": [
            "no-show",
            "tiempo de respuesta",
            "tiempo a próxima cita",
            "seguimientos post visita"
          ]
        }
      ]
    },
    "hardening_model": {
      "goal": "Pasar de preset inteligente a sistema especialista",
      "wave": "ola_2",
      "entity_queen": "mascota",
      "core_common": true,
      "domain_by_vertical": true,
      "playbooks_by_subvertical": true,
      "kpis_by_vertical": true,
      "pricing_by_vertical": true,
      "journeys_by_vertical": true,
      "reusable_modules": [
        "intake / calificación",
        "agenda / recursos",
        "cotización / propuesta",
        "pago / anticipo / membresía",
        "seguimiento / recurrencia",
        "reporting vertical"
      ],
      "minimum_viable_hardening": [
        "1 entidad reina",
        "1 pipeline propio",
        "1 cotización propia",
        "1 recurrencia propia",
        "1 dashboard propio"
      ],
      "hard_checklist": [
        "tiene entidad principal propia",
        "tiene pipeline específico",
        "tiene cotización o pricing del nicho",
        "tiene agenda o recursos del nicho",
        "tiene postventa o recurrencia del nicho",
        "tiene documentos o compliance del nicho",
        "tiene KPIs del nicho",
        "tiene 3 automatizaciones que mueven dinero",
        "tiene 2 pruebas e2e de negocio",
        "tiene subplaybooks por subvertical",
        "entidad principal propia",
        "pipeline específico",
        "pricing del nicho",
        "agenda y recursos del nicho",
        "postventa o recurrencia del nicho",
        "documentos o compliance del nicho",
        "KPIs del nicho",
        "3 automatizaciones que mueven dinero",
        "2 pruebas e2e de negocio",
        "subplaybooks por subvertical",
        "runtime ejecutable por vertical"
      ]
    },
    "specialist_layers": {
      "persistent_entities": [
        "mascota",
        "tutor / familia",
        "especie",
        "raza",
        "edad",
        "peso",
        "vacunas",
        "plan preventivo"
      ],
      "business_pipeline": {
        "primary_entity": "mascota",
        "primary_pipeline": {
          "name": "Atención y recurrencia",
          "states": [
            "lead nuevo",
            "mascota registrada",
            "servicio identificado",
            "consulta/servicio agendado",
            "confirmado",
            "asistido",
            "seguimiento post servicio",
            "plan preventivo ofrecido",
            "plan activo",
            "próxima fecha pendiente",
            "inactivo",
            "reactivado"
          ]
        },
        "secondary_pipelines": [
          {
            "name": "Preventivo",
            "states": [
              "sin plan",
              "plan ofrecido",
              "plan activo",
              "renovación pendiente",
              "renovado"
            ]
          }
        ]
      },
      "pricing_and_quotes": [
        "cotización por mascota y servicio",
        "plan preventivo recurrente",
        "bundle grooming + vacunas"
      ],
      "agenda_and_resources": [
        "médico veterinario",
        "groomer",
        "área de consulta",
        "estancia",
        "agenda por especie"
      ],
      "post_sale_and_recurrence": [
        "recordatorios por vacuna/desparasitación",
        "seguimiento por multi-mascota",
        "renovación de plan preventivo"
      ],
      "documents_compliance": [
        "cartilla de vacunación",
        "consentimiento de procedimiento",
        "instrucciones postservicio",
        "registro médico básico"
      ],
      "kpis_that_matter": [
        "citas por mascota",
        "recurrencia por tutor",
        "vacunas al día",
        "grooming repetido",
        "plan preventivo",
        "reactivación",
        "renovación de plan",
        "recompra grooming",
        "ausencias"
      ],
      "money_automations": [
        "recordatorio de vacuna pendiente",
        "recompra de grooming",
        "renovación de plan preventivo"
      ]
    },
    "domain_contract": {
      "vertical_entity_types": [
        "mascota",
        "tutor / familia",
        "especie",
        "raza",
        "edad",
        "peso",
        "vacunas",
        "plan preventivo"
      ],
      "vertical_pipeline_stages": {
        "primary": [
          "lead nuevo",
          "mascota registrada",
          "servicio identificado",
          "consulta/servicio agendado",
          "confirmado",
          "asistido",
          "seguimiento post servicio",
          "plan preventivo ofrecido",
          "plan activo",
          "próxima fecha pendiente",
          "inactivo",
          "reactivado"
        ],
        "secondary": [
          [
            "sin plan",
            "plan ofrecido",
            "plan activo",
            "renovación pendiente",
            "renovado"
          ]
        ]
      },
      "vertical_quote_types": [
        "consulta",
        "vacunación",
        "grooming",
        "daycare / hotel",
        "plan preventivo"
      ],
      "vertical_resource_types": [
        "médico veterinario",
        "groomer",
        "área de consulta",
        "estancia",
        "agenda por especie"
      ],
      "vertical_followup_policies": [
        "recordatorios por vacuna/desparasitación",
        "seguimiento por multi-mascota",
        "renovación de plan preventivo"
      ],
      "vertical_kpi_definitions": [
        "citas por mascota",
        "recurrencia por tutor",
        "vacunas al día",
        "grooming repetido",
        "plan preventivo",
        "reactivación",
        "renovación de plan",
        "recompra grooming",
        "ausencias"
      ],
      "vertical_playbooks": [
        "clínica",
        "grooming",
        "daycare",
        "hotel",
        "vacunas"
      ],
      "vertical_document_types": [
        "cartilla de vacunación",
        "consentimiento de procedimiento",
        "instrucciones postservicio",
        "registro médico básico"
      ]
    },
    "subvertical_playbooks": [
      {
        "name": "clínica",
        "focus": "Playbook operativo y comercial para clínica"
      },
      {
        "name": "grooming",
        "focus": "Playbook operativo y comercial para grooming"
      },
      {
        "name": "daycare",
        "focus": "Playbook operativo y comercial para daycare"
      },
      {
        "name": "hotel",
        "focus": "Playbook operativo y comercial para hotel"
      },
      {
        "name": "vacunas",
        "focus": "Playbook operativo y comercial para vacunas"
      }
    ],
    "business_e2e_tests": [
      {
        "name": "tutor registra mascota, agenda vacuna y activa plan preventivo",
        "status": "designed"
      },
      {
        "name": "cliente de grooming recompra y agenda siguiente visita",
        "status": "designed"
      }
    ],
    "vertical_runtime": {
      "pipeline_machine": {
        "primary_pipeline": "Atención y recurrencia",
        "entity": "mascota",
        "states": [
          "lead nuevo",
          "mascota registrada",
          "servicio identificado",
          "consulta/servicio agendado",
          "confirmado",
          "asistido",
          "seguimiento post servicio",
          "plan preventivo ofrecido",
          "plan activo",
          "próxima fecha pendiente",
          "inactivo",
          "reactivado"
        ],
        "transitions": [
          {
            "from": "lead nuevo",
            "to": "mascota registrada",
            "trigger": "qualification_complete",
            "business_effect": "advance opportunity"
          },
          {
            "from": "mascota registrada",
            "to": "servicio identificado",
            "trigger": "grooming_gap",
            "business_effect": "open commercial step"
          },
          {
            "from": "inactivo",
            "to": "reactivado",
            "trigger": "successful_outcome",
            "business_effect": "realize revenue or continuity"
          },
          {
            "from": "inactivo",
            "to": "at_risk",
            "trigger": "vaccine_due",
            "business_effect": "activate retention sequence"
          }
        ],
        "at_risk_state": "at_risk",
        "closed_states": [
          "reactivado"
        ]
      },
      "pricing_engine": {
        "quote_types": [
          "consulta",
          "plan preventivo",
          "grooming bundle",
          "hotel/daycare"
        ],
        "pricing_basis": "service_type + pet_size + species + preventive_plan",
        "rules": [
          {
            "rule": "base price by servicio type",
            "effect": "set base_price"
          },
          {
            "rule": "premium or urgent add-ons increase quote",
            "effect": "add surcharge"
          },
          {
            "rule": "bundle, membership or financing can lower immediate friction",
            "effect": "recommend package or installments"
          }
        ],
        "deposit_policy": "request advance when capacity, specialist time or inventory must be secured"
      },
      "resource_capacity": {
        "resource_types": [
          "veterinario",
          "groomer",
          "jaula",
          "consultorio",
          "espacio hotel"
        ],
        "capacity_basis": "doctor/groomer availability, room/kennel capacity and pet duration",
        "constraints": [
          "avoid double booking of critical resources",
          "respect service duration and cleanup/buffer time",
          "prioritize higher urgency and higher close probability cases"
        ],
        "priority_queue": "medico, grooming o daycare por especie"
      },
      "recurrence_engine": {
        "policies": [
          {
            "type": "vaccine_recall",
            "interval_days": 365,
            "anchor": "mascota"
          },
          {
            "type": "deworming_recall",
            "interval_days": 90,
            "anchor": "mascota"
          },
          {
            "type": "grooming_rebook",
            "interval_days": 30,
            "anchor": "mascota"
          }
        ],
        "reactivation_window_days": 365,
        "goal": "protect retention, repeat revenue and continuity"
      },
      "kpi_engine": {
        "north_star": "Recurrencia por mascota y plan preventivo activo.",
        "definitions": [
          {
            "name": "vaccines_on_time",
            "formula": "vaccines_completed / vaccines_due"
          },
          {
            "name": "grooming_repurchase",
            "formula": "repeat_grooming / grooming_clients"
          },
          {
            "name": "preventive_renewal",
            "formula": "renewed_plans / expiring_plans"
          }
        ],
        "leading_indicators": [
          "vaccine_due",
          "deworming_due",
          "no_response_7d"
        ]
      },
      "automation_engine": {
        "money_automation_policies": [
          {
            "trigger": "vaccine_due",
            "actions": [
              "send_followup",
              "escalate_owner",
              "offer_relevant_next_step"
            ],
            "goal": "save conversion or retention"
          },
          {
            "trigger": "deworming_due",
            "actions": [
              "send_quote_or_payment_link",
              "remind_deadline",
              "notify_human"
            ],
            "goal": "move revenue forward"
          },
          {
            "trigger": "plan_expiring",
            "actions": [
              "schedule_recurrence",
              "cross_sell_next_best_offer",
              "create_task"
            ],
            "goal": "increase LTV"
          }
        ],
        "quiet_hours": "21:00-08:00"
      },
      "document_flow": {
        "required_documents": [
          "cartilla de vacunacion",
          "consentimiento de procedimiento",
          "ingreso hotel",
          "plan preventivo"
        ],
        "lifecycle_rules": [
          {
            "document": "cartilla de vacunacion",
            "required_before": "first committed step",
            "signature_required": true
          },
          {
            "document": "plan preventivo",
            "required_before": "handoff or continuity step",
            "signature_required": false
          }
        ]
      },
      "matching_engine": {
        "entity": "mascota",
        "rules": [
          "species_match",
          "service_type -> staff_skill",
          "weight_range_fit",
          "multi_pet_household_priority"
        ],
        "next_best_match_outputs": [
          "best_owner",
          "best_resource_slot",
          "best_offer"
        ]
      }
    },
    "transactional_motor_v12": {
      "version": "v12_full_transactional",
      "aggregate_root": "pet_lifecycle_account",
      "main_business_entity": "mascota",
      "transaction_unit": "preventive_cycle",
      "system_of_record": {
        "write_model": [
          "commands",
          "events",
          "ledger",
          "aggregate_snapshots"
        ],
        "read_models": [
          "commercial_board",
          "operations_board",
          "finance_board",
          "continuity_board",
          "resource_load_board",
          "document_readiness_board",
          "revenue_levers_board"
        ],
        "idempotency_scope": [
          "organization_id",
          "vertical_id",
          "external_reference",
          "command_key"
        ],
        "audit_mode": "append_only_with_snapshots"
      },
      "transaction_primitives": {
        "commands": [
          "capture_intent",
          "qualify_record",
          "create_quote",
          "request_deposit",
          "reserve_capacity",
          "confirm_booking",
          "start_case",
          "approve_quote",
          "collect_payment",
          "start_fulfillment",
          "close_fulfillment",
          "schedule_recurrence",
          "issue_refund",
          "reactivate_customer",
          "register_pet_profile",
          "sell_preventive_plan",
          "log_vaccine",
          "schedule_next_due"
        ],
        "events": [
          "intent_captured",
          "record_qualified",
          "quote_created",
          "deposit_requested",
          "capacity_reserved",
          "booking_confirmed",
          "case_started",
          "quote_approved",
          "payment_collected",
          "fulfillment_started",
          "fulfillment_closed",
          "recurrence_scheduled",
          "refund_issued",
          "customer_reactivated",
          "pet_registered",
          "preventive_plan_sold",
          "vaccine_logged",
          "next_due_scheduled"
        ],
        "ledger_event_types": [
          "charge_opened",
          "deposit_collected",
          "installment_due",
          "payment_applied",
          "credit_issued",
          "refund_issued",
          "write_off_registered"
        ],
        "invariants": [
          "no vacuna sin historial mínimo",
          "no boarding sin documentos",
          "no cerrar visita sin próxima fecha",
          "todo pago debe referenciar quote, order o case activo",
          "todo cambio crítico debe emitir evento y renglón de auditoría",
          "ningún recurso se confirma dos veces en la misma ventana"
        ],
        "idempotency_keys": [
          "command_key",
          "payment_reference",
          "booking_reference",
          "external_message_id"
        ]
      },
      "aggregates": {
        "primary_record": {
          "name": "mascota",
          "status_axis": [
            "commercial",
            "operations",
            "finance",
            "continuity"
          ]
        },
        "quote": {
          "name": "service_plan_quote",
          "states": [
            "draft",
            "sent",
            "accepted",
            "expired",
            "lost"
          ]
        },
        "booking": {
          "name": "pet_visit_booking",
          "states": [
            "proposed",
            "reserved",
            "confirmed",
            "attended_or_executed",
            "missed_or_canceled"
          ]
        },
        "execution": {
          "name": "service_visit",
          "states": [
            "pending",
            "ready",
            "in_progress",
            "blocked",
            "completed",
            "closed"
          ]
        },
        "payment_account": {
          "name": "payment_account",
          "states": [
            "open",
            "partially_paid",
            "paid",
            "overdue",
            "refunded"
          ]
        },
        "continuity": {
          "name": "preventive_plan",
          "states": [
            "not_started",
            "active",
            "at_risk",
            "recovered",
            "closed"
          ]
        }
      },
      "orchestration": {
        "command_handlers": [
          "handle_capture_intent",
          "handle_qualify_record",
          "handle_create_quote",
          "handle_request_deposit",
          "handle_reserve_capacity",
          "handle_confirm_booking",
          "handle_start_case",
          "handle_approve_quote",
          "handle_register_pet_profile",
          "handle_sell_preventive_plan",
          "handle_log_vaccine",
          "handle_schedule_next_due"
        ],
        "sagas": [
          "first_visit_to_plan",
          "vaccine_due_reactivation",
          "boarding_followup"
        ],
        "money_guards": [
          "quote_before_payment",
          "capacity_before_confirmation",
          "documents_before_execution",
          "balance_before_close"
        ],
        "read_model_refresh": [
          "on_every_event",
          "nightly_reconciliation",
          "pre_dashboard_cache"
        ]
      },
      "finance": {
        "money_objects": [
          "consultation_charge",
          "plan_charge",
          "boarding_deposit",
          "grooming_charge"
        ],
        "collection_modes": [
          "por visita",
          "plan preventivo",
          "prepago de servicios"
        ],
        "refund_modes": [
          "service_credit",
          "boarding_adjustment"
        ],
        "reconciliation_views": [
          "expected_vs_collected",
          "aging_balance",
          "refund_exposure",
          "cash_by_stage"
        ]
      },
      "operations": {
        "fulfillment_unit": "preventive_cycle",
        "resource_locking": [
          "vet",
          "groomer",
          "room_kennel_capacity"
        ],
        "dispatch_or_schedule_board": [
          "queued",
          "ready",
          "assigned",
          "in_progress",
          "blocked",
          "done"
        ],
        "handoff_rules": [
          "human_handoff_on_exception",
          "supervisor_handoff_on_money_risk",
          "operator_handoff_on_compliance_gap"
        ]
      },
      "audit_compliance": {
        "timeline_entities": [
          "mascota",
          "service_plan_quote",
          "pet_visit_booking",
          "service_visit",
          "payment_account"
        ],
        "consent_gates": [
          "vaccination_card",
          "consentimiento_mascota",
          "boarding_rules"
        ],
        "required_evidence": [
          "timeline_event",
          "actor",
          "timestamp",
          "before_after_snapshot"
        ],
        "retention_rules": [
          "audit_log_append_only",
          "documents_linked_to_primary_record",
          "payment_trace_non_destructive"
        ]
      },
      "transaction_views": {
        "commercial": [
          "first_service",
          "plan_conversion",
          "family_value"
        ],
        "operations": [
          "vaccine_calendar",
          "service_history",
          "capacity"
        ],
        "finance": [
          "plan_renewals",
          "avg_ticket_per_pet",
          "open_balance"
        ],
        "continuity": [
          "next_due_date",
          "preventive_compliance",
          "multi_pet_rebuy"
        ]
      },
      "command_catalog": [
        {
          "command": "capture_intent",
          "writes": "mascota",
          "emits": "intent_captured",
          "guard": "no vacuna sin historial mínimo"
        },
        {
          "command": "qualify_record",
          "writes": "mascota",
          "emits": "record_qualified",
          "guard": "no boarding sin documentos"
        },
        {
          "command": "create_quote",
          "writes": "mascota",
          "emits": "quote_created",
          "guard": "no cerrar visita sin próxima fecha"
        },
        {
          "command": "request_deposit",
          "writes": "mascota",
          "emits": "deposit_requested",
          "guard": "no vacuna sin historial mínimo"
        },
        {
          "command": "reserve_capacity",
          "writes": "mascota",
          "emits": "capacity_reserved",
          "guard": "no boarding sin documentos"
        },
        {
          "command": "confirm_booking",
          "writes": "mascota",
          "emits": "booking_confirmed",
          "guard": "no cerrar visita sin próxima fecha"
        },
        {
          "command": "start_case",
          "writes": "mascota",
          "emits": "case_started",
          "guard": "no vacuna sin historial mínimo"
        },
        {
          "command": "approve_quote",
          "writes": "mascota",
          "emits": "quote_approved",
          "guard": "no boarding sin documentos"
        },
        {
          "command": "register_pet_profile",
          "writes": "mascota",
          "emits": "payment_collected",
          "guard": "no cerrar visita sin próxima fecha"
        },
        {
          "command": "sell_preventive_plan",
          "writes": "mascota",
          "emits": "fulfillment_started",
          "guard": "no vacuna sin historial mínimo"
        },
        {
          "command": "log_vaccine",
          "writes": "mascota",
          "emits": "fulfillment_closed",
          "guard": "no boarding sin documentos"
        },
        {
          "command": "schedule_next_due",
          "writes": "mascota",
          "emits": "recurrence_scheduled",
          "guard": "no cerrar visita sin próxima fecha"
        }
      ],
      "event_catalog": [
        {
          "event": "intent_captured",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "first_visit_to_plan"
        },
        {
          "event": "record_qualified",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "vaccine_due_reactivation"
        },
        {
          "event": "quote_created",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "boarding_followup"
        },
        {
          "event": "deposit_requested",
          "updates": [
            "timeline",
            "boards",
            "ledger"
          ],
          "next_action": "first_visit_to_plan"
        },
        {
          "event": "capacity_reserved",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "vaccine_due_reactivation"
        },
        {
          "event": "booking_confirmed",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "boarding_followup"
        },
        {
          "event": "case_started",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "first_visit_to_plan"
        },
        {
          "event": "quote_approved",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "vaccine_due_reactivation"
        },
        {
          "event": "pet_registered",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "boarding_followup"
        },
        {
          "event": "preventive_plan_sold",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "first_visit_to_plan"
        },
        {
          "event": "vaccine_logged",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "vaccine_due_reactivation"
        },
        {
          "event": "next_due_scheduled",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "boarding_followup"
        }
      ]
    },
    "is_strongest_vertical": true,
    "strongest_rank": 4,
    "ten_x_score": 94,
    "ten_x_narrative": "WAOS Vet gana cuando trata a la mascota como cuenta recurrente con consulta, prevencion, grooming y plan.",
    "ten_x_growth_loops": [
      "consulta a plan preventivo",
      "vacuna a proxima vacuna",
      "grooming a frecuencia",
      "mascota activa a recordatorio"
    ],
    "recommended_subverticals": [
      "clínica veterinaria",
      "hospital veterinario",
      "vacunación",
      "grooming"
    ],
    "subvertical_profiles": [
      {
        "id": "clínica-veterinaria",
        "name": "clínica veterinaria",
        "strength_score": 94,
        "promise": "Ordenar consulta, seguimiento y control preventivo alrededor de la mascota.",
        "growth_motion": "consult_to_prevention",
        "buyer": "Dueño de clínica veterinaria o pet care",
        "monetizes": [
          "consulta",
          "vacunas",
          "grooming",
          "hotel/daycare"
        ],
        "service_bundle": [
          "consulta general",
          "seguimiento",
          "vacunacion",
          "control anual"
        ],
        "qualification_questions": [
          "que especie y edad tiene",
          "que sintomas o necesidad hay",
          "es urgencia",
          "cuando puedes venir"
        ],
        "objections": [
          "quiero saber si es urgente",
          "solo quiero precio",
          "no tengo como moverme",
          "prefiero observarlo"
        ],
        "automation_priorities": [
          "seguimiento clínica veterinaria",
          "recordatorios",
          "winback",
          "upsell"
        ],
        "kpi_pack": [
          "citas por mascota",
          "recurrencia por tutor",
          "vacunas al día",
          "grooming repetido",
          "conversion clínica veterinaria",
          "revenue clínica veterinaria"
        ],
        "recommended_commands": [
          "avisar siguiente vacuna",
          "bloquear guardia",
          "modo humano para urgencias",
          "reactivar plan preventivo"
        ],
        "launch_assets": [
          "guion whatsapp",
          "playbook de handoff",
          "servicios seed",
          "templates seed"
        ],
        "templates": [
          {
            "key": "clínica-veterinaria-lead",
            "title": "Captacion clínica veterinaria",
            "content": "Hola, te ayudo con clínica veterinaria. Si quieres, te hago 3 preguntas y te propongo el siguiente paso ideal."
          },
          {
            "key": "clínica-veterinaria-followup",
            "title": "Seguimiento clínica veterinaria",
            "content": "Te sigo con clínica veterinaria. Si quieres, hoy mismo te propongo horario, paquete o siguiente accion."
          },
          {
            "key": "clínica-veterinaria-reactivation",
            "title": "Reactivacion clínica veterinaria",
            "content": "Te escribo porque todavia podemos mover clínica veterinaria a una accion concreta esta semana. ¿Quieres que te lo aterrice a tu caso?"
          }
        ],
        "behavior_overrides": {
          "tone": "cercano y responsable",
          "sales_intensity": "media",
          "required_phrases": [
            "te lo aterrizo a tu caso de clínica veterinaria",
            "te sigo para moverlo al siguiente paso"
          ],
          "fallback_message": "Te ayudo con clínica veterinaria. Si quieres, te hago unas preguntas rapidas y te recomiendo el siguiente paso."
        }
      },
      {
        "id": "hospital-veterinario",
        "name": "hospital veterinario",
        "strength_score": 92,
        "promise": "Convertir conversaciones de hospital veterinario en siguiente paso claro, cobro y recurrencia.",
        "growth_motion": "capture_followup_close",
        "buyer": "Dueño de clínica veterinaria o pet care",
        "monetizes": [
          "consulta",
          "vacunas",
          "grooming",
          "hotel/daycare"
        ],
        "service_bundle": [
          "servicio hospital veterinario",
          "seguimiento hospital veterinario",
          "recordatorio preventivo",
          "proxima visita"
        ],
        "qualification_questions": [
          "que especie y edad tiene",
          "que sintomas o necesidad hay",
          "es urgencia",
          "cuando puedes venir"
        ],
        "objections": [
          "precio",
          "solo quiero preguntar",
          "no sé si urge",
          "luego la llevo"
        ],
        "automation_priorities": [
          "seguimiento hospital veterinario",
          "recordatorios",
          "winback",
          "upsell"
        ],
        "kpi_pack": [
          "citas por mascota",
          "recurrencia por tutor",
          "vacunas al día",
          "grooming repetido",
          "conversion hospital veterinario",
          "revenue hospital veterinario"
        ],
        "recommended_commands": [
          "avisar siguiente vacuna",
          "bloquear guardia",
          "modo humano para urgencias",
          "reactivar plan preventivo"
        ],
        "launch_assets": [
          "guion whatsapp",
          "playbook de handoff",
          "servicios seed",
          "templates seed"
        ],
        "templates": [
          {
            "key": "hospital-veterinario-lead",
            "title": "Captacion hospital veterinario",
            "content": "Hola, te ayudo con hospital veterinario. Si quieres, te hago 3 preguntas y te propongo el siguiente paso ideal."
          },
          {
            "key": "hospital-veterinario-followup",
            "title": "Seguimiento hospital veterinario",
            "content": "Te sigo con hospital veterinario. Si quieres, hoy mismo te propongo horario, paquete o siguiente accion."
          },
          {
            "key": "hospital-veterinario-reactivation",
            "title": "Reactivacion hospital veterinario",
            "content": "Te escribo porque todavia podemos mover hospital veterinario a una accion concreta esta semana. ¿Quieres que te lo aterrice a tu caso?"
          }
        ],
        "behavior_overrides": {
          "tone": "cercano y responsable",
          "sales_intensity": "media",
          "required_phrases": [
            "te lo aterrizo a tu caso de hospital veterinario",
            "te sigo para moverlo al siguiente paso"
          ],
          "fallback_message": "Te ayudo con hospital veterinario. Si quieres, te hago unas preguntas rapidas y te recomiendo el siguiente paso."
        }
      },
      {
        "id": "vacunación",
        "name": "vacunación",
        "strength_score": 90,
        "promise": "Convertir conversaciones de vacunación en siguiente paso claro, cobro y recurrencia.",
        "growth_motion": "capture_followup_close",
        "buyer": "Dueño de clínica veterinaria o pet care",
        "monetizes": [
          "consulta",
          "vacunas",
          "grooming",
          "hotel/daycare"
        ],
        "service_bundle": [
          "servicio vacunación",
          "seguimiento vacunación",
          "recordatorio preventivo",
          "proxima visita"
        ],
        "qualification_questions": [
          "que especie y edad tiene",
          "que sintomas o necesidad hay",
          "es urgencia",
          "cuando puedes venir"
        ],
        "objections": [
          "precio",
          "solo quiero preguntar",
          "no sé si urge",
          "luego la llevo"
        ],
        "automation_priorities": [
          "seguimiento vacunación",
          "recordatorios",
          "winback",
          "upsell"
        ],
        "kpi_pack": [
          "citas por mascota",
          "recurrencia por tutor",
          "vacunas al día",
          "grooming repetido",
          "conversion vacunación",
          "revenue vacunación"
        ],
        "recommended_commands": [
          "avisar siguiente vacuna",
          "bloquear guardia",
          "modo humano para urgencias",
          "reactivar plan preventivo"
        ],
        "launch_assets": [
          "guion whatsapp",
          "playbook de handoff",
          "servicios seed",
          "templates seed"
        ],
        "templates": [
          {
            "key": "vacunación-lead",
            "title": "Captacion vacunación",
            "content": "Hola, te ayudo con vacunación. Si quieres, te hago 3 preguntas y te propongo el siguiente paso ideal."
          },
          {
            "key": "vacunación-followup",
            "title": "Seguimiento vacunación",
            "content": "Te sigo con vacunación. Si quieres, hoy mismo te propongo horario, paquete o siguiente accion."
          },
          {
            "key": "vacunación-reactivation",
            "title": "Reactivacion vacunación",
            "content": "Te escribo porque todavia podemos mover vacunación a una accion concreta esta semana. ¿Quieres que te lo aterrice a tu caso?"
          }
        ],
        "behavior_overrides": {
          "tone": "cercano y responsable",
          "sales_intensity": "media",
          "required_phrases": [
            "te lo aterrizo a tu caso de vacunación",
            "te sigo para moverlo al siguiente paso"
          ],
          "fallback_message": "Te ayudo con vacunación. Si quieres, te hago unas preguntas rapidas y te recomiendo el siguiente paso."
        }
      },
      {
        "id": "grooming",
        "name": "grooming",
        "strength_score": 88,
        "promise": "Llenar agenda recurrente con recompra y paquetes por frecuencia.",
        "growth_motion": "grooming_recurrence",
        "buyer": "Dueño de clínica veterinaria o pet care",
        "monetizes": [
          "consulta",
          "vacunas",
          "grooming",
          "hotel/daycare"
        ],
        "service_bundle": [
          "grooming basico",
          "spa pet",
          "paquete mensual",
          "recordatorio de siguiente cita"
        ],
        "qualification_questions": [
          "que especie y edad tiene",
          "que sintomas o necesidad hay",
          "es urgencia",
          "cuando puedes venir"
        ],
        "objections": [
          "se estresa",
          "solo quiero una vez",
          "esta caro",
          "no se porta bien"
        ],
        "automation_priorities": [
          "seguimiento grooming",
          "recordatorios",
          "winback",
          "upsell"
        ],
        "kpi_pack": [
          "citas por mascota",
          "recurrencia por tutor",
          "vacunas al día",
          "grooming repetido",
          "conversion grooming",
          "revenue grooming"
        ],
        "recommended_commands": [
          "avisar siguiente vacuna",
          "bloquear guardia",
          "modo humano para urgencias",
          "reactivar plan preventivo"
        ],
        "launch_assets": [
          "guion whatsapp",
          "playbook de handoff",
          "servicios seed",
          "templates seed"
        ],
        "templates": [
          {
            "key": "grooming-lead",
            "title": "Captacion grooming",
            "content": "Hola, te ayudo con grooming. Si quieres, te hago 3 preguntas y te propongo el siguiente paso ideal."
          },
          {
            "key": "grooming-followup",
            "title": "Seguimiento grooming",
            "content": "Te sigo con grooming. Si quieres, hoy mismo te propongo horario, paquete o siguiente accion."
          },
          {
            "key": "grooming-reactivation",
            "title": "Reactivacion grooming",
            "content": "Te escribo porque todavia podemos mover grooming a una accion concreta esta semana. ¿Quieres que te lo aterrice a tu caso?"
          }
        ],
        "behavior_overrides": {
          "tone": "cercano y responsable",
          "sales_intensity": "media",
          "required_phrases": [
            "te lo aterrizo a tu caso de grooming",
            "te sigo para moverlo al siguiente paso"
          ],
          "fallback_message": "Te ayudo con grooming. Si quieres, te hago unas preguntas rapidas y te recomiendo el siguiente paso."
        }
      },
      {
        "id": "hotel",
        "name": "hotel",
        "strength_score": 86,
        "promise": "Convertir estancias en una operacion confiable con upsell de servicios complementarios.",
        "growth_motion": "stay_and_addons",
        "buyer": "Dueño de clínica veterinaria o pet care",
        "monetizes": [
          "consulta",
          "vacunas",
          "grooming",
          "hotel/daycare"
        ],
        "service_bundle": [
          "estancia corta",
          "estancia larga",
          "guarderia",
          "grooming antes de salida"
        ],
        "qualification_questions": [
          "que especie y edad tiene",
          "que sintomas o necesidad hay",
          "es urgencia",
          "cuando puedes venir"
        ],
        "objections": [
          "me da pendiente dejarlo",
          "quiero ver instalaciones",
          "es caro",
          "no se adapta"
        ],
        "automation_priorities": [
          "seguimiento hotel",
          "recordatorios",
          "winback",
          "upsell"
        ],
        "kpi_pack": [
          "citas por mascota",
          "recurrencia por tutor",
          "vacunas al día",
          "grooming repetido",
          "conversion hotel",
          "revenue hotel"
        ],
        "recommended_commands": [
          "avisar siguiente vacuna",
          "bloquear guardia",
          "modo humano para urgencias",
          "reactivar plan preventivo"
        ],
        "launch_assets": [
          "guion whatsapp",
          "playbook de handoff",
          "servicios seed",
          "templates seed"
        ],
        "templates": [
          {
            "key": "hotel-lead",
            "title": "Captacion hotel",
            "content": "Hola, te ayudo con hotel. Si quieres, te hago 3 preguntas y te propongo el siguiente paso ideal."
          },
          {
            "key": "hotel-followup",
            "title": "Seguimiento hotel",
            "content": "Te sigo con hotel. Si quieres, hoy mismo te propongo horario, paquete o siguiente accion."
          },
          {
            "key": "hotel-reactivation",
            "title": "Reactivacion hotel",
            "content": "Te escribo porque todavia podemos mover hotel a una accion concreta esta semana. ¿Quieres que te lo aterrice a tu caso?"
          }
        ],
        "behavior_overrides": {
          "tone": "cercano y responsable",
          "sales_intensity": "media",
          "required_phrases": [
            "te lo aterrizo a tu caso de hotel",
            "te sigo para moverlo al siguiente paso"
          ],
          "fallback_message": "Te ayudo con hotel. Si quieres, te hago unas preguntas rapidas y te recomiendo el siguiente paso."
        }
      },
      {
        "id": "daycare",
        "name": "daycare",
        "strength_score": 84,
        "promise": "Convertir conversaciones de daycare en siguiente paso claro, cobro y recurrencia.",
        "growth_motion": "capture_followup_close",
        "buyer": "Dueño de clínica veterinaria o pet care",
        "monetizes": [
          "consulta",
          "vacunas",
          "grooming",
          "hotel/daycare"
        ],
        "service_bundle": [
          "servicio daycare",
          "seguimiento daycare",
          "recordatorio preventivo",
          "proxima visita"
        ],
        "qualification_questions": [
          "que especie y edad tiene",
          "que sintomas o necesidad hay",
          "es urgencia",
          "cuando puedes venir"
        ],
        "objections": [
          "precio",
          "solo quiero preguntar",
          "no sé si urge",
          "luego la llevo"
        ],
        "automation_priorities": [
          "seguimiento daycare",
          "recordatorios",
          "winback",
          "upsell"
        ],
        "kpi_pack": [
          "citas por mascota",
          "recurrencia por tutor",
          "vacunas al día",
          "grooming repetido",
          "conversion daycare",
          "revenue daycare"
        ],
        "recommended_commands": [
          "avisar siguiente vacuna",
          "bloquear guardia",
          "modo humano para urgencias",
          "reactivar plan preventivo"
        ],
        "launch_assets": [
          "guion whatsapp",
          "playbook de handoff",
          "servicios seed",
          "templates seed"
        ],
        "templates": [
          {
            "key": "daycare-lead",
            "title": "Captacion daycare",
            "content": "Hola, te ayudo con daycare. Si quieres, te hago 3 preguntas y te propongo el siguiente paso ideal."
          },
          {
            "key": "daycare-followup",
            "title": "Seguimiento daycare",
            "content": "Te sigo con daycare. Si quieres, hoy mismo te propongo horario, paquete o siguiente accion."
          },
          {
            "key": "daycare-reactivation",
            "title": "Reactivacion daycare",
            "content": "Te escribo porque todavia podemos mover daycare a una accion concreta esta semana. ¿Quieres que te lo aterrice a tu caso?"
          }
        ],
        "behavior_overrides": {
          "tone": "cercano y responsable",
          "sales_intensity": "media",
          "required_phrases": [
            "te lo aterrizo a tu caso de daycare",
            "te sigo para moverlo al siguiente paso"
          ],
          "fallback_message": "Te ayudo con daycare. Si quieres, te hago unas preguntas rapidas y te recomiendo el siguiente paso."
        }
      },
      {
        "id": "rehabilitación",
        "name": "rehabilitación",
        "strength_score": 82,
        "promise": "Convertir conversaciones de rehabilitación en siguiente paso claro, cobro y recurrencia.",
        "growth_motion": "capture_followup_close",
        "buyer": "Dueño de clínica veterinaria o pet care",
        "monetizes": [
          "consulta",
          "vacunas",
          "grooming",
          "hotel/daycare"
        ],
        "service_bundle": [
          "servicio rehabilitación",
          "seguimiento rehabilitación",
          "recordatorio preventivo",
          "proxima visita"
        ],
        "qualification_questions": [
          "que especie y edad tiene",
          "que sintomas o necesidad hay",
          "es urgencia",
          "cuando puedes venir"
        ],
        "objections": [
          "precio",
          "solo quiero preguntar",
          "no sé si urge",
          "luego la llevo"
        ],
        "automation_priorities": [
          "seguimiento rehabilitación",
          "recordatorios",
          "winback",
          "upsell"
        ],
        "kpi_pack": [
          "citas por mascota",
          "recurrencia por tutor",
          "vacunas al día",
          "grooming repetido",
          "conversion rehabilitación",
          "revenue rehabilitación"
        ],
        "recommended_commands": [
          "avisar siguiente vacuna",
          "bloquear guardia",
          "modo humano para urgencias",
          "reactivar plan preventivo"
        ],
        "launch_assets": [
          "guion whatsapp",
          "playbook de handoff",
          "servicios seed",
          "templates seed"
        ],
        "templates": [
          {
            "key": "rehabilitación-lead",
            "title": "Captacion rehabilitación",
            "content": "Hola, te ayudo con rehabilitación. Si quieres, te hago 3 preguntas y te propongo el siguiente paso ideal."
          },
          {
            "key": "rehabilitación-followup",
            "title": "Seguimiento rehabilitación",
            "content": "Te sigo con rehabilitación. Si quieres, hoy mismo te propongo horario, paquete o siguiente accion."
          },
          {
            "key": "rehabilitación-reactivation",
            "title": "Reactivacion rehabilitación",
            "content": "Te escribo porque todavia podemos mover rehabilitación a una accion concreta esta semana. ¿Quieres que te lo aterrice a tu caso?"
          }
        ],
        "behavior_overrides": {
          "tone": "cercano y responsable",
          "sales_intensity": "media",
          "required_phrases": [
            "te lo aterrizo a tu caso de rehabilitación",
            "te sigo para moverlo al siguiente paso"
          ],
          "fallback_message": "Te ayudo con rehabilitación. Si quieres, te hago unas preguntas rapidas y te recomiendo el siguiente paso."
        }
      },
      {
        "id": "nutrición-veterinaria",
        "name": "nutrición veterinaria",
        "strength_score": 80,
        "promise": "Convertir conversaciones de nutrición veterinaria en siguiente paso claro, cobro y recurrencia.",
        "growth_motion": "capture_followup_close",
        "buyer": "Dueño de clínica veterinaria o pet care",
        "monetizes": [
          "consulta",
          "vacunas",
          "grooming",
          "hotel/daycare"
        ],
        "service_bundle": [
          "servicio nutrición veterinaria",
          "seguimiento nutrición veterinaria",
          "recordatorio preventivo",
          "proxima visita"
        ],
        "qualification_questions": [
          "que especie y edad tiene",
          "que sintomas o necesidad hay",
          "es urgencia",
          "cuando puedes venir"
        ],
        "objections": [
          "precio",
          "solo quiero preguntar",
          "no sé si urge",
          "luego la llevo"
        ],
        "automation_priorities": [
          "seguimiento nutrición veterinaria",
          "recordatorios",
          "winback",
          "upsell"
        ],
        "kpi_pack": [
          "citas por mascota",
          "recurrencia por tutor",
          "vacunas al día",
          "grooming repetido",
          "conversion nutrición veterinaria",
          "revenue nutrición veterinaria"
        ],
        "recommended_commands": [
          "avisar siguiente vacuna",
          "bloquear guardia",
          "modo humano para urgencias",
          "reactivar plan preventivo"
        ],
        "launch_assets": [
          "guion whatsapp",
          "playbook de handoff",
          "servicios seed",
          "templates seed"
        ],
        "templates": [
          {
            "key": "nutrición-veterinaria-lead",
            "title": "Captacion nutrición veterinaria",
            "content": "Hola, te ayudo con nutrición veterinaria. Si quieres, te hago 3 preguntas y te propongo el siguiente paso ideal."
          },
          {
            "key": "nutrición-veterinaria-followup",
            "title": "Seguimiento nutrición veterinaria",
            "content": "Te sigo con nutrición veterinaria. Si quieres, hoy mismo te propongo horario, paquete o siguiente accion."
          },
          {
            "key": "nutrición-veterinaria-reactivation",
            "title": "Reactivacion nutrición veterinaria",
            "content": "Te escribo porque todavia podemos mover nutrición veterinaria a una accion concreta esta semana. ¿Quieres que te lo aterrice a tu caso?"
          }
        ],
        "behavior_overrides": {
          "tone": "cercano y responsable",
          "sales_intensity": "media",
          "required_phrases": [
            "te lo aterrizo a tu caso de nutrición veterinaria",
            "te sigo para moverlo al siguiente paso"
          ],
          "fallback_message": "Te ayudo con nutrición veterinaria. Si quieres, te hago unas preguntas rapidas y te recomiendo el siguiente paso."
        }
      },
      {
        "id": "planes-preventivos",
        "name": "planes preventivos",
        "strength_score": 78,
        "promise": "Convertir una consulta en relacion recurrente con proxima accion clara.",
        "growth_motion": "preventive_membership",
        "buyer": "Dueño de clínica veterinaria o pet care",
        "monetizes": [
          "consulta",
          "vacunas",
          "grooming",
          "hotel/daycare"
        ],
        "service_bundle": [
          "plan preventivo",
          "vacunas",
          "desparasitacion",
          "recordatorio automatico"
        ],
        "qualification_questions": [
          "que especie y edad tiene",
          "que sintomas o necesidad hay",
          "es urgencia",
          "cuando puedes venir"
        ],
        "objections": [
          "luego lo veo",
          "no sabia que tocaba",
          "es mucho gasto",
          "mi mascota esta bien"
        ],
        "automation_priorities": [
          "seguimiento planes preventivos",
          "recordatorios",
          "winback",
          "upsell"
        ],
        "kpi_pack": [
          "citas por mascota",
          "recurrencia por tutor",
          "vacunas al día",
          "grooming repetido",
          "conversion planes preventivos",
          "revenue planes preventivos"
        ],
        "recommended_commands": [
          "avisar siguiente vacuna",
          "bloquear guardia",
          "modo humano para urgencias",
          "reactivar plan preventivo"
        ],
        "launch_assets": [
          "guion whatsapp",
          "playbook de handoff",
          "servicios seed",
          "templates seed"
        ],
        "templates": [
          {
            "key": "planes-preventivos-lead",
            "title": "Captacion planes preventivos",
            "content": "Hola, te ayudo con planes preventivos. Si quieres, te hago 3 preguntas y te propongo el siguiente paso ideal."
          },
          {
            "key": "planes-preventivos-followup",
            "title": "Seguimiento planes preventivos",
            "content": "Te sigo con planes preventivos. Si quieres, hoy mismo te propongo horario, paquete o siguiente accion."
          },
          {
            "key": "planes-preventivos-reactivation",
            "title": "Reactivacion planes preventivos",
            "content": "Te escribo porque todavia podemos mover planes preventivos a una accion concreta esta semana. ¿Quieres que te lo aterrice a tu caso?"
          }
        ],
        "behavior_overrides": {
          "tone": "cercano y responsable",
          "sales_intensity": "media",
          "required_phrases": [
            "te lo aterrizo a tu caso de planes preventivos",
            "te sigo para moverlo al siguiente paso"
          ],
          "fallback_message": "Te ayudo con planes preventivos. Si quieres, te hago unas preguntas rapidas y te recomiendo el siguiente paso."
        }
      }
    ],
    "ten_x_operational_pack": {
      "recommended_commands": [
        "avisar siguiente vacuna",
        "bloquear guardia",
        "modo humano para urgencias",
        "reactivar plan preventivo"
      ],
      "launch_sequence": [
        "escoger subvertical",
        "aplicar pack",
        "simular conversaciones",
        "publicar y medir"
      ],
      "why_this_vertical": "WAOS Vet gana cuando trata a la mascota como cuenta recurrente con consulta, prevencion, grooming y plan."
    }
  },
  {
    "id": "real-estate",
    "name": "WAOS Real Estate",
    "short_name": "Inmobiliaria & property lifecycle",
    "description": "Sistema operativo conversacional para inmobiliaria y lifecycle de propiedades.",
    "problem": "Inmobiliaria pierde tiempo y cierres por leads mal calificados, mucho trabajo manual del asesor, poco seguimiento post visita y reactivación débil.",
    "subverticals": [
      "venta residencial",
      "renta residencial",
      "desarrollos",
      "preventa",
      "lujo",
      "brokers hipotecarios",
      "property management",
      "administración de rentas",
      "comercial",
      "inversión inmobiliaria"
    ],
    "objects": [
      "propiedad",
      "desarrollo",
      "zona",
      "presupuesto",
      "intención",
      "tipo de operación",
      "asesor",
      "visita",
      "documentos",
      "propietario",
      "inquilino",
      "renovación",
      "zona de interés",
      "urgencia de compra",
      "perfil financiero",
      "broker",
      "visita / open house"
    ],
    "flows": [
      "lead -> perfilado",
      "perfilado -> inventario",
      "inventario -> visita",
      "visita -> seguimiento",
      "seguimiento -> cierre o reactivación"
    ],
    "kpis": [
      "lead calificado",
      "visita agendada",
      "visita asistida",
      "conversión por asesor",
      "reactivación",
      "cierre atribuido a WhatsApp",
      "oferta emitida",
      "cierre por asesor",
      "tiempo a cierre"
    ],
    "recommended_integrations": [
      "whatsapp",
      "calendar",
      "crm",
      "media",
      "reporting"
    ],
    "default_services": [
      "asesoria de compra",
      "visita guiada",
      "renta asistida",
      "precalificacion hipotecaria",
      "property management"
    ],
    "default_faqs": [
      {
        "q": "¿Como me ayudan a encontrar propiedad?",
        "a": "Podemos perfilar presupuesto, zona e intencion para sugerirte opciones relevantes."
      },
      {
        "q": "¿Puedo agendar visita?",
        "a": "Si, el bot puede proponerte visita o llamada con el asesor correcto."
      },
      {
        "q": "¿Que documentos necesito?",
        "a": "Podemos orientarte sobre documentacion basica segun compra, renta o propiedad administrada."
      },
      {
        "q": "¿Tambien gestionan rentas?",
        "a": "Si, si operas property management podemos llevar renovaciones e incidencias basicas."
      }
    ],
    "behavior": {
      "tone": "consultivo y ejecutivo",
      "response_length": "media",
      "use_emojis": false,
      "sales_intensity": "alta",
      "offer_promotions_when": "after_budget_detected",
      "escalate_when": [
        "queja legal",
        "incidencia de inmueble",
        "oferta formal"
      ],
      "insistence_policy": "respectful",
      "can_share_price_directly": true,
      "can_negotiate": false,
      "can_mention_stock": true,
      "auto_send_images": true,
      "bot_mode": "calificacion_y_cierre",
      "active_channels": [
        "whatsapp",
        "webchat"
      ],
      "forbidden_topics": [
        "asesoria legal definitiva",
        "promesas de aprobacion hipotecaria"
      ],
      "required_phrases": [
        "te ayudo a perfilar tu busqueda",
        "puedo coordinar llamada o visita",
        "te sigo",
        "si la pregunta viene rara, igual te la aterrizo",
        "te lo aterrizo a tu caso"
      ],
      "fallback_message": "Te ayudo a filtrar propiedades, agendar visita y avanzar con el asesor correcto. Si la pregunta viene rara, en broma o medio fuera de tema, igual te sigo y la aterrizamos al negocio.",
      "humor_policy": "light_contextual",
      "strange_question_policy": "respond_validate_reframe_sell_move"
    },
    "followup_rules": [
      {
        "type": "no_response",
        "delay_minutes": 180,
        "max_attempts": 2,
        "message_template": "¿Quieres que te comparta opciones segun tu presupuesto o prefieres agendar llamada con asesor?"
      },
      {
        "type": "post_quote",
        "delay_minutes": 1440,
        "max_attempts": 2,
        "message_template": "Sigo pendiente por si quieres retomar visita, propuesta o documentacion para avanzar."
      },
      {
        "type": "reactivation",
        "delay_minutes": 20160,
        "max_attempts": 1,
        "message_template": "Tengo nuevas opciones o disponibilidad para visita. ¿Quieres que retomemos tu busqueda?"
      }
    ],
    "templates": [
      {
        "template_key": "lead_profile",
        "title": "Perfilado de lead",
        "content": "Para recomendarte mejor, dime presupuesto, zona, compra o renta y cuando quieres mudarte o invertir.",
        "variables": []
      },
      {
        "template_key": "visit_booking",
        "title": "Agendar visita",
        "content": "Puedo coordinar tu visita a {{property_name}}. ¿Te funciona {{date_option_1}} o {{date_option_2}}?",
        "variables": [
          "property_name",
          "date_option_1",
          "date_option_2"
        ]
      },
      {
        "template_key": "post_visit",
        "title": "Seguimiento post visita",
        "content": "¿Como te sentiste con la propiedad? Si quieres, avanzamos con propuesta, dudas o nuevas opciones.",
        "variables": []
      },
      {
        "template_key": "document_collection",
        "title": "Solicitud de documentos",
        "content": "Para avanzar, te comparto la lista inicial de documentos segun tu tipo de operacion.",
        "variables": []
      },
      {
        "template_key": "cold_lead_reactivation",
        "title": "Reactivacion lead frio",
        "content": "Retomo tu busqueda para compartirte opciones actualizadas segun tu presupuesto y zona ideal.",
        "variables": []
      }
    ],
    "config_overrides": {
      "objective_secondary": [
        "calificar",
        "agendar",
        "reactivar"
      ],
      "policies": [
        "No prometer aprobacion financiera",
        "Escalar temas legales o disputas"
      ],
      "can_say": [
        "propiedades",
        "rentas",
        "visitas",
        "documentos",
        "asesor asignado"
      ],
      "cannot_say": [
        "promesas legales",
        "garantia de credito",
        "cierre asegurado"
      ],
      "whatsapp_flows": [
        "perfilado_inmobiliario",
        "agenda_visita",
        "seguimiento_post_visita",
        "documentacion_basica"
      ],
      "appointment_duration_minutes": 45,
      "handoff_keywords": [
        "oferta formal",
        "contrato",
        "queja",
        "incidencia"
      ],
      "high_score_threshold": 78
    },
    "portfolio_tier": "tier_1",
    "master_thesis": "Sistema operativo conversacional para inmobiliaria y lifecycle de propiedades que perfila, recomienda, agenda visitas, sigue y reactiva oportunidades largas.",
    "buyer": {
      "primary": "Director comercial o broker principal",
      "secondary": [
        "asesores",
        "coordinación de visitas",
        "property manager"
      ]
    },
    "one_pager": {
      "headline": "WAOS Real Estate",
      "thesis": "WhatsApp se convierte en SDR inmobiliario operativo para calificar, mostrar inventario, agendar visitas y sostener funnels largos.",
      "problem": "Demasiados leads sin intención clara, poco seguimiento posterior y mucho tiempo desperdiciado por asesores caros.",
      "promise": "Cada conversación termina en visita, propuesta, reubicación de inventario o reactivación futura.",
      "monetizes": [
        "visita",
        "llamada calificada",
        "cierre de venta",
        "cierre de renta",
        "administración posterior",
        "renovación"
      ],
      "packaging": [
        "setup real estate",
        "matching de inventario",
        "seguimiento post visita",
        "property management conversacional"
      ],
      "strategic_care": "Vertical de ticket alto y muy alineada a la auditoría; debe posicionarse como control de pipeline y follow-up, no como simple chat de propiedades."
    },
    "demo_flow": [
      "El lead entra por una propiedad, zona, precio o requisitos.",
      "WAOS detecta compra o renta, presupuesto, timing e intención real.",
      "Recomienda inventario relevante y comparte fichas o assets.",
      "Agenda llamada o visita y confirma.",
      "Después de la visita recoge objeciones y reubica inventario si hace falta.",
      "Acompaña documentación, cierre o reactivación cuando cambian condiciones."
    ],
    "native_objects": {
      "core": [
        "lead",
        "propiedad",
        "desarrollo",
        "zona",
        "asesor"
      ],
      "commercial": [
        "tipo de operación",
        "presupuesto",
        "intención",
        "visita",
        "propuesta"
      ],
      "operations": [
        "estatus documental",
        "propietario",
        "inquilino",
        "renovación",
        "incidencia"
      ]
    },
    "pipeline": {
      "primary": {
        "name": "Comercialización",
        "states": [
          "lead nuevo",
          "lead perfilado",
          "lead calificado",
          "inventario enviado",
          "llamada agendada",
          "visita agendada",
          "visita asistida",
          "seguimiento post visita",
          "documentación en curso",
          "propuesta",
          "cierre pendiente",
          "cerrado",
          "perdido o reactivable"
        ]
      },
      "secondary": [
        {
          "name": "Property lifecycle",
          "states": [
            "propiedad activa",
            "renta vigente",
            "renovación pendiente",
            "renovada",
            "incidencia abierta",
            "incidencia resuelta"
          ]
        }
      ]
    },
    "bot_playbook": {
      "must_do": [
        "perfilar presupuesto",
        "detectar zona e intención",
        "recomendar opciones",
        "agendar visitas",
        "recordar citas",
        "seguir post visita",
        "reactivar leads fríos",
        "nunca quedarse seco ante bromas, preguntas raras o cambios bruscos de tema",
        "usar humor ligero cuando sume, sin sonar payaso ni poco serio",
        "validar el momento y luego reencauzar la conversacion al negocio",
        "cerrar siempre con una pregunta util o siguiente paso"
      ],
      "must_ask": [
        "compra o renta",
        "presupuesto",
        "zona",
        "tiempo de decisión",
        "tipo de inmueble",
        "forma de pago",
        "que parte del negocio se esta atorando mas",
        "si quiere que se lo aterrice a su caso"
      ],
      "objections": [
        "precio",
        "ubicación",
        "tiempos",
        "financiamiento",
        "solo estoy viendo",
        "quiero compararlo"
      ],
      "escalate_when": [
        "negociación seria",
        "cierre",
        "tema legal",
        "lead premium",
        "inversionista sofisticado"
      ],
      "forbidden": [
        "prometer disponibilidad no confirmada",
        "asesoría legal definitiva"
      ],
      "success_signals": [
        "quiero visitar",
        "mándame opciones",
        "me interesa esa zona",
        "¿qué requisitos piden?",
        "quiero avanzar"
      ],
      "style": [
        "humor ligero",
        "manejo de preguntas raras",
        "reencuadre comercial"
      ]
    },
    "automation_sequences": [
      {
        "key": "re_welcome",
        "name": "Seguimiento post inventario",
        "trigger": "opciones enviadas",
        "goal": "mover a visita",
        "steps": [
          "preguntar opción favorita",
          "ofrecer llamada",
          "cerrar visita"
        ]
      },
      {
        "key": "re_visit",
        "name": "Visita",
        "trigger": "visita agendada",
        "goal": "show-up y seguimiento posterior",
        "steps": [
          "confirmar",
          "recordatorio",
          "follow-up post visita"
        ]
      },
      {
        "key": "re_inventory_reactivation",
        "name": "Reactivación por inventario",
        "trigger": "entra nueva propiedad similar",
        "goal": "reactivar leads fríos",
        "steps": [
          "avisar novedad",
          "presentar match",
          "proponer visita"
        ]
      },
      {
        "key": "re_rental_renewal",
        "name": "Renovación de renta",
        "trigger": "contrato cercano a vencer",
        "goal": "retener renta y coordinar renovación",
        "steps": [
          "recordar vencimiento",
          "resolver dudas",
          "cerrar renovación"
        ]
      }
    ],
    "dashboard": {
      "north_star": "Visitas asistidas que avanzan a propuesta o cierre.",
      "sections": [
        {
          "name": "Funnel",
          "metrics": [
            "lead nuevo",
            "lead calificado",
            "visita agendada",
            "visita asistida",
            "visita a cierre"
          ]
        },
        {
          "name": "Asesores",
          "metrics": [
            "conversión por asesor",
            "velocidad de seguimiento",
            "tiempo a primer contacto",
            "cierre atribuido"
          ]
        },
        {
          "name": "Inventario",
          "metrics": [
            "propiedades más consultadas",
            "propiedades con más visitas",
            "leads perdidos por precio/zona",
            "reactivación por nuevo inventario"
          ]
        },
        {
          "name": "Revenue",
          "metrics": [
            "cierres atribuidos",
            "comisión estimada",
            "renta renovada",
            "property management activo"
          ]
        }
      ]
    },
    "hardening_model": {
      "goal": "Pasar de preset inteligente a sistema especialista",
      "wave": "ola_2",
      "entity_queen": "propiedad",
      "core_common": true,
      "domain_by_vertical": true,
      "playbooks_by_subvertical": true,
      "kpis_by_vertical": true,
      "pricing_by_vertical": true,
      "journeys_by_vertical": true,
      "reusable_modules": [
        "intake / calificación",
        "agenda / recursos",
        "cotización / propuesta",
        "pago / anticipo / membresía",
        "seguimiento / recurrencia",
        "reporting vertical"
      ],
      "minimum_viable_hardening": [
        "1 entidad reina",
        "1 pipeline propio",
        "1 cotización propia",
        "1 recurrencia propia",
        "1 dashboard propio"
      ],
      "hard_checklist": [
        "tiene entidad principal propia",
        "tiene pipeline específico",
        "tiene cotización o pricing del nicho",
        "tiene agenda o recursos del nicho",
        "tiene postventa o recurrencia del nicho",
        "tiene documentos o compliance del nicho",
        "tiene KPIs del nicho",
        "tiene 3 automatizaciones que mueven dinero",
        "tiene 2 pruebas e2e de negocio",
        "tiene subplaybooks por subvertical",
        "entidad principal propia",
        "pipeline específico",
        "pricing del nicho",
        "agenda y recursos del nicho",
        "postventa o recurrencia del nicho",
        "documentos o compliance del nicho",
        "KPIs del nicho",
        "3 automatizaciones que mueven dinero",
        "2 pruebas e2e de negocio",
        "subplaybooks por subvertical",
        "runtime ejecutable por vertical"
      ]
    },
    "specialist_layers": {
      "persistent_entities": [
        "propiedad",
        "tipo de operación",
        "presupuesto",
        "zona de interés",
        "urgencia de compra",
        "perfil financiero",
        "broker",
        "visita / open house"
      ],
      "business_pipeline": {
        "primary_entity": "propiedad",
        "primary_pipeline": {
          "name": "Comercialización",
          "states": [
            "lead nuevo",
            "lead perfilado",
            "lead calificado",
            "inventario enviado",
            "llamada agendada",
            "visita agendada",
            "visita asistida",
            "seguimiento post visita",
            "documentación en curso",
            "propuesta",
            "cierre pendiente",
            "cerrado",
            "perdido o reactivable"
          ]
        },
        "secondary_pipelines": [
          {
            "name": "Property lifecycle",
            "states": [
              "propiedad activa",
              "renta vigente",
              "renovación pendiente",
              "renovada",
              "incidencia abierta",
              "incidencia resuelta"
            ]
          }
        ]
      },
      "pricing_and_quotes": [
        "cotización por operación",
        "proyección de inversión",
        "reserva / apartado"
      ],
      "agenda_and_resources": [
        "broker",
        "inventario",
        "agenda de visitas",
        "open house",
        "slot de cierre"
      ],
      "post_sale_and_recurrence": [
        "seguimiento de objeciones",
        "nurture de lead según tiempo de compra",
        "reactivación de búsqueda"
      ],
      "documents_compliance": [
        "ficha de propiedad",
        "expediente de documentos",
        "propuesta / oferta",
        "perfil financiero"
      ],
      "kpis_that_matter": [
        "lead calificado",
        "visita agendada",
        "visita asistida",
        "conversión por asesor",
        "reactivación",
        "cierre atribuido a WhatsApp",
        "oferta emitida",
        "cierre por asesor",
        "tiempo a cierre"
      ],
      "money_automations": [
        "matching de propiedades",
        "seguimiento post visita",
        "reactivación de leads sin oferta"
      ]
    },
    "domain_contract": {
      "vertical_entity_types": [
        "propiedad",
        "tipo de operación",
        "presupuesto",
        "zona de interés",
        "urgencia de compra",
        "perfil financiero",
        "broker",
        "visita / open house"
      ],
      "vertical_pipeline_stages": {
        "primary": [
          "lead nuevo",
          "lead perfilado",
          "lead calificado",
          "inventario enviado",
          "llamada agendada",
          "visita agendada",
          "visita asistida",
          "seguimiento post visita",
          "documentación en curso",
          "propuesta",
          "cierre pendiente",
          "cerrado",
          "perdido o reactivable"
        ],
        "secondary": [
          [
            "propiedad activa",
            "renta vigente",
            "renovación pendiente",
            "renovada",
            "incidencia abierta",
            "incidencia resuelta"
          ]
        ]
      },
      "vertical_quote_types": [
        "renta",
        "venta",
        "preventa",
        "inversión",
        "honorarios de corretaje"
      ],
      "vertical_resource_types": [
        "broker",
        "inventario",
        "agenda de visitas",
        "open house",
        "slot de cierre"
      ],
      "vertical_followup_policies": [
        "seguimiento de objeciones",
        "nurture de lead según tiempo de compra",
        "reactivación de búsqueda"
      ],
      "vertical_kpi_definitions": [
        "lead calificado",
        "visita agendada",
        "visita asistida",
        "conversión por asesor",
        "reactivación",
        "cierre atribuido a WhatsApp",
        "oferta emitida",
        "cierre por asesor",
        "tiempo a cierre"
      ],
      "vertical_playbooks": [
        "residencial",
        "lujo",
        "inversión",
        "renta",
        "preventa"
      ],
      "vertical_document_types": [
        "ficha de propiedad",
        "expediente de documentos",
        "propuesta / oferta",
        "perfil financiero"
      ]
    },
    "subvertical_playbooks": [
      {
        "name": "residencial",
        "focus": "Playbook operativo y comercial para residencial"
      },
      {
        "name": "lujo",
        "focus": "Playbook operativo y comercial para lujo"
      },
      {
        "name": "inversión",
        "focus": "Playbook operativo y comercial para inversión"
      },
      {
        "name": "renta",
        "focus": "Playbook operativo y comercial para renta"
      },
      {
        "name": "preventa",
        "focus": "Playbook operativo y comercial para preventa"
      }
    ],
    "business_e2e_tests": [
      {
        "name": "lead calificado recibe matching, agenda visita y emite oferta",
        "status": "designed"
      },
      {
        "name": "cliente reactivado vuelve a búsqueda y agenda open house",
        "status": "designed"
      }
    ],
    "vertical_runtime": {
      "pipeline_machine": {
        "primary_pipeline": "Comercialización",
        "entity": "oportunidad inmobiliaria",
        "states": [
          "lead nuevo",
          "lead perfilado",
          "lead calificado",
          "inventario enviado",
          "llamada agendada",
          "visita agendada",
          "visita asistida",
          "seguimiento post visita",
          "documentación en curso",
          "propuesta",
          "cierre pendiente",
          "cerrado",
          "perdido o reactivable"
        ],
        "transitions": [
          {
            "from": "lead nuevo",
            "to": "lead perfilado",
            "trigger": "qualification_complete",
            "business_effect": "advance opportunity"
          },
          {
            "from": "lead perfilado",
            "to": "lead calificado",
            "trigger": "offer_pending",
            "business_effect": "open commercial step"
          },
          {
            "from": "cerrado",
            "to": "perdido o reactivable",
            "trigger": "successful_outcome",
            "business_effect": "realize revenue or continuity"
          },
          {
            "from": "cerrado",
            "to": "at_risk",
            "trigger": "inventory_match_found",
            "business_effect": "activate retention sequence"
          }
        ],
        "at_risk_state": "at_risk",
        "closed_states": [
          "perdido o reactivable"
        ]
      },
      "pricing_engine": {
        "quote_types": [
          "reserva",
          "oferta",
          "plan de pagos",
          "broker fee scenario"
        ],
        "pricing_basis": "operation_type + property_price + commission + financing stage",
        "rules": [
          {
            "rule": "base price by operación type",
            "effect": "set base_price"
          },
          {
            "rule": "premium or urgent add-ons increase quote",
            "effect": "add surcharge"
          },
          {
            "rule": "bundle, membership or financing can lower immediate friction",
            "effect": "recommend package or installments"
          }
        ],
        "deposit_policy": "request advance when capacity, specialist time or inventory must be secured"
      },
      "resource_capacity": {
        "resource_types": [
          "broker",
          "propiedad",
          "slot de visita",
          "open house",
          "sala de cierre"
        ],
        "capacity_basis": "broker calendars, property availability and visit windows",
        "constraints": [
          "avoid double booking of critical resources",
          "respect service duration and cleanup/buffer time",
          "prioritize higher urgency and higher close probability cases"
        ],
        "priority_queue": "broker, inventario y visita"
      },
      "recurrence_engine": {
        "policies": [
          {
            "type": "inventory_nurture",
            "interval_days": 14,
            "anchor": "oportunidad inmobiliaria"
          },
          {
            "type": "visit_followup",
            "interval_days": 2,
            "anchor": "oportunidad inmobiliaria"
          },
          {
            "type": "investor_reactivation",
            "interval_days": 30,
            "anchor": "oportunidad inmobiliaria"
          }
        ],
        "reactivation_window_days": 30,
        "goal": "protect retention, repeat revenue and continuity"
      },
      "kpi_engine": {
        "north_star": "Visitas asistidas que avanzan a propuesta o cierre.",
        "definitions": [
          {
            "name": "visit_show_rate",
            "formula": "visits_attended / visits_booked"
          },
          {
            "name": "offer_rate",
            "formula": "offers_sent / visits_completed"
          },
          {
            "name": "close_by_broker",
            "formula": "closed_deals / active_broker_opportunities"
          }
        ],
        "leading_indicators": [
          "inventory_match_found",
          "visit_completed",
          "no_response_7d"
        ]
      },
      "automation_engine": {
        "money_automation_policies": [
          {
            "trigger": "inventory_match_found",
            "actions": [
              "send_followup",
              "escalate_owner",
              "offer_relevant_next_step"
            ],
            "goal": "save conversion or retention"
          },
          {
            "trigger": "visit_completed",
            "actions": [
              "send_quote_or_payment_link",
              "remind_deadline",
              "notify_human"
            ],
            "goal": "move revenue forward"
          },
          {
            "trigger": "finance_docs_missing",
            "actions": [
              "schedule_recurrence",
              "cross_sell_next_best_offer",
              "create_task"
            ],
            "goal": "increase LTV"
          }
        ],
        "quiet_hours": "21:00-08:00"
      },
      "document_flow": {
        "required_documents": [
          "ficha de propiedad",
          "precalificacion financiera",
          "oferta",
          "expediente de cierre"
        ],
        "lifecycle_rules": [
          {
            "document": "ficha de propiedad",
            "required_before": "first committed step",
            "signature_required": true
          },
          {
            "document": "expediente de cierre",
            "required_before": "handoff or continuity step",
            "signature_required": false
          }
        ]
      },
      "matching_engine": {
        "entity": "oportunidad inmobiliaria",
        "rules": [
          "budget_range overlaps property.price",
          "zone_preference match",
          "operation_type match",
          "financing_readiness fit"
        ],
        "next_best_match_outputs": [
          "best_owner",
          "best_resource_slot",
          "best_offer"
        ]
      }
    },
    "transactional_motor_v12": {
      "version": "v12_full_transactional",
      "aggregate_root": "property_deal_account",
      "main_business_entity": "propiedad",
      "transaction_unit": "visit_offer_cycle",
      "system_of_record": {
        "write_model": [
          "commands",
          "events",
          "ledger",
          "aggregate_snapshots"
        ],
        "read_models": [
          "commercial_board",
          "operations_board",
          "finance_board",
          "continuity_board",
          "resource_load_board",
          "document_readiness_board",
          "revenue_levers_board"
        ],
        "idempotency_scope": [
          "organization_id",
          "vertical_id",
          "external_reference",
          "command_key"
        ],
        "audit_mode": "append_only_with_snapshots"
      },
      "transaction_primitives": {
        "commands": [
          "capture_intent",
          "qualify_record",
          "create_quote",
          "request_deposit",
          "reserve_capacity",
          "confirm_booking",
          "start_case",
          "approve_quote",
          "collect_payment",
          "start_fulfillment",
          "close_fulfillment",
          "schedule_recurrence",
          "issue_refund",
          "reactivate_customer",
          "match_inventory",
          "reserve_visit",
          "submit_offer",
          "collect_reservation_deposit"
        ],
        "events": [
          "intent_captured",
          "record_qualified",
          "quote_created",
          "deposit_requested",
          "capacity_reserved",
          "booking_confirmed",
          "case_started",
          "quote_approved",
          "payment_collected",
          "fulfillment_started",
          "fulfillment_closed",
          "recurrence_scheduled",
          "refund_issued",
          "customer_reactivated",
          "inventory_matched",
          "visit_reserved",
          "offer_submitted",
          "reservation_deposit_collected"
        ],
        "ledger_event_types": [
          "charge_opened",
          "deposit_collected",
          "installment_due",
          "payment_applied",
          "credit_issued",
          "refund_issued",
          "write_off_registered"
        ],
        "invariants": [
          "no visita sin lead calificado",
          "no apartar propiedad sin depósito",
          "no emitir propuesta sin perfil financiero",
          "todo pago debe referenciar quote, order o case activo",
          "todo cambio crítico debe emitir evento y renglón de auditoría",
          "ningún recurso se confirma dos veces en la misma ventana"
        ],
        "idempotency_keys": [
          "command_key",
          "payment_reference",
          "booking_reference",
          "external_message_id"
        ]
      },
      "aggregates": {
        "primary_record": {
          "name": "propiedad",
          "status_axis": [
            "commercial",
            "operations",
            "finance",
            "continuity"
          ]
        },
        "quote": {
          "name": "deal_proposal",
          "states": [
            "draft",
            "sent",
            "accepted",
            "expired",
            "lost"
          ]
        },
        "booking": {
          "name": "property_visit_booking",
          "states": [
            "proposed",
            "reserved",
            "confirmed",
            "attended_or_executed",
            "missed_or_canceled"
          ]
        },
        "execution": {
          "name": "deal_progression",
          "states": [
            "pending",
            "ready",
            "in_progress",
            "blocked",
            "completed",
            "closed"
          ]
        },
        "payment_account": {
          "name": "payment_account",
          "states": [
            "open",
            "partially_paid",
            "paid",
            "overdue",
            "refunded"
          ]
        },
        "continuity": {
          "name": "nurture_and_inventory_match",
          "states": [
            "not_started",
            "active",
            "at_risk",
            "recovered",
            "closed"
          ]
        }
      },
      "orchestration": {
        "command_handlers": [
          "handle_capture_intent",
          "handle_qualify_record",
          "handle_create_quote",
          "handle_request_deposit",
          "handle_reserve_capacity",
          "handle_confirm_booking",
          "handle_start_case",
          "handle_approve_quote",
          "handle_match_inventory",
          "handle_reserve_visit",
          "handle_submit_offer",
          "handle_collect_reservation_deposit"
        ],
        "sagas": [
          "inventory_matching",
          "visit_to_offer",
          "offer_to_close"
        ],
        "money_guards": [
          "quote_before_payment",
          "capacity_before_confirmation",
          "documents_before_execution",
          "balance_before_close"
        ],
        "read_model_refresh": [
          "on_every_event",
          "nightly_reconciliation",
          "pre_dashboard_cache"
        ]
      },
      "finance": {
        "money_objects": [
          "reservation_deposit",
          "broker_fee_collection",
          "rent_guarantee_charge",
          "document_fee"
        ],
        "collection_modes": [
          "apartado",
          "honorarios",
          "renta inicial"
        ],
        "refund_modes": [
          "reservation_release",
          "credit_note"
        ],
        "reconciliation_views": [
          "expected_vs_collected",
          "aging_balance",
          "refund_exposure",
          "cash_by_stage"
        ]
      },
      "operations": {
        "fulfillment_unit": "visit_offer_cycle",
        "resource_locking": [
          "broker",
          "visit_slot",
          "property_inventory_hold"
        ],
        "dispatch_or_schedule_board": [
          "queued",
          "ready",
          "assigned",
          "in_progress",
          "blocked",
          "done"
        ],
        "handoff_rules": [
          "human_handoff_on_exception",
          "supervisor_handoff_on_money_risk",
          "operator_handoff_on_compliance_gap"
        ]
      },
      "audit_compliance": {
        "timeline_entities": [
          "propiedad",
          "deal_proposal",
          "property_visit_booking",
          "deal_progression",
          "payment_account"
        ],
        "consent_gates": [
          "id_and_financial_profile",
          "offer_letter",
          "reservation_agreement"
        ],
        "required_evidence": [
          "timeline_event",
          "actor",
          "timestamp",
          "before_after_snapshot"
        ],
        "retention_rules": [
          "audit_log_append_only",
          "documents_linked_to_primary_record",
          "payment_trace_non_destructive"
        ]
      },
      "transaction_views": {
        "commercial": [
          "qualification",
          "visits",
          "offers"
        ],
        "operations": [
          "inventory_match",
          "visit_attendance",
          "followup"
        ],
        "finance": [
          "reservation_pipeline",
          "fees_collected",
          "deal_value"
        ],
        "continuity": [
          "nurture",
          "inventory_refresh",
          "reactivation"
        ]
      },
      "command_catalog": [
        {
          "command": "capture_intent",
          "writes": "propiedad",
          "emits": "intent_captured",
          "guard": "no visita sin lead calificado"
        },
        {
          "command": "qualify_record",
          "writes": "propiedad",
          "emits": "record_qualified",
          "guard": "no apartar propiedad sin depósito"
        },
        {
          "command": "create_quote",
          "writes": "propiedad",
          "emits": "quote_created",
          "guard": "no emitir propuesta sin perfil financiero"
        },
        {
          "command": "request_deposit",
          "writes": "propiedad",
          "emits": "deposit_requested",
          "guard": "no visita sin lead calificado"
        },
        {
          "command": "reserve_capacity",
          "writes": "propiedad",
          "emits": "capacity_reserved",
          "guard": "no apartar propiedad sin depósito"
        },
        {
          "command": "confirm_booking",
          "writes": "propiedad",
          "emits": "booking_confirmed",
          "guard": "no emitir propuesta sin perfil financiero"
        },
        {
          "command": "start_case",
          "writes": "propiedad",
          "emits": "case_started",
          "guard": "no visita sin lead calificado"
        },
        {
          "command": "approve_quote",
          "writes": "propiedad",
          "emits": "quote_approved",
          "guard": "no apartar propiedad sin depósito"
        },
        {
          "command": "match_inventory",
          "writes": "propiedad",
          "emits": "payment_collected",
          "guard": "no emitir propuesta sin perfil financiero"
        },
        {
          "command": "reserve_visit",
          "writes": "propiedad",
          "emits": "fulfillment_started",
          "guard": "no visita sin lead calificado"
        },
        {
          "command": "submit_offer",
          "writes": "propiedad",
          "emits": "fulfillment_closed",
          "guard": "no apartar propiedad sin depósito"
        },
        {
          "command": "collect_reservation_deposit",
          "writes": "propiedad",
          "emits": "recurrence_scheduled",
          "guard": "no emitir propuesta sin perfil financiero"
        }
      ],
      "event_catalog": [
        {
          "event": "intent_captured",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "inventory_matching"
        },
        {
          "event": "record_qualified",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "visit_to_offer"
        },
        {
          "event": "quote_created",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "offer_to_close"
        },
        {
          "event": "deposit_requested",
          "updates": [
            "timeline",
            "boards",
            "ledger"
          ],
          "next_action": "inventory_matching"
        },
        {
          "event": "capacity_reserved",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "visit_to_offer"
        },
        {
          "event": "booking_confirmed",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "offer_to_close"
        },
        {
          "event": "case_started",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "inventory_matching"
        },
        {
          "event": "quote_approved",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "visit_to_offer"
        },
        {
          "event": "inventory_matched",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "offer_to_close"
        },
        {
          "event": "visit_reserved",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "inventory_matching"
        },
        {
          "event": "offer_submitted",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "visit_to_offer"
        },
        {
          "event": "reservation_deposit_collected",
          "updates": [
            "timeline",
            "boards",
            "ledger"
          ],
          "next_action": "offer_to_close"
        }
      ]
    },
    "subvertical_profiles": [],
    "recommended_subverticals": []
  },
  {
    "id": "auto-service",
    "name": "WAOS Auto Service",
    "short_name": "Automotriz service & aftermarket",
    "description": "Sistema operativo conversacional para talleres, servicio automotriz y aftermarket.",
    "problem": "Auto service pierde confianza y dinero por intake desordenado, cotización tardía, falta de visibilidad del avance y ausencia de seguimiento al siguiente mantenimiento.",
    "subverticals": [
      "taller mecánico",
      "centro de servicio",
      "servicio eléctrico",
      "llantera",
      "hojalatería y pintura",
      "detailing",
      "PPF",
      "wraps",
      "lavado premium",
      "accesorios"
    ],
    "objects": [
      "vehículo",
      "placa/VIN",
      "servicio",
      "diagnóstico",
      "presupuesto",
      "aprobación",
      "refacción",
      "estatus",
      "técnico",
      "bahía",
      "entrega",
      "siguiente mantenimiento",
      "cliente multi-vehículo",
      "placa / VIN",
      "modelo / año",
      "motivo de servicio",
      "diagnóstico preliminar",
      "orden de trabajo",
      "mantenimiento periódico"
    ],
    "flows": [
      "solicitud -> intake",
      "intake -> revisión",
      "revisión -> cotización",
      "cotización -> aprobación",
      "trabajo -> entrega",
      "entrega -> siguiente mantenimiento"
    ],
    "kpis": [
      "ingreso agendado",
      "cotización aprobada",
      "tiempo a aprobación",
      "tiempo de ciclo",
      "retorno por mantenimiento",
      "ticket promedio",
      "aprobación de presupuesto",
      "recompra",
      "tiempo de entrega"
    ],
    "recommended_integrations": [
      "whatsapp",
      "calendar",
      "payments",
      "crm",
      "operations"
    ],
    "default_services": [
      "revision inicial",
      "mantenimiento",
      "diagnostico electrico",
      "detailing",
      "llantas y frenos"
    ],
    "default_faqs": [
      {
        "q": "¿Que datos del vehiculo necesitan?",
        "a": "El bot puede capturar placa o VIN, modelo, kilometraje y descripcion del problema."
      },
      {
        "q": "¿Pueden cotizar por WhatsApp?",
        "a": "Si, podemos iniciar una cotizacion preliminar y luego pedir aprobacion del cliente."
      },
      {
        "q": "¿Me avisan el avance?",
        "a": "Si, el bot puede comunicar estatus, refacciones y entrega."
      },
      {
        "q": "¿Recuerdan el siguiente servicio?",
        "a": "Si, configuramos recordatorios segun mantenimiento recomendado."
      }
    ],
    "behavior": {
      "tone": "tecnico y claro",
      "response_length": "media",
      "use_emojis": false,
      "sales_intensity": "media",
      "offer_promotions_when": "after_problem_classified",
      "escalate_when": [
        "seguro",
        "choque",
        "queja fuerte",
        "riesgo mecanico"
      ],
      "insistence_policy": "respectful",
      "can_share_price_directly": true,
      "can_negotiate": false,
      "can_mention_stock": true,
      "auto_send_images": true,
      "bot_mode": "intake_y_estatus",
      "active_channels": [
        "whatsapp",
        "webchat"
      ],
      "forbidden_topics": [
        "garantias no autorizadas",
        "diagnosticos definitivos sin revision"
      ],
      "required_phrases": [
        "te ayudo a registrar tu vehiculo",
        "si quieres iniciamos revision o cotizacion preliminar",
        "te sigo",
        "si la pregunta viene rara, igual te la aterrizo",
        "te lo aterrizo a tu caso"
      ],
      "fallback_message": "Te ayudo a registrar tu vehiculo, clasificar el problema y avanzar con revision o servicio. Si la pregunta viene rara, en broma o medio fuera de tema, igual te sigo y la aterrizamos al negocio.",
      "humor_policy": "light_contextual",
      "strange_question_policy": "respond_validate_reframe_sell_move"
    },
    "followup_rules": [
      {
        "type": "no_response",
        "delay_minutes": 120,
        "max_attempts": 2,
        "message_template": "¿Quieres que retomemos tu revision, cotizacion o siguiente servicio del vehiculo?"
      },
      {
        "type": "post_quote",
        "delay_minutes": 1440,
        "max_attempts": 2,
        "message_template": "Quedo atento por si quieres aprobar la cotizacion o revisar alguna partida antes de avanzar."
      },
      {
        "type": "reactivation",
        "delay_minutes": 43200,
        "max_attempts": 1,
        "message_template": "Segun tu historial, ya podria tocar el siguiente mantenimiento. ¿Quieres que te comparta opciones?"
      }
    ],
    "templates": [
      {
        "template_key": "vehicle_intake",
        "title": "Intake vehicular",
        "content": "Comparteme placa o VIN, modelo, kilometraje y el problema que notas para orientarte mejor.",
        "variables": []
      },
      {
        "template_key": "diagnostic_booking",
        "title": "Agendar revision",
        "content": "Podemos agendar ingreso o revision diagnostica para {{date}}. ¿Te funciona?",
        "variables": [
          "date"
        ]
      },
      {
        "template_key": "quote_approval",
        "title": "Solicitud de aprobacion",
        "content": "Ya tenemos la cotizacion inicial. Si te parece, te comparto detalle y avanzamos con tu aprobacion.",
        "variables": []
      },
      {
        "template_key": "status_update",
        "title": "Actualizacion de estatus",
        "content": "Tu vehiculo esta en etapa de {{job_status}}. Si surge alguna refaccion o cambio, te avisamos de inmediato.",
        "variables": [
          "job_status"
        ]
      },
      {
        "template_key": "next_service",
        "title": "Siguiente servicio",
        "content": "Tu siguiente servicio recomendado se acerca. ¿Quieres que te proponga fecha de ingreso?",
        "variables": []
      }
    ],
    "config_overrides": {
      "objective_secondary": [
        "calificar",
        "agendar",
        "reactivar"
      ],
      "policies": [
        "No prometer diagnosticos definitivos sin revision",
        "Escalar riesgos mecanicos y reclamos"
      ],
      "can_say": [
        "revision",
        "cotizacion",
        "estatus",
        "entrega",
        "mantenimiento"
      ],
      "cannot_say": [
        "garantias no autorizadas",
        "diagnostico final sin inspeccion"
      ],
      "whatsapp_flows": [
        "intake_vehicular",
        "agenda_revision",
        "aprobacion_cotizacion",
        "recordatorio_mantenimiento"
      ],
      "appointment_duration_minutes": 30,
      "handoff_keywords": [
        "seguro",
        "choque",
        "grua",
        "garantia"
      ],
      "high_score_threshold": 80
    },
    "portfolio_tier": "tier_2",
    "master_thesis": "Sistema operativo conversacional para talleres, servicio automotriz y aftermarket que ordena intake, cotización, aprobación, estatus y mantenimiento futuro.",
    "buyer": {
      "primary": "Dueño o gerente de taller/centro de servicio",
      "secondary": [
        "recepción",
        "jefe de taller",
        "asesores de servicio"
      ]
    },
    "one_pager": {
      "headline": "WAOS Auto Service",
      "thesis": "WhatsApp pasa de ser chat de cotización a sistema de intake, autorización, estatus y mantenimiento futuro.",
      "problem": "El cliente no entiende el proceso, la cotización tarda y las aprobaciones quedan dispersas.",
      "promise": "Cada solicitud se vuelve una orden clara con próximo paso visible.",
      "monetizes": [
        "revisión",
        "servicio",
        "reparación",
        "aprobación extra",
        "entrega",
        "mantenimiento recurrente"
      ],
      "packaging": [
        "setup automotriz",
        "intake por vehículo",
        "autorizaciones y estatus",
        "campañas de siguiente servicio"
      ],
      "strategic_care": "Muy buena vertical si se vende como experiencia operativa y de confianza; conviene evitar diagnósticos técnicos automatizados demasiado profundos."
    },
    "demo_flow": [
      "El cliente entra por falla, mantenimiento o servicio de estética.",
      "WAOS captura vehículo y síntoma o necesidad.",
      "Agenda revisión o ingreso y confirma.",
      "Después de revisar, envía cotización inicial y pide autorización.",
      "Actualiza estatus del trabajo y avisa cambios o refacciones.",
      "Coordina entrega, cobro y próxima fecha de mantenimiento."
    ],
    "native_objects": {
      "core": [
        "cliente",
        "vehículo",
        "placa/VIN",
        "síntoma",
        "tipo de servicio"
      ],
      "commercial": [
        "revisión",
        "cotización",
        "aprobación",
        "refacción",
        "adicional"
      ],
      "operations": [
        "técnico",
        "bahía",
        "estatus de trabajo",
        "entrega",
        "siguiente mantenimiento"
      ]
    },
    "pipeline": {
      "primary": {
        "name": "Servicio e ingreso",
        "states": [
          "lead nuevo",
          "vehículo registrado",
          "intake completado",
          "revisión agendada",
          "revisión realizada",
          "cotización enviada",
          "aprobación pendiente",
          "aprobado",
          "en trabajo",
          "listo para entrega",
          "entregado",
          "mantenimiento próximo"
        ]
      },
      "secondary": [
        {
          "name": "Winback de mantenimiento",
          "states": [
            "sin retorno",
            "recordatorio enviado",
            "reactivado",
            "servicio completado"
          ]
        }
      ]
    },
    "bot_playbook": {
      "must_do": [
        "recibir solicitud",
        "capturar vehículo",
        "guiar diagnóstico preliminar",
        "agendar revisión",
        "enviar cotización base",
        "pedir autorización",
        "informar estatus",
        "recordar siguiente servicio",
        "nunca quedarse seco ante bromas, preguntas raras o cambios bruscos de tema",
        "usar humor ligero cuando sume, sin sonar payaso ni poco serio",
        "validar el momento y luego reencauzar la conversacion al negocio",
        "cerrar siempre con una pregunta util o siguiente paso"
      ],
      "must_ask": [
        "marca/modelo/año",
        "tipo de problema o servicio",
        "urgencia",
        "fecha deseada",
        "si ya había asistido",
        "evidencia o síntomas",
        "que parte del negocio se esta atorando mas",
        "si quiere que se lo aterrice a su caso"
      ],
      "objections": [
        "precio",
        "tiempo",
        "confianza",
        "quiero otra opinión",
        "solo quiero saber cuánto"
      ],
      "escalate_when": [
        "diagnóstico técnico complejo",
        "reclamo",
        "retrabajo",
        "flotillas",
        "negociación extraordinaria"
      ],
      "forbidden": [
        "prometer reparación definitiva sin revisión",
        "dar diagnóstico técnico final por chat"
      ],
      "success_signals": [
        "quiero llevarlo",
        "¿cuándo lo revisan?",
        "mándame cotización",
        "autorizo",
        "¿cuándo me lo entregan?"
      ],
      "style": [
        "humor ligero",
        "manejo de preguntas raras",
        "reencuadre comercial"
      ]
    },
    "automation_sequences": [
      {
        "key": "auto_intake",
        "name": "Confirmación de ingreso",
        "trigger": "revisión o ingreso agendado",
        "goal": "reducir ausencias",
        "steps": [
          "confirmar cita",
          "recordatorio",
          "pedir evidencia si falta"
        ]
      },
      {
        "key": "auto_approval",
        "name": "Aprobación pendiente",
        "trigger": "cotización enviada",
        "goal": "acelerar aprobación",
        "steps": [
          "resumen de trabajo",
          "resolver objeciones",
          "cerrar autorización"
        ]
      },
      {
        "key": "auto_status",
        "name": "Estatus de trabajo",
        "trigger": "cambio de estatus",
        "goal": "dar visibilidad y confianza",
        "steps": [
          "en taller",
          "esperando refacción",
          "listo para entrega"
        ]
      },
      {
        "key": "auto_maintenance",
        "name": "Siguiente mantenimiento",
        "trigger": "ciclo de servicio cumplido",
        "goal": "retorno recurrente",
        "steps": [
          "recordatorio",
          "propuesta de servicio",
          "agenda"
        ]
      }
    ],
    "dashboard": {
      "north_star": "Cotización aprobada con retorno al siguiente mantenimiento.",
      "sections": [
        {
          "name": "Funnel",
          "metrics": [
            "solicitudes nuevas",
            "revisión agendada",
            "cotización enviada",
            "cotización aprobada"
          ]
        },
        {
          "name": "Operación",
          "metrics": [
            "tiempo a cotización",
            "tiempo a aprobación",
            "tiempo de ciclo",
            "entregas a tiempo"
          ]
        },
        {
          "name": "Revenue",
          "metrics": [
            "ticket promedio",
            "aprobaciones adicionales",
            "mantenimiento recurrente",
            "revenue por tipo de servicio"
          ]
        },
        {
          "name": "Retención",
          "metrics": [
            "clientes reactivados",
            "retorno a siguiente mantenimiento",
            "satisfacción post servicio",
            "frecuencia por vehículo"
          ]
        }
      ]
    },
    "hardening_model": {
      "goal": "Pasar de preset inteligente a sistema especialista",
      "wave": "ola_1",
      "entity_queen": "vehículo",
      "core_common": true,
      "domain_by_vertical": true,
      "playbooks_by_subvertical": true,
      "kpis_by_vertical": true,
      "pricing_by_vertical": true,
      "journeys_by_vertical": true,
      "reusable_modules": [
        "intake / calificación",
        "agenda / recursos",
        "cotización / propuesta",
        "pago / anticipo / membresía",
        "seguimiento / recurrencia",
        "reporting vertical"
      ],
      "minimum_viable_hardening": [
        "1 entidad reina",
        "1 pipeline propio",
        "1 cotización propia",
        "1 recurrencia propia",
        "1 dashboard propio"
      ],
      "hard_checklist": [
        "tiene entidad principal propia",
        "tiene pipeline específico",
        "tiene cotización o pricing del nicho",
        "tiene agenda o recursos del nicho",
        "tiene postventa o recurrencia del nicho",
        "tiene documentos o compliance del nicho",
        "tiene KPIs del nicho",
        "tiene 3 automatizaciones que mueven dinero",
        "tiene 2 pruebas e2e de negocio",
        "tiene subplaybooks por subvertical",
        "entidad principal propia",
        "pipeline específico",
        "pricing del nicho",
        "agenda y recursos del nicho",
        "postventa o recurrencia del nicho",
        "documentos o compliance del nicho",
        "KPIs del nicho",
        "3 automatizaciones que mueven dinero",
        "2 pruebas e2e de negocio",
        "subplaybooks por subvertical",
        "runtime ejecutable por vertical"
      ]
    },
    "specialist_layers": {
      "persistent_entities": [
        "vehículo",
        "cliente multi-vehículo",
        "placa / VIN",
        "modelo / año",
        "motivo de servicio",
        "diagnóstico preliminar",
        "orden de trabajo",
        "mantenimiento periódico"
      ],
      "business_pipeline": {
        "primary_entity": "vehículo",
        "primary_pipeline": {
          "name": "Servicio e ingreso",
          "states": [
            "lead nuevo",
            "vehículo registrado",
            "intake completado",
            "revisión agendada",
            "revisión realizada",
            "cotización enviada",
            "aprobación pendiente",
            "aprobado",
            "en trabajo",
            "listo para entrega",
            "entregado",
            "mantenimiento próximo"
          ]
        },
        "secondary_pipelines": [
          {
            "name": "Winback de mantenimiento",
            "states": [
              "sin retorno",
              "recordatorio enviado",
              "reactivado",
              "servicio completado"
            ]
          }
        ]
      },
      "pricing_and_quotes": [
        "cotización por diagnóstico",
        "aprobación de presupuesto",
        "próximo mantenimiento sugerido"
      ],
      "agenda_and_resources": [
        "bahía",
        "técnico",
        "elevador",
        "equipo de diagnóstico",
        "agenda por tipo de servicio"
      ],
      "post_sale_and_recurrence": [
        "recordatorios por kilometraje o tiempo",
        "seguimiento post-servicio",
        "winback de mantenimiento"
      ],
      "documents_compliance": [
        "orden de trabajo",
        "aprobación de presupuesto",
        "checklist de entrega",
        "historial de mantenimiento"
      ],
      "kpis_that_matter": [
        "ingreso agendado",
        "cotización aprobada",
        "tiempo a aprobación",
        "tiempo de ciclo",
        "retorno por mantenimiento",
        "ticket promedio",
        "aprobación de presupuesto",
        "recompra",
        "tiempo de entrega"
      ],
      "money_automations": [
        "recuperación de cotización no aprobada",
        "post-servicio con próxima visita",
        "mantenimiento periódico automático"
      ]
    },
    "domain_contract": {
      "vertical_entity_types": [
        "vehículo",
        "cliente multi-vehículo",
        "placa / VIN",
        "modelo / año",
        "motivo de servicio",
        "diagnóstico preliminar",
        "orden de trabajo",
        "mantenimiento periódico"
      ],
      "vertical_pipeline_stages": {
        "primary": [
          "lead nuevo",
          "vehículo registrado",
          "intake completado",
          "revisión agendada",
          "revisión realizada",
          "cotización enviada",
          "aprobación pendiente",
          "aprobado",
          "en trabajo",
          "listo para entrega",
          "entregado",
          "mantenimiento próximo"
        ],
        "secondary": [
          [
            "sin retorno",
            "recordatorio enviado",
            "reactivado",
            "servicio completado"
          ]
        ]
      },
      "vertical_quote_types": [
        "cotización por servicio",
        "presupuesto aprobado",
        "paquete de mantenimiento",
        "servicio por kilometraje"
      ],
      "vertical_resource_types": [
        "bahía",
        "técnico",
        "elevador",
        "equipo de diagnóstico",
        "agenda por tipo de servicio"
      ],
      "vertical_followup_policies": [
        "recordatorios por kilometraje o tiempo",
        "seguimiento post-servicio",
        "winback de mantenimiento"
      ],
      "vertical_kpi_definitions": [
        "ingreso agendado",
        "cotización aprobada",
        "tiempo a aprobación",
        "tiempo de ciclo",
        "retorno por mantenimiento",
        "ticket promedio",
        "aprobación de presupuesto",
        "recompra",
        "tiempo de entrega"
      ],
      "vertical_playbooks": [
        "llantas",
        "mecánica general",
        "detailing",
        "mantenimiento",
        "body shop"
      ],
      "vertical_document_types": [
        "orden de trabajo",
        "aprobación de presupuesto",
        "checklist de entrega",
        "historial de mantenimiento"
      ]
    },
    "subvertical_playbooks": [
      {
        "name": "llantas",
        "focus": "Playbook operativo y comercial para llantas"
      },
      {
        "name": "mecánica general",
        "focus": "Playbook operativo y comercial para mecánica general"
      },
      {
        "name": "detailing",
        "focus": "Playbook operativo y comercial para detailing"
      },
      {
        "name": "mantenimiento",
        "focus": "Playbook operativo y comercial para mantenimiento"
      },
      {
        "name": "body shop",
        "focus": "Playbook operativo y comercial para body shop"
      }
    ],
    "business_e2e_tests": [
      {
        "name": "vehículo entra por diagnóstico, aprueba presupuesto y se entrega el servicio",
        "status": "designed"
      },
      {
        "name": "cliente recibe recordatorio por kilometraje y agenda mantenimiento",
        "status": "designed"
      }
    ],
    "vertical_runtime": {
      "pipeline_machine": {
        "primary_pipeline": "Servicio e ingreso",
        "entity": "vehículo",
        "states": [
          "lead nuevo",
          "vehículo registrado",
          "intake completado",
          "revisión agendada",
          "revisión realizada",
          "cotización enviada",
          "aprobación pendiente",
          "aprobado",
          "en trabajo",
          "listo para entrega",
          "entregado",
          "mantenimiento próximo"
        ],
        "transitions": [
          {
            "from": "lead nuevo",
            "to": "vehículo registrado",
            "trigger": "qualification_complete",
            "business_effect": "advance opportunity"
          },
          {
            "from": "vehículo registrado",
            "to": "intake completado",
            "trigger": "service_completed",
            "business_effect": "open commercial step"
          },
          {
            "from": "entregado",
            "to": "mantenimiento próximo",
            "trigger": "successful_outcome",
            "business_effect": "realize revenue or continuity"
          },
          {
            "from": "entregado",
            "to": "at_risk",
            "trigger": "inspection_done",
            "business_effect": "activate retention sequence"
          }
        ],
        "at_risk_state": "at_risk",
        "closed_states": [
          "mantenimiento próximo"
        ]
      },
      "pricing_engine": {
        "quote_types": [
          "diagnostico",
          "cotizacion de servicio",
          "upgrades",
          "proximo mantenimiento"
        ],
        "pricing_basis": "service_type + parts + labor_hours + vehicle_segment",
        "rules": [
          {
            "rule": "base price by servicio type",
            "effect": "set base_price"
          },
          {
            "rule": "premium or urgent add-ons increase quote",
            "effect": "add surcharge"
          },
          {
            "rule": "bundle, membership or financing can lower immediate friction",
            "effect": "recommend package or installments"
          }
        ],
        "deposit_policy": "request advance when capacity, specialist time or inventory must be secured"
      },
      "resource_capacity": {
        "resource_types": [
          "tecnico",
          "bahia",
          "elevador",
          "equipo de alineacion",
          "advisor"
        ],
        "capacity_basis": "bay count, lift type, technician skill and service duration",
        "constraints": [
          "avoid double booking of critical resources",
          "respect service duration and cleanup/buffer time",
          "prioritize higher urgency and higher close probability cases"
        ],
        "priority_queue": "bahia, técnico y orden de trabajo"
      },
      "recurrence_engine": {
        "policies": [
          {
            "type": "maintenance_by_time",
            "interval_days": 180,
            "anchor": "vehículo"
          },
          {
            "type": "maintenance_by_mileage",
            "interval_days": 180,
            "anchor": "vehículo"
          },
          {
            "type": "post_service_nps",
            "interval_days": 3,
            "anchor": "vehículo"
          }
        ],
        "reactivation_window_days": 180,
        "goal": "protect retention, repeat revenue and continuity"
      },
      "kpi_engine": {
        "north_star": "Cotización aprobada con retorno al siguiente mantenimiento.",
        "definitions": [
          {
            "name": "quote_approval",
            "formula": "approved_quotes / issued_quotes"
          },
          {
            "name": "avg_ticket",
            "formula": "service_revenue / completed_orders"
          },
          {
            "name": "on_time_delivery",
            "formula": "orders_on_time / completed_orders"
          }
        ],
        "leading_indicators": [
          "inspection_done",
          "quote_pending_approval",
          "no_response_7d"
        ]
      },
      "automation_engine": {
        "money_automation_policies": [
          {
            "trigger": "inspection_done",
            "actions": [
              "send_followup",
              "escalate_owner",
              "offer_relevant_next_step"
            ],
            "goal": "save conversion or retention"
          },
          {
            "trigger": "quote_pending_approval",
            "actions": [
              "send_quote_or_payment_link",
              "remind_deadline",
              "notify_human"
            ],
            "goal": "move revenue forward"
          },
          {
            "trigger": "maintenance_due",
            "actions": [
              "schedule_recurrence",
              "cross_sell_next_best_offer",
              "create_task"
            ],
            "goal": "increase LTV"
          }
        ],
        "quiet_hours": "21:00-08:00"
      },
      "document_flow": {
        "required_documents": [
          "orden de trabajo",
          "aprobacion de presupuesto",
          "checklist de entrega",
          "historial de mantenimiento"
        ],
        "lifecycle_rules": [
          {
            "document": "orden de trabajo",
            "required_before": "first committed step",
            "signature_required": true
          },
          {
            "document": "historial de mantenimiento",
            "required_before": "handoff or continuity step",
            "signature_required": false
          }
        ]
      },
      "matching_engine": {
        "entity": "vehículo",
        "rules": [
          "vehicle_type -> technician_skill",
          "service_type -> bay_type",
          "branch_match",
          "urgency_priority"
        ],
        "next_best_match_outputs": [
          "best_owner",
          "best_resource_slot",
          "best_offer"
        ]
      }
    },
    "transactional_motor_v12": {
      "version": "v12_full_transactional",
      "aggregate_root": "vehicle_service_account",
      "main_business_entity": "vehículo",
      "transaction_unit": "service_order_cycle",
      "system_of_record": {
        "write_model": [
          "commands",
          "events",
          "ledger",
          "aggregate_snapshots"
        ],
        "read_models": [
          "commercial_board",
          "operations_board",
          "finance_board",
          "continuity_board",
          "resource_load_board",
          "document_readiness_board",
          "revenue_levers_board"
        ],
        "idempotency_scope": [
          "organization_id",
          "vertical_id",
          "external_reference",
          "command_key"
        ],
        "audit_mode": "append_only_with_snapshots"
      },
      "transaction_primitives": {
        "commands": [
          "capture_intent",
          "qualify_record",
          "create_quote",
          "request_deposit",
          "reserve_capacity",
          "confirm_booking",
          "start_case",
          "approve_quote",
          "collect_payment",
          "start_fulfillment",
          "close_fulfillment",
          "schedule_recurrence",
          "issue_refund",
          "reactivate_customer",
          "open_work_order",
          "approve_repair_estimate",
          "reserve_parts",
          "schedule_next_service"
        ],
        "events": [
          "intent_captured",
          "record_qualified",
          "quote_created",
          "deposit_requested",
          "capacity_reserved",
          "booking_confirmed",
          "case_started",
          "quote_approved",
          "payment_collected",
          "fulfillment_started",
          "fulfillment_closed",
          "recurrence_scheduled",
          "refund_issued",
          "customer_reactivated",
          "work_order_opened",
          "repair_estimate_approved",
          "parts_reserved",
          "next_service_scheduled"
        ],
        "ledger_event_types": [
          "charge_opened",
          "deposit_collected",
          "installment_due",
          "payment_applied",
          "credit_issued",
          "refund_issued",
          "write_off_registered"
        ],
        "invariants": [
          "no iniciar trabajo sin autorización",
          "no entregar vehículo con pago pendiente",
          "no prometer fecha sin bahía disponible",
          "todo pago debe referenciar quote, order o case activo",
          "todo cambio crítico debe emitir evento y renglón de auditoría",
          "ningún recurso se confirma dos veces en la misma ventana"
        ],
        "idempotency_keys": [
          "command_key",
          "payment_reference",
          "booking_reference",
          "external_message_id"
        ]
      },
      "aggregates": {
        "primary_record": {
          "name": "vehículo",
          "status_axis": [
            "commercial",
            "operations",
            "finance",
            "continuity"
          ]
        },
        "quote": {
          "name": "repair_estimate",
          "states": [
            "draft",
            "sent",
            "accepted",
            "expired",
            "lost"
          ]
        },
        "booking": {
          "name": "service_booking",
          "states": [
            "proposed",
            "reserved",
            "confirmed",
            "attended_or_executed",
            "missed_or_canceled"
          ]
        },
        "execution": {
          "name": "work_order_execution",
          "states": [
            "pending",
            "ready",
            "in_progress",
            "blocked",
            "completed",
            "closed"
          ]
        },
        "payment_account": {
          "name": "payment_account",
          "states": [
            "open",
            "partially_paid",
            "paid",
            "overdue",
            "refunded"
          ]
        },
        "continuity": {
          "name": "maintenance_plan",
          "states": [
            "not_started",
            "active",
            "at_risk",
            "recovered",
            "closed"
          ]
        }
      },
      "orchestration": {
        "command_handlers": [
          "handle_capture_intent",
          "handle_qualify_record",
          "handle_create_quote",
          "handle_request_deposit",
          "handle_reserve_capacity",
          "handle_confirm_booking",
          "handle_start_case",
          "handle_approve_quote",
          "handle_open_work_order",
          "handle_approve_repair_estimate",
          "handle_reserve_parts",
          "handle_schedule_next_service"
        ],
        "sagas": [
          "inspection_to_estimate",
          "estimate_to_work_order",
          "next_service_reactivation"
        ],
        "money_guards": [
          "quote_before_payment",
          "capacity_before_confirmation",
          "documents_before_execution",
          "balance_before_close"
        ],
        "read_model_refresh": [
          "on_every_event",
          "nightly_reconciliation",
          "pre_dashboard_cache"
        ]
      },
      "finance": {
        "money_objects": [
          "diagnostic_charge",
          "estimate_deposit",
          "service_collection",
          "maintenance_reminder_charge"
        ],
        "collection_modes": [
          "anticipo",
          "contra entrega",
          "plan periódico"
        ],
        "refund_modes": [
          "service_credit",
          "partial_refund"
        ],
        "reconciliation_views": [
          "expected_vs_collected",
          "aging_balance",
          "refund_exposure",
          "cash_by_stage"
        ]
      },
      "operations": {
        "fulfillment_unit": "service_order_cycle",
        "resource_locking": [
          "technician",
          "service_bay",
          "parts_hold"
        ],
        "dispatch_or_schedule_board": [
          "queued",
          "ready",
          "assigned",
          "in_progress",
          "blocked",
          "done"
        ],
        "handoff_rules": [
          "human_handoff_on_exception",
          "supervisor_handoff_on_money_risk",
          "operator_handoff_on_compliance_gap"
        ]
      },
      "audit_compliance": {
        "timeline_entities": [
          "vehículo",
          "repair_estimate",
          "service_booking",
          "work_order_execution",
          "payment_account"
        ],
        "consent_gates": [
          "vehicle_check_in",
          "repair_authorization",
          "delivery_checklist"
        ],
        "required_evidence": [
          "timeline_event",
          "actor",
          "timestamp",
          "before_after_snapshot"
        ],
        "retention_rules": [
          "audit_log_append_only",
          "documents_linked_to_primary_record",
          "payment_trace_non_destructive"
        ]
      },
      "transaction_views": {
        "commercial": [
          "inspection",
          "estimate_approval",
          "upsell"
        ],
        "operations": [
          "work_order_status",
          "bay_load",
          "delivery_eta"
        ],
        "finance": [
          "approval_rate",
          "ticket_average",
          "outstanding_balance"
        ],
        "continuity": [
          "next_service",
          "rebuy",
          "post_service_nps"
        ]
      },
      "command_catalog": [
        {
          "command": "capture_intent",
          "writes": "vehículo",
          "emits": "intent_captured",
          "guard": "no iniciar trabajo sin autorización"
        },
        {
          "command": "qualify_record",
          "writes": "vehículo",
          "emits": "record_qualified",
          "guard": "no entregar vehículo con pago pendiente"
        },
        {
          "command": "create_quote",
          "writes": "vehículo",
          "emits": "quote_created",
          "guard": "no prometer fecha sin bahía disponible"
        },
        {
          "command": "request_deposit",
          "writes": "vehículo",
          "emits": "deposit_requested",
          "guard": "no iniciar trabajo sin autorización"
        },
        {
          "command": "reserve_capacity",
          "writes": "vehículo",
          "emits": "capacity_reserved",
          "guard": "no entregar vehículo con pago pendiente"
        },
        {
          "command": "confirm_booking",
          "writes": "vehículo",
          "emits": "booking_confirmed",
          "guard": "no prometer fecha sin bahía disponible"
        },
        {
          "command": "start_case",
          "writes": "vehículo",
          "emits": "case_started",
          "guard": "no iniciar trabajo sin autorización"
        },
        {
          "command": "approve_quote",
          "writes": "vehículo",
          "emits": "quote_approved",
          "guard": "no entregar vehículo con pago pendiente"
        },
        {
          "command": "open_work_order",
          "writes": "vehículo",
          "emits": "payment_collected",
          "guard": "no prometer fecha sin bahía disponible"
        },
        {
          "command": "approve_repair_estimate",
          "writes": "vehículo",
          "emits": "fulfillment_started",
          "guard": "no iniciar trabajo sin autorización"
        },
        {
          "command": "reserve_parts",
          "writes": "vehículo",
          "emits": "fulfillment_closed",
          "guard": "no entregar vehículo con pago pendiente"
        },
        {
          "command": "schedule_next_service",
          "writes": "vehículo",
          "emits": "recurrence_scheduled",
          "guard": "no prometer fecha sin bahía disponible"
        }
      ],
      "event_catalog": [
        {
          "event": "intent_captured",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "inspection_to_estimate"
        },
        {
          "event": "record_qualified",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "estimate_to_work_order"
        },
        {
          "event": "quote_created",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "next_service_reactivation"
        },
        {
          "event": "deposit_requested",
          "updates": [
            "timeline",
            "boards",
            "ledger"
          ],
          "next_action": "inspection_to_estimate"
        },
        {
          "event": "capacity_reserved",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "estimate_to_work_order"
        },
        {
          "event": "booking_confirmed",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "next_service_reactivation"
        },
        {
          "event": "case_started",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "inspection_to_estimate"
        },
        {
          "event": "quote_approved",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "estimate_to_work_order"
        },
        {
          "event": "work_order_opened",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "next_service_reactivation"
        },
        {
          "event": "repair_estimate_approved",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "inspection_to_estimate"
        },
        {
          "event": "parts_reserved",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "estimate_to_work_order"
        },
        {
          "event": "next_service_scheduled",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "next_service_reactivation"
        }
      ]
    },
    "is_strongest_vertical": true,
    "strongest_rank": 5,
    "ten_x_score": 92,
    "ten_x_narrative": "WAOS Auto Service gana cuando ordena intake, cotizacion, aprobacion, estatus y mantenimiento futuro sin caos operativo.",
    "ten_x_growth_loops": [
      "intake a orden",
      "cotizacion a aprobacion",
      "servicio a mantenimiento",
      "entrega a siguiente visita"
    ],
    "recommended_subverticals": [
      "taller mecánico",
      "centro de servicio",
      "servicio eléctrico",
      "llantera"
    ],
    "subvertical_profiles": [
      {
        "id": "taller-mecánico",
        "name": "taller mecánico",
        "strength_score": 92,
        "promise": "Convertir WhatsApp en intake claro, aprobacion rapida y seguimiento sin friccion.",
        "growth_motion": "intake_to_approval",
        "buyer": "Dueño o gerente de taller/centro de servicio",
        "monetizes": [
          "revisión",
          "servicio",
          "reparación",
          "aprobación extra"
        ],
        "service_bundle": [
          "diagnostico",
          "servicio preventivo",
          "reparacion correctiva",
          "recordatorio de mantenimiento"
        ],
        "qualification_questions": [
          "que le notas al vehiculo",
          "es preventivo o falla",
          "cuando lo puedes traer",
          "necesitas cotizacion o cita"
        ],
        "objections": [
          "solo quiero cotizar",
          "no confio en talleres",
          "cuanto tarda",
          "lo pensare"
        ],
        "automation_priorities": [
          "seguimiento taller mecánico",
          "recordatorios",
          "winback",
          "upsell"
        ],
        "kpi_pack": [
          "ingreso agendado",
          "cotización aprobada",
          "tiempo a aprobación",
          "tiempo de ciclo",
          "conversion taller mecánico",
          "revenue taller mecánico"
        ],
        "recommended_commands": [
          "avisar entregas del dia",
          "bloquear taller",
          "pausar bot por contingencia",
          "reactivar mantenimiento de 6 meses"
        ],
        "launch_assets": [
          "guion whatsapp",
          "playbook de handoff",
          "servicios seed",
          "templates seed"
        ],
        "templates": [
          {
            "key": "taller-mecánico-lead",
            "title": "Captacion taller mecánico",
            "content": "Hola, te ayudo con taller mecánico. Si quieres, te hago 3 preguntas y te propongo el siguiente paso ideal."
          },
          {
            "key": "taller-mecánico-followup",
            "title": "Seguimiento taller mecánico",
            "content": "Te sigo con taller mecánico. Si quieres, hoy mismo te propongo horario, paquete o siguiente accion."
          },
          {
            "key": "taller-mecánico-reactivation",
            "title": "Reactivacion taller mecánico",
            "content": "Te escribo porque todavia podemos mover taller mecánico a una accion concreta esta semana. ¿Quieres que te lo aterrice a tu caso?"
          }
        ],
        "behavior_overrides": {
          "tone": "tecnico y claro",
          "sales_intensity": "media",
          "required_phrases": [
            "te lo aterrizo a tu caso de taller mecánico",
            "te sigo para moverlo al siguiente paso"
          ],
          "fallback_message": "Te ayudo con taller mecánico. Si quieres, te hago unas preguntas rapidas y te recomiendo el siguiente paso."
        }
      },
      {
        "id": "centro-de-servicio",
        "name": "centro de servicio",
        "strength_score": 90,
        "promise": "Convertir conversaciones de centro de servicio en siguiente paso claro, cobro y recurrencia.",
        "growth_motion": "capture_followup_close",
        "buyer": "Dueño o gerente de taller/centro de servicio",
        "monetizes": [
          "revisión",
          "servicio",
          "reparación",
          "aprobación extra"
        ],
        "service_bundle": [
          "diagnostico centro de servicio",
          "servicio centro de servicio",
          "autorizacion extra",
          "mantenimiento siguiente"
        ],
        "qualification_questions": [
          "que le notas al vehiculo",
          "es preventivo o falla",
          "cuando lo puedes traer",
          "necesitas cotizacion o cita"
        ],
        "objections": [
          "precio",
          "tiempo",
          "confianza",
          "quiero otra opinión"
        ],
        "automation_priorities": [
          "seguimiento centro de servicio",
          "recordatorios",
          "winback",
          "upsell"
        ],
        "kpi_pack": [
          "ingreso agendado",
          "cotización aprobada",
          "tiempo a aprobación",
          "tiempo de ciclo",
          "conversion centro de servicio",
          "revenue centro de servicio"
        ],
        "recommended_commands": [
          "avisar entregas del dia",
          "bloquear taller",
          "pausar bot por contingencia",
          "reactivar mantenimiento de 6 meses"
        ],
        "launch_assets": [
          "guion whatsapp",
          "playbook de handoff",
          "servicios seed",
          "templates seed"
        ],
        "templates": [
          {
            "key": "centro-de-servicio-lead",
            "title": "Captacion centro de servicio",
            "content": "Hola, te ayudo con centro de servicio. Si quieres, te hago 3 preguntas y te propongo el siguiente paso ideal."
          },
          {
            "key": "centro-de-servicio-followup",
            "title": "Seguimiento centro de servicio",
            "content": "Te sigo con centro de servicio. Si quieres, hoy mismo te propongo horario, paquete o siguiente accion."
          },
          {
            "key": "centro-de-servicio-reactivation",
            "title": "Reactivacion centro de servicio",
            "content": "Te escribo porque todavia podemos mover centro de servicio a una accion concreta esta semana. ¿Quieres que te lo aterrice a tu caso?"
          }
        ],
        "behavior_overrides": {
          "tone": "tecnico y claro",
          "sales_intensity": "media",
          "required_phrases": [
            "te lo aterrizo a tu caso de centro de servicio",
            "te sigo para moverlo al siguiente paso"
          ],
          "fallback_message": "Te ayudo con centro de servicio. Si quieres, te hago unas preguntas rapidas y te recomiendo el siguiente paso."
        }
      },
      {
        "id": "servicio-eléctrico",
        "name": "servicio eléctrico",
        "strength_score": 88,
        "promise": "Convertir conversaciones de servicio eléctrico en siguiente paso claro, cobro y recurrencia.",
        "growth_motion": "capture_followup_close",
        "buyer": "Dueño o gerente de taller/centro de servicio",
        "monetizes": [
          "revisión",
          "servicio",
          "reparación",
          "aprobación extra"
        ],
        "service_bundle": [
          "diagnostico servicio eléctrico",
          "servicio servicio eléctrico",
          "autorizacion extra",
          "mantenimiento siguiente"
        ],
        "qualification_questions": [
          "que le notas al vehiculo",
          "es preventivo o falla",
          "cuando lo puedes traer",
          "necesitas cotizacion o cita"
        ],
        "objections": [
          "precio",
          "tiempo",
          "confianza",
          "quiero otra opinión"
        ],
        "automation_priorities": [
          "seguimiento servicio eléctrico",
          "recordatorios",
          "winback",
          "upsell"
        ],
        "kpi_pack": [
          "ingreso agendado",
          "cotización aprobada",
          "tiempo a aprobación",
          "tiempo de ciclo",
          "conversion servicio eléctrico",
          "revenue servicio eléctrico"
        ],
        "recommended_commands": [
          "avisar entregas del dia",
          "bloquear taller",
          "pausar bot por contingencia",
          "reactivar mantenimiento de 6 meses"
        ],
        "launch_assets": [
          "guion whatsapp",
          "playbook de handoff",
          "servicios seed",
          "templates seed"
        ],
        "templates": [
          {
            "key": "servicio-eléctrico-lead",
            "title": "Captacion servicio eléctrico",
            "content": "Hola, te ayudo con servicio eléctrico. Si quieres, te hago 3 preguntas y te propongo el siguiente paso ideal."
          },
          {
            "key": "servicio-eléctrico-followup",
            "title": "Seguimiento servicio eléctrico",
            "content": "Te sigo con servicio eléctrico. Si quieres, hoy mismo te propongo horario, paquete o siguiente accion."
          },
          {
            "key": "servicio-eléctrico-reactivation",
            "title": "Reactivacion servicio eléctrico",
            "content": "Te escribo porque todavia podemos mover servicio eléctrico a una accion concreta esta semana. ¿Quieres que te lo aterrice a tu caso?"
          }
        ],
        "behavior_overrides": {
          "tone": "tecnico y claro",
          "sales_intensity": "media",
          "required_phrases": [
            "te lo aterrizo a tu caso de servicio eléctrico",
            "te sigo para moverlo al siguiente paso"
          ],
          "fallback_message": "Te ayudo con servicio eléctrico. Si quieres, te hago unas preguntas rapidas y te recomiendo el siguiente paso."
        }
      },
      {
        "id": "llantera",
        "name": "llantera",
        "strength_score": 86,
        "promise": "Mover cotizacion inmediata a cita o visita con stock y tiempos claros.",
        "growth_motion": "quote_to_visit",
        "buyer": "Dueño o gerente de taller/centro de servicio",
        "monetizes": [
          "revisión",
          "servicio",
          "reparación",
          "aprobación extra"
        ],
        "service_bundle": [
          "cotizacion llantas",
          "alineacion",
          "balanceo",
          "revision express"
        ],
        "qualification_questions": [
          "que le notas al vehiculo",
          "es preventivo o falla",
          "cuando lo puedes traer",
          "necesitas cotizacion o cita"
        ],
        "objections": [
          "quiero comparar",
          "solo una llanta",
          "esta caro",
          "voy despues"
        ],
        "automation_priorities": [
          "seguimiento llantera",
          "recordatorios",
          "winback",
          "upsell"
        ],
        "kpi_pack": [
          "ingreso agendado",
          "cotización aprobada",
          "tiempo a aprobación",
          "tiempo de ciclo",
          "conversion llantera",
          "revenue llantera"
        ],
        "recommended_commands": [
          "avisar entregas del dia",
          "bloquear taller",
          "pausar bot por contingencia",
          "reactivar mantenimiento de 6 meses"
        ],
        "launch_assets": [
          "guion whatsapp",
          "playbook de handoff",
          "servicios seed",
          "templates seed"
        ],
        "templates": [
          {
            "key": "llantera-lead",
            "title": "Captacion llantera",
            "content": "Hola, te ayudo con llantera. Si quieres, te hago 3 preguntas y te propongo el siguiente paso ideal."
          },
          {
            "key": "llantera-followup",
            "title": "Seguimiento llantera",
            "content": "Te sigo con llantera. Si quieres, hoy mismo te propongo horario, paquete o siguiente accion."
          },
          {
            "key": "llantera-reactivation",
            "title": "Reactivacion llantera",
            "content": "Te escribo porque todavia podemos mover llantera a una accion concreta esta semana. ¿Quieres que te lo aterrice a tu caso?"
          }
        ],
        "behavior_overrides": {
          "tone": "tecnico y claro",
          "sales_intensity": "media",
          "required_phrases": [
            "te lo aterrizo a tu caso de llantera",
            "te sigo para moverlo al siguiente paso"
          ],
          "fallback_message": "Te ayudo con llantera. Si quieres, te hago unas preguntas rapidas y te recomiendo el siguiente paso."
        }
      },
      {
        "id": "hojalatería-y-pintura",
        "name": "hojalatería y pintura",
        "strength_score": 84,
        "promise": "Ordenar intake con evidencia, avance y aprobaciones complementarias.",
        "growth_motion": "estimate_to_authorization",
        "buyer": "Dueño o gerente de taller/centro de servicio",
        "monetizes": [
          "revisión",
          "servicio",
          "reparación",
          "aprobación extra"
        ],
        "service_bundle": [
          "valuacion inicial",
          "diagnostico visual",
          "autorizacion extra",
          "entrega"
        ],
        "qualification_questions": [
          "que le notas al vehiculo",
          "es preventivo o falla",
          "cuando lo puedes traer",
          "necesitas cotizacion o cita"
        ],
        "objections": [
          "quiero saber si conviene",
          "cuanto tarda",
          "puedo pagarlo despues",
          "quiero comparar"
        ],
        "automation_priorities": [
          "seguimiento hojalatería y pintura",
          "recordatorios",
          "winback",
          "upsell"
        ],
        "kpi_pack": [
          "ingreso agendado",
          "cotización aprobada",
          "tiempo a aprobación",
          "tiempo de ciclo",
          "conversion hojalatería y pintura",
          "revenue hojalatería y pintura"
        ],
        "recommended_commands": [
          "avisar entregas del dia",
          "bloquear taller",
          "pausar bot por contingencia",
          "reactivar mantenimiento de 6 meses"
        ],
        "launch_assets": [
          "guion whatsapp",
          "playbook de handoff",
          "servicios seed",
          "templates seed"
        ],
        "templates": [
          {
            "key": "hojalatería-y-pintura-lead",
            "title": "Captacion hojalatería y pintura",
            "content": "Hola, te ayudo con hojalatería y pintura. Si quieres, te hago 3 preguntas y te propongo el siguiente paso ideal."
          },
          {
            "key": "hojalatería-y-pintura-followup",
            "title": "Seguimiento hojalatería y pintura",
            "content": "Te sigo con hojalatería y pintura. Si quieres, hoy mismo te propongo horario, paquete o siguiente accion."
          },
          {
            "key": "hojalatería-y-pintura-reactivation",
            "title": "Reactivacion hojalatería y pintura",
            "content": "Te escribo porque todavia podemos mover hojalatería y pintura a una accion concreta esta semana. ¿Quieres que te lo aterrice a tu caso?"
          }
        ],
        "behavior_overrides": {
          "tone": "tecnico y claro",
          "sales_intensity": "media",
          "required_phrases": [
            "te lo aterrizo a tu caso de hojalatería y pintura",
            "te sigo para moverlo al siguiente paso"
          ],
          "fallback_message": "Te ayudo con hojalatería y pintura. Si quieres, te hago unas preguntas rapidas y te recomiendo el siguiente paso."
        }
      },
      {
        "id": "detailing",
        "name": "detailing",
        "strength_score": 82,
        "promise": "Llenar agenda premium y convertir cada visita en frecuencia o paquete.",
        "growth_motion": "premium_recurrence",
        "buyer": "Dueño o gerente de taller/centro de servicio",
        "monetizes": [
          "revisión",
          "servicio",
          "reparación",
          "aprobación extra"
        ],
        "service_bundle": [
          "detailing basico",
          "detailing premium",
          "mantenimiento mensual",
          "add-on interior"
        ],
        "qualification_questions": [
          "que le notas al vehiculo",
          "es preventivo o falla",
          "cuando lo puedes traer",
          "necesitas cotizacion o cita"
        ],
        "objections": [
          "solo queria precio",
          "me da igual hoy",
          "esta caro",
          "no se que incluye"
        ],
        "automation_priorities": [
          "seguimiento detailing",
          "recordatorios",
          "winback",
          "upsell"
        ],
        "kpi_pack": [
          "ingreso agendado",
          "cotización aprobada",
          "tiempo a aprobación",
          "tiempo de ciclo",
          "conversion detailing",
          "revenue detailing"
        ],
        "recommended_commands": [
          "avisar entregas del dia",
          "bloquear taller",
          "pausar bot por contingencia",
          "reactivar mantenimiento de 6 meses"
        ],
        "launch_assets": [
          "guion whatsapp",
          "playbook de handoff",
          "servicios seed",
          "templates seed"
        ],
        "templates": [
          {
            "key": "detailing-lead",
            "title": "Captacion detailing",
            "content": "Hola, te ayudo con detailing. Si quieres, te hago 3 preguntas y te propongo el siguiente paso ideal."
          },
          {
            "key": "detailing-followup",
            "title": "Seguimiento detailing",
            "content": "Te sigo con detailing. Si quieres, hoy mismo te propongo horario, paquete o siguiente accion."
          },
          {
            "key": "detailing-reactivation",
            "title": "Reactivacion detailing",
            "content": "Te escribo porque todavia podemos mover detailing a una accion concreta esta semana. ¿Quieres que te lo aterrice a tu caso?"
          }
        ],
        "behavior_overrides": {
          "tone": "tecnico y claro",
          "sales_intensity": "media",
          "required_phrases": [
            "te lo aterrizo a tu caso de detailing",
            "te sigo para moverlo al siguiente paso"
          ],
          "fallback_message": "Te ayudo con detailing. Si quieres, te hago unas preguntas rapidas y te recomiendo el siguiente paso."
        }
      },
      {
        "id": "ppf",
        "name": "PPF",
        "strength_score": 80,
        "promise": "Convertir conversaciones de PPF en siguiente paso claro, cobro y recurrencia.",
        "growth_motion": "capture_followup_close",
        "buyer": "Dueño o gerente de taller/centro de servicio",
        "monetizes": [
          "revisión",
          "servicio",
          "reparación",
          "aprobación extra"
        ],
        "service_bundle": [
          "diagnostico PPF",
          "servicio PPF",
          "autorizacion extra",
          "mantenimiento siguiente"
        ],
        "qualification_questions": [
          "que le notas al vehiculo",
          "es preventivo o falla",
          "cuando lo puedes traer",
          "necesitas cotizacion o cita"
        ],
        "objections": [
          "precio",
          "tiempo",
          "confianza",
          "quiero otra opinión"
        ],
        "automation_priorities": [
          "seguimiento PPF",
          "recordatorios",
          "winback",
          "upsell"
        ],
        "kpi_pack": [
          "ingreso agendado",
          "cotización aprobada",
          "tiempo a aprobación",
          "tiempo de ciclo",
          "conversion PPF",
          "revenue PPF"
        ],
        "recommended_commands": [
          "avisar entregas del dia",
          "bloquear taller",
          "pausar bot por contingencia",
          "reactivar mantenimiento de 6 meses"
        ],
        "launch_assets": [
          "guion whatsapp",
          "playbook de handoff",
          "servicios seed",
          "templates seed"
        ],
        "templates": [
          {
            "key": "ppf-lead",
            "title": "Captacion PPF",
            "content": "Hola, te ayudo con PPF. Si quieres, te hago 3 preguntas y te propongo el siguiente paso ideal."
          },
          {
            "key": "ppf-followup",
            "title": "Seguimiento PPF",
            "content": "Te sigo con PPF. Si quieres, hoy mismo te propongo horario, paquete o siguiente accion."
          },
          {
            "key": "ppf-reactivation",
            "title": "Reactivacion PPF",
            "content": "Te escribo porque todavia podemos mover PPF a una accion concreta esta semana. ¿Quieres que te lo aterrice a tu caso?"
          }
        ],
        "behavior_overrides": {
          "tone": "tecnico y claro",
          "sales_intensity": "media",
          "required_phrases": [
            "te lo aterrizo a tu caso de PPF",
            "te sigo para moverlo al siguiente paso"
          ],
          "fallback_message": "Te ayudo con PPF. Si quieres, te hago unas preguntas rapidas y te recomiendo el siguiente paso."
        }
      },
      {
        "id": "wraps",
        "name": "wraps",
        "strength_score": 78,
        "promise": "Convertir conversaciones de wraps en siguiente paso claro, cobro y recurrencia.",
        "growth_motion": "capture_followup_close",
        "buyer": "Dueño o gerente de taller/centro de servicio",
        "monetizes": [
          "revisión",
          "servicio",
          "reparación",
          "aprobación extra"
        ],
        "service_bundle": [
          "diagnostico wraps",
          "servicio wraps",
          "autorizacion extra",
          "mantenimiento siguiente"
        ],
        "qualification_questions": [
          "que le notas al vehiculo",
          "es preventivo o falla",
          "cuando lo puedes traer",
          "necesitas cotizacion o cita"
        ],
        "objections": [
          "precio",
          "tiempo",
          "confianza",
          "quiero otra opinión"
        ],
        "automation_priorities": [
          "seguimiento wraps",
          "recordatorios",
          "winback",
          "upsell"
        ],
        "kpi_pack": [
          "ingreso agendado",
          "cotización aprobada",
          "tiempo a aprobación",
          "tiempo de ciclo",
          "conversion wraps",
          "revenue wraps"
        ],
        "recommended_commands": [
          "avisar entregas del dia",
          "bloquear taller",
          "pausar bot por contingencia",
          "reactivar mantenimiento de 6 meses"
        ],
        "launch_assets": [
          "guion whatsapp",
          "playbook de handoff",
          "servicios seed",
          "templates seed"
        ],
        "templates": [
          {
            "key": "wraps-lead",
            "title": "Captacion wraps",
            "content": "Hola, te ayudo con wraps. Si quieres, te hago 3 preguntas y te propongo el siguiente paso ideal."
          },
          {
            "key": "wraps-followup",
            "title": "Seguimiento wraps",
            "content": "Te sigo con wraps. Si quieres, hoy mismo te propongo horario, paquete o siguiente accion."
          },
          {
            "key": "wraps-reactivation",
            "title": "Reactivacion wraps",
            "content": "Te escribo porque todavia podemos mover wraps a una accion concreta esta semana. ¿Quieres que te lo aterrice a tu caso?"
          }
        ],
        "behavior_overrides": {
          "tone": "tecnico y claro",
          "sales_intensity": "media",
          "required_phrases": [
            "te lo aterrizo a tu caso de wraps",
            "te sigo para moverlo al siguiente paso"
          ],
          "fallback_message": "Te ayudo con wraps. Si quieres, te hago unas preguntas rapidas y te recomiendo el siguiente paso."
        }
      },
      {
        "id": "lavado-premium",
        "name": "lavado premium",
        "strength_score": 76,
        "promise": "Convertir conversaciones de lavado premium en siguiente paso claro, cobro y recurrencia.",
        "growth_motion": "capture_followup_close",
        "buyer": "Dueño o gerente de taller/centro de servicio",
        "monetizes": [
          "revisión",
          "servicio",
          "reparación",
          "aprobación extra"
        ],
        "service_bundle": [
          "diagnostico lavado premium",
          "servicio lavado premium",
          "autorizacion extra",
          "mantenimiento siguiente"
        ],
        "qualification_questions": [
          "que le notas al vehiculo",
          "es preventivo o falla",
          "cuando lo puedes traer",
          "necesitas cotizacion o cita"
        ],
        "objections": [
          "precio",
          "tiempo",
          "confianza",
          "quiero otra opinión"
        ],
        "automation_priorities": [
          "seguimiento lavado premium",
          "recordatorios",
          "winback",
          "upsell"
        ],
        "kpi_pack": [
          "ingreso agendado",
          "cotización aprobada",
          "tiempo a aprobación",
          "tiempo de ciclo",
          "conversion lavado premium",
          "revenue lavado premium"
        ],
        "recommended_commands": [
          "avisar entregas del dia",
          "bloquear taller",
          "pausar bot por contingencia",
          "reactivar mantenimiento de 6 meses"
        ],
        "launch_assets": [
          "guion whatsapp",
          "playbook de handoff",
          "servicios seed",
          "templates seed"
        ],
        "templates": [
          {
            "key": "lavado-premium-lead",
            "title": "Captacion lavado premium",
            "content": "Hola, te ayudo con lavado premium. Si quieres, te hago 3 preguntas y te propongo el siguiente paso ideal."
          },
          {
            "key": "lavado-premium-followup",
            "title": "Seguimiento lavado premium",
            "content": "Te sigo con lavado premium. Si quieres, hoy mismo te propongo horario, paquete o siguiente accion."
          },
          {
            "key": "lavado-premium-reactivation",
            "title": "Reactivacion lavado premium",
            "content": "Te escribo porque todavia podemos mover lavado premium a una accion concreta esta semana. ¿Quieres que te lo aterrice a tu caso?"
          }
        ],
        "behavior_overrides": {
          "tone": "tecnico y claro",
          "sales_intensity": "media",
          "required_phrases": [
            "te lo aterrizo a tu caso de lavado premium",
            "te sigo para moverlo al siguiente paso"
          ],
          "fallback_message": "Te ayudo con lavado premium. Si quieres, te hago unas preguntas rapidas y te recomiendo el siguiente paso."
        }
      },
      {
        "id": "accesorios",
        "name": "accesorios",
        "strength_score": 74,
        "promise": "Convertir conversaciones de accesorios en siguiente paso claro, cobro y recurrencia.",
        "growth_motion": "capture_followup_close",
        "buyer": "Dueño o gerente de taller/centro de servicio",
        "monetizes": [
          "revisión",
          "servicio",
          "reparación",
          "aprobación extra"
        ],
        "service_bundle": [
          "diagnostico accesorios",
          "servicio accesorios",
          "autorizacion extra",
          "mantenimiento siguiente"
        ],
        "qualification_questions": [
          "que le notas al vehiculo",
          "es preventivo o falla",
          "cuando lo puedes traer",
          "necesitas cotizacion o cita"
        ],
        "objections": [
          "precio",
          "tiempo",
          "confianza",
          "quiero otra opinión"
        ],
        "automation_priorities": [
          "seguimiento accesorios",
          "recordatorios",
          "winback",
          "upsell"
        ],
        "kpi_pack": [
          "ingreso agendado",
          "cotización aprobada",
          "tiempo a aprobación",
          "tiempo de ciclo",
          "conversion accesorios",
          "revenue accesorios"
        ],
        "recommended_commands": [
          "avisar entregas del dia",
          "bloquear taller",
          "pausar bot por contingencia",
          "reactivar mantenimiento de 6 meses"
        ],
        "launch_assets": [
          "guion whatsapp",
          "playbook de handoff",
          "servicios seed",
          "templates seed"
        ],
        "templates": [
          {
            "key": "accesorios-lead",
            "title": "Captacion accesorios",
            "content": "Hola, te ayudo con accesorios. Si quieres, te hago 3 preguntas y te propongo el siguiente paso ideal."
          },
          {
            "key": "accesorios-followup",
            "title": "Seguimiento accesorios",
            "content": "Te sigo con accesorios. Si quieres, hoy mismo te propongo horario, paquete o siguiente accion."
          },
          {
            "key": "accesorios-reactivation",
            "title": "Reactivacion accesorios",
            "content": "Te escribo porque todavia podemos mover accesorios a una accion concreta esta semana. ¿Quieres que te lo aterrice a tu caso?"
          }
        ],
        "behavior_overrides": {
          "tone": "tecnico y claro",
          "sales_intensity": "media",
          "required_phrases": [
            "te lo aterrizo a tu caso de accesorios",
            "te sigo para moverlo al siguiente paso"
          ],
          "fallback_message": "Te ayudo con accesorios. Si quieres, te hago unas preguntas rapidas y te recomiendo el siguiente paso."
        }
      }
    ],
    "ten_x_operational_pack": {
      "recommended_commands": [
        "avisar entregas del dia",
        "bloquear taller",
        "pausar bot por contingencia",
        "reactivar mantenimiento de 6 meses"
      ],
      "launch_sequence": [
        "escoger subvertical",
        "aplicar pack",
        "simular conversaciones",
        "publicar y medir"
      ],
      "why_this_vertical": "WAOS Auto Service gana cuando ordena intake, cotizacion, aprobacion, estatus y mantenimiento futuro sin caos operativo."
    }
  },
  {
    "id": "education",
    "name": "WAOS Education",
    "short_name": "Educacion & formacion",
    "description": "Sistema operativo conversacional para admisiones e inscripción.",
    "problem": "Educación pierde conversión por exceso de respuestas manuales, mala persecución documental, seguimiento débil y poca estructura para cerrar inscripciones y renovaciones.",
    "subverticals": [
      "colegios privados",
      "universidades privadas",
      "idiomas",
      "academias",
      "tutorías",
      "bootcamps",
      "after school",
      "formación técnica",
      "educación ejecutiva",
      "educación continua"
    ],
    "objects": [
      "campus",
      "programa",
      "nivel",
      "modalidad",
      "ciclo",
      "lead de admisión",
      "tour",
      "entrevista",
      "examen",
      "documentos",
      "inscripción",
      "colegiatura",
      "renovación",
      "aspirante",
      "alumno",
      "programa académico",
      "campus / modalidad",
      "cohorte",
      "documentos pendientes",
      "asesor educativo",
      "beca / financiamiento"
    ],
    "flows": [
      "lead -> perfilado",
      "perfilado -> tour/entrevista",
      "entrevista -> documentos",
      "documentos -> inscripción",
      "inscripción -> renovación"
    ],
    "kpis": [
      "lead a entrevista/tour",
      "entrevista a inscripción",
      "documentos completos",
      "inscripción pagada",
      "tiempo de cierre",
      "renovación por cohorte",
      "show a sesión informativa",
      "admisión",
      "inscripción",
      "deserción temprana"
    ],
    "recommended_integrations": [
      "whatsapp",
      "calendar",
      "payments",
      "crm",
      "reporting"
    ],
    "default_services": [
      "asesoria de admision",
      "tour o entrevista",
      "inscripcion",
      "programa intensivo",
      "renovacion de ciclo"
    ],
    "default_faqs": [
      {
        "q": "¿Que programa me conviene?",
        "a": "Podemos orientar segun edad, nivel e interes para recomendar el programa adecuado."
      },
      {
        "q": "¿Puedo agendar tour o entrevista?",
        "a": "Si, el bot puede coordinar llamada, tour, entrevista o examen."
      },
      {
        "q": "¿Que documentos necesito?",
        "a": "Podemos perseguir documentos pendientes y explicarte el proceso de admision."
      },
      {
        "q": "¿Puedo pagar inscripcion?",
        "a": "Si, podemos enviarte enlace de pago o seguimiento de colegiatura si esta configurado."
      }
    ],
    "behavior": {
      "tone": "claro y orientador",
      "response_length": "media",
      "use_emojis": false,
      "sales_intensity": "media",
      "offer_promotions_when": "after_program_fit_detected",
      "escalate_when": [
        "beca especial",
        "caso academico sensible",
        "queja"
      ],
      "insistence_policy": "respectful",
      "can_share_price_directly": true,
      "can_negotiate": false,
      "can_mention_stock": true,
      "auto_send_images": true,
      "bot_mode": "admision_y_renovacion",
      "active_channels": [
        "whatsapp",
        "webchat"
      ],
      "forbidden_topics": [
        "promesas de admision garantizada"
      ],
      "required_phrases": [
        "te ayudo a identificar el programa correcto",
        "puedo guiarte en el proceso de admision",
        "te sigo",
        "si la pregunta viene rara, igual te la aterrizo",
        "te lo aterrizo a tu caso"
      ],
      "fallback_message": "Te ayudo a encontrar programa, revisar requisitos y avanzar hasta inscripcion. Si la pregunta viene rara, en broma o medio fuera de tema, igual te sigo y la aterrizamos al negocio.",
      "humor_policy": "light_contextual",
      "strange_question_policy": "respond_validate_reframe_sell_move"
    },
    "followup_rules": [
      {
        "type": "no_response",
        "delay_minutes": 180,
        "max_attempts": 2,
        "message_template": "¿Quieres que te recomiende programa o agendemos llamada, tour o entrevista?"
      },
      {
        "type": "post_quote",
        "delay_minutes": 1440,
        "max_attempts": 2,
        "message_template": "Sigo pendiente por si quieres retomar admision, documentos o pago de inscripcion."
      },
      {
        "type": "reactivation",
        "delay_minutes": 43200,
        "max_attempts": 1,
        "message_template": "Todavia podemos ayudarte a completar tu proceso o renovar tu siguiente ciclo. ¿Lo retomamos?"
      }
    ],
    "templates": [
      {
        "template_key": "admissions_intake",
        "title": "Intake admision",
        "content": "Para orientarte mejor, dime edad o nivel del alumno, programa de interes y campus preferido.",
        "variables": []
      },
      {
        "template_key": "tour_booking",
        "title": "Agendar tour",
        "content": "Puedo apartarte un tour o entrevista para {{date}}. ¿Te funciona ese horario?",
        "variables": [
          "date"
        ]
      },
      {
        "template_key": "documents_followup",
        "title": "Seguimiento documentos",
        "content": "Te comparto los documentos pendientes para avanzar con tu inscripcion. Si quieres, los revisamos juntos.",
        "variables": []
      },
      {
        "template_key": "enrollment_payment",
        "title": "Pago de inscripcion",
        "content": "Si quieres asegurar tu lugar, te envio el link de pago de inscripcion ahora mismo.",
        "variables": []
      },
      {
        "template_key": "renewal_cycle",
        "title": "Renovacion de ciclo",
        "content": "Tu siguiente ciclo o nivel ya esta cerca. ¿Quieres que te ayude a renovarlo?",
        "variables": []
      }
    ],
    "config_overrides": {
      "objective_secondary": [
        "calificar",
        "agendar",
        "renovar"
      ],
      "policies": [
        "No garantizar admision sin proceso",
        "Escalar casos sensibles o becas especiales"
      ],
      "can_say": [
        "programas",
        "campus",
        "entrevistas",
        "documentos",
        "inscripcion",
        "colegiatura"
      ],
      "cannot_say": [
        "admision garantizada",
        "beca aprobada sin validacion"
      ],
      "whatsapp_flows": [
        "perfilado_programa",
        "tour_entrevista",
        "seguimiento_documentos",
        "renovacion_ciclo"
      ],
      "appointment_duration_minutes": 30,
      "handoff_keywords": [
        "beca",
        "queja",
        "caso academico",
        "reembolso"
      ],
      "high_score_threshold": 76
    },
    "portfolio_tier": "tier_1",
    "master_thesis": "Sistema operativo conversacional para admisiones, inscripción y renovación que convierte interés académico en entrevista, documentos, pago y continuidad.",
    "buyer": {
      "primary": "Director de admisiones o crecimiento",
      "secondary": [
        "asesores de admisión",
        "coordinación académica",
        "cobranzas"
      ]
    },
    "one_pager": {
      "headline": "WAOS Education",
      "thesis": "WhatsApp se vuelve el funnel de orientación, entrevista, documentos, inscripción y renovación.",
      "problem": "Admisiones responde muchísimo, pero persigue mal documentos, pagos y cierres.",
      "promise": "Cada prospecto avanza con siguiente paso visible hasta convertirse en alumno pagado y renovado.",
      "monetizes": [
        "entrevista/tour",
        "inscripción",
        "colegiatura inicial",
        "renovación",
        "upgrade de programas"
      ],
      "packaging": [
        "setup education",
        "playbooks por programa",
        "tour + documentos + pagos",
        "renovación por ciclo"
      ],
      "strategic_care": "Nicho prometedor según la auditoría; conviene venderlo como motor de admisiones y continuidad, no solo como atención informativa."
    },
    "demo_flow": [
      "Entra prospecto o padre de familia preguntando por costos, horarios o requisitos.",
      "WAOS perfila por edad, nivel, interés y modalidad.",
      "Recomienda programa y agenda llamada, tour o entrevista.",
      "Persigue documentos y recuerda examen o entrevista.",
      "Cobra inscripción o primer pago.",
      "Luego acompaña onboarding y renovación al siguiente ciclo."
    ],
    "native_objects": {
      "core": [
        "prospecto",
        "alumno",
        "tutor",
        "campus",
        "programa",
        "nivel",
        "modalidad",
        "ciclo",
        "aspirante"
      ],
      "commercial": [
        "tour",
        "entrevista",
        "examen",
        "documentos",
        "inscripción",
        "colegiatura"
      ],
      "operations": [
        "onboarding académico",
        "renovación",
        "upgrade de programa",
        "cohorte"
      ]
    },
    "pipeline": {
      "primary": {
        "name": "Admisión",
        "states": [
          "lead nuevo",
          "lead perfilado",
          "programa recomendado",
          "llamada/tour agendado",
          "entrevista realizada",
          "examen pendiente/completado",
          "documentos incompletos",
          "documentos completos",
          "inscripción pendiente",
          "inscripción pagada",
          "alumno activo",
          "renovación pendiente",
          "renovado"
        ]
      },
      "secondary": [
        {
          "name": "Reactivación de prospectos",
          "states": [
            "indeciso",
            "nurturing",
            "reactivado",
            "cerrado"
          ]
        }
      ]
    },
    "bot_playbook": {
      "must_do": [
        "orientar según perfil",
        "recomendar programa",
        "agendar tour o llamada",
        "recordar pasos",
        "perseguir documentos",
        "recordar pagos",
        "renovar ciclo",
        "nunca quedarse seco ante bromas, preguntas raras o cambios bruscos de tema",
        "usar humor ligero cuando sume, sin sonar payaso ni poco serio",
        "validar el momento y luego reencauzar la conversacion al negocio",
        "cerrar siempre con una pregunta util o siguiente paso"
      ],
      "must_ask": [
        "edad o perfil",
        "objetivo académico",
        "modalidad preferida",
        "horario",
        "sede",
        "urgencia de inscripción",
        "que parte del negocio se esta atorando mas",
        "si quiere que se lo aterrice a su caso"
      ],
      "objections": [
        "costo",
        "modalidad",
        "duración",
        "horarios",
        "quiero compararlo",
        "beca o apoyo"
      ],
      "escalate_when": [
        "negociación financiera",
        "dudas académicas profundas",
        "casos especiales",
        "beca compleja",
        "admisión internacional"
      ],
      "forbidden": [
        "prometer becas no aprobadas",
        "asegurar admisión sin proceso"
      ],
      "success_signals": [
        "quiero tour",
        "quiero inscribirme",
        "¿qué documentos envío?",
        "mándame horarios",
        "¿cómo pago?"
      ],
      "style": [
        "humor ligero",
        "manejo de preguntas raras",
        "reencuadre comercial"
      ]
    },
    "automation_sequences": [
      {
        "key": "edu_nurture",
        "name": "Nurturing inicial",
        "trigger": "lead nuevo",
        "goal": "mover a entrevista o tour",
        "steps": [
          "presentar programa",
          "resolver dudas",
          "proponer llamada/tour"
        ]
      },
      {
        "key": "edu_documents",
        "name": "Documentos faltantes",
        "trigger": "proceso abierto con expediente incompleto",
        "goal": "completar inscripción",
        "steps": [
          "recordar checklist",
          "detectar faltantes",
          "cerrar expediente"
        ]
      },
      {
        "key": "edu_payment",
        "name": "Inscripción no pagada",
        "trigger": "expediente completo sin pago",
        "goal": "cerrar matrícula",
        "steps": [
          "recordar vencimiento",
          "enviar link de pago",
          "confirmar alta"
        ]
      },
      {
        "key": "edu_renewal",
        "name": "Renovación de ciclo",
        "trigger": "ciclo próximo a cerrar",
        "goal": "retener alumno",
        "steps": [
          "recordar renovación",
          "resolver dudas",
          "cerrar pago"
        ]
      }
    ],
    "dashboard": {
      "north_star": "Entrevista o tour a inscripción pagada.",
      "sections": [
        {
          "name": "Funnel",
          "metrics": [
            "leads nuevos",
            "lead a tour/llamada",
            "entrevista completada",
            "documentos completos",
            "inscripción pagada"
          ]
        },
        {
          "name": "Revenue",
          "metrics": [
            "ingresos por inscripción",
            "colegiatura inicial",
            "renovación",
            "ingreso por programa"
          ]
        },
        {
          "name": "Operación",
          "metrics": [
            "tiempo de cierre",
            "leads sin seguimiento",
            "documentos pendientes",
            "conversión por asesor"
          ]
        },
        {
          "name": "Retención",
          "metrics": [
            "renovación por cohorte",
            "abandono temprano",
            "upgrade de programa",
            "reactivación de indecisos"
          ]
        }
      ]
    },
    "hardening_model": {
      "goal": "Pasar de preset inteligente a sistema especialista",
      "wave": "ola_3",
      "entity_queen": "aspirante",
      "core_common": true,
      "domain_by_vertical": true,
      "playbooks_by_subvertical": true,
      "kpis_by_vertical": true,
      "pricing_by_vertical": true,
      "journeys_by_vertical": true,
      "reusable_modules": [
        "intake / calificación",
        "agenda / recursos",
        "cotización / propuesta",
        "pago / anticipo / membresía",
        "seguimiento / recurrencia",
        "reporting vertical"
      ],
      "minimum_viable_hardening": [
        "1 entidad reina",
        "1 pipeline propio",
        "1 cotización propia",
        "1 recurrencia propia",
        "1 dashboard propio"
      ],
      "hard_checklist": [
        "tiene entidad principal propia",
        "tiene pipeline específico",
        "tiene cotización o pricing del nicho",
        "tiene agenda o recursos del nicho",
        "tiene postventa o recurrencia del nicho",
        "tiene documentos o compliance del nicho",
        "tiene KPIs del nicho",
        "tiene 3 automatizaciones que mueven dinero",
        "tiene 2 pruebas e2e de negocio",
        "tiene subplaybooks por subvertical",
        "entidad principal propia",
        "pipeline específico",
        "pricing del nicho",
        "agenda y recursos del nicho",
        "postventa o recurrencia del nicho",
        "documentos o compliance del nicho",
        "KPIs del nicho",
        "3 automatizaciones que mueven dinero",
        "2 pruebas e2e de negocio",
        "subplaybooks por subvertical",
        "runtime ejecutable por vertical"
      ]
    },
    "specialist_layers": {
      "persistent_entities": [
        "aspirante",
        "alumno",
        "programa académico",
        "campus / modalidad",
        "cohorte",
        "documentos pendientes",
        "asesor educativo",
        "beca / financiamiento"
      ],
      "business_pipeline": {
        "primary_entity": "aspirante",
        "primary_pipeline": {
          "name": "Admisión",
          "states": [
            "lead nuevo",
            "lead perfilado",
            "programa recomendado",
            "llamada/tour agendado",
            "entrevista realizada",
            "examen pendiente/completado",
            "documentos incompletos",
            "documentos completos",
            "inscripción pendiente",
            "inscripción pagada",
            "alumno activo",
            "renovación pendiente",
            "renovado"
          ]
        },
        "secondary_pipelines": [
          {
            "name": "Reactivación de prospectos",
            "states": [
              "indeciso",
              "nurturing",
              "reactivado",
              "cerrado"
            ]
          }
        ]
      },
      "pricing_and_quotes": [
        "cotización por programa",
        "beca / financiamiento",
        "plan de pagos"
      ],
      "agenda_and_resources": [
        "asesor",
        "campus",
        "sesión informativa",
        "entrevista",
        "cohorte / cupo"
      ],
      "post_sale_and_recurrence": [
        "automatizaciones por deadline",
        "seguimiento de no inscritos",
        "retención temprana post inscripción"
      ],
      "documents_compliance": [
        "documentos de admisión",
        "carta de admisión",
        "beca / financiamiento",
        "expediente del aspirante"
      ],
      "kpis_that_matter": [
        "lead a entrevista/tour",
        "entrevista a inscripción",
        "documentos completos",
        "inscripción pagada",
        "tiempo de cierre",
        "renovación por cohorte",
        "show a sesión informativa",
        "admisión",
        "inscripción",
        "deserción temprana"
      ],
      "money_automations": [
        "sesión informativa a entrevista",
        "reactivación de no inscritos",
        "deadline de documentos y pago"
      ]
    },
    "domain_contract": {
      "vertical_entity_types": [
        "aspirante",
        "alumno",
        "programa académico",
        "campus / modalidad",
        "cohorte",
        "documentos pendientes",
        "asesor educativo",
        "beca / financiamiento"
      ],
      "vertical_pipeline_stages": {
        "primary": [
          "lead nuevo",
          "lead perfilado",
          "programa recomendado",
          "llamada/tour agendado",
          "entrevista realizada",
          "examen pendiente/completado",
          "documentos incompletos",
          "documentos completos",
          "inscripción pendiente",
          "inscripción pagada",
          "alumno activo",
          "renovación pendiente",
          "renovado"
        ],
        "secondary": [
          [
            "indeciso",
            "nurturing",
            "reactivado",
            "cerrado"
          ]
        ]
      },
      "vertical_quote_types": [
        "colegiatura",
        "inscripción",
        "beca",
        "financiamiento",
        "plan de pagos"
      ],
      "vertical_resource_types": [
        "asesor",
        "campus",
        "sesión informativa",
        "entrevista",
        "cohorte / cupo"
      ],
      "vertical_followup_policies": [
        "automatizaciones por deadline",
        "seguimiento de no inscritos",
        "retención temprana post inscripción"
      ],
      "vertical_kpi_definitions": [
        "lead a entrevista/tour",
        "entrevista a inscripción",
        "documentos completos",
        "inscripción pagada",
        "tiempo de cierre",
        "renovación por cohorte",
        "show a sesión informativa",
        "admisión",
        "inscripción",
        "deserción temprana"
      ],
      "vertical_playbooks": [
        "cursos cortos",
        "licenciatura",
        "posgrado",
        "bootcamp",
        "educación continua"
      ],
      "vertical_document_types": [
        "documentos de admisión",
        "carta de admisión",
        "beca / financiamiento",
        "expediente del aspirante"
      ]
    },
    "subvertical_playbooks": [
      {
        "name": "cursos cortos",
        "focus": "Playbook operativo y comercial para cursos cortos"
      },
      {
        "name": "licenciatura",
        "focus": "Playbook operativo y comercial para licenciatura"
      },
      {
        "name": "posgrado",
        "focus": "Playbook operativo y comercial para posgrado"
      },
      {
        "name": "bootcamp",
        "focus": "Playbook operativo y comercial para bootcamp"
      },
      {
        "name": "educación continua",
        "focus": "Playbook operativo y comercial para educación continua"
      }
    ],
    "business_e2e_tests": [
      {
        "name": "lead académico agenda sesión, entrega documentos y se inscribe",
        "status": "designed"
      },
      {
        "name": "aspirante con beca pendiente reacciona antes del deadline y confirma lugar",
        "status": "designed"
      }
    ],
    "vertical_runtime": {
      "pipeline_machine": {
        "primary_pipeline": "Admisión",
        "entity": "aspirante",
        "states": [
          "lead nuevo",
          "lead perfilado",
          "programa recomendado",
          "llamada/tour agendado",
          "entrevista realizada",
          "examen pendiente/completado",
          "documentos incompletos",
          "documentos completos",
          "inscripción pendiente",
          "inscripción pagada",
          "alumno activo",
          "renovación pendiente",
          "renovado"
        ],
        "transitions": [
          {
            "from": "lead nuevo",
            "to": "lead perfilado",
            "trigger": "qualification_complete",
            "business_effect": "advance opportunity"
          },
          {
            "from": "lead perfilado",
            "to": "programa recomendado",
            "trigger": "admitted",
            "business_effect": "open commercial step"
          },
          {
            "from": "renovación pendiente",
            "to": "renovado",
            "trigger": "successful_outcome",
            "business_effect": "realize revenue or continuity"
          },
          {
            "from": "renovación pendiente",
            "to": "at_risk",
            "trigger": "info_session_booked",
            "business_effect": "activate retention sequence"
          }
        ],
        "at_risk_state": "at_risk",
        "closed_states": [
          "renovado"
        ]
      },
      "pricing_engine": {
        "quote_types": [
          "inscripcion",
          "colegiatura",
          "beca/financiamiento",
          "upgrade de programa"
        ],
        "pricing_basis": "program + campus + modality + scholarship/financing",
        "rules": [
          {
            "rule": "base price by programa type",
            "effect": "set base_price"
          },
          {
            "rule": "premium or urgent add-ons increase quote",
            "effect": "add surcharge"
          },
          {
            "rule": "bundle, membership or financing can lower immediate friction",
            "effect": "recommend package or installments"
          }
        ],
        "deposit_policy": "request advance when capacity, specialist time or inventory must be secured"
      },
      "resource_capacity": {
        "resource_types": [
          "asesor educativo",
          "sesion informativa",
          "entrevistador",
          "cupo de cohorte"
        ],
        "capacity_basis": "advisor bandwidth, interview slots and cohort seats",
        "constraints": [
          "avoid double booking of critical resources",
          "respect service duration and cleanup/buffer time",
          "prioritize higher urgency and higher close probability cases"
        ],
        "priority_queue": "asesor, cohorte y admisiones"
      },
      "recurrence_engine": {
        "policies": [
          {
            "type": "deadline_nudge",
            "interval_days": 7,
            "anchor": "aspirante"
          },
          {
            "type": "docs_followup",
            "interval_days": 5,
            "anchor": "aspirante"
          },
          {
            "type": "retention_check",
            "interval_days": 30,
            "anchor": "aspirante"
          }
        ],
        "reactivation_window_days": 30,
        "goal": "protect retention, repeat revenue and continuity"
      },
      "kpi_engine": {
        "north_star": "Entrevista o tour a inscripción pagada.",
        "definitions": [
          {
            "name": "admission_rate",
            "formula": "admitted / qualified_applicants"
          },
          {
            "name": "enrollment_rate",
            "formula": "enrolled / admitted"
          },
          {
            "name": "early_dropout_risk",
            "formula": "inactive_new_students / enrolled_new_students"
          }
        ],
        "leading_indicators": [
          "info_session_booked",
          "docs_missing",
          "no_response_7d"
        ]
      },
      "automation_engine": {
        "money_automation_policies": [
          {
            "trigger": "info_session_booked",
            "actions": [
              "send_followup",
              "escalate_owner",
              "offer_relevant_next_step"
            ],
            "goal": "save conversion or retention"
          },
          {
            "trigger": "docs_missing",
            "actions": [
              "send_quote_or_payment_link",
              "remind_deadline",
              "notify_human"
            ],
            "goal": "move revenue forward"
          },
          {
            "trigger": "enrollment_deadline_near",
            "actions": [
              "schedule_recurrence",
              "cross_sell_next_best_offer",
              "create_task"
            ],
            "goal": "increase LTV"
          }
        ],
        "quiet_hours": "21:00-08:00"
      },
      "document_flow": {
        "required_documents": [
          "expediente de admision",
          "documentos academicos",
          "carta de admision",
          "acuerdo de pago"
        ],
        "lifecycle_rules": [
          {
            "document": "expediente de admision",
            "required_before": "first committed step",
            "signature_required": true
          },
          {
            "document": "acuerdo de pago",
            "required_before": "handoff or continuity step",
            "signature_required": false
          }
        ]
      },
      "matching_engine": {
        "entity": "aspirante",
        "rules": [
          "program_interest match",
          "modality match",
          "campus match",
          "budget/aid fit"
        ],
        "next_best_match_outputs": [
          "best_owner",
          "best_resource_slot",
          "best_offer"
        ]
      }
    },
    "transactional_motor_v12": {
      "version": "v12_full_transactional",
      "aggregate_root": "student_admission_account",
      "main_business_entity": "aspirante",
      "transaction_unit": "admission_cycle",
      "system_of_record": {
        "write_model": [
          "commands",
          "events",
          "ledger",
          "aggregate_snapshots"
        ],
        "read_models": [
          "commercial_board",
          "operations_board",
          "finance_board",
          "continuity_board",
          "resource_load_board",
          "document_readiness_board",
          "revenue_levers_board"
        ],
        "idempotency_scope": [
          "organization_id",
          "vertical_id",
          "external_reference",
          "command_key"
        ],
        "audit_mode": "append_only_with_snapshots"
      },
      "transaction_primitives": {
        "commands": [
          "capture_intent",
          "qualify_record",
          "create_quote",
          "request_deposit",
          "reserve_capacity",
          "confirm_booking",
          "start_case",
          "approve_quote",
          "collect_payment",
          "start_fulfillment",
          "close_fulfillment",
          "schedule_recurrence",
          "issue_refund",
          "reactivate_customer",
          "assign_program_fit",
          "open_admission_file",
          "collect_enrollment_deposit",
          "activate_retention_plan"
        ],
        "events": [
          "intent_captured",
          "record_qualified",
          "quote_created",
          "deposit_requested",
          "capacity_reserved",
          "booking_confirmed",
          "case_started",
          "quote_approved",
          "payment_collected",
          "fulfillment_started",
          "fulfillment_closed",
          "recurrence_scheduled",
          "refund_issued",
          "customer_reactivated",
          "program_fit_assigned",
          "admission_file_opened",
          "enrollment_deposit_collected",
          "retention_plan_activated"
        ],
        "ledger_event_types": [
          "charge_opened",
          "deposit_collected",
          "installment_due",
          "payment_applied",
          "credit_issued",
          "refund_issued",
          "write_off_registered"
        ],
        "invariants": [
          "no admisión sin documentos mínimos",
          "no reservar lugar sin anticipo",
          "no aplicar beca sin validación",
          "todo pago debe referenciar quote, order o case activo",
          "todo cambio crítico debe emitir evento y renglón de auditoría",
          "ningún recurso se confirma dos veces en la misma ventana"
        ],
        "idempotency_keys": [
          "command_key",
          "payment_reference",
          "booking_reference",
          "external_message_id"
        ]
      },
      "aggregates": {
        "primary_record": {
          "name": "aspirante",
          "status_axis": [
            "commercial",
            "operations",
            "finance",
            "continuity"
          ]
        },
        "quote": {
          "name": "tuition_offer",
          "states": [
            "draft",
            "sent",
            "accepted",
            "expired",
            "lost"
          ]
        },
        "booking": {
          "name": "info_session_booking",
          "states": [
            "proposed",
            "reserved",
            "confirmed",
            "attended_or_executed",
            "missed_or_canceled"
          ]
        },
        "execution": {
          "name": "admission_and_enrollment",
          "states": [
            "pending",
            "ready",
            "in_progress",
            "blocked",
            "completed",
            "closed"
          ]
        },
        "payment_account": {
          "name": "payment_account",
          "states": [
            "open",
            "partially_paid",
            "paid",
            "overdue",
            "refunded"
          ]
        },
        "continuity": {
          "name": "retention_plan",
          "states": [
            "not_started",
            "active",
            "at_risk",
            "recovered",
            "closed"
          ]
        }
      },
      "orchestration": {
        "command_handlers": [
          "handle_capture_intent",
          "handle_qualify_record",
          "handle_create_quote",
          "handle_request_deposit",
          "handle_reserve_capacity",
          "handle_confirm_booking",
          "handle_start_case",
          "handle_approve_quote",
          "handle_assign_program_fit",
          "handle_open_admission_file",
          "handle_collect_enrollment_deposit",
          "handle_activate_retention_plan"
        ],
        "sagas": [
          "orientation_to_admission",
          "documents_to_enrollment",
          "non_enrolled_reactivation"
        ],
        "money_guards": [
          "quote_before_payment",
          "capacity_before_confirmation",
          "documents_before_execution",
          "balance_before_close"
        ],
        "read_model_refresh": [
          "on_every_event",
          "nightly_reconciliation",
          "pre_dashboard_cache"
        ]
      },
      "finance": {
        "money_objects": [
          "application_charge",
          "enrollment_deposit",
          "tuition_installment",
          "reentry_charge"
        ],
        "collection_modes": [
          "inscripción",
          "colegiatura",
          "financiamiento"
        ],
        "refund_modes": [
          "application_credit",
          "enrollment_release"
        ],
        "reconciliation_views": [
          "expected_vs_collected",
          "aging_balance",
          "refund_exposure",
          "cash_by_stage"
        ]
      },
      "operations": {
        "fulfillment_unit": "admission_cycle",
        "resource_locking": [
          "advisor",
          "interview_slot",
          "program_capacity"
        ],
        "dispatch_or_schedule_board": [
          "queued",
          "ready",
          "assigned",
          "in_progress",
          "blocked",
          "done"
        ],
        "handoff_rules": [
          "human_handoff_on_exception",
          "supervisor_handoff_on_money_risk",
          "operator_handoff_on_compliance_gap"
        ]
      },
      "audit_compliance": {
        "timeline_entities": [
          "aspirante",
          "tuition_offer",
          "info_session_booking",
          "admission_and_enrollment",
          "payment_account"
        ],
        "consent_gates": [
          "academic_documents",
          "admission_file",
          "financial_aid_form"
        ],
        "required_evidence": [
          "timeline_event",
          "actor",
          "timestamp",
          "before_after_snapshot"
        ],
        "retention_rules": [
          "audit_log_append_only",
          "documents_linked_to_primary_record",
          "payment_trace_non_destructive"
        ]
      },
      "transaction_views": {
        "commercial": [
          "orientation",
          "documents",
          "admission"
        ],
        "operations": [
          "cohort_fill",
          "deadline_tracking",
          "advisor_load"
        ],
        "finance": [
          "enrollment_pipeline",
          "installments",
          "scholarship_mix"
        ],
        "continuity": [
          "retention",
          "drop_risk",
          "reentry"
        ]
      },
      "command_catalog": [
        {
          "command": "capture_intent",
          "writes": "aspirante",
          "emits": "intent_captured",
          "guard": "no admisión sin documentos mínimos"
        },
        {
          "command": "qualify_record",
          "writes": "aspirante",
          "emits": "record_qualified",
          "guard": "no reservar lugar sin anticipo"
        },
        {
          "command": "create_quote",
          "writes": "aspirante",
          "emits": "quote_created",
          "guard": "no aplicar beca sin validación"
        },
        {
          "command": "request_deposit",
          "writes": "aspirante",
          "emits": "deposit_requested",
          "guard": "no admisión sin documentos mínimos"
        },
        {
          "command": "reserve_capacity",
          "writes": "aspirante",
          "emits": "capacity_reserved",
          "guard": "no reservar lugar sin anticipo"
        },
        {
          "command": "confirm_booking",
          "writes": "aspirante",
          "emits": "booking_confirmed",
          "guard": "no aplicar beca sin validación"
        },
        {
          "command": "start_case",
          "writes": "aspirante",
          "emits": "case_started",
          "guard": "no admisión sin documentos mínimos"
        },
        {
          "command": "approve_quote",
          "writes": "aspirante",
          "emits": "quote_approved",
          "guard": "no reservar lugar sin anticipo"
        },
        {
          "command": "assign_program_fit",
          "writes": "aspirante",
          "emits": "payment_collected",
          "guard": "no aplicar beca sin validación"
        },
        {
          "command": "open_admission_file",
          "writes": "aspirante",
          "emits": "fulfillment_started",
          "guard": "no admisión sin documentos mínimos"
        },
        {
          "command": "collect_enrollment_deposit",
          "writes": "aspirante",
          "emits": "fulfillment_closed",
          "guard": "no reservar lugar sin anticipo"
        },
        {
          "command": "activate_retention_plan",
          "writes": "aspirante",
          "emits": "recurrence_scheduled",
          "guard": "no aplicar beca sin validación"
        }
      ],
      "event_catalog": [
        {
          "event": "intent_captured",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "orientation_to_admission"
        },
        {
          "event": "record_qualified",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "documents_to_enrollment"
        },
        {
          "event": "quote_created",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "non_enrolled_reactivation"
        },
        {
          "event": "deposit_requested",
          "updates": [
            "timeline",
            "boards",
            "ledger"
          ],
          "next_action": "orientation_to_admission"
        },
        {
          "event": "capacity_reserved",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "documents_to_enrollment"
        },
        {
          "event": "booking_confirmed",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "non_enrolled_reactivation"
        },
        {
          "event": "case_started",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "orientation_to_admission"
        },
        {
          "event": "quote_approved",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "documents_to_enrollment"
        },
        {
          "event": "program_fit_assigned",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "non_enrolled_reactivation"
        },
        {
          "event": "admission_file_opened",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "orientation_to_admission"
        },
        {
          "event": "enrollment_deposit_collected",
          "updates": [
            "timeline",
            "boards",
            "ledger"
          ],
          "next_action": "documents_to_enrollment"
        },
        {
          "event": "retention_plan_activated",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "non_enrolled_reactivation"
        }
      ]
    },
    "subvertical_profiles": [],
    "recommended_subverticals": []
  },
  {
    "id": "beauty",
    "name": "WAOS Beauty",
    "short_name": "Belleza personal & self-care",
    "description": "Sistema operativo conversacional para belleza personal y self-care.",
    "problem": "Beauty vive en el caos del inbox: mucha pregunta repetitiva, mucha disponibilidad manual, mucho no-show, poco anticipo y poca recompra estructurada.",
    "subverticals": [
      "salón",
      "barbería",
      "uñas",
      "lashes",
      "brows",
      "maquillaje",
      "peinado social",
      "bridal beauty",
      "hair color",
      "skincare studio"
    ],
    "objects": [
      "especialista",
      "servicio",
      "duración",
      "cabina",
      "silla",
      "sucursal",
      "anticipo",
      "paquete",
      "historial",
      "frecuencia ideal",
      "rebook",
      "cliente beauty",
      "preferencias de servicio",
      "especialista preferido",
      "historial de servicios",
      "frecuencia recomendada",
      "paquetes",
      "membresías"
    ],
    "flows": [
      "consulta -> agenda",
      "agenda -> anticipo",
      "cita -> asistencia",
      "asistencia -> rebook",
      "rebook -> recurrencia"
    ],
    "kpis": [
      "ocupación",
      "no-show",
      "anticipo cobrado",
      "rebook rate",
      "add-on rate",
      "cliente recurrente",
      "recompra",
      "retención por especialista",
      "upgrade de ticket"
    ],
    "recommended_integrations": [
      "whatsapp",
      "calendar",
      "payments",
      "crm",
      "promotions"
    ],
    "default_services": [
      "corte",
      "color",
      "unas",
      "lashes",
      "facial"
    ],
    "default_faqs": [
      {
        "q": "¿Que servicio me recomiendan?",
        "a": "Podemos orientarte segun resultado deseado y tiempo disponible."
      },
      {
        "q": "¿Como veo horarios?",
        "a": "Si, podemos mostrar disponibilidad por servicio o especialista."
      },
      {
        "q": "¿Piden anticipo?",
        "a": "Si, si tu negocio lo requiere, el bot puede cobrar anticipo y confirmar cita."
      },
      {
        "q": "¿Puedo reagendar?",
        "a": "Si, podemos aplicar politica de cancelacion o rebook segun tus reglas."
      }
    ],
    "behavior": {
      "tone": "cercano y aspiracional",
      "response_length": "corta",
      "use_emojis": false,
      "sales_intensity": "alta",
      "offer_promotions_when": "after_service_interest_detected",
      "escalate_when": [
        "queja de servicio",
        "tema sensible de imagen"
      ],
      "insistence_policy": "respectful",
      "can_share_price_directly": true,
      "can_negotiate": false,
      "can_mention_stock": false,
      "auto_send_images": true,
      "bot_mode": "agenda_y_rebook",
      "active_channels": [
        "whatsapp",
        "instagram_dm"
      ],
      "forbidden_topics": [
        "promesas esteticas absolutas"
      ],
      "required_phrases": [
        "te ayudo a elegir servicio y horario",
        "puedo reservar con tu especialista ideal",
        "te sigo",
        "si la pregunta viene rara, igual te la aterrizo",
        "te lo aterrizo a tu caso"
      ],
      "fallback_message": "Te ayudo a elegir servicio, ver disponibilidad y dejar confirmada tu cita. Si la pregunta viene rara, en broma o medio fuera de tema, igual te sigo y la aterrizamos al negocio.",
      "humor_policy": "light_contextual",
      "strange_question_policy": "respond_validate_reframe_sell_move"
    },
    "followup_rules": [
      {
        "type": "no_response",
        "delay_minutes": 60,
        "max_attempts": 2,
        "message_template": "¿Quieres que te comparta horarios o te recomiende el servicio ideal?"
      },
      {
        "type": "post_quote",
        "delay_minutes": 720,
        "max_attempts": 2,
        "message_template": "Todavia puedo ayudarte a reservar tu cita o a elegir add-ons para tu servicio."
      },
      {
        "type": "reactivation",
        "delay_minutes": 20160,
        "max_attempts": 1,
        "message_template": "Ya podria tocar tu siguiente cita ideal. ¿Quieres que te comparta disponibilidad?"
      }
    ],
    "templates": [
      {
        "template_key": "service_match",
        "title": "Recomendacion de servicio",
        "content": "Cuentame que resultado buscas y te recomiendo servicio, especialista y tiempo estimado.",
        "variables": []
      },
      {
        "template_key": "appointment_hold",
        "title": "Apartado de cita",
        "content": "Tengo espacio para {{service_name}} el {{date}} a las {{time}}. ¿Quieres que lo deje apartado?",
        "variables": [
          "service_name",
          "date",
          "time"
        ]
      },
      {
        "template_key": "deposit",
        "title": "Cobro de anticipo",
        "content": "Para confirmar tu cita, te comparto el link de anticipo ahora mismo.",
        "variables": []
      },
      {
        "template_key": "rebook",
        "title": "Rebook sugerido",
        "content": "Para mantener tu resultado ideal, te sugiero reservar tu siguiente cita desde ahora. ¿Quieres que te muestre horarios?",
        "variables": []
      },
      {
        "template_key": "inactive_client",
        "title": "Cliente inactivo",
        "content": "Hace tiempo que no te vemos. Si quieres, te recomiendo servicio ideal y disponibilidad actual.",
        "variables": []
      }
    ],
    "config_overrides": {
      "objective_secondary": [
        "agendar",
        "upsell",
        "reactivar"
      ],
      "policies": [
        "No prometer resultados absolutos",
        "Escalar reclamos o casos sensibles"
      ],
      "can_say": [
        "servicios",
        "especialista",
        "duracion",
        "anticipo",
        "rebook"
      ],
      "cannot_say": [
        "garantias absolutas de resultado"
      ],
      "whatsapp_flows": [
        "recomendacion_servicio",
        "anticipo_cita",
        "rebook_sugerido",
        "reactivacion_cliente"
      ],
      "appointment_duration_minutes": 60,
      "handoff_keywords": [
        "queja",
        "alergia",
        "inconformidad"
      ],
      "high_score_threshold": 72
    },
    "portfolio_tier": "tier_2",
    "master_thesis": "Sistema operativo conversacional para belleza personal y self-care que llena agenda, cobra anticipos, reduce no-show y multiplica rebook.",
    "buyer": {
      "primary": "Dueño de salón/beauty lounge o gerente operativo",
      "secondary": [
        "recepción",
        "especialistas",
        "coordinación bridal"
      ]
    },
    "one_pager": {
      "headline": "WAOS Beauty",
      "thesis": "WhatsApp deja de ser chat de disponibilidad y se convierte en agenda comercial con anticipos y rebook.",
      "problem": "Se responde mucho pero se monetiza poco por no-show y falta de seguimiento posterior.",
      "promise": "Cada conversación debe cerrar en cita, anticipo, add-on o siguiente visita.",
      "monetizes": [
        "cita",
        "anticipo",
        "add-ons",
        "paquetes",
        "frecuencia ideal",
        "eventos especiales"
      ],
      "packaging": [
        "setup beauty",
        "agenda + anticipos",
        "rebook por especialista",
        "campañas pre-evento y winback"
      ],
      "strategic_care": "Vertical de gran volumen y fácil demostración; ideal para demos rápidas y cierres consultivos simples."
    },
    "demo_flow": [
      "La clienta entra preguntando por servicio, precio o disponibilidad.",
      "WAOS recomienda servicio y especialista.",
      "Muestra espacios disponibles y cobra anticipo.",
      "Confirma cita y manda recordatorio.",
      "Después del servicio propone add-ons y siguiente cita ideal.",
      "Si la clienta desaparece, activa winback por frecuencia recomendada."
    ],
    "native_objects": {
      "core": [
        "cliente",
        "servicio",
        "especialista",
        "duración",
        "cabina/silla",
        "sede",
        "cliente beauty"
      ],
      "commercial": [
        "anticipo",
        "paquete",
        "add-on",
        "promoción"
      ],
      "operations": [
        "historial de servicio",
        "no-show",
        "rebook",
        "frecuencia ideal"
      ]
    },
    "pipeline": {
      "primary": {
        "name": "Agenda y recurrencia",
        "states": [
          "lead nuevo",
          "servicio identificado",
          "cita ofrecida",
          "cita agendada",
          "anticipo pendiente",
          "confirmada",
          "asistida",
          "post servicio",
          "rebook sugerido",
          "rebook agendado",
          "inactiva",
          "reactivada"
        ]
      },
      "secondary": [
        {
          "name": "Eventos especiales",
          "states": [
            "consulta",
            "cotización",
            "reserva",
            "confirmación",
            "servicio realizado"
          ]
        }
      ]
    },
    "bot_playbook": {
      "must_do": [
        "recomendar servicio",
        "mostrar disponibilidad",
        "asignar especialista",
        "cobrar anticipo",
        "confirmar",
        "reprogramar",
        "vender add-ons",
        "sugerir siguiente cita",
        "nunca quedarse seco ante bromas, preguntas raras o cambios bruscos de tema",
        "usar humor ligero cuando sume, sin sonar payaso ni poco serio",
        "validar el momento y luego reencauzar la conversacion al negocio",
        "cerrar siempre con una pregunta util o siguiente paso"
      ],
      "must_ask": [
        "servicio buscado",
        "fecha deseada",
        "especialista preferida",
        "sede",
        "si es primera vez",
        "objetivo o estilo buscado",
        "que parte del negocio se esta atorando mas",
        "si quiere que se lo aterrice a su caso"
      ],
      "objections": [
        "precio",
        "disponibilidad",
        "duración",
        "quiero pensarlo",
        "no sé qué servicio me conviene"
      ],
      "escalate_when": [
        "cambio técnico complejo",
        "bridal o evento grande",
        "reclamo",
        "caso muy personalizado"
      ],
      "forbidden": [
        "prometer disponibilidad no confirmada",
        "recomendaciones técnicas fuera de protocolo"
      ],
      "success_signals": [
        "quiero cita",
        "mándame horarios",
        "apártamela",
        "¿cómo pago el anticipo?",
        "quiero con esa especialista"
      ],
      "style": [
        "humor ligero",
        "manejo de preguntas raras",
        "reencuadre comercial"
      ]
    },
    "automation_sequences": [
      {
        "key": "beauty_confirmation",
        "name": "Confirmación y anticipo",
        "trigger": "cita agendada",
        "goal": "reducir no-show",
        "steps": [
          "recordar anticipo",
          "confirmar cita",
          "recordatorio 24h"
        ]
      },
      {
        "key": "beauty_post_service",
        "name": "Post servicio",
        "trigger": "servicio realizado",
        "goal": "elevar experiencia y add-ons",
        "steps": [
          "pedir feedback",
          "sugerir add-on",
          "proponer siguiente cita"
        ]
      },
      {
        "key": "beauty_rebook",
        "name": "Rebook por frecuencia ideal",
        "trigger": "ventana ideal cumplida",
        "goal": "recurrencia",
        "steps": [
          "recordatorio",
          "mostrar horarios",
          "cerrar cita"
        ]
      },
      {
        "key": "beauty_winback",
        "name": "Winback beauty",
        "trigger": "cliente inactiva",
        "goal": "reactivar",
        "steps": [
          "mensaje personalizado",
          "oferta relevante",
          "agenda rápida"
        ]
      }
    ],
    "dashboard": {
      "north_star": "Asistencia que convierte en rebook.",
      "sections": [
        {
          "name": "Operación",
          "metrics": [
            "ocupación",
            "no-show",
            "anticipos cobrados",
            "huecos llenados"
          ]
        },
        {
          "name": "Revenue",
          "metrics": [
            "ticket promedio",
            "add-ons",
            "revenue por especialista",
            "revenue por categoría"
          ]
        },
        {
          "name": "Retención",
          "metrics": [
            "rebook rate",
            "frecuencia promedio",
            "cliente recurrente",
            "winback rate"
          ]
        },
        {
          "name": "Funnel",
          "metrics": [
            "lead a cita",
            "cita a asistencia",
            "asistencia a rebook",
            "rebook a recurrencia"
          ]
        }
      ]
    },
    "hardening_model": {
      "goal": "Pasar de preset inteligente a sistema especialista",
      "wave": "ola_2",
      "entity_queen": "cliente beauty",
      "core_common": true,
      "domain_by_vertical": true,
      "playbooks_by_subvertical": true,
      "kpis_by_vertical": true,
      "pricing_by_vertical": true,
      "journeys_by_vertical": true,
      "reusable_modules": [
        "intake / calificación",
        "agenda / recursos",
        "cotización / propuesta",
        "pago / anticipo / membresía",
        "seguimiento / recurrencia",
        "reporting vertical"
      ],
      "minimum_viable_hardening": [
        "1 entidad reina",
        "1 pipeline propio",
        "1 cotización propia",
        "1 recurrencia propia",
        "1 dashboard propio"
      ],
      "hard_checklist": [
        "tiene entidad principal propia",
        "tiene pipeline específico",
        "tiene cotización o pricing del nicho",
        "tiene agenda o recursos del nicho",
        "tiene postventa o recurrencia del nicho",
        "tiene documentos o compliance del nicho",
        "tiene KPIs del nicho",
        "tiene 3 automatizaciones que mueven dinero",
        "tiene 2 pruebas e2e de negocio",
        "tiene subplaybooks por subvertical",
        "entidad principal propia",
        "pipeline específico",
        "pricing del nicho",
        "agenda y recursos del nicho",
        "postventa o recurrencia del nicho",
        "documentos o compliance del nicho",
        "KPIs del nicho",
        "3 automatizaciones que mueven dinero",
        "2 pruebas e2e de negocio",
        "subplaybooks por subvertical",
        "runtime ejecutable por vertical"
      ]
    },
    "specialist_layers": {
      "persistent_entities": [
        "cliente beauty",
        "preferencias de servicio",
        "especialista preferido",
        "historial de servicios",
        "frecuencia recomendada",
        "paquetes",
        "membresías",
        "rebook"
      ],
      "business_pipeline": {
        "primary_entity": "cliente beauty",
        "primary_pipeline": {
          "name": "Agenda y recurrencia",
          "states": [
            "lead nuevo",
            "servicio identificado",
            "cita ofrecida",
            "cita agendada",
            "anticipo pendiente",
            "confirmada",
            "asistida",
            "post servicio",
            "rebook sugerido",
            "rebook agendado",
            "inactiva",
            "reactivada"
          ]
        },
        "secondary_pipelines": [
          {
            "name": "Eventos especiales",
            "states": [
              "consulta",
              "cotización",
              "reserva",
              "confirmación",
              "servicio realizado"
            ]
          }
        ]
      },
      "pricing_and_quotes": [
        "cotización por servicio y especialista",
        "membresías",
        "upsell de ticket"
      ],
      "agenda_and_resources": [
        "cabina",
        "estilista",
        "especialista",
        "silla",
        "agenda por recurso"
      ],
      "post_sale_and_recurrence": [
        "rebook post-servicio",
        "fidelidad / puntos",
        "mantenimiento por frecuencia recomendada"
      ],
      "documents_compliance": [
        "ficha de cliente",
        "consentimiento opcional",
        "antes / después",
        "políticas de cancelación"
      ],
      "kpis_that_matter": [
        "ocupación",
        "no-show",
        "anticipo cobrado",
        "rebook rate",
        "add-on rate",
        "cliente recurrente",
        "recompra",
        "retención por especialista",
        "upgrade de ticket"
      ],
      "money_automations": [
        "recordatorio de rebook",
        "upgrade a membresía",
        "winback por no-show o caída de frecuencia"
      ]
    },
    "domain_contract": {
      "vertical_entity_types": [
        "cliente beauty",
        "preferencias de servicio",
        "especialista preferido",
        "historial de servicios",
        "frecuencia recomendada",
        "paquetes",
        "membresías",
        "rebook"
      ],
      "vertical_pipeline_stages": {
        "primary": [
          "lead nuevo",
          "servicio identificado",
          "cita ofrecida",
          "cita agendada",
          "anticipo pendiente",
          "confirmada",
          "asistida",
          "post servicio",
          "rebook sugerido",
          "rebook agendado",
          "inactiva",
          "reactivada"
        ],
        "secondary": [
          [
            "consulta",
            "cotización",
            "reserva",
            "confirmación",
            "servicio realizado"
          ]
        ]
      },
      "vertical_quote_types": [
        "servicio individual",
        "paquete",
        "membresía",
        "upgrade",
        "rebook prepagado"
      ],
      "vertical_resource_types": [
        "cabina",
        "estilista",
        "especialista",
        "silla",
        "agenda por recurso"
      ],
      "vertical_followup_policies": [
        "rebook post-servicio",
        "fidelidad / puntos",
        "mantenimiento por frecuencia recomendada"
      ],
      "vertical_kpi_definitions": [
        "ocupación",
        "no-show",
        "anticipo cobrado",
        "rebook rate",
        "add-on rate",
        "cliente recurrente",
        "recompra",
        "retención por especialista",
        "upgrade de ticket"
      ],
      "vertical_playbooks": [
        "uñas",
        "cabello",
        "brows",
        "lashes",
        "skin bar",
        "spa"
      ],
      "vertical_document_types": [
        "ficha de cliente",
        "consentimiento opcional",
        "antes / después",
        "políticas de cancelación"
      ]
    },
    "subvertical_playbooks": [
      {
        "name": "uñas",
        "focus": "Playbook operativo y comercial para uñas"
      },
      {
        "name": "cabello",
        "focus": "Playbook operativo y comercial para cabello"
      },
      {
        "name": "brows",
        "focus": "Playbook operativo y comercial para brows"
      },
      {
        "name": "lashes",
        "focus": "Playbook operativo y comercial para lashes"
      },
      {
        "name": "skin bar",
        "focus": "Playbook operativo y comercial para skin bar"
      },
      {
        "name": "spa",
        "focus": "Playbook operativo y comercial para spa"
      }
    ],
    "business_e2e_tests": [
      {
        "name": "lead agenda servicio, asiste y deja rebook programado",
        "status": "designed"
      },
      {
        "name": "cliente frecuente sube a membresía tras tercer servicio",
        "status": "designed"
      }
    ],
    "vertical_runtime": {
      "pipeline_machine": {
        "primary_pipeline": "Agenda y recurrencia",
        "entity": "cliente beauty",
        "states": [
          "lead nuevo",
          "servicio identificado",
          "cita ofrecida",
          "cita agendada",
          "anticipo pendiente",
          "confirmada",
          "asistida",
          "post servicio",
          "rebook sugerido",
          "rebook agendado",
          "inactiva",
          "reactivada"
        ],
        "transitions": [
          {
            "from": "lead nuevo",
            "to": "servicio identificado",
            "trigger": "qualification_complete",
            "business_effect": "advance opportunity"
          },
          {
            "from": "servicio identificado",
            "to": "cita ofrecida",
            "trigger": "membership_offer",
            "business_effect": "open commercial step"
          },
          {
            "from": "inactiva",
            "to": "reactivada",
            "trigger": "successful_outcome",
            "business_effect": "realize revenue or continuity"
          },
          {
            "from": "inactiva",
            "to": "at_risk",
            "trigger": "visit_completed",
            "business_effect": "activate retention sequence"
          }
        ],
        "at_risk_state": "at_risk",
        "closed_states": [
          "reactivada"
        ]
      },
      "pricing_engine": {
        "quote_types": [
          "servicio",
          "paquete",
          "membresia",
          "upgrade premium"
        ],
        "pricing_basis": "service + stylist tier + add-ons + membership",
        "rules": [
          {
            "rule": "base price by servicio type",
            "effect": "set base_price"
          },
          {
            "rule": "premium or urgent add-ons increase quote",
            "effect": "add surcharge"
          },
          {
            "rule": "bundle, membership or financing can lower immediate friction",
            "effect": "recommend package or installments"
          }
        ],
        "deposit_policy": "request advance when capacity, specialist time or inventory must be secured"
      },
      "resource_capacity": {
        "resource_types": [
          "estilista",
          "cabina",
          "silla",
          "room",
          "franja de pico"
        ],
        "capacity_basis": "chair/cabin availability, stylist schedule and service duration",
        "constraints": [
          "avoid double booking of critical resources",
          "respect service duration and cleanup/buffer time",
          "prioritize higher urgency and higher close probability cases"
        ],
        "priority_queue": "especialista preferido, cabina y rebook"
      },
      "recurrence_engine": {
        "policies": [
          {
            "type": "rebook_cycle",
            "interval_days": 28,
            "anchor": "cliente beauty"
          },
          {
            "type": "membership_renewal",
            "interval_days": 30,
            "anchor": "cliente beauty"
          },
          {
            "type": "loyalty_nudge",
            "interval_days": 45,
            "anchor": "cliente beauty"
          }
        ],
        "reactivation_window_days": 45,
        "goal": "protect retention, repeat revenue and continuity"
      },
      "kpi_engine": {
        "north_star": "Asistencia que convierte en rebook.",
        "definitions": [
          {
            "name": "rebook_rate",
            "formula": "rebooked_visits / completed_visits"
          },
          {
            "name": "retention_by_specialist",
            "formula": "repeat_clients / clients_by_specialist"
          },
          {
            "name": "ticket_upgrade",
            "formula": "upsold_tickets / completed_visits"
          }
        ],
        "leading_indicators": [
          "visit_completed",
          "rebook_missing",
          "no_response_7d"
        ]
      },
      "automation_engine": {
        "money_automation_policies": [
          {
            "trigger": "visit_completed",
            "actions": [
              "send_followup",
              "escalate_owner",
              "offer_relevant_next_step"
            ],
            "goal": "save conversion or retention"
          },
          {
            "trigger": "rebook_missing",
            "actions": [
              "send_quote_or_payment_link",
              "remind_deadline",
              "notify_human"
            ],
            "goal": "move revenue forward"
          },
          {
            "trigger": "high_value_client_idle",
            "actions": [
              "schedule_recurrence",
              "cross_sell_next_best_offer",
              "create_task"
            ],
            "goal": "increase LTV"
          }
        ],
        "quiet_hours": "21:00-08:00"
      },
      "document_flow": {
        "required_documents": [
          "ficha de preferencias",
          "consentimiento basico",
          "before_after opcional",
          "membresia"
        ],
        "lifecycle_rules": [
          {
            "document": "ficha de preferencias",
            "required_before": "first committed step",
            "signature_required": true
          },
          {
            "document": "membresia",
            "required_before": "handoff or continuity step",
            "signature_required": false
          }
        ]
      },
      "matching_engine": {
        "entity": "cliente beauty",
        "rules": [
          "service_preference == specialist.skill",
          "preferred_staff_match",
          "time_window_match",
          "branch_match"
        ],
        "next_best_match_outputs": [
          "best_owner",
          "best_resource_slot",
          "best_offer"
        ]
      }
    },
    "transactional_motor_v12": {
      "version": "v12_full_transactional",
      "aggregate_root": "beauty_client_journey",
      "main_business_entity": "cliente beauty",
      "transaction_unit": "service_rebook_cycle",
      "system_of_record": {
        "write_model": [
          "commands",
          "events",
          "ledger",
          "aggregate_snapshots"
        ],
        "read_models": [
          "commercial_board",
          "operations_board",
          "finance_board",
          "continuity_board",
          "resource_load_board",
          "document_readiness_board",
          "revenue_levers_board"
        ],
        "idempotency_scope": [
          "organization_id",
          "vertical_id",
          "external_reference",
          "command_key"
        ],
        "audit_mode": "append_only_with_snapshots"
      },
      "transaction_primitives": {
        "commands": [
          "capture_intent",
          "qualify_record",
          "create_quote",
          "request_deposit",
          "reserve_capacity",
          "confirm_booking",
          "start_case",
          "approve_quote",
          "collect_payment",
          "start_fulfillment",
          "close_fulfillment",
          "schedule_recurrence",
          "issue_refund",
          "reactivate_customer",
          "reserve_specialist",
          "sell_membership",
          "rebook_post_service",
          "issue_loyalty_reward"
        ],
        "events": [
          "intent_captured",
          "record_qualified",
          "quote_created",
          "deposit_requested",
          "capacity_reserved",
          "booking_confirmed",
          "case_started",
          "quote_approved",
          "payment_collected",
          "fulfillment_started",
          "fulfillment_closed",
          "recurrence_scheduled",
          "refund_issued",
          "customer_reactivated",
          "specialist_reserved",
          "membership_sold",
          "post_service_rebooked",
          "loyalty_reward_issued"
        ],
        "ledger_event_types": [
          "charge_opened",
          "deposit_collected",
          "installment_due",
          "payment_applied",
          "credit_issued",
          "refund_issued",
          "write_off_registered"
        ],
        "invariants": [
          "no confirmar cita sin recurso libre",
          "no aplicar paquete sin especialista compatible",
          "no cerrar visita sin rebook sugerido",
          "todo pago debe referenciar quote, order o case activo",
          "todo cambio crítico debe emitir evento y renglón de auditoría",
          "ningún recurso se confirma dos veces en la misma ventana"
        ],
        "idempotency_keys": [
          "command_key",
          "payment_reference",
          "booking_reference",
          "external_message_id"
        ]
      },
      "aggregates": {
        "primary_record": {
          "name": "cliente beauty",
          "status_axis": [
            "commercial",
            "operations",
            "finance",
            "continuity"
          ]
        },
        "quote": {
          "name": "beauty_package_quote",
          "states": [
            "draft",
            "sent",
            "accepted",
            "expired",
            "lost"
          ]
        },
        "booking": {
          "name": "beauty_appointment",
          "states": [
            "proposed",
            "reserved",
            "confirmed",
            "attended_or_executed",
            "missed_or_canceled"
          ]
        },
        "execution": {
          "name": "service_visit",
          "states": [
            "pending",
            "ready",
            "in_progress",
            "blocked",
            "completed",
            "closed"
          ]
        },
        "payment_account": {
          "name": "payment_account",
          "states": [
            "open",
            "partially_paid",
            "paid",
            "overdue",
            "refunded"
          ]
        },
        "continuity": {
          "name": "rebook_membership_plan",
          "states": [
            "not_started",
            "active",
            "at_risk",
            "recovered",
            "closed"
          ]
        }
      },
      "orchestration": {
        "command_handlers": [
          "handle_capture_intent",
          "handle_qualify_record",
          "handle_create_quote",
          "handle_request_deposit",
          "handle_reserve_capacity",
          "handle_confirm_booking",
          "handle_start_case",
          "handle_approve_quote",
          "handle_reserve_specialist",
          "handle_sell_membership",
          "handle_rebook_post_service",
          "handle_issue_loyalty_reward"
        ],
        "sagas": [
          "first_visit_to_rebook",
          "rebook_to_membership",
          "no_show_recovery"
        ],
        "money_guards": [
          "quote_before_payment",
          "capacity_before_confirmation",
          "documents_before_execution",
          "balance_before_close"
        ],
        "read_model_refresh": [
          "on_every_event",
          "nightly_reconciliation",
          "pre_dashboard_cache"
        ]
      },
      "finance": {
        "money_objects": [
          "booking_deposit",
          "service_charge",
          "membership_charge",
          "upgrade_charge"
        ],
        "collection_modes": [
          "anticipo",
          "contra servicio",
          "membresía"
        ],
        "refund_modes": [
          "service_credit",
          "loyalty_adjustment"
        ],
        "reconciliation_views": [
          "expected_vs_collected",
          "aging_balance",
          "refund_exposure",
          "cash_by_stage"
        ]
      },
      "operations": {
        "fulfillment_unit": "service_rebook_cycle",
        "resource_locking": [
          "specialist",
          "chair_or_cabin",
          "time_block"
        ],
        "dispatch_or_schedule_board": [
          "queued",
          "ready",
          "assigned",
          "in_progress",
          "blocked",
          "done"
        ],
        "handoff_rules": [
          "human_handoff_on_exception",
          "supervisor_handoff_on_money_risk",
          "operator_handoff_on_compliance_gap"
        ]
      },
      "audit_compliance": {
        "timeline_entities": [
          "cliente beauty",
          "beauty_package_quote",
          "beauty_appointment",
          "service_visit",
          "payment_account"
        ],
        "consent_gates": [
          "service_preference_card",
          "consentimiento_imagen",
          "membership_terms"
        ],
        "required_evidence": [
          "timeline_event",
          "actor",
          "timestamp",
          "before_after_snapshot"
        ],
        "retention_rules": [
          "audit_log_append_only",
          "documents_linked_to_primary_record",
          "payment_trace_non_destructive"
        ]
      },
      "transaction_views": {
        "commercial": [
          "booking",
          "upsell",
          "membership"
        ],
        "operations": [
          "agenda",
          "rebook",
          "specialist_retention"
        ],
        "finance": [
          "ticket_upgrade",
          "membership_mrr",
          "no_show_loss"
        ],
        "continuity": [
          "service_frequency",
          "loyalty",
          "recompra"
        ]
      },
      "command_catalog": [
        {
          "command": "capture_intent",
          "writes": "cliente beauty",
          "emits": "intent_captured",
          "guard": "no confirmar cita sin recurso libre"
        },
        {
          "command": "qualify_record",
          "writes": "cliente beauty",
          "emits": "record_qualified",
          "guard": "no aplicar paquete sin especialista compatible"
        },
        {
          "command": "create_quote",
          "writes": "cliente beauty",
          "emits": "quote_created",
          "guard": "no cerrar visita sin rebook sugerido"
        },
        {
          "command": "request_deposit",
          "writes": "cliente beauty",
          "emits": "deposit_requested",
          "guard": "no confirmar cita sin recurso libre"
        },
        {
          "command": "reserve_capacity",
          "writes": "cliente beauty",
          "emits": "capacity_reserved",
          "guard": "no aplicar paquete sin especialista compatible"
        },
        {
          "command": "confirm_booking",
          "writes": "cliente beauty",
          "emits": "booking_confirmed",
          "guard": "no cerrar visita sin rebook sugerido"
        },
        {
          "command": "start_case",
          "writes": "cliente beauty",
          "emits": "case_started",
          "guard": "no confirmar cita sin recurso libre"
        },
        {
          "command": "approve_quote",
          "writes": "cliente beauty",
          "emits": "quote_approved",
          "guard": "no aplicar paquete sin especialista compatible"
        },
        {
          "command": "reserve_specialist",
          "writes": "cliente beauty",
          "emits": "payment_collected",
          "guard": "no cerrar visita sin rebook sugerido"
        },
        {
          "command": "sell_membership",
          "writes": "cliente beauty",
          "emits": "fulfillment_started",
          "guard": "no confirmar cita sin recurso libre"
        },
        {
          "command": "rebook_post_service",
          "writes": "cliente beauty",
          "emits": "fulfillment_closed",
          "guard": "no aplicar paquete sin especialista compatible"
        },
        {
          "command": "issue_loyalty_reward",
          "writes": "cliente beauty",
          "emits": "recurrence_scheduled",
          "guard": "no cerrar visita sin rebook sugerido"
        }
      ],
      "event_catalog": [
        {
          "event": "intent_captured",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "first_visit_to_rebook"
        },
        {
          "event": "record_qualified",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "rebook_to_membership"
        },
        {
          "event": "quote_created",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "no_show_recovery"
        },
        {
          "event": "deposit_requested",
          "updates": [
            "timeline",
            "boards",
            "ledger"
          ],
          "next_action": "first_visit_to_rebook"
        },
        {
          "event": "capacity_reserved",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "rebook_to_membership"
        },
        {
          "event": "booking_confirmed",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "no_show_recovery"
        },
        {
          "event": "case_started",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "first_visit_to_rebook"
        },
        {
          "event": "quote_approved",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "rebook_to_membership"
        },
        {
          "event": "specialist_reserved",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "no_show_recovery"
        },
        {
          "event": "membership_sold",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "first_visit_to_rebook"
        },
        {
          "event": "post_service_rebooked",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "rebook_to_membership"
        },
        {
          "event": "loyalty_reward_issued",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "no_show_recovery"
        }
      ]
    },
    "subvertical_profiles": [],
    "recommended_subverticals": []
  },
  {
    "id": "field-services",
    "name": "WAOS Field Services",
    "short_name": "Home services & field services",
    "description": "Sistema operativo conversacional para servicios en sitio.",
    "problem": "Field services falla cuando no clasifica urgencia, no levanta contexto suficiente, no asigna técnico rápido, no da visibilidad de estatus y no convierte servicio puntual en mantenimiento.",
    "subverticals": [
      "HVAC",
      "plomería",
      "electricidad",
      "cerrajería",
      "paneles solares",
      "limpieza especializada",
      "fumigación",
      "jardinería",
      "mantenimiento residencial",
      "seguridad electrónica"
    ],
    "objects": [
      "incidente",
      "urgencia",
      "zona",
      "técnico",
      "orden de trabajo",
      "visita",
      "evidencia",
      "cotización",
      "garantía",
      "contrato de mantenimiento",
      "sitio de servicio",
      "incidencia / trabajo",
      "prioridad",
      "técnico / cuadrilla",
      "ventana de atención",
      "materiales / evidencia",
      "firma de cierre"
    ],
    "flows": [
      "solicitud -> intake",
      "intake -> visita",
      "visita -> servicio",
      "servicio -> cobro",
      "postservicio -> garantía/mantenimiento"
    ],
    "kpis": [
      "tiempo de respuesta",
      "tiempo a visita",
      "solicitud a visita",
      "primera visita resuelta",
      "mantenimiento vendido",
      "satisfacción",
      "tiempo a asignación",
      "first-time fix",
      "ticket",
      "cancelación",
      "puntualidad"
    ],
    "recommended_integrations": [
      "whatsapp",
      "calendar",
      "operations",
      "payments",
      "crm"
    ],
    "default_services": [
      "visita diagnostica",
      "reparacion urgente",
      "mantenimiento preventivo",
      "servicio en sitio",
      "garantia"
    ],
    "default_faqs": [
      {
        "q": "¿Pueden atender urgencias?",
        "a": "Si, el bot clasifica prioridad y recopila lo necesario para asignar tecnico o visita."
      },
      {
        "q": "¿Piden fotos o ubicacion?",
        "a": "Si, podemos solicitar evidencia y direccion para despachar mejor."
      },
      {
        "q": "¿Dan rango de precio?",
        "a": "Podemos estimar un servicio inicial o programar visita diagnostica."
      },
      {
        "q": "¿Manejan garantia?",
        "a": "Si, podemos dejar seguimiento o garantia posterior si aplica."
      }
    ],
    "behavior": {
      "tone": "directo y resolutivo",
      "response_length": "media",
      "use_emojis": false,
      "sales_intensity": "media",
      "offer_promotions_when": "after_issue_categorized",
      "escalate_when": [
        "riesgo electrico",
        "fuga grave",
        "seguridad",
        "emergencia"
      ],
      "insistence_policy": "respectful",
      "can_share_price_directly": true,
      "can_negotiate": false,
      "can_mention_stock": true,
      "auto_send_images": false,
      "bot_mode": "triage_y_despacho",
      "active_channels": [
        "whatsapp",
        "webchat"
      ],
      "forbidden_topics": [
        "garantia total sin diagnostico"
      ],
      "required_phrases": [
        "te ayudo a clasificar la urgencia",
        "puedo coordinar visita o tecnico",
        "te sigo",
        "si la pregunta viene rara, igual te la aterrizo",
        "te lo aterrizo a tu caso"
      ],
      "fallback_message": "Te ayudo a clasificar el problema, tomar datos clave y coordinar la visita correcta. Si la pregunta viene rara, en broma o medio fuera de tema, igual te sigo y la aterrizamos al negocio.",
      "humor_policy": "light_contextual",
      "strange_question_policy": "respond_validate_reframe_sell_move"
    },
    "followup_rules": [
      {
        "type": "no_response",
        "delay_minutes": 45,
        "max_attempts": 2,
        "message_template": "¿Quieres que retomemos tu servicio y coordinemos tecnico o visita?"
      },
      {
        "type": "post_quote",
        "delay_minutes": 720,
        "max_attempts": 2,
        "message_template": "Sigo pendiente por si quieres avanzar con la visita o aceptar el servicio propuesto."
      },
      {
        "type": "reactivation",
        "delay_minutes": 43200,
        "max_attempts": 1,
        "message_template": "Si quieres, te ayudo a programar mantenimiento preventivo o revisar garantia de servicio."
      }
    ],
    "templates": [
      {
        "template_key": "incident_triage",
        "title": "Triage de incidente",
        "content": "Cuentame que sucede, si es urgente y comparteme ubicacion o foto para asignar mejor la visita.",
        "variables": []
      },
      {
        "template_key": "dispatch_visit",
        "title": "Despacho de visita",
        "content": "Puedo coordinar una visita para {{date}} en tu zona. ¿Te funciona?",
        "variables": [
          "date"
        ]
      },
      {
        "template_key": "estimate",
        "title": "Estimacion inicial",
        "content": "Con lo que nos compartes, podemos darte una estimacion inicial o agendar visita diagnostica.",
        "variables": []
      },
      {
        "template_key": "status_field",
        "title": "Estatus de servicio",
        "content": "Tu orden esta en {{status}}. Si hay ajuste o llegada estimada, te lo comparto por aqui.",
        "variables": [
          "status"
        ]
      },
      {
        "template_key": "warranty_followup",
        "title": "Seguimiento garantia",
        "content": "Te escribimos para confirmar que todo quedo bien y ayudarte con cualquier garantia o ajuste.",
        "variables": []
      }
    ],
    "config_overrides": {
      "objective_secondary": [
        "calificar",
        "agendar",
        "cobrar"
      ],
      "policies": [
        "Escalar riesgos de seguridad o emergencias",
        "No garantizar solucion final sin visita"
      ],
      "can_say": [
        "urgencia",
        "tecnico",
        "visita",
        "estimacion",
        "garantia"
      ],
      "cannot_say": [
        "diagnostico final sin visita",
        "garantia total sin validacion"
      ],
      "whatsapp_flows": [
        "triage_servicio",
        "agenda_visita_tecnica",
        "estimacion_inicial",
        "seguimiento_garantia"
      ],
      "appointment_duration_minutes": 60,
      "handoff_keywords": [
        "emergencia",
        "riesgo",
        "seguridad",
        "seguro"
      ],
      "high_score_threshold": 90
    },
    "portfolio_tier": "tier_1",
    "master_thesis": "Sistema operativo conversacional para servicios en sitio que convierte WhatsApp en intake, despacho, seguimiento de visita, garantía y mantenimiento.",
    "buyer": {
      "primary": "Dueño o gerente de operación de servicio en sitio",
      "secondary": [
        "dispatcher",
        "supervisor técnico",
        "equipo comercial"
      ]
    },
    "one_pager": {
      "headline": "WAOS Field Services",
      "thesis": "WhatsApp se vuelve intake y dispatch operativo, no solo atención.",
      "problem": "Sin estructura se pierde urgencia, contexto, asignación y seguimiento al cliente.",
      "promise": "Cada mensaje termina en orden de trabajo, visita programada, servicio cerrado o mantenimiento vendido.",
      "monetizes": [
        "visita diagnóstica",
        "servicio puntual",
        "urgencia",
        "garantía",
        "mantenimiento recurrente",
        "contratos"
      ],
      "packaging": [
        "setup field services",
        "intake por incidente",
        "despacho y estatus",
        "garantía + contrato de mantenimiento"
      ],
      "strategic_care": "Muy buena vertical para WAOS porque conecta conversación con acción operativa real; hay que cuidar bien urgencias críticas y promesas de llegada."
    },
    "demo_flow": [
      "El cliente entra con un problema urgente o solicitud de visita.",
      "WAOS clasifica urgencia y pide ubicación y evidencia.",
      "Arma intake y agenda o despacha técnico.",
      "Comunica estatus: en camino, trabajando, terminado.",
      "Confirma cierre y cobro.",
      "Después deja garantía y ofrece mantenimiento o contrato."
    ],
    "native_objects": {
      "core": [
        "cliente",
        "incidente",
        "prioridad",
        "zona",
        "evidencia",
        "orden de trabajo en sitio"
      ],
      "commercial": [
        "visita diagnóstica",
        "cotización",
        "servicio",
        "contrato"
      ],
      "operations": [
        "técnico",
        "orden de trabajo",
        "garantía",
        "mantenimiento",
        "encuesta"
      ]
    },
    "pipeline": {
      "primary": {
        "name": "Solicitud y servicio",
        "states": [
          "solicitud nueva",
          "intake parcial",
          "intake completo",
          "urgencia clasificada",
          "visita ofrecida",
          "visita agendada",
          "técnico asignado",
          "en camino",
          "trabajando",
          "terminado",
          "cobrado",
          "garantía activa",
          "mantenimiento próximo"
        ]
      },
      "secondary": [
        {
          "name": "Contrato de mantenimiento",
          "states": [
            "sin contrato",
            "contrato ofrecido",
            "contrato activo",
            "renovación pendiente",
            "renovado"
          ]
        }
      ]
    },
    "bot_playbook": {
      "must_do": [
        "entender problema",
        "clasificar urgencia",
        "levantar ubicación y contexto",
        "pedir evidencia",
        "programar visita",
        "comunicar estatus",
        "cerrar servicio",
        "ofrecer mantenimiento",
        "nunca quedarse seco ante bromas, preguntas raras o cambios bruscos de tema",
        "usar humor ligero cuando sume, sin sonar payaso ni poco serio",
        "validar el momento y luego reencauzar la conversacion al negocio",
        "cerrar siempre con una pregunta util o siguiente paso"
      ],
      "must_ask": [
        "tipo de falla",
        "urgencia",
        "ubicación",
        "tipo de inmueble",
        "evidencia",
        "disponibilidad",
        "que parte del negocio se esta atorando mas",
        "si quiere que se lo aterrice a su caso"
      ],
      "objections": [
        "precio",
        "tiempo de llegada",
        "desconfianza",
        "solo quiero cotizar",
        "quiero que sea hoy"
      ],
      "escalate_when": [
        "urgencia crítica",
        "negociación compleja",
        "reclamación",
        "instalación grande",
        "contrato empresarial"
      ],
      "forbidden": [
        "prometer tiempos de llegada no confirmados",
        "diagnósticos definitivos sin visita"
      ],
      "success_signals": [
        "me urge",
        "¿pueden venir hoy?",
        "¿cuánto cobran la visita?",
        "mándame técnico",
        "quiero mantenimiento"
      ],
      "style": [
        "humor ligero",
        "manejo de preguntas raras",
        "reencuadre comercial"
      ]
    },
    "automation_sequences": [
      {
        "key": "fs_request",
        "name": "Confirmación de solicitud",
        "trigger": "entra incidente",
        "goal": "completar intake",
        "steps": [
          "pedir datos mínimos",
          "clasificar urgencia",
          "proponer visita"
        ]
      },
      {
        "key": "fs_dispatch",
        "name": "Técnico en camino",
        "trigger": "técnico asignado",
        "goal": "dar visibilidad",
        "steps": [
          "avisar salida",
          "ETA",
          "confirmar llegada"
        ]
      },
      {
        "key": "fs_post_service",
        "name": "Post servicio",
        "trigger": "servicio terminado",
        "goal": "garantía y satisfacción",
        "steps": [
          "encuesta",
          "recordar garantía",
          "ofrecer mantenimiento"
        ]
      },
      {
        "key": "fs_contract",
        "name": "Renovación de contrato",
        "trigger": "contrato por vencer",
        "goal": "retener ingreso recurrente",
        "steps": [
          "recordar vencimiento",
          "mostrar beneficios",
          "cerrar renovación"
        ]
      }
    ],
    "dashboard": {
      "north_star": "Solicitudes resueltas con primera visita y mantenimiento vendido.",
      "sections": [
        {
          "name": "Operación",
          "metrics": [
            "tiempo de respuesta",
            "tiempo a visita",
            "técnico asignado a tiempo",
            "resolución en primera visita"
          ]
        },
        {
          "name": "Revenue",
          "metrics": [
            "solicitud a visita",
            "visita a servicio",
            "mantenimiento vendido",
            "contrato renovado"
          ]
        },
        {
          "name": "Calidad",
          "metrics": [
            "garantías activas",
            "reclamos",
            "satisfacción",
            "repetición de servicio"
          ]
        },
        {
          "name": "Eficiencia",
          "metrics": [
            "carga por técnico",
            "tiempos por zona",
            "abandono en intake",
            "cancelaciones"
          ]
        }
      ]
    },
    "hardening_model": {
      "goal": "Pasar de preset inteligente a sistema especialista",
      "wave": "ola_2",
      "entity_queen": "orden de trabajo en sitio",
      "core_common": true,
      "domain_by_vertical": true,
      "playbooks_by_subvertical": true,
      "kpis_by_vertical": true,
      "pricing_by_vertical": true,
      "journeys_by_vertical": true,
      "reusable_modules": [
        "intake / calificación",
        "agenda / recursos",
        "cotización / propuesta",
        "pago / anticipo / membresía",
        "seguimiento / recurrencia",
        "reporting vertical"
      ],
      "minimum_viable_hardening": [
        "1 entidad reina",
        "1 pipeline propio",
        "1 cotización propia",
        "1 recurrencia propia",
        "1 dashboard propio"
      ],
      "hard_checklist": [
        "tiene entidad principal propia",
        "tiene pipeline específico",
        "tiene cotización o pricing del nicho",
        "tiene agenda o recursos del nicho",
        "tiene postventa o recurrencia del nicho",
        "tiene documentos o compliance del nicho",
        "tiene KPIs del nicho",
        "tiene 3 automatizaciones que mueven dinero",
        "tiene 2 pruebas e2e de negocio",
        "tiene subplaybooks por subvertical",
        "entidad principal propia",
        "pipeline específico",
        "pricing del nicho",
        "agenda y recursos del nicho",
        "postventa o recurrencia del nicho",
        "documentos o compliance del nicho",
        "KPIs del nicho",
        "3 automatizaciones que mueven dinero",
        "2 pruebas e2e de negocio",
        "subplaybooks por subvertical",
        "runtime ejecutable por vertical"
      ]
    },
    "specialist_layers": {
      "persistent_entities": [
        "sitio de servicio",
        "incidencia / trabajo",
        "prioridad",
        "técnico / cuadrilla",
        "ventana de atención",
        "cotización",
        "materiales / evidencia",
        "firma de cierre"
      ],
      "business_pipeline": {
        "primary_entity": "orden de trabajo en sitio",
        "primary_pipeline": {
          "name": "Solicitud y servicio",
          "states": [
            "solicitud nueva",
            "intake parcial",
            "intake completo",
            "urgencia clasificada",
            "visita ofrecida",
            "visita agendada",
            "técnico asignado",
            "en camino",
            "trabajando",
            "terminado",
            "cobrado",
            "garantía activa",
            "mantenimiento próximo"
          ]
        },
        "secondary_pipelines": [
          {
            "name": "Contrato de mantenimiento",
            "states": [
              "sin contrato",
              "contrato ofrecido",
              "contrato activo",
              "renovación pendiente",
              "renovado"
            ]
          }
        ]
      },
      "pricing_and_quotes": [
        "cotización por incidencia",
        "recargo por prioridad",
        "mantenimiento preventivo"
      ],
      "agenda_and_resources": [
        "técnico",
        "cuadrilla",
        "ruta",
        "ventana de atención",
        "inventario básico"
      ],
      "post_sale_and_recurrence": [
        "seguimiento post-cierre",
        "recompra operativa",
        "contrato de mantenimiento preventivo"
      ],
      "documents_compliance": [
        "orden de trabajo",
        "evidencia fotográfica",
        "firma de cierre",
        "checklist de servicio"
      ],
      "kpis_that_matter": [
        "tiempo de respuesta",
        "tiempo a visita",
        "solicitud a visita",
        "primera visita resuelta",
        "mantenimiento vendido",
        "satisfacción",
        "tiempo a asignación",
        "first-time fix",
        "ticket",
        "cancelación",
        "puntualidad"
      ],
      "money_automations": [
        "diagnóstico remoto a cotización",
        "recordatorio de visita",
        "venta de mantenimiento preventivo"
      ]
    },
    "domain_contract": {
      "vertical_entity_types": [
        "sitio de servicio",
        "incidencia / trabajo",
        "prioridad",
        "técnico / cuadrilla",
        "ventana de atención",
        "cotización",
        "materiales / evidencia",
        "firma de cierre"
      ],
      "vertical_pipeline_stages": {
        "primary": [
          "solicitud nueva",
          "intake parcial",
          "intake completo",
          "urgencia clasificada",
          "visita ofrecida",
          "visita agendada",
          "técnico asignado",
          "en camino",
          "trabajando",
          "terminado",
          "cobrado",
          "garantía activa",
          "mantenimiento próximo"
        ],
        "secondary": [
          [
            "sin contrato",
            "contrato ofrecido",
            "contrato activo",
            "renovación pendiente",
            "renovado"
          ]
        ]
      },
      "vertical_quote_types": [
        "diagnóstico remoto",
        "cotización",
        "servicio en sitio",
        "mantenimiento preventivo",
        "contrato liviano"
      ],
      "vertical_resource_types": [
        "técnico",
        "cuadrilla",
        "ruta",
        "ventana de atención",
        "inventario básico"
      ],
      "vertical_followup_policies": [
        "seguimiento post-cierre",
        "recompra operativa",
        "contrato de mantenimiento preventivo"
      ],
      "vertical_kpi_definitions": [
        "tiempo de respuesta",
        "tiempo a visita",
        "solicitud a visita",
        "primera visita resuelta",
        "mantenimiento vendido",
        "satisfacción",
        "tiempo a asignación",
        "first-time fix",
        "ticket",
        "cancelación",
        "puntualidad"
      ],
      "vertical_playbooks": [
        "HVAC",
        "plomería",
        "electricidad",
        "limpieza técnica",
        "mantenimiento industrial liviano"
      ],
      "vertical_document_types": [
        "orden de trabajo",
        "evidencia fotográfica",
        "firma de cierre",
        "checklist de servicio"
      ]
    },
    "subvertical_playbooks": [
      {
        "name": "HVAC",
        "focus": "Playbook operativo y comercial para HVAC"
      },
      {
        "name": "plomería",
        "focus": "Playbook operativo y comercial para plomería"
      },
      {
        "name": "electricidad",
        "focus": "Playbook operativo y comercial para electricidad"
      },
      {
        "name": "limpieza técnica",
        "focus": "Playbook operativo y comercial para limpieza técnica"
      },
      {
        "name": "mantenimiento industrial liviano",
        "focus": "Playbook operativo y comercial para mantenimiento industrial liviano"
      }
    ],
    "business_e2e_tests": [
      {
        "name": "lead recibe diagnóstico remoto, aprueba cotización y se asigna técnico",
        "status": "designed"
      },
      {
        "name": "servicio cerrado dispara oferta de mantenimiento preventivo",
        "status": "designed"
      }
    ],
    "vertical_runtime": {
      "pipeline_machine": {
        "primary_pipeline": "Solicitud y servicio",
        "entity": "orden de trabajo en sitio",
        "states": [
          "solicitud nueva",
          "intake parcial",
          "intake completo",
          "urgencia clasificada",
          "visita ofrecida",
          "visita agendada",
          "técnico asignado",
          "en camino",
          "trabajando",
          "terminado",
          "cobrado",
          "garantía activa",
          "mantenimiento próximo"
        ],
        "transitions": [
          {
            "from": "solicitud nueva",
            "to": "intake parcial",
            "trigger": "qualification_complete",
            "business_effect": "advance opportunity"
          },
          {
            "from": "intake parcial",
            "to": "intake completo",
            "trigger": "crew_assigned",
            "business_effect": "open commercial step"
          },
          {
            "from": "garantía activa",
            "to": "mantenimiento próximo",
            "trigger": "successful_outcome",
            "business_effect": "realize revenue or continuity"
          },
          {
            "from": "garantía activa",
            "to": "at_risk",
            "trigger": "remote_diagnosis_done",
            "business_effect": "activate retention sequence"
          }
        ],
        "at_risk_state": "at_risk",
        "closed_states": [
          "mantenimiento próximo"
        ]
      },
      "pricing_engine": {
        "quote_types": [
          "diagnostico remoto",
          "cotizacion en sitio",
          "mantenimiento preventivo",
          "contrato recurrente"
        ],
        "pricing_basis": "job_type + urgency + materials + travel zone",
        "rules": [
          {
            "rule": "base price by servicio type",
            "effect": "set base_price"
          },
          {
            "rule": "premium or urgent add-ons increase quote",
            "effect": "add surcharge"
          },
          {
            "rule": "bundle, membership or financing can lower immediate friction",
            "effect": "recommend package or installments"
          }
        ],
        "deposit_policy": "request advance when capacity, specialist time or inventory must be secured"
      },
      "resource_capacity": {
        "resource_types": [
          "tecnico",
          "cuadrilla",
          "unidad movil",
          "ventana de atencion",
          "materiales"
        ],
        "capacity_basis": "crew calendars, territory routing and job duration",
        "constraints": [
          "avoid double booking of critical resources",
          "respect service duration and cleanup/buffer time",
          "prioritize higher urgency and higher close probability cases"
        ],
        "priority_queue": "cuadrilla, prioridad y ventana"
      },
      "recurrence_engine": {
        "policies": [
          {
            "type": "preventive_plan",
            "interval_days": 90,
            "anchor": "orden de trabajo en sitio"
          },
          {
            "type": "post_service_followup",
            "interval_days": 2,
            "anchor": "orden de trabajo en sitio"
          },
          {
            "type": "reactivation",
            "interval_days": 30,
            "anchor": "orden de trabajo en sitio"
          }
        ],
        "reactivation_window_days": 90,
        "goal": "protect retention, repeat revenue and continuity"
      },
      "kpi_engine": {
        "north_star": "Solicitudes resueltas con primera visita y mantenimiento vendido.",
        "definitions": [
          {
            "name": "time_to_assignment",
            "formula": "assigned_jobs / created_jobs with SLA"
          },
          {
            "name": "first_time_fix",
            "formula": "fixed_first_visit / closed_jobs"
          },
          {
            "name": "punctuality",
            "formula": "on_time_arrivals / assigned_jobs"
          }
        ],
        "leading_indicators": [
          "remote_diagnosis_done",
          "quote_sent",
          "no_response_7d"
        ]
      },
      "automation_engine": {
        "money_automation_policies": [
          {
            "trigger": "remote_diagnosis_done",
            "actions": [
              "send_followup",
              "escalate_owner",
              "offer_relevant_next_step"
            ],
            "goal": "save conversion or retention"
          },
          {
            "trigger": "quote_sent",
            "actions": [
              "send_quote_or_payment_link",
              "remind_deadline",
              "notify_human"
            ],
            "goal": "move revenue forward"
          },
          {
            "trigger": "service_closed",
            "actions": [
              "schedule_recurrence",
              "cross_sell_next_best_offer",
              "create_task"
            ],
            "goal": "increase LTV"
          }
        ],
        "quiet_hours": "21:00-08:00"
      },
      "document_flow": {
        "required_documents": [
          "orden de trabajo",
          "evidencia fotografica",
          "firma de cierre",
          "bitacora de materiales"
        ],
        "lifecycle_rules": [
          {
            "document": "orden de trabajo",
            "required_before": "first committed step",
            "signature_required": true
          },
          {
            "document": "bitacora de materiales",
            "required_before": "handoff or continuity step",
            "signature_required": false
          }
        ]
      },
      "matching_engine": {
        "entity": "orden de trabajo en sitio",
        "rules": [
          "incident_type -> crew_skill",
          "priority -> response_sla",
          "territory_match",
          "materials_available"
        ],
        "next_best_match_outputs": [
          "best_owner",
          "best_resource_slot",
          "best_offer"
        ]
      }
    },
    "transactional_motor_v12": {
      "version": "v12_full_transactional",
      "aggregate_root": "field_service_job_account",
      "main_business_entity": "orden de trabajo en sitio",
      "transaction_unit": "dispatch_cycle",
      "system_of_record": {
        "write_model": [
          "commands",
          "events",
          "ledger",
          "aggregate_snapshots"
        ],
        "read_models": [
          "commercial_board",
          "operations_board",
          "finance_board",
          "continuity_board",
          "resource_load_board",
          "document_readiness_board",
          "revenue_levers_board"
        ],
        "idempotency_scope": [
          "organization_id",
          "vertical_id",
          "external_reference",
          "command_key"
        ],
        "audit_mode": "append_only_with_snapshots"
      },
      "transaction_primitives": {
        "commands": [
          "capture_intent",
          "qualify_record",
          "create_quote",
          "request_deposit",
          "reserve_capacity",
          "confirm_booking",
          "start_case",
          "approve_quote",
          "collect_payment",
          "start_fulfillment",
          "close_fulfillment",
          "schedule_recurrence",
          "issue_refund",
          "reactivate_customer",
          "create_dispatch_job",
          "assign_crew",
          "capture_site_evidence",
          "close_with_signature"
        ],
        "events": [
          "intent_captured",
          "record_qualified",
          "quote_created",
          "deposit_requested",
          "capacity_reserved",
          "booking_confirmed",
          "case_started",
          "quote_approved",
          "payment_collected",
          "fulfillment_started",
          "fulfillment_closed",
          "recurrence_scheduled",
          "refund_issued",
          "customer_reactivated",
          "dispatch_job_created",
          "crew_assigned",
          "site_evidence_captured",
          "job_closed_signed"
        ],
        "ledger_event_types": [
          "charge_opened",
          "deposit_collected",
          "installment_due",
          "payment_applied",
          "credit_issued",
          "refund_issued",
          "write_off_registered"
        ],
        "invariants": [
          "no asignar técnico sin ventana",
          "no iniciar servicio sin aprobación",
          "no cerrar sin evidencia y firma",
          "todo pago debe referenciar quote, order o case activo",
          "todo cambio crítico debe emitir evento y renglón de auditoría",
          "ningún recurso se confirma dos veces en la misma ventana"
        ],
        "idempotency_keys": [
          "command_key",
          "payment_reference",
          "booking_reference",
          "external_message_id"
        ]
      },
      "aggregates": {
        "primary_record": {
          "name": "orden de trabajo en sitio",
          "status_axis": [
            "commercial",
            "operations",
            "finance",
            "continuity"
          ]
        },
        "quote": {
          "name": "job_quote",
          "states": [
            "draft",
            "sent",
            "accepted",
            "expired",
            "lost"
          ]
        },
        "booking": {
          "name": "service_window_booking",
          "states": [
            "proposed",
            "reserved",
            "confirmed",
            "attended_or_executed",
            "missed_or_canceled"
          ]
        },
        "execution": {
          "name": "dispatch_and_close",
          "states": [
            "pending",
            "ready",
            "in_progress",
            "blocked",
            "completed",
            "closed"
          ]
        },
        "payment_account": {
          "name": "payment_account",
          "states": [
            "open",
            "partially_paid",
            "paid",
            "overdue",
            "refunded"
          ]
        },
        "continuity": {
          "name": "maintenance_contract",
          "states": [
            "not_started",
            "active",
            "at_risk",
            "recovered",
            "closed"
          ]
        }
      },
      "orchestration": {
        "command_handlers": [
          "handle_capture_intent",
          "handle_qualify_record",
          "handle_create_quote",
          "handle_request_deposit",
          "handle_reserve_capacity",
          "handle_confirm_booking",
          "handle_start_case",
          "handle_approve_quote",
          "handle_create_dispatch_job",
          "handle_assign_crew",
          "handle_capture_site_evidence",
          "handle_close_with_signature"
        ],
        "sagas": [
          "diagnosis_to_dispatch",
          "dispatch_to_close",
          "maintenance_contract_renewal"
        ],
        "money_guards": [
          "quote_before_payment",
          "capacity_before_confirmation",
          "documents_before_execution",
          "balance_before_close"
        ],
        "read_model_refresh": [
          "on_every_event",
          "nightly_reconciliation",
          "pre_dashboard_cache"
        ]
      },
      "finance": {
        "money_objects": [
          "diagnostic_charge",
          "job_deposit",
          "completion_collection",
          "maintenance_invoice"
        ],
        "collection_modes": [
          "diagnóstico",
          "anticipo",
          "contra cierre"
        ],
        "refund_modes": [
          "service_recovery_credit",
          "partial_refund"
        ],
        "reconciliation_views": [
          "expected_vs_collected",
          "aging_balance",
          "refund_exposure",
          "cash_by_stage"
        ]
      },
      "operations": {
        "fulfillment_unit": "dispatch_cycle",
        "resource_locking": [
          "technician_or_crew",
          "route_window",
          "materials_reservation"
        ],
        "dispatch_or_schedule_board": [
          "queued",
          "ready",
          "assigned",
          "in_progress",
          "blocked",
          "done"
        ],
        "handoff_rules": [
          "human_handoff_on_exception",
          "supervisor_handoff_on_money_risk",
          "operator_handoff_on_compliance_gap"
        ]
      },
      "audit_compliance": {
        "timeline_entities": [
          "orden de trabajo en sitio",
          "job_quote",
          "service_window_booking",
          "dispatch_and_close",
          "payment_account"
        ],
        "consent_gates": [
          "site_evidence",
          "service_authorization",
          "closure_signature"
        ],
        "required_evidence": [
          "timeline_event",
          "actor",
          "timestamp",
          "before_after_snapshot"
        ],
        "retention_rules": [
          "audit_log_append_only",
          "documents_linked_to_primary_record",
          "payment_trace_non_destructive"
        ]
      },
      "transaction_views": {
        "commercial": [
          "remote_diagnosis",
          "quote_acceptance",
          "contracts"
        ],
        "operations": [
          "dispatch",
          "sla",
          "first_time_fix"
        ],
        "finance": [
          "job_margin",
          "collection_rate",
          "callbacks_cost"
        ],
        "continuity": [
          "preventive_maintenance",
          "repeat_jobs",
          "contract_renewal"
        ]
      },
      "command_catalog": [
        {
          "command": "capture_intent",
          "writes": "orden de trabajo en sitio",
          "emits": "intent_captured",
          "guard": "no asignar técnico sin ventana"
        },
        {
          "command": "qualify_record",
          "writes": "orden de trabajo en sitio",
          "emits": "record_qualified",
          "guard": "no iniciar servicio sin aprobación"
        },
        {
          "command": "create_quote",
          "writes": "orden de trabajo en sitio",
          "emits": "quote_created",
          "guard": "no cerrar sin evidencia y firma"
        },
        {
          "command": "request_deposit",
          "writes": "orden de trabajo en sitio",
          "emits": "deposit_requested",
          "guard": "no asignar técnico sin ventana"
        },
        {
          "command": "reserve_capacity",
          "writes": "orden de trabajo en sitio",
          "emits": "capacity_reserved",
          "guard": "no iniciar servicio sin aprobación"
        },
        {
          "command": "confirm_booking",
          "writes": "orden de trabajo en sitio",
          "emits": "booking_confirmed",
          "guard": "no cerrar sin evidencia y firma"
        },
        {
          "command": "start_case",
          "writes": "orden de trabajo en sitio",
          "emits": "case_started",
          "guard": "no asignar técnico sin ventana"
        },
        {
          "command": "approve_quote",
          "writes": "orden de trabajo en sitio",
          "emits": "quote_approved",
          "guard": "no iniciar servicio sin aprobación"
        },
        {
          "command": "create_dispatch_job",
          "writes": "orden de trabajo en sitio",
          "emits": "payment_collected",
          "guard": "no cerrar sin evidencia y firma"
        },
        {
          "command": "assign_crew",
          "writes": "orden de trabajo en sitio",
          "emits": "fulfillment_started",
          "guard": "no asignar técnico sin ventana"
        },
        {
          "command": "capture_site_evidence",
          "writes": "orden de trabajo en sitio",
          "emits": "fulfillment_closed",
          "guard": "no iniciar servicio sin aprobación"
        },
        {
          "command": "close_with_signature",
          "writes": "orden de trabajo en sitio",
          "emits": "recurrence_scheduled",
          "guard": "no cerrar sin evidencia y firma"
        }
      ],
      "event_catalog": [
        {
          "event": "intent_captured",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "diagnosis_to_dispatch"
        },
        {
          "event": "record_qualified",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "dispatch_to_close"
        },
        {
          "event": "quote_created",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "maintenance_contract_renewal"
        },
        {
          "event": "deposit_requested",
          "updates": [
            "timeline",
            "boards",
            "ledger"
          ],
          "next_action": "diagnosis_to_dispatch"
        },
        {
          "event": "capacity_reserved",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "dispatch_to_close"
        },
        {
          "event": "booking_confirmed",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "maintenance_contract_renewal"
        },
        {
          "event": "case_started",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "diagnosis_to_dispatch"
        },
        {
          "event": "quote_approved",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "dispatch_to_close"
        },
        {
          "event": "dispatch_job_created",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "maintenance_contract_renewal"
        },
        {
          "event": "crew_assigned",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "diagnosis_to_dispatch"
        },
        {
          "event": "site_evidence_captured",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "dispatch_to_close"
        },
        {
          "event": "job_closed_signed",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "maintenance_contract_renewal"
        }
      ]
    },
    "subvertical_profiles": [],
    "recommended_subverticals": []
  },
  {
    "id": "professional-intake",
    "name": "WAOS Professional Intake",
    "short_name": "Servicios profesionales de alto seguimiento",
    "description": "Sistema operativo conversacional para servicios profesionales de alto seguimiento.",
    "problem": "Servicios profesionales pierden tiempo caro en leads mal calificados, intake incompleto, asignación débil de especialista, documentos desordenados y consultas no cobradas.",
    "subverticals": [
      "legal",
      "migración",
      "contabilidad",
      "fiscal",
      "seguros no complejos",
      "consultoría especializada",
      "notarial",
      "gestoría",
      "compliance ligero",
      "brokers financieros simples"
    ],
    "objects": [
      "tipo de caso",
      "especialidad",
      "elegibilidad",
      "consulta",
      "fee",
      "documento",
      "milestone",
      "vencimiento",
      "asesor",
      "renovación",
      "caso / asunto",
      "expediente",
      "tipo de consulta",
      "calificación inicial",
      "documentos requeridos",
      "conflicto / elegibilidad",
      "profesional asignado",
      "honorarios / propuesta"
    ],
    "flows": [
      "lead -> intake",
      "intake -> elegibilidad",
      "elegibilidad -> consulta",
      "consulta -> expediente",
      "expediente -> renovación"
    ],
    "kpis": [
      "lead calificado",
      "consulta cobrada",
      "documento completo",
      "conversión a cliente",
      "tiempo de asignación",
      "renovación",
      "consulta agendada",
      "consulta asistida",
      "contratación",
      "tiempo a propuesta"
    ],
    "recommended_integrations": [
      "whatsapp",
      "calendar",
      "payments",
      "crm",
      "documents"
    ],
    "default_services": [
      "consulta inicial",
      "revision de caso",
      "expediente",
      "seguimiento",
      "renovacion o continuidad"
    ],
    "default_faqs": [
      {
        "q": "¿Como clasifican mi caso?",
        "a": "El bot hace intake inicial y puede dirigirte con la especialidad correcta."
      },
      {
        "q": "¿Pueden pedir documentos?",
        "a": "Si, podemos solicitar documentos iniciales para preparar la consulta o expediente."
      },
      {
        "q": "¿La consulta se paga?",
        "a": "Si, si tu operacion lo requiere, podemos cobrar consulta o anticipo desde el chat."
      },
      {
        "q": "¿Dan seguimiento a vencimientos?",
        "a": "Si, el bot puede recordar milestones, renovaciones o vencimientos importantes."
      }
    ],
    "behavior": {
      "tone": "serio y profesional",
      "response_length": "media",
      "use_emojis": false,
      "sales_intensity": "media",
      "offer_promotions_when": "never",
      "escalate_when": [
        "urgencia legal",
        "riesgo regulatorio",
        "caso sensible"
      ],
      "insistence_policy": "respectful",
      "can_share_price_directly": true,
      "can_negotiate": false,
      "can_mention_stock": false,
      "auto_send_images": false,
      "bot_mode": "intake_profesional",
      "active_channels": [
        "whatsapp",
        "webchat"
      ],
      "forbidden_topics": [
        "asesoria definitiva por chat",
        "promesas de resultado"
      ],
      "required_phrases": [
        "te ayudo a clasificar tu caso",
        "si quieres, agendamos consulta con el especialista correcto",
        "te sigo",
        "si la pregunta viene rara, igual te la aterrizo",
        "te lo aterrizo a tu caso"
      ],
      "fallback_message": "Te ayudo a ordenar tu caso, pedir lo necesario y llevarte con el especialista correcto. Si la pregunta viene rara, en broma o medio fuera de tema, igual te sigo y la aterrizamos al negocio.",
      "humor_policy": "light_contextual",
      "strange_question_policy": "respond_validate_reframe_sell_move"
    },
    "followup_rules": [
      {
        "type": "no_response",
        "delay_minutes": 240,
        "max_attempts": 2,
        "message_template": "¿Quieres que retomemos tu caso y revisemos la consulta o documentacion inicial?"
      },
      {
        "type": "post_quote",
        "delay_minutes": 1440,
        "max_attempts": 2,
        "message_template": "Sigo atento por si quieres avanzar con consulta, fee o envio de documentos."
      },
      {
        "type": "reactivation",
        "delay_minutes": 43200,
        "max_attempts": 1,
        "message_template": "Te recordamos que tu expediente o renovacion sigue abierto. ¿Quieres retomarlo hoy?"
      }
    ],
    "templates": [
      {
        "template_key": "case_intake",
        "title": "Intake de caso",
        "content": "Para orientarte mejor, dime tipo de caso, urgencia, pais o jurisdiccion y objetivo principal.",
        "variables": []
      },
      {
        "template_key": "consult_booking",
        "title": "Agendar consulta",
        "content": "Puedo coordinar tu consulta con {{specialty}} para {{date}}. ¿Te funciona?",
        "variables": [
          "specialty",
          "date"
        ]
      },
      {
        "template_key": "document_request",
        "title": "Solicitud de documentos",
        "content": "Antes de la consulta, te comparto la documentacion inicial sugerida para avanzar con tu caso.",
        "variables": []
      },
      {
        "template_key": "fee_collection",
        "title": "Cobro de consulta",
        "content": "Si quieres asegurar tu espacio o abrir expediente, te envio el link de pago ahora mismo.",
        "variables": []
      },
      {
        "template_key": "renewal_due",
        "title": "Recordatorio de vencimiento",
        "content": "Tu siguiente vencimiento o renovacion se acerca. ¿Quieres que te ayudemos a continuarlo?",
        "variables": []
      }
    ],
    "config_overrides": {
      "objective_secondary": [
        "calificar",
        "agendar",
        "renovar"
      ],
      "policies": [
        "No dar asesoria definitiva por chat",
        "Escalar casos sensibles o de alto riesgo"
      ],
      "can_say": [
        "consulta",
        "especialidad",
        "fee",
        "documentos",
        "vencimientos"
      ],
      "cannot_say": [
        "resultado garantizado",
        "asesoria definitiva",
        "promesas legales"
      ],
      "whatsapp_flows": [
        "intake_caso",
        "agenda_consulta",
        "documentos_iniciales",
        "recordatorio_vencimiento"
      ],
      "appointment_duration_minutes": 45,
      "handoff_keywords": [
        "urgencia",
        "demanda",
        "auditoria",
        "vencimiento inmediato"
      ],
      "high_score_threshold": 92
    },
    "portfolio_tier": "tier_2",
    "master_thesis": "Sistema operativo conversacional para servicios profesionales de alto seguimiento que protege tiempo experto mediante intake, filtro, consulta, documentos y renovación.",
    "buyer": {
      "primary": "Socio, director o gerente de intake/comercial",
      "secondary": [
        "paralegals o coordinadores",
        "recepción",
        "asesores senior"
      ]
    },
    "one_pager": {
      "headline": "WAOS Professional Intake",
      "thesis": "WhatsApp se vuelve intake estructurado y filtro que protege horas de especialistas caros.",
      "problem": "Mucho lead no elegible y poca estructura documental o de cobro inicial.",
      "promise": "Cada lead termina como no elegible, consulta cobrada, expediente activo o renovación.",
      "monetizes": [
        "consulta",
        "anticipo",
        "expediente",
        "renovación anual",
        "continuidad del servicio"
      ],
      "packaging": [
        "setup intake profesional",
        "filtro por especialidad",
        "fee + documentos + hitos",
        "renovación anual"
      ],
      "strategic_care": "La auditoría lo valida especialmente para legal intake; el bot debe hacer intake y filtro, no asesoría profesional compleja."
    },
    "demo_flow": [
      "El lead entra con un caso, trámite o necesidad.",
      "WAOS hace intake estructurado y filtra elegibilidad.",
      "Asigna especialidad y agenda consulta.",
      "Cobra fee o anticipo.",
      "Persigue documentos y actualiza hitos.",
      "Recuerda vencimientos y renueva o amplía servicio."
    ],
    "native_objects": {
      "core": [
        "lead",
        "tipo de caso",
        "especialidad",
        "elegibilidad",
        "caso / expediente"
      ],
      "commercial": [
        "consulta",
        "fee",
        "anticipo",
        "documento",
        "expediente"
      ],
      "operations": [
        "hito",
        "vencimiento",
        "renovación",
        "asesor",
        "caso pausado"
      ]
    },
    "pipeline": {
      "primary": {
        "name": "Intake y expediente",
        "states": [
          "lead nuevo",
          "intake en curso",
          "elegibilidad evaluada",
          "calificado",
          "consulta agendada",
          "consulta pagada",
          "documentos pendientes",
          "documentos completos",
          "expediente activo",
          "hito alcanzado",
          "cierre/entrega",
          "renovación pendiente",
          "renovado",
          "no elegible"
        ]
      },
      "secondary": [
        {
          "name": "Reactivación de casos",
          "states": [
            "expediente inactivo",
            "seguimiento",
            "reactivado",
            "cerrado"
          ]
        }
      ]
    },
    "bot_playbook": {
      "must_do": [
        "hacer intake ordenado",
        "filtrar elegibilidad",
        "asignar área correcta",
        "agendar consulta",
        "cobrar fee",
        "perseguir documentos",
        "recordar hitos",
        "renovar",
        "nunca quedarse seco ante bromas, preguntas raras o cambios bruscos de tema",
        "usar humor ligero cuando sume, sin sonar payaso ni poco serio",
        "validar el momento y luego reencauzar la conversacion al negocio",
        "cerrar siempre con una pregunta util o siguiente paso"
      ],
      "must_ask": [
        "tipo de asunto",
        "urgencia",
        "contexto general",
        "ubicación o jurisdicción",
        "si ya tiene documentos",
        "si ya trabajó antes con la firma/despacho",
        "que parte del negocio se esta atorando mas",
        "si quiere que se lo aterrice a su caso"
      ],
      "objections": [
        "precio de consulta",
        "solo quiero orientación",
        "no sé si califico",
        "necesito pensarlo",
        "quiero hablar directo con el experto"
      ],
      "escalate_when": [
        "alta complejidad",
        "caso sensible",
        "riesgo reputacional",
        "negociación premium",
        "reclamación"
      ],
      "forbidden": [
        "dar asesoría compleja definitiva por chat",
        "prometer resultado legal/fiscal"
      ],
      "success_signals": [
        "quiero consulta",
        "sí califico",
        "¿qué documentos llevo?",
        "mándame el fee",
        "quiero abrir expediente"
      ],
      "style": [
        "humor ligero",
        "manejo de preguntas raras",
        "reencuadre comercial"
      ]
    },
    "automation_sequences": [
      {
        "key": "pi_followup",
        "name": "Seguimiento post intake",
        "trigger": "lead con intake parcial o completo",
        "goal": "cerrar consulta",
        "steps": [
          "resolver duda",
          "confirmar elegibilidad",
          "proponer agenda"
        ]
      },
      {
        "key": "pi_fee",
        "name": "Fee pendiente",
        "trigger": "consulta agendada sin pago",
        "goal": "cobrar consulta",
        "steps": [
          "recordar fee",
          "enviar link",
          "confirmar pago"
        ]
      },
      {
        "key": "pi_docs",
        "name": "Documentos faltantes",
        "trigger": "expediente abierto",
        "goal": "completar expediente",
        "steps": [
          "listar faltantes",
          "recordar fecha",
          "confirmar recepción"
        ]
      },
      {
        "key": "pi_renewal",
        "name": "Renovación o vencimiento",
        "trigger": "vencimiento próximo",
        "goal": "retener servicio",
        "steps": [
          "recordar hito",
          "proponer renovación",
          "cerrar siguiente paso"
        ]
      }
    ],
    "dashboard": {
      "north_star": "Consulta pagada que abre expediente elegible.",
      "sections": [
        {
          "name": "Funnel",
          "metrics": [
            "leads nuevos",
            "elegibilidad",
            "consulta agendada",
            "consulta pagada",
            "caso abierto"
          ]
        },
        {
          "name": "Operación",
          "metrics": [
            "documentos pendientes",
            "tiempo a asignación",
            "hitos cumplidos",
            "expedientes inactivos"
          ]
        },
        {
          "name": "Revenue",
          "metrics": [
            "fee cobrado",
            "anticipo",
            "renovación",
            "LTV por cliente"
          ]
        },
        {
          "name": "Calidad",
          "metrics": [
            "tasa de no elegibles",
            "tiempo de respuesta",
            "abandono en intake",
            "conversión por especialidad"
          ]
        }
      ]
    },
    "hardening_model": {
      "goal": "Pasar de preset inteligente a sistema especialista",
      "wave": "ola_3",
      "entity_queen": "caso / expediente",
      "core_common": true,
      "domain_by_vertical": true,
      "playbooks_by_subvertical": true,
      "kpis_by_vertical": true,
      "pricing_by_vertical": true,
      "journeys_by_vertical": true,
      "reusable_modules": [
        "intake / calificación",
        "agenda / recursos",
        "cotización / propuesta",
        "pago / anticipo / membresía",
        "seguimiento / recurrencia",
        "reporting vertical"
      ],
      "minimum_viable_hardening": [
        "1 entidad reina",
        "1 pipeline propio",
        "1 cotización propia",
        "1 recurrencia propia",
        "1 dashboard propio"
      ],
      "hard_checklist": [
        "tiene entidad principal propia",
        "tiene pipeline específico",
        "tiene cotización o pricing del nicho",
        "tiene agenda o recursos del nicho",
        "tiene postventa o recurrencia del nicho",
        "tiene documentos o compliance del nicho",
        "tiene KPIs del nicho",
        "tiene 3 automatizaciones que mueven dinero",
        "tiene 2 pruebas e2e de negocio",
        "tiene subplaybooks por subvertical",
        "entidad principal propia",
        "pipeline específico",
        "pricing del nicho",
        "agenda y recursos del nicho",
        "postventa o recurrencia del nicho",
        "documentos o compliance del nicho",
        "KPIs del nicho",
        "3 automatizaciones que mueven dinero",
        "2 pruebas e2e de negocio",
        "subplaybooks por subvertical",
        "runtime ejecutable por vertical"
      ]
    },
    "specialist_layers": {
      "persistent_entities": [
        "caso / asunto",
        "expediente",
        "tipo de consulta",
        "calificación inicial",
        "documentos requeridos",
        "conflicto / elegibilidad",
        "profesional asignado",
        "honorarios / propuesta"
      ],
      "business_pipeline": {
        "primary_entity": "caso / expediente",
        "primary_pipeline": {
          "name": "Intake y expediente",
          "states": [
            "lead nuevo",
            "intake en curso",
            "elegibilidad evaluada",
            "calificado",
            "consulta agendada",
            "consulta pagada",
            "documentos pendientes",
            "documentos completos",
            "expediente activo",
            "hito alcanzado",
            "cierre/entrega",
            "renovación pendiente",
            "renovado",
            "no elegible"
          ]
        },
        "secondary_pipelines": [
          {
            "name": "Reactivación de casos",
            "states": [
              "expediente inactivo",
              "seguimiento",
              "reactivado",
              "cerrado"
            ]
          }
        ]
      },
      "pricing_and_quotes": [
        "propuesta por tipo de caso",
        "honorarios",
        "consulta pagada"
      ],
      "agenda_and_resources": [
        "profesional",
        "agenda de consulta",
        "especialidad",
        "capacidad semanal",
        "ventana de revisión"
      ],
      "post_sale_and_recurrence": [
        "seguimiento de propuesta",
        "handoff trazado a humano",
        "continuidad de caso"
      ],
      "documents_compliance": [
        "checklist documental",
        "conflicto / elegibilidad",
        "propuesta",
        "expediente inicial"
      ],
      "kpis_that_matter": [
        "lead calificado",
        "consulta cobrada",
        "documento completo",
        "conversión a cliente",
        "tiempo de asignación",
        "renovación",
        "consulta agendada",
        "consulta asistida",
        "contratación",
        "tiempo a propuesta"
      ],
      "money_automations": [
        "intake a consulta",
        "consulta a propuesta",
        "reactivación de propuesta no firmada"
      ]
    },
    "domain_contract": {
      "vertical_entity_types": [
        "caso / asunto",
        "expediente",
        "tipo de consulta",
        "calificación inicial",
        "documentos requeridos",
        "conflicto / elegibilidad",
        "profesional asignado",
        "honorarios / propuesta"
      ],
      "vertical_pipeline_stages": {
        "primary": [
          "lead nuevo",
          "intake en curso",
          "elegibilidad evaluada",
          "calificado",
          "consulta agendada",
          "consulta pagada",
          "documentos pendientes",
          "documentos completos",
          "expediente activo",
          "hito alcanzado",
          "cierre/entrega",
          "renovación pendiente",
          "renovado",
          "no elegible"
        ],
        "secondary": [
          [
            "expediente inactivo",
            "seguimiento",
            "reactivado",
            "cerrado"
          ]
        ]
      },
      "vertical_quote_types": [
        "consulta inicial",
        "propuesta",
        "honorarios",
        "fee mensual",
        "paquete de servicios"
      ],
      "vertical_resource_types": [
        "profesional",
        "agenda de consulta",
        "especialidad",
        "capacidad semanal",
        "ventana de revisión"
      ],
      "vertical_followup_policies": [
        "seguimiento de propuesta",
        "handoff trazado a humano",
        "continuidad de caso"
      ],
      "vertical_kpi_definitions": [
        "lead calificado",
        "consulta cobrada",
        "documento completo",
        "conversión a cliente",
        "tiempo de asignación",
        "renovación",
        "consulta agendada",
        "consulta asistida",
        "contratación",
        "tiempo a propuesta"
      ],
      "vertical_playbooks": [
        "legal",
        "fiscal",
        "contable",
        "consultoría",
        "psicología intake",
        "nutrición intake"
      ],
      "vertical_document_types": [
        "checklist documental",
        "conflicto / elegibilidad",
        "propuesta",
        "expediente inicial"
      ]
    },
    "subvertical_playbooks": [
      {
        "name": "legal",
        "focus": "Playbook operativo y comercial para legal"
      },
      {
        "name": "fiscal",
        "focus": "Playbook operativo y comercial para fiscal"
      },
      {
        "name": "contable",
        "focus": "Playbook operativo y comercial para contable"
      },
      {
        "name": "consultoría",
        "focus": "Playbook operativo y comercial para consultoría"
      },
      {
        "name": "psicología intake",
        "focus": "Playbook operativo y comercial para psicología intake"
      },
      {
        "name": "nutrición intake",
        "focus": "Playbook operativo y comercial para nutrición intake"
      }
    ],
    "business_e2e_tests": [
      {
        "name": "lead completa intake, agenda consulta y firma propuesta",
        "status": "designed"
      },
      {
        "name": "caso incompleto sube documentos y avanza a contratación",
        "status": "designed"
      }
    ],
    "vertical_runtime": {
      "pipeline_machine": {
        "primary_pipeline": "Intake y expediente",
        "entity": "expediente",
        "states": [
          "lead nuevo",
          "intake en curso",
          "elegibilidad evaluada",
          "calificado",
          "consulta agendada",
          "consulta pagada",
          "documentos pendientes",
          "documentos completos",
          "expediente activo",
          "hito alcanzado",
          "cierre/entrega",
          "renovación pendiente",
          "renovado",
          "no elegible"
        ],
        "transitions": [
          {
            "from": "lead nuevo",
            "to": "intake en curso",
            "trigger": "qualification_complete",
            "business_effect": "advance opportunity"
          },
          {
            "from": "intake en curso",
            "to": "elegibilidad evaluada",
            "trigger": "consultation_done",
            "business_effect": "open commercial step"
          },
          {
            "from": "renovado",
            "to": "no elegible",
            "trigger": "successful_outcome",
            "business_effect": "realize revenue or continuity"
          },
          {
            "from": "renovado",
            "to": "at_risk",
            "trigger": "intake_completed",
            "business_effect": "activate retention sequence"
          }
        ],
        "at_risk_state": "at_risk",
        "closed_states": [
          "no elegible"
        ]
      },
      "pricing_engine": {
        "quote_types": [
          "consulta inicial",
          "propuesta de honorarios",
          "retainer",
          "plan mensual"
        ],
        "pricing_basis": "case_type + complexity + seniority + retainer scope",
        "rules": [
          {
            "rule": "base price by caso type",
            "effect": "set base_price"
          },
          {
            "rule": "premium or urgent add-ons increase quote",
            "effect": "add surcharge"
          },
          {
            "rule": "bundle, membership or financing can lower immediate friction",
            "effect": "recommend package or installments"
          }
        ],
        "deposit_policy": "request advance when capacity, specialist time or inventory must be secured"
      },
      "resource_capacity": {
        "resource_types": [
          "profesional",
          "slot de consulta",
          "revisor documental",
          "backoffice"
        ],
        "capacity_basis": "professional calendar, consultation length and case load",
        "constraints": [
          "avoid double booking of critical resources",
          "respect service duration and cleanup/buffer time",
          "prioritize higher urgency and higher close probability cases"
        ],
        "priority_queue": "profesional, elegibilidad y propuesta"
      },
      "recurrence_engine": {
        "policies": [
          {
            "type": "proposal_followup",
            "interval_days": 3,
            "anchor": "expediente"
          },
          {
            "type": "case_update",
            "interval_days": 14,
            "anchor": "expediente"
          },
          {
            "type": "retainer_renewal",
            "interval_days": 30,
            "anchor": "expediente"
          }
        ],
        "reactivation_window_days": 30,
        "goal": "protect retention, repeat revenue and continuity"
      },
      "kpi_engine": {
        "north_star": "Consulta pagada que abre expediente elegible.",
        "definitions": [
          {
            "name": "consultation_show_rate",
            "formula": "consultations_attended / consultations_booked"
          },
          {
            "name": "hire_rate",
            "formula": "retained_clients / proposals_sent"
          },
          {
            "name": "time_to_proposal",
            "formula": "proposals_sent within SLA / qualified_cases"
          }
        ],
        "leading_indicators": [
          "intake_completed",
          "docs_requested",
          "no_response_7d"
        ]
      },
      "automation_engine": {
        "money_automation_policies": [
          {
            "trigger": "intake_completed",
            "actions": [
              "send_followup",
              "escalate_owner",
              "offer_relevant_next_step"
            ],
            "goal": "save conversion or retention"
          },
          {
            "trigger": "docs_requested",
            "actions": [
              "send_quote_or_payment_link",
              "remind_deadline",
              "notify_human"
            ],
            "goal": "move revenue forward"
          },
          {
            "trigger": "proposal_pending",
            "actions": [
              "schedule_recurrence",
              "cross_sell_next_best_offer",
              "create_task"
            ],
            "goal": "increase LTV"
          }
        ],
        "quiet_hours": "21:00-08:00"
      },
      "document_flow": {
        "required_documents": [
          "intake form",
          "documentos del caso",
          "conflict check",
          "propuesta"
        ],
        "lifecycle_rules": [
          {
            "document": "intake form",
            "required_before": "first committed step",
            "signature_required": true
          },
          {
            "document": "propuesta",
            "required_before": "handoff or continuity step",
            "signature_required": false
          }
        ]
      },
      "matching_engine": {
        "entity": "expediente",
        "rules": [
          "case_type -> professional_specialty",
          "conflict_check == clear",
          "budget_fit",
          "urgency_match"
        ],
        "next_best_match_outputs": [
          "best_owner",
          "best_resource_slot",
          "best_offer"
        ]
      }
    },
    "transactional_motor_v12": {
      "version": "v12_full_transactional",
      "aggregate_root": "professional_case_account",
      "main_business_entity": "caso / expediente",
      "transaction_unit": "intake_consultation_cycle",
      "system_of_record": {
        "write_model": [
          "commands",
          "events",
          "ledger",
          "aggregate_snapshots"
        ],
        "read_models": [
          "commercial_board",
          "operations_board",
          "finance_board",
          "continuity_board",
          "resource_load_board",
          "document_readiness_board",
          "revenue_levers_board"
        ],
        "idempotency_scope": [
          "organization_id",
          "vertical_id",
          "external_reference",
          "command_key"
        ],
        "audit_mode": "append_only_with_snapshots"
      },
      "transaction_primitives": {
        "commands": [
          "capture_intent",
          "qualify_record",
          "create_quote",
          "request_deposit",
          "reserve_capacity",
          "confirm_booking",
          "start_case",
          "approve_quote",
          "collect_payment",
          "start_fulfillment",
          "close_fulfillment",
          "schedule_recurrence",
          "issue_refund",
          "reactivate_customer",
          "open_case_file",
          "run_conflict_check",
          "issue_engagement_proposal",
          "handoff_to_professional"
        ],
        "events": [
          "intent_captured",
          "record_qualified",
          "quote_created",
          "deposit_requested",
          "capacity_reserved",
          "booking_confirmed",
          "case_started",
          "quote_approved",
          "payment_collected",
          "fulfillment_started",
          "fulfillment_closed",
          "recurrence_scheduled",
          "refund_issued",
          "customer_reactivated",
          "case_file_opened",
          "conflict_checked",
          "engagement_proposal_issued",
          "professional_handoff_completed"
        ],
        "ledger_event_types": [
          "charge_opened",
          "deposit_collected",
          "installment_due",
          "payment_applied",
          "credit_issued",
          "refund_issued",
          "write_off_registered"
        ],
        "invariants": [
          "no propuesta sin conflicto revisado",
          "no consulta sin intake mínimo",
          "no contratación sin engagement letter",
          "todo pago debe referenciar quote, order o case activo",
          "todo cambio crítico debe emitir evento y renglón de auditoría",
          "ningún recurso se confirma dos veces en la misma ventana"
        ],
        "idempotency_keys": [
          "command_key",
          "payment_reference",
          "booking_reference",
          "external_message_id"
        ]
      },
      "aggregates": {
        "primary_record": {
          "name": "caso / expediente",
          "status_axis": [
            "commercial",
            "operations",
            "finance",
            "continuity"
          ]
        },
        "quote": {
          "name": "engagement_proposal",
          "states": [
            "draft",
            "sent",
            "accepted",
            "expired",
            "lost"
          ]
        },
        "booking": {
          "name": "consultation_booking",
          "states": [
            "proposed",
            "reserved",
            "confirmed",
            "attended_or_executed",
            "missed_or_canceled"
          ]
        },
        "execution": {
          "name": "engagement_progress",
          "states": [
            "pending",
            "ready",
            "in_progress",
            "blocked",
            "completed",
            "closed"
          ]
        },
        "payment_account": {
          "name": "payment_account",
          "states": [
            "open",
            "partially_paid",
            "paid",
            "overdue",
            "refunded"
          ]
        },
        "continuity": {
          "name": "case_followup_plan",
          "states": [
            "not_started",
            "active",
            "at_risk",
            "recovered",
            "closed"
          ]
        }
      },
      "orchestration": {
        "command_handlers": [
          "handle_capture_intent",
          "handle_qualify_record",
          "handle_create_quote",
          "handle_request_deposit",
          "handle_reserve_capacity",
          "handle_confirm_booking",
          "handle_start_case",
          "handle_approve_quote",
          "handle_open_case_file",
          "handle_run_conflict_check",
          "handle_issue_engagement_proposal",
          "handle_handoff_to_professional"
        ],
        "sagas": [
          "intake_to_consultation",
          "consultation_to_proposal",
          "engagement_followup"
        ],
        "money_guards": [
          "quote_before_payment",
          "capacity_before_confirmation",
          "documents_before_execution",
          "balance_before_close"
        ],
        "read_model_refresh": [
          "on_every_event",
          "nightly_reconciliation",
          "pre_dashboard_cache"
        ]
      },
      "finance": {
        "money_objects": [
          "consultation_charge",
          "retainer_deposit",
          "proposal_collection",
          "followup_charge"
        ],
        "collection_modes": [
          "consulta",
          "anticipo",
          "iguala"
        ],
        "refund_modes": [
          "consultation_credit",
          "engagement_adjustment"
        ],
        "reconciliation_views": [
          "expected_vs_collected",
          "aging_balance",
          "refund_exposure",
          "cash_by_stage"
        ]
      },
      "operations": {
        "fulfillment_unit": "intake_consultation_cycle",
        "resource_locking": [
          "professional",
          "consultation_slot",
          "document_review_capacity"
        ],
        "dispatch_or_schedule_board": [
          "queued",
          "ready",
          "assigned",
          "in_progress",
          "blocked",
          "done"
        ],
        "handoff_rules": [
          "human_handoff_on_exception",
          "supervisor_handoff_on_money_risk",
          "operator_handoff_on_compliance_gap"
        ]
      },
      "audit_compliance": {
        "timeline_entities": [
          "caso / expediente",
          "engagement_proposal",
          "consultation_booking",
          "engagement_progress",
          "payment_account"
        ],
        "consent_gates": [
          "intake_form",
          "engagement_letter",
          "required_case_documents"
        ],
        "required_evidence": [
          "timeline_event",
          "actor",
          "timestamp",
          "before_after_snapshot"
        ],
        "retention_rules": [
          "audit_log_append_only",
          "documents_linked_to_primary_record",
          "payment_trace_non_destructive"
        ]
      },
      "transaction_views": {
        "commercial": [
          "intake",
          "qualification",
          "proposal"
        ],
        "operations": [
          "document_readiness",
          "handoff",
          "case_status"
        ],
        "finance": [
          "proposal_value",
          "retainers",
          "aging_balance"
        ],
        "continuity": [
          "followup",
          "renewal",
          "cross_sell"
        ]
      },
      "command_catalog": [
        {
          "command": "capture_intent",
          "writes": "caso / expediente",
          "emits": "intent_captured",
          "guard": "no propuesta sin conflicto revisado"
        },
        {
          "command": "qualify_record",
          "writes": "caso / expediente",
          "emits": "record_qualified",
          "guard": "no consulta sin intake mínimo"
        },
        {
          "command": "create_quote",
          "writes": "caso / expediente",
          "emits": "quote_created",
          "guard": "no contratación sin engagement letter"
        },
        {
          "command": "request_deposit",
          "writes": "caso / expediente",
          "emits": "deposit_requested",
          "guard": "no propuesta sin conflicto revisado"
        },
        {
          "command": "reserve_capacity",
          "writes": "caso / expediente",
          "emits": "capacity_reserved",
          "guard": "no consulta sin intake mínimo"
        },
        {
          "command": "confirm_booking",
          "writes": "caso / expediente",
          "emits": "booking_confirmed",
          "guard": "no contratación sin engagement letter"
        },
        {
          "command": "start_case",
          "writes": "caso / expediente",
          "emits": "case_started",
          "guard": "no propuesta sin conflicto revisado"
        },
        {
          "command": "approve_quote",
          "writes": "caso / expediente",
          "emits": "quote_approved",
          "guard": "no consulta sin intake mínimo"
        },
        {
          "command": "open_case_file",
          "writes": "caso / expediente",
          "emits": "payment_collected",
          "guard": "no contratación sin engagement letter"
        },
        {
          "command": "run_conflict_check",
          "writes": "caso / expediente",
          "emits": "fulfillment_started",
          "guard": "no propuesta sin conflicto revisado"
        },
        {
          "command": "issue_engagement_proposal",
          "writes": "caso / expediente",
          "emits": "fulfillment_closed",
          "guard": "no consulta sin intake mínimo"
        },
        {
          "command": "handoff_to_professional",
          "writes": "caso / expediente",
          "emits": "recurrence_scheduled",
          "guard": "no contratación sin engagement letter"
        }
      ],
      "event_catalog": [
        {
          "event": "intent_captured",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "intake_to_consultation"
        },
        {
          "event": "record_qualified",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "consultation_to_proposal"
        },
        {
          "event": "quote_created",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "engagement_followup"
        },
        {
          "event": "deposit_requested",
          "updates": [
            "timeline",
            "boards",
            "ledger"
          ],
          "next_action": "intake_to_consultation"
        },
        {
          "event": "capacity_reserved",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "consultation_to_proposal"
        },
        {
          "event": "booking_confirmed",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "engagement_followup"
        },
        {
          "event": "case_started",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "intake_to_consultation"
        },
        {
          "event": "quote_approved",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "consultation_to_proposal"
        },
        {
          "event": "case_file_opened",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "engagement_followup"
        },
        {
          "event": "conflict_checked",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "intake_to_consultation"
        },
        {
          "event": "engagement_proposal_issued",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "consultation_to_proposal"
        },
        {
          "event": "professional_handoff_completed",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "engagement_followup"
        }
      ]
    },
    "subvertical_profiles": [],
    "recommended_subverticals": []
  },
  {
    "id": "commerce",
    "name": "WAOS Commerce",
    "short_name": "Commerce & retail conversacional",
    "description": "Sistema operativo de commerce y retail conversacional por WhatsApp.",
    "problem": "Commerce conversacional pierde ventas porque tarda en responder, presenta mal el catálogo, no tiene stock claro, no recomienda bien, no arma carrito y no recupera compras abandonadas.",
    "subverticals": [
      "ropa",
      "streetwear",
      "gorras",
      "tenis",
      "joyería",
      "relojería fashion",
      "accesorios",
      "bolsas",
      "skincare",
      "cosmética",
      "perfumería",
      "regalos",
      "home decor",
      "gadgets",
      "merch",
      "marcas DTC pequeñas"
    ],
    "objects": [
      "producto",
      "variante",
      "colección",
      "categoría",
      "stock",
      "promoción",
      "asset",
      "carrito conversacional",
      "pedido",
      "link de pago",
      "envío",
      "recompra",
      "bundle",
      "carrito / intención de compra",
      "variant / SKU",
      "stock confiable",
      "checkout intent",
      "pago",
      "orden",
      "fulfillment",
      "devolución / incidencia"
    ],
    "flows": [
      "descubrimiento -> ficha",
      "ficha -> carrito",
      "carrito -> pago",
      "pago -> envío",
      "postcompra -> cross-sell",
      "abandono -> recuperación"
    ],
    "kpis": [
      "conversación a pedido",
      "pedido a pago",
      "recuperación de carrito",
      "ticket promedio",
      "recompra",
      "abandono por falta de stock",
      "abandono de carrito",
      "conversión",
      "AOV",
      "incidencia postventa"
    ],
    "recommended_integrations": [
      "whatsapp",
      "payments",
      "catalog",
      "media",
      "promotions",
      "insights"
    ],
    "default_services": [
      "descubrimiento de producto",
      "armado de pedido",
      "pago por link",
      "seguimiento de envio",
      "recompra y cross-sell"
    ],
    "default_faqs": [
      {
        "q": "¿Tienen talla, color o stock?",
        "a": "Si, el bot puede responder variantes, precio y disponibilidad del catalogo conectado."
      },
      {
        "q": "¿Puedo comprar por WhatsApp?",
        "a": "Si, podemos ayudarte a armar pedido y enviarte link de pago."
      },
      {
        "q": "¿Que pasa si no termino la compra?",
        "a": "El bot puede retomar carritos conversacionales y ayudarte a cerrarlos."
      },
      {
        "q": "¿Me avisan del envio?",
        "a": "Si, podemos confirmar compra y compartir estatus de envio o entrega."
      }
    ],
    "behavior": {
      "tone": "vendedor digital",
      "response_length": "corta",
      "use_emojis": false,
      "sales_intensity": "alta",
      "offer_promotions_when": "always_when_relevant",
      "escalate_when": [
        "fraude",
        "reclamo fuerte",
        "devolucion compleja"
      ],
      "insistence_policy": "respectful",
      "can_share_price_directly": true,
      "can_negotiate": false,
      "can_mention_stock": true,
      "auto_send_images": true,
      "bot_mode": "venta_conversacional",
      "active_channels": [
        "whatsapp",
        "instagram_dm",
        "webchat"
      ],
      "forbidden_topics": [
        "inventario no validado",
        "promesas de entrega no configuradas"
      ],
      "required_phrases": [
        "te ayudo a encontrar producto",
        "puedo armar tu pedido y enviarte link de pago",
        "te sigo",
        "si la pregunta viene rara, igual te la aterrizo",
        "te lo aterrizo a tu caso"
      ],
      "fallback_message": "Te ayudo a elegir producto, revisar variantes y cerrar tu compra por chat. Si la pregunta viene rara, en broma o medio fuera de tema, igual te sigo y la aterrizamos al negocio.",
      "humor_policy": "light_contextual",
      "strange_question_policy": "respond_validate_reframe_sell_move"
    },
    "followup_rules": [
      {
        "type": "no_response",
        "delay_minutes": 45,
        "max_attempts": 2,
        "message_template": "¿Quieres que te comparta opciones, confirme stock o arme tu pedido?"
      },
      {
        "type": "post_quote",
        "delay_minutes": 360,
        "max_attempts": 2,
        "message_template": "Todavia puedo ayudarte a completar tu compra o resolver talla, color, stock y envio."
      },
      {
        "type": "reactivation",
        "delay_minutes": 10080,
        "max_attempts": 2,
        "message_template": "Tenemos novedades, reposiciones o complementos que pueden encajar contigo. ¿Quieres ver opciones?"
      }
    ],
    "templates": [
      {
        "template_key": "product_discovery",
        "title": "Descubrimiento de producto",
        "content": "Cuentame que buscas y te recomiendo opciones de catalogo con precio, color, talla o variante disponible.",
        "variables": []
      },
      {
        "template_key": "cart_build",
        "title": "Armado de carrito",
        "content": "Ya tengo tu pedido casi listo. Si quieres, confirmamos variante, envio y te mando el link de pago.",
        "variables": []
      },
      {
        "template_key": "payment_link",
        "title": "Link de pago",
        "content": "Perfecto. Te comparto el link de pago para confirmar tu compra en este momento.",
        "variables": []
      },
      {
        "template_key": "shipment_update",
        "title": "Estatus de envio",
        "content": "Tu pedido ya esta en etapa de {{shipping_status}}. Si quieres, te comparto el siguiente paso o referencia.",
        "variables": [
          "shipping_status"
        ]
      },
      {
        "template_key": "abandoned_cart",
        "title": "Recuperacion carrito",
        "content": "Tu pedido sigue disponible. Si quieres, retomamos talla, color, stock o metodo de pago para cerrarlo hoy.",
        "variables": []
      }
    ],
    "config_overrides": {
      "objective_secondary": [
        "vender",
        "upsell",
        "reactivar"
      ],
      "policies": [
        "No prometer stock o entregas no confirmadas",
        "Escalar fraudes o devoluciones sensibles"
      ],
      "can_say": [
        "precio",
        "stock",
        "color",
        "talla",
        "envio",
        "promocion",
        "link de pago"
      ],
      "cannot_say": [
        "stock no validado",
        "entregas no configuradas",
        "promesas logisticas"
      ],
      "whatsapp_flows": [
        "descubrimiento_producto",
        "carrito_conversacional",
        "link_de_pago",
        "recuperacion_carrito"
      ],
      "appointment_duration_minutes": 20,
      "handoff_keywords": [
        "fraude",
        "cobro duplicado",
        "devolucion",
        "reembolso"
      ],
      "high_score_threshold": 70
    },
    "portfolio_tier": "tier_3_guarded",
    "master_thesis": "Sistema operativo de commerce y retail conversacional que convierte WhatsApp en descubrimiento, recomendación, pedido, pago, seguimiento y recompra para catálogos simples o medianos.",
    "buyer": {
      "primary": "Founder o gerente comercial de marca retail/DTC pequeña",
      "secondary": [
        "operación e-commerce ligera",
        "equipo de ventas por WhatsApp",
        "marketing de drops"
      ]
    },
    "one_pager": {
      "headline": "WAOS Commerce",
      "thesis": "WhatsApp se convierte en vendedor digital con catálogo estructurado, carrito conversacional, pago y recompra.",
      "problem": "La conversación sí existe, pero no se transforma en pedido porque falta catálogo serio, recomendación, stock y recuperación.",
      "promise": "Cada conversación termina en recomendación, pedido, pago, seguimiento o winback.",
      "monetizes": [
        "pedido",
        "link de pago",
        "upsell",
        "cross-sell",
        "recompra",
        "drops",
        "bundles"
      ],
      "packaging": [
        "setup commerce conversacional",
        "business hub + customer experience",
        "catálogo + media + promos + pagos",
        "retención y recompra"
      ],
      "strategic_care": "Debe venderse como retail conversacional controlado, no como e-commerce pesado con logística compleja o miles de SKUs en tiempo real."
    },
    "demo_flow": [
      "El cliente entra preguntando por producto, talla, color, precio o recomendación.",
      "WAOS detecta intención y producto/categoría/variante.",
      "Responde con ficha enriquecida, stock, promo y alternativas.",
      "Arma pedido y envía link de pago.",
      "Confirma compra y seguimiento de envío o entrega.",
      "Después activa cross-sell, recompra y recuperación de carrito."
    ],
    "native_objects": {
      "core": [
        "cliente",
        "producto",
        "variante",
        "categoría",
        "colección",
        "asset",
        "orden"
      ],
      "commercial": [
        "stock",
        "promoción",
        "bundle",
        "carrito conversacional",
        "pedido",
        "link de pago"
      ],
      "operations": [
        "envío",
        "pickup",
        "recompra",
        "pregunta de producto",
        "cliente recurrente"
      ]
    },
    "pipeline": {
      "primary": {
        "name": "Conversión conversacional",
        "states": [
          "lead nuevo",
          "producto identificado",
          "interés calificado",
          "ficha enviada",
          "carrito iniciado",
          "pago pendiente",
          "pago confirmado",
          "pedido armado",
          "envío o entrega",
          "postventa",
          "recompra pendiente",
          "recompra",
          "carrito abandonado",
          "perdido por stock/precio/silencio"
        ]
      },
      "secondary": [
        {
          "name": "Drops y lanzamientos",
          "states": [
            "anunciado",
            "interés captado",
            "lista de espera",
            "pedido",
            "agotado",
            "winback con sustituto"
          ]
        }
      ]
    },
    "bot_playbook": {
      "must_do": [
        "descubrir intención",
        "recomendar productos",
        "mostrar variantes",
        "responder precio y stock",
        "construir pedido",
        "mandar link de pago",
        "recuperar carrito",
        "seguir envío",
        "empujar recompra",
        "nunca quedarse seco ante bromas, preguntas raras o cambios bruscos de tema",
        "usar humor ligero cuando sume, sin sonar payaso ni poco serio",
        "validar el momento y luego reencauzar la conversacion al negocio",
        "cerrar siempre con una pregunta util o siguiente paso"
      ],
      "must_ask": [
        "categoría buscada",
        "talla/color/variante",
        "presupuesto",
        "urgencia",
        "uso o estilo",
        "entrega o pickup",
        "que parte del negocio se esta atorando mas",
        "si quiere que se lo aterrice a su caso"
      ],
      "objections": [
        "precio",
        "stock",
        "talla",
        "color",
        "envío",
        "quiero pensarlo",
        "muéstrame más opciones"
      ],
      "escalate_when": [
        "pedido complejo",
        "mayoreo",
        "personalización",
        "reclamación",
        "problema de pago",
        "cliente VIP"
      ],
      "forbidden": [
        "prometer stock no confirmado",
        "prometer tiempos logísticos no integrados",
        "vender como e-commerce enterprise"
      ],
      "success_signals": [
        "quiero comprar",
        "agrega ese",
        "mándame el link",
        "¿sí hay mi talla?",
        "quiero apartarlo"
      ],
      "style": [
        "humor ligero",
        "manejo de preguntas raras",
        "reencuadre comercial"
      ]
    },
    "automation_sequences": [
      {
        "key": "commerce_cart",
        "name": "Carrito abandonado",
        "trigger": "carrito iniciado sin pago",
        "goal": "recuperar compra",
        "steps": [
          "recordar producto",
          "resolver objeción",
          "reenviar link"
        ]
      },
      {
        "key": "commerce_payment",
        "name": "Pago pendiente",
        "trigger": "link emitido sin confirmación",
        "goal": "cerrar pago",
        "steps": [
          "recordar vencimiento",
          "confirmar monto",
          "reenviar link"
        ]
      },
      {
        "key": "commerce_postpurchase",
        "name": "Post compra",
        "trigger": "pedido pagado",
        "goal": "seguimiento + cross-sell",
        "steps": [
          "confirmar compra",
          "actualizar envío",
          "sugerir complemento"
        ]
      },
      {
        "key": "commerce_winback",
        "name": "Recompra o winback",
        "trigger": "ventana ideal de recompra",
        "goal": "retención",
        "steps": [
          "recomendar reposición",
          "ofrecer promo",
          "cerrar pedido"
        ]
      }
    ],
    "dashboard": {
      "north_star": "Conversación a pago confirmado con recompra.",
      "sections": [
        {
          "name": "Conversión",
          "metrics": [
            "conversaciones a producto identificado",
            "producto a pedido",
            "pedido a pago",
            "recuperación de carrito"
          ]
        },
        {
          "name": "Revenue",
          "metrics": [
            "ticket promedio",
            "revenue por categoría",
            "revenue por promoción",
            "revenue por recompra"
          ]
        },
        {
          "name": "Catálogo",
          "metrics": [
            "productos más consultados",
            "productos con más abandono",
            "pérdida por stock",
            "assets con mejor conversión"
          ]
        },
        {
          "name": "Clientes",
          "metrics": [
            "nuevos vs recurrentes",
            "frecuencia de compra",
            "cross-sell rate",
            "winback rate"
          ]
        }
      ]
    },
    "hardening_model": {
      "goal": "Pasar de preset inteligente a sistema especialista",
      "wave": "ola_3",
      "entity_queen": "orden",
      "core_common": true,
      "domain_by_vertical": true,
      "playbooks_by_subvertical": true,
      "kpis_by_vertical": true,
      "pricing_by_vertical": true,
      "journeys_by_vertical": true,
      "reusable_modules": [
        "intake / calificación",
        "agenda / recursos",
        "cotización / propuesta",
        "pago / anticipo / membresía",
        "seguimiento / recurrencia",
        "reporting vertical"
      ],
      "minimum_viable_hardening": [
        "1 entidad reina",
        "1 pipeline propio",
        "1 cotización propia",
        "1 recurrencia propia",
        "1 dashboard propio"
      ],
      "hard_checklist": [
        "tiene entidad principal propia",
        "tiene pipeline específico",
        "tiene cotización o pricing del nicho",
        "tiene agenda o recursos del nicho",
        "tiene postventa o recurrencia del nicho",
        "tiene documentos o compliance del nicho",
        "tiene KPIs del nicho",
        "tiene 3 automatizaciones que mueven dinero",
        "tiene 2 pruebas e2e de negocio",
        "tiene subplaybooks por subvertical",
        "entidad principal propia",
        "pipeline específico",
        "pricing del nicho",
        "agenda y recursos del nicho",
        "postventa o recurrencia del nicho",
        "documentos o compliance del nicho",
        "KPIs del nicho",
        "3 automatizaciones que mueven dinero",
        "2 pruebas e2e de negocio",
        "subplaybooks por subvertical",
        "runtime ejecutable por vertical"
      ]
    },
    "specialist_layers": {
      "persistent_entities": [
        "carrito / intención de compra",
        "variant / SKU",
        "stock confiable",
        "checkout intent",
        "pago",
        "orden",
        "fulfillment",
        "devolución / incidencia"
      ],
      "business_pipeline": {
        "primary_entity": "orden",
        "primary_pipeline": {
          "name": "Conversión conversacional",
          "states": [
            "lead nuevo",
            "producto identificado",
            "interés calificado",
            "ficha enviada",
            "carrito iniciado",
            "pago pendiente",
            "pago confirmado",
            "pedido armado",
            "envío o entrega",
            "postventa",
            "recompra pendiente",
            "recompra",
            "carrito abandonado",
            "perdido por stock/precio/silencio"
          ]
        },
        "secondary_pipelines": [
          {
            "name": "Drops y lanzamientos",
            "states": [
              "anunciado",
              "interés captado",
              "lista de espera",
              "pedido",
              "agotado",
              "winback con sustituto"
            ]
          }
        ]
      },
      "pricing_and_quotes": [
        "precio por variante",
        "bundle inteligente",
        "cross-sell",
        "rescate de carrito"
      ],
      "agenda_and_resources": [
        "inventario",
        "fulfillment",
        "pickup",
        "slot de envío",
        "promoción activa"
      ],
      "post_sale_and_recurrence": [
        "postcompra automatizada",
        "reseña",
        "reposición",
        "recompra"
      ],
      "documents_compliance": [
        "confirmación de orden",
        "guía / tracking",
        "política de devoluciones",
        "incidencia postventa"
      ],
      "kpis_that_matter": [
        "conversación a pedido",
        "pedido a pago",
        "recuperación de carrito",
        "ticket promedio",
        "recompra",
        "abandono por falta de stock",
        "abandono de carrito",
        "conversión",
        "AOV",
        "incidencia postventa"
      ],
      "money_automations": [
        "abandono de carrito",
        "cross-sell postcompra",
        "recompra por reposición"
      ]
    },
    "domain_contract": {
      "vertical_entity_types": [
        "carrito / intención de compra",
        "variant / SKU",
        "stock confiable",
        "checkout intent",
        "pago",
        "orden",
        "fulfillment",
        "devolución / incidencia"
      ],
      "vertical_pipeline_stages": {
        "primary": [
          "lead nuevo",
          "producto identificado",
          "interés calificado",
          "ficha enviada",
          "carrito iniciado",
          "pago pendiente",
          "pago confirmado",
          "pedido armado",
          "envío o entrega",
          "postventa",
          "recompra pendiente",
          "recompra",
          "carrito abandonado",
          "perdido por stock/precio/silencio"
        ],
        "secondary": [
          [
            "anunciado",
            "interés captado",
            "lista de espera",
            "pedido",
            "agotado",
            "winback con sustituto"
          ]
        ]
      },
      "vertical_quote_types": [
        "checkout",
        "bundle",
        "cross-sell",
        "promoción",
        "reposición / recompra"
      ],
      "vertical_resource_types": [
        "inventario",
        "fulfillment",
        "pickup",
        "slot de envío",
        "promoción activa"
      ],
      "vertical_followup_policies": [
        "postcompra automatizada",
        "reseña",
        "reposición",
        "recompra"
      ],
      "vertical_kpi_definitions": [
        "conversación a pedido",
        "pedido a pago",
        "recuperación de carrito",
        "ticket promedio",
        "recompra",
        "abandono por falta de stock",
        "abandono de carrito",
        "conversión",
        "AOV",
        "incidencia postventa"
      ],
      "vertical_playbooks": [
        "moda",
        "suplementos no regulados",
        "hogar",
        "electrónica ligera",
        "alimentos empaquetados"
      ],
      "vertical_document_types": [
        "confirmación de orden",
        "guía / tracking",
        "política de devoluciones",
        "incidencia postventa"
      ]
    },
    "subvertical_playbooks": [
      {
        "name": "moda",
        "focus": "Playbook operativo y comercial para moda"
      },
      {
        "name": "suplementos no regulados",
        "focus": "Playbook operativo y comercial para suplementos no regulados"
      },
      {
        "name": "hogar",
        "focus": "Playbook operativo y comercial para hogar"
      },
      {
        "name": "electrónica ligera",
        "focus": "Playbook operativo y comercial para electrónica ligera"
      },
      {
        "name": "alimentos empaquetados",
        "focus": "Playbook operativo y comercial para alimentos empaquetados"
      }
    ],
    "business_e2e_tests": [
      {
        "name": "cliente agrega al carrito, completa checkout y activa tracking",
        "status": "designed"
      },
      {
        "name": "comprador postventa recibe recomendación y recompra bundle",
        "status": "designed"
      }
    ],
    "vertical_runtime": {
      "pipeline_machine": {
        "primary_pipeline": "Conversión conversacional",
        "entity": "intención de compra",
        "states": [
          "lead nuevo",
          "producto identificado",
          "interés calificado",
          "ficha enviada",
          "carrito iniciado",
          "pago pendiente",
          "pago confirmado",
          "pedido armado",
          "envío o entrega",
          "postventa",
          "recompra pendiente",
          "recompra",
          "carrito abandonado",
          "perdido por stock/precio/silencio"
        ],
        "transitions": [
          {
            "from": "lead nuevo",
            "to": "producto identificado",
            "trigger": "qualification_complete",
            "business_effect": "advance opportunity"
          },
          {
            "from": "producto identificado",
            "to": "interés calificado",
            "trigger": "order_delivered",
            "business_effect": "open commercial step"
          },
          {
            "from": "carrito abandonado",
            "to": "perdido por stock/precio/silencio",
            "trigger": "successful_outcome",
            "business_effect": "realize revenue or continuity"
          },
          {
            "from": "carrito abandonado",
            "to": "at_risk",
            "trigger": "cart_abandoned",
            "business_effect": "activate retention sequence"
          }
        ],
        "at_risk_state": "at_risk",
        "closed_states": [
          "perdido por stock/precio/silencio"
        ]
      },
      "pricing_engine": {
        "quote_types": [
          "carrito",
          "checkout",
          "bundle",
          "reposicion"
        ],
        "pricing_basis": "sku + variant + bundle + shipping + promotion",
        "rules": [
          {
            "rule": "base price by orden type",
            "effect": "set base_price"
          },
          {
            "rule": "premium or urgent add-ons increase quote",
            "effect": "add surcharge"
          },
          {
            "rule": "bundle, membership or financing can lower immediate friction",
            "effect": "recommend package or installments"
          }
        ],
        "deposit_policy": "request advance when capacity, specialist time or inventory must be secured"
      },
      "resource_capacity": {
        "resource_types": [
          "sku",
          "inventario",
          "slot de pickup",
          "carrier",
          "agente postventa"
        ],
        "capacity_basis": "inventory availability, prep capacity and fulfillment windows",
        "constraints": [
          "avoid double booking of critical resources",
          "respect service duration and cleanup/buffer time",
          "prioritize higher urgency and higher close probability cases"
        ],
        "priority_queue": "sku, pago y fulfillment"
      },
      "recurrence_engine": {
        "policies": [
          {
            "type": "cart_recovery",
            "interval_days": 1,
            "anchor": "intención de compra"
          },
          {
            "type": "reorder_cycle",
            "interval_days": 30,
            "anchor": "intención de compra"
          },
          {
            "type": "review_request",
            "interval_days": 7,
            "anchor": "intención de compra"
          }
        ],
        "reactivation_window_days": 30,
        "goal": "protect retention, repeat revenue and continuity"
      },
      "kpi_engine": {
        "north_star": "Conversación a pago confirmado con recompra.",
        "definitions": [
          {
            "name": "cart_conversion",
            "formula": "paid_orders / checkouts_started"
          },
          {
            "name": "aov",
            "formula": "revenue / paid_orders"
          },
          {
            "name": "repurchase_90d",
            "formula": "repeat_buyers_90d / delivered_buyers"
          }
        ],
        "leading_indicators": [
          "cart_abandoned",
          "checkout_started",
          "no_response_7d"
        ]
      },
      "automation_engine": {
        "money_automation_policies": [
          {
            "trigger": "cart_abandoned",
            "actions": [
              "send_followup",
              "escalate_owner",
              "offer_relevant_next_step"
            ],
            "goal": "save conversion or retention"
          },
          {
            "trigger": "checkout_started",
            "actions": [
              "send_quote_or_payment_link",
              "remind_deadline",
              "notify_human"
            ],
            "goal": "move revenue forward"
          },
          {
            "trigger": "return_requested",
            "actions": [
              "schedule_recurrence",
              "cross_sell_next_best_offer",
              "create_task"
            ],
            "goal": "increase LTV"
          }
        ],
        "quiet_hours": "21:00-08:00"
      },
      "document_flow": {
        "required_documents": [
          "confirmacion de orden",
          "guia de envio",
          "solicitud de devolucion",
          "incidencia postventa"
        ],
        "lifecycle_rules": [
          {
            "document": "confirmacion de orden",
            "required_before": "first committed step",
            "signature_required": true
          },
          {
            "document": "incidencia postventa",
            "required_before": "handoff or continuity step",
            "signature_required": false
          }
        ]
      },
      "matching_engine": {
        "entity": "intención de compra",
        "rules": [
          "sku availability",
          "variant preference",
          "basket affinity",
          "shipping_zone_match"
        ],
        "next_best_match_outputs": [
          "best_owner",
          "best_resource_slot",
          "best_offer"
        ]
      }
    },
    "transactional_motor_v12": {
      "version": "v12_full_transactional",
      "aggregate_root": "commerce_order_account",
      "main_business_entity": "orden",
      "transaction_unit": "cart_checkout_cycle",
      "system_of_record": {
        "write_model": [
          "commands",
          "events",
          "ledger",
          "aggregate_snapshots"
        ],
        "read_models": [
          "commercial_board",
          "operations_board",
          "finance_board",
          "continuity_board",
          "resource_load_board",
          "document_readiness_board",
          "revenue_levers_board"
        ],
        "idempotency_scope": [
          "organization_id",
          "vertical_id",
          "external_reference",
          "command_key"
        ],
        "audit_mode": "append_only_with_snapshots"
      },
      "transaction_primitives": {
        "commands": [
          "capture_intent",
          "qualify_record",
          "create_quote",
          "request_deposit",
          "reserve_capacity",
          "confirm_booking",
          "start_case",
          "approve_quote",
          "collect_payment",
          "start_fulfillment",
          "close_fulfillment",
          "schedule_recurrence",
          "issue_refund",
          "reactivate_customer",
          "reserve_cart_stock",
          "create_checkout",
          "release_to_fulfillment",
          "open_return_case"
        ],
        "events": [
          "intent_captured",
          "record_qualified",
          "quote_created",
          "deposit_requested",
          "capacity_reserved",
          "booking_confirmed",
          "case_started",
          "quote_approved",
          "payment_collected",
          "fulfillment_started",
          "fulfillment_closed",
          "recurrence_scheduled",
          "refund_issued",
          "customer_reactivated",
          "cart_stock_reserved",
          "checkout_created",
          "released_to_fulfillment",
          "return_case_opened"
        ],
        "ledger_event_types": [
          "charge_opened",
          "deposit_collected",
          "installment_due",
          "payment_applied",
          "credit_issued",
          "refund_issued",
          "write_off_registered"
        ],
        "invariants": [
          "no checkout sin stock reservado",
          "no surtir pedido sin pago o condición válida",
          "no cerrar devolución sin trazabilidad",
          "todo pago debe referenciar quote, order o case activo",
          "todo cambio crítico debe emitir evento y renglón de auditoría",
          "ningún recurso se confirma dos veces en la misma ventana"
        ],
        "idempotency_keys": [
          "command_key",
          "payment_reference",
          "booking_reference",
          "external_message_id"
        ]
      },
      "aggregates": {
        "primary_record": {
          "name": "orden",
          "status_axis": [
            "commercial",
            "operations",
            "finance",
            "continuity"
          ]
        },
        "quote": {
          "name": "checkout_quote",
          "states": [
            "draft",
            "sent",
            "accepted",
            "expired",
            "lost"
          ]
        },
        "booking": {
          "name": "checkout_reservation",
          "states": [
            "proposed",
            "reserved",
            "confirmed",
            "attended_or_executed",
            "missed_or_canceled"
          ]
        },
        "execution": {
          "name": "order_fulfillment",
          "states": [
            "pending",
            "ready",
            "in_progress",
            "blocked",
            "completed",
            "closed"
          ]
        },
        "payment_account": {
          "name": "payment_account",
          "states": [
            "open",
            "partially_paid",
            "paid",
            "overdue",
            "refunded"
          ]
        },
        "continuity": {
          "name": "post_purchase_reorder_plan",
          "states": [
            "not_started",
            "active",
            "at_risk",
            "recovered",
            "closed"
          ]
        }
      },
      "orchestration": {
        "command_handlers": [
          "handle_capture_intent",
          "handle_qualify_record",
          "handle_create_quote",
          "handle_request_deposit",
          "handle_reserve_capacity",
          "handle_confirm_booking",
          "handle_start_case",
          "handle_approve_quote",
          "handle_reserve_cart_stock",
          "handle_create_checkout",
          "handle_release_to_fulfillment",
          "handle_open_return_case"
        ],
        "sagas": [
          "cart_to_checkout",
          "checkout_to_delivery",
          "post_purchase_reorder"
        ],
        "money_guards": [
          "quote_before_payment",
          "capacity_before_confirmation",
          "documents_before_execution",
          "balance_before_close"
        ],
        "read_model_refresh": [
          "on_every_event",
          "nightly_reconciliation",
          "pre_dashboard_cache"
        ]
      },
      "finance": {
        "money_objects": [
          "cart_charge",
          "shipping_charge",
          "refund_issue",
          "reorder_collection"
        ],
        "collection_modes": [
          "checkout",
          "contra entrega si aplica",
          "recompra"
        ],
        "refund_modes": [
          "return_refund",
          "store_credit"
        ],
        "reconciliation_views": [
          "expected_vs_collected",
          "aging_balance",
          "refund_exposure",
          "cash_by_stage"
        ]
      },
      "operations": {
        "fulfillment_unit": "cart_checkout_cycle",
        "resource_locking": [
          "inventory_unit",
          "pick_pack_capacity",
          "delivery_slot"
        ],
        "dispatch_or_schedule_board": [
          "queued",
          "ready",
          "assigned",
          "in_progress",
          "blocked",
          "done"
        ],
        "handoff_rules": [
          "human_handoff_on_exception",
          "supervisor_handoff_on_money_risk",
          "operator_handoff_on_compliance_gap"
        ]
      },
      "audit_compliance": {
        "timeline_entities": [
          "orden",
          "checkout_quote",
          "checkout_reservation",
          "order_fulfillment",
          "payment_account"
        ],
        "consent_gates": [
          "order_confirmation",
          "shipping_proof",
          "return_request"
        ],
        "required_evidence": [
          "timeline_event",
          "actor",
          "timestamp",
          "before_after_snapshot"
        ],
        "retention_rules": [
          "audit_log_append_only",
          "documents_linked_to_primary_record",
          "payment_trace_non_destructive"
        ]
      },
      "transaction_views": {
        "commercial": [
          "browse",
          "cart",
          "checkout"
        ],
        "operations": [
          "inventory",
          "fulfillment",
          "returns"
        ],
        "finance": [
          "conversion",
          "aov",
          "refund_rate"
        ],
        "continuity": [
          "reorder",
          "review",
          "cross_sell"
        ]
      },
      "command_catalog": [
        {
          "command": "capture_intent",
          "writes": "orden",
          "emits": "intent_captured",
          "guard": "no checkout sin stock reservado"
        },
        {
          "command": "qualify_record",
          "writes": "orden",
          "emits": "record_qualified",
          "guard": "no surtir pedido sin pago o condición válida"
        },
        {
          "command": "create_quote",
          "writes": "orden",
          "emits": "quote_created",
          "guard": "no cerrar devolución sin trazabilidad"
        },
        {
          "command": "request_deposit",
          "writes": "orden",
          "emits": "deposit_requested",
          "guard": "no checkout sin stock reservado"
        },
        {
          "command": "reserve_capacity",
          "writes": "orden",
          "emits": "capacity_reserved",
          "guard": "no surtir pedido sin pago o condición válida"
        },
        {
          "command": "confirm_booking",
          "writes": "orden",
          "emits": "booking_confirmed",
          "guard": "no cerrar devolución sin trazabilidad"
        },
        {
          "command": "start_case",
          "writes": "orden",
          "emits": "case_started",
          "guard": "no checkout sin stock reservado"
        },
        {
          "command": "approve_quote",
          "writes": "orden",
          "emits": "quote_approved",
          "guard": "no surtir pedido sin pago o condición válida"
        },
        {
          "command": "reserve_cart_stock",
          "writes": "orden",
          "emits": "payment_collected",
          "guard": "no cerrar devolución sin trazabilidad"
        },
        {
          "command": "create_checkout",
          "writes": "orden",
          "emits": "fulfillment_started",
          "guard": "no checkout sin stock reservado"
        },
        {
          "command": "release_to_fulfillment",
          "writes": "orden",
          "emits": "fulfillment_closed",
          "guard": "no surtir pedido sin pago o condición válida"
        },
        {
          "command": "open_return_case",
          "writes": "orden",
          "emits": "recurrence_scheduled",
          "guard": "no cerrar devolución sin trazabilidad"
        }
      ],
      "event_catalog": [
        {
          "event": "intent_captured",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "cart_to_checkout"
        },
        {
          "event": "record_qualified",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "checkout_to_delivery"
        },
        {
          "event": "quote_created",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "post_purchase_reorder"
        },
        {
          "event": "deposit_requested",
          "updates": [
            "timeline",
            "boards",
            "ledger"
          ],
          "next_action": "cart_to_checkout"
        },
        {
          "event": "capacity_reserved",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "checkout_to_delivery"
        },
        {
          "event": "booking_confirmed",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "post_purchase_reorder"
        },
        {
          "event": "case_started",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "cart_to_checkout"
        },
        {
          "event": "quote_approved",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "checkout_to_delivery"
        },
        {
          "event": "cart_stock_reserved",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "post_purchase_reorder"
        },
        {
          "event": "checkout_created",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "cart_to_checkout"
        },
        {
          "event": "released_to_fulfillment",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "checkout_to_delivery"
        },
        {
          "event": "return_case_opened",
          "updates": [
            "timeline",
            "boards",
            "aggregate"
          ],
          "next_action": "post_purchase_reorder"
        }
      ]
    },
    "subvertical_profiles": [],
    "recommended_subverticals": []
  },
  {
    "id": "waos-bot",
    "name": "WAOS Bot",
    "short_name": "Bot que vende WAOS",
    "description": "Asesor comercial conversacional para vender WAOS por WhatsApp sin sonar tecnico ni robotico.",
    "problem": "Cuando un prospecto pregunta raro, bromea, se desahoga o cambia de tema, un bot tieso rompe confianza. Esta vertical existe para que la conversacion nunca muera y siempre vuelva al negocio.",
    "subverticals": [
      "prospectos inbound",
      "referidos",
      "campanas",
      "reactivacion de leads frios",
      "agenda de demos",
      "cierres consultivos",
      "takeover humano",
      "instalacion"
    ],
    "objects": [
      "lead",
      "dolor",
      "fuga comercial",
      "objecion",
      "diagnostico",
      "demo",
      "takeover humano",
      "seguimiento",
      "propuesta",
      "instalacion"
    ],
    "flows": [
      "caos -> entendimiento",
      "entendimiento -> diagnostico",
      "diagnostico -> demo",
      "demo -> propuesta",
      "propuesta -> instalacion",
      "lead frio -> reactivacion"
    ],
    "kpis": [
      "reply speed",
      "lead to demo",
      "demo show rate",
      "demo to propuesta",
      "propuesta a cierre",
      "reactivacion de leads",
      "conversaciones que no mueren"
    ],
    "recommended_integrations": [
      "whatsapp",
      "crm",
      "calendar",
      "webhooks",
      "analytics"
    ],
    "default_services": [
      "diagnostico express",
      "demo guiada",
      "setup inicial",
      "instalacion",
      "takeover humano"
    ],
    "default_faqs": [
      {
        "q": "Que hace WAOS exactamente?",
        "a": "Te ayuda a responder mejor, seguir prospectos, no perder leads y mover conversaciones a venta por WhatsApp."
      },
      {
        "q": "Va a sonar como robot?",
        "a": "No deberia. Esta vertical esta pensada para sonar cercana, clara y comercial, sin verse tiesa ni tecnica."
      },
      {
        "q": "Puede aguantar preguntas raras o bromas?",
        "a": "Si. La idea es que nunca se quede seco: conecta, responde, reubica y sigue vendiendo."
      },
      {
        "q": "Tambien agenda demos o seguimiento?",
        "a": "Si. Puede llevar a demo, diagnostico, propuesta o takeover humano segun el momento del prospecto."
      }
    ],
    "behavior": {
      "tone": "cercano, relajado y filoso",
      "response_length": "media",
      "use_emojis": false,
      "sales_intensity": "alta",
      "offer_promotions_when": "after_pain_detected",
      "escalate_when": [
        "pide humano",
        "caso tecnico profundo",
        "contrato",
        "precio enterprise",
        "queja fuerte"
      ],
      "insistence_policy": "respectful",
      "can_share_price_directly": false,
      "can_negotiate": false,
      "can_mention_stock": false,
      "auto_send_images": false,
      "bot_mode": "diagnostico_y_cierre_consultivo",
      "active_channels": [
        "whatsapp",
        "webchat",
        "instagram_dm"
      ],
      "forbidden_topics": [
        "inventar funciones",
        "prometer resultados exactos",
        "fingir ser persona",
        "hablar como sistema"
      ],
      "required_phrases": [
        "nunca se queda seco",
        "te lo aterrizo a tu caso",
        "te sigo",
        "si la pregunta viene rara, igual te la aterrizo"
      ],
      "fallback_message": "Te sigo. Aunque la conversacion venga medio en caos, te ayudo a aterrizar si hoy te conviene responder mejor, seguir leads o cerrar mas por WhatsApp. Si la pregunta viene rara, en broma o medio fuera de tema, igual te sigo y la aterrizamos al negocio.",
      "humor_policy": "light_contextual",
      "strange_question_policy": "respond_validate_reframe_sell_move"
    },
    "followup_rules": [
      {
        "type": "no_response",
        "delay_minutes": 180,
        "max_attempts": 2,
        "message_template": "Solo retomando esto porque por lo que me contaste si hay una fuga clara. Si quieres te lo aterrizo en 2 minutos a tu negocio."
      },
      {
        "type": "post_quote",
        "delay_minutes": 1440,
        "max_attempts": 2,
        "message_template": "Quedo pendiente por si quieres ver un ejemplo ya aterrizado a tu caso o revisar como no dejar leads tirados en WhatsApp."
      },
      {
        "type": "reactivation",
        "delay_minutes": 10080,
        "max_attempts": 1,
        "message_template": "Paso rapido por aqui porque esto sigue sonando a que traes ventas fugandose. Si quieres, vemos donde meter WAOS sin complicarte mas la operacion."
      }
    ],
    "templates": [
      {
        "template_key": "lead_capture",
        "title": "Entrada con colmillo",
        "content": "Que bueno que escribiste. Te ayudo a aterrizar rapido si hoy el dolor esta en responder, seguir prospectos o cerrar mejor por WhatsApp.",
        "variables": []
      },
      {
        "template_key": "pain_diagnosis",
        "title": "Mini diagnostico",
        "content": "Por como lo cuentas, aqui no falta que contestes mas: falta que el seguimiento no se enfrie. Si quieres te hago un mini diagnostico.",
        "variables": []
      },
      {
        "template_key": "demo_offer",
        "title": "Invitacion a demo",
        "content": "Si te late, te enseño con un ejemplo como se veria WAOS contestando, reubicando y moviendo la conversacion a venta en tu negocio.",
        "variables": []
      },
      {
        "template_key": "objection_followup",
        "title": "Seguimiento con humor ligero",
        "content": "La neta, si esto siguiera cayendo en ti todo el dia cualquiera se quema. Por eso vale la pena ver como lo bajamos con WAOS. ¿Lo aterrizamos?",
        "variables": []
      },
      {
        "template_key": "human_takeover",
        "title": "Takeover humano",
        "content": "Aqui ya conviene que te pase con alguien del equipo para verlo fino y sin vueltas. Si quieres te conecto.",
        "variables": []
      }
    ],
    "config_overrides": {
      "objective_secondary": [
        "diagnosticar",
        "agendar",
        "cerrar"
      ],
      "policies": [
        "No inventar funciones, precios ni politicas",
        "No fingir ser persona",
        "No cortar conversaciones en frio",
        "Primero validar el momento emocional y luego vender"
      ],
      "can_say": [
        "responder mejor",
        "seguir leads",
        "agendar demo",
        "takeover humano",
        "recuperar conversaciones frias",
        "ordenar WhatsApp"
      ],
      "cannot_say": [
        "jerga tecnica",
        "promesas de resultados exactos",
        "precios inventados",
        "frases roboticas"
      ],
      "whatsapp_flows": [
        "diagnostico_express",
        "agenda_demo",
        "seguimiento_objecion",
        "reactivacion_lead_frio",
        "takeover_humano"
      ],
      "appointment_duration_minutes": 30,
      "handoff_keywords": [
        "humano",
        "asesor",
        "equipo",
        "contrato",
        "precio enterprise",
        "integracion especifica"
      ],
      "high_score_threshold": 78
    },
    "portfolio_tier": "tier_0_core",
    "master_thesis": "WAOS debe poder vender WAOS sin verse como bot: conversa con colmillo, aguanta caos, entiende el momento emocional y siempre reconduce hacia valor comercial y siguiente paso.",
    "buyer": {
      "primary": [
        "founder",
        "closer",
        "sales lead",
        "agencia que vende WAOS",
        "equipo comercial interno"
      ],
      "secondary": [
        "operations lead",
        "customer success",
        "growth"
      ]
    },
    "one_pager": {
      "headline": "WAOS Bot",
      "thesis": "No vender un bot que contesta: vender una capa operativa y comercial sobre WhatsApp que entiende caos, responde con naturalidad y mueve a venta.",
      "problem": "Si el bot se queda seco, el prospecto asume que asi se quedaria en su negocio. Eso mata confianza y mata cierre.",
      "promise": "WAOS conecta, responde, reencuadra, vende y deja siempre un siguiente paso.",
      "monetizes": [
        "mas demos",
        "menos leads perdidos",
        "mejor seguimiento",
        "menos carga mental comercial",
        "mejor conversion de chat a oportunidad"
      ],
      "packaging": [
        "voz nativa WAOS",
        "playbook universal de continuidad",
        "seguimiento comercial",
        "takeover humano",
        "agenda demo / propuesta"
      ],
      "strategic_care": "Nunca venderlo como FAQ bonito ni juguete de IA. Debe sentirse como compa inteligente de negocio con estructura y criterio comercial."
    },
    "demo_flow": [
      "El prospecto llega con una duda, un chiste, una queja ligera o un cambio brusco de tema.",
      "WAOS conecta primero: valida, sigue el humor o acompana sin verse tonto.",
      "Luego reinterpreta lo que dijo en lenguaje de negocio: fuga, saturacion, seguimiento perdido, cierre lento o dependencia del celular.",
      "Explica con palabras simples por que WAOS ayudaria a responder mejor, seguir leads y vender mas por WhatsApp.",
      "Cierra con un movimiento: pregunta util, mini diagnostico, invitacion a demo, propuesta o takeover humano."
    ],
    "native_objects": {
      "core": [
        "lead",
        "dolor detectado",
        "objecion",
        "momento emocional",
        "siguiente paso"
      ],
      "commercial": [
        "demo",
        "diagnostico",
        "propuesta",
        "cierre",
        "reactivacion"
      ],
      "operations": [
        "takeover humano",
        "agenda demo",
        "followup programado",
        "handoff comercial"
      ]
    },
    "pipeline": {
      "primary": {
        "states": [
          "conexion",
          "diagnostico",
          "fit detectado",
          "demo agendada",
          "demo hecha",
          "propuesta",
          "instalacion"
        ],
        "entry": "conexion",
        "win": "instalacion"
      },
      "secondary": [
        "lead frio",
        "reactivacion",
        "seguimiento en objecion",
        "takeover humano"
      ]
    },
    "bot_playbook": {
      "must_do": [
        "nunca quedarse seco",
        "hablar simple y cero tecnico",
        "conectar antes de vender",
        "reencuadrar todo hacia un problema real del negocio",
        "cerrar cada respuesta con siguiente paso",
        "nunca quedarse seco ante bromas, preguntas raras o cambios bruscos de tema",
        "usar humor ligero cuando sume, sin sonar payaso ni poco serio",
        "validar el momento y luego reencauzar la conversacion al negocio",
        "cerrar siempre con una pregunta util o siguiente paso"
      ],
      "must_ask": [
        "que es lo que mas te esta drenando hoy",
        "donde sientes mas fuga ahorita",
        "se te cae mas la gente en respuesta, seguimiento o cierre",
        "quieres que te lo aterrice a tu caso",
        "que parte del negocio se esta atorando mas",
        "si quiere que se lo aterrice a su caso"
      ],
      "objections": [
        "ya tengo quien conteste",
        "no quiero sonar robotico",
        "mis clientes cambian mucho de tema",
        "solo preguntan y no compran",
        "no tengo tiempo para estar encima"
      ],
      "escalate_when": [
        "pide demo formal",
        "pide contrato",
        "precio enterprise",
        "requiere integracion especifica",
        "solicita revision humana"
      ],
      "forbidden": [
        "hablar como sistema",
        "decir no se a secas",
        "frases roboticas",
        "jerga de software",
        "inventar funciones o precios"
      ],
      "success_signals": [
        "el prospecto dice si te creo",
        "acepta mini diagnostico",
        "pide ejemplo",
        "acepta demo",
        "describe su caos operativo con detalle"
      ],
      "style": [
        "humor ligero",
        "manejo de preguntas raras",
        "reencuadre comercial"
      ]
    },
    "automation_sequences": [
      {
        "key": "waosbot_weird_question_reframe",
        "name": "Pregunta rara -> reencuadre",
        "trigger": "mensaje fuera de contexto o bromista",
        "goal": "mantener confianza y volver al negocio",
        "steps": [
          "conectar",
          "seguir el tono",
          "reencuadrar",
          "dejar pregunta util"
        ]
      },
      {
        "key": "waosbot_pain_followup",
        "name": "Seguimiento por dolor detectado",
        "trigger": "el prospecto expresa caos o saturacion y luego se enfria",
        "goal": "reactivar con empatía y valor",
        "steps": [
          "recordar dolor",
          "aterrizar fuga",
          "proponer demo o diagnostico"
        ]
      },
      {
        "key": "waosbot_post_demo",
        "name": "Post-demo",
        "trigger": "demo realizada",
        "goal": "mover a propuesta o instalacion",
        "steps": [
          "resumir hallazgos",
          "recordar valor",
          "proponer siguiente paso"
        ]
      },
      {
        "key": "waosbot_winback",
        "name": "Reactivacion de lead frio",
        "trigger": "lead sin respuesta por varios dias",
        "goal": "reabrir conversacion sin presion",
        "steps": [
          "entrada ligera",
          "recordar contexto",
          "pregunta corta de avance"
        ]
      }
    ],
    "dashboard": {
      "north_star": "conversaciones que terminan en demo, propuesta o instalacion",
      "sections": [
        "adquisicion",
        "diagnostico",
        "demos",
        "cierres",
        "reactivacion",
        "handoff humano"
      ]
    },
    "hardening_model": {
      "goal": "que WAOS venda WAOS con voz consistente y criterio comercial",
      "wave": "continuidad conversacional primero, luego precision comercial y por ultimo automatizacion fina",
      "entity_queen": "lead_conversacional",
      "core_common": [
        "voz",
        "continuidad",
        "empatía",
        "humor ligero",
        "reencuadre",
        "siguiente paso"
      ],
      "domain_by_vertical": true,
      "playbooks_by_subvertical": true,
      "kpis_by_vertical": true,
      "pricing_by_vertical": false,
      "journeys_by_vertical": true,
      "reusable_modules": [
        "voice core",
        "humor guardrails",
        "pain diagnosis",
        "next step engine"
      ],
      "minimum_viable_hardening": [
        "voz clara",
        "regla de continuidad",
        "regla comercial",
        "takeover humano"
      ],
      "hard_checklist": [
        "nunca se queda callado",
        "nunca suena tecnico",
        "nunca pierde contexto emocional",
        "siempre empuja valor comercial",
        "responde bromas con humor ligero y control",
        "tolera cambios bruscos de tema sin romper personaje",
        "no inventa funciones, precios ni politicas",
        "cierra siempre con siguiente paso",
        "reencuadra caos operativo como fuga comercial",
        "escala a humano cuando hay molestia real o tema sensible"
      ]
    },
    "specialist_layers": {
      "persistent_entities": [
        "dolor principal",
        "objecion dominante",
        "ultimo siguiente paso"
      ],
      "business_pipeline": [
        "conexion",
        "diagnostico",
        "demo",
        "propuesta",
        "instalacion"
      ],
      "pricing_and_quotes": [
        "propuesta guiada"
      ],
      "agenda_and_resources": [
        "agenda demo",
        "asignacion a humano"
      ],
      "post_sale_and_recurrence": [
        "reactivacion de leads frios",
        "seguimiento de propuesta"
      ],
      "documents_compliance": [
        "alcances comerciales",
        "promesas permitidas"
      ],
      "kpis_that_matter": [
        "lead to demo",
        "demo to propuesta",
        "reactivacion",
        "continuidad conversacional"
      ],
      "money_automations": [
        "recordatorio de propuesta",
        "seguimiento a cierre"
      ]
    },
    "domain_contract": {
      "vertical_entity_types": [
        "lead",
        "pain_signal",
        "objection",
        "demo",
        "proposal",
        "handoff_request"
      ],
      "vertical_pipeline_stages": {
        "conexion": [
          "respuesta_inicial",
          "humor_o_empatia"
        ],
        "diagnostico": [
          "dolor_detectado",
          "fuga_identificada"
        ],
        "conversion": [
          "demo_agendada",
          "demo_realizada",
          "propuesta_emitida"
        ],
        "cierre": [
          "instalacion",
          "reactivacion"
        ]
      },
      "vertical_quote_types": [
        "demo",
        "propuesta comercial"
      ],
      "vertical_resource_types": [
        "slot_demo",
        "asesor_humano"
      ],
      "vertical_followup_policies": [
        "seguimiento suave con valor",
        "evitar presion agresiva",
        "siempre con siguiente paso"
      ],
      "vertical_kpi_definitions": [
        "lead_to_demo",
        "demo_show_rate",
        "proposal_close_rate",
        "reactivation_rate",
        "conversation_continuity_rate"
      ],
      "vertical_playbooks": [
        "voz_waos",
        "pregunta_rara",
        "desahogo",
        "objecion_robotica",
        "reactivacion_lead_frio"
      ],
      "vertical_document_types": [
        "brief comercial",
        "propuesta",
        "alcance de instalacion"
      ]
    },
    "subvertical_playbooks": [
      {
        "name": "servicios locales",
        "focus": "captar leads y demo"
      },
      {
        "name": "salud y bienestar",
        "focus": "ordenar triage comercial y seguimiento"
      },
      {
        "name": "educacion",
        "focus": "reencuadrar dudas a admision y cierre"
      },
      {
        "name": "hogar y servicios",
        "focus": "bajar carga operativa y no perder chats"
      },
      {
        "name": "retail y ecommerce",
        "focus": "recuperar conversaciones y vender mejor por whatsapp"
      }
    ],
    "business_e2e_tests": [
      {
        "name": "prospecto bromea, WAOS conecta y reencuadra hacia demo",
        "status": "designed"
      },
      {
        "name": "prospecto se desahoga, WAOS acompana y convierte el dolor en mini diagnostico",
        "status": "designed"
      },
      {
        "name": "prospecto cambia de tema y WAOS regresa al negocio sin verse forzado",
        "status": "designed"
      }
    ],
    "vertical_runtime": {
      "pipeline_machine": {
        "states": [
          "conexion",
          "diagnostico",
          "fit detectado",
          "demo agendada",
          "demo hecha",
          "propuesta",
          "instalacion"
        ],
        "entry_state": "conexion",
        "win_state": "instalacion"
      },
      "pricing_engine": {
        "quote_types": [
          "diagnostico guiado",
          "propuesta de instalacion",
          "retainer mensual"
        ],
        "rules": [
          "nunca cotizar sin entender el caos del negocio",
          "aterrizar valor a seguimiento, conversion y carga operativa"
        ]
      },
      "resource_capacity": {
        "resource_types": [
          "slot de demo",
          "slot de diagnostico",
          "slot de takeover humano"
        ],
        "policies": [
          "priorizar leads con dolor operativo claro",
          "reservar takeover para objeciones sensibles o cierre"
        ]
      },
      "recurrence_engine": {
        "policies": [
          "seguimiento de lead frio",
          "reactivacion post demo",
          "winback de propuesta enfriada"
        ]
      },
      "kpi_engine": {
        "definitions": [
          "continuidad conversacional",
          "tasa de demo agendada",
          "propuesta a instalacion",
          "recuperacion de conversaciones frias"
        ]
      },
      "automation_engine": {
        "money_automation_policies": [
          "recordar demo",
          "reactivar propuesta",
          "detectar fuga por seguimiento caido"
        ]
      },
      "document_flow": {
        "required_documents": [
          "brief comercial",
          "propuesta",
          "alcance",
          "confirmacion de instalacion"
        ]
      },
      "matching_engine": {
        "rules": [
          "mandar takeover humano si hay molestia real",
          "mantener bot si la duda sigue en modo diagnostico comercial"
        ]
      }
    },
    "transactional_motor_v12": {
      "version": "12",
      "aggregate_root": "waosbot_growth_account",
      "main_business_entity": "lead_conversacional",
      "transaction_unit": "conversation_step",
      "system_of_record": "waos crm + whatsapp",
      "transaction_primitives": {
        "commands": [
          "capture_intent",
          "qualify_record",
          "confirm_booking",
          "propose_fee",
          "start_case",
          "close_case"
        ],
        "events": [
          "intent_captured",
          "lead_qualified",
          "demo_confirmed",
          "proposal_sent",
          "installation_won"
        ]
      },
      "aggregates": [
        "lead",
        "demo",
        "proposal",
        "handoff"
      ],
      "orchestration": [
        "voice_first",
        "reframe_everything",
        "always_leave_next_step"
      ],
      "finance": {
        "money_objects": [
          "propuesta",
          "anticipo",
          "retainer"
        ],
        "policies": [
          "no inventar precio",
          "no mandar fee sin diagnostico minimo"
        ]
      },
      "operations": {
        "resource_locking": [
          "slots de demo",
          "slots de takeover humano"
        ],
        "queues": [
          "demo scheduling",
          "human takeover"
        ]
      },
      "audit_compliance": {
        "consent_gates": [
          "consentimiento para seguimiento",
          "confirmacion antes de takeover humano"
        ],
        "guardrails": [
          "no fake claims",
          "no fake pricing",
          "no fake persona"
        ]
      },
      "transaction_views": {
        "commercial": "estado comercial por lead",
        "operations": "agenda y takeover",
        "finance": "propuestas emitidas",
        "continuity": "seguimientos y winback"
      },
      "command_catalog": [
        {
          "command": "capture_intent",
          "emits": "intent_captured",
          "guard": "solo si hubo mensaje entrante"
        },
        {
          "command": "qualify_record",
          "emits": "lead_qualified",
          "guard": "solo si se detecto dolor o fit"
        },
        {
          "command": "confirm_booking",
          "emits": "demo_confirmed",
          "guard": "solo si hay slot o acuerdo de horario"
        },
        {
          "command": "propose_fee",
          "emits": "proposal_sent",
          "guard": "solo despues de demo o diagnostico suficiente"
        },
        {
          "command": "close_case",
          "emits": "installation_won",
          "guard": "solo cuando el lead confirma siguiente fase"
        }
      ],
      "event_catalog": [
        "intent_captured",
        "lead_qualified",
        "demo_confirmed",
        "proposal_sent",
        "installation_won"
      ]
    },
    "subvertical_profiles": [],
    "recommended_subverticals": []
  }
] as unknown[];

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

function normalizeName(value: string | null | undefined) {
  return String(value || "").trim().toLowerCase();
}

const FALLBACK_VERTICALS = normalizeCollection(RAW_FALLBACK_VERTICALS, normalizeVerticalProfile);

export function getFallbackVerticalCatalog(topOnly = false): VerticalProfileContract[] {
  const base = FALLBACK_VERTICALS.map((item) => clone(item));
  if (!topOnly) return base;
  const strongest = base
    .filter((item) => item.is_strongest_vertical)
    .sort((a, b) => (a.strongest_rank || 999) - (b.strongest_rank || 999));
  return strongest.length ? strongest : base.slice(0, 5);
}

export function getFallbackVerticalProfile(vertical?: string, subvertical?: string): VerticalProfileContract {
  const key = normalizeName(vertical);
  const profile = getFallbackVerticalCatalog(false).find((item) => {
    return !key || [item.id, item.name, item.short_name].some((candidate) => normalizeName(candidate) === key);
  }) || getFallbackVerticalCatalog(false)[0];
  const selected = clone(profile);
  const subKey = normalizeName(subvertical);
  if (subKey) {
    const selectedSubvertical = selected.subvertical_profiles.find((item) => normalizeName(item.name) === subKey)
      || selected.selected_subvertical
      || selected.subvertical_profiles[0]
      || (selected.subverticals.find((item) => normalizeName(item) === subKey)
        ? { id: subvertical || "subvertical", name: subvertical || "Subvertical", templates: [], monetizes: [], service_bundle: [], qualification_questions: [], objections: [], automation_priorities: [], kpi_pack: [], recommended_commands: [], launch_assets: [] }
        : undefined);
    if (selectedSubvertical) selected.selected_subvertical = clone(selectedSubvertical as typeof selected.selected_subvertical);
  }
  return selected;
}
