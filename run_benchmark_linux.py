import subprocess
import time
import os
import sys

# --- KONFIGURATION ---
NUM_INSTANCES = 6
PROJECT_DIR = r"/home/student/Schreibtisch/synthetic-dart-dataset-generator"
BLEND_FILE = "dev_scene.blend"
PYTHON_SCRIPT = "randomization_test.py"

# EIN gemeinsamer Ordner für alle
#OUTPUT_DIR = r"/home/student/Schreibtisch/synthetic-dart-dataset-generator/output/dataset_v1/images"
# --- ENDE KONFIGURATION ---

def main():
    if not os.path.exists(PROJECT_DIR):
        print(f"FEHLER: Projektordner nicht gefunden: {PROJECT_DIR}")
        return

    # Gemeinsamen Ordner erstellen
    #if not os.path.exists(OUTPUT_DIR):
    #    os.makedirs(OUTPUT_DIR)

    # Der Pfad ist für ALLE Instanzen gleich
    # Blender ersetzt ###### durch die Frame-Nummer
    #shared_output_path = os.path.join(OUTPUT_DIR, "frame_######")

    # Der Befehl ist nun für alle gleich
    command = [
        "blender",
        "-b", BLEND_FILE,
        "-P", PYTHON_SCRIPT,
        #"-o", shared_output_path, # Alle schreiben hierhin
        "-a"
    ]

    print(f"--- Starte Benchmark mit {NUM_INSTANCES} Instanzen ---")
    #print(f"Ziel: {OUTPUT_DIR} (Shared Rendering)")
    print("-" * 60)

    processes = []

    try:
        for i in range(NUM_INSTANCES):
            print(f"Starte Instanz {i+1}...")
            # Alle Instanzen bekommen exakt denselben Befehl
            p = subprocess.Popen(command, cwd=PROJECT_DIR)
            processes.append(p)

        print("-" * 60)
        print("Warte auf Fertigstellung...")
        for p in processes:
            p.wait()

    except KeyboardInterrupt:
        print("\nAbbruch! Beende Prozesse...")
        for p in processes:
            p.kill()
        sys.exit(0)

if __name__ == "__main__":
    main()