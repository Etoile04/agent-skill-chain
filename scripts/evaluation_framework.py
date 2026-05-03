"""跨层评测体系 - Cross-layer Evaluation Framework."""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class MetricRecord:
    """A single measurement record for a metric."""

    metric_name: str
    layer: str
    target: float
    value: float
    unit: str
    timestamp: str = ""
    description: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

    def passes_target(self) -> bool:
        """Return True if the measured value meets or exceeds the target."""
        return self.value >= self.target


class EvaluationFramework:
    """Framework for registering metrics, recording measurements, and computing scores."""

    def __init__(self):
        # metric_name -> {layer, target, unit, description}
        self._metrics: Dict[str, Dict] = {}
        # metric_name -> list of MetricRecord
        self._records: Dict[str, List[MetricRecord]] = {}

    # -- registration --

    def register_metric(
        self,
        name: str,
        layer: str,
        target: float,
        unit: str,
        description: str = "",
    ) -> None:
        """Register a new metric definition."""
        self._metrics[name] = {
            "layer": layer,
            "target": target,
            "unit": unit,
            "description": description,
        }
        if name not in self._records:
            self._records[name] = []

    def list_metrics(self) -> List[Dict]:
        """Return a list of all registered metric definitions."""
        result = []
        for name, meta in self._metrics.items():
            result.append({
                "name": name,
                "layer": meta["layer"],
                "target": meta["target"],
                "unit": meta["unit"],
                "description": meta["description"],
            })
        return result

    # -- recording --

    def record(self, metric_name: str, value: float) -> MetricRecord:
        """Record a measurement for a registered metric."""
        if metric_name not in self._metrics:
            raise ValueError(f"Metric '{metric_name}' is not registered")
        meta = self._metrics[metric_name]
        rec = MetricRecord(
            metric_name=metric_name,
            layer=meta["layer"],
            value=value,
            target=meta["target"],
            unit=meta["unit"],
            description=meta["description"],
        )
        self._records[metric_name].append(rec)
        return rec

    def get_records(self, metric_name: str) -> List[MetricRecord]:
        """Return all recorded measurements for a metric."""
        return list(self._records.get(metric_name, []))

    # -- scoring --

    def compute_layer_score(self, layer: str) -> float:
        """Compute the average of the latest values for all metrics in a layer."""
        latest_values: List[float] = []
        for name, meta in self._metrics.items():
            if meta["layer"] != layer:
                continue
            recs = self._records.get(name, [])
            if recs:
                latest_values.append(recs[-1].value)
        if not latest_values:
            return 0.0
        return sum(latest_values) / len(latest_values)

    def compute_overall_score(self) -> float:
        """Compute the average of all layer scores."""
        layers = {meta["layer"] for meta in self._metrics.values()}
        if not layers:
            return 0.0
        scores = [self.compute_layer_score(layer) for layer in layers]
        return sum(scores) / len(scores)

    # -- diagnostics --

    def get_failing_metrics(self) -> List[MetricRecord]:
        """Return the latest record for each metric that does not meet its target."""
        failing = []
        for name in self._metrics:
            recs = self._records.get(name, [])
            if recs and not recs[-1].passes_target():
                failing.append(recs[-1])
        return failing

    def get_layer_summary(self) -> Dict[str, Dict]:
        """Return a summary dict keyed by layer with score, metrics, and failing list."""
        layers = {meta["layer"] for meta in self._metrics.values()}
        summary: Dict[str, Dict] = {}
        for layer in layers:
            metrics_in_layer = [
                name for name, meta in self._metrics.items() if meta["layer"] == layer
            ]
            failing = [
                rec
                for name in metrics_in_layer
                for rec in [self._records.get(name, [])]
                if rec and not rec[-1].passes_target()
                for rec in [rec[-1]]
            ]
            summary[layer] = {
                "score": self.compute_layer_score(layer),
                "metrics": metrics_in_layer,
                "failing": failing,
            }
        return summary
