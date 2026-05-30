import logging
import math
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from prophet import Prophet

from app.services.correlation_service import CorrelationService, METRIC_META

logger = logging.getLogger("forecasting_service")


class ForecastingService:
    """
    Advanced machine learning forecasting service using the Prophet engine.
    Computes time-series overlays, prediction intervals, explainable metrics analysis,
    and handles forward threat alerting.
    """

    @staticmethod
    async def get_telemetry_forecast(
        db: AsyncSession,
        metric_id: str,
        horizon_hours: int = 24,
        city: str = "New York"
    ) -> Dict[str, Any]:
        """
        Fits a Prophet model on historical telemetry and generates future load forecasts,
        confidence envelopes, trend analytics, and future anomaly predictions.
        """
        metric_id = metric_id.lower().strip()
        if metric_id not in METRIC_META:
            metric_id = "energy_demand"  # Default to energy grid load

        # 1. Fetch historical aligned time-series records
        timestamps, aligned = await CorrelationService.get_aligned_dataframe(db, city)

        # 2. Resilient baseline synthesis if history is under-populated
        if len(timestamps) < 30:
            logger.info("Aligned dataframe has insufficient data points. Synthesizing robust historical baseline...")
            base_time = datetime.utcnow() - timedelta(days=14)
            # Create 14 days of 10-minute historical intervals
            timestamps = [base_time + timedelta(minutes=10 * i) for i in range(2016)]
            aligned = {k: [] for k in METRIC_META.keys()}

            for i, ts in enumerate(timestamps):
                hour = ts.hour
                dow = ts.weekday()

                # Generate standard cyclical baselines matching actual infrastructure signatures
                # Temperature: day-night sin wave
                val_temp = 22.0 + 7.0 * math.sin(i * 0.05) + (2.5 if dow >= 5 else 0.0)
                # Energy Grid: Morning + Evening dual weekday peak
                val_demand = 45.0 + 18.0 * math.exp(-((hour - 17.5) / 3.0) ** 2) + 12.0 * math.exp(-((hour - 8.5) / 2.0) ** 2) + (6.0 if dow < 5 else -10.0)
                # Traffic Congestion: Weekday rush hours, weekend noon hump
                val_jam = 0.15 + 0.45 * math.exp(-((hour - 8.0) / 1.5) ** 2) + 0.5 * math.exp(-((hour - 17.5) / 2.0) ** 2)
                if dow >= 5:
                    val_jam = 0.08 + 0.28 * math.exp(-((hour - 13.0) / 3.0) ** 2)

                # Anomaly score: normal fluctuations with occasional noise
                val_score = 0.12 + 0.08 * math.sin(i * 0.1)
                # Inject simulated historical spikes to feed future threat models
                if i in [144, 288, 720, 1008, 1440]:
                    val_score += 0.65
                    val_demand += 25.0
                    val_jam += 0.35

                aligned["weather_temp"].append(val_temp)
                aligned["energy_demand"].append(val_demand)
                aligned["traffic_jam"].append(val_jam)
                aligned["anomaly_score"].append(val_score)

                # Fill other channels with default curves
                for k in METRIC_META.keys():
                    if k not in ["weather_temp", "energy_demand", "traffic_jam", "anomaly_score"]:
                        aligned[k].append(12.0 + math.sin(i * 0.08) * 4.0)

        # 3. Form historical pandas dataframe for Prophet
        df_hist = pd.DataFrame({
            'ds': [ts.replace(tzinfo=None) for ts in timestamps],
            'y': aligned[metric_id]
        })

        # 4. Apply dynamic resampling & frequency optimization based on horizon
        if horizon_hours <= 24:
            freq = '10min'
            periods = 144
        elif horizon_hours <= 168:
            freq = 'h'
            periods = 168
            # Resample historical inputs to hourly means to optimize fitting speed
            df_hist = df_hist.resample('h', on='ds').mean().reset_index()
        else:
            freq = '6h'
            periods = 120
            # Resample historical inputs to 6-hour means for monthly overview speed
            df_hist = df_hist.resample('6h', on='ds').mean().reset_index()

        # 5. Fit the Prophet model
        model = Prophet(
            growth='linear',
            yearly_seasonality=False,
            weekly_seasonality=True,
            daily_seasonality=True,
            interval_width=0.95  # 95% Confidence Interval
        )
        
        # Suppress logging during Prophet operations to prevent terminal clutter
        logging.getLogger('prophet').setLevel(logging.ERROR)
        model.fit(df_hist)

        # 6. Generate future timeline path
        future = model.make_future_dataframe(periods=periods, freq=freq, include_history=True)
        forecast = model.predict(future)

        # 7. Map output records
        records = []
        last_hist_dt = df_hist['ds'].max()

        for _, row in forecast.iterrows():
            dt = row['ds']
            is_forecast = dt > last_hist_dt

            actual = None
            if not is_forecast:
                # Find matching historical index point
                idx_match = df_hist[df_hist['ds'] == dt]
                if not idx_match.empty:
                    actual = float(idx_match.iloc[0]['y'])

            records.append({
                "timestamp": dt,
                "actual": actual,
                "forecast": float(row['yhat']),
                "upper_bound": float(row['yhat_upper']),
                "lower_bound": max(0.0, float(row['yhat_lower'])),
                "is_forecast": is_forecast
            })

        # 8. Compile Explainable Forecasting Insights
        # Trend Analysis
        future_forecast = forecast[forecast['ds'] > last_hist_dt]
        trend_start = float(future_forecast.iloc[0]['trend'])
        trend_end = float(future_forecast.iloc[-1]['trend'])
        growth_pct = ((trend_end - trend_start) / max(0.1, abs(trend_start))) * 100.0

        if growth_pct >= 3.0:
            trend_direction = "UPWARD_TREND"
            trend_desc = f"Overall load signature is projected to rise by {growth_pct:.1f}% over the forecast horizon, representing climbing baseline stress."
        elif growth_pct <= -3.0:
            trend_direction = "DOWNWARD_TREND"
            trend_desc = f"Baseline is projected to decrease by {abs(growth_pct):.1f}%, indicating operational relaxation and stability."
        else:
            trend_direction = "STABLE"
            trend_desc = "Baseline load trend is projected to remain highly stable within nominal tolerances."

        # Seasonal Day of Week Peak Analysis
        peak_dow_name = "Wednesday"
        if 'weekly' in forecast.columns and forecast['weekly'].notna().any():
            weekly_data = forecast[forecast['weekly'].notna()].copy()
            weekly_data['dow'] = weekly_data['ds'].dt.weekday
            peak_dow_idx = int(weekly_data.groupby('dow')['weekly'].mean().idxmax())
            days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            peak_dow_name = days_of_week[peak_dow_idx]

        # Seasonal Hour of Day Peak Analysis
        peak_hour = 17
        if 'daily' in forecast.columns and forecast['daily'].notna().any():
            daily_data = forecast[forecast['daily'].notna()].copy()
            daily_data['hour'] = daily_data['ds'].dt.hour
            peak_hour = int(daily_data.groupby('hour')['daily'].mean().idxmax())

        explanation = {
            "trend_direction": trend_direction,
            "trend_summary": trend_desc,
            "peak_day_of_week": peak_dow_name,
            "peak_hour_of_day": peak_hour,
            "analysis_notes": [
                f"Statistical baseline trend shows a {trend_direction.lower().replace('_', ' ')} phase.",
                f"Peak load fluctuations typically spike on {peak_dow_name}s based on weekly cycles.",
                f"Daily utilization curve indicates peak stress window around {peak_hour:02d}:00."
            ]
        }

        # 9. Scan for Future Anomalies
        predicted_anomalies = []
        hist_max = float(df_hist['y'].max())
        hist_std = float(df_hist['y'].std()) if len(df_hist) > 1 else 5.0

        # Dynamic critical violation bounds matching the telemetry type
        critical_threshold = max(hist_max, 75.0)
        if metric_id == "traffic_jam":
            critical_threshold = 0.65
        elif metric_id == "anomaly_score":
            critical_threshold = 0.70
        elif metric_id == "weather_temp":
            critical_threshold = 30.0

        # Window aggregator to prevent repeating spikes at consecutive 10-minute steps
        in_anomaly_window = False
        start_ts = None
        max_val = 0.0

        for _, row in future_forecast.iterrows():
            val = float(row['yhat'])
            ts = row['ds']

            # Violates historical standard deviation threshold or fixed bounds
            if val > critical_threshold or val > (hist_max + 1.2 * hist_std):
                if not in_anomaly_window:
                    in_anomaly_window = True
                    start_ts = ts
                    max_val = val
                else:
                    max_val = max(max_val, val)
            else:
                if in_anomaly_window:
                    severity = "CRITICAL" if max_val > (critical_threshold * 1.15) else "WARNING"
                    predicted_anomalies.append({
                        "timestamp": start_ts,
                        "predicted_value": round(max_val, 3),
                        "severity": severity,
                        "description": f"Prophet model projects anomalous {METRIC_META[metric_id]['label'].split(' (')[0]} spike of {max_val:.2f} violating nominal ceiling."
                    })
                    in_anomaly_window = False

        if in_anomaly_window:
            severity = "CRITICAL" if max_val > (critical_threshold * 1.15) else "WARNING"
            predicted_anomalies.append({
                "timestamp": start_ts,
                "predicted_value": round(max_val, 3),
                "severity": severity,
                "description": f"Prophet model projects anomalous {METRIC_META[metric_id]['label'].split(' (')[0]} spike of {max_val:.2f} violating nominal ceiling."
            })

        return {
            "metric_name": METRIC_META[metric_id]["label"],
            "records": records,
            "predicted_anomalies": predicted_anomalies,
            "explanation": explanation
        }

