# 📸 Web Photo Quick Cropper, Saver & Printer (Qt6) + Microsoft Edge Watcher

**Author & Developer:** Corey Kiesel  
**Version:** 1.0 (Windows)

A modern, high-performance Qt6 desktop application designed to watch Microsoft Edge, load photos when clicked or copied, and crop, save, or **print** them directly.

---

## 📦 Windows Installer

A standalone Windows installer has been compiled and ready for distribution:

### 🚀 **Installer Location:**
- [`dist/Setup_WebPhotoCropper.exe`](file:///d:/TEST/dist/Setup_WebPhotoCropper.exe)

### ⚙️ What the Installer Does:
1. **Zero Prerequisites**: Does **not** require Python, Pip, or Qt to be pre-installed on the target machine.
2. **Setup Wizard**: Lets the user select installation path (defaults to `%LOCALAPPDATA%\Programs\WebPhotoCropper`).
3. **Shortcuts**: Automatically creates **Desktop** and **Start Menu** shortcuts with the application icon.
4. **Uninstaller**: Places a clean `Uninstall.bat` script inside the directory.
5. **Instant Launch**: Offers to launch Web Photo Cropper immediately upon installation.

---

## 🖨️ Comprehensive Print & Scaling Studio

- **📐 Universal Scaling Modes**:
  - **🎯 Fit to Printable Page**: Automatically scales photo to maximize printable area while strictly preserving aspect ratio.
  - **🖼️ Fill Page / Bleed (Crop to Fit)**: Scales photo to cover entire sheet or margins with clean centered clipping.
  - **🔍 100% Original Actual Pixel Size**: Hardware-accurate 1:1 pixel rendering at selectable DPI (300 DPI Photo Quality, 600 DPI Fine, 150 DPI Draft, 96 DPI Screen).
  - **📊 Custom Scale Percentage**: Smooth slider & spinbox from **5% to 500%** with quick presets (`25%`, `50%`, `75%`, `100%`, `150%`, `200%`).
  - **📏 Standard Photo Size Presets**: 1-click scaling to standard photo formats:
    - `4" × 6"` (Standard Photo)
    - `5" × 7"` (Photo Print)
    - `8" × 10"` (Portrait Frame)
    - `8.5" × 11"` (US Letter Full)
    - `A4 (210 × 297 mm)`
    - `2.5" × 3.5"` (Wallet Size)
    - `2" × 2"` (Passport / ID)
    - `4" × 4"`, `5" × 5"`, `8" × 8"` (Square Prints)
  - **📐 Specific Custom Dimensions**: Enter exact target Width × Height in inches with optional aspect ratio lock.

- **🧭 9-Point Alignment & Fine Nudge**:
  - Top-Left, Top-Center, Top-Right, Center-Left, Center, Center-Right, Bottom-Left, Bottom-Center, Bottom-Right.
  - Fine X & Y offset adjusters in inches.

- **📄 Margins, Orientation & Decorative Frames**:
  - Margin Presets: Normal (0.5"), Narrow (0.25"), Borderless (0.0"), or Custom.
  - Orientation: Auto-Detect (matches photo orientation), Force Portrait, Force Landscape.
  - Frames: Thin border, Medium frame, Thick border, White photo mat, Classic black frame.

- **👁️ Real-time Live Sheet Preview**:
  - Interactive white sheet canvas showing exact paper placement, margin guidelines, dimension annotations, and zoom controls.

- **💾 PDF Export & System Print**:
  - Instant vector/raster **Export to PDF...**
  - Native System Print Dialog and System Print Preview.

---

## 🌐 Microsoft Edge Watcher & Direct Click

1. **Automatic Background Server**: Listens on `http://127.0.0.1:59999` when the app runs.
2. **Permanent Edge Extension** in [`d:/TEST/extension/`](file:///d:/TEST/extension/): Load unpacked once in `edge://extensions` to enable 100% automatic direct clicking across all websites.
3. **1-Click Bookmarklet**: Open [`edge_bookmark_helper.html`](file:///d:/TEST/edge_bookmark_helper.html) and drag `[✂️ Send to Cropper]` to your Favorites bar.
4. **Real-time Clipboard Auto-Sync**: Right-click -> "Copy image" in Edge auto-loads the photo immediately into the app.

---

## ⌨️ Shortcuts

| Shortcut | Action |
| :--- | :--- |
| `Ctrl + P` | **Print Selected Photo / Crop** |
| `Enter` | **Save Crop to File** |
| `Esc` / `Del` | **Clear Crop Selection** |
| `Mouse Wheel` | **Zoom In / Out** |
| `Middle / Right Drag` | **Pan Canvas** |
