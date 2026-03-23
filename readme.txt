Generic Concurrent Real-Time Data Pipeline

A configurable, multiprocessing-based pipeline for real-time data ingestion, processing, and visualization.
The system is fully domain-agnostic and driven entirely by config.json

Features
Config-driven execution (no hardcoded dataset logic)
Multiprocessing with parallel core workers
Real-time streaming using bounded queues
Cryptographic signature verification
Running average
Backpressure handling
Telemetry dashboard using Observer Pattern

Architecture
Input → Raw Queue → Core Workers (Parallel) → Processed Queue → Output Dashboard
↑
Telemetry Monitor

Notes
Works with unseen datasets
Modules are fully decoupled
Ready for evaluation
