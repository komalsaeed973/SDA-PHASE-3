#realtime dashboard driven entirely by config.json
import threading #to run _drain_queue() in the bg
import time
from collections import deque
def _set_backend():
    import matplotlib
    for backend in ["TkAgg", "Qt5Agg", "QtAgg", "Agg"]:
        try:
            matplotlib.use(backend)
            import matplotlib.pyplot as plt
            plt.figure()
            plt.close()
            print(f"[Dashboard] Using backend: {backend}")
            return backend
        except Exception:
            continue
    return "Agg"
from modules.telemetry import TelemetryObserver #OUTPUT module must implement on_telemetry_update() to be a valid observer

class OutputModule(TelemetryObserver):
    MAX_DISPLAY_POINTS = 200 #charts only show last 200 data points
    def __init__(self, config: dict, processed_queue):
        self._processed_q = processed_queue
        self._vis_cfg     = config["visualizations"]
        self._tel_cfg     = self._vis_cfg["telemetry"]
        self._chart_cfgs  = self._vis_cfg["data_charts"]
        self._max_q_size  = config["pipeline_dynamics"]["stream_queue_max_size"]

        self._x_vals   = deque(maxlen=self.MAX_DISPLAY_POINTS)
        self._y_vals   = deque(maxlen=self.MAX_DISPLAY_POINTS)
        self._avg_vals = deque(maxlen=self.MAX_DISPLAY_POINTS)

        self._tel_snapshot = {}
        self._tel_lock     = threading.Lock()
        self._running      = True
    def on_telemetry_update(self, snapshot: dict):
        with self._tel_lock:
            self._tel_snapshot = snapshot

    def run(self):
        t = threading.Thread(target=self._drain_queue, daemon=True)
        t.start()
        active_backend = _set_backend()
        if active_backend == "Agg":
            print("[Dashboard] No GUI available — terminal-only mode.")
            print("[Dashboard] Pipeline running... Press Ctrl+C to stop.")
            t.join()
        else:
            self._build_and_run_dashboard()
    def _drain_queue(self):
        while self._running:
            packet = self._processed_q.get()
            if packet is None:
                self._running = False
                print("\n[Dashboard] All packets processed.")
                break
            if self._chart_cfgs:
                x_key = self._chart_cfgs[0]["x_axis"]
                y_key = self._chart_cfgs[0]["y_axis"]
                self._x_vals.append(packet.get(x_key, 0))
                self._y_vals.append(packet.get(y_key, 0))
            if len(self._chart_cfgs) > 1:
                self._avg_vals.append(packet.get("computed_metric", 0))
            #slowing down a little for visibility
            time.sleep(0.5)
    def _build_and_run_dashboard(self):
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
        from matplotlib.animation import FuncAnimation
        n_tel_rows = sum([
            self._tel_cfg.get("show_raw_stream",          False),
            self._tel_cfg.get("show_intermediate_stream", False),
            self._tel_cfg.get("show_processed_stream",    False),
        ])
        n_chart_rows = len(self._chart_cfgs)
        total_rows   = n_tel_rows + n_chart_rows
        fig, axes = plt.subplots(total_rows, 1, figsize=(12, 3 * total_rows))
        fig.suptitle("Real-Time Pipeline Dashboard", fontsize=14, fontweight="bold")
        fig.tight_layout(pad=3.0)

        if total_rows == 1:
            axes = [axes]
        row = 0
        tel_axes   = []
        tel_labels = []
        if self._tel_cfg.get("show_raw_stream"):
            tel_axes.append(axes[row]); tel_labels.append("Raw Queue"); row += 1
        if self._tel_cfg.get("show_intermediate_stream"):
            tel_axes.append(axes[row]); tel_labels.append("Intermediate Queue"); row += 1
        if self._tel_cfg.get("show_processed_stream"):
            tel_axes.append(axes[row]); tel_labels.append("Processed Queue"); row += 1
        chart_axes = []
        for cfg in self._chart_cfgs:
            ax = axes[row]
            ax.set_title(cfg["title"], fontsize=10)
            ax.set_xlabel(cfg["x_axis"])
            ax.set_ylabel(cfg["y_axis"])
            chart_axes.append((ax, cfg))
            row += 1

        def _update(_frame):
            with self._tel_lock:
                snap = dict(self._tel_snapshot)

            q_sizes = [
                snap.get("raw_queue_size",          0),
                snap.get("intermediate_queue_size", 0),
                snap.get("processed_queue_size",    0),
            ]

            for idx, (ax, lbl) in enumerate(zip(tel_axes, tel_labels)):
                ax.cla()
                ax.set_xlim(0, self._max_q_size)
                ax.set_ylim(0, 1)
                ax.set_yticks([])
                ax.set_title(lbl, fontsize=10)
                size   = q_sizes[idx] if idx < len(q_sizes) else 0
                ratio  = size / max(self._max_q_size, 1)
                colour = "green" if ratio < 0.5 else ("orange" if ratio < 0.8 else "red")
                ax.barh(0.5, size, height=0.6, color=colour, alpha=0.8)
                ax.text(size + 0.5, 0.5, f"{size}/{self._max_q_size}", va="center", fontsize=9)
                patches = [
                    mpatches.Patch(color="green",  label="Flowing   (<50%)"),
                    mpatches.Patch(color="orange", label="Filling   (50-80%)"),
                    mpatches.Patch(color="red",    label="Backpressure (>80%)"),
                ]
                ax.legend(handles=patches, loc="lower right", fontsize=7)
            for ax, cfg in chart_axes:
                ax.cla()
                ax.set_title(cfg["title"], fontsize=10)
                ax.set_xlabel(cfg["x_axis"])
                ax.set_ylabel(cfg["y_axis"])
                if cfg["type"] == "real_time_line_graph_values" and self._x_vals:
                    ax.plot(list(self._x_vals), list(self._y_vals),
                            color="steelblue", linewidth=1)
                elif cfg["type"] == "real_time_line_graph_average" and self._x_vals:
                    ax.plot(list(self._x_vals), list(self._avg_vals),
                            color="darkorange", linewidth=1.5)

            if not self._running:
                ani.event_source.stop()
        ani = FuncAnimation(fig, _update, interval=300, cache_frame_data=False)
        try:
            plt.show()
        except Exception as e:
            print(f"[Dashboard] GUI error: {e}")