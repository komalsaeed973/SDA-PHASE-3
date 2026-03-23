"""
modules/input_module.py
Reads CSV, maps columns, casts types — all from config.json.
"""
import csv
import time
import multiprocessing
from typing import Any


_CASTERS = {
    "string":  str,
    "integer": int,
    "float":   float,
    "bool":    lambda v: v.strip().lower() in ("true", "1", "yes"),
}


def _cast(value: str, data_type: str) -> Any:
    caster = _CASTERS.get(data_type.lower(), str)
    return caster(value)


class InputModule:

    def __init__(self, config: dict, raw_queue):
        self._dataset_path = config["dataset_path"]
        self._delay        = config["pipeline_dynamics"]["input_delay_seconds"]
        self._schema       = config["schema_mapping"]["columns"]
        self._raw_queue    = raw_queue
        self._num_workers  = config["pipeline_dynamics"]["core_parallelism"]

    def run(self):
        print("[Input] Starting ...")
        rows_sent = 0

        with open(self._dataset_path, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for raw_row in reader:
                packet = self._map_row(raw_row)
                if packet is None:
                    continue
                self._raw_queue.put(packet)
                rows_sent += 1
                time.sleep(self._delay)

        for _ in range(self._num_workers):
            self._raw_queue.put(None)

        print(f"[Input] Done — {rows_sent} packets sent.")

    def _map_row(self, raw_row: dict):
        packet = {}
        for col_spec in self._schema:
            src   = col_spec["source_name"]
            dest  = col_spec["internal_mapping"]
            dtype = col_spec["data_type"]

            if src not in raw_row:
                print(f"[Input] WARNING: column '{src}' not found — skipping row")
                return None

            try:
                packet[dest] = _cast(raw_row[src], dtype)
            except (ValueError, TypeError) as exc:
                print(f"[Input] WARNING: cannot cast '{raw_row[src]}' to {dtype}: {exc} — skipping row")
                return None

        return packet