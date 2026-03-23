#observer design pattern for real time pipeline health monitoring.
import time 
import threading #to run the telemetry polling in a bg thread so it never blocks the main pipeline
from abc import ABC, abstractmethod #abstract base class. wull use it to create telemetryobserver interface so any class that inherits it will implement on_telemetry_update()


#observer interface:
class TelemetryObserver(ABC): #any class that wants to recieve telemetry updates must inherit from this
    @abstractmethod 
    def on_telemetry_update(self, snapshot: dict):
        pass
#subject:
class PipelineTelemetry:  #this is the subject in the observer pattern. it watches the queues and notifies all registered observers
    POLL_INTERVAL = 0.2 #wakes up rbery 0.2 sec to check queue sizes
    def __init__(self,
                 raw_queue,
                 intermediate_queue,
                 processed_queue,
                 max_size: int):
        self._raw_q    = raw_queue
        self._inter_q  = intermediate_queue
        self._proc_q   = processed_queue
        self._max_size = max_size

        self._observers = [] #will hold all registered observers like consoletelemetryobserver,outputmodule
        self._running   = False #true on start(), false on stop()
        self._thread    = None #will hold the bg polling thread
        self.latest     = {}
    def subscribe(self, observer): #adds an observer to the list
        self._observers.append(observer)

    def unsubscribe(self, observer): #removes an observer from the list
        self._observers.remove(observer)

    def _notify(self, snapshot: dict): #subject tells all obervers about a new event
        for obs in self._observers:
            obs.on_telemetry_update(snapshot)

    def start(self):
        self._running = True
        self._thread  = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
    def _poll_loop(self):
        while self._running:
            try:
                raw_size   = self._raw_q.qsize()
                inter_size = self._inter_q.qsize()
                proc_size  = self._proc_q.qsize()
            except Exception:
                raw_size = inter_size = proc_size = 0
            snapshot = {
                "raw_queue_size":          raw_size,
                "intermediate_queue_size": inter_size,
                "processed_queue_size":    proc_size,
                "max_size":                self._max_size,
                "timestamp":               time.time(),
            }
            self.latest = snapshot
            self._notify(snapshot)
            time.sleep(self.POLL_INTERVAL)

#concrete observer
class ConsoleTelemetryObserver(TelemetryObserver): #will print colour-coded queeu bars 

    _RESET  = "\033[0m"
    _GREEN  = "\033[92m"
    _YELLOW = "\033[93m"
    _RED    = "\033[91m"
    def on_telemetry_update(self, snapshot: dict):
        max_s = snapshot["max_size"] or 1
        def _bar(size):
            ratio  = size / max_s
            filled = int(ratio * 20)
            empty  = 20 - filled
            if ratio < 0.5:
                colour = self._GREEN
            elif ratio < 0.8:
                colour = self._YELLOW
            else:
                colour = self._RED
            return colour + "▓" * filled + "░" * empty + self._RESET

        print(
            f"\r[Telemetry]  "
            f"Raw[{snapshot['raw_queue_size']:3d}/{max_s}] {_bar(snapshot['raw_queue_size'])}  "
            f"Inter[{snapshot['intermediate_queue_size']:3d}/{max_s}] {_bar(snapshot['intermediate_queue_size'])}  "
            f"Proc[{snapshot['processed_queue_size']:3d}/{max_s}] {_bar(snapshot['processed_queue_size'])}",
            end="", flush=True
        )
