
 NeonThreadocalypse - Generic Concurrent Real Time Pipeline

MAIN FILE
    run.py

CONFIG FILE LOCATION
    config.json  (placed at project root, same level as run.py)

DATA FILE LOCATION
    Placed CSV dataset inside the  data/  folder.
    Default expected path:  data/climate_data.csv

    If using a different file then will have to update "dataset_path" in config.json accordingly.

HOW TO RUN
Step 1 — Install dependency:
    pip install matplotlib

Step 2 — Place CSV in the data/folder

Step 3 — Run the pipeline:
    python run.py
    Or with a custom config:
    python run.py --config config.json

REQUIREMENTS
    Python 3.10+
    matplotlib -> pip install matplotlib

SIGNATURE PROTOCOL
    algorithm : pbkdf2_hmac SHA-256
    password  : secret_key  (UTF-8 encoded)
    salt      : raw_value rounded to 2 decimal places  (UTF-8 encoded)
    iterations: defined in config.json

UNSEEN DATASET INSTRUCTIONS
1. Drop the new CSV into  data/
2. Edit config.json:
      "dataset_path"  -> path to the new CSV  e.g. "data/unseen_data.csv"
      "schema_mapping" -> match source_name to the new column headers
      "secret_key"  -> update if a different key is provided
      "iterations" -> update if different iterations are provided
3. Run:  python run.py

DASHBOARD
    A matplotlib window will open showing:
    - Raw Queue health bar   (green / orange / red)
    - Intermediate Queue health bar
    - Processed Queue health bar
    - Live Sensor Values chart (blue line)
    - Live Running Average chart  (orange line)

    Colour coding:
    Green  = Flowing smoothly  (queue < 50% full)
    Orange = Filling up        (queue 50-80% full)
    Red    = Backpressure      (queue > 80% full)

PROJECT STRUCTURE
    SDA PHASE 3/
    ├── run.py                   ← MAIN FILE (entry point)
    ├── config.json              ← All runtime configuration
    ├── generate_data.py         ← Sample dataset generator
    ├── readme.txt               ← This file
    ├── data/
    │   └── climate_data.csv     ← dataset here
    └── modules/
        ├── __init__.py
        ├── input_module.py      ← Generic CSV reader + schema mapper
        ├── core_module.py       ← Crypto verifier + sliding-window aggregator
        ├── output_module.py     ← Real-time dashboard (matplotlib)
        └── telemetry.py         ← Observer pattern - PipelineTelemetry subject

DESIGN PATTERNS USED
    Producer-Consumer   : Input → Core → Aggregator → Output via bounded queues
    Scatter-Gather      : 4 CoreWorker threads process packets in parallel
    Functional Core     : verify_signature() and compute_window_average() are pure functions
    Imperative Shell    : CoreWorker and Aggregator own all mutable state
    Observer Pattern    : PipelineTelemetry (Subject) notifies Dashboard and Console (Observers)
    Dependency Inversion: All modules depend on abstractions (config dict, Queue interface)

CONCURRENCY MODEL
    All pipeline stages run as daemon threads (Windows-compatible):
    - 1 InputThread       → reads CSV, pushes to raw_queue
    - 4 CoreWorker threads → verify signatures, push to intermediate_queue
    - 1 AggregatorThread  → computes running average, pushes to processed_queue
    - 1 Dashboard (main thread) → renders live charts

    Backpressure is natural — bounded queues block producers when full,
    automatically throttling the pipeline without any extra code.

