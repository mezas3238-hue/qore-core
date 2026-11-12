"""Source-pinned Pine R4-A -> strategy R1 static QA. NOT TradingView compile."""
from __future__ import annotations

import hashlib
import re
import unittest
from pathlib import Path

PINE = (
    Path(__file__).resolve().parents[1] / "pine"
    / "QORE_CRT_TRADER_R1_V34_12X_ORIGINAL_ENGINE_QA.pine"
)
ORIGINAL_PIN = "693e3f49719e86e2ea0702f7b355af33bd0c4c7c"
ENGINE_GIT_BLOB = "777fa066e7aea2274d236750d6475979b05042ce"
EXPECTED_34 = (
    "AUDJPY", "GBPUSD", "GBPJPY", "XAUUSD", "USTEC", "US500", "US30",
    "BTCUSD", "AUDUSD", "USDCAD", "USDJPY", "EURUSD", "USDCHF",
    "NZDUSD", "NZDJPY", "NZDCHF", "XAGUSD", "AUDCAD", "AUDCHF",
    "AUDNZD", "CADCHF", "CADJPY", "CHFJPY", "EURAUD", "EURCAD",
    "EURCHF", "EURGBP", "EURJPY", "EURNZD", "GBPAUD", "GBPCAD",
    "GBPCHF", "GBPNZD", "NZDCAD",
)


def git_sha1_blob(contents: str) -> str:
    payload = contents.encode("utf-8")
    return hashlib.sha1(
        b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload,
    ).hexdigest()


def source() -> str:
    return PINE.read_text(encoding="utf-8")


def restore_pinned_detector(text: str) -> str:
    """Restore ONLY 2 snapshot-last guards to prove untouched source logic."""
    begin = text.index("f_engine() =>")
    end = text.index("\n// ==================", begin)
    engine = text[begin:end].rstrip()
    original_vis = (
        "FamilyVisual outFamilyVisual = barstate.islast ? "
        "FamilyVisual.new(familyC1At, familyC1Hi, familyC1Lo, "
        "familyEventAt, familyDir, familyVisualKind, familyHasOwnC1) : na"
    )
    extended_vis = (
        "FamilyVisual outFamilyVisual = "
        "FamilyVisual.new(familyC1At, familyC1Hi, familyC1Lo, "
        "familyEventAt, familyDir, familyVisualKind, familyHasOwnC1)"
    )
    if engine.count(extended_vis) != 1 or engine.count("\n    Signal.new(") != 1:
        raise ValueError("source engine was not translated in exactly 2 places")
    engine = engine.replace(extended_vis, original_vis)
    engine = engine.replace("\n    Signal.new(", "\n    barstate.islast ? Signal.new(")
    return engine + " : na\n"


class PineR1SourceQA(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.script = source()
        cls.active = "\n".join(
            line for line in cls.script.splitlines()
            if not line.lstrip().startswith("//")
        )
        cls.adapter = cls.script.split(
            "// QORE CRT TRADER R1 - SIMULACION DEL INDICADOR ORIGINAL POR GRAFICO"
        )[-1]

    def test_01_source_blob_pin_exact_detector_core(self) -> None:
        self.assertIn(ORIGINAL_PIN, self.script)
        self.assertEqual(
            git_sha1_blob(restore_pinned_detector(self.script)),
            ENGINE_GIT_BLOB,
        )

    def test_02_strategy_not_an_indicator_or_broker(self) -> None:
        self.assertTrue(self.script.startswith("//@version=6"))
        self.assertEqual(self.active.count('strategy("QORE CRT TRADER R1'), 1)
        self.assertFalse(re.search(r"^indicator\s*\(", self.active, re.M))
        self.assertNotIn("request.security(", self.active)
        self.assertNotIn("alert(", self.active)
        self.assertNotIn("alertcondition(", self.active)

    def test_03_34_fixed_ic_markets_exactly_no_substitutes(self) -> None:
        catalog = re.search(
            r"var array<string> qoreUniverse = array.from\(([^\n]+)\)",
            self.script,
        )
        self.assertIsNotNone(catalog)
        assert catalog is not None
        actual = re.findall(r'"IC:([A-Z0-9]+)"', catalog.group(1))
        self.assertEqual(tuple(actual), EXPECTED_34)
        self.assertEqual(len(set(actual)), 34)
        self.assertNotIn("COINBASE:", catalog.group(1))
        self.assertNotIn("OANDA:", catalog.group(1))

    def test_04_one_symbol_chart_only_no_34_security_scan(self) -> None:
        for marker in (
            "Signal tr = f_engine()",
            "chart.is_standard",
            "trIsM5",
            "ticker.standard(syminfo.tickerid)",
            'str.upper(syminfo.prefix) == "IC"',
            "array.includes(qoreUniverse, trTicker)",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.adapter)

    def test_05_no_repainting_shortcuts_or_intrabar_fills(self) -> None:
        declaration = self.script.split("\n", 15)[7]
        # Use whole declaration line in case future header comments change.
        match = re.search(r'^strategy\("QORE CRT TRADER R1[^\n]+', self.script, re.M)
        self.assertIsNotNone(match)
        assert match is not None
        decl = match.group(0)
        for flag in (
            "process_orders_on_close=false",
            "calc_on_order_fills=false",
            "calc_on_every_tick=false",
            "pyramiding=0",
        ):
            self.assertIn(flag, decl)
        self.assertIn("barstate.isconfirmed", self.adapter)
        self.assertIn("int trEndClosed = time_close[1]", self.adapter)
        self.assertNotIn("lookahead=barmerge.lookahead_on", self.active)
        self.assertNotIn("barstate.islast ? Signal.new(", self.script)

    def test_06_seven_explicit_gate_paths(self) -> None:
        for j in range(1, 8):
            self.assertRegex(self.adapter, rf"bool trF{j} = ")
        self.assertIn("trExtraM5Own", self.adapter)
        self.assertIn("trExtraM15Own", self.adapter)
        self.assertIn('tr.retest15State == "RETEST M15 QA"', self.adapter)
        self.assertIn("tr.entryConfirmedAt", self.adapter)
        self.assertIn("tr.extraFamilyM15C1 == tr.extraFamilyC1", self.adapter)
        self.assertIn("tr.extraFamilyM5C1 == tr.extraFamilyC1", self.adapter)

    def test_07_no_provisional_or_rejected_catalog_as_orders(self) -> None:
        trader_part = self.script.split(
            "// Guardas estrictas: catalogMask 2/4/16"
        )[-1]
        self.assertIn('tr.modelKind == "CRT_2C_RETURN"', self.adapter)
        self.assertIn('tr.phase == 2', self.adapter)
        self.assertIn('tr.entryStage == "M15 CONFIRMADO"', trader_part)
        self.assertNotIn("tr.phase == 1", trader_part)
        self.assertNotIn('tr.entryFamily == "CRT EXPANSION"', trader_part)

    def test_08_only_disabled_by_default_hypothetical_orders(self) -> None:
        self.assertIn('input.bool(false, "Habilitar SOLO ordenes simuladas"', self.adapter)
        self.assertIn('strategy.entry("QORE-L", strategy.long', self.adapter)
        self.assertIn('strategy.entry("QORE-S", strategy.short', self.adapter)
        self.assertIn('strategy.exit("QORE-LX", from_entry="QORE-L"', self.adapter)
        self.assertIn('strategy.exit("QORE-SX", from_entry="QORE-S"', self.adapter)
        self.assertNotIn("strategy.order(", self.active)
        self.assertNotIn("strategy.close_all(", self.active)

    def test_09_no_unbounded_costless_profit_authorization(self) -> None:
        for marker in (
            "trMinRR",
            "trMaxRiskPercent",
            "risk / close * 100 <= trMaxRiskPercent",
            "reward / risk >= trMinRR",
            "stopPx > 0",
            "targetPx > 0",
            "commission_type=strategy.commission.percent",
            "slippage=2",
        ):
            self.assertIn(marker, self.script)
        self.assertIn("PINE COMPILACION Y PARIDAD PENDIENTES", self.adapter)
        self.assertIn("NO LIVE", self.script)

    def test_10_no_double_count_for_same_family_cycle(self) -> None:
        self.assertIn("var array<string> trSeen = array.new_string(7", self.adapter)
        self.assertIn('array.get(trSeen, j) != eventKey', self.adapter)
        self.assertIn('if trCountNow > 1', self.adapter)
        self.assertIn('bool trIsFlat', self.adapter)
        self.assertIn('else if trCountNow == 1 and trIsFlat', self.adapter)

    def test_11_nonstandard_charts_blocked(self) -> None:
        self.assertIn("trIsM5 and chart.is_standard", self.adapter)
        self.assertIn("BLOQUEADO: grafico no estandar", self.adapter)

    def test_12_not_misrepresenting_engine_qa_as_certified(self) -> None:
        self.assertIn("Las siete familias son hipotesis", self.script)
        self.assertIn("NO CERTIFICADO", self.script)
        self.assertIn("NO LIVE", self.script)


if __name__ == "__main__":
    unittest.main(verbosity=2)
