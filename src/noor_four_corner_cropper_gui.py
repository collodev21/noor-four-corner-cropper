"""Tkinter GUI for Noor Four-Corner Cropper."""
from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path

from PIL import Image, ImageDraw, ImageTk
from noor_four_corner_cropper import SUPPORTED, open_image, warp_image, save_corrected, output_dimensions

COLORS = ("#e53935", "#43a047", "#1e88e5", "#8e24aa")
NAMES = ("Top-left", "Top-right", "Bottom-right", "Bottom-left")


class CropperApp:
    def __init__(self, root):
        self.root = root
        root.title("Noor Four-Corner Cropper — Manual Perspective Correction")
        root.geometry("1100x760")
        root.minsize(800, 560)
        self.path: Path | None = None
        self.original: Image.Image | None = None
        self.points: list[list[float]] = []
        self.photo = None
        self.scale = 1.0
        self.offset = (0.0, 0.0)
        self.drag_index = None
        self._build()
        root.protocol("WM_DELETE_WINDOW", self._close)

    def _build(self):
        shell = ttk.Frame(self.root, padding=12); shell.pack(fill="both", expand=True)
        ttk.Label(shell, text="Noor Four-Corner Cropper", font=("Segoe UI", 16, "bold")).pack(anchor="w")
        ttk.Label(shell, text="Open a photo, drag the four handles clockwise around the document, preview and save a corrected copy.").pack(anchor="w", pady=(2, 8))
        buttons = ttk.Frame(shell); buttons.pack(fill="x", pady=(0, 7))
        ttk.Button(buttons, text="Open image…", command=self._open).pack(side="left")
        ttk.Button(buttons, text="Reset corners", command=self._reset).pack(side="left", padx=6)
        ttk.Button(buttons, text="Preview correction", command=self._preview).pack(side="left", padx=6)
        ttk.Button(buttons, text="Save corrected copy…", command=self._save).pack(side="left", padx=6)
        self.info = ttk.Label(buttons, text="No image selected")
        self.info.pack(side="right")
        self.canvas = tk.Canvas(shell, background="#23272e", highlightthickness=0, cursor="crosshair")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda _e: self._draw())
        self.canvas.bind("<Button-1>", self._press)
        self.canvas.bind("<B1-Motion>", self._motion)
        self.canvas.bind("<ButtonRelease-1>", lambda _e: setattr(self, "drag_index", None))
        ttk.Label(shell, text="Corner order is fixed: red TL → green TR → blue BR → purple BL. Drag handles; do not cross them. Original image is never overwritten.").pack(anchor="w", pady=(7, 0))

    def _open(self):
        patterns = " ".join("*" + ext for ext in sorted(SUPPORTED))
        name = filedialog.askopenfilename(title="Open document photo", filetypes=[("Images", patterns), ("All files", "*.*")])
        if not name: return
        try:
            new = open_image(name)
            if self.original: self.original.close()
            self.original = new
            self.path = Path(name)
            w, h = new.size
            margin_x, margin_y = max(1, w * .04), max(1, h * .04)
            self.points = [[margin_x, margin_y], [w-1-margin_x, margin_y],
                           [w-1-margin_x, h-1-margin_y], [margin_x, h-1-margin_y]]
            self.info.configure(text=f"{self.path.name} — {w} × {h} px")
            self._draw()
        except Exception as exc:
            messagebox.showerror("Cannot open image", str(exc))

    def _close(self):
        if self.original: self.original.close()
        self.root.destroy()

    def _reset(self):
        if not self.original: return
        w, h = self.original.size
        mx, my = max(1, w * .04), max(1, h * .04)
        self.points = [[mx, my], [w-1-mx, my], [w-1-mx, h-1-my], [mx, h-1-my]]
        self._draw()

    def _draw(self):
        self.canvas.delete("all")
        if self.original is None: return
        cw, ch = max(1, self.canvas.winfo_width()), max(1, self.canvas.winfo_height())
        iw, ih = self.original.size
        self.scale = min((cw-30)/iw, (ch-30)/ih)
        if self.scale <= 0: self.scale = .1
        display = self.original.copy()
        display.thumbnail((max(1, int(iw*self.scale)), max(1, int(ih*self.scale))), Image.Resampling.LANCZOS)
        self.scale = display.width / iw
        self.offset = ((cw-display.width)/2, (ch-display.height)/2)
        overlay = display.convert("RGBA")
        draw = ImageDraw.Draw(overlay)
        pts = [(round(x*self.scale), round(y*self.scale)) for x,y in self.points]
        if len(pts) == 4:
            draw.line(pts+[pts[0]], fill=(255, 235, 59, 240), width=max(2, round(2*self.scale)))
            radius = max(6, round(min(display.size)*.014))
            for i, (x,y) in enumerate(pts):
                draw.ellipse((x-radius,y-radius,x+radius,y+radius), fill=COLORS[i], outline="white", width=2)
                draw.text((x+radius+2,y-radius-4), NAMES[i], fill="white", stroke_width=2, stroke_fill="#111111")
        self.photo = ImageTk.PhotoImage(overlay)
        self.canvas.create_image(*self.offset, image=self.photo, anchor="nw")
        display.close(); overlay.close()

    def _canvas_to_image(self, x, y):
        return ((x-self.offset[0])/self.scale, (y-self.offset[1])/self.scale)

    def _press(self, event):
        if not self.points: return
        nearest, distance = None, float("inf")
        for i, p in enumerate(self.points):
            px = self.offset[0]+p[0]*self.scale
            py = self.offset[1]+p[1]*self.scale
            d = (px-event.x)**2+(py-event.y)**2
            if d < distance: nearest, distance = i, d
        if nearest is not None and distance <= 28**2: self.drag_index = nearest

    def _motion(self, event):
        if self.drag_index is None or self.original is None: return
        x, y = self._canvas_to_image(event.x, event.y)
        x = min(max(0, x), self.original.width-1)
        y = min(max(0, y), self.original.height-1)
        candidate = [p[:] for p in self.points]
        candidate[self.drag_index] = [x,y]
        try:
            from noor_four_corner_cropper import validate_corners
            validate_corners(candidate, self.original.width, self.original.height)
            self.points = candidate
            self._draw()
        except ValueError:
            # Do not permit self-intersecting or degenerate corner positions.
            pass

    def _corrected(self):
        if self.original is None: raise ValueError("Open an image first")
        return warp_image(self.original, self.points)

    def _preview(self):
        try:
            corrected = self._corrected()
            win = tk.Toplevel(self.root); win.title("Corrected preview")
            display = corrected.copy(); display.thumbnail((900,650), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(display)
            label = ttk.Label(win, image=photo); label.image = photo; label.pack(padx=10,pady=10)
            dims = output_dimensions(self.points)
            ttk.Label(win, text=f"Output: {corrected.width} × {corrected.height} pixels (estimated from selected edges; source edges {dims[0]} × {dims[1]} px)").pack(padx=10,pady=(0,10))
            display.close(); corrected.close()
        except Exception as exc:
            messagebox.showerror("Cannot create preview", str(exc))

    def _save(self):
        if not self.path: return
        name = filedialog.asksaveasfilename(title="Save corrected copy", initialdir=str(self.path.parent),
             initialfile=f"{self.path.stem}-corrected.png", defaultextension=".png",
             filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg *.jpeg"), ("TIFF", "*.tif *.tiff"), ("WebP", "*.webp")])
        if not name: return
        try:
            result = save_corrected(self.path, name, self.points)
            messagebox.showinfo("Saved", f"Corrected copy saved:\n{result}")
        except Exception as exc:
            messagebox.showerror("Save failed", str(exc))


def run_gui():
    root = tk.Tk(); CropperApp(root); root.mainloop()


if __name__ == "__main__": run_gui()
