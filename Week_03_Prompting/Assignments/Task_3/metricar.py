import csv
import json
import re
import sqlite3
from collections import Counter, defaultdict, deque
from pathlib import Path

prompt_frameworks = ["icio", "pact", "gkp"]

prompt_times = {
    "icio": 13.5,
    "pact": 6.2,
    "gkp": 7.5
}

prompt_accuracy = {
    "icio": 0.2774,
    "pact": 0.2774,
    "gkp": 0.1613
}

generated_sql_total_length = {
    "icio": 0,
    "pact": 0,
    "gkp": 0
}

generated_files = {
    "icio": "./Week_03_Prompting/Assignments/Task_3/icio.csv",
    "pact": "./Week_03_Prompting/Assignments/Task_3/pact.csv",
    "gkp": "./Week_03_Prompting/Assignments/Task_3/gkp.csv"
}

total = 0

for framework in prompt_frameworks:
    file_path = Path(generated_files[framework])
    source = open(file_path, "r", encoding="utf-8", newline="")
    for line_number, row in enumerate(csv.DictReader(source), start=2):
        query = row["predicted_sql"]
        generated_sql_total_length[framework] += len(query)
    source.close()

    print(f"Framework: {framework}")
    print(f"Total generated SQL length: {generated_sql_total_length[framework]}")
    print(f"Accuracy: {prompt_accuracy[framework]}")
    print(f"Total time: {prompt_times[framework]}")
    print(f"total rank: accuracy/(time*length) = {1000000 * prompt_accuracy[framework] / (prompt_times[framework] * generated_sql_total_length[framework])}")
    print()