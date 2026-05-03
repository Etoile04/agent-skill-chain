"""Self Optimizer — performance-driven parameter auto-tuning."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class OptimizationRecord:
    parameter_name: str
    old_value: float
    new_value: float
    performance_before: float
    timestamp: str


class ParameterSet:
    """Thin wrapper around a parameter dict."""

    def __init__(self, params: Dict[str, float] | None = None):
        self._params: Dict[str, float] = dict(params) if params else {}

    def get(self, key: str) -> Optional[float]:
        return self._params.get(key)

    def set(self, key: str, value: float) -> None:
        self._params[key] = value

    def _raw(self) -> Dict[str, float]:
        return self._params


class SelfOptimizer:
    """Closed-loop parameter optimizer.

    Registers tunable parameters with bounds and step size. On each
    evaluation, if the performance score is below 0.7 the parameter
    value is adjusted by one step in the direction indicated by
    *direction* ("maximize" or "minimize"), clamped to its bounds.
    """

    _ADJUST_THRESHOLD = 0.7

    def __init__(self):
        self._params: Dict[str, float] = {}
        self._meta: Dict[str, Dict[str, float]] = {}  # min, max, step
        self._history: List[OptimizationRecord] = []

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register_parameter(
        self,
        name: str,
        default: float,
        min_val: float,
        max_val: float,
        step: float,
    ) -> None:
        self._params[name] = default
        self._meta[name] = {"min": min_val, "max": max_val, "step": step}

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get_current_params(self) -> ParameterSet:
        return ParameterSet(dict(self._params))

    def get_history(self) -> List[OptimizationRecord]:
        return list(self._history)

    def suggest(self, param_name: str) -> Optional[float]:
        """Return the best-known value for *param_name*.

        Looks at history for the record with the highest
        *performance_before* and returns its *new_value*.  Falls back
        to the current parameter value.
        """
        best_record: Optional[OptimizationRecord] = None
        for rec in self._history:
            if rec.parameter_name != param_name:
                continue
            if best_record is None or rec.performance_before > best_record.performance_before:
                best_record = rec
        if best_record is not None:
            return best_record.new_value
        return self._params.get(param_name)

    # ------------------------------------------------------------------
    # Evaluate & adjust
    # ------------------------------------------------------------------

    def evaluate(
        self,
        param_name: str,
        performance_score: float,
        direction: str = "maximize",
    ) -> Optional[OptimizationRecord]:
        """Evaluate performance and optionally adjust the parameter.

        Returns an ``OptimizationRecord`` when an adjustment was made,
        or ``None`` when performance was satisfactory (>= 0.7).
        """
        if performance_score >= self._ADJUST_THRESHOLD:
            return None

        old_value = self._params[param_name]
        meta = self._meta[param_name]
        step = meta["step"]

        if direction == "maximize":
            new_value = old_value + step
        else:
            new_value = old_value - step

        # Clamp to bounds
        new_value = max(meta["min"], min(meta["max"], new_value))

        self._params[param_name] = new_value

        record = OptimizationRecord(
            parameter_name=param_name,
            old_value=old_value,
            new_value=new_value,
            performance_before=performance_score,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self._history.append(record)
        return record
