import os
import random
import re
import sys
import tkinter as tk
from tkinter import messagebox, ttk


RANGE_PARAMETERS = [
    "ai_planes_count",
    "lead_plane_count_allied",
    "escort_plane_count_allied",
    "lead_plane_count_axis",
    "escort_plane_count_axis",
    "plane_altitude_allied",
    "plane_altitude_axis",
]
SINGLE_VALUE_PARAMETERS = []
MISSION_TIME_OPTIONS = [
    "dawn",
    "early morning",
    "late morning",
    "noon",
    "early afternoon",
    "late afternoon",
    "dusk",
    "midnight",
]
MISSION_CLOUD_OPTIONS = [
    "clear skies",
    "low clouds scattered",
    "low clouds dense",
    "low cloud cover",
    "cumulus scattered",
    "cumulus dense",
    "rain clouds",
    "thunderclouds",
    "high clouds",
    "high cloud cover",
    "cirrus clouds",
]
SEASONAL_MISSION_TIME_OPTIONS = {
    "winter": ["late morning", "noon", "early afternoon"],
    "summer": [
        "early morning",
        "late morning",
        "noon",
        "early afternoon",
        "late afternoon",
    ],
}
PARAMETER_SPECS = {
    "ai_planes_count": {"min": 0, "max": 24, "step": 1, "color_style": "Result.TLabel"},
    "lead_plane_count_allied": {"min": 0, "max": 12, "step": 1, "color_style": "Allied.TLabel"},
    "escort_plane_count_allied": {"min": 0, "max": 12, "step": 1, "color_style": "Allied.TLabel"},
    "lead_plane_count_axis": {"min": 0, "max": 12, "step": 1, "color_style": "Axis.TLabel"},
    "escort_plane_count_axis": {"min": 0, "max": 12, "step": 1, "color_style": "Axis.TLabel"},
    "plane_altitude_allied": {
        "min": 200,
        "max": 9000,
        "step": 100,
        "color_style": "Allied.TLabel",
    },
    "plane_altitude_axis": {
        "min": 200,
        "max": 9000,
        "step": 100,
        "color_style": "Axis.TLabel",
    },
}
EXCLUDED_RANDOM_VALUES = {
    "lead_plane_count_axis": {3},
    "escort_plane_count_axis": {3},
}
TOOLTIP_TEXTS = {
    "ai_planes_count": "Choose the min and max range for AI plane groups. Higher values can create much larger missions.",
    "lead_plane_count_allied": "Choose the min and max range for allied lead aircraft.",
    "escort_plane_count_allied": "Choose the min and max range for allied escort aircraft.",
    "plane_altitude_allied": "Choose the min and max altitude range for allied aircraft in metres.",
    "lead_plane_count_axis": "Choose the min and max range for axis lead aircraft. Value 3 is excluded automatically.",
    "escort_plane_count_axis": "Choose the min and max range for axis escort aircraft. Value 3 is excluded automatically.",
    "plane_altitude_axis": "Choose the min and max altitude range for axis aircraft in metres.",
    "mission_time": "Select one or more mission times. Click once to choose a single value. Use Ctrl+click to select multiple values. One of the selected entries will be used randomly, unless seasonal random is enabled.",
    "mission_cloud": "Select one or more cloud presets. Click once to choose a single value. Use Ctrl+click to select multiple values. One of the selected entries will be used randomly.",
    "seasonal_mission_time": "Uses the mission date from config.ini to determine the season automatically. Winter is 01.10 to 31.03. Summer is 01.04 to 30.09. Then one value is randomly selected from the matching subset. Winter: late morning, noon, early afternoon. Summer: early morning, late morning, noon, early afternoon, late afternoon.",
}


def get_base_directory():
    """Return the folder that contains the script or bundled executable."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def get_config_path():
    """Build the config.ini path from the local script/exe folder."""
    return os.path.join(get_base_directory(), "config.ini")


def read_config_entry(config_text, parameter):
    """Read a raw config value as text while ignoring trailing comments."""
    pattern = re.compile(
        rf"^\s*{re.escape(parameter)}\s*=\s*(.*?)\s*(?:[;#].*)?$",
        re.MULTILINE,
    )
    match = pattern.search(config_text)
    if not match:
        return None
    return match.group(1).strip()


def read_config_values(config_path):
    """Read current values for supported parameters found in config.ini."""
    with open(config_path, "r", encoding="utf-8") as config_file:
        content = config_file.read()

    values = {}
    for parameter in RANGE_PARAMETERS + SINGLE_VALUE_PARAMETERS:
        value_text = read_config_entry(content, parameter)
        if value_text is None:
            continue
        try:
            values[parameter] = int(value_text)
        except ValueError:
            continue

    for parameter in ("mission_time", "mission_cloud"):
        value_text = read_config_entry(content, parameter)
        if value_text is not None:
            values[parameter] = value_text

    return values


def update_config_file(config_path, values):
    """Replace supported config values while preserving unrelated lines."""
    with open(config_path, "r", encoding="utf-8") as config_file:
        content = config_file.read()

    changed_parameters = []
    skipped_parameters = []

    for parameter, new_value in values.items():
        pattern = re.compile(
            rf"^(\s*{re.escape(parameter)}\s*=\s*)(.*?)(\s*(?:[;#].*)?)$",
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


def generate_random_value(parameter, min_value, max_value):
    """Generate one random integer while respecting parameter-specific exclusions."""
    excluded_values = EXCLUDED_RANDOM_VALUES.get(parameter, set())
    allowed_values = [
        value for value in range(min_value, max_value + 1) if value not in excluded_values
    ]

    if not allowed_values:
        raise ValueError(
            f"No valid random values available for {parameter} in the selected range."
        )

    return random.choice(allowed_values)


def generate_random_values(range_vars):
    """Generate one random value per range-based parameter."""
    return {
        parameter: generate_random_value(parameter, min_var.get(), max_var.get())
        for parameter, (min_var, max_var) in range_vars.items()
    }


def generate_subset_random_value(selected_values, field_name):
    """Pick one random value from the user's selected subset."""
    if not selected_values:
        raise ValueError(f"Select at least one option for {field_name}.")
    return random.choice(selected_values)


def get_mission_time_season(config_path):
    """Determine whether the config date falls into the summer or winter rule set."""
    with open(config_path, "r", encoding="utf-8") as config_file:
        content = config_file.read()

    day_text = read_config_entry(content, "date_day")
    month_text = read_config_entry(content, "date_month")

    if day_text is None or month_text is None:
        raise ValueError("date_day or date_month not found in config.ini.")

    try:
        day = int(day_text)
        month = int(month_text)
    except ValueError as error:
        raise ValueError("date_day or date_month is not a valid integer.") from error

    if not 1 <= month <= 12:
        raise ValueError("date_month must be between 1 and 12.")
    if not 1 <= day <= 31:
        raise ValueError("date_day must be between 1 and 31.")

    if 4 <= month <= 9:
        return "summer"
    return "winter"


def generate_mission_time(config_path, selected_values, seasonal_mode):
    """Generate mission_time either from dropdown mode or seasonal random mode."""
    if seasonal_mode:
        season = get_mission_time_season(config_path)
        return random.choice(SEASONAL_MISSION_TIME_OPTIONS[season])
    return generate_subset_random_value(selected_values, "mission_time")


def meters_to_feet(meters):
    """Convert metres to rounded feet for display."""
    return round(meters * 3.28084)


def format_range_label(min_value, max_value):
    """Format a visible min/max indicator for range sliders."""
    return f"{min_value} - {max_value}"


def format_altitude_range_label(min_value, max_value):
    """Format an altitude range in metres and feet for display."""
    return (
        f"{min_value}-{max_value} m / "
        f"{meters_to_feet(min_value)}-{meters_to_feet(max_value)} ft"
    )


def snap_value(value, min_value, max_value, step):
    """Snap a scale value to the configured integer step."""
    snapped = min_value + round((float(value) - min_value) / step) * step
    return max(min_value, min(max_value, int(snapped)))


def update_current_value_labels(display_mode_var, value_labels):
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


def resize_window_to_content(root):
    """Resize the window to the current content size."""
    root.update_idletasks()
    root.geometry("")


def build_update_summary(changed_parameters, skipped_parameters):
    """Create a concise result message without exposing generated values."""
    summary_lines = []

    if changed_parameters:
        summary_lines.append(f"Updated: {', '.join(changed_parameters)}")
    else:
        summary_lines.append("Updated: none")

    if skipped_parameters:
        summary_lines.append(f"Skipped (not found): {', '.join(skipped_parameters)}")
    else:
        summary_lines.append("Skipped (not found): none")

    return "\n".join(summary_lines)


def handle_generate_and_update(
    range_vars,
    mission_time_listbox,
    mission_cloud_listbox,
    seasonal_mission_time_var,
    display_mode_var,
    value_labels,
    root,
):
    """Generate hidden random values and write them into config.ini."""
    config_path = get_config_path()

    if not os.path.isfile(config_path):
        messagebox.showerror("Error", "config.ini was not found in the application folder.")
        return

    try:
        values = generate_random_values(range_vars)
        values["mission_time"] = generate_mission_time(
            config_path,
            get_listbox_selected_values(mission_time_listbox),
            seasonal_mission_time_var.get(),
        )
        values["mission_cloud"] = generate_subset_random_value(
            get_listbox_selected_values(mission_cloud_listbox),
            "mission_cloud",
        )
        changed_parameters, skipped_parameters = update_config_file(config_path, values)
        update_current_value_labels(display_mode_var, value_labels)
        resize_window_to_content(root)
    except ValueError as error:
        messagebox.showerror("Error", str(error))
    except OSError as error:
        messagebox.showerror("Error", f"Failed to update config.ini: {error}")
    else:
        messagebox.showinfo("Success", build_update_summary(changed_parameters, skipped_parameters))


def create_styles(root):
    """Configure ttk styles for a cleaner Windows-friendly UI."""
    style = ttk.Style(root)
    available_themes = style.theme_names()
    if "vista" in available_themes:
        style.theme_use("vista")
    elif "clam" in available_themes:
        style.theme_use("clam")

    style.configure("Card.TLabelframe", padding=12)
    style.configure("Card.TLabelframe.Label", font=("Segoe UI", 10, "bold"))
    style.configure("Allied.TLabel", foreground="#b42318")
    style.configure("Axis.TLabel", foreground="#175cd3")
    style.configure("Result.TLabel", foreground="#027a48")
    style.configure("Muted.TLabel", foreground="#475467")
    style.configure("Value.TLabel", font=("Segoe UI", 9, "bold"))
    style.configure("Primary.TButton", padding=(14, 8))
    style.configure("Help.TLabel", foreground="#667085")
    style.configure("ValueBox.TFrame", relief="solid", borderwidth=1)


def create_value_box(parent, row_index, value_labels, parameter_name):
    """Create a framed area for the current config value display."""
    value_frame = ttk.Frame(parent, style="ValueBox.TFrame", padding=(8, 4))
    value_frame.grid(row=row_index, column=4, sticky="w")

    value_label = ttk.Label(value_frame, text="", style="Muted.TLabel", width=22)
    value_label.grid(row=0, column=0, sticky="w")
    value_labels[parameter_name] = value_label


def create_labeled_section(parent, title, row):
    """Create a grouped section with consistent spacing."""
    section = ttk.LabelFrame(parent, text=title, style="Card.TLabelframe")
    section.grid(row=row, column=0, sticky="ew", pady=(0, 12))
    section.grid_columnconfigure(1, weight=1)
    section.grid_columnconfigure(2, weight=1)
    section.grid_columnconfigure(3, minsize=160)
    return section


class ToolTip:
    """Simple hover tooltip for small help labels."""

    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, _event=None):
        if self.tooltip_window or not self.text:
            return

        x_position = self.widget.winfo_rootx() + 18
        y_position = self.widget.winfo_rooty() + 20

        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x_position}+{y_position}")

        tooltip_label = tk.Label(
            self.tooltip_window,
            text=self.text,
            justify="left",
            bg="#fff8db",
            fg="#101828",
            relief="solid",
            bd=1,
            padx=8,
            pady=5,
            wraplength=280,
        )
        tooltip_label.pack()

    def hide(self, _event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None


def create_parameter_heading(parent, row_index, text, style_name, tooltip_text, sticky="w"):
    """Create a label plus a compact hover help control."""
    heading_frame = ttk.Frame(parent)
    heading_frame.grid(row=row_index, column=0, sticky=sticky, padx=(0, 10), pady=6)

    ttk.Label(
        heading_frame,
        text=text,
        style=style_name,
        width=26,
    ).grid(row=0, column=0, sticky="w")

    help_label = ttk.Label(heading_frame, text="[?]", style="Help.TLabel", cursor="question_arrow")
    help_label.grid(row=0, column=1, sticky="w", padx=(4, 0))
    ToolTip(help_label, tooltip_text)


def create_range_row(parent, row_index, parameter_name, range_vars, value_labels):
    """Create a ttk-based min/max slider row with live range labels."""
    spec = PARAMETER_SPECS[parameter_name]
    min_var = tk.IntVar(value=spec["min"])
    max_var = tk.IntVar(value=spec["max"])
    range_vars[parameter_name] = (min_var, max_var)

    create_parameter_heading(
        parent,
        row_index,
        parameter_name,
        spec["color_style"],
        TOOLTIP_TEXTS[parameter_name],
    )

    slider_frame = ttk.Frame(parent)
    slider_frame.grid(row=row_index, column=1, columnspan=2, sticky="ew")
    slider_frame.grid_columnconfigure(0, weight=1)
    slider_frame.grid_columnconfigure(1, weight=1)

    min_header = ttk.Label(slider_frame, text="Min", style="Muted.TLabel")
    min_header.grid(row=0, column=0, sticky="w")
    max_header = ttk.Label(slider_frame, text="Max", style="Muted.TLabel")
    max_header.grid(row=0, column=1, sticky="e")

    min_value_label = ttk.Label(slider_frame, text=str(min_var.get()), style="Value.TLabel", width=4)
    min_value_label.grid(row=1, column=0, sticky="w")
    max_value_label = ttk.Label(slider_frame, text=str(max_var.get()), style="Value.TLabel", width=4)
    max_value_label.grid(row=1, column=1, sticky="e")

    min_scale = ttk.Scale(
        slider_frame,
        from_=spec["min"],
        to=spec["max"],
    )
    min_scale.grid(row=2, column=0, sticky="ew", padx=(0, 8))

    max_scale = ttk.Scale(
        slider_frame,
        from_=spec["min"],
        to=spec["max"],
    )
    max_scale.grid(row=2, column=1, sticky="ew", padx=(8, 0))

    formatter = (
        format_altitude_range_label
        if parameter_name in {"plane_altitude_allied", "plane_altitude_axis"}
        else format_range_label
    )

    range_label = ttk.Label(parent, text=formatter(min_var.get(), max_var.get()), style="Value.TLabel")
    range_label.grid(row=row_index, column=3, sticky="w", padx=(10, 10))

    create_value_box(parent, row_index, value_labels, parameter_name)
    is_adjusting = {"value": False}

    def refresh_labels():
        min_value_label.config(text=str(min_var.get()))
        max_value_label.config(text=str(max_var.get()))
        range_label.config(text=formatter(min_var.get(), max_var.get()))

    def on_min_change(raw_value):
        if is_adjusting["value"]:
            return
        snapped = snap_value(raw_value, spec["min"], spec["max"], spec["step"])
        is_adjusting["value"] = True
        try:
            if snapped > max_var.get():
                max_var.set(snapped)
                max_scale.set(snapped)
            min_var.set(snapped)
            min_scale.set(snapped)
            refresh_labels()
        finally:
            is_adjusting["value"] = False

    def on_max_change(raw_value):
        if is_adjusting["value"]:
            return
        snapped = snap_value(raw_value, spec["min"], spec["max"], spec["step"])
        is_adjusting["value"] = True
        try:
            if snapped < min_var.get():
                min_var.set(snapped)
                min_scale.set(snapped)
            max_var.set(snapped)
            max_scale.set(snapped)
            refresh_labels()
        finally:
            is_adjusting["value"] = False

    min_scale.configure(command=on_min_change)
    max_scale.configure(command=on_max_change)
    min_scale.set(min_var.get())
    max_scale.set(max_var.get())


def get_listbox_selected_values(listbox):
    """Return selected listbox values in display order."""
    return [
        listbox.get(index)
        for index in range(listbox.size())
        if listbox.selection_includes(index)
    ]


def bind_listbox_selection_behavior(listbox):
    """Make normal click exclusive and Ctrl+click additive for listboxes."""

    def on_click(event):
        clicked_index = listbox.nearest(event.y)
        if clicked_index < 0:
            return "break"

        is_ctrl_click = bool(event.state & 0x0004)
        if is_ctrl_click:
            if listbox.selection_includes(clicked_index):
                listbox.selection_clear(clicked_index)
            else:
                listbox.selection_set(clicked_index)
            listbox.activate(clicked_index)
            return "break"

        listbox.selection_clear(0, tk.END)
        listbox.selection_set(clicked_index)
        listbox.activate(clicked_index)
        return "break"

    listbox.bind("<Button-1>", on_click)


def update_mission_time_mode(seasonal_var, mission_time_listbox):
    """Enable or disable mission_time subset selection based on seasonal mode."""
    state = "disabled" if seasonal_var.get() else "normal"
    mission_time_listbox.configure(state=state)


def create_mission_time_row(parent, row_index, value_labels):
    """Create the mission_time controls with subset selection and seasonal toggle."""
    create_parameter_heading(
        parent,
        row_index,
        "mission_time",
        "TLabel",
        TOOLTIP_TEXTS["mission_time"],
        sticky="nw",
    )
    seasonal_var = tk.BooleanVar(value=False)

    mission_time_listbox = tk.Listbox(
        parent,
        selectmode=tk.MULTIPLE,
        exportselection=False,
        height=min(len(MISSION_TIME_OPTIONS), 6),
        width=22,
    )
    mission_time_listbox.grid(row=row_index, column=1, sticky="w")
    for option in MISSION_TIME_OPTIONS:
        mission_time_listbox.insert(tk.END, option)
    for index in range(mission_time_listbox.size()):
        mission_time_listbox.selection_set(index)
    bind_listbox_selection_behavior(mission_time_listbox)

    ttk.Checkbutton(
        parent,
        text="Use seasonal random",
        variable=seasonal_var,
        command=lambda: update_mission_time_mode(seasonal_var, mission_time_listbox),
    ).grid(row=row_index, column=2, sticky="w", padx=(10, 0))
    seasonal_help = ttk.Label(parent, text="[?]", style="Help.TLabel", cursor="question_arrow")
    seasonal_help.grid(row=row_index, column=3, sticky="w")
    ToolTip(seasonal_help, TOOLTIP_TEXTS["seasonal_mission_time"])

    create_value_box(parent, row_index, value_labels, "mission_time")

    return mission_time_listbox, seasonal_var


def create_mission_cloud_row(parent, row_index, value_labels):
    """Create the mission_cloud subset selection row."""
    create_parameter_heading(
        parent,
        row_index,
        "mission_cloud",
        "TLabel",
        TOOLTIP_TEXTS["mission_cloud"],
        sticky="nw",
    )

    mission_cloud_listbox = tk.Listbox(
        parent,
        selectmode=tk.MULTIPLE,
        exportselection=False,
        height=min(len(MISSION_CLOUD_OPTIONS), 6),
        width=22,
    )
    mission_cloud_listbox.grid(row=row_index, column=1, sticky="w")
    for option in MISSION_CLOUD_OPTIONS:
        mission_cloud_listbox.insert(tk.END, option)
    for index in range(mission_cloud_listbox.size()):
        mission_cloud_listbox.selection_set(index)
    bind_listbox_selection_behavior(mission_cloud_listbox)

    create_value_box(parent, row_index, value_labels, "mission_cloud")

    return mission_cloud_listbox


def create_gui():
    """Build and start the Tkinter user interface."""
    root = tk.Tk()
    root.title("EMG Avanced Random Settings Editor")
    root.resizable(True, False)
    root.minsize(1100, 0)
    create_styles(root)

    container = ttk.Frame(root, padding=(16, 16))
    container.grid(row=0, column=0, sticky="nsew")
    container.grid_columnconfigure(0, weight=1)
    root.grid_columnconfigure(0, weight=1)

    header = ttk.Label(
        container,
        text="Set mission ranges and randomization options",
        font=("Segoe UI", 12, "bold"),
    )
    header.grid(row=0, column=0, sticky="w", pady=(0, 6))

    subheader = ttk.Label(
        container,
        text="Generated values remain hidden unless the current config values are explicitly shown.",
        style="Muted.TLabel",
    )
    subheader.grid(row=1, column=0, sticky="w", pady=(0, 14))

    display_mode_var = tk.StringVar(value="hide")
    toggle_row = ttk.Frame(container)
    toggle_row.grid(row=2, column=0, sticky="w", pady=(0, 14))

    ttk.Radiobutton(
        toggle_row,
        text="Show current config values",
        variable=display_mode_var,
        value="show",
        command=lambda: (update_current_value_labels(display_mode_var, value_labels), resize_window_to_content(root)),
    ).grid(row=0, column=0, padx=(0, 14))

    ttk.Radiobutton(
        toggle_row,
        text="Hide current config values",
        variable=display_mode_var,
        value="hide",
        command=lambda: (update_current_value_labels(display_mode_var, value_labels), resize_window_to_content(root)),
    ).grid(row=0, column=1)

    range_vars = {}
    value_labels = {}

    general_section = create_labeled_section(container, "General", 3)
    create_range_row(general_section, 0, "ai_planes_count", range_vars, value_labels)

    allied_section = create_labeled_section(container, "Allied", 4)
    create_range_row(allied_section, 0, "lead_plane_count_allied", range_vars, value_labels)
    create_range_row(allied_section, 1, "escort_plane_count_allied", range_vars, value_labels)
    create_range_row(allied_section, 2, "plane_altitude_allied", range_vars, value_labels)

    axis_section = create_labeled_section(container, "Axis", 5)
    create_range_row(axis_section, 0, "lead_plane_count_axis", range_vars, value_labels)
    create_range_row(axis_section, 1, "escort_plane_count_axis", range_vars, value_labels)
    create_range_row(axis_section, 2, "plane_altitude_axis", range_vars, value_labels)

    environment_section = create_labeled_section(container, "Environment", 6)
    mission_time_listbox, seasonal_mission_time_var = create_mission_time_row(
        environment_section, 0, value_labels
    )
    mission_cloud_listbox = create_mission_cloud_row(environment_section, 1, value_labels)

    button_row = ttk.Frame(container)
    button_row.grid(row=7, column=0, sticky="ew", pady=(6, 0))
    button_row.grid_columnconfigure(0, weight=1)

    ttk.Button(
        button_row,
        text="Generate and Update",
        style="Primary.TButton",
        command=lambda: handle_generate_and_update(
            range_vars,
            mission_time_listbox,
            mission_cloud_listbox,
            seasonal_mission_time_var,
            display_mode_var,
            value_labels,
            root,
        ),
    ).grid(row=0, column=0, sticky="e")

    update_current_value_labels(display_mode_var, value_labels)
    resize_window_to_content(root)
    return root


def main():
    app = create_gui()
    app.mainloop()


if __name__ == "__main__":
    main()
