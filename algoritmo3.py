# ============================================================
# Algorithm 3 - Didactic Dynamic Scenario Generator
# Web Learning Version v1.0
#
# Purpose:
#   Transform predictive and adaptive information into:
#   - disruption context
#   - five plausible future scenarios
#   - dynamic scenario probabilities
#   - adaptive robustness budget
#   - scenario validation
#   - educational explanations
#
# Inputs:
#   Algorithm 1 output
#   Algorithm 2 output
#
# Outputs:
#   Dynamic Scenario Package for Algorithm 4
# ============================================================

from dataclasses import dataclass, asdict
from typing import List, Dict
import numpy as np


# ============================================================
# 1. Input structures
# ============================================================

@dataclass
class PredictiveState:

    predicted_pressure: float
    predicted_state: str
    prediction_confidence: float

    supply_availability: float
    demand_level: float
    transport_availability: float
    processing_capacity: float
    quality_index: float
    lead_time_index: float

    disruption_intensity: float
    disruption_persistence: float


@dataclass
class AdaptivePolicyState:

    memory_after: float

    recommended_scis_layer_code: int

    policy_score: float
    decision_confidence: float
    decision_quality: float

    expected_net_utility: float


# ============================================================
# 2. Scenario structure
# ============================================================

@dataclass
class Scenario:

    scenario_id: str
    scenario_name: str

    probability: float

    supply_availability: float
    demand_level: float
    transport_availability: float
    processing_capacity: float
    lead_time_index: float

    operational_pressure: float

    severity: str

    valid: bool
    explanation: str


# ============================================================
# 3. Algorithm 3 output
# ============================================================

@dataclass
class DynamicScenarioPackage:

    disruption_context: str

    dominant_risk: float
    novelty_score: float

    robustness_budget: float

    scenario_entropy: float

    scenarios: List[Dict]

    most_probable_scenario: str
    worst_case_probability: float

    package_valid: bool

    learning_message: str


# ============================================================
# 4. Disruption context identification
# ============================================================

def identify_disruption_context(
    state: PredictiveState
) -> str:

    supply_loss = 1 - state.supply_availability
    transport_loss = 1 - state.transport_availability
    capacity_loss = 1 - state.processing_capacity

    demand_pressure = max(
        0,
        state.demand_level - 1
    )

    lead_time_pressure = max(
        0,
        state.lead_time_index - 1
    )

    risks = {
        "Supply_Disruption": supply_loss,
        "Demand_Anomaly": demand_pressure,
        "Transportation_Disruption": (
            0.65 * transport_loss
            + 0.35 * lead_time_pressure
        ),
        "Production_Degradation":
            capacity_loss,
        "Persistent_Disruption":
            state.disruption_persistence
    }

    dominant = max(
        risks,
        key=risks.get
    )

    return dominant


# ============================================================
# 5. Novelty estimation
# ============================================================

def compute_novelty_score(
    predictive_state: PredictiveState,
    adaptive_state: AdaptivePolicyState
) -> float:

    """
    Novelty increases when:
    - current disruption is severe
    - prediction confidence is low
    - adaptive memory is weak
    """

    novelty = (
        0.40 * predictive_state.disruption_intensity
        + 0.25 * predictive_state.disruption_persistence
        + 0.20 * (
            1 - predictive_state.prediction_confidence
        )
        + 0.15 * (
            1 - adaptive_state.memory_after
        )
    )

    return float(
        np.clip(novelty, 0, 1)
    )


# ============================================================
# 6. Adaptive robustness budget
# ============================================================

def compute_robustness_budget(
    pressure: float,
    novelty: float,
    decision_confidence: float,
    memory_level: float
) -> float:

    """
    Higher uncertainty and pressure increase the
    robustness requirement.

    Strong memory and confidence reduce unnecessary
    conservatism.
    """

    budget = (
        0.35 * pressure
        + 0.30 * novelty
        + 0.20 * (
            1 - decision_confidence
        )
        + 0.15 * (
            1 - memory_level
        )
    )

    return float(
        np.clip(budget, 0.05, 1.0)
    )


# ============================================================
# 7. Scenario transformation utility
# ============================================================

def apply_scenario_multiplier(
    value: float,
    multiplier: float,
    lower: float,
    upper: float
) -> float:

    return float(
        np.clip(
            value * multiplier,
            lower,
            upper
        )
    )


# ============================================================
# 8. Scenario pressure
# ============================================================

def scenario_pressure(
    supply: float,
    demand: float,
    transport: float,
    capacity: float,
    lead_time: float
) -> float:

    pressure = (
        0.25 * (1 - supply)
        + 0.20 * (1 - transport)
        + 0.20 * (1 - capacity)
        + 0.15 * max(0, demand - 1)
        + 0.20 * max(0, lead_time - 1)
    )

    return float(
        np.clip(pressure, 0, 1)
    )


# ============================================================
# 9. Severity classification
# ============================================================

def severity_from_pressure(
    pressure: float
) -> str:

    if pressure < 0.10:
        return "Low"

    if pressure < 0.20:
        return "Moderate"

    if pressure < 0.35:
        return "High"

    if pressure < 0.50:
        return "Critical"

    return "Extreme"


# ============================================================
# 10. Generate five representative scenarios
# ============================================================

def generate_scenarios(
    state: PredictiveState,
    robustness_budget: float
) -> List[Scenario]:

    """
    Five futures:
    1. Dominant
    2. Optimistic
    3. Pessimistic
    4. Recovery
    5. Worst-case
    """

    scenario_definitions = {

        "Dominant": {
            "supply": 1.00,
            "demand": 1.00,
            "transport": 1.00,
            "capacity": 1.00,
            "lead_time": 1.00
        },

        "Optimistic": {
            "supply": 1.04,
            "demand": 0.98,
            "transport": 1.06,
            "capacity": 1.04,
            "lead_time": 0.92
        },

        "Pessimistic": {
            "supply": 0.92,
            "demand": 1.05,
            "transport": 0.88,
            "capacity": 0.92,
            "lead_time": 1.15
        },

        "Recovery": {
            "supply": 1.06,
            "demand": 1.00,
            "transport": 1.08,
            "capacity": 1.05,
            "lead_time": 0.88
        },

        "Worst_case": {
            "supply": (
                1 - 0.25 * robustness_budget
            ),
            "demand": (
                1 + 0.20 * robustness_budget
            ),
            "transport": (
                1 - 0.35 * robustness_budget
            ),
            "capacity": (
                1 - 0.30 * robustness_budget
            ),
            "lead_time": (
                1 + 0.45 * robustness_budget
            )
        }
    }

    scenarios = []

    for i, (name, m) in enumerate(
        scenario_definitions.items(),
        start=1
    ):

        supply = apply_scenario_multiplier(
            state.supply_availability,
            m["supply"],
            0.05,
            1.00
        )

        demand = apply_scenario_multiplier(
            state.demand_level,
            m["demand"],
            0.50,
            2.00
        )

        transport = apply_scenario_multiplier(
            state.transport_availability,
            m["transport"],
            0.05,
            1.00
        )

        capacity = apply_scenario_multiplier(
            state.processing_capacity,
            m["capacity"],
            0.05,
            1.00
        )

        lead_time = apply_scenario_multiplier(
            state.lead_time_index,
            m["lead_time"],
            0.50,
            2.50
        )

        pressure = scenario_pressure(
            supply,
            demand,
            transport,
            capacity,
            lead_time
        )

        scenarios.append(
            Scenario(
                scenario_id=f"S{i}",
                scenario_name=name,

                probability=0.0,

                supply_availability=
                    round(supply, 4),

                demand_level=
                    round(demand, 4),

                transport_availability=
                    round(transport, 4),

                processing_capacity=
                    round(capacity, 4),

                lead_time_index=
                    round(lead_time, 4),

                operational_pressure=
                    round(pressure, 4),

                severity=
                    severity_from_pressure(
                        pressure
                    ),

                valid=True,

                explanation=""
            )
        )

    return scenarios


# ============================================================
# 11. Dynamic probabilities
# ============================================================

def assign_scenario_probabilities(
    scenarios: List[Scenario],
    prediction_confidence: float,
    disruption_persistence: float,
    novelty: float
) -> List[Scenario]:

    """
    Probability changes according to:
    - forecast confidence
    - disruption persistence
    - novelty
    """

    base = {
        "Dominant": 0.40,
        "Optimistic": 0.15,
        "Pessimistic": 0.20,
        "Recovery": 0.15,
        "Worst_case": 0.10
    }

    weights = []

    for scenario in scenarios:

        w = base[
            scenario.scenario_name
        ]

        if scenario.scenario_name == "Dominant":

            w *= (
                0.70
                + 0.60
                * prediction_confidence
            )

        elif scenario.scenario_name == "Optimistic":

            w *= (
                1.20
                - 0.50
                * disruption_persistence
            )

        elif scenario.scenario_name == "Recovery":

            w *= (
                1.15
                - 0.45
                * disruption_persistence
            )

        elif scenario.scenario_name == "Pessimistic":

            w *= (
                0.80
                + 0.70
                * disruption_persistence
            )

        elif scenario.scenario_name == "Worst_case":

            w *= (
                0.60
                + 0.80 * novelty
                + 0.50
                * disruption_persistence
            )

        weights.append(
            max(w, 0.001)
        )

    total = sum(weights)

    for scenario, w in zip(
        scenarios,
        weights
    ):

        scenario.probability = round(
            w / total,
            4
        )

    return scenarios


# ============================================================
# 12. Scenario validation layer
# ============================================================

def validate_scenario(
    scenario: Scenario
) -> bool:

    """
    Simplified educational version of SVRL.
    """

    checks = [

        0.05 <=
        scenario.supply_availability
        <= 1.00,

        0.50 <=
        scenario.demand_level
        <= 2.00,

        0.05 <=
        scenario.transport_availability
        <= 1.00,

        0.05 <=
        scenario.processing_capacity
        <= 1.00,

        0.50 <=
        scenario.lead_time_index
        <= 2.50,

        0 <=
        scenario.operational_pressure
        <= 1
    ]

    return all(checks)


def validate_scenarios(
    scenarios: List[Scenario]
) -> List[Scenario]:

    for scenario in scenarios:

        scenario.valid = (
            validate_scenario(
                scenario
            )
        )

        if scenario.valid:

            scenario.explanation = (
                "Scenario satisfies all "
                "operational feasibility bounds."
            )

        else:

            scenario.explanation = (
                "Scenario violates at least one "
                "operational feasibility bound."
            )

    return scenarios


# ============================================================
# 13. Scenario entropy
# ============================================================

def compute_scenario_entropy(
    scenarios: List[Scenario]
) -> float:

    probabilities = np.array([
        s.probability
        for s in scenarios
    ])

    probabilities = probabilities[
        probabilities > 0
    ]

    entropy = -np.sum(
        probabilities
        * np.log(probabilities)
    )

    normalized = entropy / np.log(
        len(scenarios)
    )

    return float(
        np.clip(normalized, 0, 1)
    )


# ============================================================
# 14. Educational explanation
# ============================================================

def generate_learning_message(
    context: str,
    scenarios: List[Scenario],
    robustness_budget: float,
    entropy: float
) -> str:

    dominant = max(
        scenarios,
        key=lambda s: s.probability
    )

    worst = next(
        s
        for s in scenarios
        if s.scenario_name
        == "Worst_case"
    )

    return (
        f"The Digital Twin identified "
        f"{context} as the dominant disruption context. "
        f"The most probable future is "
        f"{dominant.scenario_name} "
        f"with probability "
        f"{dominant.probability:.1%}. "
        f"The worst-case trajectory retains "
        f"{worst.probability:.1%} probability. "
        f"The adaptive robustness budget is "
        f"{robustness_budget:.2f}. "
        f"Scenario uncertainty is "
        f"{entropy:.2f} on a normalized 0-1 scale."
    )


# ============================================================
# 15. Main Algorithm 3
# ============================================================

def algorithm_3(
    predictive_state: PredictiveState,
    adaptive_state: AdaptivePolicyState
) -> DynamicScenarioPackage:

    # --------------------------------------------------------
    # Step 1 - Identify disruption context
    # --------------------------------------------------------

    context = identify_disruption_context(
        predictive_state
    )

    # --------------------------------------------------------
    # Step 2 - Estimate novelty
    # --------------------------------------------------------

    novelty = compute_novelty_score(
        predictive_state,
        adaptive_state
    )

    # --------------------------------------------------------
    # Step 3 - Calculate robustness budget
    # --------------------------------------------------------

    robustness_budget = (
        compute_robustness_budget(

            pressure=
                predictive_state
                .predicted_pressure,

            novelty=novelty,

            decision_confidence=
                adaptive_state
                .decision_confidence,

            memory_level=
                adaptive_state
                .memory_after
        )
    )

    # --------------------------------------------------------
    # Step 4 - Generate five futures
    # --------------------------------------------------------

    scenarios = generate_scenarios(
        predictive_state,
        robustness_budget
    )

    # --------------------------------------------------------
    # Step 5 - Assign probabilities
    # --------------------------------------------------------

    scenarios = (
        assign_scenario_probabilities(

            scenarios,

            predictive_state
            .prediction_confidence,

            predictive_state
            .disruption_persistence,

            novelty
        )
    )

    # --------------------------------------------------------
    # Step 6 - Validate scenarios
    # --------------------------------------------------------

    scenarios = validate_scenarios(
        scenarios
    )

    # --------------------------------------------------------
    # Step 7 - Quantify scenario uncertainty
    # --------------------------------------------------------

    entropy = compute_scenario_entropy(
        scenarios
    )

    # --------------------------------------------------------
    # Step 8 - Determine dominant future
    # --------------------------------------------------------

    dominant = max(
        scenarios,
        key=lambda s: s.probability
    )

    worst = next(
        s
        for s in scenarios
        if s.scenario_name
        == "Worst_case"
    )

    # --------------------------------------------------------
    # Step 9 - Validate complete package
    # --------------------------------------------------------

    package_valid = all(
        s.valid
        for s in scenarios
    )

    # --------------------------------------------------------
    # Step 10 - Explain DT reasoning
    # --------------------------------------------------------

    learning_message = (
        generate_learning_message(
            context=context,
            scenarios=scenarios,
            robustness_budget=
                robustness_budget,
            entropy=entropy
        )
    )

    # --------------------------------------------------------
    # Step 11 - Frontend output
    # --------------------------------------------------------

    scenario_output = [
        asdict(s)
        for s in scenarios
    ]

    return DynamicScenarioPackage(

        disruption_context=
            context,

        dominant_risk=
            round(
                predictive_state
                .disruption_intensity,
                4
            ),

        novelty_score=
            round(novelty, 4),

        robustness_budget=
            round(
                robustness_budget,
                4
            ),

        scenario_entropy=
            round(entropy, 4),

        scenarios=
            scenario_output,

        most_probable_scenario=
            dominant.scenario_name,

        worst_case_probability=
            worst.probability,

        package_valid=
            package_valid,

        learning_message=
            learning_message
    )


# ============================================================
# 16. Example
# ============================================================

if __name__ == "__main__":

    predictive_state = PredictiveState(

        predicted_pressure=0.34,
        predicted_state=
            "S2_Disruption",

        prediction_confidence=0.86,

        supply_availability=0.87,
        demand_level=1.12,
        transport_availability=0.54,
        processing_capacity=0.91,
        quality_index=0.94,
        lead_time_index=1.35,

        disruption_intensity=0.58,
        disruption_persistence=0.55
    )

    adaptive_state = AdaptivePolicyState(

        memory_after=0.57,

        recommended_scis_layer_code=3,

        policy_score=0.63,

        decision_confidence=0.88,
        decision_quality=0.82,

        expected_net_utility=0.63
    )

    result = algorithm_3(
        predictive_state,
        adaptive_state
    )

    print("\nDYNAMIC SCENARIO PACKAGE")
    print("------------------------")

    print(
        "Disruption context:",
        result.disruption_context
    )

    print(
        "Novelty:",
        result.novelty_score
    )

    print(
        "Robustness budget:",
        result.robustness_budget
    )

    print(
        "Scenario entropy:",
        result.scenario_entropy
    )

    print("\nSCENARIOS")

    for scenario in result.scenarios:

        print(
            scenario["scenario_name"],
            "| Probability:",
            scenario["probability"],
            "| Pressure:",
            scenario[
                "operational_pressure"
            ],
            "| Severity:",
            scenario["severity"]
        )

    print(
        "\n",
        result.learning_message
    )