# ============================================================
# Algorithm 2 - Didactic Adaptive Memory and Policy Learning
# Web Learning Version v1.0
#
# Purpose:
#   Use historical disruption episodes to:
#   - retrieve similar experiences
#   - update adaptive memory
#   - evaluate possible SCIS responses
#   - recommend an adaptive policy
#   - explain why the recommendation was made
#
# Designed for:
#   FastAPI / Streamlit / Flask backend
#
# Input:
#   Output from Didactic Algorithm 1
#
# Output:
#   Adaptive memory state
#   Similar historical episodes
#   Recommended SCIS response
#   Decision confidence
#   Decision quality
#   Policy explanation
# ============================================================

from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
import numpy as np


# ============================================================
# 1. SCIS action space
# ============================================================

SCIS_ACTIONS = {
    0: "L0_No_SCIS",
    1: "L1_Monitoring",
    2: "L2_Pre_activation",
    3: "L3_Full_activation",
    4: "L4_Emergency_response"
}


ACTION_COST = {
    0: 0.00,
    1: 0.02,
    2: 0.07,
    3: 0.18,
    4: 0.36
}


# ============================================================
# 2. Historical episode
# ============================================================

@dataclass
class MemoryEpisode:

    episode_id: str

    disruption_type: str
    operational_pressure: float
    disruption_intensity: float
    disruption_persistence: float

    supply_availability: float
    transport_availability: float
    processing_capacity: float

    scis_layer_used: int

    viability_before: float
    viability_after: float

    service_level_after: float

    intervention_cost: float

    success_score: float


# ============================================================
# 3. Current decision state
# ============================================================

@dataclass
class AdaptiveDecisionState:

    predicted_pressure: float
    predicted_state: str

    prediction_confidence: float

    disruption_intensity: float
    disruption_persistence: float

    supply_availability: float
    transport_availability: float
    processing_capacity: float

    previous_memory: float


# ============================================================
# 4. Algorithm 2 output
# ============================================================

@dataclass
class AdaptivePolicyResult:

    retrieved_episodes: List[Dict]

    memory_before: float
    memory_after: float

    recommended_scis_layer: str
    recommended_scis_layer_code: int

    policy_score: float

    decision_confidence: float
    decision_quality: float

    expected_benefit: float
    intervention_cost: float
    expected_net_utility: float

    learning_message: str


# ============================================================
# 5. Episode descriptor
# ============================================================

def episode_vector(ep: MemoryEpisode) -> np.ndarray:

    return np.array([
        ep.operational_pressure,
        ep.disruption_intensity,
        ep.disruption_persistence,
        1 - ep.supply_availability,
        1 - ep.transport_availability,
        1 - ep.processing_capacity
    ], dtype=float)


def current_state_vector(state: AdaptiveDecisionState) -> np.ndarray:

    return np.array([
        state.predicted_pressure,
        state.disruption_intensity,
        state.disruption_persistence,
        1 - state.supply_availability,
        1 - state.transport_availability,
        1 - state.processing_capacity
    ], dtype=float)


# ============================================================
# 6. Similarity measure
# ============================================================

def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:

    denominator = np.linalg.norm(a) * np.linalg.norm(b)

    if denominator == 0:
        return 0.0

    return float(np.dot(a, b) / denominator)


# ============================================================
# 7. Retrieve similar experiences
# ============================================================

def retrieve_similar_episodes(
    current_state: AdaptiveDecisionState,
    memory_repository: List[MemoryEpisode],
    k: int = 3
) -> List[Dict]:

    query = current_state_vector(current_state)

    matches = []

    for episode in memory_repository:

        vector = episode_vector(episode)

        similarity = cosine_similarity(
            query,
            vector
        )

        usefulness = (
            0.45 * episode.success_score
            + 0.30 * episode.viability_after
            + 0.25 * episode.service_level_after
        )

        retrieval_score = (
            0.70 * similarity
            + 0.30 * usefulness
        )

        matches.append({
            "episode": episode,
            "similarity": similarity,
            "usefulness": usefulness,
            "retrieval_score": retrieval_score
        })

    matches = sorted(
        matches,
        key=lambda x: x["retrieval_score"],
        reverse=True
    )

    return matches[:k]


# ============================================================
# 8. Update adaptive memory
# ============================================================

def update_memory_stock(
    previous_memory: float,
    retrieved: List[Dict],
    current_pressure: float
) -> float:

    if not retrieved:
        return previous_memory

    mean_similarity = np.mean([
        r["similarity"]
        for r in retrieved
    ])

    mean_success = np.mean([
        r["episode"].success_score
        for r in retrieved
    ])

    # More severe situations reinforce useful memory.
    reinforcement = (
        0.40 * mean_similarity
        + 0.35 * mean_success
        + 0.25 * current_pressure
    )

    # Calm periods allow gradual forgetting.
    forgetting_rate = (
        0.03
        if current_pressure < 0.10
        else 0.01
    )

    memory_after = (
        (1 - forgetting_rate) * previous_memory
        + 0.18 * reinforcement
    )

    return float(
        np.clip(memory_after, 0, 1)
    )


# ============================================================
# 9. Evaluate candidate SCIS actions
# ============================================================

def evaluate_scis_actions(
    state: AdaptiveDecisionState,
    retrieved: List[Dict],
    memory_stock: float
) -> List[Dict]:

    if retrieved:

        historical_layer = np.average(
            [
                r["episode"].scis_layer_used
                for r in retrieved
            ],
            weights=[
                max(r["retrieval_score"], 0.001)
                for r in retrieved
            ]
        )

        historical_success = np.mean([
            r["episode"].success_score
            for r in retrieved
        ])

    else:

        historical_layer = 1
        historical_success = 0.50

    pressure_target = np.clip(
        state.predicted_pressure / 0.50 * 4,
        0,
        4
    )

    evaluations = []

    for layer in range(5):

        response_match = (
            1
            - abs(layer - pressure_target) / 4
        )

        memory_match = (
            1
            - abs(layer - historical_layer) / 4
        )

        expected_benefit = (
            0.35 * response_match
            + 0.25 * memory_match
            + 0.20 * historical_success
            + 0.10 * memory_stock
            + 0.10 * state.prediction_confidence
        )

        intervention_cost = ACTION_COST[layer]

        net_utility = (
            expected_benefit
            - intervention_cost
        )

        evaluations.append({
            "layer": layer,
            "action": SCIS_ACTIONS[layer],
            "expected_benefit":
                float(expected_benefit),
            "intervention_cost":
                intervention_cost,
            "net_utility":
                float(net_utility)
        })

    return evaluations


# ============================================================
# 10. Select adaptive policy
# ============================================================

def select_adaptive_policy(
    evaluations: List[Dict]
) -> Dict:

    return max(
        evaluations,
        key=lambda x: x["net_utility"]
    )


# ============================================================
# 11. Decision confidence
# ============================================================

def compute_decision_confidence(
    prediction_confidence: float,
    retrieved: List[Dict],
    memory_stock: float
) -> float:

    if retrieved:

        retrieval_confidence = np.mean([
            r["similarity"]
            for r in retrieved
        ])

    else:

        retrieval_confidence = 0.30

    confidence = (
        0.45 * prediction_confidence
        + 0.35 * retrieval_confidence
        + 0.20 * memory_stock
    )

    return float(
        np.clip(confidence, 0, 1)
    )


# ============================================================
# 12. Decision quality
# ============================================================

def compute_decision_quality(
    confidence: float,
    policy: Dict,
    memory_stock: float
) -> float:

    quality = (
        0.40 * confidence
        + 0.30 * policy["expected_benefit"]
        + 0.20 * memory_stock
        + 0.10 * (
            1 - policy["intervention_cost"]
        )
    )

    return float(
        np.clip(quality, 0, 1)
    )


# ============================================================
# 13. Learning explanation
# ============================================================

def generate_learning_message(
    retrieved: List[Dict],
    memory_before: float,
    memory_after: float,
    policy: Dict,
    decision_confidence: float
) -> str:

    if retrieved:

        best = retrieved[0]

        episode = best["episode"]

        similarity_pct = (
            best["similarity"] * 100
        )

        memory_text = (
            f"The Digital Twin retrieved episode "
            f"{episode.episode_id}, associated with "
            f"{episode.disruption_type}, with "
            f"{similarity_pct:.1f}% similarity."
        )

    else:

        memory_text = (
            "No sufficiently similar previous "
            "episode was available."
        )

    if memory_after > memory_before:

        memory_change = (
            "Adaptive memory was reinforced because "
            "the current situation resembles useful "
            "previous disruption experiences."
        )

    else:

        memory_change = (
            "Adaptive memory remained stable because "
            "the current operating condition provides "
            "limited new information."
        )

    policy_text = (
        f"The recommended response is "
        f"{policy['action']}. "
        f"Its expected benefit is "
        f"{policy['expected_benefit']:.2f}, "
        f"with an intervention cost of "
        f"{policy['intervention_cost']:.2f}. "
        f"Decision confidence is "
        f"{decision_confidence:.1%}."
    )

    return (
        memory_text
        + " "
        + memory_change
        + " "
        + policy_text
    )


# ============================================================
# 14. Main Algorithm 2
# ============================================================

def algorithm_2(
    state: AdaptiveDecisionState,
    memory_repository: List[MemoryEpisode],
    k: int = 3
) -> AdaptivePolicyResult:

    # --------------------------------------------------------
    # Step 1 - Retrieve similar disruption experiences
    # --------------------------------------------------------

    retrieved = retrieve_similar_episodes(
        current_state=state,
        memory_repository=memory_repository,
        k=k
    )

    # --------------------------------------------------------
    # Step 2 - Update adaptive memory
    # --------------------------------------------------------

    memory_before = state.previous_memory

    memory_after = update_memory_stock(
        previous_memory=memory_before,
        retrieved=retrieved,
        current_pressure=state.predicted_pressure
    )

    # --------------------------------------------------------
    # Step 3 - Evaluate possible SCIS responses
    # --------------------------------------------------------

    evaluations = evaluate_scis_actions(
        state=state,
        retrieved=retrieved,
        memory_stock=memory_after
    )

    # --------------------------------------------------------
    # Step 4 - Select adaptive response
    # --------------------------------------------------------

    policy = select_adaptive_policy(
        evaluations
    )

    # --------------------------------------------------------
    # Step 5 - Estimate decision confidence
    # --------------------------------------------------------

    decision_confidence = compute_decision_confidence(
        prediction_confidence=
            state.prediction_confidence,

        retrieved=retrieved,

        memory_stock=memory_after
    )

    # --------------------------------------------------------
    # Step 6 - Estimate decision quality
    # --------------------------------------------------------

    decision_quality = compute_decision_quality(
        confidence=decision_confidence,
        policy=policy,
        memory_stock=memory_after
    )

    # --------------------------------------------------------
    # Step 7 - Explain decision
    # --------------------------------------------------------

    learning_message = generate_learning_message(
        retrieved=retrieved,
        memory_before=memory_before,
        memory_after=memory_after,
        policy=policy,
        decision_confidence=
            decision_confidence
    )

    # --------------------------------------------------------
    # Step 8 - Prepare retrieved episodes for frontend
    # --------------------------------------------------------

    retrieved_frontend = []

    for item in retrieved:

        ep = item["episode"]

        retrieved_frontend.append({

            "episode_id":
                ep.episode_id,

            "disruption_type":
                ep.disruption_type,

            "similarity":
                round(
                    item["similarity"],
                    4
                ),

            "success_score":
                round(
                    ep.success_score,
                    4
                ),

            "previous_scis_response":
                SCIS_ACTIONS[
                    ep.scis_layer_used
                ],

            "viability_after":
                round(
                    ep.viability_after,
                    4
                )
        })

    return AdaptivePolicyResult(

        retrieved_episodes=
            retrieved_frontend,

        memory_before=
            round(memory_before, 4),

        memory_after=
            round(memory_after, 4),

        recommended_scis_layer=
            policy["action"],

        recommended_scis_layer_code=
            policy["layer"],

        policy_score=
            round(
                policy["net_utility"],
                4
            ),

        decision_confidence=
            round(
                decision_confidence,
                4
            ),

        decision_quality=
            round(
                decision_quality,
                4
            ),

        expected_benefit=
            round(
                policy["expected_benefit"],
                4
            ),

        intervention_cost=
            round(
                policy[
                    "intervention_cost"
                ],
                4
            ),

        expected_net_utility=
            round(
                policy[
                    "net_utility"
                ],
                4
            ),

        learning_message=
            learning_message
    )


# ============================================================
# 15. Example memory repository
# ============================================================

if __name__ == "__main__":

    memory_repository = [

        MemoryEpisode(
            episode_id="E001",
            disruption_type=
                "Transportation strike",

            operational_pressure=0.38,
            disruption_intensity=0.70,
            disruption_persistence=0.60,

            supply_availability=0.90,
            transport_availability=0.45,
            processing_capacity=0.92,

            scis_layer_used=3,

            viability_before=0.42,
            viability_after=0.72,

            service_level_after=0.83,

            intervention_cost=0.18,

            success_score=0.88
        ),

        MemoryEpisode(
            episode_id="E002",
            disruption_type=
                "Water scarcity",

            operational_pressure=0.27,
            disruption_intensity=0.45,
            disruption_persistence=0.80,

            supply_availability=0.78,
            transport_availability=0.92,
            processing_capacity=0.75,

            scis_layer_used=2,

            viability_before=0.55,
            viability_after=0.74,

            service_level_after=0.87,

            intervention_cost=0.07,

            success_score=0.82
        ),

        MemoryEpisode(
            episode_id="E003",
            disruption_type=
                "Local road restriction",

            operational_pressure=0.19,
            disruption_intensity=0.32,
            disruption_persistence=0.25,

            supply_availability=0.96,
            transport_availability=0.72,
            processing_capacity=0.95,

            scis_layer_used=1,

            viability_before=0.78,
            viability_after=0.86,

            service_level_after=0.92,

            intervention_cost=0.02,

            success_score=0.79
        )
    ]

    current_state = AdaptiveDecisionState(

        predicted_pressure=0.34,
        predicted_state="S2_Disruption",

        prediction_confidence=0.86,

        disruption_intensity=0.58,
        disruption_persistence=0.55,

        supply_availability=0.87,
        transport_availability=0.54,
        processing_capacity=0.91,

        previous_memory=0.40
    )

    result = algorithm_2(
        current_state,
        memory_repository
    )

    print("\nADAPTIVE MEMORY AND POLICY")
    print("--------------------------")

    for key, value in asdict(result).items():
        print(key, ":", value)