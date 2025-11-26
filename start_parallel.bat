@echo off
REM UTF-8 aktivieren
chcp 65001 >nul

REM --- KONFIGURATION ---

REM Pfad zur Blender EXE
SET "BLENDER_EXE=C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"

REM Pfad zum Projekt-Ordner (Wo die .blend und das Skript liegen)
SET "PROJECT_DIR=C:\Users\Tim\OneDrive - TH Köln\03_Hochschule\7_Semester\Bachelorarbeit\source\blender-dart-dataset-generator"

REM Name der Blend-Datei und des Skripts
SET "BLEND_FILE=dev_scene.blend"
SET "PYTHON_SCRIPT=randomization_test.py"

REM --- ENDE KONFIGURATION ---


REM In das Verzeichnis wechseln (wichtig für relative Pfade im Python Skript)
cd /d "%PROJECT_DIR%"

REM Start der 4 Instanzen
REM Wir nutzen 'cmd /k call "..."', damit CMD die Pfade mit Leerzeichen versteht.

echo Starte Render-Instanz 1...
start "Blender Render 1" cmd /k call "%BLENDER_EXE%" -b "%BLEND_FILE%" -P "%PYTHON_SCRIPT%" -a

echo Starte Render-Instanz 2...
start "Blender Render 2" cmd /k call "%BLENDER_EXE%" -b "%BLEND_FILE%" -P "%PYTHON_SCRIPT%" -a

echo Starte Render-Instanz 3...
start "Blender Render 3" cmd /k call "%BLENDER_EXE%" -b "%BLEND_FILE%" -P "%PYTHON_SCRIPT%" -a

echo Starte Render-Instanz 4...
start "Blender Render 4" cmd /k call "%BLENDER_EXE%" -b "%BLEND_FILE%" -P "%PYTHON_SCRIPT%" -a

echo Starte Render-Instanz 5...
start "Blender Render 5" cmd /k call "%BLENDER_EXE%" -b "%BLEND_FILE%" -P "%PYTHON_SCRIPT%" -a

echo Starte Render-Instanz 6...
start "Blender Render 6" cmd /k call "%BLENDER_EXE%" -b "%BLEND_FILE%" -P "%PYTHON_SCRIPT%" -a

echo.
echo Alle Instanzen gestartet. Dieses Fenster kann geschlossen werden, die anderen arbeiten weiter.
pause