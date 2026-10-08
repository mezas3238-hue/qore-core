"""Tests for immutable pre-entry-only ATTACK adverse partial opt-in."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from cibo_trader_lab_three_mode_ceiling import _causal_partial_features
from qore.infrastructure.cibo_position_lifecycle import CiboLifecycleFeature


class PreentryPartialGateTests(unittest.TestCase):
    def setUp(self):
        self.partial=CiboLifecycleFeature.ADVERSE_PARTIAL_REDUCTION
        self.stop=CiboLifecycleFeature.DEFENSIVE_INITIAL_STOP_CAP
        self.full=frozenset({self.stop,self.partial})

    def test_no_context_gate_preserves_original_feature_set(self):
        selected,active=_causal_partial_features(self.full,{},())
        self.assertTrue(active)
        self.assertEqual(selected,self.full)

    def test_matching_preentry_geometry_keeps_partial(self):
        selected,active=_causal_partial_features(
            self.full, {"reg_m5_volatility_state":"compressed"},
            (("reg_m5_volatility_state","compressed"),))
        self.assertTrue(active)
        self.assertIn(self.partial,selected)

    def test_nonmatching_preentry_geometry_disables_only_partial(self):
        selected,active=_causal_partial_features(
            self.full, {"reg_m5_volatility_state":"expanded"},
            (("reg_m5_volatility_state","compressed"),))
        self.assertFalse(active)
        self.assertNotIn(self.partial,selected)
        self.assertIn(self.stop,selected)

    def test_missing_field_fails_closed_for_partial(self):
        selected,active=_causal_partial_features(
            self.full,{},(("ctx_source_range_state_bucket","q4:<=2.0"),))
        self.assertFalse(active)
        self.assertEqual(selected,frozenset({self.stop}))

    def test_multiple_conditions_require_all_matches(self):
        selected,active=_causal_partial_features(
            self.full, {"reg_m5_volatility_state":"compressed",
                         "reg_h1_body_alignment":"flat"},
            (("reg_m5_volatility_state","compressed"),
             ("reg_h1_body_alignment","flat")))
        self.assertTrue(active)
        self.assertEqual(selected,self.full)
        selected,active=_causal_partial_features(
            self.full, {"reg_m5_volatility_state":"compressed",
                         "reg_h1_body_alignment":"with"},
            (("reg_m5_volatility_state","compressed"),
             ("reg_h1_body_alignment","flat")))
        self.assertFalse(active)
        self.assertEqual(selected,frozenset({self.stop}))

    def test_feature_absent_does_not_auto_enable_it(self):
        selected,active=_causal_partial_features(
            frozenset({self.stop}),{"reg_m5_volatility_state":"compressed"},
            (("reg_m5_volatility_state","compressed"),))
        self.assertTrue(active)
        self.assertEqual(selected,frozenset({self.stop}))


if __name__=="__main__":
    unittest.main()
