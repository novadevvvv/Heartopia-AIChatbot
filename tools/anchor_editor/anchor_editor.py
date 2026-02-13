import argparse
import json
from pathlib import Path
import tkinter as tk
from tkinter import messagebox

from PIL import Image, ImageTk


STAGES = [
    ("panel_tl", "Click chat panel top-left"),
    ("panel_br", "Click chat panel bottom-right"),
    ("list_tl", "Click message-list top-left"),
    ("list_br", "Click message-list bottom-right"),
    ("left_lane", "Click approximate LEFT bubble lane center"),
    ("right_lane", "Click approximate RIGHT bubble lane center"),
    ("split_x", "Click side split line (left of this=LEFT, right of this=RIGHT)"),
]


class AnchorEditor:
    def __init__(self, images_dir: Path, image_path: Path | None, output_path: Path):
        self.images_dir = images_dir
        self.output_path = output_path
        self.image_files = self._discover_images(images_dir)
        if not self.image_files:
            raise FileNotFoundError(f"No PNG/JPG images found in: {images_dir}")

        self.image_path = self._resolve_initial_image(image_path)
        self.points: dict[str, tuple[int, int]] = {}
        self.stage_index = 0

        self.source_image: Image.Image | None = None
        self.source_w = 0
        self.source_h = 0
        self.scale = 1.0
        self.display_image: Image.Image | None = None
        self.tk_image = None

        self.root = tk.Tk()
        self.root.title("Anchor Editor")

        self.instructions = tk.StringVar()
        self.status = tk.StringVar()

        info = tk.Label(self.root, textvariable=self.instructions, anchor="w", font=("Segoe UI", 11, "bold"))
        info.pack(fill="x", padx=10, pady=(10, 4))

        hints = tk.Label(
            self.root,
            text="Left click: set point  |  Right click: undo  |  S: save  |  R: reset  |  Q: quit",
            anchor="w",
            font=("Segoe UI", 9),
        )
        hints.pack(fill="x", padx=10, pady=(0, 6))

        picker_row = tk.Frame(self.root)
        picker_row.pack(fill="x", padx=10, pady=(0, 6))
        tk.Label(picker_row, text="Screenshot:").pack(side="left")
        self.image_var = tk.StringVar()
        self.image_menu = tk.OptionMenu(picker_row, self.image_var, *[p.name for p in self.image_files], command=self._on_image_change)
        self.image_menu.pack(side="left", fill="x", expand=True, padx=(8, 8))
        tk.Button(picker_row, text="Reload", command=self._reload_current_image).pack(side="left")

        self.canvas = tk.Canvas(self.root, width=1200, height=700, bg="#111111", highlightthickness=0)
        self.canvas.pack(padx=10, pady=10)
        self.canvas_image_id = self.canvas.create_image(0, 0, anchor="nw")

        status = tk.Label(self.root, textvariable=self.status, anchor="w", font=("Segoe UI", 9))
        status.pack(fill="x", padx=10, pady=(0, 10))

        self.canvas.bind("<Button-1>", self.on_left_click)
        self.canvas.bind("<Button-3>", self.on_right_click)
        self.root.bind("<s>", lambda _: self.save())
        self.root.bind("<S>", lambda _: self.save())
        self.root.bind("<r>", lambda _: self.reset())
        self.root.bind("<R>", lambda _: self.reset())
        self.root.bind("<q>", lambda _: self.root.destroy())
        self.root.bind("<Q>", lambda _: self.root.destroy())

        self._load_image(self.image_path, reset_points=True, preserve_points=False)
        self._update_labels()

    @staticmethod
    def _discover_images(images_dir: Path) -> list[Path]:
        patterns = ("*.png", "*.jpg", "*.jpeg", "*.webp")
        files: list[Path] = []
        for pattern in patterns:
            files.extend(images_dir.glob(pattern))
        return sorted(files)

    def _resolve_initial_image(self, image_path: Path | None) -> Path:
        if image_path and image_path.exists():
            return image_path
        return self.image_files[0]

    def _compute_scale(self, width: int, height: int) -> float:
        max_w = 1400
        max_h = 900
        scale_w = max_w / width
        scale_h = max_h / height
        return min(1.0, scale_w, scale_h)

    def _points_to_normalized(self) -> dict[str, tuple[float, float]]:
        if self.source_w <= 1 or self.source_h <= 1:
            return {}
        normalized: dict[str, tuple[float, float]] = {}
        for key, (x, y) in self.points.items():
            nx = x / max(1, self.source_w - 1)
            ny = y / max(1, self.source_h - 1)
            normalized[key] = (max(0.0, min(1.0, nx)), max(0.0, min(1.0, ny)))
        return normalized

    def _normalized_to_points(self, normalized: dict[str, tuple[float, float]]) -> dict[str, tuple[int, int]]:
        restored: dict[str, tuple[int, int]] = {}
        for key, (nx, ny) in normalized.items():
            x = int(round(nx * max(1, self.source_w - 1)))
            y = int(round(ny * max(1, self.source_h - 1)))
            x = max(0, min(self.source_w - 1, x))
            y = max(0, min(self.source_h - 1, y))
            restored[key] = (x, y)
        return restored

    def _load_image(self, image_path: Path, reset_points: bool, preserve_points: bool) -> None:
        saved_points_norm = self._points_to_normalized() if preserve_points else {}
        self.image_path = image_path
        self.source_image = Image.open(image_path).convert("RGB")
        self.source_w, self.source_h = self.source_image.size
        self.scale = self._compute_scale(self.source_w, self.source_h)
        draw_w = int(self.source_w * self.scale)
        draw_h = int(self.source_h * self.scale)
        self.display_image = self.source_image.resize((draw_w, draw_h), Image.Resampling.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(self.display_image)
        self.canvas.config(width=draw_w, height=draw_h)
        self.canvas.itemconfig(self.canvas_image_id, image=self.tk_image)
        self.root.title(f"Anchor Editor - {image_path.name}")
        self.image_var.set(image_path.name)
        if reset_points:
            self.reset()
        elif preserve_points and saved_points_norm:
            self.points = self._normalized_to_points(saved_points_norm)
            self.stage_index = min(len(self.points), len(STAGES))
            self._draw_overlay()
            self._update_labels()
        else:
            self._draw_overlay()
            self._update_labels()

    def _on_image_change(self, selected_name: str) -> None:
        target = self.images_dir / selected_name
        if target == self.image_path:
            return
        self._load_image(target, reset_points=False, preserve_points=True)

    def _reload_current_image(self) -> None:
        self._load_image(self.image_path, reset_points=False, preserve_points=True)

    def _to_image_coords(self, x: int, y: int) -> tuple[int, int]:
        ix = int(round(x / self.scale))
        iy = int(round(y / self.scale))
        ix = max(0, min(ix, self.source_w - 1))
        iy = max(0, min(iy, self.source_h - 1))
        return ix, iy

    def _update_labels(self) -> None:
        if self.stage_index < len(STAGES):
            _, prompt = STAGES[self.stage_index]
            self.instructions.set(f"Step {self.stage_index + 1}/{len(STAGES)}: {prompt}")
        else:
            self.instructions.set("All points captured. Press S to save or R to reset.")
        self.status.set(
            f"Image: {self.image_path}  |  Resolution: {self.source_w}x{self.source_h}  |  Saved points: {len(self.points)}"
        )

    def _draw_overlay(self) -> None:
        if self.source_image is None:
            return
        self.canvas.delete("overlay")
        for key, (ix, iy) in self.points.items():
            dx = int(ix * self.scale)
            dy = int(iy * self.scale)
            self.canvas.create_oval(dx - 4, dy - 4, dx + 4, dy + 4, fill="#ffcc00", outline="#000000", tags="overlay")
            self.canvas.create_text(dx + 8, dy - 8, text=key, fill="#ffffff", anchor="w", tags="overlay")

        panel_tl = self.points.get("panel_tl")
        panel_br = self.points.get("panel_br")
        if panel_tl and panel_br:
            x1, y1 = int(panel_tl[0] * self.scale), int(panel_tl[1] * self.scale)
            x2, y2 = int(panel_br[0] * self.scale), int(panel_br[1] * self.scale)
            self.canvas.create_rectangle(x1, y1, x2, y2, outline="#00d0ff", width=2, tags="overlay")

        list_tl = self.points.get("list_tl")
        list_br = self.points.get("list_br")
        if list_tl and list_br:
            x1, y1 = int(list_tl[0] * self.scale), int(list_tl[1] * self.scale)
            x2, y2 = int(list_br[0] * self.scale), int(list_br[1] * self.scale)
            self.canvas.create_rectangle(x1, y1, x2, y2, outline="#00ff88", width=2, tags="overlay")

        left_lane = self.points.get("left_lane")
        if left_lane:
            x = int(left_lane[0] * self.scale)
            self.canvas.create_line(x, 0, x, int(self.source_h * self.scale), fill="#ff6f91", dash=(4, 2), tags="overlay")

        right_lane = self.points.get("right_lane")
        if right_lane:
            x = int(right_lane[0] * self.scale)
            self.canvas.create_line(x, 0, x, int(self.source_h * self.scale), fill="#ffd166", dash=(4, 2), tags="overlay")

        split_x = self.points.get("split_x")
        if split_x:
            x = int(split_x[0] * self.scale)
            self.canvas.create_line(x, 0, x, int(self.source_h * self.scale), fill="#b388ff", width=2, dash=(6, 3), tags="overlay")

    def on_left_click(self, event) -> None:
        if self.stage_index >= len(STAGES):
            return
        key, _ = STAGES[self.stage_index]
        self.points[key] = self._to_image_coords(event.x, event.y)
        self.stage_index += 1
        self._update_labels()
        self._draw_overlay()

    def on_right_click(self, _) -> None:
        if self.stage_index == 0:
            return
        self.stage_index -= 1
        key, _ = STAGES[self.stage_index]
        self.points.pop(key, None)
        self._update_labels()
        self._draw_overlay()

    def reset(self) -> None:
        self.points.clear()
        self.stage_index = 0
        self._update_labels()
        self._draw_overlay()

    def _build_profile(self) -> dict:
        required = {"panel_tl", "panel_br", "list_tl", "list_br"}
        missing = sorted(required - set(self.points.keys()))
        if missing:
            raise ValueError(f"Missing required points: {', '.join(missing)}")

        panel_tl = self.points["panel_tl"]
        panel_br = self.points["panel_br"]
        list_tl = self.points["list_tl"]
        list_br = self.points["list_br"]

        panel_x1, panel_y1 = min(panel_tl[0], panel_br[0]), min(panel_tl[1], panel_br[1])
        panel_x2, panel_y2 = max(panel_tl[0], panel_br[0]), max(panel_tl[1], panel_br[1])

        list_x1, list_y1 = min(list_tl[0], list_br[0]), min(list_tl[1], list_br[1])
        list_x2, list_y2 = max(list_tl[0], list_br[0]), max(list_tl[1], list_br[1])

        left_lane_x = self.points.get("left_lane", (list_x1 + (list_x2 - list_x1) // 4, 0))[0]
        right_lane_x = self.points.get("right_lane", (list_x1 + 3 * (list_x2 - list_x1) // 4, 0))[0]
        split_x = self.points.get("split_x", ((left_lane_x + right_lane_x) // 2, 0))[0]

        return {
            "resolution": {"width": self.source_w, "height": self.source_h},
            "panel": {
                "x": panel_x1,
                "y": panel_y1,
                "width": panel_x2 - panel_x1,
                "height": panel_y2 - panel_y1,
            },
            "message_list": {
                "x": list_x1,
                "y": list_y1,
                "width": list_x2 - list_x1,
                "height": list_y2 - list_y1,
            },
            "lanes": {
                "left_x": left_lane_x,
                "right_x": right_lane_x,
            },
            "classifier": {
                "split_x": split_x,
            },
            "source_image": str(self.image_path),
        }

    def save(self) -> None:
        try:
            profile = self._build_profile()
        except ValueError as exc:
            messagebox.showerror("Cannot save", str(exc))
            return

        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        data = {"profiles": {}}
        if self.output_path.exists():
            try:
                data = json.loads(self.output_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                messagebox.showerror("Cannot save", f"Invalid JSON in {self.output_path}")
                return
            if not isinstance(data, dict):
                data = {"profiles": {}}
            if "profiles" not in data or not isinstance(data["profiles"], dict):
                data["profiles"] = {}

        key = f"{self.source_w}x{self.source_h}"
        data["profiles"][key] = profile
        self.output_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        messagebox.showinfo("Saved", f"Saved anchors for {key} to:\n{self.output_path}")

    def run(self) -> None:
        self._draw_overlay()
        self.root.mainloop()


def main() -> None:
    parser = argparse.ArgumentParser(description="Manual anchor editor for Heartopia screenshot preprocessing.")
    parser.add_argument("--image", help="Path to initial screenshot image.")
    parser.add_argument(
        "--dir",
        default="tests/fixtures/screenshots",
        help="Directory to pick screenshots from.",
    )
    parser.add_argument(
        "--output",
        default="tools/anchor_editor/anchors.json",
        help="Path to anchors JSON output.",
    )
    args = parser.parse_args()

    image_path = Path(args.image).resolve() if args.image else None
    images_dir = Path(args.dir).resolve()
    output_path = Path(args.output).resolve()

    if not images_dir.exists():
        raise FileNotFoundError(f"Directory not found: {images_dir}")

    app = AnchorEditor(images_dir=images_dir, image_path=image_path, output_path=output_path)
    app.run()


if __name__ == "__main__":
    main()
