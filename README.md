# Noor Four-Corner Cropper

**Day 4 — offline manual perspective correction for photographed documents.**

Open an image, position four draggable handles around the document in clockwise order, preview the perspective-corrected result, and save a new image. The cropper does not alter the source file, upload images, recognize document content, or claim that the result is an official scan.

## What it does

The four selected points define a quadrilateral in the source photograph. The app maps that shape into a rectangle by a projective transform. Output width and height are estimated from the average lengths of opposite selected edges. The optional CLI accepts explicit output dimensions in pixels. The tool does not auto-detect edges; users select and adjust them manually.

Features include EXIF orientation handling, draggable corner handles in a fitted preview, corrected preview, PNG/JPEG/TIFF/BMP/WebP output, output-size safeguards, and safe save-as behavior. Processing is local using Python and Pillow only. The source image is never overwritten.

## Related tools and distinct scope

[Perspec](https://github.com/ad-si/Perspec) is a more mature perspective-correction desktop app with automatic corner detection, manual corner movement, zoom/pan, batch workflows and OCR-backed PDF support; its repository README describes Haskell/FlatCV tooling and its source license as AGPL-3.0. [Free Scanner](https://github.com/ujjawal200/Document-Scanner) is an Android camera scanner with OpenCV edge detection, draggable manual corners, OCR and PDF/JPEG export. [LiteObject/doc-scanner](https://github.com/LiteObject/doc-scanner) is a CLI scanner using OpenCV/NumPy for automatic document detection and enhancement. Noor Four-Corner Cropper is intentionally narrower: a lightweight Windows-friendly manual cropper that uses Pillow without requiring a camera, OpenCV, OCR or cloud service. This summary reflects their public repository documentation, not an independent security audit.

## Requirements

- Windows 10/11 recommended; Python 3.10 or newer.
- Pillow is the only runtime package. The GUI uses Tkinter/Tcl-Tk, which normally ships with the python.org Windows installation. Verify the Tk/Tcl option is installed if importing `tkinter` fails.
- This is source code, not a packaged executable or installer.

## Windows installation and use

Install Python from [python.org](https://www.python.org/downloads/windows/) and include Tcl/Tk. In PowerShell, from this repository:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python .\src\noor_four_corner_cropper_gui.py
```

Open an image. The initial quadrilateral is inset slightly from the image edges. Drag the red top-left, green top-right, blue bottom-right and purple bottom-left handles clockwise around the document. Use **Preview correction** to inspect the warp, then **Save corrected copy** to export. Keep a flat, clear margin around the document in the source photo where possible; the tool does not reconstruct obscured or off-frame edges.

### Command line

Supply source coordinates in pixel units, clockwise from the top-left corner. For example:

```powershell
python .\src\noor_four_corner_cropper.py "C:\Scans\photo.png" --corners 110 80 930 120 900 1180 90 1120 --output "C:\Scans\photo-corrected.png"
```

Use `--width` and `--height` together to request explicit output pixel dimensions. If omitted, dimensions are derived from the average lengths of opposite edges. Do not specify just one of them.

## Tests

Install test dependencies and run:

```powershell
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

Seven automated tests cover rectangular and trapezoidal perspective transforms, output geometry, invalid/reversed/out-of-frame/self-crossing corners, too-small selections, Unicode paths, preservation of the original, corrupt input, unsupported output extension and collision protection. GitHub Actions is configured for the core tests on Windows and Ubuntu with Python 3.10 and 3.12.

## Limitations and status

- This is a manual cropper; it does not detect page boundaries automatically or enhance contrast.
- The GUI has a fit-to-window preview but no zoom/pan controls. Precise corners near tiny details can be hard to place at small preview scales.
- It exports corrected image files, not multi-page PDFs. Use a separate PDF tool for document assembly.
- The Linux build environment used for this version has no Tkinter. The GUI itself could not be launched here.
- Physical scanner/camera and Windows desktop interaction tests are not performed in the Linux environment. A CI pass for the Python core is not evidence that a user interacted with the GUI.
- No screenshot, Windows executable, installer, signed package or release is included.
- French/Arabic translations and RTL interface support are future work.

## Privacy and safe use

Images are processed locally; the app has no telemetry, network upload or OCR. Save corrected output as a new file and check it before using it for official purposes. Do not use this utility to forge, falsify or alter the content of identity documents. Do not post real customer documents in bug reports; use synthetic or redacted samples.

## License

MIT; see [LICENSE](LICENSE). Security reporting: see [SECURITY.md](SECURITY.md).
