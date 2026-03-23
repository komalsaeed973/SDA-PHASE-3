"""
main.py  —  Central Orchestrator (Windows-compatible)
"""
import sys
import json
import argparse
import multiprocessing


def _run_input(config, raw_q):
    from modules.input_module import InputModule
    InputModule(config, raw_q).run()

def _run_core_worker(config, raw_q, inter_q, worker_id):
    from modules.core_module import CoreWorker
    CoreWorker(config, raw_q, inter_q, worker_id).run()

def _run_aggregator(config, inter_q, proc_q, num_workers):
    from modules.core_module import Aggregator
    Aggregator(config, inter_q, proc_q, num_workers).run()


def main(config_path: str = "config.json"):
    with open(config_path, "r", encoding="utf-8") as fh:
        config = json.load(fh)

    dynamics   = config["pipeline_dynamics"]
    max_q_size = dynamics["stream_queue_max_size"]
    n_workers  = dynamics["core_parallelism"]

    print(f"[Main] Config loaded: {config_path}")
    print(f"[Main] Workers={n_workers}, QueueMax={max_q_size}")

    raw_queue          = multiprocessing.Queue(maxsize=max_q_size)
    intermediate_queue = multiprocessing.Queue(maxsize=max_q_size)
    processed_queue    = multiprocessing.Queue(maxsize=max_q_size)

    print("[Main] Queues created...")

    from modules.telemetry import PipelineTelemetry, ConsoleTelemetryObserver
    from modules.output_module import OutputModule

    telemetry = PipelineTelemetry(
        raw_queue, intermediate_queue, processed_queue, max_q_size
    )
    console_observer = ConsoleTelemetryObserver()
    telemetry.subscribe(console_observer)
    telemetry.start()

    output_mod = OutputModule(config, processed_queue)
    telemetry.subscribe(output_mod)

    print("[Main] Starting processes...")

    input_proc = multiprocessing.Process(
        target=_run_input,
        args=(config, raw_queue),
        name="InputProcess",
        daemon=True,
    )

    core_procs = [
        multiprocessing.Process(
            target=_run_core_worker,
            args=(config, raw_queue, intermediate_queue, wid),
            name=f"CoreWorker-{wid}",
            daemon=True,
        )
        for wid in range(n_workers)
    ]

    agg_proc = multiprocessing.Process(
        target=_run_aggregator,
        args=(config, intermediate_queue, processed_queue, n_workers),
        name="AggregatorProcess",
        daemon=True,
    )

    input_proc.start()
    print("[Main] Input process started")
    for cp in core_procs:
        cp.start()
    print("[Main] Core workers started")
    agg_proc.start()
    print("[Main] Aggregator started")

    try:
        output_mod.run()
    except KeyboardInterrupt:
        print("\n[Main] Interrupted by user.")

    input_proc.join()
    for cp in core_procs:
        cp.join()
    agg_proc.join()

    telemetry.stop()
    print("\n[Main] Pipeline complete.")


if __name__ == "__main__":
    multiprocessing.freeze_support()
    multiprocessing.set_start_method("spawn", force=True)

    parser = argparse.ArgumentParser(description="Generic Concurrent Real-Time Pipeline")
    parser.add_argument("--config", default="config.json")
    args = parser.parse_args()
    main(args.config)
