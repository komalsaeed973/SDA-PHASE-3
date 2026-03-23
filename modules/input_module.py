"""
Module name:
modules/input_module.py
The main purpose of this module is that it acts as 
"Data Ingestion Layer" of the Pipeline

It is responsible for 
a- Reading CSV file data 
b- Maps CSV columns to internal schema 
c. Cast values to data types 
d. sending processed packets to multiprocessing queue
"""
import csv
import time
import multiprocessing
from typing import Any


# here I am mapping string type names to python casting functions 
_CASTERS = {
    "string":  str,
    "integer": int,
    "float":   float,
    "bool":    lambda v: v.strip().lower() in ("true", "1", "yes"),
}

# here cast string value to required data type 
# it takes two paramters 1- value which is raw string from csv
#datatype-> the one I defined in config
# it returns a casted value 

def _cast(value: str, data_type: str) -> Any:
    caster = _CASTERS.get(data_type.lower(), str)
    return caster(value)

# this one reads input data from csv and transforms it using schema mappping
# and then it pushes it into raw queue for futher processing 

class InputModule:

    def __init__(self, config: dict, raw_queue):
        self._dataset_path = config["dataset_path"]
        self._delay        = config["pipeline_dynamics"]["input_delay_seconds"]
        self._schema       = config["schema_mapping"]["columns"]
        self._raw_queue    = raw_queue
        self._num_workers  = config["pipeline_dynamics"]["core_parallelism"]

# here data path is path to csv file 
# pipeline_dynamics.input_delay_seconds is the delay between packets
# schema_mapping.columns is the column mapping + data types
# pipeline_dynamics.core_parallelism: number of worker processes

    def run(self):
        print("[Input] Starting ...")
        rows_sent = 0
#open 
        with open(self._dataset_path, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            #process each row
            for raw_row in reader:
                packet = self._map_row(raw_row)
                #strip invalid 
                if packet is None:
                    continue
                #push processed to queue
                self._raw_queue.put(packet)
                rows_sent += 1
                #stimulating delay
                time.sleep(self._delay)

#this tells worker no more data coming
        for _ in range(self._num_workers):
            self._raw_queue.put(None)

        print(f"[Input] Done — {rows_sent} packets sent.")

# this one reads csv row by row
# maps and casts each row
# pushes valid packets intp queue
# sends termination signals after it is finished 


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

    #map row validates the required columns existence 
    #cast each to required type and then rename fields 
    #it returns packet if valid and none if invalid 