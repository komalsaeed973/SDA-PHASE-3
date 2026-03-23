import csv
import hashlib
import random
import os

SECRET_KEY = "sda_spring_2026_secure_key"
ITERATIONS = 100        # fast — matches config
NUM_ROWS   = 500


def make_signature(raw_value: float, secret_key: str, iterations: int) -> str:
    value_str = f"{raw_value:.2f}"
    password  = secret_key.encode("utf-8")
    salt      = value_str.encode("utf-8")
    sig = hashlib.pbkdf2_hmac("sha256", password, salt, iterations)
    return sig.hex()


def generate_dataset(path: str):
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Sensor_ID", "Timestamp", "Raw_Value", "Auth_Signature"])
        for i in range(NUM_ROWS):
            sensor_id = f"SENSOR_{random.randint(1, 10):03d}"
            timestamp = 1000 + i
            raw_value = round(random.uniform(15.0, 35.0), 2)
            if random.random() < 0.2:
                signature = "INVALID_SPOOFED"
            else:
                signature = make_signature(raw_value, SECRET_KEY, ITERATIONS)
            writer.writerow([sensor_id, timestamp, raw_value, signature])
    print(f"Done — {NUM_ROWS} rows written to {path}")


if __name__ == "__main__":
    generate_dataset("data/climate_data.csv")