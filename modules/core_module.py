#functional core + imperative Shell with Scatter-Gather
import hashlib
import time
from collections import deque

#functional core.. pure functions
def verify_signature(metric_value: float,
                     security_hash: str,
                     secret_key: str,
                     algorithm: str,
                     iterations: int) -> bool:
    value_str = f"{metric_value:.2f}"
    password  = secret_key.encode("utf-8")
    salt      = value_str.encode("utf-8")
    computed  = hashlib.pbkdf2_hmac(algorithm, password, salt, iterations)
    return computed.hex() == security_hash

def compute_window_average(window: deque) -> float:
    if not window:
        return 0.0
    return sum(window) / len(window)


#imPERATIVE SHELL CoreWorker
class CoreWorker:
    def __init__(self, config: dict, raw_queue, intermediate_queue, worker_id: int = 0):
        tasks         = config["processing"]["stateless_tasks"]
        self._secret  = tasks["secret_key"]
        self._algo    = tasks["algorithm"]
        self._iters   = tasks["iterations"]
        self._raw_q   = raw_queue
        self._inter_q = intermediate_queue
        self._id      = worker_id
    def run(self):
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

        print(f"[CoreWorker-{self._id}] Done — verified={verified}, dropped={dropped}")


#IMPERATIVE SHELL aggregator 
class Aggregator:
    def __init__(self, config: dict, intermediate_queue, processed_queue, num_workers: int):
        window_cfg        = config["processing"]["stateful_tasks"]
        self._window_size = window_cfg["running_average_window_size"]
        self._inter_q     = intermediate_queue
        self._proc_q      = processed_queue
        self._num_workers = num_workers
        self._window      = deque(maxlen=self._window_size)

    def run(self):
        print("[Aggregator] Starting ...")
        sentinels_received = 0
        processed = 0

        while True:
            packet = self._inter_q.get()

            if packet is None:
                sentinels_received += 1
                if sentinels_received >= self._num_workers:
                    break
                continue

            self._window.append(packet["metric_value"])
            avg = compute_window_average(self._window)

            enriched = dict(packet)
            enriched["computed_metric"] = round(avg, 4)
            self._proc_q.put(enriched)
            processed += 1

        self._proc_q.put(None)
        print(f"[Aggregator] Done — {processed} packets forwarded.")