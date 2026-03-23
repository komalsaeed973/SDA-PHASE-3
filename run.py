#this is our main.py 
# the code must be run from here 

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
import threading
import queue
import argparse
import time

from modules.input_module import InputModule
from modules.core_module import CoreWorker, Aggregator
from modules.output_module import OutputModule
from modules.telemetry import PipelineTelemetry, ConsoleTelemetryObserver


class SlowCoreWorker(CoreWorker):
    """CoreWorker with artificial delay to demonstrate backpressure."""
    def run(self):
        from modules.core_module import verify_signature, compute_window_average
        print(f"[CoreWorker-{self._id}] Starting ...")
        verified = dropped = 0
        while True:
            packet = self._raw_q.get()
            if packet is None:
                self._inter_q.put(None)
                break
            if verify_signature(
                packet["metric_value"],
                packet["security_hash"],
                self._secret,
                self._algo,
                self._iters,
            ):
                self._inter_q.put(packet)
                verified += 1
            else:
                dropped += 1
            time.sleep(0.4)   # artificial delay — makes Raw Queue fill up visibly
        print(f"[CoreWorker-{self._id}] Done — verified={verified}, dropped={dropped}")


class SlowAggregator(Aggregator):
    """Aggregator with artificial delay to demonstrate intermediate backpressure."""
    def run(self):
        from modules.core_module import compute_window_average
        from collections import deque
        print("[Aggregator] Starting ...")
        sentinels_received = 0
        processed = 0
        window = deque(maxlen=self._window_size)
        while True:
            packet = self._inter_q.get()
            if packet is None:
                sentinels_received += 1
                if sentinels_received >= self._num_workers:
                    break
                continue
            window.append(packet["metric_value"])
            avg = compute_window_average(window)
            enriched = dict(packet)
            enriched["computed_metric"] = round(avg, 4)
            self._proc_q.put(enriched)
            processed += 1
            time.sleep(0.2)   # artificial delay — makes Intermediate Queue fill up
        self._proc_q.put(None)
        print(f"[Aggregator] Done — {processed} packets forwarded.")


def main(config_path="config.json"):
    with open(config_path, "r", encoding="utf-8") as fh:
        config = json.load(fh)

    dynamics   = config["pipeline_dynamics"]
    max_q_size = dynamics["stream_queue_max_size"]
    n_workers  = dynamics["core_parallelism"]

    print(f"[Main] Config loaded: {config_path}")
    print(f"[Main] Workers={n_workers}, QueueMax={max_q_size}")

    raw_queue          = queue.Queue(maxsize=max_q_size)
    intermediate_queue = queue.Queue(maxsize=max_q_size)
    processed_queue    = queue.Queue(maxsize=max_q_size)

    print("[Main] Queues created...")

    telemetry = PipelineTelemetry(
        raw_queue, intermediate_queue, processed_queue, max_q_size
    )
    telemetry.subscribe(ConsoleTelemetryObserver())
    telemetry.start()

    output_mod = OutputModule(config, processed_queue)
    telemetry.subscribe(output_mod)

    input_thread = threading.Thread(
        target=lambda: InputModule(config, raw_queue).run(),
        name="InputThread",
        daemon=True
    )

    core_threads = [
        threading.Thread(
            target=lambda wid=wid: SlowCoreWorker(config, raw_queue, intermediate_queue, wid).run(),
            name=f"CoreWorker-{wid}",
            daemon=True
        )
        for wid in range(n_workers)
    ]

    agg_thread = threading.Thread(
        target=lambda: SlowAggregator(config, intermediate_queue, processed_queue, n_workers).run(),
        name="AggregatorThread",
        daemon=True
    )

    print("[Main] Starting all threads...")
    input_thread.start()
    for t in core_threads:
        t.start()
    agg_thread.start()
    print("[Main] All threads running!\n")

    try:
        output_mod.run()
    except KeyboardInterrupt:
        print("\n[Main] Stopped by user.")

    input_thread.join()
    for t in core_threads:
        t.join()
    agg_thread.join()

    telemetry.stop()
    print("\n[Main] Pipeline complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.json")
    args = parser.parse_args()
    main(args.config)
