import json
import matplotlib.pyplot as plt
from datetime import datetime

def generate_delta_chart(log_path="hedge_log.json"):
    try:
        with open(log_path, "r") as f:
            data = json.load(f)
    except:
        return None

    times = []
    sizes = []

    for entry in data[-10:]:  # Show last 10 entries
        time = datetime.fromisoformat(entry["time"])
        times.append(time)
        sizes.append(entry["size"])

    if not times:
        return None

    plt.figure(figsize=(8, 4))
    plt.plot(times, sizes, marker="o", color="blue")
    plt.title("🔄 Hedge Sizes Over Time")
    plt.xlabel("Time")
    plt.ylabel("Size (Asset Units)")
    plt.grid(True)
    plt.tight_layout()

    path = "delta_chart.png"
    plt.savefig(path)
    plt.close()
    return path
