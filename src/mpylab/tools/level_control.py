# -*- coding: utf-8 -*-
"""This is :mod:`mpylab.tools.level_control`.

   Provides different classes for level control

   :author: Hans Georg Krauthäuser (main author)

   :license: GPL-3 or higher
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional, Sequence, Tuple, Union

import numpy as np
from numpy.polynomial import Polynomial
from scipy.interpolate import interp1d
from scipy.optimize import fsolve, leastsq


Number = Union[float, int]


@dataclass
class ControlResult:
    guess: float
    actual: float
    iterations: int
    evaluations: int


class ControlBase:
    """
    Basisklasse für iterative inverse Regel-/Abgleichverfahren.

    Prinzip:
    - setter(cntrl) setzt den Stellwert
    - reader() liest den Istwert
    - aus gemessenen (cntrl, actual)-Paaren wird ein neuer Stellwert geschätzt
    """

    def __init__(
        self,
        actual_reader: Callable[[], Number],
        setter: Callable[[float], object],
        initial: Sequence[Number],
        abstol: Number,
        max_iter: int = 20,
        min_cntrl: Optional[Number] = None,
        max_cntrl: Optional[Number] = None,
        stagnation_tol: float = 1e-12,
    ):
        if not callable(actual_reader):
            raise TypeError("actual_reader must be callable")
        if not callable(setter):
            raise TypeError("setter must be callable")
        if initial is None or len(initial) < 2:
            raise ValueError("initial must contain at least two control values")
        if abstol <= 0:
            raise ValueError("abstol must be > 0")
        if max_iter <= 0:
            raise ValueError("max_iter must be > 0")
        if min_cntrl is not None and max_cntrl is not None and min_cntrl > max_cntrl:
            raise ValueError("min_cntrl must be <= max_cntrl")

        self.reader = actual_reader
        self.setter = setter
        self.initial = [float(x) for x in initial]
        self.abstol = float(abstol)
        self.max_iter = int(max_iter)
        self.min_cntrl = None if min_cntrl is None else float(min_cntrl)
        self.max_cntrl = None if max_cntrl is None else float(max_cntrl)
        self.stagnation_tol = float(stagnation_tol)

        self.N = 0  # Anzahl der reader()-Aufrufe

    def clamp_cntrl(self, cntrl: Number) -> float:
        value = float(cntrl)
        if self.min_cntrl is not None:
            value = max(value, self.min_cntrl)
        if self.max_cntrl is not None:
            value = min(value, self.max_cntrl)
        return value

    def set_cntrl_val(self, cntrl: Number) -> float:
        cntrl_val = self.clamp_cntrl(cntrl)
        self.setter(cntrl_val)
        actual = float(self.reader())
        self.N += 1
        return actual

    def guess(self, cntrl: Sequence[float], act: Sequence[float], nominal: float) -> float:
        raise NotImplementedError

    def _raise_boundary_or_stagnation(self, guess: float, nominal: float, last_actual: float, iteration: int) -> None:
        at_lower_bound = self.min_cntrl is not None and abs(guess - self.min_cntrl) <= self.stagnation_tol
        at_upper_bound = self.max_cntrl is not None and abs(guess - self.max_cntrl) <= self.stagnation_tol

        if at_lower_bound or at_upper_bound:
            raise RuntimeError(
                f"Control hit control boundary at guess={guess} and cannot move further. "
                f"Last actual={last_actual}, nominal={nominal}. "
                f"The nominal value may be unreachable with the configured control limits "
                f"or the initial support points do not cover the relevant range."
            )

        raise RuntimeError(
            f"Control stagnated after {iteration - 1} iterations "
            f"(guess={guess}, nominal={nominal}, last_actual={last_actual})."
        )

    def do_cntrl(
        self,
        nominal: Number,
        initial: Optional[Sequence[Number]] = None,
        return_result_object: bool = False,
    ) -> Union[Tuple[float, float], ControlResult]:
        nominal = float(nominal)
        cntrl_points = list(self.initial if initial is None else [float(x) for x in initial])

        if len(cntrl_points) < 2:
            raise ValueError("initial must contain at least two control values")

        self.N = 0
        act_points = [self.set_cntrl_val(cntrl) for cntrl in cntrl_points]

        prev_guess = None
        guess = float("nan")
        actual = float("nan")

        for iteration in range(1, self.max_iter + 1):
            raw_guess = float(self.guess(cntrl_points, act_points, nominal))
            guess = self.clamp_cntrl(raw_guess)

            if prev_guess is not None and abs(guess - prev_guess) <= self.stagnation_tol:
                self._raise_boundary_or_stagnation(
                    guess=guess,
                    nominal=nominal,
                    last_actual=float(act_points[-1]),
                    iteration=iteration,
                )

            actual = self.set_cntrl_val(guess)

            if abs(actual - nominal) <= self.abstol:
                if return_result_object:
                    return ControlResult(
                        guess=guess,
                        actual=actual,
                        iterations=iteration,
                        evaluations=self.N,
                    )
                return guess, actual

            cntrl_points.append(guess)
            act_points.append(actual)
            prev_guess = guess

        raise RuntimeError(
            f"Control did not converge to nominal={nominal} within {self.max_iter} iterations. "
            f"Last guess={guess}, last actual={actual}, abstol={self.abstol}."
        )


class ControlPolyfit(ControlBase):
    def __init__(
        self,
        actual_reader: Callable[[], Number],
        setter: Callable[[float], object],
        initial: Sequence[Number],
        abstol: Number,
        maxorder: int = 2,
        **kwargs,
    ):
        super().__init__(actual_reader, setter, initial, abstol, **kwargs)
        if maxorder < 1:
            raise ValueError("maxorder must be >= 1")
        self.maxorder = int(maxorder)

    def guess(self, cntrl: Sequence[float], act: Sequence[float], nominal: float) -> float:
        order = min(self.maxorder, len(cntrl) - 1)
        poly = Polynomial.fit(act, cntrl, order).convert()
        return float(poly(nominal))


class ControlInterpol(ControlBase):
    def _prepare_points(self, cntrl: Sequence[float], act: Sequence[float]) -> Tuple[np.ndarray, np.ndarray]:
        act_arr = np.asarray(act, dtype=float)
        cntrl_arr = np.asarray(cntrl, dtype=float)

        order = np.argsort(act_arr)
        act_sorted = act_arr[order]
        cntrl_sorted = cntrl_arr[order]

        unique_act = []
        unique_cntrl = []

        i = 0
        n = len(act_sorted)
        while i < n:
            same_cntrl = [cntrl_sorted[i]]
            j = i + 1
            while j < n and np.isclose(act_sorted[j], act_sorted[i], rtol=0.0, atol=1e-12):
                same_cntrl.append(cntrl_sorted[j])
                j += 1

            unique_act.append(act_sorted[i])
            unique_cntrl.append(float(np.mean(same_cntrl)))
            i = j

        if len(unique_act) < 2:
            raise RuntimeError("Need at least two distinct actual values for interpolation")

        return np.asarray(unique_cntrl, dtype=float), np.asarray(unique_act, dtype=float)

    def guess(self, cntrl: Sequence[float], act: Sequence[float], nominal: float) -> float:
        cntrl_u, act_u = self._prepare_points(cntrl, act)
        inv_interpol = interp1d(act_u, cntrl_u, bounds_error=False, fill_value="extrapolate")
        return float(inv_interpol(nominal))


class ControlRapp(ControlBase):
    """
    Fit eines sättigenden Rapp-Modells:

        y = g*x / (1 + (g*x/sat)^(2p))^(1/(2p))
    """

    def __init__(
        self,
        actual_reader: Callable[[], Number],
        setter: Callable[[float], object],
        initial: Sequence[Number],
        abstol: Number,
        p: float = 1.0,
        g: float = 1.0,
        sat: float = 20.0,
        **kwargs,
    ):
        super().__init__(actual_reader, setter, initial, abstol, **kwargs)
        if p <= 0:
            raise ValueError("p must be > 0")
        if g <= 0:
            raise ValueError("g must be > 0")
        if sat <= 0:
            raise ValueError("sat must be > 0")

        self.p = float(p)
        self.g = float(g)
        self.sat = float(sat)

    @staticmethod
    def _rapp(par: Sequence[float], x):
        g, p, sat = par
        x = np.asarray(x, dtype=float)
        pp = 2.0 * p
        base = 1.0 + np.power(g * x / sat, pp)
        return g * x / np.power(base, 1.0 / pp)

    def guess(self, cntrl: Sequence[float], act: Sequence[float], nominal: float) -> float:
        cntrl_arr = np.asarray(cntrl, dtype=float)
        act_arr = np.asarray(act, dtype=float)

        def errfunc(par, x, y):
            return self._rapp(par, x) - y

        p0 = [self.g, self.p, self.sat]
        fit, _ = leastsq(errfunc, p0, args=(cntrl_arr, act_arr), maxfev=2000)
        self.g, self.p, self.sat = [float(v) for v in fit]

        def rapp_min(x):
            return self._rapp((self.g, self.p, self.sat), x) - nominal

        start = float(cntrl_arr[-1])
        sol = fsolve(rapp_min, start)
        return float(sol[0])


class ControlBracketInterpol(ControlBase):
    """
    Monotone inverse Regelung mit Bracketing und Interpolation.

    Idee:
    1. Aus den bereits gemessenen Punkten ein Intervall suchen, das den Sollwert einklammert.
    2. Falls kein Intervall existiert:
       - nach oben oder unten vorsichtig extrapolieren
       - mit begrenzter Schrittweite, um Überschwingen zu vermeiden
    3. Falls ein Intervall existiert:
       - lineare inverse Interpolation innerhalb des Intervalls
    4. Optional: nur von unten annähern bzw. Überschwingen dämpfen

    Gut geeignet für monotone Kennlinien, z. B. HF-Pegelregelung über
    Signalgenerator + Leistungsverstärker.
    """

    def __init__(
        self,
        actual_reader,
        setter,
        initial,
        abstol,
        max_iter=20,
        min_cntrl=None,
        max_cntrl=None,
        stagnation_tol=1e-12,
        max_step_up=3.0,
        max_step_down=6.0,
        safety_margin=0.0,
        prefer_from_below=True,
    ):
        super().__init__(
            actual_reader=actual_reader,
            setter=setter,
            initial=initial,
            abstol=abstol,
            max_iter=max_iter,
            min_cntrl=min_cntrl,
            max_cntrl=max_cntrl,
            stagnation_tol=stagnation_tol,
        )

        if max_step_up <= 0:
            raise ValueError("max_step_up must be > 0")
        if max_step_down <= 0:
            raise ValueError("max_step_down must be > 0")
        if safety_margin < 0:
            raise ValueError("safety_margin must be >= 0")

        self.max_step_up = float(max_step_up)
        self.max_step_down = float(max_step_down)
        self.safety_margin = float(safety_margin)
        self.prefer_from_below = bool(prefer_from_below)

    @staticmethod
    def _sorted_points(cntrl, act):
        pairs = sorted(zip(cntrl, act), key=lambda t: t[1])
        return [(float(c), float(a)) for c, a in pairs]

    @staticmethod
    def _find_bracket(points, nominal):
        """
        points: nach actual sortierte Liste [(cntrl, actual), ...]
        Rückgabe:
            ((c_lo, a_lo), (c_hi, a_hi)) oder None
        """
        for p0, p1 in zip(points[:-1], points[1:]):
            _, a0 = p0
            _, a1 = p1
            if a0 <= nominal <= a1:
                return p0, p1
        return None

    @staticmethod
    def _linear_inverse(c0, a0, c1, a1, nominal):
        if abs(a1 - a0) <= 1e-15:
            return 0.5 * (c0 + c1)
        return c0 + (nominal - a0) * (c1 - c0) / (a1 - a0)

    def _limit_step(self, guess, current_cntrl):
        delta = guess - current_cntrl
        if delta > self.max_step_up:
            return current_cntrl + self.max_step_up
        if delta < -self.max_step_down:
            return current_cntrl - self.max_step_down
        return guess

    def guess(self, cntrl, act, nominal):
        points = self._sorted_points(cntrl, act)

        # Letzten tatsächlich gesetzten Punkt als Ausgang für Schrittbegrenzung nehmen
        current_cntrl = float(cntrl[-1])
        current_actual = float(act[-1])

        bracket = self._find_bracket(points, nominal)

        if bracket is not None:
            (c_lo, a_lo), (c_hi, a_hi) = bracket

            guess = self._linear_inverse(c_lo, a_lo, c_hi, a_hi, nominal)

            # Optional leicht von unten annähern, um Overshoot zu dämpfen
            if self.prefer_from_below and a_lo < nominal < a_hi:
                safe_nominal = max(a_lo, nominal - self.safety_margin)
                guess = self._linear_inverse(c_lo, a_lo, c_hi, a_hi, safe_nominal)

            guess = self._limit_step(guess, current_cntrl)
            return float(guess)

        # Kein Bracket vorhanden -> vorsichtige Extrapolation / Suchschritt
        a_min = points[0][1]
        a_max = points[-1][1]

        # Sollwert liegt oberhalb aller bisherigen Messwerte -> Pegel erhöhen
        if nominal > a_max:
            # Falls schon zwei obere Punkte da sind, daraus extrapolieren
            if len(points) >= 2:
                (c0, a0), (c1, a1) = points[-2], points[-1]
                guess = self._linear_inverse(c0, a0, c1, a1, nominal)
            else:
                guess = current_cntrl + self.max_step_up

            guess = max(guess, current_cntrl)  # nicht zurückspringen
            guess = self._limit_step(guess, current_cntrl)
            return float(guess)

        # Sollwert liegt unterhalb aller bisherigen Messwerte -> Pegel senken
        if nominal < a_min:
            if len(points) >= 2:
                (c0, a0), (c1, a1) = points[0], points[1]
                guess = self._linear_inverse(c0, a0, c1, a1, nominal)
            else:
                guess = current_cntrl - self.max_step_down

            if self.prefer_from_below and current_actual <= nominal:
                # wenn wir bereits unterhalb sind, nicht unnötig stark nach unten springen
                guess = min(guess, current_cntrl)

            guess = self._limit_step(guess, current_cntrl)
            return float(guess)

        # Fallback, sollte praktisch kaum erreicht werden
        return float(current_cntrl)

control = ControlBracketInterpol


if __name__ == "__main__":
    from matplotlib import pyplot as plt

    class Data:
        def __init__(self, data):
            self.data = data
            self.level = 0.0
            self.xsteps = []
            self.ysteps = []

        def setter(self, x):
            self.level = float(x)
            self.xsteps.append(self.level)
            return self.level

        def getter(self):
            actual = float(self.data(self.level))
            self.ysteps.append(actual)
            return actual

    # Beispielkennlinie: monotone sättigende Funktion
    x = np.arange(0, 101, dtype=float)
    y = np.zeros_like(x)
    mask = x > 0
    y[mask] = 1.0 / (0.1 / x[mask] + 1.0 / 20.0)

    xy = interp1d(x, y, bounds_error=False, fill_value="extrapolate")

    # Eine Methode auswählen:
    # control = ControlPolyfit
    # control = ControlInterpol
    # control = ControlRapp

    for nominal in np.arange(1.0, 20.0, 2.0):
        D = Data(xy)
        C = ControlBracketInterpol(
            D.getter,
            D.setter,
            initial=[0.0, 1.0, 3.0],
            abstol=0.2,
            max_iter=12,
            min_cntrl=0.0,
            max_cntrl=120.0,
            max_step_up=2.0,
            max_step_down=4.0,
            safety_margin=0.1,
            prefer_from_below=True,
        )
        # C = control(
        #     D.getter,
        #     D.setter,
        #     initial=[0.0, 1.0, 3.0],
        #     abstol=0.5,
        #     max_iter=15,
        #     min_cntrl=0.0,
        #     max_cntrl=120.0,
        # )

        try:
            result = C.do_cntrl(nominal, return_result_object=True)
            print(
                f"nominal={nominal:.2f}, guess={result.guess:.4f}, "
                f"actual={result.actual:.4f}, iterations={result.iterations}, "
                f"evaluations={result.evaluations}"
            )
        except RuntimeError as exc:
            print(f"nominal={nominal:.2f} failed: {exc}")

        plt.figure()
        plt.plot(x, y, "r--", label="Kennlinie")
        plt.plot(D.xsteps, D.ysteps, "bo", label="Schritte")

        for i, point in enumerate(zip(D.xsteps, D.ysteps)):
            plt.annotate(str(i), point)

        plt.xlabel("control")
        plt.ylabel("actual")
        plt.title(f"{control.__name__}, nominal={nominal:.2f}")
        plt.legend()
        plt.show()
