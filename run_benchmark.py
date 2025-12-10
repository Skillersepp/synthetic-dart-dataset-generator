import subprocess
import time
import os
import sys

# --- KONFIGURATION ---

# Anzahl der parallelen Blender-Instanzen
NUM_INSTANCES = 4

# Pfade (Nutze r"..." Strings für Windows-Pfade, damit Backslashes kein Problem sind)
BLENDER_EXE = r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"
PROJECT_DIR = r"C:\Users\Tim\OneDrive - TH Köln\03_Hochschule\7_Semester\Bachelorarbeit\source\blender-dart-dataset-generator"
BLEND_FILE = "dev_scene.blend"
PYTHON_SCRIPT = "randomization_test.py"

# --- ENDE KONFIGURATION ---

def main():
    # Prüfen, ob der Projektordner existiert
    if not os.path.exists(PROJECT_DIR):
        print(f"FEHLER: Projektordner nicht gefunden: {PROJECT_DIR}")
        return

    # Der Befehl als Liste (Subprocess mag Listen lieber als lange Strings mit Leerzeichen)
    # Entspricht: blender.exe -b datei.blend -P skript.py -a
    command = [
        BLENDER_EXE,
        "-b", BLEND_FILE,
        "-P", PYTHON_SCRIPT,
        "-a"
    ]

    print(f"--- Starte Benchmark mit {NUM_INSTANCES} Instanzen ---")
    print(f"Projekt: {PROJECT_DIR}")
    print("Drücke STRG+C, um abzubrechen (es dauert einen Moment, bis alle Prozesse stoppen).")
    print("-" * 60)

    # Zeitmessung starten
    start_time = time.perf_counter()
    
    processes = []

    try:
        # 1. Alle Prozesse starten (asynchron)
        for i in range(NUM_INSTANCES):
            print(f"Starte Instanz {i+1} von {NUM_INSTANCES}...")
            
            # Popen startet den Prozess im Hintergrund.
            # cwd=PROJECT_DIR sorgt dafür, dass Blender im richtigen Ordner startet.
            # stdout=subprocess.DEVNULL würde die Ausgabe unterdrücken (weniger Chaos),
            # aber du willst evtl. sehen, ob Fehler passieren.
            p = subprocess.Popen(command, cwd=PROJECT_DIR)
            processes.append(p)

        print("-" * 60)
        print("Alle Instanzen laufen. Warte auf Fertigstellung...")

        # 2. Warten, bis alle Prozesse beendet sind
        for p in processes:
            p.wait()

    except KeyboardInterrupt:
        print("\n\nAbbruch durch Benutzer! Beende Blender-Prozesse...")
        for p in processes:
            p.kill() # Erzwingt das Beenden
        sys.exit(0)

    # Zeitmessung stoppen
    end_time = time.perf_counter()
    duration = end_time - start_time

    print("-" * 60)
    print(f"FERTIG!")
    print(f"Gesamtdauer: {duration:.2f} Sekunden")
    print("-" * 60)

if __name__ == "__main__":
    main()