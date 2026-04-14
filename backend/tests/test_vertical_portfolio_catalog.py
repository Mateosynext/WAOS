from backend.app.ai import generate_response, heuristic_generate
from backend.app.defaults import default_bot_config
from backend.app.verticals import build_vertical_bot_setup, get_vertical_profile, list_vertical_profiles


def test_vertical_catalog_has_complete_portfolio_sections() -> None:
    profiles = list_vertical_profiles()
    assert len(profiles) >= 11
    for profile in profiles:
        assert profile["one_pager"]["headline"]
        assert profile["master_thesis"]
        assert profile["buyer"]["primary"]
        assert len(profile["demo_flow"]) >= 5
        assert profile["native_objects"]["core"]
        assert profile["pipeline"]["primary"]["states"]
        assert profile["bot_playbook"]["must_do"]
        assert profile["automation_sequences"]
        assert profile["dashboard"]["sections"]
        assert profile["hardening_model"]["entity_queen"]
        assert len(profile["hardening_model"]["hard_checklist"]) >= 10
        assert profile["specialist_layers"]["pricing_and_quotes"]
        assert profile["domain_contract"]["vertical_quote_types"]
        assert profile["vertical_runtime"]["pipeline_machine"]["states"]
        assert profile["vertical_runtime"]["pricing_engine"]["rules"]
        assert profile["vertical_runtime"]["resource_capacity"]["resource_types"]
        assert profile["vertical_runtime"]["recurrence_engine"]["policies"]
        assert profile["vertical_runtime"]["kpi_engine"]["definitions"]
        assert profile["vertical_runtime"]["automation_engine"]["money_automation_policies"]
        assert profile["vertical_runtime"]["document_flow"]["required_documents"]
        assert profile["vertical_runtime"]["matching_engine"]["rules"]
        assert profile["transactional_motor_v12"]["aggregate_root"]
        assert profile["transactional_motor_v12"]["transaction_primitives"]["commands"]
        assert profile["transactional_motor_v12"]["finance"]["money_objects"]
        assert profile["transactional_motor_v12"]["operations"]["resource_locking"]
        assert profile["transactional_motor_v12"]["audit_compliance"]["consent_gates"]
        assert profile["transactional_motor_v12"]["command_catalog"]
        assert profile["transactional_motor_v12"]["event_catalog"]
        assert len(profile["subvertical_playbooks"]) >= 5
        assert len(profile["business_e2e_tests"]) >= 2


def test_build_vertical_bot_setup_exposes_portfolio_context() -> None:
    setup = build_vertical_bot_setup(
        "dental",
        business_name="Clínica Demo",
        bot_name="WAOS Dental",
        tone="claro",
        language="es",
        timezone="America/Mexico_City",
        primary_objective="cerrar_valoraciones",
        services=None,
        faqs=None,
        hours="L-V 9:00-18:00",
        whatsapp_number="+520000000000",
    )
    context = setup["vertical_context"]
    assert context["id"] == "dental"
    assert context["portfolio_tier"] == "tier_1"
    assert context["one_pager"]["headline"] == "WAOS Dental"
    assert context["pipeline"]["primary"]["states"]
    assert context["hardening_model"]["entity_queen"] == "caso clínico dental"
    assert context["specialist_layers"]["documents_compliance"]
    assert context["domain_contract"]["vertical_document_types"]
    assert context["vertical_runtime"]["pricing_engine"]["quote_types"]
    assert context["vertical_runtime"]["matching_engine"]["rules"]
    assert context["transactional_motor_v12"]["aggregate_root"] == "dental_case_account"
    assert context["transactional_motor_v12"]["finance"]["money_objects"]
    assert setup["rules"]["must_ask"]
    assert setup["rules"]["objection_handling"]
    assert setup["rules"]["success_signals"]
    assert setup["personality"]["tone_of_voice_understanding"] is True
    assert setup["v7_modules"]["multilingual"]["supported_languages"] == ["es", "en"]
    assert setup["v7_modules"]["voice"]["context_from_vox"] is True


def test_commerce_is_guarded_tier() -> None:
    profile = get_vertical_profile("commerce")
    assert profile["portfolio_tier"] == "tier_3_guarded"
    assert "e-commerce" in profile["one_pager"]["strategic_care"] or "retail conversacional" in profile["one_pager"]["strategic_care"]


def test_all_verticals_get_global_humor_and_rare_question_defaults() -> None:
    for profile in list_vertical_profiles():
        behavior = profile["behavior"]
        playbook = profile["bot_playbook"]
        assert behavior["humor_policy"] == "light_contextual"
        assert behavior["strange_question_policy"] == "respond_validate_reframe_sell_move"
        assert "te sigo" in behavior["required_phrases"]
        assert "pregunta viene rara" in behavior["fallback_message"].lower()
        assert any("preguntas raras" in item for item in playbook["must_do"])


def test_default_bot_config_seeds_global_conversation_guards() -> None:
    config = default_bot_config(
        business_name="Demo",
        vertical="dental",
        bot_name="WAOS Demo",
        primary_objective="agendar",
        tone="claro",
        language="es",
        timezone="America/Mexico_City",
    )
    assert config["personality"]["humor_policy"] == "light_contextual"
    assert config["personality"]["strange_question_policy"] == "respond_validate_reframe_sell_move"
    assert config["personality"]["tone_of_voice_understanding"] is True
    assert config["v7_modules"]["multilingual"]["supported_languages"] == ["es", "en"]
    assert config["v7_modules"]["multilingual"]["reply_in_detected_language"] is True
    assert config["v7_modules"]["voice"]["tone_of_voice_detection"] is True
    assert config["v7_modules"]["voice"]["context_from_vox"] is True
    assert "nunca quedarse seco" in config["rules"]["conversation_guards"]


def test_heuristic_generate_handles_weird_questions_with_reframe() -> None:
    config = default_bot_config(
        business_name="Demo",
        vertical="dental",
        bot_name="WAOS Demo",
        primary_objective="agendar",
        tone="claro",
        language="es",
        timezone="America/Mexico_City",
    )
    message = heuristic_generate(
        "y tambien me lava los trastes o que jaja",
        {"intent": "general", "objection": ""},
        config,
        {},
    )
    lowered = message.lower()
    assert "te sigo" in lowered
    assert "waos" in lowered
    assert "seguimiento" in lowered or "respuestas" in lowered


def test_heuristic_generate_replies_in_english_when_contact_is_english() -> None:
    config = default_bot_config(
        business_name="Demo",
        vertical="dental",
        bot_name="WAOS Demo",
        primary_objective="book",
        tone="clear",
        language="es",
        timezone="America/Mexico_City",
    )
    message = heuristic_generate(
        "haha can you also follow up with clients at 3 am or what?",
        {"intent": "general", "objection": ""},
        config,
        {},
    )
    lowered = message.lower()
    assert "i got you" in lowered or "haha" in lowered
    assert "waos" in lowered
    assert "follow-up" in lowered or "replies" in lowered or "closing" in lowered


def test_default_bot_config_seeds_native_voice_matrix() -> None:
    config = default_bot_config(
        business_name="Demo",
        vertical="dental",
        bot_name="WAOS Demo",
        primary_objective="agendar",
        tone="claro",
        language="es",
        timezone="America/Mexico_City",
    )
    assert config["personality"]["native_voice_by_language"] is True
    assert config["personality"]["tone_matrix_by_language"] is True
    assert config["v7_modules"]["multilingual"]["native_voice_by_language"] is True
    assert config["v7_modules"]["multilingual"]["tone_matrix_by_language"] is True
    assert config["v7_modules"]["voice"]["vox_context_priority"] == ["summary", "detected_language", "intent", "urgency_level", "emotion"]


def test_generate_response_exposes_language_voice_layer_and_vox_context() -> None:
    config = default_bot_config(
        business_name="Demo",
        vertical="dental",
        bot_name="WAOS Demo",
        primary_objective="book",
        tone="clear",
        language="es",
        timezone="America/Mexico_City",
    )
    response, payload = generate_response(
        "hey, honestly I'm swamped and need help with follow-up",
        {"intent": "general", "objection": "", "requested_human": False},
        config,
        {},
        recent_messages=[{"direction": "inbound", "body": "hey there"}],
        recent_voice_notes=[{"summary": "customer sounds stressed and wants faster follow-up", "detected_language": "en", "intent": "follow_up", "urgency_level": "high", "emotion": "negative"}],
        language_config={
            "default_language": "es",
            "supported_languages": ["es", "en"],
            "templates": {
                "es": {"voice_profile": {"persona": "cercano"}, "tone_matrix": {"casual": {"ack": "va", "bridge": "te lo aterrizo fácil", "close": "si quieres, lo vemos a tu caso"}}},
                "en": {"voice_profile": {"persona": "native and sharp"}, "tone_matrix": {"overwhelmed": {"ack": "I get you", "bridge": "when everything piles up, that is where time and sales start leaking", "close": "what is draining you the most right now?"}}},
            },
        },
    )
    assert payload["language_context"]["detected_language"] == "en"
    assert payload["language_voice_layer"]["voice_profile"]["persona"] == "native and sharp"
    assert payload["recent_voice_context"][0]["summary"] == "customer sounds stressed and wants faster follow-up"
    assert "I get you" in response
