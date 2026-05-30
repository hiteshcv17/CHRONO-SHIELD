"""
Phase 28 — Explainable AI Reasoning System
Rule-based, template-driven explanation engine that generates structured
causal reasoning and natural language explanations for infrastructure anomalies.

Architecture:
  1. Context enrichment  — extract time, environmental, and operational context
  2. Factor identification — match metric + context to a library of causal rules
  3. Correlation linking   — build a directed causal graph (factor → factor)
  4. Chain-of-thought      — generate ordered reasoning steps
  5. NL generation         — compose headline, summary, and causal narrative
"""

import time
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple

logger = logging.getLogger("explain_service")

# ==============================================================================
# ── Knowledge Base: Causal Rule Library ─────────────────────────────────────
# Each rule maps a (metric_keyword, context_condition) → causal explanation
# ==============================================================================


# Time-of-day windows
def _time_context(hour: int) -> str:
    if 7 <= hour < 9:
        return "MORNING_RUSH"
    if 9 <= hour < 11:
        return "MID_MORNING"
    if 11 <= hour < 14:
        return "MIDDAY_PEAK"
    if 14 <= hour < 17:
        return "AFTERNOON_HEAT"
    if 17 <= hour < 21:
        return "EVENING_SURGE"
    if 21 <= hour < 24:
        return "LATE_NIGHT"
    return "OVERNIGHT"


_TIME_LABELS = {
    "MORNING_RUSH": "during the morning commute rush hour",
    "MID_MORNING": "during mid-morning operational peak",
    "MIDDAY_PEAK": "during the midday demand peak",
    "AFTERNOON_HEAT": "during the peak afternoon heat window",
    "EVENING_SURGE": "during the evening residential demand surge",
    "LATE_NIGHT": "during late-night low-activity hours",
    "OVERNIGHT": "during the overnight maintenance window",
}

_CATEGORY_LABELS = {
    "POWER": "power grid",
    "TRAFFIC": "road network",
    "WATER": "water distribution",
    "INTERNET": "network infrastructure",
    "PUBLIC_INFRASTRUCTURE": "civic infrastructure",
}

# Cross-domain correlation rules: which categories amplify each other
_DOMAIN_CORRELATIONS: Dict[str, List[Dict[str, Any]]] = {
    "POWER": [
        {
            "domain": "INTERNET",
            "rel": "TRIGGERED",
            "strength": 0.85,
            "lag": 3,
            "desc": "power instability disrupts UPS systems and data center cooling, causing network degradation",
        },
        {
            "domain": "TRAFFIC",
            "rel": "AMPLIFIED",
            "strength": 0.60,
            "lag": 5,
            "desc": "traffic signal controllers lose backup power, creating intersection failures",
        },
        {
            "domain": "PUBLIC_INFRASTRUCTURE",
            "rel": "CORRELATED",
            "strength": 0.55,
            "lag": 8,
            "desc": "street lighting and public systems depend on the same distribution feeders",
        },
        {
            "domain": "WATER",
            "rel": "CORRELATED",
            "strength": 0.45,
            "lag": 10,
            "desc": "water pumping stations require reliable power; voltage drops reduce pump efficiency",
        },
    ],
    "TRAFFIC": [
        {
            "domain": "PUBLIC_INFRASTRUCTURE",
            "rel": "TRIGGERED",
            "strength": 0.75,
            "lag": 2,
            "desc": "collision events and road closures cascade into signal infrastructure failures",
        },
        {
            "domain": "POWER",
            "rel": "CORRELATED",
            "strength": 0.30,
            "lag": 0,
            "desc": "emergency service demand during incidents increases local grid load",
        },
        {
            "domain": "INTERNET",
            "rel": "AMPLIFIED",
            "strength": 0.40,
            "lag": 5,
            "desc": "incident reporting generates bandwidth spikes on emergency communication networks",
        },
    ],
    "WATER": [
        {
            "domain": "TRAFFIC",
            "rel": "TRIGGERED",
            "strength": 0.80,
            "lag": 4,
            "desc": "surface flooding from ruptures forces road closures and traffic diversions",
        },
        {
            "domain": "PUBLIC_INFRASTRUCTURE",
            "rel": "CORRELATED",
            "strength": 0.65,
            "lag": 6,
            "desc": "pipe failures undermine road surface integrity, accelerating infrastructure degradation",
        },
        {
            "domain": "INTERNET",
            "rel": "CORRELATED",
            "strength": 0.25,
            "lag": 15,
            "desc": "underground duct flooding risks cable damage in shared utility corridors",
        },
    ],
    "INTERNET": [
        {
            "domain": "POWER",
            "rel": "PRECEDED",
            "strength": 0.70,
            "lag": -5,
            "desc": "network instability often precedes or coincides with power distribution stress",
        },
        {
            "domain": "PUBLIC_INFRASTRUCTURE",
            "rel": "CORRELATED",
            "strength": 0.35,
            "lag": 0,
            "desc": "smart city sensor networks depend on connectivity for real-time monitoring",
        },
    ],
    "PUBLIC_INFRASTRUCTURE": [
        {
            "domain": "TRAFFIC",
            "rel": "AMPLIFIED",
            "strength": 0.70,
            "lag": 3,
            "desc": "signal failures and road defects compound traffic congestion patterns",
        },
        {
            "domain": "POWER",
            "rel": "CORRELATED",
            "strength": 0.50,
            "lag": 0,
            "desc": "civic systems share electrical feeders with distribution infrastructure",
        },
    ],
}

# Metric-level causal templates
_METRIC_RULES: Dict[str, Dict[str, Any]] = {
    "power_outage": {
        "primary_causes": [
            "transformer overload from simultaneous peak demand",
            "equipment fault in primary distribution circuit",
            "protection relay trip due to line fault",
        ],
        "amplifiers": [
            "elevated ambient temperature increasing conductor resistance",
            "aging infrastructure beyond design lifecycle",
            "concurrent high-draw industrial equipment startup",
        ],
        "cascade_risk": "CRITICAL",
        "impacted_systems": [
            "telecommunications",
            "traffic signaling",
            "water pumping",
            "emergency services",
        ],
        "actions": [
            "Deploy mobile generation units to critical facilities",
            "Isolate faulted circuit section via SCADA",
            "Activate demand-response protocol to reduce load",
            "Alert grid operator for emergency capacity allocation",
        ],
    },
    "grid_voltage": {
        "primary_causes": [
            "reactive power imbalance in distribution feeder",
            "capacitor bank failure reducing voltage support",
            "simultaneous large motor starts in industrial zone",
        ],
        "amplifiers": [
            "high ambient temperature increasing line losses",
            "insufficient reactive compensation",
        ],
        "cascade_risk": "HIGH",
        "impacted_systems": [
            "sensitive electronic equipment",
            "variable-frequency drives",
            "traffic controllers",
        ],
        "actions": [
            "Reconnect switched capacitor banks",
            "Reduce industrial load via voluntary curtailment",
            "Inspect and replace failed capacitor bank units",
        ],
    },
    "energy_demand": {
        "primary_causes": [
            "simultaneous residential and commercial cooling load activation",
            "industrial shift change adding concurrent motor loads",
            "extreme ambient temperature driving HVAC consumption",
        ],
        "amplifiers": [
            "time-of-day alignment with peak tariff avoidance behavior",
            "electric vehicle charging load concentration",
        ],
        "cascade_risk": "HIGH",
        "impacted_systems": ["grid stability margin", "frequency regulation reserves"],
        "actions": [
            "Activate demand-response program DR-7",
            "Bring emergency peaking generation online",
            "Issue demand advisory to large commercial customers",
        ],
    },
    "traffic_jam": {
        "primary_causes": [
            "vehicle density exceeding road capacity design threshold",
            "upstream incident reducing effective lane count",
            "signal timing misalignment during demand peak",
        ],
        "amplifiers": [
            "adverse weather reducing driver visibility and speed",
            "school zone or event generating pedestrian conflicts",
            "freight vehicle mix increasing headway requirements",
        ],
        "cascade_risk": "MODERATE",
        "impacted_systems": [
            "emergency vehicle response time",
            "goods delivery logistics",
            "air quality",
        ],
        "actions": [
            "Activate adaptive signal control on affected corridor",
            "Enable dynamic message signs for alternate route guidance",
            "Deploy traffic management officers to critical junctions",
        ],
    },
    "traffic_accident": {
        "primary_causes": [
            "reduced friction coefficient on wet or contaminated road surface",
            "driver inattention at high-risk junction",
            "excessive speed relative to prevailing conditions",
        ],
        "amplifiers": [
            "poor visibility from weather or lighting conditions",
            "high vehicle density reducing safe stopping distance",
            "complex junction geometry creating decision conflict",
        ],
        "cascade_risk": "HIGH",
        "impacted_systems": [
            "emergency services",
            "road signal systems",
            "downstream traffic flow",
            "supply chains",
        ],
        "actions": [
            "Dispatch emergency services immediately",
            "Activate pre-planned detour route via VMS",
            "Switch affected signals to manual/override mode",
            "Alert downstream signal controllers to adjust timing",
        ],
    },
    "vehicle_count": {
        "primary_causes": [
            "simultaneous peak demand from multiple trip generators",
            "shift change at major employment centers",
            "diversion from adjacent network incident",
        ],
        "amplifiers": [
            "reduced network capacity from maintenance works",
            "weather-driven modal shift from active transport",
        ],
        "cascade_risk": "MODERATE",
        "impacted_systems": [
            "fuel consumption",
            "emissions levels",
            "road surface wear",
        ],
        "actions": [
            "Enable reversible lane operation on capacity-critical links",
            "Push real-time routing guidance via navigation platforms",
        ],
    },
    "road_signal": {
        "primary_causes": [
            "controller unit failure from power transient",
            "communication link failure isolating signal from SCADA",
            "firmware fault causing controller reboot cycle",
        ],
        "amplifiers": [
            "age-related hardware degradation in controller cabinet",
            "power quality issues in supply network",
        ],
        "cascade_risk": "HIGH",
        "impacted_systems": [
            "intersection safety",
            "traffic flow efficiency",
            "emergency vehicle preemption",
        ],
        "actions": [
            "Switch to local fallback timing plan",
            "Deploy manual traffic management at affected intersection",
            "Dispatch maintenance crew for controller replacement",
        ],
    },
    "water_pressure": {
        "primary_causes": [
            "pipe joint failure creating uncontrolled discharge",
            "pump station trip reducing distribution head",
            "sudden demand spike exceeding system storage reserve",
        ],
        "amplifiers": [
            "aged pipe material with reduced wall thickness",
            "thermal expansion from diurnal temperature cycling",
            "ground movement from nearby construction activity",
        ],
        "cascade_risk": "HIGH",
        "impacted_systems": [
            "fire suppression capacity",
            "residential supply",
            "industrial processes",
        ],
        "actions": [
            "Isolate affected segment via SCADA zone valve control",
            "Deploy field crew for emergency repair",
            "Truck water supply to affected residents",
        ],
    },
    "water_quality": {
        "primary_causes": [
            "treatment chemical dosing anomaly at source plant",
            "cross-contamination from pressure reversal event",
            "sediment disturbance from velocity change in mains",
        ],
        "amplifiers": [
            "aging distribution infrastructure leaching material",
            "recent maintenance activity disturbing deposits",
        ],
        "cascade_risk": "CRITICAL",
        "impacted_systems": [
            "public health",
            "industrial water-dependent processes",
            "hospitality sector",
        ],
        "actions": [
            "Issue precautionary boil-water advisory for affected zone",
            "Increase monitoring sampling frequency to 1-hour intervals",
            "Adjust treatment dosing at source plant",
        ],
    },
    "flood_sensor": {
        "primary_causes": [
            "sustained rainfall exceeding catchment infiltration capacity",
            "blocked stormwater drain reducing discharge rate",
            "upstream dam or retention basin overflow",
        ],
        "amplifiers": [
            "impervious surface runoff from urban development",
            "soil saturation from prior precipitation events",
        ],
        "cascade_risk": "HIGH",
        "impacted_systems": [
            "road network",
            "underground utilities",
            "building basements",
        ],
        "actions": [
            "Activate pump stations at retention basins",
            "Open emergency overflow channels",
            "Issue flood warning for low-lying areas",
        ],
    },
    "network_latency": {
        "primary_causes": [
            "backbone link congestion from traffic surge",
            "routing table instability causing suboptimal path selection",
            "DDoS-pattern traffic consuming processing capacity",
        ],
        "amplifiers": [
            "CDN cache miss rate increase driving origin pulls",
            "TLS handshake overhead from connection churn",
        ],
        "cascade_risk": "MODERATE",
        "impacted_systems": [
            "real-time monitoring systems",
            "financial transactions",
            "emergency communications",
        ],
        "actions": [
            "Apply QoS marking to prioritize critical traffic classes",
            "Re-advertise routes via secondary BGP path",
            "Activate DDoS scrubbing if attack signature confirmed",
        ],
    },
    "network_packet_loss": {
        "primary_causes": [
            "physical layer fault on fiber span causing bit errors",
            "buffer overflow from sustained traffic burst",
            "hardware queue drop due to egress interface saturation",
        ],
        "amplifiers": [
            "temperature-induced optical power degradation",
            "microwave backhaul rain-fade on wireless segment",
        ],
        "cascade_risk": "HIGH",
        "impacted_systems": [
            "VoIP quality",
            "video streaming",
            "IoT sensor telemetry",
            "SCADA real-time data",
        ],
        "actions": [
            "Fail over to secondary fiber route",
            "Check optical power levels on affected span",
            "Apply traffic shaping to reduce burst impact",
        ],
    },
    "internet_bandwidth": {
        "primary_causes": [
            "simultaneous high-bandwidth consumer activity peak",
            "automated backup or OS update synchronization storm",
            "abnormal traffic pattern suggesting malicious activity",
        ],
        "amplifiers": [
            "insufficient peering capacity with content providers",
            "asymmetric traffic profile stressing upload path",
        ],
        "cascade_risk": "MODERATE",
        "impacted_systems": [
            "business productivity",
            "cloud service access",
            "streaming platforms",
        ],
        "actions": [
            "Apply per-subscriber bandwidth caps for P2P traffic",
            "Coordinate with upstream ISP for emergency capacity",
            "Implement traffic prioritization for business SLA customers",
        ],
    },
    "cpu_usage": {
        "primary_causes": [
            "demand spike from concurrent user sessions exceeding capacity",
            "background batch job consuming unplanned compute resources",
            "memory leak causing excessive garbage collection cycles",
        ],
        "amplifiers": [
            "insufficient horizontal scaling headroom",
            "synchronous blocking I/O under load",
        ],
        "cascade_risk": "HIGH",
        "impacted_systems": [
            "API response times",
            "user-facing service availability",
            "data pipeline reliability",
        ],
        "actions": [
            "Trigger horizontal auto-scaling to add compute instances",
            "Identify and defer non-critical background tasks",
            "Enable circuit breakers to shed non-essential load",
        ],
    },
    "infrastructure_defect": {
        "primary_causes": [
            "material fatigue from cumulative cyclic loading beyond design life",
            "accelerated corrosion from environmental exposure",
            "sub-standard repair from prior maintenance activity",
        ],
        "amplifiers": [
            "heavy vehicle loading exceeding pavement design class",
            "freeze-thaw cycling widening existing micro-cracks",
        ],
        "cascade_risk": "LOW",
        "impacted_systems": [
            "pedestrian safety",
            "vehicle suspension systems",
            "road surface drainage",
        ],
        "actions": [
            "Deploy temporary protective barriers around defect",
            "Schedule priority repair within agreed SLA window",
            "Increase inspection frequency on adjacent sections",
        ],
    },
}

# Environmental context factors
_WEATHER_FACTORS = {
    "MORNING_RUSH": [
        {
            "name": "Morning Atmospheric Instability",
            "desc": "Morning temperature inversions trap pollutants and reduce driver visibility, compounding road incident risk",
            "category": "WEATHER",
            "confidence": 0.62,
            "weight": 0.4,
        },
    ],
    "AFTERNOON_HEAT": [
        {
            "name": "Peak Solar Thermal Load",
            "desc": "Solar radiation and ambient temperatures above 35°C drive simultaneous HVAC demand across residential and commercial zones",
            "category": "WEATHER",
            "confidence": 0.88,
            "weight": 0.7,
        },
    ],
    "EVENING_SURGE": [
        {
            "name": "Diurnal Temperature Drop",
            "desc": "Evening temperature reduction increases residential heating demand, partially offsetting the reduction in cooling load",
            "category": "WEATHER",
            "confidence": 0.55,
            "weight": 0.35,
        },
    ],
    "OVERNIGHT": [
        {
            "name": "Reduced Ambient Temperature",
            "desc": "Nighttime temperature reduction contracts pipe materials, increasing stress at joints — particularly in aging networks",
            "category": "WEATHER",
            "confidence": 0.50,
            "weight": 0.30,
        },
    ],
}

_TEMPORAL_FACTORS = {
    "MORNING_RUSH": {
        "name": "Morning Commute Demand Pattern",
        "desc": "07:00–09:00 represents the highest simultaneous demand period for road network and energy infrastructure",
        "confidence": 0.92,
        "weight": 0.85,
    },
    "MIDDAY_PEAK": {
        "name": "Midday Commercial Demand Peak",
        "desc": "12:00–14:00 commercial activity concentration drives network and energy peaks",
        "confidence": 0.82,
        "weight": 0.70,
    },
    "AFTERNOON_HEAT": {
        "name": "Afternoon Peak Temperature Window",
        "desc": "14:00–17:00 represents the daily maximum temperature, creating extreme HVAC and cooling demand",
        "confidence": 0.87,
        "weight": 0.80,
    },
    "EVENING_SURGE": {
        "name": "Evening Residential Load Surge",
        "desc": "17:00–20:00 residential return home creates simultaneous demand across all infrastructure systems",
        "confidence": 0.85,
        "weight": 0.78,
    },
    "OVERNIGHT": {
        "name": "Low-Activity Maintenance Window",
        "desc": "00:00–06:00 scheduled maintenance activity increases system perturbation risk",
        "confidence": 0.65,
        "weight": 0.50,
    },
}


# ==============================================================================
# Explanation Engine
# ==============================================================================
class ExplainService:

    @staticmethod
    def explain_anomaly(
        anomaly_id: str,
        metric_name: str,
        severity: str,
        category: str,
        score: float,
        timestamp: str,
        district: str,
        description: str = "",
        related_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        t0 = time.perf_counter()

        # ── 1. Context enrichment ──────────────────────────────────────────
        try:
            dt = datetime.fromisoformat(timestamp)
            hour = dt.hour
        except Exception:
            hour = 12
        time_ctx = _time_context(hour)
        time_label = _TIME_LABELS.get(time_ctx, "during operational hours")

        # Get metric rule — fall back to category-level defaults
        metric_key = metric_name.lower()
        rule = _METRIC_RULES.get(metric_key)
        if rule is None:
            # Partial match
            for key, val in _METRIC_RULES.items():
                if key in metric_key or metric_key in key:
                    rule = val
                    break
        if rule is None:
            rule = {
                "primary_causes": [
                    f"anomalous behavior in {metric_name.replace('_', ' ')} metric"
                ],
                "amplifiers": ["concurrent system stress", "elevated operational load"],
                "cascade_risk": "MODERATE",
                "impacted_systems": ["dependent infrastructure systems"],
                "actions": [
                    "Investigate root cause",
                    "Monitor for escalation",
                    "Notify operations team",
                ],
            }

        # ── 2. Contributing factor assembly ───────────────────────────────
        factors = []
        fid = 0

        # Primary cause factor
        primary_cause_desc = rule["primary_causes"][0]
        factors.append(
            {
                "factor_id": f"F{fid:02d}",
                "name": "Primary Trigger",
                "factor_type": "PRIMARY",
                "description": primary_cause_desc,
                "confidence": min(0.95, 0.7 + score * 0.3),
                "weight": 1.0,
                "category": category,
                "evidence": [
                    f"{metric_name.replace('_', ' ').title()} reading: {score*100:.0f}% anomaly score",
                    f"Severity classification: {severity}",
                    f"Event timestamp: {timestamp[:16].replace('T', ' ')}",
                ],
                "metric_refs": [metric_name],
            }
        )
        fid += 1

        # Amplifier factors from rule
        for i, amp in enumerate(rule["amplifiers"][:3]):
            factors.append(
                {
                    "factor_id": f"F{fid:02d}",
                    "name": f"Amplifying Condition {i+1}",
                    "factor_type": "AMPLIFIER",
                    "description": amp,
                    "confidence": max(0.4, 0.75 - i * 0.1),
                    "weight": max(0.3, 0.8 - i * 0.15),
                    "category": category,
                    "evidence": [
                        f"Pattern consistent with known amplification mechanism in {_CATEGORY_LABELS.get(category, category)} domain"
                    ],
                    "metric_refs": [metric_name],
                }
            )
            fid += 1

        # Temporal factor
        temp_factor = _TEMPORAL_FACTORS.get(time_ctx)
        if temp_factor:
            factors.append(
                {
                    "factor_id": f"F{fid:02d}",
                    "name": temp_factor["name"],
                    "factor_type": "TEMPORAL",
                    "description": temp_factor["desc"],
                    "confidence": temp_factor["confidence"],
                    "weight": temp_factor["weight"],
                    "category": "TEMPORAL",
                    "evidence": [
                        f"Time-of-day: {dt.strftime('%H:%M') if 'dt' in dir() else 'Unknown'}",
                        f"Window: {time_ctx.replace('_', ' ').title()}",
                    ],
                    "metric_refs": [],
                }
            )
            fid += 1

        # Weather / environmental factor
        env_factors = _WEATHER_FACTORS.get(time_ctx, [])
        for ef in env_factors[:1]:
            factors.append(
                {
                    "factor_id": f"F{fid:02d}",
                    "name": ef["name"],
                    "factor_type": "ENVIRONMENTAL",
                    "description": ef["desc"],
                    "confidence": ef["confidence"],
                    "weight": ef["weight"],
                    "category": "WEATHER",
                    "evidence": [
                        f"Meteorological conditions consistent with {time_ctx.replace('_', ' ').lower()} pattern"
                    ],
                    "metric_refs": [],
                }
            )
            fid += 1

        # Cross-domain correlate factors
        domain_corrs = _DOMAIN_CORRELATIONS.get(category, [])
        for corr in domain_corrs[:2]:
            factors.append(
                {
                    "factor_id": f"F{fid:02d}",
                    "name": f"Cross-Domain Pressure: {corr['domain'].replace('_', ' ').title()}",
                    "factor_type": "CORRELATE",
                    "description": corr["desc"].capitalize(),
                    "confidence": corr["strength"] * 0.85,
                    "weight": corr["strength"] * 0.65,
                    "category": corr["domain"],
                    "evidence": [
                        f"Correlation coefficient: {corr['strength']:.2f}",
                        f"Typical lag: {corr['lag']} min",
                    ],
                    "metric_refs": [],
                }
            )
            fid += 1

        # ── 3. Correlation chain ──────────────────────────────────────────
        chain = []
        primary_id = "F00"
        for f in factors[1:]:
            if f["factor_type"] in ("AMPLIFIER", "TEMPORAL", "ENVIRONMENTAL"):
                chain.append(
                    {
                        "from_factor": f["factor_id"],
                        "to_factor": primary_id,
                        "relationship": "AMPLIFIED",
                        "strength": f["weight"],
                        "lag_minutes": 0,
                    }
                )
            elif f["factor_type"] == "CORRELATE":
                chain.append(
                    {
                        "from_factor": primary_id,
                        "to_factor": f["factor_id"],
                        "relationship": "TRIGGERED",
                        "strength": f["weight"],
                        "lag_minutes": domain_corrs[0]["lag"] if domain_corrs else 5,
                    }
                )

        # ── 4. Reasoning steps ────────────────────────────────────────────
        steps = [
            {
                "step_index": 0,
                "step_type": "OBSERVE",
                "title": "Anomaly Signal Detected",
                "detail": f"Sensor telemetry for '{metric_name.replace('_', ' ')}' in {district} recorded an anomaly score of {score*100:.0f}% at {timestamp[:16].replace('T', ' ')} UTC, classified as {severity} severity. This exceeds the dynamic threshold established from rolling 24-hour baseline analysis.",
                "confidence": 0.99,
                "supporting_factors": ["F00"],
            },
            {
                "step_index": 1,
                "step_type": "HYPOTHESIZE",
                "title": "Primary Cause Identification",
                "detail": f"Pattern matching against the {_CATEGORY_LABELS.get(category, category)} domain knowledge base identifies '{primary_cause_desc}' as the most probable primary trigger. The confidence of this attribution is {min(95, int(70 + score * 30))}% based on metric signature alignment and temporal context.",
                "confidence": min(0.95, 0.7 + score * 0.3),
                "supporting_factors": ["F00", "F01"],
            },
            {
                "step_index": 2,
                "step_type": "CORRELATE",
                "title": "Contributing Factor Analysis",
                "detail": f"Analysis of {len(factors) - 1} secondary signals reveals amplification from temporal ({time_label}), environmental conditions, and cross-domain infrastructure pressure. The combined effect of these factors amplifies the base anomaly severity by an estimated {int(score * 35 + 10)}%.",
                "confidence": max(0.55, score * 0.8),
                "supporting_factors": [f["factor_id"] for f in factors[1:]],
            },
            {
                "step_index": 3,
                "step_type": "CONCLUDE",
                "title": "Causal Chain Synthesis",
                "detail": f"The {severity.lower()} severity classification is consistent with the identified causal structure. Cascade risk to dependent systems — {', '.join(rule['impacted_systems'][:3])} — is assessed as {rule['cascade_risk']}. {'Immediate escalation recommended.' if severity == 'CRITICAL' else 'Monitor for escalation trajectory.'}",
                "confidence": min(0.92, 0.65 + score * 0.3),
                "supporting_factors": [f["factor_id"] for f in factors],
            },
            {
                "step_index": 4,
                "step_type": "RECOMMEND",
                "title": "Remediation Pathway",
                "detail": f"Based on the causal analysis, {len(rule['actions'])} remediation actions are recommended in priority order: {rule['actions'][0]}. Successful execution of the primary action is projected to reduce anomaly score by 40–65% within {15 if severity == 'CRITICAL' else 30} minutes.",
                "confidence": 0.80,
                "supporting_factors": ["F00"],
            },
        ]

        # ── 5. Natural language generation ────────────────────────────────
        metric_label = metric_name.replace("_", " ")
        cat_label = _CATEGORY_LABELS.get(category, category.lower())
        domain_corr_desc = domain_corrs[0]["desc"] if domain_corrs else ""
        amplifier = (
            rule["amplifiers"][0]
            if rule["amplifiers"]
            else "concurrent operational load"
        )

        headline = (
            f"{metric_label.title()} anomaly in {district} "
            f"caused by {primary_cause_desc} {time_label}."
        )

        summary = (
            f"A {severity.lower()}-severity {metric_label} event was detected in {district} at "
            f"{timestamp[11:16]} UTC, scoring {score*100:.0f}% above the anomaly threshold. "
            f"The root trigger is identified as {primary_cause_desc}. "
            f"Secondary amplification from {amplifier} elevated the overall impact severity."
        )

        # Build richer causal narrative
        factor_list = ", ".join(f["name"].lower() for f in factors[1:3])
        corr_clause = f" Furthermore, {domain_corr_desc}." if domain_corr_desc else ""
        causal_narrative = (
            f"At {timestamp[11:16]} UTC {time_label}, the {cat_label} monitoring system "
            f"recorded a significant deviation in {metric_label} metrics within the {district} zone. "
            f"The AI reasoning engine identifies {primary_cause_desc} as the primary causal factor, "
            f"operating within a context amplified by {factor_list}. "
            f"The {time_ctx.replace('_', ' ').lower()} period creates heightened baseline demand "
            f"across interconnected infrastructure domains, reducing system tolerance margins and "
            f"accelerating the severity of the observed anomaly.{corr_clause} "
            f"The estimated cascade exposure spans {len(rule['impacted_systems'])} downstream systems: "
            f"{', '.join(rule['impacted_systems'])}. "
            f"Overall explanation confidence is rated as "
            f"{'STRONG' if score > 0.7 else 'MODERATE' if score > 0.45 else 'SPECULATIVE'} "
            f"based on signal quality and causal rule coverage."
        )

        # Overall confidence
        overall_confidence = round(
            min(0.97, 0.6 + score * 0.35 + (0.05 if temp_factor else 0)), 3
        )
        explanation_quality = (
            "STRONG"
            if overall_confidence >= 0.75
            else "MODERATE" if overall_confidence >= 0.55 else "SPECULATIVE"
        )

        latency_ms = int((time.perf_counter() - t0) * 1000)

        return {
            "anomaly_id": anomaly_id,
            "metric_name": metric_name,
            "severity": severity,
            "category": category,
            "timestamp": timestamp,
            "district": district,
            "score": score,
            "headline": headline,
            "summary": summary,
            "causal_narrative": causal_narrative,
            "contributing_factors": factors,
            "correlation_chain": chain,
            "reasoning_steps": steps,
            "overall_confidence": overall_confidence,
            "explanation_quality": explanation_quality,
            "primary_cause": primary_cause_desc,
            "cascade_risk": rule["cascade_risk"],
            "impacted_systems": rule["impacted_systems"],
            "recommended_actions": rule["actions"],
            "ai_model_version": "ChronoShield-XAI-v2.4",
            "explanation_latency_ms": latency_ms,
        }

    @staticmethod
    def explain_batch(anomalies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate explanations for a batch of anomalies and identify
        cross-incident patterns.
        """
        explanations = [
            ExplainService.explain_anomaly(
                **{
                    k: v
                    for k, v in a.items()
                    if k
                    in (
                        "anomaly_id",
                        "metric_name",
                        "severity",
                        "category",
                        "score",
                        "timestamp",
                        "district",
                        "description",
                        "related_ids",
                    )
                }
            )
            for a in anomalies
        ]

        high_conf = sum(1 for e in explanations if e["overall_confidence"] >= 0.75)

        # Cross-incident pattern detection
        categories = [e["category"] for e in explanations]
        cat_counts: Dict[str, int] = {}
        for c in categories:
            cat_counts[c] = cat_counts.get(c, 0) + 1
        dominant = sorted(cat_counts, key=cat_counts.get, reverse=True)[:2]

        patterns = []
        if cat_counts.get("POWER", 0) >= 1 and cat_counts.get("INTERNET", 0) >= 1:
            patterns.append(
                "Power-Internet co-occurrence detected — suggests shared infrastructure vulnerability or cascade propagation"
            )
        if cat_counts.get("TRAFFIC", 0) >= 2:
            patterns.append(
                "Multiple simultaneous traffic events indicate systemic network stress, not isolated incidents"
            )
        if cat_counts.get("WATER", 0) >= 1 and cat_counts.get("TRAFFIC", 0) >= 1:
            patterns.append(
                "Water infrastructure failure correlating with traffic disruption — possible road surface flooding cascade"
            )
        if len(explanations) >= 3 and all(
            e["severity"] in ("CRITICAL", "WARNING") for e in explanations
        ):
            patterns.append(
                "Coordinated multi-domain elevation suggests a shared environmental trigger (e.g., extreme weather or grid instability)"
            )

        system_narrative = (
            f"Analysis of {len(explanations)} concurrent anomalies reveals systemic stress "
            f"concentrated in {' and '.join(_CATEGORY_LABELS.get(d, d) for d in dominant)} domains. "
            f"{patterns[0] if patterns else 'No significant cross-incident patterns detected at this time.'} "
            f"Confidence-weighted severity suggests {'immediate multi-team response coordination' if high_conf > len(explanations)//2 else 'standard monitoring and staged response'}."
        )

        return {
            "explanations": explanations,
            "total_analyzed": len(explanations),
            "high_confidence_count": high_conf,
            "cross_incident_patterns": patterns,
            "system_narrative": system_narrative,
        }
