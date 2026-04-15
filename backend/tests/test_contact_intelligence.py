from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("ALLOW_SQLITE_FOR_TESTS", "true")

from backend.app.ai import update_memory
from backend.app.application.conversation_service import ConversationService
from backend.app.backend_runtime import ensure_backend_runtime_schema
from backend.app.contact_intelligence import enrich_conversation_row
from backend.app.db import SCHEMA_PATH
from backend.app.domains.schema_setup import ensure_v9_schema
from backend.app.repositories.contacts import upsert_contact, upsert_memory
from backend.app.utils import utcnow_iso


class ContactIntelligenceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
        self.conn = sqlite3.connect(self.tmp.name)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(Path(SCHEMA_PATH).read_text())
        ensure_v9_schema(self.conn)
        ensure_backend_runtime_schema(self.conn)
        now = utcnow_iso()
        self.conn.execute("INSERT INTO users (id, email, full_name, password_hash, global_role, is_active, created_at, updated_at) VALUES ('usr_1', 'qa@example.com', 'QA', 'hash', 'super_admin', 1, ?, ?)", (now, now))
        self.conn.execute("INSERT INTO organizations (id, name, slug, status, timezone, vertical, settings_json, created_at, updated_at) VALUES ('org_1', 'Org', 'org', 'active', 'America/Mexico_City', 'services', '{}', ?, ?)", (now, now))
        self.conn.execute("INSERT INTO bots (id, organization_id, name, business_name, vertical, language, timezone, status, ai_paused, current_state, config_draft_json, created_at, updated_at) VALUES ('bot_1', 'org_1', 'Bot', 'Org', 'services', 'es', 'America/Mexico_City', 'active', 0, 'published', '{}', ?, ?)", (now, now))
        self.contact = upsert_contact(self.conn, organization_id='org_1', phone='+525511111111', name='Clau')
        self.memory = upsert_memory(self.conn, organization_id='org_1', contact_id=self.contact['id'], bot_id='bot_1')
        self.conversation_id = 'conv_1'
        self.conn.execute("INSERT INTO conversations (id, organization_id, bot_id, contact_id, status, human_takeover, ai_active, paused_until, automation_freeze_until, last_message_at, last_human_at, last_ai_at, assigned_user_id, created_at, updated_at) VALUES (?, 'org_1', 'bot_1', ?, 'ai_active', 0, 1, NULL, NULL, ?, NULL, NULL, NULL, ?, ?)", (self.conversation_id, self.contact['id'], now, now, now))
        self.conn.commit()

    def tearDown(self):
        self.conn.close()
        Path(self.tmp.name).unlink(missing_ok=True)

    def test_update_memory_builds_known_personal_profile_and_urgency(self):
        updated = update_memory(
            self.conn,
            organization_id='org_1',
            contact_id=self.contact['id'],
            bot_id='bot_1',
            incoming_text='Hola, soy tu prima y es una emergencia del hospital, háblame ya mismo.',
            classification={
                'intent': 'general',
                'lead_stage': 'contacted',
                'objection': '',
                'score_delta': 0,
                'requested_human': False,
                'interest': None,
            },
            contact=self.contact,
            recent_messages=[{'direction': 'inbound', 'body': 'Necesito ayuda'}],
        )
        payload = json.loads(updated['memory_json'])
        profile = payload['relationship_intelligence']
        self.assertTrue(profile['known_contact'])
        self.assertEqual(profile['relation_key'], 'family')
        self.assertIn(profile['urgency_level'], {'high', 'critical'})
        self.assertIn(updated['next_action'], {'owner_attention', 'priority_followup'})

    def test_update_memory_builds_sales_mode_for_customer_requests(self):
        updated = update_memory(
            self.conn,
            organization_id='org_1',
            contact_id=self.contact['id'],
            bot_id='bot_1',
            incoming_text='Quiero cotizar y agendar una cita para mañana.',
            classification={
                'intent': 'schedule',
                'lead_stage': 'qualified',
                'objection': '',
                'score_delta': 25,
                'requested_human': False,
                'interest': 'consulta',
            },
            contact=self.contact,
            recent_messages=[{'direction': 'inbound', 'body': 'Quiero cotizar y agendar una cita para mañana.'}],
        )
        payload = json.loads(updated['memory_json'])
        profile = payload['relationship_intelligence']
        self.assertEqual(profile['current_mode'], 'sales')
        self.assertEqual(profile['current_intent'], 'schedule')
        self.assertEqual(profile['relation_key'], 'customer')
        self.assertIn('schedule', profile['top_topics'])

    def test_conversation_service_list_exposes_relationship_and_urgency(self):
        updated = update_memory(
            self.conn,
            organization_id='org_1',
            contact_id=self.contact['id'],
            bot_id='bot_1',
            incoming_text='Hola, soy tu primo y es urgente, márcame ya.',
            classification={
                'intent': 'general',
                'lead_stage': 'contacted',
                'objection': '',
                'score_delta': 0,
                'requested_human': False,
                'interest': None,
            },
            contact=self.contact,
            recent_messages=[{'direction': 'inbound', 'body': 'márcame ya'}],
        )
        row = {
            'id': self.conversation_id,
            'contact_name': self.contact['name'],
            'contact_phone': self.contact['phone'],
            'status': 'ai_active',
            'lead_score': updated['lead_score'],
            'lead_stage': updated['lead_stage'],
            'summary': updated['summary'],
            'memory_json': updated['memory_json'],
        }
        enriched = enrich_conversation_row(row)
        self.assertEqual(enriched['relationship_label'], 'familia')
        self.assertTrue(enriched['known_contact'])
        self.assertIn(enriched['urgency_level'], {'high', 'critical'})


if __name__ == '__main__':
    unittest.main()
