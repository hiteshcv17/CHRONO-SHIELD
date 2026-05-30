# ChronoShield AI Datasets Directory

This folder holds baseline datasets and temporal sequences utilized for calibration, training, and unit verification loops.

---

## 📊 Directory Overview

Place your sequence metrics in this folder during training runs. Standard accepted formats are:
- `.csv`: Tabular time-series indices containing timestamps and metric features.
- `.parquet`: Standardized columns optimized for high-performance IO (highly recommended for deep sequence loops).
- `.h5` / `.hdf5`: Hierarchical data files containing deep structured time-series grids.

---

## 📈 Standard Input Telemetry Schema

For multi-dimensional anomaly detection inputs, structure datasets with the following baseline keys:

| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| `timestamp` | `datetime64[ns]` | Ingestion timestamp aligned with metrics sampling window. |
| `metric_id` | `string` | Unique label of the physical host or instance monitored. |
| `cpu_usage` | `float32` | Processor usage metrics [0.0 - 100.0] |
| `memory_usage`| `float32` | Memory saturation metrics [0.0 - 100.0] |
| `disk_io` | `float32` | Storage IO wait times or operations count. |
| `network_in`  | `float32` | Network ingress throughput rate. |
| `network_out` | `float32` | Network egress throughput rate. |
| `latency` | `float32` | System transaction delays or response latency. |

---

## 🧠 Sequence Processing Notes

The `TemporalDataPipeline` automatically consumes tables in this directory, aligns time offsets, fills missing sequences using linear interpolation, standardizes metrics utilizing rolling z-score transforms, and generates overlapping sequence arrays matching configured sliding limits (e.g. `SEQUENCE_LENGTH=60`).
