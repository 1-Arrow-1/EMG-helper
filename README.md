# EMG Helper

Small standalone helper tool for Vander's EMG Mission Generator for IL-2 Sturmovik Great Battles.

This prototype provides a simple Tkinter GUI to define min/max ranges for selected `config.ini` parameters and then write randomized values back into the local `config.ini` file.

## What It Does

The tool supports these EMG parameters:

- `ai_planes_count`
- `lead_plane_count_allied`
- `escort_plane_count_allied`
- `lead_plane_count_axis`
- `escort_plane_count_axis`

For each parameter, the GUI provides:

- one `Min` slider
- one `Max` slider
- automatic range validation so `Min` cannot exceed `Max`
- optional display of the currently stored value from `config.ini`

When `Generate and Update` is clicked, the tool:

1. generates one random integer for each supported parameter
2. uses the selected inclusive min/max range
3. updates only those values in the local `config.ini`
4. preserves the rest of the file as much as possible

## Current UI Behavior

- Window title: `Mission Config Editor`
- `ai_planes_count` is shown in green
- allied lead/escort rows are shown in red
- axis lead/escort rows are shown in blue
- allied rows are grouped together
- axis rows are grouped together
- each slider has visual tick marks
- generated values are hidden by default
- the radio buttons can show or hide the current values stored in `config.ini`

Important:

- the tool works with the `config.ini` in the same folder as the script or built `.exe`
- there is no file picker on purpose
- the random values are not previewed before writing

## Files

- `emg_config_editor.py`: main application
- `config.ini`: local EMG configuration file that gets updated

## Requirements

- Python 3
- Tkinter available in the Python installation

No external Python packages are required to run the script.

## Run From Source

From the project folder:

```powershell
py emg_config_editor.py
```

If `py` is not available on the machine, use your local Python executable instead:

```powershell
python emg_config_editor.py
```

## How It Works

The application resolves its working folder with:

```python
os.path.dirname(os.path.abspath(__file__))
```

When bundled as an executable, it switches to the executable folder via `sys.executable`, so the same "local folder" behavior still applies after packaging.

The config update logic:

- reads the file as plain text
- uses regular expressions to find the five supported keys
- replaces only the numeric value on matching lines
- keeps whitespace and trailing comments intact where possible

## Error Handling

The prototype shows a message box if:

- `config.ini` is missing
- one of the supported parameters is missing from `config.ini`
- the file cannot be read
- the file cannot be written

## Packaging With PyInstaller

To build a single Windows executable:

1. install PyInstaller
2. build the app as a windowed one-file executable

```powershell
pip install pyinstaller
pyinstaller --onefile --windowed emg_config_editor.py
```

The generated executable will be placed in the `dist` folder.

To use it correctly:

- copy `config.ini` next to the generated `.exe`
- run the `.exe` from that folder

Because the tool always looks for `config.ini` beside the script/executable, both files must stay together.

## Prototype Notes

This is intentionally a small first prototype:

- single-file Python app
- simple Tkinter layout
- no dependency on EMG internals beyond the supported `config.ini` keys
- suitable for later extension and packaging

Possible future improvements:

- save/load presets for slider ranges
- support more EMG parameters
- remember last-used ranges between launches
- improve styling and spacing for packaged desktop use
