import os
import random
import re
import sys
import tkinter as tk
from tkinter import messagebox


PARAMETERS = [
    "ai_planes_count",
    "lead_plane_count_allied",
    "escort_plane_count_allied",
    "lead_plane_count_axis",
    "escort_plane_count_axis",
]

SLIDER_MIN = 0
SLIDER_MAX = 12
PARAMETER_COLORS = {
    "ai_planes_count": "green",
    "lead_plane_count_allied": "red",
    "escort_plane_count_allied": "red",
    "lead_plane_count_axis": "blue",
    "escort_plane_count_axis": "blue",
}


def get_base_directory():
    """Return the folder that contains the script or bundled executable."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def get_config_path():
    """Build the config.ini path from the local script/exe folder."""
    return os.path.join(get_base_directory(), "config.ini")


def generate_random_values(range_vars):
    """Generate one random value per parameter using the active min/max range."""
    return {
        parameter: random.randint(min_var.get(), max_var.get())
        for parameter, (min_var, max_var) in range_vars.items()
    }


def read_config_values(config_path):
    """Read current numeric values for any supported parameters found in config.ini."""
    with open(config_path, "r", encoding="utf-8") as config_file:
        content = config_file.read()

    values = {}
    for parameter in PARAMETERS:
        pattern = re.compile(
            rf"^\s*{re.escape(parameter)}\s*=\s*(-?\d+)\s*(?:[;#].*)?$",
            re.MULTILINE,
        )
        match = pattern.search(content)
        if match:
            values[parameter] = int(match.group(1))

    return values


def update_config_file(config_path, values):
    """
    Replace only the numeric values for supported keys while preserving
    surrounding formatting and unrelated lines.
    """
    with open(config_path, "r", encoding="utf-8") as config_file:
        content = config_file.read()

    changed_parameters = []
    skipped_parameters = []

    for parameter, new_value in values.items():
        pattern = re.compile(
            rf"^(\s*{re.escape(parameter)}\s*=\s*)(-?\d+)(\s*(?:[;#].*)?)$",
            re.MULTILINE,
        )

        def replace_match(match):
            changed_parameters.append(parameter)
            return f"{match.group(1)}{new_value}{match.group(3)}"

        updated_content, replacements = pattern.subn(replace_match, content, count=1)
        if replacements == 0:
            skipped_parameters.append(parameter)
        else:
            content = updated_content

    if changed_parameters:
        with open(config_path, "w", encoding="utf-8") as config_file:
            config_file.write(content)

    return changed_parameters, skipped_parameters


def sync_range(low_var, high_var, changed_bound):
    """Keep each parameter range valid while the user moves the sliders."""
    low_value = low_var.get()
    high_value = high_var.get()

    if changed_bound == "min" and low_value > high_value:
        high_var.set(low_value)
    elif changed_bound == "max" and high_value < low_value:
        low_var.set(high_value)


def refresh_value_labels(display_mode_var, value_labels):
    """Show or hide the current config values beside each parameter row."""
    config_path = get_config_path()

    if not os.path.isfile(config_path):
        for value_label in value_labels.values():
            value_label.config(text="")
        return

    try:
        config_values = read_config_values(config_path)
    except OSError as error:
        for value_label in value_labels.values():
            value_label.config(text="")
        messagebox.showerror("Error", f"Failed to read config.ini: {error}")
        return

    if display_mode_var.get() == "show":
        for parameter, value_label in value_labels.items():
            if parameter in config_values:
                value_label.config(text=f"Current: {config_values[parameter]}")
            else:
                value_label.config(text="Not found")
    else:
        for value_label in value_labels.values():
            value_label.config(text="")


def build_update_summary(changed_parameters, skipped_parameters):
    """Create a concise result message without exposing generated values."""
    summary_lines = []

    if changed_parameters:
        changed_list = ", ".join(changed_parameters)
        summary_lines.append(f"Updated: {changed_list}")
    else:
        summary_lines.append("Updated: none")

    if skipped_parameters:
        skipped_list = ", ".join(skipped_parameters)
        summary_lines.append(f"Skipped (not found): {skipped_list}")
    else:
        summary_lines.append("Skipped (not found): none")

    return "\n".join(summary_lines)


def handle_generate_and_update(range_vars, display_mode_var, value_labels):
    """Generate hidden random values and write them into config.ini."""
    config_path = get_config_path()

    if not os.path.isfile(config_path):
        messagebox.showerror("Error", "config.ini was not found in the application folder.")
        return

    try:
        values = generate_random_values(range_vars)
        changed_parameters, skipped_parameters = update_config_file(config_path, values)
        refresh_value_labels(display_mode_var, value_labels)
    except OSError as error:
        messagebox.showerror("Error", f"Failed to update config.ini: {error}")
    else:
        summary_message = build_update_summary(changed_parameters, skipped_parameters)
        messagebox.showinfo("Success", summary_message)


def create_tick_marks(parent, scale_widget):
    """Draw simple tick marks under a slider using the slider's real coordinates."""
    tick_canvas = tk.Canvas(parent, height=10, highlightthickness=0, bd=0)
    tick_canvas.configure(bg=parent.cget("bg"))

    def redraw_ticks(_event=None):
        scale_widget.update_idletasks()
        canvas_width = max(scale_widget.winfo_width(), 1)
        tick_canvas.config(width=canvas_width)
        tick_canvas.delete("tick")

        for value in range(SLIDER_MIN, SLIDER_MAX + 1):
            x_position, _y_position = scale_widget.coords(value)
            tick_canvas.create_line(x_position, 2, x_position, 8, fill="black", tags="tick")

    scale_widget.bind("<Configure>", redraw_ticks)
    tick_canvas.bind("<Configure>", redraw_ticks)
    tick_canvas.after_idle(redraw_ticks)
    return tick_canvas


def create_parameter_row(parent, row_index, parameter_name, range_vars, value_labels):
    """Create one compact row with a label and paired min/max sliders."""
    label = tk.Label(
        parent,
        text=parameter_name,
        anchor="w",
        width=26,
        fg=PARAMETER_COLORS.get(parameter_name, "black"),
    )
    label.grid(row=row_index, column=0, padx=(0, 10), pady=6, sticky="w")

    min_value = tk.IntVar(value=SLIDER_MIN)
    max_value = tk.IntVar(value=SLIDER_MAX)
    range_vars[parameter_name] = (min_value, max_value)

    min_label = tk.Label(parent, text="Min")
    min_label.grid(row=row_index, column=1, padx=(0, 4), sticky="e")

    min_frame = tk.Frame(parent)
    min_frame.grid(row=row_index, column=2, padx=(0, 12), sticky="w")

    min_scale = tk.Scale(
        min_frame,
        from_=SLIDER_MIN,
        to=SLIDER_MAX,
        orient=tk.HORIZONTAL,
        resolution=1,
        showvalue=True,
        variable=min_value,
        length=180,
        command=lambda _value, low=min_value, high=max_value: sync_range(low, high, "min"),
    )
    min_scale.pack(anchor="w")

    min_ticks = create_tick_marks(min_frame, min_scale)
    min_ticks.pack(anchor="w")

    max_label = tk.Label(parent, text="Max")
    max_label.grid(row=row_index, column=3, padx=(0, 4), sticky="e")

    max_frame = tk.Frame(parent)
    max_frame.grid(row=row_index, column=4, sticky="w")

    max_scale = tk.Scale(
        max_frame,
        from_=SLIDER_MIN,
        to=SLIDER_MAX,
        orient=tk.HORIZONTAL,
        resolution=1,
        showvalue=True,
        variable=max_value,
        length=180,
        command=lambda _value, low=min_value, high=max_value: sync_range(low, high, "max"),
    )
    max_scale.pack(anchor="w")

    max_ticks = create_tick_marks(max_frame, max_scale)
    max_ticks.pack(anchor="w")

    value_label = tk.Label(parent, text="", anchor="w", width=12)
    value_label.grid(row=row_index, column=5, padx=(12, 0), sticky="w")
    value_labels[parameter_name] = value_label


def create_gui():
    """Build and start the Tkinter user interface."""
    root = tk.Tk()
    root.title("Mission Config Editor")
    root.resizable(False, False)

    container = tk.Frame(root, padx=14, pady=14)
    container.pack(fill="both", expand=True)

    header = tk.Label(container, text="Set min/max ranges for mission values")
    header.grid(row=0, column=0, columnspan=6, pady=(0, 10), sticky="w")

    display_mode_var = tk.StringVar(value="hide")
    radio_frame = tk.Frame(container)
    radio_frame.grid(row=1, column=0, columnspan=6, pady=(0, 10), sticky="w")

    range_vars = {}
    value_labels = {}

    show_button = tk.Radiobutton(
        radio_frame,
        text="Show generated values",
        variable=display_mode_var,
        value="show",
        command=lambda: refresh_value_labels(display_mode_var, value_labels),
    )
    show_button.pack(side="left", padx=(0, 12))

    hide_button = tk.Radiobutton(
        radio_frame,
        text="Hide generated values",
        variable=display_mode_var,
        value="hide",
        command=lambda: refresh_value_labels(display_mode_var, value_labels),
    )
    hide_button.pack(side="left")

    for row_offset, parameter in enumerate(PARAMETERS, start=2):
        create_parameter_row(container, row_offset, parameter, range_vars, value_labels)

    update_button = tk.Button(
        container,
        text="Generate and Update",
        width=20,
        command=lambda: handle_generate_and_update(range_vars, display_mode_var, value_labels),
    )
    update_button.grid(row=len(PARAMETERS) + 2, column=0, columnspan=6, pady=(12, 0))

    refresh_value_labels(display_mode_var, value_labels)

    return root


def main():
    app = create_gui()
    app.mainloop()


if __name__ == "__main__":
    main()
