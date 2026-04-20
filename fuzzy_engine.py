import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl
from skfuzzy.control.term import Term, TermAggregate
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

INFERENCE_MAMDANI = "mamdani"
INFERENCE_SUGENO = "sugeno"

# Zero-order Sugeno singletons (crisp consequent per output term).
_SUGENO_SINGLETONS = {
    "Vites_Kucult": 12.0,
    "Gazdan_Cek": 35.0,
    "Durumu_Koru": 55.0,
    "Vites_Buyut": 82.0,
}

def _build_rules(devir, gaz, egim, karar):
    """Shared Mamdani / zero-order Sugeno rule base (same IF–THEN structure)."""
    return [
        ctrl.Rule(
            devir["İdeal"] & gaz["Orta"] & egim["Duz"],
            karar["Durumu_Koru"],
            label="R01_flat_ideal_moderate",
        ),
        ctrl.Rule(
            devir["Yüksek"] & gaz["Orta"] & egim["Duz"],
            karar["Vites_Buyut"],
            label="R02_flat_high_moderate",
        ),
        ctrl.Rule(
            devir["Yüksek"] & gaz["Az"] & egim["Duz"],
            karar["Vites_Buyut"],
            label="R03_flat_high_light",
        ),
        ctrl.Rule(
            devir["İdeal"] & gaz["Az"] & egim["Duz"],
            karar["Durumu_Koru"],
            label="R04_flat_ideal_light",
        ),
        ctrl.Rule(
            devir["Düşük"] & gaz["Orta"] & egim["Duz"],
            karar["Vites_Kucult"],
            label="R05_flat_low_moderate",
        ),
        ctrl.Rule(
            devir["İdeal"] & gaz["Tam_Gaz"] & egim["Duz"],
            karar["Vites_Kucult"],
            label="R06_flat_ideal_full",
        ),
        ctrl.Rule(
            devir["Düşük"] & gaz["Tam_Gaz"] & egim["Duz"],
            karar["Vites_Kucult"],
            label="R07_flat_low_full",
        ),
        ctrl.Rule(
            devir["Düşük"] & egim["Yokus_Yukari"],
            karar["Vites_Kucult"],
            label="R08_uphill_low",
        ),
        ctrl.Rule(
            devir["İdeal"] & gaz["Tam_Gaz"] & egim["Yokus_Yukari"],
            karar["Vites_Kucult"],
            label="R09_uphill_ideal_full",
        ),
        ctrl.Rule(
            devir["İdeal"] & gaz["Orta"] & egim["Yokus_Yukari"],
            karar["Durumu_Koru"],
            label="R10_uphill_ideal_moderate",
        ),
        ctrl.Rule(
            devir["Yüksek"] & gaz["Tam_Gaz"] & egim["Yokus_Yukari"],
            karar["Durumu_Koru"],
            label="R11_uphill_high_full",
        ),
        ctrl.Rule(
            devir["Yüksek"] & gaz["Orta"] & egim["Yokus_Yukari"],
            karar["Durumu_Koru"],
            label="R12_uphill_high_moderate",
        ),
        ctrl.Rule(
            devir["İdeal"] & egim["Yokus_Asagi"],
            karar["Gazdan_Cek"],
            label="R13_downhill_ideal",
        ),
        ctrl.Rule(
            devir["Yüksek"] & gaz["Az"] & egim["Yokus_Asagi"],
            karar["Gazdan_Cek"],
            label="R14_downhill_high_light",
        ),
        ctrl.Rule(
            devir["Düşük"] & gaz["Az"] & egim["Yokus_Asagi"],
            karar["Durumu_Koru"],
            label="R15_downhill_low_light",
        ),
        ctrl.Rule(
            devir["Düşük"] & gaz["Orta"] & egim["Yokus_Asagi"],
            karar["Vites_Buyut"],
            label="R16_downhill_low_moderate",
        ),
    ]


class FuzzyEngine:
    def __init__(self, config, inference_mode=INFERENCE_MAMDANI):
        """
        Parametric fuzzy controller for one engine profile.

        inference_mode
        ----------------
        * ``mamdani`` — Mamdani inference, centroid defuzzification (scikit-fuzzy).
        * ``sugeno`` — Same rules; **zero-order Sugeno** crisp consequents with
          weighted-average aggregation (implemented here; portable across
          scikit-fuzzy versions that lack ``wtaver`` in ``defuzz()``).
        """
        mode = (inference_mode or INFERENCE_MAMDANI).lower()
        if mode not in (INFERENCE_MAMDANI, INFERENCE_SUGENO):
            raise ValueError(
                f"inference_mode must be '{INFERENCE_MAMDANI}' or '{INFERENCE_SUGENO}'"
            )
        self.inference_mode = mode
        self.config = config
        self.rpm_max = config["rpm_max"]
        self.ideal_min, self.ideal_max = config["ideal_range"]
        self.high_rev = config["high_rev"]
        self._build_engine()

    def _build_engine(self):
        devir = ctrl.Antecedent(np.arange(0, self.rpm_max + 1, 1), "devir")
        gaz = ctrl.Antecedent(np.arange(0, 101, 1), "gaz")
        egim = ctrl.Antecedent(np.arange(-20, 21, 1), "egim")
        karar = ctrl.Consequent(np.arange(0, 101, 1), "asistan_karari")
        karar.defuzzify_method = "centroid"

        devir["Düşük"] = fuzz.trimf(devir.universe, [0, 0, self.ideal_min + 100])
        ideal_mid = (self.ideal_min + self.ideal_max) / 2
        devir["İdeal"] = fuzz.trimf(
            devir.universe,
            [self.ideal_min - 200, ideal_mid, self.ideal_max + 200],
        )
        devir["Yüksek"] = fuzz.trapmf(
            devir.universe,
            [self.ideal_max, self.high_rev, self.rpm_max, self.rpm_max],
        )

        gaz["Az"] = fuzz.trimf(gaz.universe, [0, 0, 30])
        gaz["Orta"] = fuzz.trimf(gaz.universe, [20, 50, 80])
        gaz["Tam_Gaz"] = fuzz.trimf(gaz.universe, [70, 100, 100])

        egim["Yokus_Asagi"] = fuzz.trimf(egim.universe, [-20, -20, -5])
        egim["Duz"] = fuzz.trimf(egim.universe, [-10, 0, 10])
        egim["Yokus_Yukari"] = fuzz.trimf(egim.universe, [5, 20, 20])

        karar["Vites_Kucult"] = fuzz.trimf(karar.universe, [0, 0, 30])
        karar["Gazdan_Cek"] = fuzz.trimf(karar.universe, [20, 35, 50])
        karar["Durumu_Koru"] = fuzz.trimf(karar.universe, [40, 55, 70])
        karar["Vites_Buyut"] = fuzz.trimf(karar.universe, [60, 100, 100])

        rules = _build_rules(devir, gaz, egim, karar)
        self._rules_list = rules
        self._devir, self._gaz, self._egim = devir, gaz, egim
        self.karar_degiskeni = karar
        karar_ctrl = ctrl.ControlSystem(rules)
        self.sim = ctrl.ControlSystemSimulation(karar_ctrl, cache=True)

    def _crisp_inputs(self, devir_val, gaz_val, egim_val):
        return {
            "devir": float(devir_val),
            "gaz": float(gaz_val),
            "egim": float(egim_val),
        }

    def _antecedent_rows_from_inputs(self, inputs):
        rows = []
        for var in (self._devir, self._gaz, self._egim):
            x = inputs[var.label]
            for label in var.terms:
                mu = float(fuzz.interp_membership(var.universe, var[label].mf, x))
                rows.append({"variable": var.label, "term": label, "mu": mu})
        return sorted(rows, key=lambda r: (r["variable"], r["term"]))

    def _eval_antecedent_strength(self, node, inputs):
        if isinstance(node, Term):
            var = node.parent
            x = inputs[var.label]
            return float(fuzz.interp_membership(var.universe, var[node.label].mf, x))
        assert isinstance(node, TermAggregate)
        if node.kind == "not":
            return 1.0 - self._eval_antecedent_strength(node.term1, inputs)
        a = self._eval_antecedent_strength(node.term1, inputs)
        b = self._eval_antecedent_strength(node.term2, inputs)
        if node.kind == "and":
            return min(a, b)
        return max(a, b)

    def _evaluate_zero_order_sugeno(self, devir_val, gaz_val, egim_val, base):
        inputs = self._crisp_inputs(devir_val, gaz_val, egim_val)
        num = 0.0
        den = 0.0
        firings = []
        for rule in self._rules_list:
            w = self._eval_antecedent_strength(rule.antecedent, inputs)
            cons = rule.consequent[0].term
            key = cons.label
            s_val = _SUGENO_SINGLETONS[key]
            num += w * s_val
            den += w
            lbl = rule.label if isinstance(rule.label, str) else str(rule.label)
            firings.append(
                {
                    "label": lbl,
                    "strength": float(w),
                    "rule_if_then": str(rule).split("\n")[0],
                }
            )
        firings.sort(key=lambda r: -r["strength"])

        if den <= 1e-12:
            return {
                **base,
                "defuzz_method": "zero_order_sugeno",
                "skor": 50.0,
                "tavsiye": "DURUMU KORU",
                "success": False,
                "hata": "KeyError",
                "antecedent_mu": self._antecedent_rows_from_inputs(inputs),
                "rule_firings": firings,
            }

        skor = float(np.clip(num / den, 0.0, 100.0))
        uyelik_dereceleri = {
            "VİTES KÜÇÜLT": fuzz.interp_membership(
                self.karar_degiskeni.universe,
                self.karar_degiskeni["Vites_Kucult"].mf,
                skor,
            ),
            "GAZDAN ÇEK": fuzz.interp_membership(
                self.karar_degiskeni.universe,
                self.karar_degiskeni["Gazdan_Cek"].mf,
                skor,
            ),
            "DURUMU KORU": fuzz.interp_membership(
                self.karar_degiskeni.universe,
                self.karar_degiskeni["Durumu_Koru"].mf,
                skor,
            ),
            "VİTES BÜYÜT": fuzz.interp_membership(
                self.karar_degiskeni.universe,
                self.karar_degiskeni["Vites_Buyut"].mf,
                skor,
            ),
        }
        en_iyi_tavsiye = max(uyelik_dereceleri, key=uyelik_dereceleri.get)
        return {
            **base,
            "defuzz_method": "zero_order_sugeno",
            "skor": skor,
            "tavsiye": en_iyi_tavsiye,
            "success": True,
            "antecedent_mu": self._antecedent_rows_from_inputs(inputs),
            "rule_firings": firings,
        }

    def _antecedent_memberships(self):
        rows = []
        for var in self.sim.ctrl.antecedents:
            for term in var.terms.values():
                try:
                    mu = term.membership_value[self.sim]
                except KeyError:
                    continue
                if mu is None:
                    continue
                rows.append(
                    {
                        "variable": var.label,
                        "term": term.label,
                        "mu": float(np.asarray(mu).reshape(-1)[0]),
                    }
                )
        return sorted(rows, key=lambda r: (r["variable"], r["term"]))

    def _rule_firings(self):
        out = []
        for rule in self.sim.ctrl.rules:
            try:
                strength = rule.aggregate_firing[self.sim]
            except KeyError:
                continue
            if strength is None:
                continue
            s = float(np.asarray(strength).reshape(-1)[0])
            lbl = rule.label if isinstance(rule.label, str) else str(rule.label)
            out.append(
                {
                    "label": lbl,
                    "strength": s,
                    "rule_if_then": str(rule).split("\n")[0],
                }
            )
        out.sort(key=lambda r: -r["strength"])
        return out

    def evaluate(self, devir_val, gaz_val, egim_val):
        base = {
            "inference": self.inference_mode,
            "defuzz_method": self.karar_degiskeni.defuzzify_method,
        }

        if self.inference_mode == INFERENCE_SUGENO:
            return self._evaluate_zero_order_sugeno(devir_val, gaz_val, egim_val, base)

        self.sim.input["devir"] = devir_val
        self.sim.input["gaz"] = gaz_val
        self.sim.input["egim"] = egim_val

        try:
            self.sim.compute()
            skor = self.sim.output["asistan_karari"]
            uyelik_dereceleri = {
                "VİTES KÜÇÜLT": fuzz.interp_membership(
                    self.karar_degiskeni.universe,
                    self.karar_degiskeni["Vites_Kucult"].mf,
                    skor,
                ),
                "GAZDAN ÇEK": fuzz.interp_membership(
                    self.karar_degiskeni.universe,
                    self.karar_degiskeni["Gazdan_Cek"].mf,
                    skor,
                ),
                "DURUMU KORU": fuzz.interp_membership(
                    self.karar_degiskeni.universe,
                    self.karar_degiskeni["Durumu_Koru"].mf,
                    skor,
                ),
                "VİTES BÜYÜT": fuzz.interp_membership(
                    self.karar_degiskeni.universe,
                    self.karar_degiskeni["Vites_Buyut"].mf,
                    skor,
                ),
            }
            en_iyi_tavsiye = max(uyelik_dereceleri, key=uyelik_dereceleri.get)
            return {
                **base,
                "skor": skor,
                "tavsiye": en_iyi_tavsiye,
                "success": True,
                "antecedent_mu": self._antecedent_memberships(),
                "rule_firings": self._rule_firings(),
            }
        except KeyError:
            return {
                **base,
                "skor": 50.0,
                "tavsiye": "DURUMU KORU",
                "success": False,
                "hata": "KeyError",
                "antecedent_mu": [],
                "rule_firings": [],
            }
        except ValueError:
            return {
                **base,
                "skor": 50.0,
                "tavsiye": "DURUMU KORU",
                "success": False,
                "hata": "ValueError",
                "antecedent_mu": [],
                "rule_firings": [],
            }

    def plot_result(self, skor):
        plt.close("all")
        fig, ax = plt.subplots(figsize=(10, 3.5))
        x_karar = self.karar_degiskeni.universe

        ax.plot(x_karar, self.karar_degiskeni["Vites_Kucult"].mf, "b", label="Vites Küçült")
        ax.plot(x_karar, self.karar_degiskeni["Gazdan_Cek"].mf, "g", label="Gazdan Çek")
        ax.plot(x_karar, self.karar_degiskeni["Durumu_Koru"].mf, "y", label="Durumu Koru")
        ax.plot(x_karar, self.karar_degiskeni["Vites_Buyut"].mf, "r", label="Vites Büyüt")

        ax.axvline(x=skor, color="k", linestyle="--", linewidth=3, label=f"Skor: {skor:.1f}")
        ax.set_xlabel("Karar Skoru")
        ax.set_ylabel("Üyelik Derecesi")
        ax.legend()
        ax.grid(True, alpha=0.3)
        return fig
