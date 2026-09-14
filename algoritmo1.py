# ============================================================
# Algorithm 1 - Didactic Predictive Digital Twin
# Web Learning Version v1.0
#
# Purpose:
#   Convert observable supply-chain conditions into:
#   - Operational Pressure Index
#   - Predicted next operating state
#   - Prediction confidence
#   - Alert level
#   - SCIS activation recommendation
#   - Adaptive parameter vector
#   - Human-readable learning explanation
#
# Designed for:
#   FastAPI / Streamlit / Flask / React backend
# ============================================================

from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
import numpy as np


# ============================================================
# 1. Operational states
# ============================================================

STATE_ORDER = [
    "S0_Normal",
    "S1_Mild_stress",
    "S2_Disruption",
    "S3_Critical",
    "S4_Severe"
]

STATE_BOUNDS = {
    "S0_Normal": (0.00, 0.10),
    "S1_Mild_stress": (0.10, 0.20),
    "S2_Disruption": (0.20, 0.35),
    "S3_Critical": (0.35, 0.50),
    "S4_Severe": (0.50, 1.00)
}


def state_from_pressure(pressure: float) -> str:
    """Translate operational pressure into a DT state."""

    if pressure < 0.10:
        return "S0_Normal"
    elif pressure < 0.20:
        return "S1_Mild_stress"
    elif pressure < 0.35:
        return "S2_Disruption"
    elif pressure < 0.50:
        return "S3_Critical"

    return "S4_Severe"


def alert_from_state(state: str) -> str:
    return {
        "S0_Normal": "A0_Monitor",
        "S1_Mild_stress": "A1_Preventive_monitoring",
        "S2_Disruption": "A2_SCIS_pre_activation",
        "S3_Critical": "A3_SCIS_activation",
        "S4_Severe": "A4_Emergency_response"
    }[state]


def scis_layer_from_state(state: str) -> str:
    return {
        "S0_Normal": "L0_No_SCIS",
        "S1_Mild_stress": "L1_Monitoring",
        "S2_Disruption": "L2_Pre_activation",
        "S3_Critical": "L3_Full_activation",
        "S4_Severe": "L4_Emergency_response"
    }[state]


# ============================================================
# 2. Input data model
# ============================================================

@dataclass
class SupplyChainObservation:

    supply_availability: float = 1.0
    demand_level: float = 1.0
    transport_availability: float = 1.0
    processing_capacity: float = 1.0
    quality_index: float = 1.0
    lead_time_index: float = 1.0

    disruption_intensity: float = 0.0
    disruption_persistence: float = 0.0

    previous_pressure: float = 0.0
    previous_memory: float = 0.0


# ============================================================
# 3. Output data model
# ============================================================

@dataclass
class DigitalTwinPrediction:

    current_pressure: float
    predicted_pressure: float

    current_state: str
    predicted_state: str

    prediction_confidence: float

    alert_level: str
    scis_layer: str
    scis_activation_signal: int

    adaptive_parameters: Dict[str, float]

    main_pressure_drivers: List[Dict]
    learning_message: str


# ============================================================
# 4. Operational pressure calculation
# ============================================================

def compute_operational_pressure(obs: SupplyChainObservation) -> float:
    """
    Educational Operational Pressure Index.

    Higher values represent greater degradation.
    All input indexes should normally be between 0 and 1.
    """

    supply_loss = 1 - np.clip(obs.supply_availability, 0, 1)
    transport_loss = 1 - np.clip(obs.transport_availability, 0, 1)
    capacity_loss = 1 - np.clip(obs.processing_capacity, 0, 1)
    quality_loss = 1 - np.clip(obs.quality_index, 0, 1)

    demand_pressure = np.clip(obs.demand_level - 1, 0, 1)
    lead_time_pressure = np.clip(obs.lead_time_index - 1, 0, 1)

    disruption = np.clip(obs.disruption_intensity, 0, 1)
    persistence = np.clip(obs.disruption_persistence, 0, 1)

    pressure = (
        0.18 * supply_loss
        + 0.15 * transport_loss
        + 0.15 * capacity_loss
        + 0.08 * quality_loss
        + 0.10 * demand_pressure
        + 0.08 * lead_time_pressure
        + 0.18 * disruption
        + 0.08 * persistence
    )

    return float(np.clip(pressure, 0, 1))


# ============================================================
# 5. Predict next operating pressure
# ============================================================

def predict_next_pressure(
    current_pressure: float,
    previous_pressure: float,
    disruption_intensity: float,
    persistence: float,
    memory_level: float
) -> float:

    """
    Lightweight educational approximation of the predictive
    mechanism used in the research APDT.

    For production use this function can be replaced by the
    trained ML model from Algorithm 1 of the paper.
    """

    trend = current_pressure - previous_pressure

    predicted = (
        0.55 * current_pressure
        + 0.15 * np.clip(current_pressure + trend, 0, 1)
        + 0.15 * disruption_intensity
        + 0.10 * persistence
        - 0.05 * memory_level
    )

    return float(np.clip(predicted, 0, 1))


# ============================================================
# 6. Prediction confidence
# ============================================================

def compute_prediction_confidence(
    current_pressure: float,
    predicted_pressure: float,
    disruption_intensity: float
) -> float:

    """
    Confidence decreases when abrupt changes are expected.
    """

    transition = abs(predicted_pressure - current_pressure)

    confidence = (
        0.95
        - 0.65 * transition
        - 0.15 * disruption_intensity
    )

    return float(np.clip(confidence, 0.20, 0.99))


# ============================================================
# 7. SCIS adaptive parameters
# ============================================================

def estimate_scis_parameters(
    pressure: float,
    memory_level: float,
    confidence: float
) -> Dict[str, float]:

    rho_R = np.clip(
        0.35 + 1.25 * pressure,
        0.35,
        1.85
    )

    lambda_M = np.clip(
        0.13
        - 0.02 * pressure
        + 0.01 * memory_level,
        0.075,
        0.135
    )

    phi_M = np.clip(
        0.12
        + 0.085 * pressure
        + 0.02 * memory_level,
        0.12,
        0.22
    )

    gamma_M = np.clip(
        0.045
        + 0.025 * pressure
        + 0.01 * (1 - confidence),
        0.045,
        0.08
    )

    return {
        "rho_R": round(float(rho_R), 4),
        "lambda_M": round(float(lambda_M), 4),
        "phi_M": round(float(phi_M), 4),
        "gamma_M": round(float(gamma_M), 4)
    }


# ============================================================
# 8. Identify main pressure drivers
# ============================================================

def identify_pressure_drivers(
    obs: SupplyChainObservation
) -> List[Dict]:

    drivers = {
        "Supply shortage":
            1 - obs.supply_availability,

        "Transport restriction":
            1 - obs.transport_availability,

        "Processing capacity loss":
            1 - obs.processing_capacity,

        "Quality deterioration":
            1 - obs.quality_index,

        "Demand pressure":
            max(0, obs.demand_level - 1),

        "Lead-time deterioration":
            max(0, obs.lead_time_index - 1),

        "Disruption intensity":
            obs.disruption_intensity,

        "Disruption persistence":
            obs.disruption_persistence
    }

    ordered = sorted(
        drivers.items(),
        key=lambda x: x[1],
        reverse=True
    )

    return [
        {
            "driver": name,
            "intensity": round(float(value), 3)
        }
        for name, value in ordered[:3]
    ]


# ============================================================
# 9. Educational explanation
# ============================================================

def generate_learning_message(
    current_state: str,
    predicted_state: str,
    confidence: float,
    scis_layer: str,
    drivers: List[Dict]
) -> str:

    main_driver = drivers[0]["driver"]

    if current_state == predicted_state:

        transition_text = (
            f"The Digital Twin expects the supply chain to remain "
            f"in {predicted_state}."
        )

    else:

        transition_text = (
            f"The Digital Twin detects a transition from "
            f"{current_state} to {predicted_state}."
        )

    return (
        f"{transition_text} "
        f"The main source of operational pressure is "
        f"{main_driver}. "
        f"Prediction confidence is {confidence:.1%}. "
        f"The recommended immune-inspired response is "
        f"{scis_layer}."
    )


# ============================================================
# 10. Main Algorithm 1
# ============================================================

def algorithm_1(
    observation: SupplyChainObservation
) -> DigitalTwinPrediction:

    # Step 1 — observe physical supply chain
    current_pressure = compute_operational_pressure(
        observation
    )

    current_state = state_from_pressure(
        current_pressure
    )

    # Step 2 — predict next operating state
    predicted_pressure = predict_next_pressure(
        current_pressure=current_pressure,
        previous_pressure=observation.previous_pressure,
        disruption_intensity=observation.disruption_intensity,
        persistence=observation.disruption_persistence,
        memory_level=observation.previous_memory
    )

    predicted_state = state_from_pressure(
        predicted_pressure
    )

    # Step 3 — assess prediction confidence
    prediction_confidence = compute_prediction_confidence(
        current_pressure=current_pressure,
        predicted_pressure=predicted_pressure,
        disruption_intensity=observation.disruption_intensity
    )

    # Step 4 — generate adaptive alert
    alert_level = alert_from_state(
        predicted_state
    )

    # Step 5 — determine SCIS layer
    scis_layer = scis_layer_from_state(
        predicted_state
    )

    activation_signal = (
        1
        if predicted_state in [
            "S2_Disruption",
            "S3_Critical",
            "S4_Severe"
        ]
        else 0
    )

    # Step 6 — adaptive parameter estimation
    adaptive_parameters = estimate_scis_parameters(
        pressure=predicted_pressure,
        memory_level=observation.previous_memory,
        confidence=prediction_confidence
    )

    # Step 7 — explain the DT reasoning
    drivers = identify_pressure_drivers(
        observation
    )

    learning_message = generate_learning_message(
        current_state=current_state,
        predicted_state=predicted_state,
        confidence=prediction_confidence,
        scis_layer=scis_layer,
        drivers=drivers
    )

    return DigitalTwinPrediction(

        current_pressure=round(
            current_pressure, 4
        ),

        predicted_pressure=round(
            predicted_pressure, 4
        ),

        current_state=current_state,
        predicted_state=predicted_state,

        prediction_confidence=round(
            prediction_confidence, 4
        ),

        alert_level=alert_level,
        scis_layer=scis_layer,
        scis_activation_signal=activation_signal,

        adaptive_parameters=adaptive_parameters,
        main_pressure_drivers=drivers,
        learning_message=learning_message
    )


# ============================================================
# 11. Example
# ============================================================

if __name__ == "__main__":

    scenario = SupplyChainObservation(

        supply_availability=0.82,
        demand_level=1.12,
        transport_availability=0.65,
        processing_capacity=0.90,
        quality_index=0.94,
        lead_time_index=1.35,

        disruption_intensity=0.55,
        disruption_persistence=0.40,

        previous_pressure=0.18,
        previous_memory=0.35
    )

    result = algorithm_1(scenario)

    print("\nDIGITAL TWIN STATE")
    print("-------------------")

    for key, value in asdict(result).items():
        print(key, ":", value)