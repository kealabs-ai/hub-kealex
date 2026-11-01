import unittest
from types import SimpleNamespace

from app.application.use_cases.phase_queries import build_next_phases


class PhaseQueryTests(unittest.TestCase):
    def test_returns_only_phases_after_the_current_phase(self):
        phases = [
            SimpleNamespace(label="Protocolo", status="concluida"),
            SimpleNamespace(label="Citacao", status="ativa"),
            SimpleNamespace(label="Audiencia", status="futura"),
        ]

        result = build_next_phases(phases, 1)

        self.assertEqual(result["faseAtual"], 1)
        self.assertEqual(result["faseAtualLabel"], "Citacao")
        self.assertEqual(result["proximasFases"], [{"ordem": 2, "label": "Audiencia", "status": "futura"}])
