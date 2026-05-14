from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import pandas as pd
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.core.problem import ElementwiseProblem
from pymoo.optimize import minimize
from pymoo.termination import get_termination

from src.optimization.objective import evaluate_factor_rotation_parameters_on_window
from src.strategies.factor_rotation import FactorRotationParameters

OBJECTIVE_NAMES = (
    "negative_sharpe",
    "negative_cagr",
    "max_drawdown_abs",
    "average_turnover",
)


@dataclass(frozen=True)
class NSGA2SearchSpace:
    """Continuous/discrete search space for factor-rotation NSGA-II smoke."""

    momentum_windows: tuple[int, ...] = (63, 126, 252)
    volatility_windows: tuple[int, ...] = (21, 63, 126)
    drawdown_windows: tuple[int, ...] = (63, 126, 252)
    factor_weight_min: float = 0.0
    factor_weight_max: float = 2.0
    top_k_min: int = 2
    top_k_max: int = 6
    max_asset_weight_min: float = 0.2
    max_asset_weight_max: float = 0.5
    rebalance_frequency: str = "ME"

    def __post_init__(self) -> None:
        """Validate search-space boundaries."""
        window_groups = {
            "momentum_windows": self.momentum_windows,
            "volatility_windows": self.volatility_windows,
            "drawdown_windows": self.drawdown_windows,
        }
        for name, values in window_groups.items():
            if not values:
                raise ValueError(f"{name} must not be empty.")
            if any(value <= 0 for value in values):
                raise ValueError(f"{name} must contain only positive windows.")

        if self.factor_weight_min < 0.0:
            raise ValueError("factor_weight_min must be non-negative.")
        if self.factor_weight_max <= self.factor_weight_min:
            raise ValueError("factor_weight_max must exceed factor_weight_min.")

        if self.top_k_min <= 0:
            raise ValueError("top_k_min must be positive.")
        if self.top_k_max < self.top_k_min:
            raise ValueError("top_k_max must be >= top_k_min.")

        if self.max_asset_weight_min <= 0.0:
            raise ValueError("max_asset_weight_min must be positive.")
        if self.max_asset_weight_max > 1.0:
            raise ValueError("max_asset_weight_max must be <= 1.")
        if self.max_asset_weight_max < self.max_asset_weight_min:
            raise ValueError("max_asset_weight_max must be >= max_asset_weight_min.")

    @property
    def variable_count(self) -> int:
        """Return optimizer vector dimensionality."""
        return 8

    def bounds(self) -> tuple[np.ndarray, np.ndarray]:
        """Return lower/upper bounds for pymoo."""
        lower = np.array(
            [
                0,
                0,
                0,
                self.factor_weight_min,
                self.factor_weight_min,
                self.factor_weight_min,
                self.top_k_min,
                self.max_asset_weight_min,
            ],
            dtype="float64",
        )
        upper = np.array(
            [
                len(self.momentum_windows) - 1,
                len(self.volatility_windows) - 1,
                len(self.drawdown_windows) - 1,
                self.factor_weight_max,
                self.factor_weight_max,
                self.factor_weight_max,
                self.top_k_max,
                self.max_asset_weight_max,
            ],
            dtype="float64",
        )

        return lower, upper

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-compatible search-space description."""
        payload = asdict(self)
        return {
            key: list(value) if isinstance(value, tuple) else value
            for key, value in payload.items()
        }

    @staticmethod
    def round_choice_index(value: float, choice_count: int) -> int:
        """Round a continuous optimizer value to a valid discrete choice index."""
        rounded = int(np.rint(value))
        return int(np.clip(rounded, 0, choice_count - 1))

    def decode_vector(self, vector: Iterable[float]) -> FactorRotationParameters:
        """Decode optimizer vector into factor-rotation parameters."""
        vector_array = np.asarray(list(vector), dtype="float64")

        if vector_array.shape != (self.variable_count,):
            raise ValueError(
                f"Expected vector shape ({self.variable_count},), " f"got {vector_array.shape}."
            )

        momentum_index = self.round_choice_index(
            value=vector_array[0],
            choice_count=len(self.momentum_windows),
        )
        volatility_index = self.round_choice_index(
            value=vector_array[1],
            choice_count=len(self.volatility_windows),
        )
        drawdown_index = self.round_choice_index(
            value=vector_array[2],
            choice_count=len(self.drawdown_windows),
        )

        top_k = int(np.clip(np.rint(vector_array[6]), self.top_k_min, self.top_k_max))
        max_asset_weight = float(
            np.clip(
                vector_array[7],
                self.max_asset_weight_min,
                self.max_asset_weight_max,
            )
        )

        return FactorRotationParameters(
            momentum_window=self.momentum_windows[momentum_index],
            volatility_window=self.volatility_windows[volatility_index],
            drawdown_window=self.drawdown_windows[drawdown_index],
            momentum_weight=float(
                np.clip(
                    vector_array[3],
                    self.factor_weight_min,
                    self.factor_weight_max,
                )
            ),
            volatility_weight=float(
                np.clip(
                    vector_array[4],
                    self.factor_weight_min,
                    self.factor_weight_max,
                )
            ),
            drawdown_weight=float(
                np.clip(
                    vector_array[5],
                    self.factor_weight_min,
                    self.factor_weight_max,
                )
            ),
            top_k=top_k,
            max_asset_weight=max_asset_weight,
            rebalance_frequency=self.rebalance_frequency,
        )


def objective_dict_to_array(objectives: dict[str, float]) -> np.ndarray:
    """Convert objective dictionary to fixed-order pymoo objective array."""
    return np.array(
        [float(objectives[name]) for name in OBJECTIVE_NAMES],
        dtype="float64",
    )


def objective_array_to_dict(values: Iterable[float]) -> dict[str, float]:
    """Convert fixed-order objective vector to dictionary."""
    return {name: float(value) for name, value in zip(OBJECTIVE_NAMES, values, strict=True)}


class FactorRotationNSGA2Problem(ElementwiseProblem):
    """Pymoo ElementwiseProblem for train-only factor-rotation optimization."""

    def __init__(
        self,
        price_matrix: pd.DataFrame,
        train_start: str | pd.Timestamp,
        train_end: str | pd.Timestamp,
        search_space: NSGA2SearchSpace,
        transaction_cost_bps: float = 10.0,
        risk_free_rate: float = 0.0,
        min_return_observations: int = 1000,
        penalty_value: float = 1_000_000.0,
    ) -> None:
        self.price_matrix = price_matrix
        self.train_start = train_start
        self.train_end = train_end
        self.search_space = search_space
        self.transaction_cost_bps = transaction_cost_bps
        self.risk_free_rate = risk_free_rate
        self.min_return_observations = min_return_observations
        self.penalty_value = penalty_value
        self.evaluations: list[dict[str, Any]] = []

        lower_bounds, upper_bounds = search_space.bounds()

        super().__init__(
            n_var=search_space.variable_count,
            n_obj=len(OBJECTIVE_NAMES),
            n_constr=0,
            xl=lower_bounds,
            xu=upper_bounds,
        )

    def _evaluate(
        self,
        x: np.ndarray,
        out: dict[str, Any],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Evaluate one optimizer vector."""
        parameters = self.search_space.decode_vector(x)
        evaluation = evaluate_factor_rotation_parameters_on_window(
            price_matrix=self.price_matrix,
            parameters=parameters,
            train_start=self.train_start,
            train_end=self.train_end,
            transaction_cost_bps=self.transaction_cost_bps,
            risk_free_rate=self.risk_free_rate,
            min_return_observations=self.min_return_observations,
            penalty_value=self.penalty_value,
        )
        objective_array = objective_dict_to_array(evaluation.objectives)
        out["F"] = objective_array

        payload = evaluation.to_dict()
        payload["candidate_id"] = f"evaluation_{len(self.evaluations):04d}"
        payload["optimizer_vector"] = [float(value) for value in x.tolist()]
        self.evaluations.append(payload)


def build_pareto_front_records(
    result_x: np.ndarray | None,
    result_f: np.ndarray | None,
    search_space: NSGA2SearchSpace,
) -> list[dict[str, Any]]:
    """Build JSON-compatible Pareto-front records from pymoo result arrays."""
    if result_x is None or result_f is None:
        return []

    vectors = np.atleast_2d(result_x)
    objectives = np.atleast_2d(result_f)

    records: list[dict[str, Any]] = []
    for index, (vector, objective_values) in enumerate(zip(vectors, objectives, strict=True)):
        parameters = search_space.decode_vector(vector)
        records.append(
            {
                "pareto_id": f"pareto_{index:03d}",
                "strategy_name": parameters.strategy_name(),
                "parameters": asdict(parameters),
                "optimizer_vector": [float(value) for value in vector.tolist()],
                "objectives": objective_array_to_dict(objective_values),
            }
        )

    return records


def run_nsga2_train_optimizer(
    price_matrix: pd.DataFrame,
    train_start: str | pd.Timestamp,
    train_end: str | pd.Timestamp,
    search_space: NSGA2SearchSpace,
    population_size: int = 12,
    generations: int = 3,
    seed: int = 42,
    transaction_cost_bps: float = 10.0,
    risk_free_rate: float = 0.0,
    min_return_observations: int = 1000,
    penalty_value: float = 1_000_000.0,
) -> dict[str, Any]:
    """Run train-only NSGA-II smoke optimization."""
    if population_size <= 0:
        raise ValueError("population_size must be positive.")
    if generations <= 0:
        raise ValueError("generations must be positive.")

    problem = FactorRotationNSGA2Problem(
        price_matrix=price_matrix,
        train_start=train_start,
        train_end=train_end,
        search_space=search_space,
        transaction_cost_bps=transaction_cost_bps,
        risk_free_rate=risk_free_rate,
        min_return_observations=min_return_observations,
        penalty_value=penalty_value,
    )

    algorithm = NSGA2(
        pop_size=population_size,
        eliminate_duplicates=True,
    )
    termination = get_termination("n_gen", generations)

    result = minimize(
        problem=problem,
        algorithm=algorithm,
        termination=termination,
        seed=seed,
        verbose=False,
        save_history=False,
    )

    pareto_front = build_pareto_front_records(
        result_x=result.X,
        result_f=result.F,
        search_space=search_space,
    )

    return {
        "objective_names": list(OBJECTIVE_NAMES),
        "population_size": population_size,
        "generations": generations,
        "seed": seed,
        "search_space": search_space.to_dict(),
        "evaluation_count": len(problem.evaluations),
        "valid_evaluation_count": sum(
            1 for evaluation in problem.evaluations if evaluation["valid"]
        ),
        "invalid_evaluation_count": sum(
            1 for evaluation in problem.evaluations if not evaluation["valid"]
        ),
        "all_evaluations": problem.evaluations,
        "pareto_front": pareto_front,
        "pareto_candidate_count": len(pareto_front),
    }
