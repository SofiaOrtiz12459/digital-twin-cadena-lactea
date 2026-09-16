import copy
import streamlit as st
import pandas as pd

# El optimizador pesado se importa SOLO cuando el usuario entra
# a la página de Diseño y optimización. Así el Dashboard arranca rápido.
OPTIMIZER_AVAILABLE = None

def load_optimizer():
    global OPTIMIZER_AVAILABLE
    try:
        from modelo_ursp_scis import OptimizerData, solve_model, scenario_table
        OPTIMIZER_AVAILABLE = True
        return OptimizerData, solve_model, scenario_table
    except Exception as exc:
        OPTIMIZER_AVAILABLE = False
        return None, None, exc

from algoritmo1 import SupplyChainObservation, algorithm_1
from algoritmo2 import AdaptiveDecisionState, MemoryEpisode, algorithm_2
from algoritmo3 import PredictiveState, AdaptivePolicyState, algorithm_3
from algoritmo4 import PhysicalSupplyChainState, algorithm_4

st.set_page_config(
    page_title="Digital Twin — Cadena Láctea",
    page_icon="🌐",
    layout="wide"
)

# ============================================================
# CONFIGURACIÓN
# ============================================================

SCENARIO_DEFAULTS = {
    "Operación normal": {
        "supply": 0.82, "demand": 1.12, "transport": 0.85,
        "processing": 0.90, "quality": 0.94, "lead": 1.00,
        "intensity": 0.10, "persistence": 0.10
    },
    "Huelga de transporte": {
        "supply": 0.82, "demand": 1.12, "transport": 0.45,
        "processing": 0.90, "quality": 0.94, "lead": 1.45,
        "intensity": 0.70, "persistence": 0.60
    },
    "Escasez de agua": {
        "supply": 0.78, "demand": 1.10, "transport": 0.90,
        "processing": 0.65, "quality": 0.90, "lead": 1.25,
        "intensity": 0.45, "persistence": 0.80
    },
    "Restricción vial": {
        "supply": 0.95, "demand": 1.05, "transport": 0.65,
        "processing": 0.95, "quality": 0.94, "lead": 1.35,
        "intensity": 0.32, "persistence": 0.25
    },
    "Fallo de planta": {
        "supply": 0.80, "demand": 1.15, "transport": 0.90,
        "processing": 0.45, "quality": 0.88, "lead": 1.50,
        "intensity": 0.75, "persistence": 0.55
    },
    "Personalizado": {
        "supply": 0.82, "demand": 1.12, "transport": 0.65,
        "processing": 0.90, "quality": 0.94, "lead": 1.35,
        "intensity": 0.55, "persistence": 0.40
    }
}

BASE_MEMORY_A2 = [
    MemoryEpisode("E001", "Huelga de transporte", 0.38, 0.70, 0.60, 0.90, 0.45, 0.92, 3, 0.42, 0.72, 0.83, 0.18, 0.88),
    MemoryEpisode("E002", "Escasez de agua", 0.27, 0.45, 0.80, 0.78, 0.92, 0.75, 2, 0.55, 0.74, 0.87, 0.07, 0.82),
    MemoryEpisode("E003", "Restricción vial", 0.19, 0.32, 0.25, 0.96, 0.72, 0.95, 1, 0.78, 0.86, 0.92, 0.02, 0.79)
]

BASE_MEMORY_A4 = [
    {"episode_id": "E001", "pressure": 0.38, "disruption_intensity": 0.70, "persistence": 0.60, "scis_layer": 3, "success": 0.88},
    {"episode_id": "E002", "pressure": 0.27, "disruption_intensity": 0.45, "persistence": 0.80, "scis_layer": 2, "success": 0.82},
    {"episode_id": "E003", "pressure": 0.19, "disruption_intensity": 0.32, "persistence": 0.25, "scis_layer": 1, "success": 0.79}
]


def reset_state():
    d = SCENARIO_DEFAULTS["Operación normal"].copy()
    st.session_state.cycle = 1
    st.session_state.previous_pressure = 0.18
    st.session_state.memory_level = 0.35
    st.session_state.physical = d
    st.session_state.history = []
    st.session_state.last_package = None
    st.session_state.what_if_package = None
    st.session_state.scenario_name = "Operación normal"


if "cycle" not in st.session_state:
    reset_state()
if "memory_repository_a2" not in st.session_state:
    st.session_state.memory_repository_a2 = copy.deepcopy(BASE_MEMORY_A2)
if "memory_repository_a4" not in st.session_state:
    st.session_state.memory_repository_a4 = copy.deepcopy(BASE_MEMORY_A4)

# ============================================================
# FUNCIONES DE CÁLCULO
# ============================================================

def execute_cycle(current, cycle_number, previous_pressure, memory_level, memory_a2, memory_a4, scenario):
    """Ejecuta A1→A2→A3→A4 sin modificar session_state."""
    observation = SupplyChainObservation(
        supply_availability=current["supply"],
        demand_level=current["demand"],
        transport_availability=current["transport"],
        processing_capacity=current["processing"],
        quality_index=current["quality"],
        lead_time_index=current["lead"],
        disruption_intensity=current["intensity"],
        disruption_persistence=current["persistence"],
        previous_pressure=previous_pressure,
        previous_memory=memory_level
    )
    result1 = algorithm_1(observation)

    current_state = AdaptiveDecisionState(
        predicted_pressure=result1.predicted_pressure,
        predicted_state=result1.predicted_state,
        prediction_confidence=result1.prediction_confidence,
        disruption_intensity=current["intensity"],
        disruption_persistence=current["persistence"],
        supply_availability=current["supply"],
        transport_availability=current["transport"],
        processing_capacity=current["processing"],
        previous_memory=memory_level
    )
    result2 = algorithm_2(current_state, memory_a2)

    scis_text = str(result2.recommended_scis_layer)
    scis_code = 4 if "L4" in scis_text else 3 if "L3" in scis_text else 2 if "L2" in scis_text else 1 if "L1" in scis_text else 0

    predictive_state = PredictiveState(
        predicted_pressure=result1.predicted_pressure,
        predicted_state=result1.predicted_state,
        prediction_confidence=result1.prediction_confidence,
        supply_availability=current["supply"],
        demand_level=current["demand"],
        transport_availability=current["transport"],
        processing_capacity=current["processing"],
        quality_index=current["quality"],
        lead_time_index=current["lead"],
        disruption_intensity=current["intensity"],
        disruption_persistence=current["persistence"]
    )
    adaptive_policy_state = AdaptivePolicyState(
        memory_after=result2.memory_after,
        recommended_scis_layer_code=scis_code,
        policy_score=result2.expected_net_utility,
        decision_confidence=result2.decision_confidence,
        decision_quality=result2.decision_quality,
        expected_net_utility=result2.expected_net_utility
    )
    result3 = algorithm_3(predictive_state, adaptive_policy_state)

    physical_state = PhysicalSupplyChainState(
        cycle=cycle_number,
        supply_availability=current["supply"],
        demand_level=current["demand"],
        transport_availability=current["transport"],
        processing_capacity=current["processing"],
        quality_index=current["quality"],
        lead_time_index=current["lead"],
        disruption_intensity=current["intensity"],
        disruption_persistence=current["persistence"],
        inventory_level=0.70,
        service_level=0.90,
        profitability=0.75,
        viability=0.80
    )
    result4 = algorithm_4(
        physical_state=physical_state,
        memory_repository=memory_a4,
        previous_pressure=previous_pressure,
        memory_level=memory_level
    )

    return {
        "cycle": cycle_number,
        "scenario": scenario,
        "input": current.copy(),
        "a1": result1,
        "a2": result2,
        "a3": result3,
        "a4": result4
    }


def next_physical_from_package(package):
    current = package["input"]
    ns = package["a4"].next_physical_state
    return {
        "supply": float(ns.get("supply_availability", current["supply"])),
        "demand": float(ns.get("demand_level", current["demand"])),
        "transport": float(ns.get("transport_availability", current["transport"])),
        "processing": float(ns.get("processing_capacity", current["processing"])),
        "quality": float(ns.get("quality_index", current["quality"])),
        "lead": float(ns.get("lead_time_index", current["lead"])),
        "intensity": float(ns.get("disruption_intensity", current["intensity"])),
        "persistence": float(ns.get("disruption_persistence", current["persistence"]))
    }


def commit_package(package):
    """Guarda el ciclo y prepara el siguiente estado."""
    r2, r4 = package["a2"], package["a4"]
    current = package["input"]
    st.session_state.last_package = package
    st.session_state.history.append(package)
    st.session_state.physical = next_physical_from_package(package)
    st.session_state.previous_pressure = float(r4.predicted_pressure)
    st.session_state.memory_level = float(r2.memory_after)

    success = float(r4.outcome.get("decision_success", 0.0))
    if success >= 0.50:
        ep_id = f"C{package['cycle']:02d}"
        st.session_state.memory_repository_a4.append({
            "episode_id": ep_id,
            "pressure": float(r4.operational_pressure),
            "disruption_intensity": current["intensity"],
            "persistence": current["persistence"],
            "scis_layer": int(r4.final_decision.get("scis_layer_code", 0)),
            "success": success
        })
        st.session_state.memory_repository_a2.append(MemoryEpisode(
            episode_id=ep_id,
            disruption_type=package["scenario"],
            operational_pressure=float(r4.operational_pressure),
            disruption_intensity=current["intensity"],
            disruption_persistence=current["persistence"],
            supply_availability=current["supply"],
            transport_availability=current["transport"],
            processing_capacity=current["processing"],
            scis_layer_used=int(r4.final_decision.get("scis_layer_code", 0)),
            viability_before=float(r4.outcome.get("viability_before", 0.0)),
            viability_after=float(r4.outcome.get("viability_after", 0.0)),
            service_level_after=float(r4.outcome.get("service_after", 0.0)),
            intervention_cost=float(r4.outcome.get("intervention_cost", 0.0)),
            success_score=success
        ))
    st.session_state.cycle += 1



def calculate_lean_indicators(current, outcome=None):
    """Indicadores Lean didácticos (proxies) a partir de las variables del modelo.
    No modifican A1-A4; sirven para visualizar desperdicios en la interfaz.
    Escala 0-1: 0 = bajo desperdicio, 1 = alto desperdicio.
    """
    waiting = max(0.0, min(1.0, (current["lead"] - 0.50) / 2.00))
    transport = max(0.0, min(1.0, 1.0 - current["transport"]))
    processing = max(0.0, min(1.0, 1.0 - current["processing"]))
    defects = max(0.0, min(1.0, 1.0 - current["quality"]))
    overproduction = max(0.0, min(1.0, current["supply"] - min(current["demand"], 1.0)))
    accumulation = max(0.0, min(1.0, max(0.0, current["supply"] - min(current["demand"], 1.0)) * 0.9 + max(0.0, current["lead"] - 1.0) * 0.1))

    values = {
        "Esperas": waiting,
        "Transporte": transport,
        "Inventario / acumulación": accumulation,
        "Sobreproducción": overproduction,
        "Procesamiento": processing,
        "Defectos / calidad": defects,
    }
    return values


def lean_level(value):
    if value < 0.33:
        return "🟢 Bajo"
    if value < 0.66:
        return "🟡 Medio"
    return "🔴 Alto"


def generate_lean_diagnosis(current, lean_values, lean_avg, previous_lean=None):
    """Genera un diagnóstico automático del desperdicio LEAN."""
    dominant_waste = max(lean_values, key=lean_values.get)
    dominant_value = lean_values[dominant_waste]

    if lean_avg < 0.33:
        level = "🟢 Bajo"
    elif lean_avg < 0.66:
        level = "🟡 Medio"
    else:
        level = "🔴 Alto"

    diagnoses = {
        "Esperas": (
            "El Lead Time es elevado y genera tiempos de espera dentro de la cadena.",
            "Puede retrasar la entrega de productos lácteos y aumentar la presión operativa.",
            "Reducir el Lead Time, mejorar la coordinación de procesos y evaluar una intervención adaptativa."
        ),
        "Transporte": (
            "La disponibilidad de transporte es insuficiente.",
            "Puede generar retrasos en la recolección, distribución y entrega del producto lácteo.",
            "Fortalecer la disponibilidad de transporte, optimizar rutas y evaluar una respuesta adaptativa."
        ),
        "Inventario / acumulación": (
            "Existe una desalineación entre suministro, demanda y tiempos de operación.",
            "Puede producir acumulación de producto, costos adicionales y riesgo de deterioro.",
            "Ajustar inventario y sincronizar suministro, producción y demanda."
        ),
        "Sobreproducción": (
            "El suministro disponible supera las necesidades inmediatas de la demanda.",
            "Puede provocar producción innecesaria, acumulación y mayores costos operativos.",
            "Alinear la producción con la demanda y utilizar la predicción del Digital Twin para ajustar la operación."
        ),
        "Procesamiento": (
            "La capacidad de procesamiento disponible es limitada.",
            "Puede generar cuellos de botella y aumentar la presión sobre la planta.",
            "Fortalecer la capacidad de procesamiento y priorizar recursos en los puntos críticos."
        ),
        "Defectos / calidad": (
            "El índice de calidad presenta un nivel inferior al óptimo.",
            "Puede generar reprocesos, pérdidas de producto y disminución del nivel de servicio.",
            "Fortalecer el control de calidad y prevenir las causas que generan producto no conforme."
        )
    }

    cause, effect, recommendation = diagnoses.get(
        dominant_waste,
        (
            "Se presentan condiciones operativas que incrementan el desperdicio.",
            "Estas condiciones pueden afectar el desempeño general de la cadena.",
            "Analizar las variables críticas y aplicar una decisión adaptativa."
        )
    )

    trend = None
    if previous_lean is not None:
        difference = lean_avg - previous_lean
        if difference <= -0.03:
            trend = "🟢 El desperdicio está disminuyendo respecto al ciclo anterior."
        elif difference >= 0.03:
            trend = "🔴 El desperdicio está aumentando respecto al ciclo anterior."
        else:
            trend = "🟡 El desperdicio se mantiene relativamente estable."

    return {
        "dominant_waste": dominant_waste,
        "dominant_value": dominant_value,
        "level": level,
        "cause": cause,
        "effect": effect,
        "recommendation": recommendation,
        "trend": trend
    }


def run_cycle():
    package = execute_cycle(
        st.session_state.physical,
        st.session_state.cycle,
        st.session_state.previous_pressure,
        st.session_state.memory_level,
        st.session_state.memory_repository_a2,
        st.session_state.memory_repository_a4,
        st.session_state.scenario_name
    )
    commit_package(package)


# ============================================================
# INTERFAZ — DISEÑO TIPO LEARNING LAB
# ============================================================

st.markdown("""
<style>
:root { --navy:#08264a; --blue:#1769aa; --light:#f5f8fc; --line:#dbe4ef; }
/* Compatibilidad visual: fuerza tema claro y contraste estable en cualquier equipo */
html, body, [data-testid="stAppViewContainer"], .stApp {
    color-scheme: light !important;
    color: #172033 !important;
}
[data-testid="stAppViewContainer"] { background: #f4f7fb !important; }
[data-testid="stMain"], [data-testid="stMainBlockContainer"] { color: #172033 !important; }

/* Texto general del contenido principal */
[data-testid="stAppViewContainer"] p,
[data-testid="stAppViewContainer"] label,
[data-testid="stAppViewContainer"] h1,
[data-testid="stAppViewContainer"] h2,
[data-testid="stAppViewContainer"] h3,
[data-testid="stAppViewContainer"] h4,
[data-testid="stAppViewContainer"] h5,
[data-testid="stAppViewContainer"] h6,
[data-testid="stAppViewContainer"] li,
[data-testid="stAppViewContainer"] span { color: #172033; }

/* Componentes con fondo claro */
.card, .top-strip, .kpi, .lean-box { color:#172033 !important; }
.card *, .top-strip *, .kpi *, .lean-box * { color: inherit; }
.card-sub, .small-muted, .kpi-label, .kpi-note { color:#64748b !important; }
.explain, .explain * { color:#17324d !important; }
.pill, .pill * { color:#174a7e !important; }

/* Header oscuro: mantener texto blanco */
.lab-header, .lab-header *, .sidebar-brand, .sidebar-brand * { color:white !important; }

/* Inputs, selects y number inputs: siempre legibles */
[data-baseweb="select"] > div,
[data-baseweb="input"] > div,
[data-testid="stNumberInput"] input,
[data-testid="stTextInput"] input {
    background-color:#ffffff !important;
    color:#172033 !important;
}
[data-baseweb="select"] *, [data-baseweb="input"] * { color:#172033 !important; }
ul[role="listbox"], ul[role="listbox"] li, [role="option"] {
    background-color:#ffffff !important;
    color:#172033 !important;
}

/* Métricas */
[data-testid="stMetric"] { color:#172033 !important; }
[data-testid="stMetricLabel"] *, [data-testid="stMetricValue"] * { color:#172033 !important; }

/* Tablas y dataframes */
[data-testid="stDataFrame"], [data-testid="stTable"] { color:#172033 !important; }

/* Sidebar permanece oscuro aunque el sistema use tema claro u oscuro */
[data-testid="stSidebar"] { background:#071f3d !important; }
[data-testid="stSidebar"] * { color:#eef5ff !important; }

/* Botones secundarios legibles; el primario conserva el color de Streamlit */
[data-testid="stBaseButton-secondary"] { background:#ffffff !important; color:#172033 !important; border-color:#cbd5e1 !important; }
[data-testid="stBaseButton-secondary"] * { color:#172033 !important; }

.stApp { background: #f4f7fb; }
.block-container { padding-top: 1rem; max-width: 1500px; }
.lab-header { background: linear-gradient(135deg,#062447,#0d3d6d); color:white; padding:20px 24px; border-radius:18px; box-shadow:0 8px 24px rgba(8,38,74,.18); margin-bottom:14px; }
.lab-title {font-size:1.65rem;font-weight:800;margin:0;}
.lab-subtitle {font-size:.88rem;opacity:.86;margin-top:3px;}
.top-strip {background:white;border:1px solid var(--line);border-radius:14px;padding:8px 10px;margin-bottom:14px;box-shadow:0 2px 10px rgba(30,60,90,.05);}
.step-row {display:grid;grid-template-columns:repeat(6,1fr);gap:6px;}
.step {padding:9px 6px;text-align:center;border-radius:10px;font-weight:700;font-size:.82rem;background:#edf3f9;border:1px solid #e2e9f2;}
.step:nth-child(1){border-top:4px solid #3b82f6}.step:nth-child(2){border-top:4px solid #22c55e}.step:nth-child(3){border-top:4px solid #8b5cf6}.step:nth-child(4){border-top:4px solid #f59e0b}.step:nth-child(5){border-top:4px solid #ef4444}.step:nth-child(6){border-top:4px solid #16a34a}
.card {background:white;border:1px solid var(--line);border-radius:15px;padding:15px 16px;margin-bottom:12px;box-shadow:0 2px 10px rgba(30,60,90,.045);}
.card-title {font-weight:800;font-size:1.02rem;margin-bottom:8px;}
.card-sub {color:#64748b;font-size:.78rem;margin-bottom:8px;}
.kpi {background:white;border:1px solid var(--line);border-radius:13px;padding:10px 12px;min-height:80px;box-shadow:0 2px 8px rgba(30,60,90,.04);}
.kpi-label {color:#64748b;font-size:.72rem}.kpi-value{font-size:1.25rem;font-weight:800;margin-top:2px}.kpi-note{font-size:.68rem;color:#64748b}
.pill {display:inline-block;padding:4px 9px;border-radius:999px;background:#eef5ff;color:#174a7e;font-size:.73rem;font-weight:700;border:1px solid #d8e7f8;}
.explain {background:#eef6ff;border:1px solid #d8e8fa;border-radius:11px;padding:10px 12px;font-size:.82rem;}
.lean-box {background:#fbfdfb;border:1px solid #dfe9e1;border-radius:12px;padding:10px;}
.sidebar-brand {background:#08264a;color:white;border-radius:12px;padding:12px;margin-bottom:12px;font-weight:800;}
.small-muted {color:#64748b;font-size:.75rem;}
[data-testid="stSidebar"] {background:#071f3d;}
[data-testid="stSidebar"] * {color:#eef5ff;}
[data-testid="stSidebar"] .stRadio label {font-size:.88rem;}
[data-testid="stSidebar"] hr {border-color:rgba(255,255,255,.16);}
</style>
""", unsafe_allow_html=True)

# ---------- Sidebar ----------
with st.sidebar:
    st.markdown('<div class="sidebar-brand">🌐 Supply Chain<br>Digital Twin Learning Lab<div style="font-size:.68rem;font-weight:400;opacity:.8;margin-top:4px">Cadena de suministro láctea</div></div>', unsafe_allow_html=True)
    page = st.radio("NAVEGACIÓN", ["Dashboard", "Diseño y optimización", "Transporte y logística", "Escenarios", "Laboratorio DT", "Comparación", "Historial de ciclos", "Lecciones", "Glossary"], index=0)
    st.divider()
    st.markdown("**INDICADORES CLAVE (APDT)**")
    last = st.session_state.get("last_package")
    if last is None:
        sidebar_kpis = [("Viabilidad actual","—"),("Nivel de servicio","—"),("Utilidad esperada","—"),("CVaR","—"),("Presión operacional","—"),("Confianza A1","—"),("Memoria adaptativa",f"{st.session_state.memory_level:.2f}"),("Nivel SCIS","—")]
    else:
        rr1, rr2, rr3, rr4 = last["a1"], last["a2"], last["a3"], last["a4"]
        sidebar_kpis = [
            ("Viabilidad actual",f"{rr4.outcome.get('viability_after',0):.2f}"),
            ("Nivel de servicio",f"{rr4.outcome.get('service_after',0):.2f}"),
            ("Utilidad esperada",f"{rr2.expected_net_utility:.2f}"),
            ("CVaR",f"{rr3.worst_case_probability:.2f}"),
            ("Presión operacional",f"{rr1.current_pressure:.2f}"),
            ("Confianza A1",f"{rr1.prediction_confidence:.2f}"),
            ("Memoria adaptativa",f"{rr2.memory_after:.2f}"),
            ("Nivel SCIS",str(rr4.final_decision.get('scis_layer','L0')))
        ]
    for label, value in sidebar_kpis:
        st.markdown(f'<div style="margin:5px 0"><div class="small-muted">{label}</div><b>{value}</b></div>', unsafe_allow_html=True)
    st.divider()
    if st.button("🔄 Reiniciar experimento", use_container_width=True):
        reset_state()
        st.session_state.memory_repository_a2 = copy.deepcopy(BASE_MEMORY_A2)
        st.session_state.memory_repository_a4 = copy.deepcopy(BASE_MEMORY_A4)
        st.session_state.what_if_package = None
        st.rerun()
    st.caption("Modelo didáctico · A1–A4 · SCIS · LEAN")

# ---------- Header / controls ----------
st.markdown('<div class="lab-header"><div class="lab-title">Supply Chain Digital Twin Learning Lab</div><div class="lab-subtitle">Aprende, experimenta y decide con un Digital Twin Adaptativo</div></div>', unsafe_allow_html=True)

hc1, hc2, hc3, hc4 = st.columns([1.35, .55, 1.1, .85])
with hc1:
    scenario_options = list(SCENARIO_DEFAULTS.keys())
    scenario_name = st.selectbox("Escenario actual", scenario_options, index=scenario_options.index(st.session_state.scenario_name), key="header_scenario")
with hc2:
    st.metric("Ciclo actual", f"{max(1, st.session_state.cycle-1)} / 20")
with hc3:
    horizon = st.selectbox("Horizonte", ["1 ciclo","5 ciclos","10 ciclos","20 ciclos"], key="header_horizon")
with hc4:
    mode = st.selectbox("Modo de aprendizaje", ["Guiado","Laboratorio","Comparación"], key="header_mode")

if scenario_name != st.session_state.scenario_name:
    st.session_state.scenario_name = scenario_name
    st.session_state.physical = SCENARIO_DEFAULTS[scenario_name].copy()
    st.session_state.cycle = 1
    st.session_state.previous_pressure = 0.18
    st.session_state.memory_level = 0.35
    st.session_state.history = []
    st.session_state.last_package = None
    st.session_state.memory_repository_a2 = copy.deepcopy(BASE_MEMORY_A2)
    st.session_state.memory_repository_a4 = copy.deepcopy(BASE_MEMORY_A4)
    st.session_state.what_if_package = None
    st.rerun()

b1,b2,b3 = st.columns([1.15,1.15,2.2])
with b1:
    ejecutar = st.button("▶ Ejecutar siguiente ciclo", type="primary", use_container_width=True)
with b2:
    ejecutar_horizonte = st.button("⏩ Ejecutar horizonte", use_container_width=True)
with b3:
    st.markdown(f'<div class="explain">Modo <b>{mode}</b> · Escenario <b>{st.session_state.scenario_name}</b> · Próximo ciclo <b>{st.session_state.cycle}</b></div>', unsafe_allow_html=True)

if ejecutar_horizonte:
    n = int(horizon.split()[0])
    for _ in range(n): run_cycle()
    st.rerun()
if ejecutar:
    run_cycle()
    st.rerun()

# ---------- Flow ----------
st.markdown('<div class="top-strip"><div class="step-row"><div class="step">1<br>Observar</div><div class="step">2<br>Predecir</div><div class="step">3<br>Recordar</div><div class="step">4<br>Imaginar futuros</div><div class="step">5<br>Decidir</div><div class="step">6<br>Aprender</div></div></div>', unsafe_allow_html=True)

package = st.session_state.last_package

# ============================================================
# VISTAS
# ============================================================

def lean_pack(pkg):
    vals = calculate_lean_indicators(pkg["input"], pkg["a4"].outcome)
    avg = sum(vals.values())/len(vals)
    prev = None
    if len(st.session_state.history) >= 2:
        old = st.session_state.history[-2]
        pv = calculate_lean_indicators(old["input"])
        prev = sum(pv.values())/len(pv)
    return vals, avg, prev


def render_physical():
    st.markdown('<div class="card-title">🔵 Estado físico de la cadena</div><div class="card-sub">Condiciones observadas en el ciclo actual</div>', unsafe_allow_html=True)
    p = st.session_state.physical
    c1,c2 = st.columns(2)
    with c1:
        p["supply"] = st.slider("Disponibilidad de suministro",.05,1.,float(p["supply"]),.01,key="supply_main")
        p["demand"] = st.slider("Nivel de demanda",.50,2.,float(p["demand"]),.01,key="demand_main")
        p["transport"] = st.slider("Disponibilidad de transporte",.05,1.,float(p["transport"]),.01,key="transport_main")
        p["processing"] = st.slider("Capacidad de procesamiento",.05,1.,float(p["processing"]),.01,key="processing_main")
    with c2:
        p["quality"] = st.slider("Índice de calidad",.50,1.,float(p["quality"]),.01,key="quality_main")
        p["lead"] = st.slider("Índice de Lead Time",.50,2.50,float(p["lead"]),.01,key="lead_main")
        p["intensity"] = st.slider("Intensidad de la disrupción",0.,1.,float(p["intensity"]),.01,key="intensity_main")
        p["persistence"] = st.slider("Persistencia de la disrupción",0.,1.,float(p["persistence"]),.01,key="persistence_main")
    a,b,c,d,e = st.columns(5)
    a.metric("Suministro",f"{p['supply']:.0%}")
    b.metric("Demanda",f"{p['demand']:.0%}")
    c.metric("Transporte",f"{p['transport']:.0%}")
    d.metric("Calidad",f"{p['quality']:.0%}")
    e.metric("Disrupción",f"{p['intensity']:.0%}")


def render_a1(r1):
    st.markdown('<div class="card-title">🟢 Predicción del Digital Twin (Alg. 1)</div>', unsafe_allow_html=True)
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Presión actual",f"{r1.current_pressure:.2f}")
    c2.metric("Presión predicha",f"{r1.predicted_pressure:.2f}",delta=f"{r1.predicted_pressure-r1.current_pressure:+.2f}")
    c3.metric("Confianza",f"{r1.prediction_confidence:.1%}")
    c4.metric("Estado predicho",str(r1.predicted_state))
    st.progress(min(1,max(0,float(r1.prediction_confidence))))
    st.caption(f"Alerta: {r1.alert_level} · SCIS: {r1.scis_layer}")


def render_a2(r2):
    st.markdown('<div class="card-title">🟣 Memoria adaptativa (Alg. 2)</div>', unsafe_allow_html=True)
    c1,c2,c3 = st.columns(3)
    c1.metric("Memoria antes",f"{r2.memory_before:.2f}")
    c2.metric("Memoria después",f"{r2.memory_after:.2f}",delta=f"{r2.memory_after-r2.memory_before:+.2f}")
    c3.metric("Confianza",f"{r2.decision_confidence:.1%}")
    st.success(f"SCIS recomendado: {r2.recommended_scis_layer}")
    st.caption(f"Experiencias recuperadas: {len(r2.retrieved_episodes)} · Utilidad neta esperada: {r2.expected_net_utility:.2f}")


def render_selectable_chart(data, key, height=240, default="Barras"):
    """Permite cambiar solo la visualización sin alterar datos ni cálculos."""
    options = ["Barras", "Línea", "Área"]
    idx = options.index(default) if default in options else 0
    chart_type = st.selectbox("Tipo de gráfica", options, index=idx, key=f"chart_type_{key}")
    if chart_type == "Línea":
        st.line_chart(data, height=height)
    elif chart_type == "Área":
        st.area_chart(data, height=height)
    else:
        st.bar_chart(data, height=height)


def render_a3(r3):
    st.markdown('<div class="card-title">🟠 Escenarios y futuros (Alg. 3)</div>', unsafe_allow_html=True)
    c1,c2,c3 = st.columns(3)
    c1.metric("Riesgo dominante",str(r3.dominant_risk))
    c2.metric("Robustez",f"{r3.robustness_budget:.1%}")
    c3.metric("Escenarios",str(len(r3.scenarios)))
    rows=[]
    for s in r3.scenarios:
        rows.append({"Escenario":s["scenario_name"],"Probabilidad":s["probability"]})
    sdf=pd.DataFrame(rows)
    render_selectable_chart(sdf.set_index("Escenario"), "a3_scenarios", height=180)
    st.caption(f"Más probable: {r3.most_probable_scenario} · Worst-case: {r3.worst_case_probability:.1%}")


def render_a4(r4):
    fd=r4.final_decision; bl=r4.baseline_decision; o=r4.outcome
    st.markdown('<div class="card-title">🔴 Decisión y regulación (Alg. 4)</div>', unsafe_allow_html=True)
    c1,c2 = st.columns(2)
    with c1:
        st.markdown("**Baseline**")
        st.metric("Intervención",f"{bl.get('intervention_level',0):.1%}")
        st.write(f"Producción {bl.get('production_adjustment',0):+.1%} · Inventario {bl.get('inventory_adjustment',0):+.1%}")
        st.write(f"Transporte {bl.get('transport_adjustment',0):+.1%} · Abastecimiento {bl.get('sourcing_adjustment',0):+.1%}")
    with c2:
        st.markdown("**APDT / Digital Twin**")
        st.metric("Capa SCIS",fd.get("scis_layer","L0_No_SCIS"))
        st.write(f"Producción {fd.get('production_adjustment',0):+.1%} · Inventario {fd.get('inventory_adjustment',0):+.1%}")
        st.write(f"Transporte {fd.get('transport_adjustment',0):+.1%} · Recuperación {fd.get('recovery_effort',0):.1%}")
    x1,x2,x3,x4=st.columns(4)
    x1.metric("Viabilidad",f"{o.get('viability_after',0):.1%}")
    x2.metric("Servicio",f"{o.get('service_after',0):.1%}")
    x3.metric("Rentabilidad",f"{o.get('profitability_after',0):.1%}")
    x4.metric("Éxito",f"{o.get('decision_success',0):.1%}")


def render_lean(pkg):
    vals,avg,prev=lean_pack(pkg)
    diag=generate_lean_diagnosis(pkg["input"],vals,avg,prev)
    st.markdown('<div class="card-title">♻️ Desperdicio LEAN y aprendizaje</div>', unsafe_allow_html=True)
    c1,c2,c3=st.columns(3)
    c1.metric("Índice global LEAN",f"{avg:.1%}")
    c2.metric("Desperdicio dominante",diag["dominant_waste"])
    c3.metric("Nivel",diag["level"])
    ldf=pd.DataFrame({"Desperdicio":list(vals.keys()),"Nivel":list(vals.values())})
    render_selectable_chart(ldf.set_index("Desperdicio"), "lean_waste", height=220)
    cols=st.columns(3)
    for i,(name,val) in enumerate(vals.items()):
        with cols[i%3]:
            st.markdown(f"**{name}** · {val:.1%}")
            st.progress(val)
    st.markdown(f'<div class="explain"><b>Interpretación:</b> {diag["cause"]}<br><b>Recomendación:</b> {diag["recommendation"]}</div>', unsafe_allow_html=True)
    action_map={
        "Esperas":"Reducir Lead Time y reforzar coordinación/transporte.",
        "Transporte":"Optimizar disponibilidad, rutas y recuperación.",
        "Inventario / acumulación":"Sincronizar inventario, suministro y demanda.",
        "Sobreproducción":"Ajustar producción a la demanda prevista.",
        "Procesamiento":"Priorizar capacidad en puntos críticos.",
        "Defectos / calidad":"Fortalecer control de calidad y recuperación."
    }
    st.info(f"🔗 **LEAN → A4:** {action_map.get(diag['dominant_waste'],'Revisar variables críticas y aplicar decisión adaptativa.')}")
    return vals,avg,diag


def render_transport_optimizer(result):
    """Visualiza los resultados físicos y económicos del optimizador URSP–SCIS."""
    scenarios = result.get("scenario", {})
    if not scenarios:
        st.info("Ejecuta primero la optimización URSP–SCIS para obtener los resultados de transporte.")
        return

    total_p = sum(float(v.get("probability", 0.0)) for v in scenarios.values()) or 1.0

    exp_pcd = sum(float(v.get("probability",0.0))*float(v.get("trips_plant_cd",0.0)) for v in scenarios.values()) / total_p
    exp_cdc = sum(float(v.get("probability",0.0))*float(v.get("trips_cd_market",0.0)) for v in scenarios.values()) / total_p
    exp_ship = sum(float(v.get("probability",0.0))*float(v.get("shipment",0.0)) for v in scenarios.values()) / total_p
    exp_service = sum(float(v.get("probability",0.0))*float(v.get("service_level",0.0)) for v in scenarios.values()) / total_p
    min_avail = min(float(v.get("gams_logistics_min",1.0)) for v in scenarios.values())
    exp_hato = sum(float(v.get("probability",0.0))*float(v.get("trips_farm_plant",0.0)) for v in scenarios.values()) / total_p
    exp_inter = sum(float(v.get("probability",0.0))*float(v.get("trips_interplant",0.0)) for v in scenarios.values()) / total_p
    exp_cost = sum(float(v.get("probability",0.0))*float(v.get("transport_cost_gams",0.0)) for v in scenarios.values()) / total_p

    st.markdown("#### 🚚 Transporte y logística — resultados URSP–SCIS integrado")
    st.caption("Flujo físico modelado: Hatos → Plantas ↔ Plantas → Centros de Distribución → n1/n2/n3.")

    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("Viajes Hato → Planta", f"{exp_hato:,.0f}")
    c2.metric("Viajes interplanta", f"{exp_inter:,.0f}")
    c3.metric("Viajes Planta → CD", f"{exp_pcd:,.0f}")
    c4.metric("Viajes CD → n1/n2/n3", f"{exp_cdc:,.0f}")
    c5.metric("Servicio logístico", f"{exp_service:.1%}")
    d1,d2,d3 = st.columns(3)
    d1.metric("Producto entregado", f"{exp_ship:,.0f}")
    d2.metric("Disponibilidad mínima", f"{min_avail:.1%}")
    d3.metric("Costo transporte GAMS", f"${exp_cost:,.0f}")

    rows = []
    for s,v in scenarios.items():
        demand = float(v.get("demand_total",0.0))
        shortage = float(v.get("shortage",0.0))
        pcd = float(v.get("trips_plant_cd",0.0))
        cdc = float(v.get("trips_cd_market",0.0))
        delivered = float(v.get("shipment",0.0))
        availability = float(v.get("gams_logistics_min",1.0))
        transport_waste = max(0.0, min(1.0, 1.0 - availability))
        rows.append({
            "Escenario": s,
            "Probabilidad": float(v.get("probability",0.0)),
            "Demanda": demand,
            "Entregado": delivered,
            "Faltante": shortage,
            "Servicio": float(v.get("service_level",0.0)),
            "Viajes Planta → CD": pcd,
            "Viajes CD → Mercado": cdc,
            "AvailCDC mínima": availability,
            "Desperdicio Lean transporte": transport_waste,
        })

    tdf = pd.DataFrame(rows)
    st.dataframe(
        tdf.style.format({
            "Probabilidad":"{:.1%}",
            "Demanda":"{:,.0f}",
            "Entregado":"{:,.0f}",
            "Faltante":"{:,.0f}",
            "Servicio":"{:.1%}",
            "Viajes Planta → CD":"{:,.0f}",
            "Viajes CD → Mercado":"{:,.0f}",
            "AvailCDC mínima":"{:.1%}",
            "Desperdicio Lean transporte":"{:.1%}",
        }),
        use_container_width=True,
        hide_index=True
    )

    chart = tdf.set_index("Escenario")[["Viajes Planta → CD","Viajes CD → Mercado"]]
    render_selectable_chart(chart, "transport_trips", height=260)

    worst = min(rows, key=lambda r: r["AvailCDC mínima"])
    if worst["AvailCDC mínima"] < 0.70:
        st.warning(
            f"🟠 El escenario {worst['Escenario']} presenta la menor disponibilidad logística "
            f"({worst['AvailCDC mínima']:.1%}). Esto puede elevar viajes requeridos, faltantes, "
            "esperas y desperdicio Lean asociado al transporte."
        )
    else:
        st.success("🟢 La disponibilidad logística se mantiene en un rango operativo favorable en los escenarios evaluados.")

    st.markdown(
        '<div class="explain"><b>Conexión LEAN:</b> cuando disminuye AvailCDC, la red tiene menos '
        'capacidad efectiva para movilizar producto. El Digital Twin permite observar el efecto '
        'sobre viajes, entregas, faltantes y nivel de servicio antes de aplicar una decisión.</div>',
        unsafe_allow_html=True
    )



if page == "Diseño y optimización":
    st.markdown("### 🧩 Diseño y optimización URSP–SCIS")
    st.markdown("<div class=\"explain\"><b>Flujo:</b> PARAMETRIZAR → FIJAR → GENERAR ESCENARIOS → OPTIMIZAR → SIMULAR → ANALIZAR EFECTOS</div>", unsafe_allow_html=True)

    with st.spinner("Cargando módulo URSP–SCIS..."):
        OptimizerData, solve_model, scenario_table = load_optimizer()

    if not OPTIMIZER_AVAILABLE:
        st.error(f"No fue posible cargar el optimizador: {scenario_table}")
        st.stop()

    if "optimizer_data" not in st.session_state:
        st.session_state.optimizer_data = OptimizerData.from_gams_defaults()
    if "optimizer_base_demand" not in st.session_state:
        st.session_state.optimizer_base_demand = dict(st.session_state.optimizer_data.demand)
    od = st.session_state.optimizer_data

    st.markdown("#### 1. Parametrizar la cadena")
    c1,c2,c3 = st.columns(3)
    with c1:
        demand_factor = st.slider("Demanda global", 0.60, 1.50, 1.00, 0.05)
        od.capacity_per_plant = st.number_input("Capacidad por planta", min_value=1000., max_value=200000., value=float(od.capacity_per_plant), step=1000.)
    with c2:
        od.eps_y = st.slider("Tolerancia homeostática (eps_y)", 0.01, 0.30, float(od.eps_y), 0.01)
        od.theta = st.slider("Umbral de viabilidad (theta)", 0.40, 0.95, float(od.theta), 0.01)
    with c3:
        od.rhoR = st.slider("Aversión al riesgo (rhoR)", 0.0, 5.0, float(od.rhoR), 0.1)
        od.alpha = st.slider("Confianza CVaR (alpha)", 0.50, 0.95, float(od.alpha), 0.01)

    od.demand = {k:v*demand_factor for k,v in st.session_state.optimizer_base_demand.items()}

    st.markdown("#### 2. Fijar diseño")
    d1,d2=st.columns(2)
    with d1:
        st.write("**Plantas activas**")
        plant_choices=[]
        for j in ["j1","j2","j3"]:
            if st.checkbox(j, value=True, key=f"opt_{j}"):
                plant_choices.append(j)
    with d2:
        st.write("**Centros de distribución activos**")
        cd_choices=[]
        for k in ["k1","k2","k3","k4"]:
            if st.checkbox(k, value=k in ["k1","k2","k3"], key=f"opt_{k}"):
                cd_choices.append(k)

    # v29: los costos fijos permanecen iguales a los del GAMS.
    # Las casillas ya no "apagan" instalaciones haciendo su costo cero.
    od.fixed_plants = {"j1":12200000.,"j2":12000000.,"j3":12000000.}
    od.fixed_cds = {"k1":5500000.,"k2":5000000.,"k3":5200000.,"k4":5350000.}

    # Fijación matemática real de las binarias del optimizador v29.
    # Marcada = 1 (activa); desmarcada = 0 (cerrada).
    od.plant_design_status = {
        j: (1 if j in plant_choices else 0) for j in ["j1","j2","j3"]
    }
    od.cd_design_status = {
        k: (1 if k in cd_choices else 0) for k in ["k1","k2","k3","k4"]
    }

    st.caption(
        "🔒 Diseño fijado: las casillas obligan directamente YP y YCD a 1/0 "
        "en el modelo matemático; los costos fijos GAMS no se modifican."
    )

    st.markdown("#### 3. Generar escenarios")
    probs = st.columns(5)
    for idx,s in enumerate(["s1","s2","s3","s4","s5"]):
        od.probabilities[s] = probs[idx].number_input(s, min_value=0.0, max_value=1.0, value=float(od.probabilities[s]), step=0.05, key=f"prob_{s}")
    total_p=sum(od.probabilities.values())
    st.caption(f"Suma de probabilidades: {total_p:.2f} — se normalizan automáticamente antes de resolver.")

    st.markdown("#### 4. Simular y optimizar")
    if st.button("🚀 EJECUTAR OPTIMIZACIÓN URSP–SCIS", type="primary", use_container_width=True):
        with st.spinner("Resolviendo el MILP URSP–SCIS..."):
            try:
                st.session_state.optimizer_result = solve_model(od)
            except Exception as exc:
                st.session_state.optimizer_result = None
                st.error(f"No fue posible resolver el modelo: {exc}")

    result = st.session_state.get("optimizer_result")
    if result:
        st.markdown("#### 5. Resultados y efectos")

        # Estado de terminación del solver HiGHS.
        solver_status = str(result.get("termination", result.get("solver_status", "No disponible")))
        time_limit = result.get("solver_time_limit", None)
        mip_gap = result.get("solver_mip_rel_gap", None)
        optimal = bool(result.get("solution_optimal", solver_status.lower() == "optimal"))
        hit_limit = bool(result.get("time_limit_reached", "maxtimelimit" in solver_status.lower().replace(" ", "")))

        if optimal:
            st.success(f"✅ Estado del solver: {solver_status} — solución óptima.")
        elif hit_limit:
            st.warning(
                f"⏱️ Estado del solver: {solver_status}. "
                "HiGHS alcanzó el límite de tiempo; se muestra la mejor solución factible disponible."
            )
        else:
            st.info(f"ℹ️ Estado del solver: {solver_status}")

        sc1, sc2 = st.columns(2)
        sc1.metric("Tiempo máximo del solver", f"{float(time_limit):.0f} s" if time_limit is not None else "—")
        sc2.metric("Gap MIP configurado", f"{100*float(mip_gap):.1f}%" if mip_gap is not None else "—")

        # Diagnóstico estructural del MILP.
        # Diagnóstico de convergencia MILP — valores reales reportados por HiGHS.
        st.markdown("#### 🎯 Diagnóstico de convergencia HiGHS")
        incumbent = result.get("incumbent_objective")
        best_bound = result.get("best_bound")
        achieved_gap = result.get("achieved_mip_gap")
        wall_time = result.get("solver_wallclock_time")

        g1, g2, g3, g4 = st.columns(4)
        g1.metric(
            "Mejor solución (incumbente)",
            "No disponible" if incumbent is None else f"{incumbent:,.0f}"
        )
        g2.metric(
            "Mejor bound",
            "No disponible" if best_bound is None else f"{best_bound:,.0f}"
        )
        g3.metric(
            "MIP gap alcanzado",
            "No disponible" if achieved_gap is None else f"{achieved_gap:.2%}"
        )
        g4.metric(
            "Tiempo real solver",
            "No disponible" if wall_time is None else f"{wall_time:.1f} s"
        )

        if achieved_gap is not None:
            if achieved_gap <= 0.02:
                st.success("El gap alcanzado está dentro de la tolerancia configurada del 2%.")
            elif achieved_gap <= 0.10:
                st.warning("HiGHS encontró una solución factible relativamente cercana al bound, pero no cerró el gap al 2% dentro del tiempo.")
            else:
                st.warning("El gap alcanzado todavía es amplio; conviene seguir mejorando la formulación MILP.")
        else:
            st.caption("Si HiGHS/Pyomo no expone el gap en esta interfaz, aparecerá como “No disponible”; no se inventa ningún valor.")

        diag = result.get("model_diagnostics", {})
        if diag:
            st.markdown("##### 🔎 Diagnóstico estructural del modelo")
            d1, d2, d3, d4, d5 = st.columns(5)
            d1.metric("Variables", f'{diag.get("variables_total", 0):,}')
            d2.metric("Continuas", f'{diag.get("variables_continuous", 0):,}')
            d3.metric("Enteras", f'{diag.get("variables_integer", 0):,}')
            d4.metric("Binarias", f'{diag.get("variables_binary", 0):,}')
            d5.metric("Restricciones", f'{diag.get("constraints_total", 0):,}')

            largest = diag.get("largest_constraint_blocks", [])
            if largest:
                import pandas as pd
                st.dataframe(
                    pd.DataFrame(largest, columns=["Bloque de restricciones", "Cantidad"]),
                    use_container_width=True,
                    hide_index=True,
                )

        k1,k2,k3,k4,k5=st.columns(5)
        k1.metric("Objetivo", f"{result['objective']:,.0f}")
        k2.metric("Utilidad esperada", f"{result['expected_profit']:,.0f}")
        k3.metric("CVaR", f"{result['cvar']:,.0f}")
        k4.metric("Viabilidad", f"{result['expected_viability']:.1%}")
        k5.metric("Faltante esperado", f"{result['expected_shortage']:,.0f}")
        st.write(f"**Diseño seleccionado:** {result['plants_active']} plantas activas y {result['cds_active']} CD activos.")

        # Verificación visible de que la fijación solicitada llegó a la solución.
        # v8 — Diagnóstico SCIS proveniente del optimizador v31.
        st.markdown("### 🧬 Diagnóstico SCIS")
        st.caption(
            "Auditoría de la respuesta adaptativa por escenario. "
            "Estos indicadores se leen de la solución y no modifican el MILP."
        )

        scis_rows = []
        for s, sv in result.get("scenario", {}).items():
            scis_rows.append({
                "Escenario": s,
                "Probabilidad": float(sv.get("probability", 0.0)),
                "zInn promedio": float(sv.get("scis_zinn_avg", 0.0)),
                "zInn final": float(sv.get("scis_zinn_end", 0.0)),
                "Memoria SCIS final": float(sv.get("scis_memory_end", sv.get("memory_end", 0.0))),
                "Violación homeostasis": float(sv.get("homeostasis_violation", 0.0)),
                "Desempeño SCIS mínimo": float(sv.get("scis_perf_min", 0.0)),
                "Activación InnON": float(sv.get("scis_inn_on_rate", 0.0)),
                "Activación Out": float(sv.get("scis_out_rate", 0.0)),
            })

        if scis_rows:
            df_scis = pd.DataFrame(scis_rows)
            st.dataframe(
                df_scis.style.format({
                    "Probabilidad": "{:.2%}",
                    "zInn promedio": "{:.4f}",
                    "zInn final": "{:.4f}",
                    "Memoria SCIS final": "{:.4f}",
                    "Violación homeostasis": "{:,.2f}",
                    "Desempeño SCIS mínimo": "{:.4f}",
                    "Activación InnON": "{:.2%}",
                    "Activación Out": "{:.2%}",
                }),
                use_container_width=True,
                hide_index=True,
            )

            weights = df_scis["Probabilidad"]
            den = float(weights.sum()) or 1.0
            sc1, sc2, sc3, sc4 = st.columns(4)
            with sc1:
                st.metric("zInn esperado", f"{float((df_scis['zInn promedio']*weights).sum()/den):.4f}")
            with sc2:
                st.metric("Memoria SCIS esperada", f"{float((df_scis['Memoria SCIS final']*weights).sum()/den):.4f}")
            with sc3:
                st.metric("Violación homeostasis esp.", f"{float((df_scis['Violación homeostasis']*weights).sum()/den):,.2f}")
            with sc4:
                st.metric("Pperf mínimo global", f"{float(df_scis['Desempeño SCIS mínimo'].min()):.4f}")

            st.info(
                "zInn representa activación adaptativa continua; Mmem acumula memoria; "
                "ViolY mide relajación de homeostasis; Pperf resume desempeño; "
                "InnON y Out son activaciones binarias del bloque SCIS."
            )
        else:
            st.warning(
                "La solución no contiene indicadores SCIS. "
                "Verifica que modelo_ursp_scis.py corresponda a la v31."
            )

        solved_design = result.get("design", {})
        solved_plants = solved_design.get("plants", {})
        solved_cds = solved_design.get("cds", {})
        if solved_plants or solved_cds:
            st.markdown("##### 🔒 Verificación del diseño fijado")
            vc1, vc2 = st.columns(2)
            with vc1:
                st.write("**Plantas (YP)**")
                for j in ["j1","j2","j3"]:
                    requested = int(od.plant_design_status.get(j,0))
                    obtained = int(round(float(solved_plants.get(j,0))))
                    st.write(f"{j}: solicitado {requested} → solución {obtained}")
            with vc2:
                st.write("**Centros de distribución (YCD)**")
                for k in ["k1","k2","k3","k4"]:
                    requested = int(od.cd_design_status.get(k,0))
                    obtained = int(round(float(solved_cds.get(k,0))))
                    st.write(f"{k}: solicitado {requested} → solución {obtained}")

            design_ok = (
                all(int(round(float(solved_plants.get(j,0)))) == int(od.plant_design_status.get(j,0))
                    for j in ["j1","j2","j3"])
                and
                all(int(round(float(solved_cds.get(k,0)))) == int(od.cd_design_status.get(k,0))
                    for k in ["k1","k2","k3","k4"])
            )
            if design_ok:
                st.success("✅ La solución respeta exactamente el diseño fijado (YP/YCD).")
            else:
                st.error("⚠️ La solución mostrada no coincide con el diseño fijado; revisar la corrida.")
        st.dataframe(scenario_table(result), use_container_width=True, hide_index=True)
        render_transport_optimizer(result)
        st.markdown("#### Lectura para el Digital Twin")
        if result["expected_viability"] >= od.theta:
            st.success("🟢 La configuración mantiene la viabilidad esperada dentro del umbral definido.")
        else:
            st.warning("🟠 La configuración cae por debajo del umbral de viabilidad; conviene revisar capacidad, demanda, transporte o diseño.")
        st.info("Los resultados pueden utilizarse como evidencia para comparar decisiones, observar efectos LEAN y alimentar el siguiente ciclo del Digital Twin.")

if page == "Dashboard":
    st.markdown("### Dashboard")
    if package is None:
        st.info("Configura el escenario y ejecuta un ciclo para activar el tablero. También puedes entrar a **Laboratorio DT** para modificar las variables.")
        render_physical()
        st.markdown("### Vista previa del aprendizaje")
        q1,q2,q3,q4,q5,q6=st.columns(6)
        for col,num,title in zip([q1,q2,q3,q4,q5,q6],range(1,7),["Observar","Predecir","Recordar","Imaginar futuros","Decidir","Aprender"]):
            with col:
                st.markdown(f'<div class="card"><b>{num}. {title}</b><br><span class="small-muted">Pendiente de ejecutar</span></div>',unsafe_allow_html=True)
        st.stop()

    r1,r2,r3,r4=package["a1"],package["a2"],package["a3"],package["a4"]
    vals,avg,diag=render_lean(package)
    st.markdown("### Resultados del ciclo")
    c1,c2=st.columns([1.05,1.25])
    with c1:
        st.markdown('<div class="card">',unsafe_allow_html=True); render_physical(); st.markdown('</div>',unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="card">',unsafe_allow_html=True); render_a1(r1); st.markdown('</div>',unsafe_allow_html=True)
    c1,c2=st.columns(2)
    with c1:
        st.markdown('<div class="card">',unsafe_allow_html=True); render_a2(r2); st.markdown('</div>',unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="card">',unsafe_allow_html=True); render_a3(r3); st.markdown('</div>',unsafe_allow_html=True)
    c1,c2=st.columns(2)
    with c1:
        st.markdown('<div class="card">',unsafe_allow_html=True); render_a4(r4); st.markdown('</div>',unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="card">',unsafe_allow_html=True)
        st.markdown('<div class="card-title">🔵 Resultados y aprendizaje</div>',unsafe_allow_html=True)
        o=r4.outcome
        z1,z2,z3=st.columns(3)
        z1.metric("Servicio",f"{o.get('service_after',0):.1%}")
        z2.metric("Viabilidad",f"{o.get('viability_after',0):.1%}")
        z3.metric("Éxito",f"{o.get('decision_success',0):.1%}")
        next_input=next_physical_from_package(package); nv=calculate_lean_indicators(next_input); navg=sum(nv.values())/len(nv)
        st.metric("Desperdicio estimado siguiente",f"{navg:.1%}",delta=f"{navg-avg:+.1%}")
        if navg < avg-0.03: st.success("🟢 La cadena muestra una mejora esperada.")
        elif navg > avg+0.03: st.warning("🔴 La cadena requiere revisar la decisión.")
        else: st.info("🟡 El cambio esperado es pequeño.")
        st.markdown('</div>',unsafe_allow_html=True)

elif page == "Transporte y logística":
    st.markdown("### 🚚 Transporte y logística")
    st.markdown(
        '<div class="explain"><b>Cadena visualizada:</b> Planta → CD → Mercado. '
        'Esta vista utiliza los viajes enteros, capacidades y disponibilidad logística calculados por el optimizador URSP–SCIS.</div>',
        unsafe_allow_html=True
    )

    result = st.session_state.get("optimizer_result")
    if not result:
        st.info("Primero entra a **Diseño y optimización**, ejecuta la optimización URSP–SCIS y luego vuelve a esta vista.")
        p = st.session_state.physical
        a,b,c = st.columns(3)
        a.metric("Disponibilidad DT", f"{p['transport']:.1%}")
        b.metric("Lead Time", f"{p['lead']:.2f}")
        c.metric("Desperdicio Lean transporte", f"{max(0.0,min(1.0,1.0-p['transport'])):.1%}")
    else:
        render_transport_optimizer(result)

        if package is not None:
            st.markdown("#### 🔗 Transporte del optimizador + decisión A4")
            fd = package["a4"].final_decision
            p = package["input"]
            lean_transport = max(0.0, min(1.0, 1.0-p["transport"]))
            a,b,c,d = st.columns(4)
            a.metric("Disponibilidad observada", f"{p['transport']:.1%}")
            b.metric("Desperdicio Lean", f"{lean_transport:.1%}")
            c.metric("Ajuste transporte A4", f"{fd.get('transport_adjustment',0):+.1%}")
            d.metric("Capa SCIS", str(fd.get("scis_layer","L0")))

            st.markdown(
                '<div class="explain"><b>Interpretación:</b> la optimización determina cómo se comporta '
                'la red física de transporte y A4 propone la respuesta adaptativa del Digital Twin. '
                'Así se conecta el resultado matemático con la reducción del desperdicio Lean de transporte.</div>',
                unsafe_allow_html=True
            )


elif page == "Escenarios":
    st.markdown("### 🔮 Escenarios")
    st.write("Selecciona un escenario en la barra superior y ejecuta ciclos para observar cómo cambia la respuesta del Digital Twin.")
    rows=[]
    for name,d in SCENARIO_DEFAULTS.items():
        rows.append({"Escenario":name,"Suministro":d["supply"],"Demanda":d["demand"],"Transporte":d["transport"],"Procesamiento":d["processing"],"Lead Time":d["lead"],"Disrupción":d["intensity"]})
    st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
    if package is not None:
        render_a3(package["a3"])

elif page == "Laboratorio DT":
    st.markdown("### 🧪 Laboratorio Digital Twin")
    render_physical()
    c1,c2=st.columns(2)
    with c1:
        st.session_state.previous_pressure=st.slider("Presión anterior",0.,1.,float(st.session_state.previous_pressure),.01)
    with c2:
        st.session_state.memory_level=st.slider("Memoria adaptativa",0.,1.,float(st.session_state.memory_level),.01)
    st.markdown("#### 🧬 What-if — sin alterar historial")
    with st.expander("Abrir sandbox What-if"):
        base=st.session_state.physical.copy()
        a,b=st.columns(2)
        with a:
            ws=st.slider("Suministro",.05,1.,float(base["supply"]),.01,key="wi_supply2")
            wd=st.slider("Demanda",.5,2.,float(base["demand"]),.01,key="wi_demand2")
            wt=st.slider("Transporte",.05,1.,float(base["transport"]),.01,key="wi_transport2")
            wp=st.slider("Procesamiento",.05,1.,float(base["processing"]),.01,key="wi_processing2")
        with b:
            wq=st.slider("Calidad",.5,1.,float(base["quality"]),.01,key="wi_quality2")
            wl=st.slider("Lead Time",.5,2.5,float(base["lead"]),.01,key="wi_lead2")
            wi=st.slider("Intensidad",0.,1.,float(base["intensity"]),.01,key="wi_intensity2")
            wpe=st.slider("Persistencia",0.,1.,float(base["persistence"]),.01,key="wi_persistence2")
        if st.button("🔬 Simular What-if",type="secondary"):
            wcur={"supply":ws,"demand":wd,"transport":wt,"processing":wp,"quality":wq,"lead":wl,"intensity":wi,"persistence":wpe}
            st.session_state.what_if_package=execute_cycle(wcur,st.session_state.cycle,st.session_state.previous_pressure,st.session_state.memory_level,copy.deepcopy(st.session_state.memory_repository_a2),copy.deepcopy(st.session_state.memory_repository_a4),"What-if")
        if st.session_state.get("what_if_package") is not None:
            w=st.session_state.what_if_package
            x1,x2,x3,x4=st.columns(4)
            x1.metric("Presión",f"{w['a1'].current_pressure:.1%}")
            x2.metric("Predicción",f"{w['a1'].predicted_pressure:.1%}")
            x3.metric("SCIS",w['a4'].final_decision.get('scis_layer','L0'))
            x4.metric("Éxito",f"{w['a4'].outcome.get('decision_success',0):.1%}")
            st.success("🔒 El What-if no modifica el historial.")

elif page == "Comparación":
    st.markdown("### ⚖️ Baseline vs APDT")
    if package is None:
        st.info("Ejecuta al menos un ciclo para comparar decisiones.")
    else:
        r4=package["a4"]; render_a4(r4)
        bl=r4.baseline_decision; fd=r4.final_decision
        df=pd.DataFrame({"Baseline":[bl.get("expected_service_level",0),bl.get("expected_profitability",0),bl.get("expected_viability",0)],"APDT":[fd.get("expected_service_level",0),fd.get("expected_profitability",0),fd.get("expected_viability",0)]},index=["Servicio","Rentabilidad","Viabilidad"])
        render_selectable_chart(df, "baseline_apdt", height=300)
        st.write(f"**Fuente de decisión:** {fd.get('decision_source','Decisión adaptativa')}")

elif page == "Historial de ciclos":
    st.markdown("### 📈 Historial de ciclos")
    if not st.session_state.history:
        st.info("Todavía no hay ciclos registrados.")
    else:
        rows=[]
        for item in st.session_state.history:
            a1,a2,a4=item["a1"],item["a2"],item["a4"]
            lv=calculate_lean_indicators(item["input"]); la=sum(lv.values())/len(lv)
            rows.append({"Ciclo":item["cycle"],"Escenario":item["scenario"],"Presión":a1.current_pressure,"Predicción":a1.predicted_pressure,"Memoria":a2.memory_after,"Servicio":a4.outcome.get("service_after",0),"Viabilidad":a4.outcome.get("viability_after",0),"Éxito":a4.outcome.get("decision_success",0),"Desperdicio LEAN":la})
        df=pd.DataFrame(rows).set_index("Ciclo")
        render_selectable_chart(df[["Presión","Predicción"]], "history_pressure", height=240, default="Línea")
        render_selectable_chart(df[["Servicio","Viabilidad","Éxito"]], "history_outcomes", height=240, default="Línea")
        render_selectable_chart(df[["Desperdicio LEAN"]], "history_lean", height=240, default="Línea")
        st.dataframe(df,use_container_width=True)
        st.download_button("⬇️ Exportar historial CSV",df.to_csv().encode("utf-8-sig"),"digital_twin_historial.csv","text/csv",use_container_width=True)

elif page == "Lecciones":
    st.markdown("### 🎓 Lecciones y aprendizaje")
    if package is None:
        st.info("Ejecuta un ciclo para generar una lección automática.")
    else:
        vals,avg,diag=lean_pack(package)
        st.markdown(f'<div class="explain"><b>Lección del ciclo:</b> el principal desperdicio fue <b>{diag["dominant_waste"]}</b> con un nivel de {diag["dominant_value"]:.1%}. {diag["effect"]} La acción sugerida es: {diag["recommendation"]}</div>',unsafe_allow_html=True)
        st.markdown("#### Trazabilidad")
        r1,r2,r3,r4=package["a1"],package["a2"],package["a3"],package["a4"]
        st.write(f"1. **Observar:** escenario {package['scenario']}.")
        st.write(f"2. **Predecir:** presión {r1.current_pressure:.1%} → {r1.predicted_pressure:.1%}.")
        st.write(f"3. **Recordar:** memoria {r2.memory_before:.1%} → {r2.memory_after:.1%}.")
        st.write(f"4. **Imaginar futuros:** {r3.most_probable_scenario} es el escenario más probable.")
        st.write(f"5. **Decidir:** {r4.final_decision.get('decision_source','APDT')} con {r4.final_decision.get('scis_layer','L0')}.")
        st.write(f"6. **Aprender:** desperdicio LEAN global {avg:.1%}; el resultado puede alimentar los siguientes ciclos.")

else:
    st.markdown("### 📘 Glossary")
    glossary={
        "Digital Twin":"Representación computacional de la cadena para experimentar con su estado y decisiones.",
        "A1 — Predecir":"Calcula presión operacional, estado predicho y confianza.",
        "A2 — Recordar":"Recupera experiencias y actualiza memoria adaptativa.",
        "A3 — Imaginar futuros":"Genera escenarios futuros y sus probabilidades.",
        "A4 — Decidir":"Compara alternativas y aplica una decisión sobre el estado físico.",
        "SCIS":"Capa de decisión/coordination adaptativa usada por el modelo.",
        "LEAN":"Enfoque de mejora que busca reducir desperdicios y actividades que no agregan valor.",
        "AvailCDC":"Disponibilidad efectiva de la capacidad logística CD → mercado por periodo y escenario.",
        "Viajes Planta → CD":"Viajes enteros de la flota que transporta producto terminado desde plantas hacia centros de distribución.",
        "Viajes CD → Mercado":"Viajes enteros de la flota que entrega producto desde centros de distribución hacia el mercado.",
        "What-if":"Experimento alternativo que no modifica el historial principal."
    }
    for term,definition in glossary.items():
        st.markdown(f"**{term}** — {definition}")

# ---------- Footer ----------
st.divider()
st.caption("Supply Chain Digital Twin Learning Lab · Cadena de suministro láctea · Laboratorio didáctico A1–A4 + SCIS + LEAN")
