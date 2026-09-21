"""
URSP-SCIS para Digital Twin de cadena láctea
Versión ejecutable v2 basada en la estructura ACTIVA del GAMS suministrado.

IMPORTANTE:
- Conserva la interfaz OptimizerData / solve_model / scenario_table usada por app.py.
- Implementa 5 escenarios con efectos reales sobre demanda, suministro, transporte y proceso.
- Mantiene diseño binario de plantas/CD, faltantes, SCIS, memoria, homeostasis y CVaR.
- No modifica algoritmo1.py ... algoritmo4.py.
- Esta versión es una implementación integrada y ejecutable en Pyomo/HiGHS.
  La validación 1:1 de las 2.191 líneas del GAMS debe hacerse por bloques contra GAMS.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional
import math

SCENARIOS = ["s1", "s2", "s3", "s4", "s5"]
PERIODS = ["semana1", "semana2", "semana3", "semana4"]
PRODUCTS = ["mantequilla", "yogurt", "leche_past"]
PLANTS = ["j1", "j2", "j3"]
CDS = ["k1", "k2", "k3", "k4"]

# ===== RED DINÁMICA PARAMETRIZABLE =====
# Los datos GAMS originales existen para j1-j3 y k1-k4. Para nodos adicionales
# se usa una extensión determinística basada en los perfiles originales.
BASE_PLANTS = tuple(PLANTS)
BASE_CDS = tuple(CDS)

def _node_number(name: str, prefix: str) -> int:
    try:
        n = int(str(name).replace(prefix, "", 1))
        return max(1, n)
    except Exception:
        return 1

def _base_plant(j: str) -> str:
    n = _node_number(j, "j")
    return BASE_PLANTS[(n - 1) % len(BASE_PLANTS)]

def _base_cd(k: str) -> str:
    n = _node_number(k, "k")
    return BASE_CDS[(n - 1) % len(BASE_CDS)]

def make_plants(count: int):
    count = max(1, int(count))
    return [f"j{i}" for i in range(1, count + 1)]

def make_cds(count: int):
    count = max(1, int(count))
    return [f"k{i}" for i in range(1, count + 1)]
CONSUMERS = ["n1","n2","n3"]

DEFAULT_PROB = {"s1": .15, "s2": .20, "s3": .15, "s4": .15, "s5": .35}
DEFAULT_ING = {"mantequilla": 20760., "yogurt": 6560., "leche_past": 3700.}
DEFAULT_FIXED_PLANT = {"j1": 12200000., "j2": 12000000., "j3": 12000000.}
DEFAULT_FIXED_CD = {"k1": 5500000., "k2": 5000000., "k3": 5200000., "k4": 5350000.}

# Trayectorias diferenciadas para que A3/Streamlit pueda sustituirlas dinámicamente.
DEFAULT_DEMAND_FACTOR = {"s1": 1.00, "s2": 1.08, "s3": 0.94, "s4": 1.02, "s5": 1.15}
DEFAULT_SUPPLY_FACTOR = {"s1": 1.00, "s2": 0.82, "s3": 1.05, "s4": 0.92, "s5": 0.70}
DEFAULT_TRANSPORT_FACTOR = {"s1": 1.00, "s2": 0.72, "s3": 1.00, "s4": 0.82, "s5": 0.58}
DEFAULT_PROCESSING_FACTOR = {"s1": 1.00, "s2": 0.88, "s3": 1.02, "s4": 0.90, "s5": 0.68}
DEFAULT_DISRUPTION = {"s1": 0.10, "s2": 0.40, "s3": 0.05, "s4": 0.25, "s5": 0.65}

# ===== DATOS OPERATIVOS EXTRAÍDOS DEL GAMS ORIGINAL =====
GAMS_BASE_DEMAND = {
    ("mantequilla","semana1"): 536+564+620,
    ("mantequilla","semana2"): 435+464+487,
    ("mantequilla","semana3"): 449+459+508,
    ("mantequilla","semana4"): 578+570+635,
    ("yogurt","semana1"): 7866+8226+8382,
    ("yogurt","semana2"): 6868+6598+6736,
    ("yogurt","semana3"): 6643+6885+7092,
    ("yogurt","semana4"): 7885+8153+8197,
    ("leche_past","semana1"): 17688+17210+16567,
    ("leche_past","semana2"): 14057+14414+14358,
    ("leche_past","semana3"): 14165+14093+14291,
    ("leche_past","semana4"): 17773+17175+17163,
}
GAMS_FDEM = {(t,s):1.0 for t in PERIODS for s in SCENARIOS}
GAMS_FDEM.update({
    ("semana2","s1"):1.30, ("semana3","s1"):2.50, ("semana4","s1"):1.30,
    ("semana2","s2"):2.60, ("semana3","s2"):2.00, ("semana4","s2"):2.00,
    ("semana2","s3"):2.05,
    ("semana1","s4"):2.10, ("semana2","s4"):1.15,
    ("semana2","s5"):2.20, ("semana3","s5"):1.30, ("semana4","s5"):2.10,
})
GAMS_ENV = {(i,t,s):1.0 for i in PRODUCTS for t in PERIODS for s in SCENARIOS}
def _set_env(product, scenario, vals):
    for t,v in vals.items(): GAMS_ENV[(product,t,scenario)] = v
_set_env("leche_past","s1",{"semana2":.55,"semana3":.60})
_set_env("yogurt","s1",{"semana2":.60,"semana3":.70})
_set_env("mantequilla","s1",{"semana2":.60,"semana3":.85})
_set_env("leche_past","s3",{"semana2":.40,"semana3":.05,"semana4":.40})
_set_env("yogurt","s3",{"semana2":.40,"semana3":.35,"semana4":.40})
_set_env("mantequilla","s3",{"semana2":.50,"semana3":.55,"semana4":.25})
_set_env("leche_past","s4",{"semana2":.30,"semana3":.10,"semana4":.35})
_set_env("yogurt","s4",{"semana2":.25,"semana3":.42,"semana4":.30})
_set_env("mantequilla","s4",{"semana2":.30,"semana3":.40,"semana4":.25})
_set_env("leche_past","s5",{"semana3":.35,"semana4":.20})
_set_env("yogurt","s5",{"semana3":.35,"semana4":.20})
_set_env("mantequilla","s5",{"semana3":.35,"semana4":.20})

GAMS_AVAIL_CDC = {(t,s):1.0 for t in PERIODS for s in SCENARIOS}
GAMS_AVAIL_CDC.update({
    ("semana3","s1"):.35, ("semana4","s1"):.40,
    ("semana2","s2"):.50, ("semana3","s2"):.35, ("semana4","s2"):.40,
    ("semana3","s3"):.15,
    ("semana3","s4"):.55, ("semana4","s4"):.35,
    ("semana3","s5"):.50, ("semana4","s5"):.45,
})
GAMS_PACK_CAP = {
    ("mantequilla","j1"):700., ("mantequilla","j2"):700., ("mantequilla","j3"):800.,
    ("yogurt","j1"):12000., ("yogurt","j2"):12000., ("yogurt","j3"):16000.,
    ("leche_past","j1"):25000., ("leche_past","j2"):25000., ("leche_past","j3"):34000.,
}


# ===== v5: DISPONIBILIDAD DE PROCESO Y OFERTA DEL GAMS =====
GAMS_FPROC_OVERRIDES = {('Pasteurizacion_l1', 'j2', 'semana2', 's1'): 0.15, ('Pasteurizacion_l1', 'j2', 'semana3', 's1'): 0.2, ('homoge_leche', 'j2', 'semana2', 's1'): 0.25, ('homoge_leche', 'j2', 'semana3', 's1'): 0.0, ('homoge_leche', 'j2', 'semana4', 's1'): 0.55, ('Filtracion_l2', 'j2', 'semana2', 's1'): 0.2, ('Filtracion_l2', 'j2', 'semana3', 's1'): 0.2, ('homoge_leche', 'j1', 'semana2', 's2'): 0.75, ('homoge_leche', 'j1', 'semana3', 's2'): 0.0, ('homoge_leche', 'j1', 'semana4', 's2'): 0.55, ('Pasteurizacion_l1', 'j1', 'semana2', 's2'): 0.05, ('Pasteurizacion_l1', 'j1', 'semana3', 's2'): 0.2, ('Filtracion_l2', 'j2', 'semana2', 's2'): 0.2, ('Filtracion_l2', 'j2', 'semana3', 's2'): 0.2, ('Filtracion_l2', 'j1', 'semana2', 's2'): 0.2, ('Filtracion_l2', 'j1', 'semana3', 's2'): 0.2, ('homoge_leche', 'j2', 'semana2', 's3'): 0.55, ('homoge_leche', 'j2', 'semana3', 's3'): 0.25, ('Pasteurizacion_l1', 'j2', 'semana2', 's3'): 0.1, ('Pasteurizacion_l1', 'j2', 'semana3', 's3'): 0.3, ('Pasteurizacion_l1', 'j1', 'semana2', 's4'): 0.39, ('Pasteurizacion_l1', 'j1', 'semana3', 's4'): 0.5, ('homoge_leche', 'j1', 'semana2', 's4'): 0.75, ('homoge_leche', 'j1', 'semana3', 's4'): 0.25, ('homoge_leche', 'j1', 'semana4', 's4'): 0.55, ('Filtracion_l2', 'j1', 'semana2', 's4'): 0.59, ('Filtracion_l2', 'j1', 'semana3', 's4'): 0.5, ('Maduracion', 'j3', 'semana3', 's5'): 0.25, ('Homoge_yogurt', 'j3', 'semana3', 's5'): 0.25, ('Pasteurizacion_l1', 'j1', 'semana2', 's5'): 0.09, ('Pasteurizacion_l1', 'j1', 'semana3', 's5'): 0.1, ('homoge_leche', 'j1', 'semana2', 's5'): 0.45, ('homoge_leche', 'j1', 'semana3', 's5'): 0.25, ('homoge_leche', 'j1', 'semana4', 's5'): 0.55, ('Pasteurizacion_l1', 'j2', 'semana2', 's5'): 1.1, ('Pasteurizacion_l1', 'j2', 'semana3', 's5'): 1.05, ('Pasteurizacion_l1', 'j3', 'semana2', 's5'): 1.05, ('Pasteurizacion_l1', 'j3', 'semana3', 's5'): 1.1}
GAMS_FSUP_OVERRIDES = {('leche2', 'semana2', 's1'): 0.4, ('leche2', 'semana3', 's1'): 0.2, ('leche2', 'semana4', 's1'): 0.7, ('leche2', 'semana2', 's3'): 0.4, ('leche2', 'semana3', 's3'): 0.2, ('leche2', 'semana4', 's3'): 0.7}

def gams_fproc(q,j,t,s):
    return GAMS_FPROC_OVERRIDES.get((q,_base_plant(j),t,s), 1.0)

def gams_fsup(a,t,s):
    return GAMS_FSUP_OVERRIDES.get((a,t,s), 1.0)

# Oferta OFH1 agregada sobre los cuatro clusters h (litros/unidades del GAMS).
GAMS_SUPPLY_BASE = {
    ("leche1","semana1"): 2240+2160+2000+2240,
    ("leche1","semana2"): 2240+2000+2080+2080,
    ("leche1","semana3"): 2080+2160+2240+2240,
    ("leche1","semana4"): 2160+2160+2080+2080,
    ("leche2","semana1"): 48600+46800+48600+47700,
    ("leche2","semana2"): 54000+45000+53100+45900,
    ("leche2","semana3"): 52200+50400+54000+51300,
    ("leche2","semana4"): 49500+45000+47700+48600,
}

# Capacidades de procesos clave CAPXRA0. Las plantas j1/j2 usan 24k para las
# etapas lácteas principales y j3 28k; las capacidades finales vienen del GAMS.
GAMS_MAIN_PROCESS_CAP = {"j1":24000., "j2":24000., "j3":28000.}
GAMS_YOG_PROCESS_CAP = {"j1":12000., "j2":12000., "j3":16000.}

# ===== v6: TIEMPO EXTRA, SUBCONTRATACIÓN Y STACK BUFFER DEL GAMS =====
GAMS_MAXSUB0 = {
    ("mantequilla","j1"):250., ("mantequilla","j2"):250., ("mantequilla","j3"):275.,
    ("yogurt","j1"):500., ("yogurt","j2"):500., ("yogurt","j3"):375.,
    ("leche_past","j1"):875., ("leche_past","j2"):625., ("leche_past","j3"):675.,
}
# En GAMS: MAXSUB = MAXSUB0*0.5
GAMS_MAXSUB = {k: 0.5*v for k,v in GAMS_MAXSUB0.items()}

GAMS_SUB_COST = {
    ("mantequilla","j1"):25060., ("mantequilla","j2"):22060., ("mantequilla","j3"):22060.,
    ("yogurt","j1"):7660., ("yogurt","j2"):7660., ("yogurt","j3"):7660.,
    ("leche_past","j1"):3800., ("leche_past","j2"):3800., ("leche_past","j3"):3800.,
}
GAMS_BUFFER_COST = {
    ("mantequilla","j1"):125., ("mantequilla","j2"):160., ("mantequilla","j3"):170.,
    ("yogurt","j1"):160., ("yogurt","j2"):170., ("yogurt","j3"):176.,
    ("leche_past","j1"):138., ("leche_past","j2"):140., ("leche_past","j3"):135.,
}
GAMS_BUFFER_CAP = {
    ("mantequilla","j1"):675., ("mantequilla","j2"):700., ("mantequilla","j3"):770.,
    ("yogurt","j1"):490., ("yogurt","j2"):728., ("yogurt","j3"):700.,
    ("leche_past","j1"):658., ("leche_past","j2"):560., ("leche_past","j3"):588.,
}
GAMS_FINAL_REG_COST = {"mantequilla":40., "yogurt":60., "leche_past":15.}

# ===== v7: RED DE PROCESOS INTERMEDIOS DEL GAMS =====
PROCESS_STAGES = [
    "Filtracion_l1","Refrigeracion_l1","Pasteurizacion_l1",
    "Filtracion_l2","Refrigeracion_l2","Pasteurizacion_l2",
    "Mantecado","Maduracion","Homoge_yogurt","homoge_leche"
]
GAMS_PROCESS_BASE_CAP = {
    q: {"j1":24000.,"j2":24000.,"j3":28000.}
    for q in ["Filtracion_l1","Refrigeracion_l1","Pasteurizacion_l1",
              "Filtracion_l2","Refrigeracion_l2","Pasteurizacion_l2"]
}
GAMS_PROCESS_BASE_CAP.update({
    "Mantecado":{"j1":700.,"j2":700.,"j3":700.},
    "Maduracion":{"j1":12000.,"j2":12000.,"j3":16000.},
    "Homoge_yogurt":{"j1":12000.,"j2":12000.,"j3":16000.},
    "homoge_leche":{"j1":25000.,"j2":25000.,"j3":34000.},
})


# ===== v9: HATOS -> PLANTA / RECOLECCIÓN DE LECHE CRUDA =====
RAW_MILKS = ["leche1","leche2"]
FARMS = ["h1","h2","h3","h4"]
TRUCK_HATO = ["l1","l2","l3"]

GAMS_CAPCHT = {"l1":4000.,"l2":8000.,"l3":12000.}
GAMS_CAPCH = {"l1":4.,"l2":8.,"l3":12.}
GAMS_CCTH = {"l1":10,"l2":15,"l3":18}
GAMS_NMAXVH = {"l1":18,"l2":16,"l3":14}
GAMS_PEH = {"leche1":1.05,"leche2":1.02}
GAMS_VEH = {"leche1":.00105,"leche2":.00102}

GAMS_OFH1 = {
 ("h1","leche1","semana1"):2240.,("h1","leche1","semana2"):2240.,("h1","leche1","semana3"):2080.,("h1","leche1","semana4"):2160.,
 ("h1","leche2","semana1"):48600.,("h1","leche2","semana2"):54000.,("h1","leche2","semana3"):52200.,("h1","leche2","semana4"):49500.,
 ("h2","leche1","semana1"):2160.,("h2","leche1","semana2"):2000.,("h2","leche1","semana3"):2160.,("h2","leche1","semana4"):2160.,
 ("h2","leche2","semana1"):46800.,("h2","leche2","semana2"):45000.,("h2","leche2","semana3"):50400.,("h2","leche2","semana4"):45000.,
 ("h3","leche1","semana1"):2000.,("h3","leche1","semana2"):2080.,("h3","leche1","semana3"):2240.,("h3","leche1","semana4"):2080.,
 ("h3","leche2","semana1"):48600.,("h3","leche2","semana2"):53100.,("h3","leche2","semana3"):54000.,("h3","leche2","semana4"):47700.,
 ("h4","leche1","semana1"):2240.,("h4","leche1","semana2"):2080.,("h4","leche1","semana3"):2240.,("h4","leche1","semana4"):2080.,
 ("h4","leche2","semana1"):47700.,("h4","leche2","semana2"):45900.,("h4","leche2","semana3"):51300.,("h4","leche2","semana4"):48600.,
}
GAMS_CCLH = {
 ("leche1","h1","semana1"):820.,("leche1","h1","semana2"):811.,("leche1","h1","semana3"):813.,("leche1","h1","semana4"):820.,
 ("leche2","h1","semana1"):996.,("leche2","h1","semana2"):996.,("leche2","h1","semana3"):988.,("leche2","h1","semana4"):994.,
 ("leche1","h2","semana1"):809.,("leche1","h2","semana2"):807.,("leche1","h2","semana3"):800.,("leche1","h2","semana4"):821.,
 ("leche2","h2","semana1"):991.,("leche2","h2","semana2"):990.,("leche2","h2","semana3"):991.,("leche2","h2","semana4"):994.,
 ("leche1","h3","semana1"):804.,("leche1","h3","semana2"):817.,("leche1","h3","semana3"):812.,("leche1","h3","semana4"):804.,
 ("leche2","h3","semana1"):999.,("leche2","h3","semana2"):991.,("leche2","h3","semana3"):998.,("leche2","h3","semana4"):997.,
 ("leche1","h4","semana1"):810.,("leche1","h4","semana2"):818.,("leche1","h4","semana3"):811.,("leche1","h4","semana4"):812.,
 ("leche2","h4","semana1"):997.,("leche2","h4","semana2"):994.,("leche2","h4","semana3"):996.,("leche2","h4","semana4"):993.,
}
GAMS_DPCDH = {
 ("h1","j1"):11.0500,("h1","j2"):11.2320,("h1","j3"):11.4580,
 ("h2","j1"):11.6620,("h2","j2"):11.3240,("h2","j3"):11.3590,
 ("h3","j1"):11.8490,("h3","j2"):11.2540,("h3","j3"):11.1800,
 ("h4","j1"):11.0760,("h4","j2"):11.9060,("h4","j3"):11.3130,
}
GAMS_CACH = {
 ("l1","semana1"):15000.,("l1","semana2"):25000.,("l1","semana3"):25000.,("l1","semana4"):25000.,
 ("l2","semana1"):25000.,("l2","semana2"):35000.,("l2","semana3"):35000.,("l2","semana4"):35000.,
 ("l3","semana1"):30000.,("l3","semana2"):40000.,("l3","semana3"):40000.,("l3","semana4"):40000.,
}
def gams_ofh(h,a,t,s):
    return GAMS_OFH1[(h,a,t)] * gams_fsup(a,t,s)

def gams_cvh(l,h,j,t):
    # GAMS: CVH = CACH + 2*500*DPCDH
    return GAMS_CACH[(l,t)] + 1000.0*GAMS_DPCDH[(h,_base_plant(j))]





# ===== v12: COSTOS DE TRANSPORTE DEL GAMS =====
# Datos portados del bloque COSTRAS del archivo URSP SCIS Viability H2.
GAMS_CAC = {
 ("m1","semana1"):25000.,("m1","semana2"):25000.,("m1","semana3"):25000.,("m1","semana4"):25000.,
 ("m2","semana1"):35000.,("m2","semana2"):35000.,("m2","semana3"):35000.,("m2","semana4"):35000.,
}
GAMS_CACCD = {
 ("o1","semana1"):25000.,("o1","semana2"):25000.,("o1","semana3"):25000.,("o1","semana4"):25000.,
 ("o2","semana1"):35000.,("o2","semana2"):35000.,("o2","semana3"):35000.,("o2","semana4"):35000.,
 ("o3","semana1"):40000.,("o3","semana2"):40000.,("o3","semana3"):40000.,("o3","semana4"):40000.,
}
GAMS_CACPP = {
 ("z1","semana1"):25000.,("z1","semana2"):25000.,("z1","semana3"):25000.,("z1","semana4"):25000.,
 ("z2","semana1"):35000.,("z2","semana2"):35000.,("z2","semana3"):35000.,("z2","semana4"):35000.,
}
GAMS_DPCD = {
 ("j1","k1"):21.6560,("j1","k2"):21.0990,("j1","k3"):21.1457,("j1","k4"):18.777,
 ("j2","k1"):21.5710,("j2","k2"):20.1310,("j2","k3"):19.2150,("j2","k4"):19.254,
 ("j3","k1"):21.4820,("j3","k2"):20.3260,("j3","k3"):20.0140,("j3","k4"):19.457,
}
GAMS_DCDC = {
 ("k1","n1"):11.1910,("k1","n2"):11.4070,("k1","n3"):11.4310,
 ("k2","n1"):11.4230,("k2","n2"):11.0880,("k2","n3"):11.9450,
 ("k3","n1"):12.1910,("k3","n2"):10.4070,("k3","n3"):12.4310,
 ("k4","n1"):10.4230,("k4","n2"):11.4880,("k4","n3"):10.9450,
}
# La tabla DCPP del GAMS es triangular; las celdas no declaradas quedan en 0.
GAMS_DCPP = {
 ("j1","j1"):0.,("j1","j2"):0.,("j1","j3"):0.,
 ("j2","j1"):24.,("j2","j2"):0.,("j2","j3"):0.,
 ("j3","j1"):25.,("j3","j2"):24.,("j3","j3"):0.,
}
GAMS_CTCDC = {}
for _i in PRODUCTS:
    for _k in CDS:
        for _n in CONSUMERS:
            for _t in PERIODS:
                if _i == "mantequilla":
                    _c = 25.
                elif _i == "leche_past":
                    _c = 10.
                else:
                    _c = 30.
                    if (_k,_n,_t) in {
                        ("k1","n3","semana1"),("k1","n3","semana2"),
                        ("k2","n1","semana1"),("k2","n2","semana1"),
                        ("k2","n3","semana2"),("k2","n3","semana3"),
                        ("k3","n3","semana1"),("k3","n3","semana2"),
                        ("k4","n1","semana1"),("k4","n2","semana1"),
                        ("k4","n3","semana2"),("k4","n3","semana3"),
                    }:
                        _c = 35.
                GAMS_CTCDC[(_i,_k,_n,_t)] = _c

def gams_ctcdc(i,k,n,t):
    return GAMS_CTCDC[(i,_base_cd(k),n,t)]

GAMS_CTPCD = {"mantequilla":20.,"yogurt":30.,"leche_past":10.}
GAMS_CTPPL = 30.
GAMS_COSTPP = 10.

def gams_cvc(m,j,k,t):
    return GAMS_CAC[(m,t)] + 1200.0*GAMS_DPCD[(_base_plant(j),_base_cd(k))]

def gams_cvccd(o,k,n,t):
    return GAMS_CACCD[(o,t)] + 1400.0*GAMS_DCDC[(_base_cd(k),n)]

def gams_cvpp(z,j,jp,t):
    return GAMS_CACPP[(z,t)] + 1400.0*GAMS_DCPP[(_base_plant(j),_base_plant(jp))]


# ===== v11: CENTROS DE CONSUMO n1-n3 / XTCDC / NVCC =====

# Dem(i,n,t) exacta del GAMS.
GAMS_DEM_N = {
 ("mantequilla","n1","semana1"):536.,("mantequilla","n1","semana2"):435.,("mantequilla","n1","semana3"):449.,("mantequilla","n1","semana4"):578.,
 ("mantequilla","n2","semana1"):564.,("mantequilla","n2","semana2"):464.,("mantequilla","n2","semana3"):459.,("mantequilla","n2","semana4"):570.,
 ("mantequilla","n3","semana1"):620.,("mantequilla","n3","semana2"):487.,("mantequilla","n3","semana3"):508.,("mantequilla","n3","semana4"):635.,
 ("yogurt","n1","semana1"):7866.,("yogurt","n1","semana2"):6868.,("yogurt","n1","semana3"):6643.,("yogurt","n1","semana4"):7885.,
 ("yogurt","n2","semana1"):8226.,("yogurt","n2","semana2"):6598.,("yogurt","n2","semana3"):6885.,("yogurt","n2","semana4"):8153.,
 ("yogurt","n3","semana1"):8382.,("yogurt","n3","semana2"):6736.,("yogurt","n3","semana3"):7092.,("yogurt","n3","semana4"):8197.,
 ("leche_past","n1","semana1"):17688.,("leche_past","n1","semana2"):14057.,("leche_past","n1","semana3"):14165.,("leche_past","n1","semana4"):17773.,
 ("leche_past","n2","semana1"):17210.,("leche_past","n2","semana2"):14414.,("leche_past","n2","semana3"):14093.,("leche_past","n2","semana4"):17175.,
 ("leche_past","n3","semana1"):16567.,("leche_past","n3","semana2"):14358.,("leche_past","n3","semana3"):14291.,("leche_past","n3","semana4"):17163.,
}

# Totales base GAMS por producto (suma de n y t).
# Se usan únicamente para traducir OptimizerData.demand a un multiplicador
# proporcional; la distribución original por centro y semana se conserva.
GAMS_DEMAND_PRODUCT_TOTAL = {
    i: sum(GAMS_DEM_N[(i,n,t)] for n in CONSUMERS for t in PERIODS)
    for i in PRODUCTS
}

def gams_demand_n(i,n,t,s, demand_override=None):
    base = GAMS_DEM_N[(i,n,t)]
    scale = 1.0
    if demand_override is not None:
        target = float(demand_override.get(i, GAMS_DEMAND_PRODUCT_TOTAL[i]))
        denom = float(GAMS_DEMAND_PRODUCT_TOTAL[i])
        scale = target / denom if denom else 1.0
    return base * scale * GAMS_FDEM[(t,s)]


# ===== v10: TRANSPORTE INTERPLANTA =====
TRUCK_INTERPLANT = ["z1","z2"]
GAMS_CAPCPZ = {"z1":5000.,"z2":10000.}   # kg
GAMS_CCVZ = {"z1":5.,"z2":10.}           # m3
GAMS_CCTZ = {"z1":10,"z2":15}
GAMS_NMAXZ = {"z1":18,"z2":19}
GAMS_PIP = 1.02
GAMS_VIP = .00102

# En el GAMS, PAPP moviliza leche intermedia refrigerada entre plantas.
INTERPLANT_STAGES = ["Refrigeracion_l1","Refrigeracion_l2"]


# ===== v8: DISTRIBUCIÓN Y FLOTAS =====
TRUCK_PCD = ["m1","m2"]
TRUCK_CDC = ["o1","o2","o3"]
GAMS_CAPCP = {"m1":5000.,"m2":10000.}
GAMS_CCT = {"m1":5,"m2":10}
GAMS_NMAXV = {"m1":18,"m2":19}
GAMS_CCV = {"m1":10.,"m2":15.}
GAMS_CAPCCD = {"o1":5000.,"o2":10000.,"o3":12000.}
GAMS_CCTCD = {"o1":5,"o2":10,"o3":15}
GAMS_NMAXVCD = {"o1":16,"o2":16,"o3":15}
GAMS_CCVCD = {"o1":10.,"o2":15.,"o3":20.}
GAMS_PEP = {"mantequilla":1.05,"yogurt":1.02,"leche_past":1.20}
GAMS_VP = {"mantequilla":.00105,"yogurt":.00108,"leche_past":.00106}

# CCD = 2*CCD1 del GAMS.
GAMS_CCD1 = {
 ("mantequilla","k1","semana1"):573,("mantequilla","k1","semana2"):567,("mantequilla","k1","semana3"):579,("mantequilla","k1","semana4"):594,
 ("mantequilla","k2","semana1"):446,("mantequilla","k2","semana2"):441,("mantequilla","k2","semana3"):450,("mantequilla","k2","semana4"):462,
 ("mantequilla","k3","semana1"):573,("mantequilla","k3","semana2"):567,("mantequilla","k3","semana3"):579,("mantequilla","k3","semana4"):594,
 ("mantequilla","k4","semana1"):446,("mantequilla","k4","semana2"):441,("mantequilla","k4","semana3"):450,("mantequilla","k4","semana4"):462,
 ("yogurt","k1","semana1"):8158,("yogurt","k1","semana2"):8265,("yogurt","k1","semana3"):8435,("yogurt","k1","semana4"):8078,
 ("yogurt","k2","semana1"):6345,("yogurt","k2","semana2"):6428,("yogurt","k2","semana3"):6561,("yogurt","k2","semana4"):6283,
 ("yogurt","k3","semana1"):8158,("yogurt","k3","semana2"):8265,("yogurt","k3","semana3"):8435,("yogurt","k3","semana4"):8078,
 ("yogurt","k4","semana1"):6345,("yogurt","k4","semana2"):6428,("yogurt","k4","semana3"):6561,("yogurt","k4","semana4"):6283,
 ("leche_past","k1","semana1"):17155,("leche_past","k1","semana2"):17521,("leche_past","k1","semana3"):17406,("leche_past","k1","semana4"):17370,
 ("leche_past","k2","semana1"):13343,("leche_past","k2","semana2"):13628,("leche_past","k2","semana3"):13538,("leche_past","k2","semana4"):13510,
 ("leche_past","k3","semana1"):17155,("leche_past","k3","semana2"):17521,("leche_past","k3","semana3"):17406,("leche_past","k3","semana4"):17370,
 ("leche_past","k4","semana1"):13343,("leche_past","k4","semana2"):13628,("leche_past","k4","semana3"):13538,("leche_past","k4","semana4"):13510,
}
def gams_ccd(i,k,t):
    return 2.0*GAMS_CCD1[(i,_base_cd(k),t)]

GAMS_PROCESS_COST = {
    "Filtracion_l1":40.,"Refrigeracion_l1":40.,"Pasteurizacion_l1":40.,
    "Filtracion_l2":45.,"Refrigeracion_l2":45.,"Pasteurizacion_l2":45.,
    "Mantecado":20.,"Maduracion":20.,"Homoge_yogurt":20.,"homoge_leche":10.
}
GAMS_INITIAL_PROCESS_INV = {
    "Filtracion_l1":1.,"Refrigeracion_l1":0.,"Pasteurizacion_l1":5.,
    "Filtracion_l2":0.,"Refrigeracion_l2":3.,"Pasteurizacion_l2":0.,
    "Mantecado":0.,"Maduracion":2.,"Homoge_yogurt":0.,"homoge_leche":1.
}

@dataclass
class OptimizerData:
    probabilities: Dict[str, float] = field(default_factory=lambda: DEFAULT_PROB.copy())
    demand: Dict[str, float] = field(default_factory=lambda: GAMS_DEMAND_PRODUCT_TOTAL.copy())
    demand_factor: Dict[str, float] = field(default_factory=lambda: DEFAULT_DEMAND_FACTOR.copy())
    supply_factor: Dict[str, float] = field(default_factory=lambda: DEFAULT_SUPPLY_FACTOR.copy())
    transport_factor: Dict[str, float] = field(default_factory=lambda: DEFAULT_TRANSPORT_FACTOR.copy())
    processing_factor: Dict[str, float] = field(default_factory=lambda: DEFAULT_PROCESSING_FACTOR.copy())
    disruption: Dict[str, float] = field(default_factory=lambda: DEFAULT_DISRUPTION.copy())

    # Dimensión de red elegida por el usuario. No está limitada a la red base 3x4.
    number_of_plants: int = 3
    number_of_cds: int = 4

    fixed_plants: Dict[str, float] = field(default_factory=lambda: DEFAULT_FIXED_PLANT.copy())
    fixed_cds: Dict[str, float] = field(default_factory=lambda: DEFAULT_FIXED_CD.copy())

    # v29: control explícito del diseño.
    # None = diseño libre (HiGHS decide). Dict = fijar cada binaria YP/YCD a 0/1.
    plant_design_status: Optional[Dict[str, int]] = None
    cd_design_status: Optional[Dict[str, int]] = None

    capacity_per_plant: float = 55000.
    capacity_per_cd: float = 45000.
    production_unit_cost: Dict[str, float] = field(default_factory=lambda: {
        "mantequilla": 7600., "yogurt": 2650., "leche_past": 1800.
    })
    transport_unit_cost: Dict[str, float] = field(default_factory=lambda: {
        "mantequilla": 320., "yogurt": 210., "leche_past": 170.
    })
    inventory_unit_cost: Dict[str, float] = field(default_factory=lambda: {
        "mantequilla": 45., "yogurt": 32., "leche_past": 25.
    })

    eps_y: float = .10
    xD0: float = .10
    share_max: float = .60
    lam1: float = .20
    eta1: float = .30
    eta2: float = .30
    eta3: float = .30
    lamM: float = .10
    phiM: float = .20
    gammaM: float = .050
    cA: float = 1.0
    cU: float = .1
    cR: float = .01
    cP: float = 10.0
    Mbig: float = 1e6
    theta: float = .65
    alpha: float = .75
    rhoR: float = 2.0
    profit_min: float = 9.5e8
    penalty_short_factor: float = 1.05

    # Si True reproduce la FO activa del GAMS entregado: ViolY NO se penaliza.
    # Si False permite experimentar luego con la formulación del artículo.
    exact_active_gams_homeostasis: bool = True
    homeostasis_penalty: float = 1e7

    @classmethod
    def from_gams_defaults(cls) -> "OptimizerData":
        return cls()

    def normalized(self) -> "OptimizerData":
        out = OptimizerData(**asdict(self))
        out.number_of_plants = max(1, int(self.number_of_plants))
        out.number_of_cds = max(1, int(self.number_of_cds))
        plants = make_plants(out.number_of_plants)
        cds = make_cds(out.number_of_cds)
        # Conserva los valores GAMS originales y extiende nuevos nodos con perfiles base.
        out.fixed_plants = {j: float((self.fixed_plants or {}).get(j, DEFAULT_FIXED_PLANT[_base_plant(j)])) for j in plants}
        out.fixed_cds = {k: float((self.fixed_cds or {}).get(k, DEFAULT_FIXED_CD[_base_cd(k)])) for k in cds}
        p = {s: max(0.0, float(self.probabilities.get(s, 0.0))) for s in SCENARIOS}
        z = sum(p.values()) or 1.0
        out.probabilities = {s: p[s] / z for s in SCENARIOS}
        for attr in ("demand_factor", "supply_factor", "transport_factor", "processing_factor", "disruption"):
            src = getattr(self, attr, {}) or {}
            setattr(out, attr, {s: float(src.get(s, getattr(out, attr)[s])) for s in SCENARIOS})

        if self.plant_design_status is not None:
            out.plant_design_status = {
                j: 1 if int(self.plant_design_status.get(j, 0)) else 0 for j in plants
            }
        if self.cd_design_status is not None:
            out.cd_design_status = {
                k: 1 if int(self.cd_design_status.get(k, 0)) else 0 for k in cds
            }
        return out

def _require_pyomo():
    try:
        import pyomo.environ as pyo
        return pyo
    except ImportError as exc:
        raise RuntimeError(
            "Falta Pyomo. En CMD ejecuta: python -m pip install pyomo highspy"
        ) from exc

def build_model(data: OptimizerData):
    pyo = _require_pyomo()
    d = data.normalized()
    plants = make_plants(d.number_of_plants)
    cds = make_cds(d.number_of_cds)
    m = pyo.ConcreteModel("URSP_SCIS_Dairy_v36_1_GAMSExactEU_InnONAudit")

    m.S = pyo.Set(initialize=SCENARIOS, ordered=True)
    m.T = pyo.Set(initialize=PERIODS, ordered=True)
    m.I = pyo.Set(initialize=PRODUCTS, ordered=True)
    m.J = pyo.Set(initialize=plants, ordered=True)
    m.K = pyo.Set(initialize=cds, ordered=True)
    m.N = pyo.Set(initialize=CONSUMERS, ordered=True)
    m.QP = pyo.Set(initialize=PROCESS_STAGES, ordered=True)
    m.M = pyo.Set(initialize=TRUCK_PCD, ordered=True)
    m.O = pyo.Set(initialize=TRUCK_CDC, ordered=True)
    m.A = pyo.Set(initialize=RAW_MILKS, ordered=True)
    m.H = pyo.Set(initialize=FARMS, ordered=True)
    m.L = pyo.Set(initialize=TRUCK_HATO, ordered=True)
    m.Z = pyo.Set(initialize=TRUCK_INTERPLANT, ordered=True)
    m.QZ = pyo.Set(initialize=INTERPLANT_STAGES, ordered=True)

    # Pares interplanta realmente utilizables. El GAMS prohíbe j=jp;
    # no creamos esas variables para después fijarlas a cero.
    m.JJ = pyo.Set(
        dimen=2,
        initialize=[(j, jp) for j in plants for jp in plants if j != jp],
        ordered=True,
    )

    m.ps = pyo.Param(m.S, initialize=d.probabilities)
    m.ing = pyo.Param(m.I, initialize=DEFAULT_ING)
    m.fixedP = pyo.Param(m.J, initialize=d.fixed_plants)
    m.fixedCD = pyo.Param(m.K, initialize=d.fixed_cds)

    # Demanda escenario-dependiente, como debe ocurrir en la formulación estocástica.
    m.D = pyo.Param(
        m.I, m.N, m.T, m.S,
        initialize=lambda m, i, n, t, s: gams_demand_n(i,n,t,s,d.demand)
    )

    # Diseño de red.
    m.YP = pyo.Var(m.J, within=pyo.Binary)
    m.YCD = pyo.Var(m.K, within=pyo.Binary)

    # v29: si la interfaz solicita diseño fijado, fijar las binarias reales.
    # Esto NO altera los costos fijos; obliga matemáticamente YP/ YCD = 0 o 1.
    if d.plant_design_status is not None:
        for j in plants:
            m.YP[j].fix(1 if int(d.plant_design_status.get(j, 0)) else 0)
    if d.cd_design_status is not None:
        for k in cds:
            m.YCD[k].fix(1 if int(d.cd_design_status.get(k, 0)) else 0)

    # Recolección Hato -> Planta (XH/NVCH del GAMS).
    m.XH = pyo.Var(m.A,m.H,m.J,m.L,m.T,m.S,within=pyo.NonNegativeReals)
    # Cotas superiores implícitas en las restricciones de flota del GAMS.
    # No cambian la región factible; ayudan a HiGHS a acotar los enteros.
    m.NVCH = pyo.Var(
        m.L,m.H,m.J,m.T,m.S,
        within=pyo.NonNegativeIntegers,
        bounds=lambda m,l,h,j,t,s: (0, GAMS_CCTH[l]*GAMS_NMAXVH[l])
    )
    m.raw_in = pyo.Var(m.A,m.J,m.T,m.S,within=pyo.NonNegativeReals)
    m.raw_filter = pyo.Var(m.A, ["Filtracion_l1","Filtracion_l2"], m.J,m.T,m.S, within=pyo.NonNegativeReals)

    # PAPP/NVPP: flujo y viajes entre plantas.
    m.PAPP = pyo.Var(m.JJ,m.QZ,m.T,m.S,within=pyo.NonNegativeReals)
    m.NVPP = pyo.Var(
        m.Z,m.JJ,m.T,m.S,
        within=pyo.NonNegativeIntegers,
        bounds=lambda m,z,j,jp,t,s: (0, GAMS_CCTZ[z]*GAMS_NMAXZ[z])
    )

    # Operación.
    m.prod = pyo.Var(m.I, m.J, m.T, m.S, within=pyo.NonNegativeReals)
    m.xr_final = pyo.Var(m.I, m.J, m.T, m.S, within=pyo.NonNegativeReals)
    m.xe_final = pyo.Var(m.I, m.J, m.T, m.S, within=pyo.NonNegativeReals)
    m.sub = pyo.Var(m.I, m.J, m.T, m.S, within=pyo.NonNegativeReals)
    m.buffer = pyo.Var(m.I, m.J, m.T, m.S, within=pyo.NonNegativeReals)
    # XR/XE e inventarios de procesos intermedios.
    m.xr_proc = pyo.Var(m.QP, m.J, m.T, m.S, within=pyo.NonNegativeReals)
    m.xe_proc = pyo.Var(m.QP, m.J, m.T, m.S, within=pyo.NonNegativeReals)
    m.inv_proc = pyo.Var(m.QP, m.J, m.T, m.S, bounds=(0,500))
    # PAP: flujos entre procesos. Se declaran solo los arcos activos de la formulación.
    m.pap_f1_r1 = pyo.Var(m.J,m.T,m.S,within=pyo.NonNegativeReals)
    m.pap_r1_p1 = pyo.Var(m.J,m.T,m.S,within=pyo.NonNegativeReals)
    m.pap_p1_mante = pyo.Var(m.J,m.T,m.S,within=pyo.NonNegativeReals)
    m.pap_p1_madur = pyo.Var(m.J,m.T,m.S,within=pyo.NonNegativeReals)
    m.pap_f2_r2 = pyo.Var(m.J,m.T,m.S,within=pyo.NonNegativeReals)
    m.pap_r2_p2 = pyo.Var(m.J,m.T,m.S,within=pyo.NonNegativeReals)
    m.pap_p2_madur = pyo.Var(m.J,m.T,m.S,within=pyo.NonNegativeReals)
    m.pap_p2_holec = pyo.Var(m.J,m.T,m.S,within=pyo.NonNegativeReals)
    m.pap_mante_env = pyo.Var(m.J,m.T,m.S,within=pyo.NonNegativeReals)
    m.pap_madur_hoyog = pyo.Var(m.J,m.T,m.S,within=pyo.NonNegativeReals)
    m.pap_hoyog_env = pyo.Var(m.J,m.T,m.S,within=pyo.NonNegativeReals)
    m.pap_holec_env = pyo.Var(m.J,m.T,m.S,within=pyo.NonNegativeReals)
    m.ship = pyo.Var(m.I, m.J, m.K, m.T, m.S, within=pyo.NonNegativeReals)
    m.delivery = pyo.Var(m.I, m.K, m.N, m.T, m.S, within=pyo.NonNegativeReals)
    m.trip_pcd = pyo.Var(
        m.M, m.J, m.K, m.T, m.S,
        within=pyo.NonNegativeIntegers,
        bounds=lambda m,mm,j,k,t,s: (0, GAMS_CCT[mm]*GAMS_NMAXV[mm])
    )
    # Cota entera reforzada directamente por DISPONIBTRANSCD del GAMS.
    # Como trip_cdc es entera y:
    # NVCC <= NMAXVCD*CCTCD*AvailCDC,
    # floor(RHS) es una cota superior válida y NO cambia la región factible.
    m.trip_cdc = pyo.Var(
        m.O, m.K, m.N, m.T, m.S,
        within=pyo.NonNegativeIntegers,
        bounds=lambda m,o,k,n,t,s: (
            0,
            math.floor(
                GAMS_CCTCD[o]*GAMS_NMAXVCD[o]*GAMS_AVAIL_CDC[(t,s)]
                + 1e-9
            )
        )
    )
    m.short = pyo.Var(m.I, m.N, m.T, m.S, within=pyo.NonNegativeReals)
    m.inv = pyo.Var(m.I, m.K, m.T, m.S, within=pyo.NonNegativeReals)
    m.overtime = pyo.Var(m.T, m.S, within=pyo.NonNegativeReals)

    # SCIS.
    m.DemTot = pyo.Var(m.T, m.S, within=pyo.NonNegativeReals)
    m.ShipTot = pyo.Var(m.T, m.S, within=pyo.NonNegativeReals)
    m.EY = pyo.Var(m.T, m.S, within=pyo.NonNegativeReals)
    m.EU = pyo.Var(m.T, m.S, within=pyo.NonNegativeReals)
    m.Rdes = pyo.Var(bounds=(0, 1))
    # v32: GAMS declara Ddes como Positive Variable y solo impone Ddes >= Rdes.
    # No existe Ddes.up en el archivo fuente.
    m.Ddes = pyo.Var(within=pyo.NonNegativeReals)
    m.Vsdes = pyo.Var(bounds=(0, 1))
    m.xB = pyo.Var(m.T, m.S, within=pyo.NonNegativeReals)
    m.InnON = pyo.Var(m.T, m.S, within=pyo.Binary)
    # v34 SCIS CORREGIDO:
    # El GAMS documenta zInn como "Estímulo innato (Eq7 proxy, 0-1)".
    # En esta variante funcional se hace explícito ese dominio semántico.
    # NOTA: esto es una corrección intencional; la réplica literal queda en v33.
    m.zInn = pyo.Var(m.T, m.S, bounds=(0, 1))
    m.Mmem = pyo.Var(m.T, m.S, within=pyo.NonNegativeReals)
    m.Deff = pyo.Var(m.T, m.S, within=pyo.NonNegativeReals)
    m.ViolY = pyo.Var(m.T, m.S, within=pyo.NonNegativeReals)
    m.Pperf = pyo.Var(m.T, m.S, bounds=(0, 1))
    m.Out = pyo.Var(m.T, m.S, within=pyo.Binary)
    m.Aact = pyo.Var(m.T, m.S, within=pyo.NonNegativeReals)
    m.Uact = pyo.Var(m.T, m.S, within=pyo.NonNegativeReals)
    m.Rbuf = pyo.Var(m.T, m.S, within=pyo.NonNegativeReals)
    m.Cadapt = pyo.Var(m.S, within=pyo.NonNegativeReals)

    # v34: semana0 es condición inicial, no un periodo de activación SCIS.
    for s in SCENARIOS:
        m.zInn[PERIODS[0], s].fix(0.0)

    # Economía / riesgo.
    m.FOSP = pyo.Var(m.S)
    m.Loss = pyo.Var(m.S)
    m.eta = pyo.Var()
    m.zeta = pyo.Var(m.S, within=pyo.NonNegativeReals)
    m.FO = pyo.Var()

    # Demanda, entregas y faltantes.
    m.dem_total = pyo.Constraint(
        m.T, m.S,
        rule=lambda m, t, s: m.DemTot[t, s] == sum(m.D[i, n, t, s] for i in m.I for n in m.N)
    )
    m.ship_total = pyo.Constraint(
        m.T, m.S,
        rule=lambda m, t, s: m.ShipTot[t, s] ==
        sum(m.delivery[i, k, n, t, s] for i in m.I for k in m.K for n in m.N)
    )
    m.short_def = pyo.Constraint(
        m.T, m.S,
        rule=lambda m, t, s: m.EY[t, s] == sum(m.short[i, n, t, s] for i in m.I for n in m.N)
    )
    m.demand_balance = pyo.Constraint(
        m.I, m.N, m.T, m.S,
        rule=lambda m, i, n, t, s:
        sum(m.delivery[i, k, n, t, s] for k in m.K) + m.short[i, n, t, s]
        == m.D[i, n, t, s]
    )

    # Capacidad de producción y disponibilidad de suministro.
    def _final_q(i):
        return {"mantequilla":"Envase_mantequilla", "yogurt":"Envase_yogurt", "leche_past":"Envase_leche"}[i]

    def final_regular_cap_rule(m, i, j, t, s):
        q = _final_q(i)
        cap = GAMS_PACK_CAP[(i,_base_plant(j))] * GAMS_ENV[(i,t,s)] * gams_fproc(q,j,t,s)
        return m.xr_final[i,j,t,s] <= cap * m.YP[j]
    m.final_regular_cap = pyo.Constraint(m.I, m.J, m.T, m.S, rule=final_regular_cap_rule)

    # GAMS: CAPXE = 0.05*CAPXRAjus.
    def final_overtime_cap_rule(m, i, j, t, s):
        q = _final_q(i)
        cap = GAMS_PACK_CAP[(i,_base_plant(j))] * GAMS_ENV[(i,t,s)] * gams_fproc(q,j,t,s)
        return m.xe_final[i,j,t,s] <= 0.05 * cap * m.YP[j]
    m.final_overtime_cap = pyo.Constraint(m.I, m.J, m.T, m.S, rule=final_overtime_cap_rule)

    # GAMS: XS <= MAXSUB*YP.
    m.sub_cap = pyo.Constraint(
        m.I, m.J, m.T, m.S,
        rule=lambda m,i,j,t,s: m.sub[i,j,t,s] <= GAMS_MAXSUB[(i,_base_plant(j))] * m.YP[j]
    )

    # GAMS final-product equation:
    # XR(envase)+XE(envase)+XS = XPF.
    m.final_product_balance = pyo.Constraint(
        m.I, m.J, m.T, m.S,
        rule=lambda m,i,j,t,s:
        m.prod[i,j,t,s] == m.xr_final[i,j,t,s] + m.xe_final[i,j,t,s] + m.sub[i,j,t,s]
    )

    # Stack-buffer capacity from CAPSB.
    m.buffer_cap = pyo.Constraint(
        m.I, m.J, m.T, m.S,
        rule=lambda m,i,j,t,s: m.buffer[i,j,t,s] <= GAMS_BUFFER_CAP[(i,_base_plant(j))]
    )

    # Capacidades XR/XE de procesos intermedios: CAPXRAjus y CAPXE=5%.
    def proc_reg_cap_rule(m,q,j,t,s):
        cap = GAMS_PROCESS_BASE_CAP[q][_base_plant(j)] * gams_fproc(q,j,t,s)
        return m.xr_proc[q,j,t,s] <= cap*m.YP[j]
    m.proc_reg_cap = pyo.Constraint(m.QP,m.J,m.T,m.S,rule=proc_reg_cap_rule)

    def proc_ot_cap_rule(m,q,j,t,s):
        cap = GAMS_PROCESS_BASE_CAP[q][_base_plant(j)] * gams_fproc(q,j,t,s)
        return m.xe_proc[q,j,t,s] <= .05*cap*m.YP[j]
    m.proc_ot_cap = pyo.Constraint(m.QP,m.J,m.T,m.S,rule=proc_ot_cap_rule)

    def _prev_inv(m,q,j,t,s):
        idx = PERIODS.index(t)
        return GAMS_INITIAL_PROCESS_INV[q] if idx == 0 else m.inv_proc[q,j,PERIODS[idx-1],s]

    # Línea 1: filtración -> refrigeración -> pasteurización -> mantequilla/yogurt.
    m.bal_f1 = pyo.Constraint(m.J,m.T,m.S,rule=lambda m,j,t,s:
        .99*(m.xr_proc["Filtracion_l1",j,t,s]+m.xe_proc["Filtracion_l1",j,t,s]) + _prev_inv(m,"Filtracion_l1",j,t,s)
        == m.pap_f1_r1[j,t,s] + m.inv_proc["Filtracion_l1",j,t,s])
    m.bal_r1 = pyo.Constraint(m.J,m.T,m.S,rule=lambda m,j,t,s:
        m.pap_f1_r1[j,t,s] + _prev_inv(m,"Refrigeracion_l1",j,t,s)
        == m.xr_proc["Refrigeracion_l1",j,t,s]+m.xe_proc["Refrigeracion_l1",j,t,s]+m.inv_proc["Refrigeracion_l1",j,t,s])
    m.out_r1 = pyo.Constraint(m.J,m.T,m.S,rule=lambda m,j,t,s:
        m.xr_proc["Refrigeracion_l1",j,t,s]+m.xe_proc["Refrigeracion_l1",j,t,s]+_prev_inv(m,"Refrigeracion_l1",j,t,s)-m.inv_proc["Refrigeracion_l1",j,t,s]
        == m.pap_r1_p1[j,t,s] + sum(m.PAPP[j,jp,"Refrigeracion_l1",t,s] for jp in m.J if jp != j))
    # GAMS Rest_equ_pasteu_l1:
    # 0.98*sum(jp,PAPP(j,jp,"Refrigeracion_l1",t,s))
    # + PAP(Refrigeracion_l1,Pasteurizacion_l1,...) + inventario previo
    # = XR + XE + inventario final.
    # Se conserva literalmente la orientación (j,jp) escrita en el GAMS.
    m.bal_p1 = pyo.Constraint(m.J,m.T,m.S,rule=lambda m,j,t,s:
        .98*sum(m.PAPP[j,jp,"Refrigeracion_l1",t,s] for jp in m.J if jp != j)
        + m.pap_r1_p1[j,t,s]
        + _prev_inv(m,"Pasteurizacion_l1",j,t,s)
        == m.xr_proc["Pasteurizacion_l1",j,t,s]+m.xe_proc["Pasteurizacion_l1",j,t,s]+m.inv_proc["Pasteurizacion_l1",j,t,s])
    m.out_p1 = pyo.Constraint(m.J,m.T,m.S,rule=lambda m,j,t,s:
        m.xr_proc["Pasteurizacion_l1",j,t,s]+m.xe_proc["Pasteurizacion_l1",j,t,s]+_prev_inv(m,"Pasteurizacion_l1",j,t,s)-m.inv_proc["Pasteurizacion_l1",j,t,s]
        == m.pap_p1_mante[j,t,s]+m.pap_p1_madur[j,t,s])

    # Mantequilla: rendimiento 0.08.
    m.bal_mante = pyo.Constraint(m.J,m.T,m.S,rule=lambda m,j,t,s:
        .08*m.pap_p1_mante[j,t,s] + _prev_inv(m,"Mantecado",j,t,s)
        == m.xr_proc["Mantecado",j,t,s]+m.xe_proc["Mantecado",j,t,s]+m.inv_proc["Mantecado",j,t,s])
    m.out_mante = pyo.Constraint(m.J,m.T,m.S,rule=lambda m,j,t,s:
        m.xr_proc["Mantecado",j,t,s]+m.xe_proc["Mantecado",j,t,s]+_prev_inv(m,"Mantecado",j,t,s)-m.inv_proc["Mantecado",j,t,s]
        == m.pap_mante_env[j,t,s])
    m.link_butter = pyo.Constraint(m.J,m.T,m.S,rule=lambda m,j,t,s:
        m.pap_mante_env[j,t,s] == m.xr_final["mantequilla",j,t,s]+m.xe_final["mantequilla",j,t,s])

    # Línea 2: filtración -> refrigeración -> pasteurización.
    m.bal_f2 = pyo.Constraint(m.J,m.T,m.S,rule=lambda m,j,t,s:
        .99*(m.xr_proc["Filtracion_l2",j,t,s]+m.xe_proc["Filtracion_l2",j,t,s]) + _prev_inv(m,"Filtracion_l2",j,t,s)
        == m.pap_f2_r2[j,t,s] + m.inv_proc["Filtracion_l2",j,t,s])
    m.bal_r2 = pyo.Constraint(m.J,m.T,m.S,rule=lambda m,j,t,s:
        m.pap_f2_r2[j,t,s] + _prev_inv(m,"Refrigeracion_l2",j,t,s)
        == m.xr_proc["Refrigeracion_l2",j,t,s]+m.xe_proc["Refrigeracion_l2",j,t,s]+m.inv_proc["Refrigeracion_l2",j,t,s])
    m.out_r2 = pyo.Constraint(m.J,m.T,m.S,rule=lambda m,j,t,s:
        m.xr_proc["Refrigeracion_l2",j,t,s]+m.xe_proc["Refrigeracion_l2",j,t,s]+_prev_inv(m,"Refrigeracion_l2",j,t,s)-m.inv_proc["Refrigeracion_l2",j,t,s]
        == m.pap_r2_p2[j,t,s] + sum(m.PAPP[j,jp,"Refrigeracion_l2",t,s] for jp in m.J if jp != j))
    # GAMS Rest_equ_pasteu_l2: misma orientación literal (j,jp) y rendimiento 0.98.
    m.bal_p2 = pyo.Constraint(m.J,m.T,m.S,rule=lambda m,j,t,s:
        .98*sum(m.PAPP[j,jp,"Refrigeracion_l2",t,s] for jp in m.J if jp != j)
        + m.pap_r2_p2[j,t,s]
        + _prev_inv(m,"Pasteurizacion_l2",j,t,s)
        == m.xr_proc["Pasteurizacion_l2",j,t,s]+m.xe_proc["Pasteurizacion_l2",j,t,s]+m.inv_proc["Pasteurizacion_l2",j,t,s])
    m.out_p2 = pyo.Constraint(m.J,m.T,m.S,rule=lambda m,j,t,s:
        m.xr_proc["Pasteurizacion_l2",j,t,s]+m.xe_proc["Pasteurizacion_l2",j,t,s]+_prev_inv(m,"Pasteurizacion_l2",j,t,s)-m.inv_proc["Pasteurizacion_l2",j,t,s]
        == m.pap_p2_madur[j,t,s]+m.pap_p2_holec[j,t,s])

    # Yogurt: 0.65 desde línea 1 + flujo de línea 2.
    m.bal_madur = pyo.Constraint(m.J,m.T,m.S,rule=lambda m,j,t,s:
        .65*m.pap_p1_madur[j,t,s] + m.pap_p2_madur[j,t,s] + _prev_inv(m,"Maduracion",j,t,s)
        == m.xr_proc["Maduracion",j,t,s]+m.xe_proc["Maduracion",j,t,s]+m.inv_proc["Maduracion",j,t,s])
    m.out_madur = pyo.Constraint(m.J,m.T,m.S,rule=lambda m,j,t,s:
        m.xr_proc["Maduracion",j,t,s]+m.xe_proc["Maduracion",j,t,s]+_prev_inv(m,"Maduracion",j,t,s)-m.inv_proc["Maduracion",j,t,s]
        == m.pap_madur_hoyog[j,t,s])
    m.bal_hoyog = pyo.Constraint(m.J,m.T,m.S,rule=lambda m,j,t,s:
        m.pap_madur_hoyog[j,t,s] + _prev_inv(m,"Homoge_yogurt",j,t,s)
        == m.xr_proc["Homoge_yogurt",j,t,s]+m.xe_proc["Homoge_yogurt",j,t,s]+m.inv_proc["Homoge_yogurt",j,t,s])
    m.out_hoyog = pyo.Constraint(m.J,m.T,m.S,rule=lambda m,j,t,s:
        m.xr_proc["Homoge_yogurt",j,t,s]+m.xe_proc["Homoge_yogurt",j,t,s]+_prev_inv(m,"Homoge_yogurt",j,t,s)-m.inv_proc["Homoge_yogurt",j,t,s]
        == m.pap_hoyog_env[j,t,s])
    m.link_yogurt = pyo.Constraint(m.J,m.T,m.S,rule=lambda m,j,t,s:
        m.pap_hoyog_env[j,t,s] == m.xr_final["yogurt",j,t,s]+m.xe_final["yogurt",j,t,s])

    # Leche pasteurizada: rendimiento 0.99 en homogeneización.
    m.bal_holec = pyo.Constraint(m.J,m.T,m.S,rule=lambda m,j,t,s:
        .99*m.pap_p2_holec[j,t,s] + _prev_inv(m,"homoge_leche",j,t,s)
        == m.xr_proc["homoge_leche",j,t,s]+m.xe_proc["homoge_leche",j,t,s]+m.inv_proc["homoge_leche",j,t,s])
    m.out_holec = pyo.Constraint(m.J,m.T,m.S,rule=lambda m,j,t,s:
        m.xr_proc["homoge_leche",j,t,s]+m.xe_proc["homoge_leche",j,t,s]+_prev_inv(m,"homoge_leche",j,t,s)-m.inv_proc["homoge_leche",j,t,s]
        == m.pap_holec_env[j,t,s])
    m.link_milk = pyo.Constraint(m.J,m.T,m.S,rule=lambda m,j,t,s:
        m.pap_holec_env[j,t,s] == m.xr_final["leche_past",j,t,s]+m.xe_final["leche_past",j,t,s])

    # CD y transporte: XTECD (planta->CD), XTCDC agregado (CD->mercado), NVC y NVCC.
    # Capacidad de inventario/uso del CD: CCD = 2*CCD1.
    m.cd_inv_cap = pyo.Constraint(
        m.I,m.K,m.T,m.S,
        rule=lambda m,i,k,t,s: m.inv[i,k,t,s] <= gams_ccd(i,k,t)*m.YCD[k]
    )
    m.cd_use_cap = pyo.Constraint(
        m.I,m.K,m.T,m.S,
        rule=lambda m,i,k,t,s: sum(m.delivery[i,k,n,t,s] for n in m.N) <= gams_ccd(i,k,t)*m.YCD[k]
    )

    # Balance del CD: XTECD + inventario previo = XTCDC + inventario actual.
    def cd_balance_rule(m,i,k,t,s):
        idx = PERIODS.index(t)
        prev = 0.0 if idx == 0 else m.inv[i,k,PERIODS[idx-1],s]
        return sum(m.ship[i,j,k,t,s] for j in m.J) + prev == sum(m.delivery[i,k,n,t,s] for n in m.N) + m.inv[i,k,t,s]
    m.cd_balance = pyo.Constraint(m.I,m.K,m.T,m.S,rule=cd_balance_rule)

    # Flota planta->CD. Semántica temporal fiel al GAMS (LEAD0=1).
    m.fleet_pcd = pyo.Constraint(
        m.M,m.T,m.S,
        rule=lambda m,mm,t,s: sum(m.trip_pcd[mm,j,k,t,s] for j in m.J for k in m.K)
        <= GAMS_CCT[mm]*GAMS_NMAXV[mm]
    )
    # CAP_CARG_PCD_KG: capacidad base con CCT.
    def pcd_kg_base_rule(m,mm,j,k,t,s):
        # Semana2..4: pcd_lead_cap es más fuerte porque GAMS_CCT[mm] > 1.
        if PERIODS.index(t) != 0:
            return pyo.Constraint.Skip
        return sum(GAMS_PEP[i]*m.ship[i,j,k,t,s] for i in m.I) <= GAMS_CAPCP[mm]*m.trip_pcd[mm,j,k,t,s]*GAMS_CCT[mm]
    m.pcd_kg_base = pyo.Constraint(m.M,m.J,m.K,m.T,m.S,rule=pcd_kg_base_rule)
    # C_CARG_PCD_MAX_VOL: no depende de NVC.
    m.pcd_vol_cap = pyo.Constraint(
        m.M,m.J,m.K,m.T,m.S,
        rule=lambda m,mm,j,k,t,s:
        sum(GAMS_VP[i]*m.ship[i,j,k,t,s] for i in m.I)
        <= GAMS_CCT[mm]*GAMS_CCV[mm]*GAMS_NMAXV[mm]
    )
    # CAPACIDADTRAN: TA(t)>LEAD0=1 => semana2..semana4, sin CCT.
    def pcd_lead_rule(m,mm,j,k,t,s):
        if PERIODS.index(t) == 0:
            return pyo.Constraint.Skip
        return sum(GAMS_PEP[i]*m.ship[i,j,k,t,s] for i in m.I) <= GAMS_CAPCP[mm]*m.trip_pcd[mm,j,k,t,s]
    m.pcd_lead_cap = pyo.Constraint(m.M,m.J,m.K,m.T,m.S,rule=pcd_lead_rule)

    # Flota CD->CC: semántica GAMS de LEAD2=1.
    m.fleet_cdc = pyo.Constraint(
        m.O,m.T,m.S,
        rule=lambda m,o,t,s: sum(m.trip_cdc[o,k,n,t,s] for k in m.K for n in m.N)
        <= GAMS_CCTCD[o]*GAMS_NMAXVCD[o]
    )
    def cdc_availability_rule(m,o,k,n,t,s):
        if PERIODS.index(t) == 0:
            return pyo.Constraint.Skip
        return m.trip_cdc[o,k,n,t,s] <= GAMS_NMAXVCD[o]*GAMS_CCTCD[o]*GAMS_AVAIL_CDC[(t,s)]
    # v27: la restricción explícita DISPONIBTRANSCD se omite porque
    # trip_cdc ya es entero y tiene ub=floor(CCTCD*NMAXVCD*AvailCDC).
    # Para x entero: x <= R <=> x <= floor(R).
    m.cdc_availability = pyo.Constraint(m.O,m.K,m.N,m.T,m.S,
        rule=lambda m,o,k,n,t,s: pyo.Constraint.Skip)

    # CAP_CARG_CDC_KG.
    # Semana1: solo existe la capacidad base.
    # Semana2..4: si CCTCD*AvailCDC >= 1, la restricción lead (sin ese
    # multiplicador) es igual o más fuerte y esta base es redundante.
    # Si CCTCD*AvailCDC < 1, la base es más fuerte y se conserva.
    def cdc_kg_base_rule(m,o,k,n,t,s):
        mult = GAMS_CCTCD[o]*GAMS_AVAIL_CDC[(t,s)]
        if PERIODS.index(t) != 0 and mult >= 1.0 - 1e-12:
            return pyo.Constraint.Skip
        return (
            sum(GAMS_PEP[i]*m.delivery[i,k,n,t,s] for i in m.I)
            <= GAMS_CAPCCD[o]*mult*m.trip_cdc[o,k,n,t,s]
        )
    m.cdc_kg_base = pyo.Constraint(m.O,m.K,m.N,m.T,m.S,rule=cdc_kg_base_rule)
    # C_CARG_CDC_MAX_VOL: no depende de NVCC.
    m.cdc_vol_cap = pyo.Constraint(
        m.O,m.K,m.N,m.T,m.S,
        rule=lambda m,o,k,n,t,s:
        sum(GAMS_VP[i]*m.delivery[i,k,n,t,s] for i in m.I)
        <= GAMS_CCTCD[o]*GAMS_CCVCD[o]*GAMS_NMAXVCD[o]*GAMS_AVAIL_CDC[(t,s)]
    )
    # CAPACIDADTRANCC: semana2..4, sin CCTCD ni AvailCDC.
    # Si CCTCD*AvailCDC <= 1, la capacidad base es igual o más fuerte,
    # por lo que no se duplica la restricción lead.
    def cdc_lead_rule(m,o,k,n,t,s):
        if PERIODS.index(t) == 0:
            return pyo.Constraint.Skip
        mult = GAMS_CCTCD[o]*GAMS_AVAIL_CDC[(t,s)]
        if mult <= 1.0 + 1e-12:
            return pyo.Constraint.Skip
        return sum(GAMS_PEP[i]*m.delivery[i,k,n,t,s] for i in m.I) <= GAMS_CAPCCD[o]*m.trip_cdc[o,k,n,t,s]
    m.cdc_lead_cap = pyo.Constraint(m.O,m.K,m.N,m.T,m.S,rule=cdc_lead_rule)

    # No se puede despachar más que lo producido.
    def stack_buffer_rule(m, i, j, t, s):
        idx = PERIODS.index(t)
        prev = 0.0 if idx == 0 else m.buffer[i,j,PERIODS[idx-1],s]
        return m.prod[i,j,t,s] + prev == sum(m.ship[i,j,k,t,s] for k in m.K) + m.buffer[i,j,t,s]
    m.stack_buffer_balance = pyo.Constraint(m.I, m.J, m.T, m.S, rule=stack_buffer_rule)

    # Máximo activo del GAMS.
    m.max_cds = pyo.Constraint(expr=sum(m.YCD[k] for k in m.K) <= 3)

    # Hatos -> Planta: oferta, balance de leche y flota de recolección.
    def farm_supply_rule(m,h,a,t,s):
        return sum(m.XH[a,h,j,l,t,s] for j in m.J for l in m.L) <= gams_ofh(h,a,t,s)
    m.farm_supply = pyo.Constraint(m.H,m.A,m.T,m.S,rule=farm_supply_rule)

    def raw_in_rule(m,a,j,t,s):
        return m.raw_in[a,j,t,s] == sum(m.XH[a,h,j,l,t,s] for h in m.H for l in m.L)
    m.raw_in_balance = pyo.Constraint(m.A,m.J,m.T,m.S,rule=raw_in_rule)

    # Balance GAMS por tipo de leche:
    # sum(h,l) XH(a,h,j,l,t,s) = X(a,j,Filtracion_l1,t,s) + X(a,j,Filtracion_l2,t,s)
    m.raw_to_filters = pyo.Constraint(
        m.A,m.J,m.T,m.S,
        rule=lambda m,a,j,t,s:
        m.raw_in[a,j,t,s] ==
        m.raw_filter[a,"Filtracion_l1",j,t,s] +
        m.raw_filter[a,"Filtracion_l2",j,t,s]
    )

    # Entrada total de cada línea. Esta versión elimina la asignación artificial
    # leche1->l1 y leche2->l2 que existía en v9-v13.
    m.filter_input_l1 = pyo.Constraint(
        m.J,m.T,m.S,
        rule=lambda m,j,t,s:
        sum(m.raw_filter[a,"Filtracion_l1",j,t,s] for a in m.A)
        == m.xr_proc["Filtracion_l1",j,t,s] + m.xe_proc["Filtracion_l1",j,t,s]
    )
    m.filter_input_l2 = pyo.Constraint(
        m.J,m.T,m.S,
        rule=lambda m,j,t,s:
        sum(m.raw_filter[a,"Filtracion_l2",j,t,s] for a in m.A)
        == m.xr_proc["Filtracion_l2",j,t,s] + m.xe_proc["Filtracion_l2",j,t,s]
    )

    # Número total de viajes por tipo de carrotanque.
    m.farm_fleet = pyo.Constraint(
        m.L,m.T,m.S,
        rule=lambda m,l,t,s:
        sum(m.NVCH[l,h,j,t,s] for h in m.H for j in m.J)
        <= GAMS_CCTH[l]*GAMS_NMAXVH[l]
    )

    # Capacidad kg y volumen. Se conserva la estructura activa del GAMS,
    # incluyendo el multiplicador CCTH en estas dos restricciones.
    def farm_kg_cap_rule(m,a,h,j,l,t,s):
        # Semana2..4: farm_lead_cap es más fuerte porque GAMS_CCTH[l] > 1.
        if PERIODS.index(t) != 0:
            return pyo.Constraint.Skip
        return GAMS_PEH[a]*m.XH[a,h,j,l,t,s] <= GAMS_CAPCHT[l]*m.NVCH[l,h,j,t,s]*GAMS_CCTH[l]
    m.farm_kg_cap = pyo.Constraint(m.A,m.H,m.J,m.L,m.T,m.S,rule=farm_kg_cap_rule)
    # farm_vol_cap del GAMS no se instancia aquí porque es algebraicamente
    # idéntica a farm_kg_cap con los datos activos:
    # VEH[a] = PEH[a]/1000 y CAPCH[l] = CAPCHT[l]/1000.
    # Por tanto, ambas restricciones definen exactamente la misma cota.


    # CAPACIDADTRAN_Hatos: LEAD1=1, semana2..4, sin CCTH.
    def farm_lead_rule(m,a,h,j,l,t,s):
        if PERIODS.index(t) == 0:
            return pyo.Constraint.Skip
        return GAMS_PEH[a]*m.XH[a,h,j,l,t,s] <= GAMS_CAPCHT[l]*m.NVCH[l,h,j,t,s]
    m.farm_lead_cap = pyo.Constraint(m.A,m.H,m.J,m.L,m.T,m.S,rule=farm_lead_rule)


    # Transporte interplanta PAPP/NVPP.
    # Los pares j=jp no existen en m.JJ, equivalente a fijarlos en cero.

    # Límite total de viajes por tipo de flota interplanta.
    m.interplant_fleet = pyo.Constraint(
        m.Z,m.T,m.S,
        rule=lambda m,z,t,s:
        sum(m.NVPP[z,j,jp,t,s] for (j,jp) in m.JJ)
        <= GAMS_CCTZ[z]*GAMS_NMAXZ[z]
    )

    # Capacidad interplanta. Semántica GAMS con LEADZ=1.
    def interplant_kg_base_rule(m,z,j,jp,t,s):
        # Semana2..4: interplant_lead_cap es más fuerte porque GAMS_CCTZ[z] > 1.
        if PERIODS.index(t) != 0:
            return pyo.Constraint.Skip
        return GAMS_PIP*sum(m.PAPP[j,jp,q,t,s] for q in m.QZ) <= GAMS_CAPCPZ[z]*m.NVPP[z,j,jp,t,s]*GAMS_CCTZ[z]
    m.interplant_kg_base = pyo.Constraint(m.Z,m.JJ,m.T,m.S,rule=interplant_kg_base_rule)
    # C_CARG_PCD_MAX_VOL_PLAN: no depende de NVPP.
    m.interplant_vol_cap = pyo.Constraint(
        m.Z,m.JJ,m.T,m.S,
        rule=lambda m,z,j,jp,t,s:
        GAMS_VIP*sum(m.PAPP[j,jp,q,t,s] for q in m.QZ)
        <= GAMS_CCTZ[z]*GAMS_CCVZ[z]*GAMS_NMAXZ[z]
    )
    # CAPACIDADTRAN_PLAN: semana2..4, sin CCTZ.
    def interplant_lead_rule(m,z,j,jp,t,s):
        if PERIODS.index(t) == 0:
            return pyo.Constraint.Skip
        return GAMS_PIP*sum(m.PAPP[j,jp,q,t,s] for q in m.QZ) <= GAMS_CAPCPZ[z]*m.NVPP[z,j,jp,t,s]
    m.interplant_lead_cap = pyo.Constraint(m.Z,m.JJ,m.T,m.S,rule=interplant_lead_rule)

    # PAPP ya está acoplado directamente a los balances de Refrigeración
    # y Pasteurización; no se requiere una cota fuente separada.


    # Diversificación.
    def div_rule(m, j, t, s):
        total = sum(m.ship[i, jp, k, t, s] for i in m.I for jp in m.J for k in m.K)
        own = sum(m.ship[i, j, k, t, s] for i in m.I for k in m.K)
        return own <= d.share_max * total
    m.diversification = pyo.Constraint(m.J, m.T, m.S, rule=div_rule)

    # SCIS: absorción estructural.
    m.rdes = pyo.Constraint(expr=m.Rdes == sum(m.YP[j] for j in m.J) / len(plants))
    m.vsdes = pyo.Constraint(expr=m.Vsdes == sum(m.YCD[k] for k in m.K) / len(cds))
    m.ddes_lb = pyo.Constraint(expr=m.Ddes >= m.Rdes)
    # v32: sin cota superior artificial; el GAMS solo contiene Ddes >= Rdes.

    def xb_rule(m, t, s):
        idx = PERIODS.index(t)
        structural = d.eta1*m.Rdes + d.eta2*m.Ddes + d.eta3*m.Vsdes
        if idx == 0:
            return m.xB[t, s] == structural
        return m.xB[t, s] == (1-d.lam1)*m.xB[PERIODS[idx-1], s] + structural
    m.xb = pyo.Constraint(m.T, m.S, rule=xb_rule)

    # Esfuerzo operativo proxy; incluye severidad para diferenciar escenarios.
    m.eu = pyo.Constraint(
        m.T, m.S,
        rule=lambda m, t, s:
        m.EU[t, s] ==
        sum(m.xe_proc[q,j,t,s] for q in m.QP for j in m.J) +
        sum(m.sub[i,j,t,s] for i in m.I for j in m.J) +
        sum(m.NVCH[l,h,j,t,s] for l in m.L for h in m.H for j in m.J) +
        sum(m.trip_pcd[mm,j,k,t,s] for mm in m.M for j in m.J for k in m.K) +
        sum(m.trip_cdc[o,k,n,t,s] for o in m.O for k in m.K for n in m.N) +
        sum(m.NVPP[z,j,jp,t,s] for z in m.Z for (j,jp) in m.JJ)
    )

    # Gatillo innato Big-M.
    m.inn_upper = pyo.Constraint(
        m.T, m.S,
        rule=lambda m, t, s:
        m.EY[t, s] + m.EU[t, s] - d.xD0*m.DemTot[t, s] <= d.Mbig*m.InnON[t, s]
    )
    m.inn_lower = pyo.Constraint(
        m.T, m.S,
        rule=lambda m, t, s:
        m.EY[t, s] + m.EU[t, s] - d.xD0*m.DemTot[t, s] >= -d.Mbig*(1-m.InnON[t, s])
    )
    # GAMS exacto: zInn_link está COMENTADA, por lo que zInn NO se iguala a InnON.
    # Restricciones activas del GAMS:
    # ViolY <= Mbig*zInn
    # ViolY >= epsAct*zInn
    epsAct = 1e-6
    def zinn_viol_upper_rule(m, t, s):
        if t == PERIODS[0]:
            return pyo.Constraint.Skip
        return m.ViolY[t,s] <= d.Mbig*m.zInn[t,s]
    m.zinn_viol_upper = pyo.Constraint(m.T, m.S, rule=zinn_viol_upper_rule)

    def zinn_viol_lower_rule(m, t, s):
        if t == PERIODS[0]:
            return pyo.Constraint.Skip
        return m.ViolY[t,s] >= epsAct*m.zInn[t,s]
    m.zinn_viol_lower = pyo.Constraint(m.T, m.S, rule=zinn_viol_lower_rule)

    # v34 SCIS CORREGIDO:
    # Se activa la ecuación que está COMENTADA en el GAMS original:
    # zInn_link(t,s)$(ord(t) ne 1).. zInn(t,s) =E= InnON(t,s);
    # Así, zInn conserva interpretación 0-1 y sigue el gatillo innato.
    def zinn_link_corrected_rule(m, t, s):
        if t == PERIODS[0]:
            return pyo.Constraint.Skip
        return m.zInn[t,s] == m.InnON[t,s]
    m.zinn_link_corrected = pyo.Constraint(m.T, m.S, rule=zinn_link_corrected_rule)

    # Memoria literal GAMS:
    # Mmem('semana0',s)=0; dinámica solo para ord(t)>1.
    def mem_rule(m, t, s):
        idx = PERIODS.index(t)
        if idx == 0:
            return m.Mmem[t, s] == 0
        return m.Mmem[t, s] == (1-d.lamM)*m.Mmem[PERIODS[idx-1], s] + d.phiM*m.zInn[t, s]
    m.mem = pyo.Constraint(m.T, m.S, rule=mem_rule)

    m.deff1 = pyo.Constraint(m.T, m.S, rule=lambda m,t,s: m.Deff[t,s] <= m.EY[t,s])
    m.deff2 = pyo.Constraint(
        m.T, m.S,
        rule=lambda m,t,s: m.Deff[t,s] >= m.EY[t,s] - d.gammaM*m.Mmem[t,s]
    )

    # Homeostasis y desempeño.
    def homeostasis_rule(m, t, s):
        if t == PERIODS[0]:
            return pyo.Constraint.Skip
        return m.EY[t,s] <= d.eps_y*m.DemTot[t,s] + m.ViolY[t,s]
    m.homeostasis = pyo.Constraint(m.T, m.S, rule=homeostasis_rule)
    m.perf = pyo.Constraint(
        m.T, m.S,
        rule=lambda m,t,s: m.Pperf[t,s] == 1 - m.EY[t,s] / sum(m.D[i,n,t,s] for i in m.I for n in m.N)
    )
    def out1_rule(m, t, s):
        if t == PERIODS[0]:
            return pyo.Constraint.Skip
        return m.Pperf[t,s] >= d.theta - d.Mbig*m.Out[t,s]
    m.out1 = pyo.Constraint(m.T, m.S, rule=out1_rule)

    def out2_rule(m, t, s):
        if t == PERIODS[0]:
            return pyo.Constraint.Skip
        return m.Pperf[t,s] <= d.theta - 1e-6 + d.Mbig*(1-m.Out[t,s])
    m.out2 = pyo.Constraint(m.T, m.S, rule=out2_rule)

    # Recursos adaptativos.
    m.aact = pyo.Constraint(
        m.T, m.S,
        rule=lambda m,t,s: m.Aact[t,s] == sum(m.xe_final[i,j,t,s] + m.sub[i,j,t,s] for i in m.I for j in m.J)
    )
    m.uact = pyo.Constraint(
        m.T, m.S,
        rule=lambda m,t,s: m.Uact[t,s] == sum(m.NVCH[l,h,j,t,s] for l in m.L for h in m.H for j in m.J) + sum(m.NVPP[z,j,jp,t,s] for z in m.Z for (j,jp) in m.JJ) + sum(m.trip_pcd[mm,j,k,t,s] for mm in m.M for j in m.J for k in m.K) + sum(m.trip_cdc[o,k,n,t,s] for o in m.O for k in m.K for n in m.N)
    )
    m.rbuf = pyo.Constraint(
        m.T, m.S,
        rule=lambda m,t,s: m.Rbuf[t,s] == sum(m.inv[i,k,t,s] for i in m.I for k in m.K) + sum(m.buffer[i,j,t,s] for i in m.I for j in m.J) + sum(m.inv_proc[q,j,t,s] for q in m.QP for j in m.J)
    )
    m.cadapt = pyo.Constraint(
        m.S,
        rule=lambda m,s: m.Cadapt[s] == sum(
            d.cA*m.Aact[t,s] +
            d.cU*m.Uact[t,s] +
            d.cR*m.Rbuf[t,s] +
            d.cP*(m.EY[t,s]/sum(m.D[i,n,t,s] for i in m.I for n in m.N))
            for t in m.T
        )
    )

    # Economía.
    def revenue(m, s):
        return sum(
            m.ing[i]*m.delivery[i,k,n,t,s]
            for i in m.I for k in m.K for n in m.N for t in m.T
        )
    def fixed(m):
        return sum(m.fixedP[j]*m.YP[j] for j in m.J) + sum(m.fixedCD[k]*m.YCD[k] for k in m.K)
    def prod_cost(m, s):
        regular = sum(
            GAMS_FINAL_REG_COST[i]*m.xr_final[i,j,t,s]
            for i in m.I for j in m.J for t in m.T
        )
        overtime = sum(
            1.40*GAMS_FINAL_REG_COST[i]*m.xe_final[i,j,t,s]
            for i in m.I for j in m.J for t in m.T
        )
        subcontract = sum(
            GAMS_SUB_COST[(i,_base_plant(j))]*m.sub[i,j,t,s]
            for i in m.I for j in m.J for t in m.T
        )
        proc_regular = sum(
            GAMS_PROCESS_COST[q]*m.xr_proc[q,j,t,s]
            for q in m.QP for j in m.J for t in m.T
        )
        proc_overtime = sum(
            1.40*GAMS_PROCESS_COST[q]*m.xe_proc[q,j,t,s]
            for q in m.QP for j in m.J for t in m.T
        )
        return regular + overtime + subcontract + proc_regular + proc_overtime
    def raw_milk_cost(m, s):
        return sum(
            GAMS_CCLH[(a,h,t)]*m.XH[a,h,j,l,t,s]
            for a in m.A for h in m.H for j in m.J for l in m.L for t in m.T
        )
    def farm_transport_cost(m, s):
        return sum(
            gams_cvh(l,h,j,t)*m.NVCH[l,h,j,t,s]
            for l in m.L for h in m.H for j in m.J for t in m.T
        )
    def interplant_transport_cost(m, s):
        # GAMS: CVPP*NVPP + CTPPL*PAPP
        trips = sum(
            gams_cvpp(z,j,jp,t)*m.NVPP[z,j,jp,t,s]
            for z in m.Z for (j,jp) in m.JJ for t in m.T
        )
        flow = sum(
            GAMS_CTPPL*m.PAPP[j,jp,q,t,s]
            for (j,jp) in m.JJ for q in m.QZ for t in m.T
        )
        return trips + flow

    def pap_transport_cost(m, s):
        # GAMS: sum((q,qn,t,j), PAP(q,qn,t,j,s)*COSTPP)
        pap_vars = (
            m.pap_f1_r1, m.pap_r1_p1, m.pap_p1_mante, m.pap_p1_madur,
            m.pap_f2_r2, m.pap_r2_p2, m.pap_p2_madur, m.pap_p2_holec,
            m.pap_mante_env, m.pap_madur_hoyog, m.pap_hoyog_env, m.pap_holec_env
        )
        return GAMS_COSTPP*sum(
            v[j,t,s] for v in pap_vars for j in m.J for t in m.T
        )

    def trans_cost(m, s):
        # COSTRAS del GAMS: viajes + costos unitarios de los flujos.
        plant_cd_trips = sum(
            gams_cvc(mm,j,k,t)*m.trip_pcd[mm,j,k,t,s]
            for mm in m.M for j in m.J for k in m.K for t in m.T
        )
        cd_market_trips = sum(
            gams_cvccd(o,k,n,t)*m.trip_cdc[o,k,n,t,s]
            for o in m.O for k in m.K for n in m.N for t in m.T
        )
        plant_cd_flow = sum(
            GAMS_CTPCD[i]*m.ship[i,j,k,t,s]
            for i in m.I for j in m.J for k in m.K for t in m.T
        )
        cd_market_flow = sum(
            gams_ctcdc(i,k,n,t)*m.delivery[i,k,n,t,s]
            for i in m.I for k in m.K for n in m.N for t in m.T
        )
        return plant_cd_trips + cd_market_trips + plant_cd_flow + cd_market_flow + pap_transport_cost(m,s)

    def inv_cost(m, s):
        cd = sum(
            100.0*m.inv[i,k,t,s]
            for i in m.I for k in m.K for t in m.T
        )
        process = 10.0 * sum(m.inv_proc[q,j,t,s] for q in m.QP for j in m.J for t in m.T)
        plant = sum(
            GAMS_BUFFER_COST[(i,_base_plant(j))]*m.buffer[i,j,t,s]
            for i in m.I for j in m.J for t in m.T
        )
        return cd + plant + process
    def shortage_pen(m, s):
        return sum(
            d.penalty_short_factor*m.ing[i]*m.short[i,n,t,s]
            for i in m.I for n in m.N for t in m.T
        )

    def fosp_rule(m, s):
        homeo_pen = 0
        if not d.exact_active_gams_homeostasis:
            homeo_pen = d.homeostasis_penalty * sum(m.ViolY[t,s] for t in m.T)
        return m.FOSP[s] == (
            revenue(m,s) - fixed(m) - raw_milk_cost(m,s) - prod_cost(m,s) - farm_transport_cost(m,s) - interplant_transport_cost(m,s) - trans_cost(m,s) -
            inv_cost(m,s) - shortage_pen(m,s) - homeo_pen
        )
    m.fosp_def = pyo.Constraint(m.S, rule=fosp_rule)

    m.loss_def = pyo.Constraint(m.S, rule=lambda m,s: m.Loss[s] == d.profit_min - m.FOSP[s])
    m.cvar_excess = pyo.Constraint(m.S, rule=lambda m,s: m.zeta[s] >= m.Loss[s] - m.eta)
    m.cvar = pyo.Expression(
        expr=m.eta + 1/(1-d.alpha)*sum(m.ps[s]*m.zeta[s] for s in m.S)
    )
    m.objective_def = pyo.Constraint(
        expr=m.FO == sum(m.ps[s]*m.FOSP[s] for s in m.S) - d.rhoR*m.cvar
    )
    m.obj = pyo.Objective(expr=m.FO, sense=pyo.maximize)

    return m


def model_diagnostics(model) -> Dict[str, Any]:
    """Resumen estructural del MILP, sin alterar la formulación."""
    pyo = _require_pyomo()

    active_vars = list(model.component_data_objects(pyo.Var, active=True))
    binaries = sum(1 for v in active_vars if v.is_binary())
    integers = sum(1 for v in active_vars if v.is_integer() and not v.is_binary())
    continuous = len(active_vars) - binaries - integers

    constraints = list(model.component_data_objects(pyo.Constraint, active=True))
    by_block = {}
    for comp in model.component_objects(pyo.Constraint, active=True):
        try:
            by_block[comp.name] = len(comp)
        except Exception:
            by_block[comp.name] = sum(1 for _ in comp.values())

    largest = sorted(by_block.items(), key=lambda kv: kv[1], reverse=True)[:20]

    return {
        "variables_total": len(active_vars),
        "variables_binary": binaries,
        "variables_integer": integers,
        "variables_continuous": continuous,
        "constraints_total": len(constraints),
        "largest_constraint_blocks": largest,
    }

def solve_model(
    data: OptimizerData,
    solver: str = "highs",
    tee: bool = False,
    time_limit: float = 600.0,
    mip_rel_gap: float = 0.02,
) -> Dict[str, Any]:
    """Resuelve URSP-SCIS con un límite de tiempo seguro para Streamlit.

    Si HiGHS alcanza el límite pero ya encontró una solución factible,
    se conservan esos valores y la app puede seguir mostrando resultados.
    """
    pyo = _require_pyomo()
    d = data.normalized()
    model = build_model(d)
    diagnostics = model_diagnostics(model)
    opt = pyo.SolverFactory(solver)
    if opt is None or not opt.available(exception_flag=False):
        raise RuntimeError("HiGHS no está disponible. En CMD: python -m pip install highspy")

    if solver.lower() in {"highs", "appsi_highs"}:
        opt.options["time_limit"] = float(time_limit)
        opt.options["mip_rel_gap"] = float(mip_rel_gap)
        opt.options["presolve"] = "on"

        # Compatibilidad Streamlit Cloud / Pyomo + HiGHS.
        # Solo silencia la salida de consola del solver para evitar conflictos
        # TeeStream con stdout/stderr; no modifica el modelo matemático.
        opt.options["log_to_console"] = False
        opt.options["output_flag"] = False

    result = opt.solve(model, tee=tee, load_solutions=True)
    term = str(result.solver.termination_condition)
    term_l = term.lower().replace(" ", "")

    usable = {
        "optimal", "feasible", "maxtimelimit", "maxTimeLimit".lower(),
        "maxTimeLimit".lower().replace(" ", "")
    }
    if term_l not in {x.lower().replace(" ", "") for x in usable}:
        raise RuntimeError(f"El modelo no terminó en una solución utilizable: {term}")

    out = extract_results(model, d, term)
    # Exponer la condición real de terminación para que Streamlit pueda
    # distinguir Optimal, maxTimeLimit, infeasible, etc.
    out["termination"] = term
    out["model_diagnostics"] = diagnostics
    out["solver_status"] = str(result.solver.status)
    out["solver_time_limit"] = float(time_limit)
    out["solver_mip_rel_gap"] = float(mip_rel_gap)

    # Diagnóstico REAL reportado por HiGHS/Pyomo cuando está disponible.
    # No confundir solver_mip_rel_gap (tolerancia solicitada) con achieved_mip_gap.
    def _solver_metric(*names):
        for name in names:
            try:
                v = getattr(result.solver, name, None)
                if v is not None:
                    return float(v)
            except Exception:
                pass
        return None

    out["solver_wallclock_time"] = _solver_metric(
        "wallclock_time", "time", "user_time", "system_time"
    )
    out["best_bound"] = _solver_metric("best_bound")
    out["problem_lower_bound"] = None
    out["problem_upper_bound"] = None
    out["achieved_mip_gap"] = _solver_metric(
        "gap", "mip_gap", "relative_gap"
    )

    # El incumbente siempre puede recuperarse del modelo cargado.
    try:
        out["incumbent_objective"] = float(pyo.value(model.OBJ))
    except Exception:
        try:
            out["incumbent_objective"] = float(pyo.value(model.obj))
        except Exception:
            out["incumbent_objective"] = out.get("objective")

    # Algunos plugins de Pyomo guardan bounds/gap en problem en vez de solver.
    try:
        problem0 = result.problem[0]
        lb = getattr(problem0, "lower_bound", None)
        ub = getattr(problem0, "upper_bound", None)
        if lb is not None:
            out["problem_lower_bound"] = float(lb)
        if ub is not None:
            out["problem_upper_bound"] = float(ub)

        # En maximización, Pyomo suele reportar incumbent como lower bound y
        # best dual bound como upper bound. Se conservan ambos campos crudos.
        if out["best_bound"] is None and ub is not None:
            out["best_bound"] = float(ub)

        if out["achieved_mip_gap"] is None and lb is not None and ub is not None:
            lb, ub = float(lb), float(ub)
            denom = max(1.0, abs(lb), abs(ub))
            out["achieved_mip_gap"] = abs(ub-lb)/denom
    except Exception:
        pass

    out["solution_optimal"] = term_l == "optimal"
    out["time_limit_reached"] = term_l in {"maxtimelimit", "maxTimeLimit".lower()}
    return out

def extract_results(model, data: OptimizerData, termination: str = "") -> Dict[str, Any]:
    pyo = _require_pyomo()
    def val(x):
        try:
            v = float(pyo.value(x))
            return 0.0 if abs(v) < 1e-9 else v
        except Exception:
            return 0.0

    plants = list(model.J)
    cds = list(model.K)
    scenario = {}
    for s in SCENARIOS:
        dem = sum(val(model.D[i,n,t,s]) for i in PRODUCTS for n in CONSUMERS for t in PERIODS)
        short = sum(val(model.short[i,n,t,s]) for i in PRODUCTS for n in CONSUMERS for t in PERIODS)
        ship = sum(
            val(model.delivery[i,k,n,t,s])
            for i in PRODUCTS for k in cds for n in CONSUMERS for t in PERIODS
        )
        perf = [val(model.Pperf[t,s]) for t in PERIODS]
        scenario[s] = {
            "probability": data.probabilities[s],
            "FO_SP": val(model.FOSP[s]),
            "shortage": short,
            "shipment": ship,
            "service_level": max(0.0, min(1.0, 1-short/max(1e-6,dem))),
            "viability": sum(perf)/len(perf),
            "min_viability": min(perf),
            "innate_rate": sum(val(model.zInn[t,s]) for t in PERIODS)/len(PERIODS),
            "memory_end": val(model.Mmem[PERIODS[-1],s]),
            "adaptive_cost": val(model.Cadapt[s]),
            "overtime_final": sum(val(model.xe_final[i,j,t,s]) for i in PRODUCTS for j in plants for t in PERIODS),
            "subcontracting": sum(val(model.sub[i,j,t,s]) for i in PRODUCTS for j in plants for t in PERIODS),
            "plant_buffer": sum(val(model.buffer[i,j,t,s]) for i in PRODUCTS for j in plants for t in PERIODS),
            "process_inventory": sum(val(model.inv_proc[q,j,t,s]) for q in PROCESS_STAGES for j in plants for t in PERIODS),
            "process_overtime": sum(val(model.xe_proc[q,j,t,s]) for q in PROCESS_STAGES for j in plants for t in PERIODS),
            "trips_farm_plant": sum(val(model.NVCH[l,h,j,t,s]) for l in TRUCK_HATO for h in FARMS for j in plants for t in PERIODS),
            "raw_milk_collected": sum(val(model.XH[a,h,j,l,t,s]) for a in RAW_MILKS for h in FARMS for j in plants for l in TRUCK_HATO for t in PERIODS),
            "raw_milk_cost": sum(GAMS_CCLH[(a,h,t)]*val(model.XH[a,h,j,l,t,s]) for a in RAW_MILKS for h in FARMS for j in plants for l in TRUCK_HATO for t in PERIODS),
            "farm_transport_cost": sum(gams_cvh(l,h,j,t)*val(model.NVCH[l,h,j,t,s]) for l in TRUCK_HATO for h in FARMS for j in plants for t in PERIODS),
            "trips_interplant": sum(val(model.NVPP[z,j,jp,t,s]) for z in TRUCK_INTERPLANT for j in plants for jp in plants if j != jp for t in PERIODS),
            "interplant_flow": sum(val(model.PAPP[j,jp,q,t,s]) for j in plants for jp in plants for q in INTERPLANT_STAGES if j != jp for t in PERIODS),
            "trips_plant_cd": sum(val(model.trip_pcd[mm,j,k,t,s]) for mm in TRUCK_PCD for j in plants for k in cds for t in PERIODS),
            "trips_cd_market": sum(val(model.trip_cdc[o,k,n,t,s]) for o in TRUCK_CDC for k in cds for n in CONSUMERS for t in PERIODS),
            # Coste total de transporte calculado directamente aquí.
            # Los helpers farm_transport_cost/interplant_transport_cost/trans_cost
            # son locales a build_model() y no existen dentro de extract_results().
            "transport_cost_gams": (
                sum(
                    gams_cvh(l,h,j,t) * val(model.NVCH[l,h,j,t,s])
                    for l in TRUCK_HATO for h in FARMS for j in plants for t in PERIODS
                )
                + sum(
                    gams_cvpp(z,j,jp,t) * val(model.NVPP[z,j,jp,t,s])
                    for z in TRUCK_INTERPLANT for j in plants for jp in plants if j != jp for t in PERIODS
                )
                + GAMS_CTPPL * sum(
                    val(model.PAPP[j,jp,q,t,s])
                    for j in plants for jp in plants for q in INTERPLANT_STAGES if j != jp for t in PERIODS
                )
                + sum(
                    gams_cvc(mm,j,k,t) * val(model.trip_pcd[mm,j,k,t,s])
                    for mm in TRUCK_PCD for j in plants for k in cds for t in PERIODS
                )
                + sum(
                    gams_cvccd(o,k,n,t) * val(model.trip_cdc[o,k,n,t,s])
                    for o in TRUCK_CDC for k in cds for n in CONSUMERS for t in PERIODS
                )
                + sum(
                    GAMS_CTPCD[i] * val(model.ship[i,j,k,t,s])
                    for i in PRODUCTS for j in plants for k in cds for t in PERIODS
                )
                + sum(
                    gams_ctcdc(i,k,n,t) * val(model.delivery[i,k,n,t,s])
                    for i in PRODUCTS for k in cds for n in CONSUMERS for t in PERIODS
                )
                + GAMS_COSTPP * sum(
                    val(v[j,t,s])
                    for v in (
                        model.pap_f1_r1, model.pap_r1_p1, model.pap_p1_mante, model.pap_p1_madur,
                        model.pap_f2_r2, model.pap_r2_p2, model.pap_p2_madur, model.pap_p2_holec,
                        model.pap_mante_env, model.pap_madur_hoyog, model.pap_hoyog_env, model.pap_holec_env
                    )
                    for j in plants for t in PERIODS
                )
            ),
            "homeostasis_violation": sum(val(model.ViolY[t,s]) for t in PERIODS),
            # v31: auditoría SCIS (solo lectura; no cambia el MILP).
            # v35: KPIs SCIS calculados sobre periodos operativos (semana1..semana4).
            # semana0 se reporta aparte porque es condición inicial.
            "scis_inn_on_rate": sum(val(model.InnON[t,s]) for t in PERIODS[1:]) / len(PERIODS[1:]),
            "scis_zinn_avg": sum(val(model.zInn[t,s]) for t in PERIODS[1:]) / len(PERIODS[1:]),
            "scis_zinn_end": val(model.zInn[PERIODS[-1],s]),
            "scis_zinn_week0": val(model.zInn[PERIODS[0],s]),
            "scis_innon_week0": val(model.InnON[PERIODS[0],s]),
            "scis_zinn_innon_maxdiff": max(
                abs(val(model.zInn[t,s]) - val(model.InnON[t,s])) for t in PERIODS[1:]
            ),
            "scis_trigger_min": min(
                val(model.EY[t,s]) + val(model.EU[t,s]) - float(data.xD0)*val(model.DemTot[t,s])
                for t in PERIODS[1:]
            ),
            "scis_trigger_max": max(
                val(model.EY[t,s]) + val(model.EU[t,s]) - float(data.xD0)*val(model.DemTot[t,s])
                for t in PERIODS[1:]
            ),
            "scis_EY_operational": sum(val(model.EY[t,s]) for t in PERIODS[1:]),
            "scis_EU_operational": sum(val(model.EU[t,s]) for t in PERIODS[1:]),
            "scis_memory_end": val(model.Mmem[PERIODS[-1],s]),
            "scis_deff_total": sum(val(model.Deff[t,s]) for t in PERIODS[1:]),
            "scis_perf_min": min(val(model.Pperf[t,s]) for t in PERIODS[1:]),
            "scis_out_rate": sum(val(model.Out[t,s]) for t in PERIODS[1:]) / len(PERIODS[1:]),
            "demand_total": dem,
            "gams_logistics_min": min(GAMS_AVAIL_CDC[(t,s)] for t in PERIODS),
            "effective_raw_supply": sum(GAMS_SUPPLY_BASE[(a,t)]*gams_fsup(a,t,s) for a in ("leche1","leche2") for t in PERIODS),
        }

    probs = data.probabilities
    return {
        "status": termination,
        "network_size": {"plants": len(plants), "cds": len(cds)},
        "network_origin": {
            "base_plants": list(BASE_PLANTS), "base_cds": list(BASE_CDS),
            "note": "Nodos adicionales usan extensión determinística de perfiles GAMS base."
        },
        "objective": val(model.FO),
        "cvar": val(model.cvar),
        "plants_active": sum(round(val(model.YP[j])) for j in plants),
        "cds_active": sum(round(val(model.YCD[k])) for k in cds),
        "expected_profit": sum(probs[s]*scenario[s]["FO_SP"] for s in SCENARIOS),
        "expected_shortage": sum(probs[s]*scenario[s]["shortage"] for s in SCENARIOS),
        "expected_viability": sum(probs[s]*scenario[s]["viability"] for s in SCENARIOS),
        "worst_service": min(scenario[s]["service_level"] for s in SCENARIOS),
        "scenario": scenario,
        "design": {
            "plants": {j: round(val(model.YP[j])) for j in plants},
            "cds": {k: round(val(model.YCD[k])) for k in cds},
        },
    }

def scenario_table(results: Dict[str, Any]):
    import pandas as pd
    rows = []
    for s, v in results["scenario"].items():
        rows.append({
            "Escenario": s,
            "Probabilidad": v["probability"],
            "zInn promedio": v.get("scis_zinn_avg", 0.0),
            "zInn final": v.get("scis_zinn_end", 0.0),
            "Memoria SCIS final": v.get("scis_memory_end", 0.0),
            "Violación homeostasis": v.get("homeostasis_violation", 0.0),
            "Desempeño SCIS mínimo": v.get("scis_perf_min", 0.0),
            "Activación InnON": v.get("scis_inn_on_rate", 0.0),
            "Activación Out": v.get("scis_out_rate", 0.0),
            "Demanda": v["demand_total"],
            "Utilidad": v["FO_SP"],
            "Faltante": v["shortage"],
            "Nivel servicio": v["service_level"],
            "Viabilidad": v["viability"],
            "Viabilidad mínima": v["min_viability"],
            "Memoria": v["memory_end"],
            "Costo adaptativo": v["adaptive_cost"],
            "Viajes Hato-Planta": v.get("trips_farm_plant",0),
            "Leche recolectada": v.get("raw_milk_collected",0),
            "Viajes interplanta": v.get("trips_interplant",0),
            "Flujo interplanta": v.get("interplant_flow",0),
        })
    return pd.DataFrame(rows)

def parameter_summary(data: OptimizerData):
    return {
        "Escenarios": SCENARIOS,
        "Probabilidades": data.probabilities,
        "Demanda base": data.demand,
        "Diseño plantas": "Fijado" if data.plant_design_status is not None else "Libre",
        "Estado plantas fijado": data.plant_design_status,
        "Diseño CD": "Fijado" if data.cd_design_status is not None else "Libre",
        "Estado CD fijado": data.cd_design_status,
        "Factor demanda": data.demand_factor,
        "Factor suministro": data.supply_factor,
        "Factor transporte": data.transport_factor,
        "Factor proceso": data.processing_factor,
        "Disrupción": data.disruption,
        "eps_y": data.eps_y,
        "theta": data.theta,
        "rhoR": data.rhoR,
        "alpha": data.alpha,
        "profit_min": data.profit_min,
        "Modo FO homeostasis": "GAMS activo" if data.exact_active_gams_homeostasis else "Artículo penalizado",
    }

if __name__ == "__main__":
    r = solve_model(OptimizerData.from_gams_defaults())
    print("Estado:", r["status"])
    print("FO:", r["objective"])
    print("Plantas:", r["design"]["plants"])
    print("CD:", r["design"]["cds"])
    print(scenario_table(r).to_string(index=False))
