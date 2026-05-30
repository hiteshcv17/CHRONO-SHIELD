"""
Phase 27 — Historical Replay & Incident Timeline Analysis
Forensic timeline reconstruction engine.

Builds a 24-hour incident timeline bucketed into 30-minute windows,
computes per-bucket health metrics, and supports incident comparison
for root-cause and cascading failure analysis.
"""
import logging
import math
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any

logger = logging.getLogger("replay_service")

# ==============================================================================
# Deterministic Synthetic Incident Dataset — 24h x 48 buckets
# Structured to mimic realistic infrastructure failure patterns:
#   - Morning rush: traffic / power load (07:00–09:00)
#   - Midday web spike: internet / CPU anomalies (12:00–14:00)
#   - Afternoon power demand: energy grid (14:00–17:00)
#   - Evening social surge: water / infrastructure (18:00–21:00)
#   - Late-night maintenance window incidents (01:00–04:00)
# ==============================================================================

def _ts(base: datetime, h: int, m: int) -> str:
    return (base + timedelta(hours=h, minutes=m)).isoformat()

def _build_incident_dataset(base_date: datetime) -> List[Dict[str, Any]]:
    """
    Generates a rich 24-hour synthetic incident corpus with realistic
    temporal distribution patterns and cascade relationships.
    """
    B = base_date  # shorthand

    raw = [
        # ── Late-night maintenance window (00:00–03:30) ──────────────────────
        {"id": "INC-001", "h": 0,  "m": 12, "metric": "network_latency",   "sev": "INFO",     "score": 0.38, "cat": "INTERNET",              "dist": "North District",  "dur": 8,  "cascade": False, "desc": "Elevated latency during scheduled CDN maintenance window.",       "root": "Scheduled maintenance", "res": "No action needed — expected window."},
        {"id": "INC-002", "h": 0,  "m": 45, "metric": "grid_voltage",      "sev": "WARNING",  "score": 0.61, "cat": "POWER",                 "dist": "North District",  "dur": 15, "cascade": True,  "desc": "Voltage fluctuation detected during substation load balancing.",   "root": "Load balancing routine", "res": "Monitor substation output — escalate if >15min."},
        {"id": "INC-003", "h": 1,  "m": 5,  "metric": "cpu_usage",         "sev": "INFO",     "score": 0.42, "cat": "INTERNET",              "dist": "Central Grid",    "dur": 10, "cascade": False, "desc": "High CPU utilization on api-gateway-02 during batch job.",         "root": "Scheduled batch workload", "res": "Review batch scheduling — consider off-peak window."},
        {"id": "INC-004", "h": 1,  "m": 30, "metric": "water_pressure",    "sev": "WARNING",  "score": 0.57, "cat": "WATER",                 "dist": "South Harbor",    "dur": 22, "cascade": False, "desc": "Pressure drop in Zone 3 distribution network.",                   "root": "Valve partial blockage", "res": "Dispatch field crew to Zone 3 isolation valve."},
        {"id": "INC-005", "h": 2,  "m": 15, "metric": "power_outage",      "sev": "CRITICAL", "score": 0.93, "cat": "POWER",                 "dist": "East Industrial", "dur": 45, "cascade": True,  "desc": "Complete power outage — Industrial Block C, 4 facilities affected.","root": "Transformer fault B-7",  "res": "Deploy mobile generator. Isolate transformer B-7."},
        {"id": "INC-006", "h": 2,  "m": 18, "metric": "network_packet_loss","sev":"CRITICAL", "score": 0.88, "cat": "INTERNET",              "dist": "East Industrial", "dur": 38, "cascade": True,  "desc": "Packet loss spike — cascade from power outage INC-005.",          "root": "UPS failure (cascade INC-005)", "res": "Switch to secondary routing. Replace UPS units."},
        {"id": "INC-007", "h": 2,  "m": 55, "metric": "flood_sensor",      "sev": "WARNING",  "score": 0.64, "cat": "WATER",                 "dist": "South Harbor",    "dur": 30, "cascade": False, "desc": "Rising water level in retention basin — approaching threshold.",   "root": "Overnight rainfall accumulation", "res": "Open overflow channels. Alert civil engineering team."},
        {"id": "INC-008", "h": 3,  "m": 20, "metric": "road_signal",       "sev": "INFO",     "score": 0.33, "cat": "PUBLIC_INFRASTRUCTURE",  "dist": "Central Grid",    "dur": 12, "cascade": False, "desc": "Traffic signal controller reboot at Junction 42.",                "root": "Firmware update restart", "res": "Verify signal timing post-reboot."},
        {"id": "INC-009", "h": 4,  "m": 0,  "metric": "internet_bandwidth", "sev": "INFO",    "score": 0.29, "cat": "INTERNET",              "dist": "West Residential","dur": 8,  "cascade": False, "desc": "Unusually low bandwidth utilization — potential sensor offline.",  "root": "Sensor connectivity issue", "res": "Ping sensor node. Schedule hardware check."},
        {"id": "INC-010", "h": 4,  "m": 45, "metric": "energy_demand",     "sev": "INFO",     "score": 0.35, "cat": "POWER",                 "dist": "Central Grid",    "dur": 10, "cascade": False, "desc": "Low energy consumption detected — possible load shedding event.",  "root": "Off-peak consumption pattern", "res": "Verify with distribution team — normal for 04:45."},

        # ── Pre-dawn system wake-up (05:00–06:30) ────────────────────────────
        {"id": "INC-011", "h": 5,  "m": 15, "metric": "cpu_usage",         "sev": "INFO",     "score": 0.44, "cat": "INTERNET",              "dist": "North District",  "dur": 15, "cascade": False, "desc": "Morning system boot-up load spike across API gateway cluster.",    "root": "Scheduled service restarts", "res": "Expected pattern. No action required."},
        {"id": "INC-012", "h": 5,  "m": 50, "metric": "water_quality",     "sev": "WARNING",  "score": 0.60, "cat": "WATER",                 "dist": "Central Grid",    "dur": 25, "cascade": False, "desc": "Turbidity spike at water treatment plant — morning flush cycle.",  "root": "Routine morning flush", "res": "Monitor turbidity for 25min. Escalate if >NTU threshold."},
        {"id": "INC-013", "h": 6,  "m": 10, "metric": "traffic_jam",       "sev": "INFO",     "score": 0.40, "cat": "TRAFFIC",               "dist": "East Industrial", "dur": 20, "cascade": False, "desc": "Early commuter traffic building on Eastern Expressway.",           "root": "Morning commute start", "res": "Activate adaptive signal timing — Eastern corridor."},

        # ── Morning rush hour peak (07:00–09:30) ─────────────────────────────
        {"id": "INC-014", "h": 7,  "m": 0,  "metric": "traffic_jam",       "sev": "WARNING",  "score": 0.72, "cat": "TRAFFIC",               "dist": "Central Grid",    "dur": 35, "cascade": False, "desc": "Severe congestion at Central Business District crossroads.",       "root": "Peak commute hour", "res": "Deploy traffic management officers at key junctions."},
        {"id": "INC-015", "h": 7,  "m": 15, "metric": "energy_demand",     "sev": "WARNING",  "score": 0.75, "cat": "POWER",                 "dist": "North District",  "dur": 120,"cascade": True,  "desc": "Grid load surge — residential and commercial morning demand.",     "root": "Simultaneous AC + appliance startup", "res": "Activate demand-response protocol DR-7."},
        {"id": "INC-016", "h": 7,  "m": 30, "metric": "vehicle_count",     "sev": "WARNING",  "score": 0.68, "cat": "TRAFFIC",               "dist": "East Industrial", "dur": 45, "cascade": False, "desc": "Vehicle density 340% above baseline — East Industrial approach.", "root": "Factory shift change + school run", "res": "Enable reversible lanes on Sector 14 highway."},
        {"id": "INC-017", "h": 8,  "m": 0,  "metric": "traffic_accident",  "sev": "CRITICAL", "score": 0.89, "cat": "TRAFFIC",               "dist": "North District",  "dur": 65, "cascade": True,  "desc": "Multi-vehicle collision — NH-8 northbound, lanes 1-3 blocked.",    "root": "Wet road + tailgating", "res": "Dispatch emergency services. Activate detour routes N2, N4."},
        {"id": "INC-018", "h": 8,  "m": 5,  "metric": "road_signal",       "sev": "CRITICAL", "score": 0.82, "cat": "PUBLIC_INFRASTRUCTURE",  "dist": "North District",  "dur": 50, "cascade": True,  "desc": "Signal failure cascade from accident INC-017 at key intersection.","root": "Cascade from INC-017", "res": "Switch to manual traffic management. Repair signal controller."},
        {"id": "INC-019", "h": 8,  "m": 45, "metric": "internet_bandwidth", "sev": "WARNING", "score": 0.70, "cat": "INTERNET",              "dist": "Central Grid",    "dur": 30, "cascade": False, "desc": "Bandwidth saturation — office buildings connecting simultaneously.", "root": "Corporate network morning peak", "res": "Apply QoS throttling for non-critical applications."},
        {"id": "INC-020", "h": 9,  "m": 10, "metric": "water_pressure",    "sev": "INFO",     "score": 0.45, "cat": "WATER",                 "dist": "West Residential","dur": 15, "cascade": False, "desc": "Pressure variation as residential morning demand peaks.",          "root": "Morning usage spike (showers, etc.)", "res": "Normal operational range. Monitor only."},

        # ── Mid-morning (09:30–11:30) ─────────────────────────────────────────
        {"id": "INC-021", "h": 9,  "m": 45, "metric": "grid_voltage",      "sev": "INFO",     "score": 0.39, "cat": "POWER",                 "dist": "South Harbor",    "dur": 12, "cascade": False, "desc": "Minor voltage sag on harbor feeder — within acceptable range.",    "root": "Industrial equipment startup", "res": "Log event. No immediate action required."},
        {"id": "INC-022", "h": 10, "m": 20, "metric": "infrastructure_defect","sev":"WARNING","score": 0.58, "cat": "PUBLIC_INFRASTRUCTURE",  "dist": "West Residential","dur": 0,  "cascade": False, "desc": "Pothole cluster reported — Sector 7B main road, 12 reports.",      "root": "Road surface degradation", "res": "Schedule repair crew. Temporary patching by EOD."},
        {"id": "INC-023", "h": 10, "m": 55, "metric": "network_latency",   "sev": "INFO",     "score": 0.36, "cat": "INTERNET",              "dist": "South Harbor",    "dur": 8,  "cascade": False, "desc": "Latency spikes on inter-zone fiber link — self-recovered.",        "root": "Transient congestion", "res": "Monitor for recurrence. No action required."},
        {"id": "INC-024", "h": 11, "m": 15, "metric": "flood_sensor",      "sev": "INFO",     "score": 0.32, "cat": "WATER",                 "dist": "Central Grid",    "dur": 0,  "cascade": False, "desc": "Low flood sensor reading — canal level below seasonal average.",   "root": "Dry season conditions", "res": "Inform water authority. Update seasonal baseline."},

        # ── Noon surge (11:30–14:00) ──────────────────────────────────────────
        {"id": "INC-025", "h": 11, "m": 50, "metric": "energy_demand",     "sev": "WARNING",  "score": 0.74, "cat": "POWER",                 "dist": "Central Grid",    "dur": 95, "cascade": False, "desc": "AC load surge as midday temperatures rise — peak cooling demand.", "root": "Temperature: 38°C recorded", "res": "Activate peak demand management. Rotate industrial loads."},
        {"id": "INC-026", "h": 12, "m": 5,  "metric": "cpu_usage",         "sev": "WARNING",  "score": 0.77, "cat": "INTERNET",              "dist": "Central Grid",    "dur": 40, "cascade": False, "desc": "API gateway CPU at 91% — lunchtime traffic spike.",               "root": "Noon API request peak", "res": "Spin up 2 additional gateway instances. Enable auto-scale."},
        {"id": "INC-027", "h": 12, "m": 30, "metric": "traffic_jam",       "sev": "WARNING",  "score": 0.65, "cat": "TRAFFIC",               "dist": "Central Grid",    "dur": 60, "cascade": False, "desc": "Midday congestion — restaurant and retail zones at capacity.",     "root": "Lunch hour activity", "res": "Encourage alt routes via navigation platforms."},
        {"id": "INC-028", "h": 13, "m": 0,  "metric": "water_quality",     "sev": "WARNING",  "score": 0.63, "cat": "WATER",                 "dist": "East Industrial", "dur": 45, "cascade": False, "desc": "pH deviation at industrial discharge monitoring station.",         "root": "Industrial effluent release", "res": "Alert industrial unit. Increase treatment chemical dosing."},
        {"id": "INC-029", "h": 13, "m": 40, "metric": "internet_bandwidth", "sev": "CRITICAL","score": 0.92, "cat": "INTERNET",              "dist": "North District",  "dur": 55, "cascade": True,  "desc": "Backbone saturation — CDN failover triggered, high packet loss.",  "root": "DDoS-pattern traffic from external AS", "res": "Activate DDoS mitigation. Null-route suspicious prefixes."},
        {"id": "INC-030", "h": 13, "m": 42, "metric": "cpu_usage",         "sev": "CRITICAL", "score": 0.95, "cat": "INTERNET",              "dist": "North District",  "dur": 48, "cascade": True,  "desc": "API cluster at 99% CPU — cascade from bandwidth event INC-029.",   "root": "Cascade from INC-029", "res": "Rate-limit inbound connections. Scale horizontally immediately."},

        # ── Afternoon (14:00–17:00) ───────────────────────────────────────────
        {"id": "INC-031", "h": 14, "m": 10, "metric": "grid_voltage",      "sev": "CRITICAL", "score": 0.91, "cat": "POWER",                 "dist": "West Residential","dur": 40, "cascade": True,  "desc": "Voltage drop in West zone — 11% below nominal. Brownout risk.",   "root": "Industrial peak + cooling load simultaneous", "res": "Emergency load shedding Schedule B. Alert residential customers."},
        {"id": "INC-032", "h": 14, "m": 14, "metric": "energy_demand",     "sev": "CRITICAL", "score": 0.96, "cat": "POWER",                 "dist": "North District",  "dur": 55, "cascade": True,  "desc": "Peak demand record — 4,820 MW, 12% above safety threshold.",      "root": "Heatwave + simultaneous industrial demand", "res": "Activate emergency generation units G-11, G-12. Alert grid operator."},
        {"id": "INC-033", "h": 14, "m": 30, "metric": "road_signal",       "sev": "WARNING",  "score": 0.62, "cat": "PUBLIC_INFRASTRUCTURE",  "dist": "West Residential","dur": 25, "cascade": True,  "desc": "Signal controllers rebooting due to voltage instability INC-031.", "root": "Cascade from INC-031", "res": "UPS backup for signal controllers. Deploy traffic officers."},
        {"id": "INC-034", "h": 15, "m": 0,  "metric": "water_pressure",    "sev": "WARNING",  "score": 0.67, "cat": "WATER",                 "dist": "Central Grid",    "dur": 35, "cascade": False, "desc": "Pressure anomaly in main distribution trunk — possible pipe leak.", "root": "Pipe joint failure at km 4.2", "res": "Isolate segment 4A. Deploy emergency repair team."},
        {"id": "INC-035", "h": 15, "m": 45, "metric": "traffic_jam",       "sev": "WARNING",  "score": 0.69, "cat": "TRAFFIC",               "dist": "Central Grid",    "dur": 45, "cascade": False, "desc": "School dismissal + office early exits creating mixed congestion.", "root": "School hours + early office departures", "res": "Stagger signal phases. Deploy crossing guards at school zones."},
        {"id": "INC-036", "h": 16, "m": 20, "metric": "network_packet_loss","sev":"INFO",     "score": 0.40, "cat": "INTERNET",              "dist": "South Harbor",    "dur": 12, "cascade": False, "desc": "Brief packet loss on harbor monitoring link — self-healed.",       "root": "Transient fiber interference", "res": "Check fiber splice at Point 7. Schedule inspection."},
        {"id": "INC-037", "h": 16, "m": 50, "metric": "vehicle_count",     "sev": "WARNING",  "score": 0.71, "cat": "TRAFFIC",               "dist": "North District",  "dur": 75, "cascade": False, "desc": "Evening commute starting — NH-8 southbound approaching saturation.", "root": "Post-office-hours exodus", "res": "Activate evening variable message signs — alternate routes."},

        # ── Evening peak (17:00–21:00) ────────────────────────────────────────
        {"id": "INC-038", "h": 17, "m": 15, "metric": "energy_demand",     "sev": "WARNING",  "score": 0.76, "cat": "POWER",                 "dist": "West Residential","dur": 90, "cascade": False, "desc": "Residential evening load surge — cooking + entertainment appliances.","root": "Post-work residential peak", "res": "Continue DR-7 demand response protocol."},
        {"id": "INC-039", "h": 17, "m": 30, "metric": "traffic_accident",  "sev": "WARNING",  "score": 0.73, "cat": "TRAFFIC",               "dist": "East Industrial", "dur": 40, "cascade": False, "desc": "Minor collision at freight depot entrance — partial lane block.",   "root": "Freight truck blind spot", "res": "Dispatch traffic unit. Clear within 40 minutes."},
        {"id": "INC-040", "h": 18, "m": 0,  "metric": "internet_bandwidth", "sev": "WARNING", "score": 0.78, "cat": "INTERNET",              "dist": "West Residential","dur": 60, "cascade": False, "desc": "Streaming traffic surge — residential broadband at 87% capacity.", "root": "Evening entertainment peak (video streaming)", "res": "Apply bandwidth shaping for P2P protocols."},
        {"id": "INC-041", "h": 18, "m": 45, "metric": "water_pressure",    "sev": "CRITICAL", "score": 0.94, "cat": "WATER",                 "dist": "South Harbor",    "dur": 80, "cascade": True,  "desc": "Critical pipe rupture — South Harbor Zone 6, 2000 residents affected.","root": "Corrosion fatigue — pipe age 34yr", "res": "Emergency isolation. Truck tankers to Zone 6. 24hr repair window."},
        {"id": "INC-042", "h": 18, "m": 48, "metric": "flood_sensor",      "sev": "WARNING",  "score": 0.65, "cat": "WATER",                 "dist": "South Harbor",    "dur": 60, "cascade": True,  "desc": "Water flooding road surface from rupture INC-041.",               "root": "Cascade from INC-041", "res": "Traffic diversion. Pumping crew deployment."},
        {"id": "INC-043", "h": 19, "m": 30, "metric": "infrastructure_defect","sev":"WARNING","score": 0.55, "cat": "PUBLIC_INFRASTRUCTURE",  "dist": "Central Grid",    "dur": 0,  "cascade": False, "desc": "Street light outage cluster — 14 units in Sector 11.",             "root": "Feeder cable fault", "res": "Emergency electrician dispatch. Temporary pole lights."},
        {"id": "INC-044", "h": 20, "m": 0,  "metric": "grid_voltage",      "sev": "WARNING",  "score": 0.66, "cat": "POWER",                 "dist": "East Industrial", "dur": 30, "cascade": False, "desc": "Voltage irregularity at factory substation — equipment at risk.",  "root": "Capacitor bank failure", "res": "Isolate capacitor bank CB-4. Arrange replacement."},
        {"id": "INC-045", "h": 20, "m": 30, "metric": "traffic_jam",       "sev": "INFO",     "score": 0.43, "cat": "TRAFFIC",               "dist": "Central Grid",    "dur": 25, "cascade": False, "desc": "Late evening event dispersal from Stadium — temporary congestion.", "root": "Post-event crowd dispersal", "res": "Event traffic management in place. Self-resolving by 21:30."},

        # ── Late evening / night (21:00–24:00) ───────────────────────────────
        {"id": "INC-046", "h": 21, "m": 15, "metric": "water_quality",     "sev": "INFO",     "score": 0.37, "cat": "WATER",                 "dist": "Central Grid",    "dur": 0,  "cascade": False, "desc": "Chlorine residual slightly elevated in Zone 2B distribution.",     "root": "Over-dosing during treatment", "res": "Adjust dosing pump P-7. Flush Zone 2B hydrants."},
        {"id": "INC-047", "h": 21, "m": 45, "metric": "network_latency",   "sev": "INFO",     "score": 0.34, "cat": "INTERNET",              "dist": "East Industrial", "dur": 10, "cascade": False, "desc": "Latency increase on industrial IoT segment — sensor backlog.",     "root": "Data backfill after INC-006 recovery", "res": "Normal post-outage behavior. Will resolve within 15min."},
        {"id": "INC-048", "h": 22, "m": 10, "metric": "energy_demand",     "sev": "INFO",     "score": 0.30, "cat": "POWER",                 "dist": "North District",  "dur": 20, "cascade": False, "desc": "Demand falling as residential load reduces post-21:00.",           "root": "Expected evening demand taper", "res": "Ramp down emergency generation. Return to base load."},
        {"id": "INC-049", "h": 22, "m": 40, "metric": "road_signal",       "sev": "INFO",     "score": 0.28, "cat": "PUBLIC_INFRASTRUCTURE",  "dist": "West Residential","dur": 8,  "cascade": False, "desc": "Traffic signal switching to night-mode low-frequency cycling.",    "root": "Scheduled night mode activation", "res": "Expected behavior. No action needed."},
        {"id": "INC-050", "h": 23, "m": 20, "metric": "water_pressure",    "sev": "WARNING",  "score": 0.59, "cat": "WATER",                 "dist": "North District",  "dur": 35, "cascade": False, "desc": "Pressure anomaly at northern reservoir — level dropping faster than normal.","root": "Pipe leak — Zone 9 suspected", "res": "Deploy SCADA isolation. Night crew inspection of Zone 9."},
        {"id": "INC-051", "h": 23, "m": 55, "metric": "internet_bandwidth", "sev": "WARNING", "score": 0.66, "cat": "INTERNET",              "dist": "Central Grid",    "dur": 40, "cascade": False, "desc": "Anomalous bandwidth spike — possible automated backup jobs.",      "root": "Backup jobs + OS update synchronization", "res": "Throttle backup bandwidth. Schedule for 03:00–05:00 slot."},
    ]

    # Build cascade relationship map
    cascade_pairs = {
        "INC-005": ["INC-006"],
        "INC-017": ["INC-018"],
        "INC-029": ["INC-030"],
        "INC-031": ["INC-033"],
        "INC-032": [],
        "INC-041": ["INC-042"],
    }

    incidents = []
    for r in raw:
        ts = _ts(B, r["h"], r["m"])
        bucket_index = (r["h"] * 60 + r["m"]) // 30

        # Build related IDs
        related = []
        for parent, children in cascade_pairs.items():
            if r["id"] in children:
                related.append(parent)
            if r["id"] == parent:
                related.extend(children)

        incidents.append({
            "id": r["id"],
            "timestamp": ts,
            "metric_name": r["metric"],
            "severity": r["sev"],
            "category": r["cat"],
            "score": r["score"],
            "description": r["desc"],
            "district": r["dist"],
            "acknowledged": r["score"] < 0.70,
            "duration_minutes": r["dur"],
            "cascaded": r["cascade"],
            "related_ids": related,
            "root_cause_hint": r.get("root"),
            "resolution_hint": r.get("res"),
            "bucket_index": bucket_index,
        })

    return incidents


def _bucket_label(base: datetime, bucket_idx: int, bucket_mins: int) -> str:
    start = base + timedelta(minutes=bucket_idx * bucket_mins)
    end = start + timedelta(minutes=bucket_mins)
    return f"{start.strftime('%b %d, %H:%M')} – {end.strftime('%H:%M')}"


SEVERITY_WEIGHT = {"CRITICAL": 1.0, "WARNING": 0.6, "INFO": 0.25}


class ReplayService:
    """
    Forensic timeline reconstruction engine.
    Builds structured 30-minute bucket timelines from incident records,
    computes system health trajectories, and supports incident comparison.
    """

    @staticmethod
    def get_timeline(time_range_hours: int = 24) -> Dict[str, Any]:
        """
        Construct a full replay timeline for the given time range.
        Returns bucketed timeline + full incident list.
        """
        bucket_mins = 30
        n_buckets = (time_range_hours * 60) // bucket_mins

        # Use a fixed reference point: "today midnight" for reproducibility
        now = datetime.utcnow()
        base = datetime(now.year, now.month, now.day, 0, 0, 0)

        incidents = _build_incident_dataset(base)

        # Group incidents into buckets
        bucket_incidents: Dict[int, List[Dict]] = {i: [] for i in range(n_buckets)}
        for inc in incidents:
            bi = inc["bucket_index"]
            if 0 <= bi < n_buckets:
                bucket_incidents[bi].append(inc)

        # Build bucket summaries
        buckets = []
        cumulative_health = 92.0
        peak_bucket = 0
        peak_count = 0

        for idx in range(n_buckets):
            incs = bucket_incidents[idx]
            bucket_start = base + timedelta(minutes=idx * bucket_mins)
            bucket_end = bucket_start + timedelta(minutes=bucket_mins)

            sev_dist = {"CRITICAL": 0, "WARNING": 0, "INFO": 0}
            cat_dist = {"POWER": 0, "TRAFFIC": 0, "WATER": 0, "INTERNET": 0, "PUBLIC_INFRASTRUCTURE": 0}
            peak_score = 0.0
            health_penalty = 0.0

            for inc in incs:
                sev_dist[inc["severity"]] = sev_dist.get(inc["severity"], 0) + 1
                cat_dist[inc["category"]] = cat_dist.get(inc["category"], 0) + 1
                peak_score = max(peak_score, inc["score"])
                health_penalty += SEVERITY_WEIGHT.get(inc["severity"], 0.3) * inc["score"] * 4.5

            health_delta = -round(min(health_penalty, 20.0), 2)

            buckets.append({
                "bucket_index": idx,
                "timestamp_start": bucket_start.isoformat(),
                "timestamp_end": bucket_end.isoformat(),
                "label": _bucket_label(base, idx, bucket_mins),
                "anomaly_count": len(incs),
                "critical_count": sev_dist["CRITICAL"],
                "severity_distribution": sev_dist,
                "category_distribution": cat_dist,
                "peak_score": round(peak_score, 3),
                "health_delta": health_delta,
                "event_ids": [i["id"] for i in incs],
            })

            if len(incs) > peak_count:
                peak_count = len(incs)
                peak_bucket = idx

        total_critical = sum(1 for i in incidents if i["severity"] == "CRITICAL")

        return {
            "buckets": buckets,
            "incidents": incidents,
            "time_range_hours": time_range_hours,
            "bucket_duration_minutes": bucket_mins,
            "total_incidents": len(incidents),
            "total_critical": total_critical,
            "peak_bucket_index": peak_bucket,
            "timeline_start": base.isoformat(),
            "timeline_end": (base + timedelta(hours=time_range_hours)).isoformat(),
        }

    @staticmethod
    def get_replay_frame(bucket_index: int, incidents: List[Dict]) -> Dict[str, Any]:
        """
        Build a single replay frame for a given bucket index.
        """
        active = [i for i in incidents if i["bucket_index"] == bucket_index]
        cumulative = [i for i in incidents if i["bucket_index"] <= bucket_index]

        total_penalty = sum(
            SEVERITY_WEIGHT.get(i["severity"], 0.3) * i["score"] * 2.5
            for i in cumulative
        )
        health = max(5.0, min(100.0, 92.0 - total_penalty))

        critical_count = sum(1 for i in cumulative if i["severity"] == "CRITICAL")
        total_count = len(cumulative)

        cat_counts: Dict[str, int] = {}
        for inc in active:
            cat_counts[inc["category"]] = cat_counts.get(inc["category"], 0) + 1
        dominant = max(cat_counts, key=cat_counts.get) if cat_counts else None

        if health >= 75:
            alert_level = "NOMINAL"
        elif health >= 55:
            alert_level = "ELEVATED"
        elif health >= 35:
            alert_level = "HIGH"
        else:
            alert_level = "CRISIS"

        # Find bucket metadata
        bucket_data = {
            "bucket_index": bucket_index,
            "timestamp_start": "",
            "timestamp_end": "",
            "label": f"Bucket {bucket_index}",
            "anomaly_count": len(active),
            "critical_count": sum(1 for i in active if i["severity"] == "CRITICAL"),
            "severity_distribution": {"CRITICAL": 0, "WARNING": 0, "INFO": 0},
            "category_distribution": {"POWER": 0, "TRAFFIC": 0, "WATER": 0, "INTERNET": 0, "PUBLIC_INFRASTRUCTURE": 0},
            "peak_score": max((i["score"] for i in active), default=0.0),
            "health_delta": 0.0,
            "event_ids": [i["id"] for i in active],
        }

        return {
            "bucket": bucket_data,
            "active_incidents": active,
            "cumulative_critical": critical_count,
            "cumulative_total": total_count,
            "system_health": round(health, 1),
            "dominant_category": dominant,
            "alert_level": alert_level,
        }

    @staticmethod
    def compare_incidents(id_a: str, id_b: str, incidents: List[Dict]) -> Dict[str, Any]:
        """
        Perform forensic side-by-side comparison of two incidents.
        """
        inc_a = next((i for i in incidents if i["id"] == id_a), None)
        inc_b = next((i for i in incidents if i["id"] == id_b), None)

        if not inc_a or not inc_b:
            return {}

        # Similarity score based on category, severity, and district match
        sim = 0.0
        if inc_a["category"] == inc_b["category"]:
            sim += 0.4
        if inc_a["severity"] == inc_b["severity"]:
            sim += 0.25
        if inc_a["district"] == inc_b["district"]:
            sim += 0.2
        # Score proximity
        score_diff = abs(inc_a["score"] - inc_b["score"])
        sim += (1.0 - score_diff) * 0.15
        sim = round(min(1.0, sim), 3)

        # Time delta
        try:
            ta = datetime.fromisoformat(inc_a["timestamp"])
            tb = datetime.fromisoformat(inc_b["timestamp"])
            time_delta = int(abs((tb - ta).total_seconds()) / 60)
        except Exception:
            time_delta = 0

        # Shared properties
        shared_cats = ([inc_a["category"]] if inc_a["category"] == inc_b["category"] else [])
        shared_dists = ([inc_a["district"]] if inc_a["district"] == inc_b["district"] else [])

        # Correlation hint
        likely_correlated = bool(
            time_delta < 30 and
            (inc_a["category"] == inc_b["category"] or bool(shared_dists))
        )

        # Severity comparison
        sev_rank = {"CRITICAL": 3, "WARNING": 2, "INFO": 1}
        sa, sb = sev_rank.get(inc_a["severity"], 1), sev_rank.get(inc_b["severity"], 1)
        if sa > sb:
            severity_diff = f"{inc_a['id']} is more severe by {sa - sb} level(s)"
        elif sb > sa:
            severity_diff = f"{inc_b['id']} is more severe by {sb - sa} level(s)"
        else:
            severity_diff = "Equal severity level"

        # Combined risk
        combined = max(inc_a["score"], inc_b["score"])
        if combined >= 0.85:
            combined_risk = "EXTREME"
        elif combined >= 0.65:
            combined_risk = "HIGH"
        else:
            combined_risk = "MODERATE"

        return {
            "incident_a": inc_a,
            "incident_b": inc_b,
            "similarity_score": sim,
            "shared_categories": shared_cats,
            "shared_districts": shared_dists,
            "time_delta_minutes": time_delta,
            "likely_correlated": likely_correlated,
            "severity_diff": severity_diff,
            "score_diff": round(abs(inc_a["score"] - inc_b["score"]), 3),
            "combined_risk": combined_risk,
        }
