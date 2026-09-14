# ============================================================
# Algorithm 4 - Didactic Integrated Digital Twin Decision Cycle
# Web Learning Version v1.0
#
# Purpose:
#   Integrate Algorithms 1, 2, and 3 into a recurrent
#   Digital Twin learning and decision cycle.
#
# Main logic:
#   Physical State
#       -> Algorithm 1: Predict
#       -> Baseline planning
#       -> Trigger evaluation
#       -> Algorithm 2: Remember / Learn
#       -> Algorithm 3: Generate plausible futures
#       -> Adaptive operational response
#       -> Implementation
#       -> Outcome evaluation
#       -> Memory update
#       -> Next DT cycle
#
# Designed for:
#   Educational web platform
#   FastAPI / Streamlit / React backend
# ============================================================

from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
import numpy as np
import uuid
from datetime import datetime


# ============================================================
# 1. Physical supply-chain state
# ============================================================

@dataclass
class PhysicalSupplyChainState:

    cycle: int

    supply_availability: float
    demand_level: float
    transport_availability: float
    processing_capacity: float
    quality_index: float
    lead_time_index: float

    disruption_intensity: float
    disruption_persistence: float

    inventory_level: float = 0.70
    service_level: float = 0.90
    profitability: float = 0.75
    viability: float = 0.80


# ============================================================
# 2. Baseline decision
# ============================================================

@dataclass
class BaselineDecision:

    production_adjustment: float
    inventory_adjustment: float
    transport_adjustment: float
    sourcing_adjustment: float

    intervention_level: float

    expected_service_level: float
    expected_profitability: float
    expected_viability: float


# ============================================================
# 3. Adaptive decision
# ============================================================

@dataclass
class AdaptiveOperationalDecision:

    scis_layer: str
    scis_layer_code: int

    production_adjustment: float
    inventory_adjustment: float
    transport_adjustment: float
    sourcing_adjustment: float

    recovery_effort: float

    robustness_budget: float

    expected_service_level: float
    expected_profitability: float
    expected_viability: float

    decision_source: str


# ============================================================
# 4. Outcome
# ============================================================

@dataclass
class CycleOutcome:

    viability_before: float
    viability_after: float

    service_before: float
    service_after: float

    profitability_before: float
    profitability_after: float

    viability_gain: float
    service_gain: float
    profitability_gain: float

    intervention_cost: float

    decision_success: float


# ============================================================
# 5. Cycle result
# ============================================================

@dataclass
class DigitalTwinCycleResult:

    cycle: int
    timestamp: str

    operational_pressure: float
    predicted_pressure: float

    current_state: str
    predicted_state: str

    alert_level: str

    scis_triggered: bool

    baseline_decision: Dict

    adaptive_policy: Optional[Dict]
    scenario_package: Optional[Dict]

    final_decision: Dict

    outcome: Dict

    next_physical_state: Dict

    memory_size: int

    learning_message: str


# ============================================================
# 6. Simple state classification
# ============================================================

def classify_pressure(pressure: float) -> str:

    if pressure < 0.10:
        return "S0_Normal"

    elif pressure < 0.20:
        return "S1_Mild_stress"

    elif pressure < 0.35:
        return "S2_Disruption"

    elif pressure < 0.50:
        return "S3_Critical"

    return "S4_Severe"


# ============================================================
# 7. Operational pressure
# ============================================================

def calculate_operational_pressure(
    state: PhysicalSupplyChainState
) -> float:

    supply_loss = 1 - state.supply_availability
    transport_loss = 1 - state.transport_availability
    capacity_loss = 1 - state.processing_capacity
    quality_loss = 1 - state.quality_index

    demand_pressure = max(
        0,
        state.demand_level - 1
    )

    lead_time_pressure = max(
        0,
        state.lead_time_index - 1
    )

    pressure = (

        0.17 * supply_loss
        + 0.16 * transport_loss
        + 0.15 * capacity_loss
        + 0.07 * quality_loss

        + 0.10 * demand_pressure
        + 0.08 * lead_time_pressure

        + 0.18 * state.disruption_intensity
        + 0.09 * state.disruption_persistence
    )

    return float(
        np.clip(
            pressure,
            0,
            1
        )
    )


# ============================================================
# 8. Lightweight Algorithm 1 connector
# ============================================================

def run_predictive_layer(
    state: PhysicalSupplyChainState,
    previous_pressure: float,
    memory_level: float
) -> Dict:

    current_pressure = (
        calculate_operational_pressure(
            state
        )
    )

    trend = (
        current_pressure
        - previous_pressure
    )

    predicted_pressure = (

        0.55 * current_pressure

        + 0.15 * np.clip(
            current_pressure + trend,
            0,
            1
        )

        + 0.15
        * state.disruption_intensity

        + 0.10
        * state.disruption_persistence

        - 0.05
        * memory_level
    )

    predicted_pressure = float(
        np.clip(
            predicted_pressure,
            0,
            1
        )
    )

    prediction_confidence = (

        0.95

        - 0.60
        * abs(
            predicted_pressure
            - current_pressure
        )

        - 0.15
        * state.disruption_intensity
    )

    prediction_confidence = float(
        np.clip(
            prediction_confidence,
            0.20,
            0.99
        )
    )

    current_state = classify_pressure(
        current_pressure
    )

    predicted_state = classify_pressure(
        predicted_pressure
    )

    alerts = {

        "S0_Normal":
            "A0_Monitor",

        "S1_Mild_stress":
            "A1_Preventive_monitoring",

        "S2_Disruption":
            "A2_SCIS_pre_activation",

        "S3_Critical":
            "A3_SCIS_activation",

        "S4_Severe":
            "A4_Emergency_response"
    }

    trigger = (
        predicted_state
        in [
            "S2_Disruption",
            "S3_Critical",
            "S4_Severe"
        ]
    )

    return {

        "current_pressure":
            current_pressure,

        "predicted_pressure":
            predicted_pressure,

        "current_state":
            current_state,

        "predicted_state":
            predicted_state,

        "prediction_confidence":
            prediction_confidence,

        "alert_level":
            alerts[
                predicted_state
            ],

        "scis_trigger":
            trigger
    }


# ============================================================
# 9. Baseline planning
# ============================================================

def generate_baseline_decision(
    state: PhysicalSupplyChainState,
    predicted_pressure: float
) -> BaselineDecision:

    """
    Educational approximation of conventional planning.

    It reacts to current/predicted conditions but does not use
    adaptive memory or multiple future scenarios.
    """

    production_adjustment = float(
        np.clip(
            1 - 0.40 * predicted_pressure,
            0.55,
            1.00
        )
    )

    inventory_adjustment = float(
        np.clip(
            1 + 0.25 * predicted_pressure,
            1.00,
            1.25
        )
    )

    transport_adjustment = float(
        np.clip(
            1 + 0.20 * predicted_pressure,
            1.00,
            1.20
        )
    )

    sourcing_adjustment = float(
        np.clip(
            1 + 0.15 * predicted_pressure,
            1.00,
            1.15
        )
    )

    intervention_level = float(
        np.mean([
            abs(
                production_adjustment
                - 1
            ),
            inventory_adjustment - 1,
            transport_adjustment - 1,
            sourcing_adjustment - 1
        ])
    )

    expected_service = float(
        np.clip(
            state.service_level
            - 0.30 * predicted_pressure
            + 0.12 * intervention_level,
            0,
            1
        )
    )

    expected_profit = float(
        np.clip(
            state.profitability
            - 0.22 * predicted_pressure
            - 0.08 * intervention_level,
            0,
            1
        )
    )

    expected_viability = float(
        np.clip(
            0.55 * expected_service
            + 0.45 * expected_profit,
            0,
            1
        )
    )

    return BaselineDecision(

        production_adjustment=
            production_adjustment,

        inventory_adjustment=
            inventory_adjustment,

        transport_adjustment=
            transport_adjustment,

        sourcing_adjustment=
            sourcing_adjustment,

        intervention_level=
            intervention_level,

        expected_service_level=
            expected_service,

        expected_profitability=
            expected_profit,

        expected_viability=
            expected_viability
    )


# ============================================================
# 10. Educational Algorithm 2 connector
# ============================================================

def run_adaptive_memory_layer(
    prediction: Dict,
    state: PhysicalSupplyChainState,
    memory_repository: List[Dict],
    memory_level: float
) -> Dict:

    """
    Simplified connector equivalent to Didactic Algorithm 2.
    """

    similarities = []

    for episode in memory_repository:

        distance = (

            abs(
                prediction[
                    "predicted_pressure"
                ]
                - episode[
                    "pressure"
                ]
            )

            + abs(
                state.disruption_intensity
                - episode[
                    "disruption_intensity"
                ]
            )

            + abs(
                state.disruption_persistence
                - episode[
                    "persistence"
                ]
            )
        ) / 3

        similarity = float(
            np.clip(
                1 - distance,
                0,
                1
            )
        )

        similarities.append({

            **episode,

            "similarity":
                similarity
        })

    similarities = sorted(
        similarities,
        key=lambda x:
            x["similarity"],
        reverse=True
    )

    retrieved = similarities[:3]

    if retrieved:

        mean_similarity = np.mean([
            r["similarity"]
            for r in retrieved
        ])

        mean_success = np.mean([
            r["success"]
            for r in retrieved
        ])

    else:

        mean_similarity = 0.30
        mean_success = 0.50

    memory_after = (

        0.82 * memory_level

        + 0.10 * mean_similarity

        + 0.08 * mean_success
    )

    memory_after = float(
        np.clip(
            memory_after,
            0,
            1
        )
    )

    pressure = prediction[
        "predicted_pressure"
    ]

    target_layer = int(
        np.clip(
            round(
                pressure / 0.50 * 4
            ),
            0,
            4
        )
    )

    if retrieved:

        historical_layer = int(
            round(
                np.mean([
                    r["scis_layer"]
                    for r
                    in retrieved
                ])
            )
        )

        recommended_layer = int(
            round(
                0.60
                * target_layer
                + 0.40
                * historical_layer
            )
        )

    else:

        recommended_layer = (
            target_layer
        )

    recommended_layer = int(
        np.clip(
            recommended_layer,
            0,
            4
        )
    )

    decision_confidence = (

        0.45
        * prediction[
            "prediction_confidence"
        ]

        + 0.35
        * mean_similarity

        + 0.20
        * memory_after
    )

    decision_confidence = float(
        np.clip(
            decision_confidence,
            0,
            1
        )
    )

    return {

        "retrieved_episodes":
            retrieved,

        "memory_before":
            memory_level,

        "memory_after":
            memory_after,

        "recommended_scis_layer_code":
            recommended_layer,

        "decision_confidence":
            decision_confidence,

        "historical_similarity":
            float(
                mean_similarity
            )
    }


# ============================================================
# 11. Educational Algorithm 3 connector
# ============================================================

def run_scenario_layer(
    prediction: Dict,
    adaptive_policy: Dict,
    state: PhysicalSupplyChainState
) -> Dict:

    novelty = (

        0.40
        * state.disruption_intensity

        + 0.25
        * state.disruption_persistence

        + 0.20
        * (
            1
            - prediction[
                "prediction_confidence"
            ]
        )

        + 0.15
        * (
            1
            - adaptive_policy[
                "memory_after"
            ]
        )
    )

    novelty = float(
        np.clip(
            novelty,
            0,
            1
        )
    )

    robustness_budget = (

        0.35
        * prediction[
            "predicted_pressure"
        ]

        + 0.30
        * novelty

        + 0.20
        * (
            1
            - adaptive_policy[
                "decision_confidence"
            ]
        )

        + 0.15
        * (
            1
            - adaptive_policy[
                "memory_after"
            ]
        )
    )

    robustness_budget = float(
        np.clip(
            robustness_budget,
            0.05,
            1
        )
    )

    scenario_multipliers = {

        "Optimistic": 0.65,

        "Recovery": 0.80,

        "Dominant": 1.00,

        "Pessimistic": 1.25,

        "Worst_case":
            1.40
            + 0.30
            * robustness_budget
    }

    raw_probabilities = {

        "Optimistic":
            0.14
            * (
                1
                - 0.40
                * state
                .disruption_persistence
            ),

        "Recovery":
            0.16
            * (
                1
                - 0.35
                * state
                .disruption_persistence
            ),

        "Dominant":
            0.38
            * (
                0.70
                + 0.60
                * prediction[
                    "prediction_confidence"
                ]
            ),

        "Pessimistic":
            0.20
            * (
                0.80
                + 0.60
                * state
                .disruption_persistence
            ),

        "Worst_case":
            0.12
            * (
                0.70
                + 0.80
                * novelty
                + 0.40
                * state
                .disruption_persistence
            )
    }

    probability_total = sum(
        raw_probabilities.values()
    )

    scenarios = []

    for name, multiplier in (
        scenario_multipliers.items()
    ):

        pressure = float(
            np.clip(
                prediction[
                    "predicted_pressure"
                ]
                * multiplier,
                0,
                1
            )
        )

        probability = (
            raw_probabilities[name]
            / probability_total
        )

        scenarios.append({

            "scenario":
                name,

            "probability":
                float(probability),

            "pressure":
                pressure,

            "severity":
                classify_pressure(
                    pressure
                )
        })

    most_probable = max(
        scenarios,
        key=lambda x:
            x["probability"]
    )

    return {

        "novelty_score":
            novelty,

        "robustness_budget":
            robustness_budget,

        "scenarios":
            scenarios,

        "most_probable_scenario":
            most_probable[
                "scenario"
            ]
    }


# ============================================================
# 12. Adaptive decision generation
# ============================================================

def generate_adaptive_decision(
    state: PhysicalSupplyChainState,
    prediction: Dict,
    adaptive_policy: Dict,
    scenario_package: Dict
) -> AdaptiveOperationalDecision:

    layer = adaptive_policy[
        "recommended_scis_layer_code"
    ]

    robustness = scenario_package[
        "robustness_budget"
    ]

    # --------------------------------------------------------
    # Regulation intensity by SCIS layer
    # --------------------------------------------------------

    layer_strength = {
        0: 0.00,
        1: 0.15,
        2: 0.35,
        3: 0.65,
        4: 0.90
    }[layer]

    production_adjustment = float(
        np.clip(
            1
            - 0.20
            * prediction[
                "predicted_pressure"
            ]

            + 0.10
            * layer_strength,
            0.60,
            1.10
        )
    )

    inventory_adjustment = float(
        np.clip(
            1
            + 0.30
            * layer_strength
            + 0.15
            * robustness,
            1,
            1.50
        )
    )

    transport_adjustment = float(
        np.clip(
            1
            + 0.35
            * layer_strength
            + 0.20
            * robustness,
            1,
            1.60
        )
    )

    sourcing_adjustment = float(
        np.clip(
            1
            + 0.30
            * layer_strength
            + 0.15
            * robustness,
            1,
            1.50
        )
    )

    recovery_effort = float(
        np.clip(
            0.60
            * layer_strength
            + 0.40
            * robustness,
            0,
            1
        )
    )

    intervention_cost = (

        0.05
        * (inventory_adjustment - 1)

        + 0.07
        * (transport_adjustment - 1)

        + 0.06
        * (sourcing_adjustment - 1)

        + 0.08
        * recovery_effort
    )

    expected_service = float(
        np.clip(

            state.service_level

            - 0.32
            * prediction[
                "predicted_pressure"
            ]

            + 0.30
            * layer_strength

            + 0.18
            * robustness,

            0,
            1
        )
    )

    expected_profit = float(
        np.clip(

            state.profitability

            - 0.20
            * prediction[
                "predicted_pressure"
            ]

            + 0.14
            * layer_strength

            - intervention_cost,

            0,
            1
        )
    )

    expected_viability = float(
        np.clip(

            0.60
            * expected_service

            + 0.40
            * expected_profit,

            0,
            1
        )
    )

    layer_name = {

        0: "L0_No_SCIS",
        1: "L1_Monitoring",
        2: "L2_Pre_activation",
        3: "L3_Full_activation",
        4: "L4_Emergency_response"

    }[layer]

    return AdaptiveOperationalDecision(

        scis_layer=
            layer_name,

        scis_layer_code=
            layer,

        production_adjustment=
            production_adjustment,

        inventory_adjustment=
            inventory_adjustment,

        transport_adjustment=
            transport_adjustment,

        sourcing_adjustment=
            sourcing_adjustment,

        recovery_effort=
            recovery_effort,

        robustness_budget=
            robustness,

        expected_service_level=
            expected_service,

        expected_profitability=
            expected_profit,

        expected_viability=
            expected_viability,

        decision_source=
            "APDT_SCIS"
    )


# ============================================================
# 13. Convert baseline to final decision format
# ============================================================

def baseline_as_final_decision(
    baseline: BaselineDecision
) -> AdaptiveOperationalDecision:

    return AdaptiveOperationalDecision(

        scis_layer=
            "L0_Baseline_planning",

        scis_layer_code=
            0,

        production_adjustment=
            baseline.production_adjustment,

        inventory_adjustment=
            baseline.inventory_adjustment,

        transport_adjustment=
            baseline.transport_adjustment,

        sourcing_adjustment=
            baseline.sourcing_adjustment,

        recovery_effort=
            0.0,

        robustness_budget=
            0.0,

        expected_service_level=
            baseline.expected_service_level,

        expected_profitability=
            baseline.expected_profitability,

        expected_viability=
            baseline.expected_viability,

        decision_source=
            "Baseline"
    )


# ============================================================
# 14. Implement decision in physical system
# ============================================================

def implement_decision(
    state: PhysicalSupplyChainState,
    decision: AdaptiveOperationalDecision
) -> PhysicalSupplyChainState:

    """
    Educational transition model.

    The decision influences the next state of the physical
    supply chain.
    """

    regulatory_strength = (
        decision.scis_layer_code
        / 4
    )

    supply_next = float(
        np.clip(

            state.supply_availability

            + 0.06
            * (
                decision.sourcing_adjustment
                - 1
            )

            + 0.03
            * regulatory_strength

            - 0.08
            * state.disruption_intensity,

            0.05,
            1
        )
    )

    transport_next = float(
        np.clip(

            state.transport_availability

            + 0.08
            * (
                decision.transport_adjustment
                - 1
            )

            + 0.04
            * decision.recovery_effort

            - 0.10
            * state.disruption_intensity,

            0.05,
            1
        )
    )

    capacity_next = float(
        np.clip(

            state.processing_capacity

            + 0.04
            * regulatory_strength

            + 0.03
            * decision.recovery_effort

            - 0.07
            * state.disruption_intensity,

            0.05,
            1
        )
    )

    persistence_next = float(
        np.clip(

            state.disruption_persistence

            - 0.08
            * decision.recovery_effort,

            0,
            1
        )
    )

    disruption_next = float(
        np.clip(

            state.disruption_intensity

            - 0.04
            * decision.recovery_effort,

            0,
            1
        )
    )

    lead_time_next = float(
        np.clip(

            state.lead_time_index

            - 0.10
            * (
                decision.transport_adjustment
                - 1
            )

            - 0.05
            * decision.recovery_effort,

            0.50,
            2.50
        )
    )

    return PhysicalSupplyChainState(

        cycle=
            state.cycle + 1,

        supply_availability=
            supply_next,

        demand_level=
            state.demand_level,

        transport_availability=
            transport_next,

        processing_capacity=
            capacity_next,

        quality_index=
            state.quality_index,

        lead_time_index=
            lead_time_next,

        disruption_intensity=
            disruption_next,

        disruption_persistence=
            persistence_next,

        inventory_level=float(
            np.clip(

                state.inventory_level

                + 0.10
                * (
                    decision
                    .inventory_adjustment
                    - 1
                )

                - 0.05
                * state
                .disruption_intensity,

                0,
                1
            )
        ),

        service_level=
            decision
            .expected_service_level,

        profitability=
            decision
            .expected_profitability,

        viability=
            decision
            .expected_viability
    )


# ============================================================
# 15. Evaluate implemented outcome
# ============================================================

def evaluate_outcome(
    previous_state:
        PhysicalSupplyChainState,

    next_state:
        PhysicalSupplyChainState,

    decision:
        AdaptiveOperationalDecision
) -> CycleOutcome:

    viability_gain = (
        next_state.viability
        - previous_state.viability
    )

    service_gain = (
        next_state.service_level
        - previous_state.service_level
    )

    profitability_gain = (
        next_state.profitability
        - previous_state.profitability
    )

    intervention_cost = (

        0.04
        * abs(
            decision
            .production_adjustment
            - 1
        )

        + 0.05
        * abs(
            decision
            .inventory_adjustment
            - 1
        )

        + 0.06
        * abs(
            decision
            .transport_adjustment
            - 1
        )

        + 0.05
        * abs(
            decision
            .sourcing_adjustment
            - 1
        )

        + 0.08
        * decision
        .recovery_effort
    )

    # --------------------------------------------------------
    # Success balances viability improvement and intervention
    # --------------------------------------------------------

    success = (

        0.50
        * next_state.viability

        + 0.25
        * next_state.service_level

        + 0.15
        * next_state.profitability

        + 0.10
        * (
            1
            - min(
                intervention_cost,
                1
            )
        )
    )

    return CycleOutcome(

        viability_before=
            previous_state.viability,

        viability_after=
            next_state.viability,

        service_before=
            previous_state.service_level,

        service_after=
            next_state.service_level,

        profitability_before=
            previous_state.profitability,

        profitability_after=
            next_state.profitability,

        viability_gain=
            viability_gain,

        service_gain=
            service_gain,

        profitability_gain=
            profitability_gain,

        intervention_cost=
            float(
                intervention_cost
            ),

        decision_success=
            float(
                np.clip(
                    success,
                    0,
                    1
                )
            )
    )


# ============================================================
# 16. Store experience in adaptive memory
# ============================================================

def store_episode(
    memory_repository: List[Dict],
    prediction: Dict,
    state: PhysicalSupplyChainState,
    decision: AdaptiveOperationalDecision,
    outcome: CycleOutcome
) -> List[Dict]:

    episode = {

        "episode_id":
            str(
                uuid.uuid4()
            )[:8],

        "cycle":
            state.cycle,

        "pressure":
            prediction[
                "predicted_pressure"
            ],

        "disruption_intensity":
            state
            .disruption_intensity,

        "persistence":
            state
            .disruption_persistence,

        "scis_layer":
            decision
            .scis_layer_code,

        "viability_before":
            outcome
            .viability_before,

        "viability_after":
            outcome
            .viability_after,

        "service_after":
            outcome
            .service_after,

        "profitability_after":
            outcome
            .profitability_after,

        "success":
            outcome
            .decision_success,

        "decision_source":
            decision
            .decision_source
    }

    memory_repository.append(
        episode
    )

    return memory_repository


# ============================================================
# 17. Educational explanation
# ============================================================

def build_cycle_explanation(
    prediction: Dict,
    scis_triggered: bool,
    final_decision:
        AdaptiveOperationalDecision,
    outcome: CycleOutcome,
    scenario_package:
        Optional[Dict]
) -> str:

    if not scis_triggered:

        return (

            f"The Digital Twin predicted "
            f"{prediction['predicted_state']} "
            f"with operational pressure "
            f"{prediction['predicted_pressure']:.2f}. "
            f"Adaptive regulation was not required, "
            f"so the baseline operating plan was retained. "
            f"Resulting viability was "
            f"{outcome.viability_after:.2f}."
        )

    scenario_text = ""

    if scenario_package:

        scenario_text = (

            f"The most probable scenario was "
            f"{scenario_package['most_probable_scenario']}, "
            f"and the adaptive robustness budget was "
            f"{scenario_package['robustness_budget']:.2f}. "
        )

    return (

        f"The Digital Twin predicted "
        f"{prediction['predicted_state']} "
        f"with operational pressure "
        f"{prediction['predicted_pressure']:.2f}. "

        f"This activated "
        f"{final_decision.scis_layer}. "

        + scenario_text +

        f"After implementing the adaptive response, "
        f"viability changed from "
        f"{outcome.viability_before:.2f} "
        f"to {outcome.viability_after:.2f}. "
        f"The experience was stored in adaptive memory "
        f"for future decision cycles."
    )


# ============================================================
# 18. MAIN ALGORITHM 4
# ============================================================

def algorithm_4(
    physical_state:
        PhysicalSupplyChainState,

    memory_repository:
        List[Dict],

    previous_pressure:
        float = 0.0,

    memory_level:
        float = 0.0
) -> DigitalTwinCycleResult:

    # ========================================================
    # STEP 1
    # Observe and synchronize the physical supply chain
    # ========================================================

    current_state = (
        physical_state
    )

    # ========================================================
    # STEP 2
    # Algorithm 1 - predictive intelligence
    # ========================================================

    prediction = (
        run_predictive_layer(

            state=
                current_state,

            previous_pressure=
                previous_pressure,

            memory_level=
                memory_level
        )
    )

    # ========================================================
    # STEP 3
    # Generate baseline operating plan
    # ========================================================

    baseline = (
        generate_baseline_decision(

            state=
                current_state,

            predicted_pressure=
                prediction[
                    "predicted_pressure"
                ]
        )
    )

    # ========================================================
    # STEP 4
    # Evaluate SCIS trigger
    # ========================================================

    scis_triggered = (
        prediction[
            "scis_trigger"
        ]
    )

    adaptive_policy = None
    scenario_package = None

    # ========================================================
    # STEP 5A
    # No adaptive regulation required
    # ========================================================

    if not scis_triggered:

        final_decision = (
            baseline_as_final_decision(
                baseline
            )
        )

    # ========================================================
    # STEP 5B
    # Adaptive regulation required
    # ========================================================

    else:

        # ----------------------------------------------------
        # Algorithm 2
        # Adaptive memory and policy learning
        # ----------------------------------------------------

        adaptive_policy = (
            run_adaptive_memory_layer(

                prediction=
                    prediction,

                state=
                    current_state,

                memory_repository=
                    memory_repository,

                memory_level=
                    memory_level
            )
        )

        # ----------------------------------------------------
        # Algorithm 3
        # Dynamic scenario generation
        # ----------------------------------------------------

        scenario_package = (
            run_scenario_layer(

                prediction=
                    prediction,

                adaptive_policy=
                    adaptive_policy,

                state=
                    current_state
            )
        )

        # ----------------------------------------------------
        # Adaptive URSP-SCIS-like decision
        # ----------------------------------------------------

        final_decision = (
            generate_adaptive_decision(

                state=
                    current_state,

                prediction=
                    prediction,

                adaptive_policy=
                    adaptive_policy,

                scenario_package=
                    scenario_package
            )
        )

    # ========================================================
    # STEP 6
    # Implement selected decision
    # ========================================================

    next_state = (
        implement_decision(

            state=
                current_state,

            decision=
                final_decision
        )
    )

    # ========================================================
    # STEP 7
    # Evaluate real outcome
    # ========================================================

    outcome = (
        evaluate_outcome(

            previous_state=
                current_state,

            next_state=
                next_state,

            decision=
                final_decision
        )
    )

    # ========================================================
    # STEP 8
    # Store validated episode
    # ========================================================

    memory_repository = (
        store_episode(

            memory_repository=
                memory_repository,

            prediction=
                prediction,

            state=
                current_state,

            decision=
                final_decision,

            outcome=
                outcome
        )
    )

    # ========================================================
    # STEP 9
    # Generate explanation for student
    # ========================================================

    explanation = (
        build_cycle_explanation(

            prediction=
                prediction,

            scis_triggered=
                scis_triggered,

            final_decision=
                final_decision,

            outcome=
                outcome,

            scenario_package=
                scenario_package
        )
    )

    # ========================================================
    # STEP 10
    # Return complete Digital Twin cycle
    # ========================================================

    return DigitalTwinCycleResult(

        cycle=
            current_state.cycle,

        timestamp=
            datetime.utcnow()
            .isoformat(),

        operational_pressure=
            round(
                prediction[
                    "current_pressure"
                ],
                4
            ),

        predicted_pressure=
            round(
                prediction[
                    "predicted_pressure"
                ],
                4
            ),

        current_state=
            prediction[
                "current_state"
            ],

        predicted_state=
            prediction[
                "predicted_state"
            ],

        alert_level=
            prediction[
                "alert_level"
            ],

        scis_triggered=
            scis_triggered,

        baseline_decision=
            asdict(
                baseline
            ),

        adaptive_policy=
            adaptive_policy,

        scenario_package=
            scenario_package,

        final_decision=
            asdict(
                final_decision
            ),

        outcome=
            asdict(
                outcome
            ),

        next_physical_state=
            asdict(
                next_state
            ),

        memory_size=
            len(
                memory_repository
            ),

        learning_message=
            explanation
    )


# ============================================================
# 19. Example - one Digital Twin decision cycle
# ============================================================

if __name__ == "__main__":

    # --------------------------------------------------------
    # Initial physical supply chain
    # --------------------------------------------------------

    physical_state = (
        PhysicalSupplyChainState(

            cycle=1,

            supply_availability=0.86,
            demand_level=1.12,
            transport_availability=0.58,
            processing_capacity=0.90,

            quality_index=0.95,
            lead_time_index=1.28,

            disruption_intensity=0.58,
            disruption_persistence=0.55,

            inventory_level=0.68,
            service_level=0.84,
            profitability=0.76,
            viability=0.78
        )
    )

    # --------------------------------------------------------
    # Previous DT memory
    # --------------------------------------------------------

    memory_repository = [

        {
            "episode_id":
                "E001",

            "cycle":
                -3,

            "pressure":
                0.37,

            "disruption_intensity":
                0.65,

            "persistence":
                0.60,

            "scis_layer":
                3,

            "viability_before":
                0.44,

            "viability_after":
                0.71,

            "service_after":
                0.82,

            "profitability_after":
                0.69,

            "success":
                0.87,

            "decision_source":
                "Historical"
        },

        {
            "episode_id":
                "E002",

            "cycle":
                -2,

            "pressure":
                0.24,

            "disruption_intensity":
                0.42,

            "persistence":
                0.35,

            "scis_layer":
                2,

            "viability_before":
                0.62,

            "viability_after":
                0.78,

            "service_after":
                0.85,

            "profitability_after":
                0.73,

            "success":
                0.81,

            "decision_source":
                "Historical"
        }
    ]

    # --------------------------------------------------------
    # Run complete APDT cycle
    # --------------------------------------------------------

    result = (
        algorithm_4(

            physical_state=
                physical_state,

            memory_repository=
                memory_repository,

            previous_pressure=
                0.22,

            memory_level=
                0.42
        )
    )

    print(
        "\n============================================"
    )

    print(
        " DIGITAL TWIN DECISION CYCLE"
    )

    print(
        "============================================"
    )

    print(
        "Cycle:",
        result.cycle
    )

    print(
        "Current state:",
        result.current_state
    )

    print(
        "Predicted state:",
        result.predicted_state
    )

    print(
        "Operational pressure:",
        result.operational_pressure
    )

    print(
        "Predicted pressure:",
        result.predicted_pressure
    )

    print(
        "Alert:",
        result.alert_level
    )

    print(
        "SCIS triggered:",
        result.scis_triggered
    )

    print(
        "\nFinal decision:"
    )

    for key, value in (
        result.final_decision.items()
    ):

        print(
            key,
            ":",
            value
        )

    print(
        "\nOutcome:"
    )

    for key, value in (
        result.outcome.items()
    ):

        print(
            key,
            ":",
            value
        )

    print(
        "\nDT explanation:"
    )

    print(
        result.learning_message
    )