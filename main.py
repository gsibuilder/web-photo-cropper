"""
Web Photo Quick Cropper, Saver & Printer - Modern Qt6 Application
Created & Developed by: Corey Kiesel
With Microsoft Edge Auto-Watcher, Direct Click Plugin & System Printing
"""
import sys
import os
import json
import time
import urllib.parse
import webbrowser
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
import socket
from datetime import datetime
if sys.platform != "win32":
    os.environ["QT_QPA_PLATFORM"] = "xcb"

def open_in_browser(path):
    # Open a file or URL in the system's default web browser (Chrome on Linux if set as default)
    if os.path.isfile(path):
        webbrowser.open_new_tab(f"file://{os.path.abspath(path)}")
    else:
        webbrowser.open_new_tab(path)

def open_path(path):
    if sys.platform == "win32":
        os.startfile(path)
    else:
        subprocess.run(["xdg-open", path])

from PyQt6.QtCore import (
    Qt, QSize, QPoint, QRect, QRectF, pyqtSignal, QThread, QObject, 
    QStandardPaths, QUrl, QTimer, QRunnable, QThreadPool
)
from PyQt6.QtGui import (
    QAction, QColor, QCursor, QFont, QIcon, QImage, QKeySequence, 
    QPainter, QPen, QBrush, QPixmap, QTransform, QGuiApplication, 
    QDragEnterEvent, QDropEvent, QShortcut, QPageLayout, QPageSize
)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QSplitter, QLabel, QLineEdit, QPushButton, QComboBox, QSpinBox, 
    QDoubleSpinBox, QGroupBox, QCheckBox, QFileDialog, QScrollArea, QFrame, 
    QToolBar, QStatusBar, QMessageBox, QListWidget, QListWidgetItem, 
    QTabWidget, QGridLayout, QSlider, QButtonGroup, QRadioButton, 
    QSizePolicy, QToolTip, QDialog, QTextEdit, QMenu
)

try:
    from PyQt6.QtPrintSupport import QPrinter, QPrintDialog, QPrintPreviewDialog
    HAS_PRINT_SUPPORT = True
except Exception:
    HAS_PRINT_SUPPORT = False

import requests
from PIL import Image
import io


class ReusableHTTPServer(HTTPServer):
    allow_reuse_address = True


class EdgeWebhookHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_OPTIONS(self):
        try:
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()
        except Exception:
            pass

    def do_GET(self):
        try:
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path == '/load':
                query = urllib.parse.parse_qs(parsed.query)
                if 'url' in query and len(query['url']) > 0:
                    img_url = query['url'][0]
                    if hasattr(self.server, 'worker_signal'):
                        self.server.worker_signal.emit(img_url)
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(b'{"status": "ok", "message": "Photo received by Qt app"}')
                    return

            self.send_response(404)
            self.end_headers()
        except Exception:
            pass

    def do_POST(self):
        try:
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path == '/load':
                content_length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_length).decode('utf-8', errors='ignore')
                data = json.loads(body)
                img_url = data.get('url', '')
                if img_url and hasattr(self.server, 'worker_signal'):
                    self.server.worker_signal.emit(img_url)

                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(b'{"status": "ok"}')
                return

            self.send_response(404)
            self.end_headers()
        except Exception:
            pass


class EdgeServerThread(QThread):
    imageReceived = pyqtSignal(str)

    def __init__(self, port=59999):
        super().__init__()
        self.port = port
        self.httpd = None
        self._is_running = True

    def run(self):
        ports_to_try = [self.port, 59998, 59997, 59996]
        for p in ports_to_try:
            try:
                self.httpd = ReusableHTTPServer(('127.0.0.1', p), EdgeWebhookHandler)
                self.httpd.worker_signal = self.imageReceived
                self.port = p
                break
            except Exception:
                continue

        if self.httpd:
            try:
                self.httpd.serve_forever()
            except Exception:
                pass

    def stop(self):
        self._is_running = False
        if self.httpd:
            try:
                self.httpd.shutdown()
                self.httpd.server_close()
            except Exception:
                pass


class DownloadSignals(QObject):
    finished = pyqtSignal(QPixmap, str, dict)
    error = pyqtSignal(str)


class ImageDownloadTask(QRunnable):
    def __init__(self, url):
        super().__init__()
        self.url = url
        self.signals = DownloadSignals()

    def run(self):
        try:
            if not self.url:
                self.signals.error.emit("Empty URL provided.")
                return

            image_data = None
            if self.url.startswith("data:image/"):
                header, encoded = self.url.split(",", 1)
                import base64
                image_data = base64.b64decode(encoded)
            elif self.url.startswith("http://") or self.url.startswith("https://"):
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                }
                response = requests.get(self.url, headers=headers, timeout=12)
                response.raise_for_status()
                image_data = response.content
            elif os.path.exists(self.url):
                with open(self.url, 'rb') as f:
                    image_data = f.read()
            else:
                self.signals.error.emit(f"Unrecognized image source: {self.url[:60]}")
                return

            if not image_data:
                self.signals.error.emit("No image data received.")
                return

            image = QImage()
            if not image.loadFromData(image_data):
                try:
                    pil_img = Image.open(io.BytesIO(image_data))
                    if pil_img.mode != "RGBA":
                        pil_img = pil_img.convert("RGBA")
                    data = pil_img.tobytes("raw", "RGBA")
                    image = QImage(data, pil_img.size[0], pil_img.size[1], QImage.Format.Format_RGBA8888)
                except Exception as pil_err:
                    self.signals.error.emit(f"Image decode failed: {str(pil_err)}")
                    return

            if image.isNull():
                self.signals.error.emit("Decoded image is empty.")
                return

            pixmap = QPixmap.fromImage(image)
            metadata = {
                'size_bytes': len(image_data),
                'width': pixmap.width(),
                'height': pixmap.height()
            }
            self.signals.finished.emit(pixmap, self.url, metadata)
        except Exception as e:
            self.signals.error.emit(f"Failed to load photo: {str(e)}")


class InteractiveCropper(QWidget):
    cropCompleted = pyqtSignal(QPixmap, QRect)
    mouseMovedOnImage = pyqtSignal(int, int)
    statusMessage = pyqtSignal(str)
    fileOrUrlDropped = pyqtSignal(str)

    MODE_DRAG_RECT = 0
    MODE_CLICK_FIXED = 1
    MODE_PAN = 2

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAcceptDrops(True)

        self.pixmap = None
        self.scale_factor = 1.0
        self.offset = QPoint(0, 0)
        
        self.mode = self.MODE_DRAG_RECT
        self.instant_save_on_click = True
        self.instant_save_on_drag_release = False
        
        self.fixed_crop_width = 300
        self.fixed_crop_height = 300
        
        self.crop_rect = QRect()
        self.is_drawing_rect = False
        self.is_moving_rect = False
        self.is_resizing_rect = False
        self.resize_handle_index = -1
        
        self.drag_start_pos = QPoint()
        self.rect_start_origin = QRect()
        self.aspect_ratio_mode = "Free"
        
        self.is_panning = False
        self.pan_start_pos = QPoint()
        self.handle_size = 10

        self.setStyleSheet("background-color: #121316;")

    def dragEnterEvent(self, event: QDragEnterEvent):
        try:
            if event.mimeData().hasUrls() or event.mimeData().hasText() or event.mimeData().hasImage():
                event.acceptProposedAction()
        except Exception:
            pass

    def dropEvent(self, event: QDropEvent):
        try:
            mime = event.mimeData()
            if mime.hasUrls():
                for url in mime.urls():
                    url_str = url.toString()
                    if url.isLocalFile():
                        url_str = url.toLocalFile()
                    self.fileOrUrlDropped.emit(url_str)
                    event.acceptProposedAction()
                    return
            elif mime.hasText():
                text = mime.text().strip()
                if text.startswith("http://") or text.startswith("https://") or text.startswith("data:image/"):
                    self.fileOrUrlDropped.emit(text)
                    event.acceptProposedAction()
                    return
            elif mime.hasImage():
                img = mime.imageData()
                if isinstance(img, QImage) and not img.isNull():
                    self.setPixmap(QPixmap.fromImage(img))
                    event.acceptProposedAction()
        except Exception:
            pass

    def setPixmap(self, pixmap: QPixmap):
        if pixmap and not pixmap.isNull():
            self.pixmap = pixmap
            self.crop_rect = QRect()
            self.resetZoom()
            self.update()

    def resetZoom(self):
        if not self.pixmap or self.pixmap.isNull():
            self.scale_factor = 1.0
            self.offset = QPoint(0, 0)
            return

        w = max(1, self.pixmap.width())
        h = max(1, self.pixmap.height())
        w_ratio = (self.width() - 40) / w
        h_ratio = (self.height() - 40) / h
        self.scale_factor = max(0.05, min(w_ratio, h_ratio, 1.0))
        
        img_w = w * self.scale_factor
        img_h = h * self.scale_factor
        self.offset = QPoint(int((self.width() - img_w) / 2), int((self.height() - img_h) / 2))
        self.update()

    def zoomIn(self):
        self.zoom(1.25, QPoint(self.width() // 2, self.height() // 2))

    def zoomOut(self):
        self.zoom(0.8, QPoint(self.width() // 2, self.height() // 2))

    def zoom(self, factor, center_pos: QPoint):
        if not self.pixmap or self.pixmap.isNull():
            return
        
        old_scale = self.scale_factor
        new_scale = max(0.05, min(old_scale * factor, 15.0))
        if old_scale == new_scale:
            return

        img_x = (center_pos.x() - self.offset.x()) / old_scale
        img_y = (center_pos.y() - self.offset.y()) / old_scale

        self.scale_factor = new_scale
        self.offset = QPoint(
            int(center_pos.x() - img_x * self.scale_factor),
            int(center_pos.y() - img_y * self.scale_factor)
        )
        self.update()

    def wheelEvent(self, event):
        if not self.pixmap:
            return
        delta = event.angleDelta().y()
        if delta > 0:
            self.zoom(1.15, event.position().toPoint())
        elif delta < 0:
            self.zoom(0.87, event.position().toPoint())

    def screenToImage(self, screen_pos: QPoint) -> QPoint:
        if not self.pixmap or self.scale_factor == 0:
            return QPoint(0, 0)
        x = int((screen_pos.x() - self.offset.x()) / self.scale_factor)
        y = int((screen_pos.y() - self.offset.y()) / self.scale_factor)
        return QPoint(x, y)

    def imageToScreen(self, img_pos: QPoint) -> QPoint:
        x = int(img_pos.x() * self.scale_factor + self.offset.x())
        y = int(img_pos.y() * self.scale_factor + self.offset.y())
        return QPoint(x, y)

    def imageRectToScreen(self, r: QRect) -> QRect:
        top_left = self.imageToScreen(r.topLeft())
        w = int(r.width() * self.scale_factor)
        h = int(r.height() * self.scale_factor)
        return QRect(top_left.x(), top_left.y(), w, h)

    def getHandleRects(self, screen_rect: QRect):
        hs = self.handle_size
        half = hs // 2
        r = screen_rect
        return [
            QRect(r.left() - half, r.top() - half, hs, hs),
            QRect(r.center().x() - half, r.top() - half, hs, hs),
            QRect(r.right() - half, r.top() - half, hs, hs),
            QRect(r.right() - half, r.center().y() - half, hs, hs),
            QRect(r.right() - half, r.bottom() - half, hs, hs),
            QRect(r.center().x() - half, r.bottom() - half, hs, hs),
            QRect(r.left() - half, r.bottom() - half, hs, hs),
            QRect(r.left() - half, r.center().y() - half, hs, hs)
        ]

    def getHandleAtPos(self, screen_pos: QPoint) -> int:
        if self.crop_rect.isEmpty():
            return -1
        screen_r = self.imageRectToScreen(self.crop_rect)
        handles = self.getHandleRects(screen_r)
        for idx, handle in enumerate(handles):
            if handle.contains(screen_pos):
                return idx
        return -1

    def mousePressEvent(self, event):
        if not self.pixmap or self.pixmap.isNull():
            return

        pos = event.position().toPoint()
        img_pos = self.screenToImage(pos)

        if event.button() == Qt.MouseButton.MiddleButton or (event.button() == Qt.MouseButton.RightButton and event.modifiers() == Qt.KeyboardModifier.NoModifier):
            self.is_panning = True
            self.pan_start_pos = pos
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return

        if event.button() == Qt.MouseButton.LeftButton:
            if self.mode == self.MODE_PAN:
                self.is_panning = True
                self.pan_start_pos = pos
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
                return

            if self.mode == self.MODE_CLICK_FIXED:
                crop_w = min(self.fixed_crop_width, self.pixmap.width())
                crop_h = min(self.fixed_crop_height, self.pixmap.height())
                
                top_left_x = int(img_pos.x() - crop_w / 2)
                top_left_y = int(img_pos.y() - crop_h / 2)
                
                top_left_x = max(0, min(top_left_x, self.pixmap.width() - crop_w))
                top_left_y = max(0, min(top_left_y, self.pixmap.height() - crop_h))
                
                self.crop_rect = QRect(top_left_x, top_left_y, crop_w, crop_h)
                self.update()
                
                if self.instant_save_on_click:
                    self.executeCrop()
                else:
                    self.statusMessage.emit(f"Selected crop at ({top_left_x}, {top_left_y}) - {crop_w}x{crop_h}px")
                return

            handle_idx = self.getHandleAtPos(pos)
            if handle_idx != -1:
                self.is_resizing_rect = True
                self.resize_handle_index = handle_idx
                self.drag_start_pos = img_pos
                self.rect_start_origin = QRect(self.crop_rect)
                return

            screen_rect = self.imageRectToScreen(self.crop_rect)
            if not self.crop_rect.isEmpty() and screen_rect.contains(pos):
                self.is_moving_rect = True
                self.drag_start_pos = img_pos
                self.rect_start_origin = QRect(self.crop_rect)
                self.setCursor(Qt.CursorShape.SizeAllCursor)
                return

            self.is_drawing_rect = True
            img_x = max(0, min(img_pos.x(), self.pixmap.width()))
            img_y = max(0, min(img_pos.y(), self.pixmap.height()))
            self.drag_start_pos = QPoint(img_x, img_y)
            self.crop_rect = QRect(self.drag_start_pos, QSize(0, 0))
            self.update()

    def mouseMoveEvent(self, event):
        pos = event.position().toPoint()
        img_pos = self.screenToImage(pos)
        self.mouseMovedOnImage.emit(img_pos.x(), img_pos.y())

        if self.is_panning:
            delta = pos - self.pan_start_pos
            self.offset += delta
            self.pan_start_pos = pos
            self.update()
            return

        if not self.pixmap or self.pixmap.isNull():
            return

        if self.is_drawing_rect:
            img_x = max(0, min(img_pos.x(), self.pixmap.width()))
            img_y = max(0, min(img_pos.y(), self.pixmap.height()))
            
            w = img_x - self.drag_start_pos.x()
            h = img_y - self.drag_start_pos.y()
            
            w, h = self.applyAspectRatioConstraint(w, h)

            new_rect = QRect(self.drag_start_pos.x(), self.drag_start_pos.y(), w, h).normalized()
            clamped_rect = new_rect.intersected(QRect(0, 0, self.pixmap.width(), self.pixmap.height()))
            self.crop_rect = clamped_rect
            self.update()
            return

        if self.is_moving_rect:
            delta_x = img_pos.x() - self.drag_start_pos.x()
            delta_y = img_pos.y() - self.drag_start_pos.y()
            
            new_rect = self.rect_start_origin.translated(delta_x, delta_y)
            if new_rect.left() < 0:
                new_rect.moveLeft(0)
            if new_rect.top() < 0:
                new_rect.moveTop(0)
            if new_rect.right() > self.pixmap.width():
                new_rect.moveRight(self.pixmap.width())
            if new_rect.bottom() > self.pixmap.height():
                new_rect.moveBottom(self.pixmap.height())

            self.crop_rect = new_rect
            self.update()
            return

        if self.is_resizing_rect:
            delta_x = img_pos.x() - self.drag_start_pos.x()
            delta_y = img_pos.y() - self.drag_start_pos.y()
            
            r = QRect(self.rect_start_origin)
            idx = self.resize_handle_index
            
            if idx == 0:
                r.setTopLeft(r.topLeft() + QPoint(delta_x, delta_y))
            elif idx == 1:
                r.setTop(r.top() + delta_y)
            elif idx == 2:
                r.setTopRight(r.topRight() + QPoint(delta_x, delta_y))
            elif idx == 3:
                r.setRight(r.right() + delta_x)
            elif idx == 4:
                r.setBottomRight(r.bottomRight() + QPoint(delta_x, delta_y))
            elif idx == 5:
                r.setBottom(r.bottom() + delta_y)
            elif idx == 6:
                r.setBottomLeft(r.bottomLeft() + QPoint(delta_x, delta_y))
            elif idx == 7:
                r.setLeft(r.left() + delta_x)

            normalized = r.normalized()
            clamped = normalized.intersected(QRect(0, 0, self.pixmap.width(), self.pixmap.height()))
            self.crop_rect = clamped
            self.update()
            return

        if self.mode == self.MODE_DRAG_RECT:
            handle = self.getHandleAtPos(pos)
            if handle in (0, 4):
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            elif handle in (2, 6):
                self.setCursor(Qt.CursorShape.SizeBDiagCursor)
            elif handle in (1, 5):
                self.setCursor(Qt.CursorShape.SizeVerCursor)
            elif handle in (3, 7):
                self.setCursor(Qt.CursorShape.SizeHorCursor)
            elif not self.crop_rect.isEmpty() and self.imageRectToScreen(self.crop_rect).contains(pos):
                self.setCursor(Qt.CursorShape.SizeAllCursor)
            else:
                self.setCursor(Qt.CursorShape.CrossCursor)
        elif self.mode == self.MODE_CLICK_FIXED:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        elif self.mode == self.MODE_PAN:
            self.setCursor(Qt.CursorShape.OpenHandCursor)

    def applyAspectRatioConstraint(self, w, h):
        ratio_map = {
            "1:1": 1.0,
            "4:3": 4.0 / 3.0,
            "16:9": 16.0 / 9.0,
            "3:2": 3.0 / 2.0,
            "9:16": 9.0 / 16.0,
            "2:3": 2.0 / 3.0
        }
        if self.aspect_ratio_mode not in ratio_map:
            return w, h
        
        target_ratio = ratio_map[self.aspect_ratio_mode]
        sign_x = 1 if w >= 0 else -1
        sign_y = 1 if h >= 0 else -1
        
        abs_w = abs(w)
        abs_h = abs(h)
        calculated_h = abs_w / target_ratio
        return int(abs_w * sign_x), int(calculated_h * sign_y)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.is_drawing_rect:
                self.is_drawing_rect = False
                if self.crop_rect.width() > 5 and self.crop_rect.height() > 5:
                    if self.instant_save_on_drag_release:
                        self.executeCrop()
                    else:
                        self.statusMessage.emit(f"Selection ready: {self.crop_rect.width()}x{self.crop_rect.height()}px. Press Enter, Save, or Print.")
                else:
                    self.crop_rect = QRect()
                self.update()

            if self.is_moving_rect:
                self.is_moving_rect = False

            if self.is_resizing_rect:
                self.is_resizing_rect = False
                self.resize_handle_index = -1

        if event.button() in (Qt.MouseButton.MiddleButton, Qt.MouseButton.RightButton, Qt.MouseButton.LeftButton):
            if self.is_panning:
                self.is_panning = False
                self.setCursor(Qt.CursorShape.ArrowCursor)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.executeCrop()
        elif event.key() == Qt.Key.Key_Escape:
            self.crop_rect = QRect()
            self.update()
        elif event.key() == Qt.Key.Key_Delete:
            self.crop_rect = QRect()
            self.update()
        else:
            super().keyPressEvent(event)

    def getSelectedOrFullPixmap(self) -> QPixmap:
        if not self.pixmap or self.pixmap.isNull():
            return QPixmap()
        if not self.crop_rect.isEmpty() and self.crop_rect.width() > 1 and self.crop_rect.height() > 1:
            return self.pixmap.copy(self.crop_rect)
        return self.pixmap

    def executeCrop(self):
        if not self.pixmap or self.pixmap.isNull():
            return
        
        target_rect = self.crop_rect
        if target_rect.isEmpty() or target_rect.width() < 2 or target_rect.height() < 2:
            self.statusMessage.emit("No crop area selected.")
            return

        cropped_pixmap = self.pixmap.copy(target_rect)
        self.cropCompleted.emit(cropped_pixmap, target_rect)
        self.statusMessage.emit(f"Cropped {target_rect.width()}x{target_rect.height()}px successfully!")

    def selectEntireImage(self):
        if not self.pixmap or self.pixmap.isNull():
            return
        self.crop_rect = QRect(0, 0, self.pixmap.width(), self.pixmap.height())
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        painter.fillRect(self.rect(), QColor("#14161a"))
        
        if not self.pixmap or self.pixmap.isNull():
            painter.setPen(QColor("#7d8590"))
            painter.setFont(QFont("Segoe UI", 12))
            text = "No Photo Loaded\n\n🖱️ Click any picture in Edge (Plugin / Bookmark active)\n📋 Or right-click 'Copy image' in Edge to auto-load!"
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, text)
            return

        screen_w = int(self.pixmap.width() * self.scale_factor)
        screen_h = int(self.pixmap.height() * self.scale_factor)
        img_dest_rect = QRect(self.offset.x(), self.offset.y(), screen_w, screen_h)

        shadow_rect = img_dest_rect.adjusted(-2, -2, 2, 2)
        painter.fillRect(shadow_rect, QColor(0, 0, 0, 80))
        painter.drawPixmap(img_dest_rect, self.pixmap)

        if not self.crop_rect.isEmpty() and self.crop_rect.isValid():
            screen_crop = self.imageRectToScreen(self.crop_rect)
            dim_brush = QBrush(QColor(0, 0, 0, 160))
            
            painter.fillRect(QRect(img_dest_rect.left(), img_dest_rect.top(), img_dest_rect.width(), max(0, screen_crop.top() - img_dest_rect.top())), dim_brush)
            painter.fillRect(QRect(img_dest_rect.left(), screen_crop.bottom() + 1, img_dest_rect.width(), max(0, img_dest_rect.bottom() - screen_crop.bottom())), dim_brush)
            painter.fillRect(QRect(img_dest_rect.left(), screen_crop.top(), max(0, screen_crop.left() - img_dest_rect.left()), screen_crop.height()), dim_brush)
            painter.fillRect(QRect(screen_crop.right() + 1, screen_crop.top(), max(0, img_dest_rect.right() - screen_crop.right()), screen_crop.height()), dim_brush)

            pen = QPen(QColor("#388bfd"), 2, Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(screen_crop)

            grid_pen = QPen(QColor(255, 255, 255, 60), 1, Qt.PenStyle.DashLine)
            painter.setPen(grid_pen)
            w_third = screen_crop.width() / 3.0
            h_third = screen_crop.height() / 3.0
            for i in (1, 2):
                x = int(screen_crop.left() + i * w_third)
                painter.drawLine(x, screen_crop.top(), x, screen_crop.bottom())
                y = int(screen_crop.top() + i * h_third)
                painter.drawLine(screen_crop.left(), y, screen_crop.right(), y)

            handle_brush = QBrush(QColor("#ffffff"))
            handle_pen = QPen(QColor("#1f6feb"), 2)
            painter.setPen(handle_pen)
            painter.setBrush(handle_brush)
            for h_rect in self.getHandleRects(screen_crop):
                painter.drawRoundedRect(h_rect, 2, 2)

            dim_text = f"{self.crop_rect.width()} × {self.crop_rect.height()} px"
            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            tag_rect = QRect(screen_crop.left() + 6, max(img_dest_rect.top() + 6, screen_crop.top() - 26), 110, 22)
            painter.fillRect(tag_rect, QColor(20, 24, 30, 210))
            painter.setPen(QColor("#58a6ff"))
            painter.drawText(tag_rect, Qt.AlignmentFlag.AlignCenter, dim_text)


class EdgeSetupDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚡ Microsoft Edge Plugin & Direct Click Setup - by Corey Kiesel")
        self.resize(680, 520)
        self.setStyleSheet("""
            QDialog { background-color: #161b22; color: #c9d1d9; font-family: Segoe UI, sans-serif; }
            QLabel { color: #c9d1d9; font-size: 13px; }
            QTextEdit { background-color: #0d1117; color: #79c0ff; font-family: Consolas, monospace; font-size: 11px; border: 1px solid #30363d; border-radius: 6px; }
            QPushButton { background-color: #21262d; border: 1px solid #30363d; color: #c9d1d9; font-weight: 500; border-radius: 6px; padding: 8px 14px; }
            QPushButton:hover { background-color: #30363d; color: #ffffff; }
            #btnPrimary { background-color: #238636; border: 1px solid #2ea043; color: white; font-weight: bold; }
            #btnPrimary:hover { background-color: #2ea043; }
            #btnEdge { background-color: #1f6feb; border: 1px solid #388bfd; color: white; font-weight: bold; }
            #btnEdge:hover { background-color: #388bfd; }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("🚀 Microsoft Edge Direct Click Plugin & Bookmarklet")
        title.setStyleSheet("font-size: 17px; font-weight: bold; color: #58a6ff;")
        layout.addWidget(title)

        author_badge = QLabel("Created by Corey Kiesel")
        author_badge.setStyleSheet("color: #7ee787; font-weight: bold; font-size: 12px; margin-bottom: 4px;")
        layout.addWidget(author_badge)

        desc = QLabel(
            "<b>Two ways to automatically send Edge pictures into this app on click:</b><br><br>"
            "<b>Method A (Permanent Edge Extension - 100% Automatic on All Sites):</b><br>"
            "1. Click <b>'📂 Open Extension Folder'</b> below.<br>"
            "2. In Edge, go to <code>edge://extensions</code>, turn on <b>Developer mode</b>, and click <b>'Load unpacked'</b>.<br>"
            "3. Select the <code>extension</code> folder. Now clicking ANY photo on ANY site auto-loads it!<br><br>"
            "<b>Method B (1-Click Bookmarklet - No Installation Required):</b><br>"
            "• Open the Bookmark page below and drag <b>'✂️ Send to Cropper'</b> to your Edge Favorites bar."
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)

        action_row = QHBoxLayout()
        action_row.setSpacing(10)

        open_folder_btn = QPushButton("📂 Open Extension Folder")
        open_folder_btn.setObjectName("btnEdge")
        open_folder_btn.clicked.connect(self.openExtensionFolder)
        action_row.addWidget(open_folder_btn)

        open_edge_btn = QPushButton("🌐 Open Bookmark Setup Page in Edge")
        open_edge_btn.setObjectName("btnPrimary")
        open_edge_btn.clicked.connect(self.openSetupInEdge)
        action_row.addWidget(open_edge_btn)

        copy_code_btn = QPushButton("📋 Copy Bookmarklet Code")
        copy_code_btn.clicked.connect(self.copyScript)
        action_row.addWidget(copy_code_btn)

        layout.addLayout(action_row)

        self.js_code = (
            "javascript:(function(){"
            "if(window._edgeCropWatchActive){alert('Edge Photo Watch is already active! Click any picture.');return;}"
            "window._edgeCropWatchActive=true;"
            "function getBestSrc(el){"
            "if(el.currentSrc)return el.currentSrc;"
            "if(el.src)return el.src;"
            "if(el.getAttribute('data-src'))return el.getAttribute('data-src');"
            "if(el.getAttribute('data-original'))return el.getAttribute('data-original');"
            "if(el.srcset){var parts=el.srcset.split(',');var best=parts[parts.length-1].trim().split(' ')[0];if(best)return best;}"
            "var bg=window.getComputedStyle(el).backgroundImage;"
            "if(bg&&bg!=='none'&&bg.startsWith('url(')){return bg.slice(4,-1).replace(/[\"']/g,'');}"
            "return'';"
            "}"
            "var elements=document.querySelectorAll('img, picture img, [role=img], svg image, div[style*=\"background\"]');"
            "elements.forEach(function(el){"
            "var src=getBestSrc(el);"
            "if(!src)return;"
            "el.style.transition='outline 0.2s ease, transform 0.2s ease';"
            "el.style.outline='3px dashed #00e5ff';"
            "el.style.cursor='crosshair';"
            "el.title='⚡ Click to Send to Photo Cropper (Corey Kiesel)';"
            "el.addEventListener('click',function(e){"
            "e.preventDefault();e.stopPropagation();"
            "var targetSrc=getBestSrc(this);"
            "if(!targetSrc)return;"
            "this.style.outline='4px solid #00ff66';"
            "this.style.transform='scale(0.98)';"
            "var currentEl=this;"
            "fetch('http://127.0.0.1:59999/load?url='+encodeURIComponent(targetSrc))"
            ".then(function(){"
            "setTimeout(function(){currentEl.style.outline='3px dashed #00e5ff';currentEl.style.transform='scale(1)';},500);"
            "}).catch(function(err){"
            "alert('Could not connect to Cropper App. Make sure main.py is running!');"
            "});"
            "},true);"
            "});"
            "var toast=document.createElement('div');"
            "toast.innerHTML='🎯 <b>Edge Photo Watch Active!</b><br>Click any picture to crop & save.'; "
            "toast.style='position:fixed;top:20px;right:20px;z-index:9999999;background:#1f6feb;color:#ffffff;padding:14px 20px;border-radius:10px;font-family:sans-serif;box-shadow:0 6px 20px rgba(0,0,0,0.5);font-size:14px;line-height:1.4;';"
            "document.body.appendChild(toast);"
            "setTimeout(function(){toast.remove();},4000);"
            "})();"
        )

        raw_label = QLabel("Or paste this Bookmark URL manually into your Edge favorites:")
        raw_label.setStyleSheet("font-size: 11px; color: #8b949e; margin-top: 6px;")
        layout.addWidget(raw_label)

        self.code_edit = QTextEdit()
        self.code_edit.setPlainText(self.js_code)
        self.code_edit.setReadOnly(True)
        self.code_edit.setFixedHeight(75)
        layout.addWidget(self.code_edit)

        bottom_row = QHBoxLayout()
        close_btn = QPushButton("Done / Close")
        close_btn.clicked.connect(self.accept)
        bottom_row.addStretch()
        bottom_row.addWidget(close_btn)
        layout.addLayout(bottom_row)

    def openExtensionFolder(self):
        try:
            ext_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "extension")
            if os.path.exists(ext_folder):
                open_path(ext_folder)
            else:
                QMessageBox.warning(self, "Folder Not Found", f"Extension folder not found at: {ext_folder}")
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

    def openSetupInEdge(self):
        try:
            helper_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "edge_bookmark_helper.html")
            if os.path.exists(helper_path):
                open_path(helper_path)
            else:
                QMessageBox.warning(self, "File Not Found", f"Helper HTML not found at: {helper_path}")
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

    def copyScript(self):
        try:
            QGuiApplication.clipboard().setText(self.js_code)
            QMessageBox.information(
                self, 
                "Copied!", 
                "Bookmarklet code copied to clipboard!\n\nYou can create a new Favorite in Edge and paste this as the URL."
            )
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))


class PrintScalingOptions:
    FIT_PAGE = "fit_page"
    FILL_PAGE = "fill_page"
    ACTUAL_SIZE = "actual_size"
    CUSTOM_PERCENT = "custom_percent"
    PRESET_SIZE = "preset_size"
    CUSTOM_DIMENSIONS = "custom_dimensions"

    def __init__(self):
        self.scale_mode = self.FIT_PAGE
        self.custom_percent = 100.0
        self.preset_size = "4\" × 6\" (Standard Photo)"
        self.custom_w_in = 4.0
        self.custom_h_in = 6.0
        self.lock_aspect = True
        self.dpi_mode = 300
        
        self.align_h = "center"   # "left", "center", "right"
        self.align_v = "center"   # "top", "center", "bottom"
        self.offset_x_in = 0.0
        self.offset_y_in = 0.0
        
        self.orientation = "auto" # "auto", "portrait", "landscape"
        self.margin_mode = "normal" # "normal" (0.5"), "narrow" (0.25"), "none" (0.0"), "custom"
        self.custom_margin_in = 0.5
        
        self.border_style = "none" # "none", "thin", "medium", "thick", "mat_white", "mat_black"
        self.border_width_pt = 1
        self.border_color = "#000000"


PHOTO_PRESETS = {
    "4\" × 6\" (Standard Photo)": (4.0, 6.0),
    "5\" × 7\" (Photo Print)": (5.0, 7.0),
    "8\" × 10\" (Portrait / Frame)": (8.0, 10.0),
    "8.5\" × 11\" (US Letter Full)": (8.5, 11.0),
    "A4 (8.27\" × 11.69\")": (8.27, 11.69),
    "2.5\" × 3.5\" (Wallet Size)": (2.5, 3.5),
    "2\" × 2\" (Passport / ID)": (2.0, 2.0),
    "4\" × 4\" (Square Print)": (4.0, 4.0),
    "5\" × 5\" (Square Print)": (5.0, 5.0),
    "8\" × 8\" (Square Print)": (8.0, 8.0)
}


def renderScaledPhoto(painter: QPainter, page_rect_px: QRect, full_rect_px: QRect, dpi: int, pixmap: QPixmap, options: PrintScalingOptions) -> dict:
    """
    Universally renders a pixmap to any QPainter target (Printer, Preview Dialog, or Widget Preview)
    with complete scaling, margins, alignment, offsets, orientation, and borders.
    """
    if not pixmap or pixmap.isNull() or not painter:
        return {}

    dpi = max(72, int(dpi))
    img_w = max(1, pixmap.width())
    img_h = max(1, pixmap.height())

    # Determine effective printable bounds based on margin mode
    if options.margin_mode == "none":
        bounds = QRect(full_rect_px)
    elif options.margin_mode == "narrow":
        m_px = int(0.25 * dpi)
        bounds = full_rect_px.adjusted(m_px, m_px, -m_px, -m_px)
    elif options.margin_mode == "normal":
        m_px = int(0.5 * dpi)
        bounds = full_rect_px.adjusted(m_px, m_px, -m_px, -m_px)
    elif options.margin_mode == "custom":
        m_px = int(max(0.0, options.custom_margin_in) * dpi)
        bounds = full_rect_px.adjusted(m_px, m_px, -m_px, -m_px)
    else:
        bounds = QRect(page_rect_px)

    if bounds.width() < 10 or bounds.height() < 10:
        bounds = QRect(full_rect_px)

    target_w = bounds.width()
    target_h = bounds.height()

    # Calculate Draw Dimensions
    if options.scale_mode == PrintScalingOptions.FIT_PAGE:
        scale = min(target_w / img_w, target_h / img_h)
        draw_w = img_w * scale
        draw_h = img_h * scale
        scale_pct = (scale / (min(target_w / img_w, target_h / img_h))) * 100.0

    elif options.scale_mode == PrintScalingOptions.FILL_PAGE:
        scale = max(target_w / img_w, target_h / img_h)
        draw_w = img_w * scale
        draw_h = img_h * scale
        scale_pct = (scale / (min(target_w / img_w, target_h / img_h))) * 100.0

    elif options.scale_mode == PrintScalingOptions.ACTUAL_SIZE:
        effective_dpi = float(options.dpi_mode if options.dpi_mode > 0 else 300)
        scale = dpi / effective_dpi
        draw_w = img_w * scale
        draw_h = img_h * scale
        fit_scale = min(target_w / img_w, target_h / img_h)
        scale_pct = (scale / fit_scale) * 100.0 if fit_scale > 0 else 100.0

    elif options.scale_mode == PrintScalingOptions.CUSTOM_PERCENT:
        fit_scale = min(target_w / img_w, target_h / img_h)
        scale = fit_scale * (options.custom_percent / 100.0)
        draw_w = img_w * scale
        draw_h = img_h * scale
        scale_pct = options.custom_percent

    elif options.scale_mode == PrintScalingOptions.PRESET_SIZE:
        preset_w_in, preset_h_in = PHOTO_PRESETS.get(options.preset_size, (4.0, 6.0))
        # Auto-match orientation of preset to image orientation
        if (img_w > img_h and preset_w_in < preset_h_in) or (img_w < img_h and preset_w_in > preset_h_in):
            preset_w_in, preset_h_in = preset_h_in, preset_w_in
        
        pw_px = preset_w_in * dpi
        ph_px = preset_h_in * dpi
        if options.lock_aspect:
            scale = min(pw_px / img_w, ph_px / img_h)
            draw_w = img_w * scale
            draw_h = img_h * scale
        else:
            draw_w = pw_px
            draw_h = ph_px
        fit_scale = min(target_w / img_w, target_h / img_h)
        scale_pct = ((draw_w / img_w) / fit_scale) * 100.0 if fit_scale > 0 else 100.0

    elif options.scale_mode == PrintScalingOptions.CUSTOM_DIMENSIONS:
        cw_px = max(0.1, options.custom_w_in) * dpi
        ch_px = max(0.1, options.custom_h_in) * dpi
        if options.lock_aspect:
            scale = min(cw_px / img_w, ch_px / img_h)
            draw_w = img_w * scale
            draw_h = img_h * scale
        else:
            draw_w = cw_px
            draw_h = ch_px
        fit_scale = min(target_w / img_w, target_h / img_h)
        scale_pct = ((draw_w / img_w) / fit_scale) * 100.0 if fit_scale > 0 else 100.0
    else:
        scale = min(target_w / img_w, target_h / img_h)
        draw_w = img_w * scale
        draw_h = img_h * scale
        scale_pct = 100.0

    # Calculate Alignment Position
    off_x = options.offset_x_in * dpi
    off_y = options.offset_y_in * dpi

    if options.align_h == "left":
        x = bounds.left() + off_x
    elif options.align_h == "right":
        x = bounds.right() - draw_w - off_x
    else: # center
        x = bounds.left() + (bounds.width() - draw_w) / 2.0 + off_x

    if options.align_v == "top":
        y = bounds.top() + off_y
    elif options.align_v == "bottom":
        y = bounds.bottom() - draw_h - off_y
    else: # center
        y = bounds.top() + (bounds.height() - draw_h) / 2.0 + off_y

    dest_rect = QRectF(x, y, draw_w, draw_h)

    # Render Image
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

    if options.scale_mode == PrintScalingOptions.FILL_PAGE:
        # Clip strictly to printable bounds so fill doesn't overflow page margins
        painter.setClipRect(bounds)
        painter.drawPixmap(dest_rect.toRect(), pixmap)
    else:
        painter.drawPixmap(dest_rect.toRect(), pixmap)

    # Render Optional Border / Mat
    if options.border_style != "none":
        b_width_px = max(1, int(options.border_width_pt * (dpi / 72.0)))
        if options.border_style == "thin":
            painter.setPen(QPen(QColor(options.border_color), max(1, int(1 * dpi / 72.0))))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(dest_rect)
        elif options.border_style == "medium":
            painter.setPen(QPen(QColor(options.border_color), max(2, int(2.5 * dpi / 72.0))))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(dest_rect)
        elif options.border_style == "thick":
            painter.setPen(QPen(QColor(options.border_color), max(4, int(5 * dpi / 72.0))))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(dest_rect)
        elif options.border_style == "mat_white":
            mat_px = int(0.25 * dpi)
            mat_rect = dest_rect.adjusted(-mat_px, -mat_px, mat_px, mat_px)
            painter.setPen(QPen(QColor("#d0d0d0"), 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(mat_rect)
        elif options.border_style == "mat_black":
            mat_px = int(0.15 * dpi)
            mat_rect = dest_rect.adjusted(-mat_px, -mat_px, mat_px, mat_px)
            painter.setPen(QPen(QColor("#000000"), max(2, int(2 * dpi / 72.0))))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(mat_rect)

    painter.restore()

    return {
        "draw_w_px": draw_w,
        "draw_h_px": draw_h,
        "draw_w_in": draw_w / dpi,
        "draw_h_in": draw_h / dpi,
        "scale_pct": scale_pct,
        "dest_rect": dest_rect,
        "bounds": bounds,
        "dpi": dpi
    }


class PrintPaperPreviewWidget(QWidget):
    """
    Interactive Paper Sheet Preview Widget that simulates real physical paper,
    margins, scaling, and positioning in real-time.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.pixmap = QPixmap()
        self.options = PrintScalingOptions()
        self.dpi = 150 # Simulated DPI for high fidelity preview
        self.paper_w_in = 8.5
        self.paper_h_in = 11.0
        self.zoom_factor = 1.0
        self.last_render_info = {}
        self.setMinimumSize(320, 420)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet("background-color: #090d13; border-radius: 8px;")

    def updateState(self, pixmap: QPixmap, options: PrintScalingOptions):
        self.pixmap = pixmap
        self.options = options
        
        # Calculate effective paper orientation
        img_w = pixmap.width() if pixmap and not pixmap.isNull() else 1
        img_h = pixmap.height() if pixmap and not pixmap.isNull() else 1
        
        if options.orientation == "portrait":
            self.paper_w_in, self.paper_h_in = 8.5, 11.0
        elif options.orientation == "landscape":
            self.paper_w_in, self.paper_h_in = 11.0, 8.5
        else: # auto
            if img_w > img_h:
                self.paper_w_in, self.paper_h_in = 11.0, 8.5
            else:
                self.paper_w_in, self.paper_h_in = 8.5, 11.0
                
        self.update()

    def setZoom(self, zoom: float):
        self.zoom_factor = max(0.4, min(3.0, zoom))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        painter.fillRect(self.rect(), QColor("#090d13"))

        if not self.pixmap or self.pixmap.isNull():
            painter.setPen(QColor("#8b949e"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No Photo to Preview")
            return

        # Dimensions of simulated paper sheet in screen pixels
        avail_w = self.width() - 40
        avail_h = self.height() - 40
        
        paper_aspect = self.paper_w_in / self.paper_h_in
        if (avail_w / max(1, avail_h)) > paper_aspect:
            sheet_h = int(avail_h * self.zoom_factor)
            sheet_w = int(sheet_h * paper_aspect)
        else:
            sheet_w = int(avail_w * self.zoom_factor)
            sheet_h = int(sheet_w / paper_aspect)

        sheet_x = (self.width() - sheet_w) // 2
        sheet_y = (self.height() - sheet_h) // 2
        sheet_rect = QRect(sheet_x, sheet_y, sheet_w, sheet_h)

        # Draw Paper Drop Shadow
        shadow_rect = sheet_rect.adjusted(-4, -4, 6, 6)
        painter.fillRect(shadow_rect, QColor(0, 0, 0, 110))

        # Draw White Paper Sheet
        painter.fillRect(sheet_rect, QColor("#ffffff"))
        painter.setPen(QPen(QColor("#d0d7de"), 1))
        painter.drawRect(sheet_rect)

        # Calculate simulated DPI on sheet
        sim_dpi = sheet_w / self.paper_w_in
        full_px = QRect(0, 0, sheet_w, sheet_h)
        
        # Printable area inside sheet
        m_sim = int(0.5 * sim_dpi)
        page_px = full_px.adjusted(m_sim, m_sim, -m_sim, -m_sim)

        # Render Photo onto Sheet using universal renderer
        painter.save()
        painter.translate(sheet_x, sheet_y)

        # Draw Margin Guideline (subtle dashed blue line)
        if self.options.margin_mode != "none":
            guide_m = int((0.25 if self.options.margin_mode == "narrow" else self.options.custom_margin_in if self.options.margin_mode == "custom" else 0.5) * sim_dpi)
            guide_rect = full_px.adjusted(guide_m, guide_m, -guide_m, -guide_m)
            guide_pen = QPen(QColor("#0969da"), 1, Qt.PenStyle.DashLine)
            painter.setPen(guide_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(guide_rect)

        self.last_render_info = renderScaledPhoto(
            painter, 
            page_px, 
            full_px, 
            sim_dpi, 
            self.pixmap, 
            self.options
        )
        painter.restore()

        # Paper size label overlay
        painter.setPen(QColor("#7d8590"))
        painter.setFont(QFont("Segoe UI", 9))
        orientation_str = "Landscape" if self.paper_w_in > self.paper_h_in else "Portrait"
        paper_label = f"📄 Standard Sheet ({self.paper_w_in}\" × {self.paper_h_in}\" {orientation_str})"
        painter.drawText(QRect(10, self.height() - 25, self.width() - 20, 20), Qt.AlignmentFlag.AlignLeft, paper_label)


class PrintScalingDialog(QDialog):
    """
    Comprehensive Print & Scaling Control Center with interactive real-time preview,
    preset photo sizes, percentage scaling, margin controls, and direct print actions.
    """
    def __init__(self, pixmap: QPixmap, parent=None):
        super().__init__(parent)
        self.pixmap = pixmap
        self.options = PrintScalingOptions()
        self.setWindowTitle("🖨️ Print & Scaling Settings - Corey Kiesel")
        self.resize(1020, 720)
        self.setMinimumSize(880, 600)
        
        self.applyStyle()
        self.initUI()
        self.updatePreview()

    def applyStyle(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #0d1117;
                color: #c9d1d9;
                font-family: 'Segoe UI', sans-serif;
            }
            QLabel {
                color: #c9d1d9;
            }
            QGroupBox {
                border: 1px solid #30363d;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 14px;
                font-weight: bold;
                color: #58a6ff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
            }
            QRadioButton {
                color: #c9d1d9;
                spacing: 6px;
                font-size: 12px;
            }
            QRadioButton:hover {
                color: #ffffff;
            }
            QRadioButton::indicator:checked {
                background-color: #58a6ff;
                border: 2px solid #ffffff;
                border-radius: 6px;
            }
            QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 6px 10px;
                color: #f0f6fc;
            }
            QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover {
                border-color: #58a6ff;
            }
            QSlider::groove:horizontal {
                height: 6px;
                background: #21262d;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: #1f6feb;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #58a6ff;
                border: 1px solid #ffffff;
                width: 14px;
                margin-top: -4px;
                margin-bottom: -4px;
                border-radius: 7px;
            }
            QPushButton {
                background-color: #21262d;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 8px 14px;
                color: #c9d1d9;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #30363d;
                color: #ffffff;
            }
            #btnPrimary {
                background-color: #238636;
                border: 1px solid #2ea043;
                color: #ffffff;
                font-weight: bold;
            }
            #btnPrimary:hover {
                background-color: #2ea043;
            }
            #btnPrintSpecial {
                background: linear-gradient(135deg, #8957e5, #1f6feb);
                border: 1px solid #8957e5;
                color: #ffffff;
                font-weight: bold;
                font-size: 13px;
            }
            #btnPrintSpecial:hover {
                background: linear-gradient(135deg, #a371f7, #388bfd);
            }
            QTabWidget::pane {
                border: 1px solid #30363d;
                border-radius: 6px;
                background-color: #161b22;
                padding: 10px;
            }
            QTabBar::tab {
                background: #0d1117;
                border: 1px solid #30363d;
                border-bottom: none;
                color: #8b949e;
                padding: 8px 16px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 4px;
            }
            QTabBar::tab:selected {
                background: #161b22;
                color: #58a6ff;
                font-weight: bold;
                border-bottom: 2px solid #58a6ff;
            }
        """)

    def initUI(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(10)

        # Top Header Banner
        header = QHBoxLayout()
        header_title = QLabel("🖨️ Photo Print & Universal Scaling Studio")
        header_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #58a6ff;")
        header.addWidget(header_title)

        author_tag = QLabel("👤 Created by Corey Kiesel")
        author_tag.setStyleSheet("color: #d2a8ff; font-weight: bold;")
        header.addWidget(author_tag, alignment=Qt.AlignmentFlag.AlignRight)
        main_layout.addLayout(header)

        # Split Content: Left (Preview) vs Right (Controls)
        content_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left Pane: Real-time Paper Preview
        left_box = QFrame()
        left_layout = QVBoxLayout(left_box)
        left_layout.setContentsMargins(0, 0, 8, 0)
        left_layout.setSpacing(8)

        preview_header = QHBoxLayout()
        preview_title = QLabel("👁️ Live Sheet Print Preview")
        preview_title.setStyleSheet("font-weight: bold; color: #7ee787;")
        preview_header.addWidget(preview_title)

        # Zoom Controls for Preview
        zoom_row = QHBoxLayout()
        zoom_row.addWidget(QLabel("Zoom:"))
        self.slider_zoom = QSlider(Qt.Orientation.Horizontal)
        self.slider_zoom.setRange(50, 200)
        self.slider_zoom.setValue(100)
        self.slider_zoom.setFixedWidth(100)
        self.slider_zoom.valueChanged.connect(lambda v: self.preview_canvas.setZoom(v / 100.0))
        zoom_row.addWidget(self.slider_zoom)
        preview_header.addLayout(zoom_row)
        left_layout.addLayout(preview_header)

        self.preview_canvas = PrintPaperPreviewWidget(self)
        left_layout.addWidget(self.preview_canvas, stretch=1)

        # Dimension and Scaling Info Badge
        self.info_badge = QLabel("📐 Print Dimensions: Calculating...")
        self.info_badge.setStyleSheet("background-color: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 8px; font-size: 12px; color: #79c0ff; font-weight: 500;")
        self.info_badge.setWordWrap(True)
        left_layout.addWidget(self.info_badge)

        content_splitter.addWidget(left_box)

        # Right Pane: Scaling & Layout Options Tabbed Widget
        right_box = QFrame()
        right_layout = QVBoxLayout(right_box)
        right_layout.setContentsMargins(8, 0, 0, 0)
        right_layout.setSpacing(8)

        self.tabs = QTabWidget()

        # Tab 1: 📐 Scaling Modes & Dimensions
        tab_scaling = QWidget()
        tab_scale_layout = QVBoxLayout(tab_scaling)
        tab_scale_layout.setSpacing(12)

        scale_group = QGroupBox("Select Scaling Mode")
        scale_group_layout = QVBoxLayout(scale_group)
        scale_group_layout.setSpacing(10)

        self.rb_fit = QRadioButton("🎯 Fit to Printable Page (Maintain Aspect Ratio)")
        self.rb_fit.setChecked(True)
        self.rb_fit.toggled.connect(self.onScalingModeChanged)
        scale_group_layout.addWidget(self.rb_fit)

        self.rb_fill = QRadioButton("🖼️ Fill Entire Page / Bleed (Crop to fill margins)")
        self.rb_fill.toggled.connect(self.onScalingModeChanged)
        scale_group_layout.addWidget(self.rb_fill)

        # Actual Size Row
        actual_box = QWidget()
        actual_layout = QHBoxLayout(actual_box)
        actual_layout.setContentsMargins(0, 0, 0, 0)
        self.rb_actual = QRadioButton("🔍 100% Original Actual Pixel Size @")
        self.rb_actual.toggled.connect(self.onScalingModeChanged)
        actual_layout.addWidget(self.rb_actual)
        self.combo_dpi = QComboBox()
        self.combo_dpi.addItems(["300 DPI (Photo Quality)", "600 DPI (High Res)", "150 DPI (Draft)", "96 DPI (Screen Standard)"])
        self.combo_dpi.currentIndexChanged.connect(self.onScalingModeChanged)
        actual_layout.addWidget(self.combo_dpi)
        scale_group_layout.addWidget(actual_box)

        # Custom Scale Percentage Row
        percent_box = QWidget()
        percent_layout = QVBoxLayout(percent_box)
        percent_layout.setContentsMargins(0, 0, 0, 0)
        percent_layout.setSpacing(4)
        
        pct_head = QHBoxLayout()
        self.rb_percent = QRadioButton("📊 Custom Scale Percentage:")
        self.rb_percent.toggled.connect(self.onScalingModeChanged)
        pct_head.addWidget(self.rb_percent)
        
        self.spin_percent = QDoubleSpinBox()
        self.spin_percent.setRange(5.0, 500.0)
        self.spin_percent.setValue(100.0)
        self.spin_percent.setSuffix(" %")
        self.spin_percent.setSingleStep(5.0)
        self.spin_percent.valueChanged.connect(self.onPercentSpinChanged)
        pct_head.addWidget(self.spin_percent)
        percent_layout.addLayout(pct_head)

        pct_slider_row = QHBoxLayout()
        self.slider_percent = QSlider(Qt.Orientation.Horizontal)
        self.slider_percent.setRange(10, 300)
        self.slider_percent.setValue(100)
        self.slider_percent.valueChanged.connect(self.onPercentSliderChanged)
        pct_slider_row.addWidget(self.slider_percent)
        percent_layout.addLayout(pct_slider_row)

        # Quick Preset Buttons
        quick_btn_row = QHBoxLayout()
        quick_btn_row.setSpacing(4)
        for pct_val in [25, 50, 75, 100, 150, 200]:
            btn = QPushButton(f"{pct_val}%")
            btn.setFixedHeight(24)
            btn.setStyleSheet("padding: 2px 6px; font-size: 11px;")
            btn.clicked.connect(lambda _, p=pct_val: self.setQuickPercent(p))
            quick_btn_row.addWidget(btn)
        percent_layout.addLayout(quick_btn_row)
        scale_group_layout.addWidget(percent_box)

        # Standard Photo Presets Row
        preset_box = QWidget()
        preset_layout = QHBoxLayout(preset_box)
        preset_layout.setContentsMargins(0, 0, 0, 0)
        self.rb_preset = QRadioButton("📏 Standard Photo Preset:")
        self.rb_preset.toggled.connect(self.onScalingModeChanged)
        preset_layout.addWidget(self.rb_preset)
        self.combo_presets = QComboBox()
        self.combo_presets.addItems(list(PHOTO_PRESETS.keys()))
        self.combo_presets.currentTextChanged.connect(self.onScalingModeChanged)
        preset_layout.addWidget(self.combo_presets)
        scale_group_layout.addWidget(preset_box)

        # Custom Width / Height Dimensions Row
        custom_dim_box = QWidget()
        custom_dim_layout = QVBoxLayout(custom_dim_box)
        custom_dim_layout.setContentsMargins(0, 0, 0, 0)
        custom_dim_layout.setSpacing(4)

        dim_head = QHBoxLayout()
        self.rb_custom_dim = QRadioButton("📐 Specific Dimensions (Inches):")
        self.rb_custom_dim.toggled.connect(self.onScalingModeChanged)
        dim_head.addWidget(self.rb_custom_dim)
        custom_dim_layout.addLayout(dim_head)

        dim_inputs = QHBoxLayout()
        dim_inputs.addWidget(QLabel("W:"))
        self.spin_dim_w = QDoubleSpinBox()
        self.spin_dim_w.setRange(0.5, 30.0)
        self.spin_dim_w.setValue(4.0)
        self.spin_dim_w.setSuffix(' "')
        self.spin_dim_w.valueChanged.connect(self.onCustomDimChanged)
        dim_inputs.addWidget(self.spin_dim_w)

        dim_inputs.addWidget(QLabel("× H:"))
        self.spin_dim_h = QDoubleSpinBox()
        self.spin_dim_h.setRange(0.5, 30.0)
        self.spin_dim_h.setValue(6.0)
        self.spin_dim_h.setSuffix(' "')
        self.spin_dim_h.valueChanged.connect(self.onCustomDimChanged)
        dim_inputs.addWidget(self.spin_dim_h)

        self.chk_lock_aspect = QCheckBox("🔒 Lock Aspect Ratio")
        self.chk_lock_aspect.setChecked(True)
        self.chk_lock_aspect.toggled.connect(self.onCustomDimChanged)
        dim_inputs.addWidget(self.chk_lock_aspect)
        custom_dim_layout.addLayout(dim_inputs)

        scale_group_layout.addWidget(custom_dim_box)
        tab_scale_layout.addWidget(scale_group)
        tab_scale_layout.addStretch()
        self.tabs.addTab(tab_scaling, "📐 Scaling & Sizes")

        # Tab 2: 🧭 Positioning & Margins
        tab_position = QWidget()
        tab_pos_layout = QVBoxLayout(tab_position)
        tab_pos_layout.setSpacing(12)

        align_group = QGroupBox("Page Alignment (9-Point Grid)")
        align_grid = QGridLayout(align_group)
        align_grid.setSpacing(6)

        self.align_buttons = {}
        align_defs = [
            ("↖ Top-Left", "left", "top", 0, 0),
            ("⬆ Top-Center", "center", "top", 0, 1),
            ("↗ Top-Right", "right", "top", 0, 2),
            ("⬅ Center-Left", "left", "center", 1, 0),
            ("⏺ Center (Default)", "center", "center", 1, 1),
            ("➡ Center-Right", "right", "center", 1, 2),
            ("↙ Bottom-Left", "left", "bottom", 2, 0),
            ("⬇ Bottom-Center", "center", "bottom", 2, 1),
            ("↘ Bottom-Right", "right", "bottom", 2, 2)
        ]

        for label, h, v, r, c in align_defs:
            btn = QPushButton(label)
            btn.setCheckable(True)
            if h == "center" and v == "center":
                btn.setChecked(True)
            btn.clicked.connect(lambda _, ah=h, av=v: self.setAlignment(ah, av))
            align_grid.addWidget(btn, r, c)
            self.align_buttons[(h, v)] = btn

        tab_pos_layout.addWidget(align_group)

        # Nudge Offset Box
        nudge_group = QGroupBox("Fine Position Offsets (Nudge)")
        nudge_layout = QHBoxLayout(nudge_group)
        nudge_layout.addWidget(QLabel("X Offset:"))
        self.spin_off_x = QDoubleSpinBox()
        self.spin_off_x.setRange(-5.0, 5.0)
        self.spin_off_x.setValue(0.0)
        self.spin_off_x.setSingleStep(0.1)
        self.spin_off_x.setSuffix(' "')
        self.spin_off_x.valueChanged.connect(self.onOffsetChanged)
        nudge_layout.addWidget(self.spin_off_x)

        nudge_layout.addWidget(QLabel("Y Offset:"))
        self.spin_off_y = QDoubleSpinBox()
        self.spin_off_y.setRange(-5.0, 5.0)
        self.spin_off_y.setValue(0.0)
        self.spin_off_y.setSingleStep(0.1)
        self.spin_off_y.setSuffix(' "')
        self.spin_off_y.valueChanged.connect(self.onOffsetChanged)
        nudge_layout.addWidget(self.spin_off_y)

        reset_nudge_btn = QPushButton("Reset to 0")
        reset_nudge_btn.clicked.connect(self.resetNudge)
        nudge_layout.addWidget(reset_nudge_btn)

        tab_pos_layout.addWidget(nudge_group)
        tab_pos_layout.addStretch()
        self.tabs.addTab(tab_position, "🧭 Alignment & Position")

        # Tab 3: 📄 Page, Margins & Borders
        tab_page = QWidget()
        tab_page_layout = QVBoxLayout(tab_page)
        tab_page_layout.setSpacing(12)

        orient_group = QGroupBox("Paper Orientation")
        orient_layout = QHBoxLayout(orient_group)
        self.rb_orient_auto = QRadioButton("🔄 Auto Detect (Recommended)")
        self.rb_orient_auto.setChecked(True)
        self.rb_orient_auto.toggled.connect(self.onOrientationChanged)
        orient_layout.addWidget(self.rb_orient_auto)

        self.rb_orient_port = QRadioButton("📱 Force Portrait")
        self.rb_orient_port.toggled.connect(self.onOrientationChanged)
        orient_layout.addWidget(self.rb_orient_port)

        self.rb_orient_land = QRadioButton("🖥️ Force Landscape")
        self.rb_orient_land.toggled.connect(self.onOrientationChanged)
        orient_layout.addWidget(self.rb_orient_land)
        tab_page_layout.addWidget(orient_group)

        margin_group = QGroupBox("Page Margins")
        margin_layout = QHBoxLayout(margin_group)
        self.combo_margins = QComboBox()
        self.combo_margins.addItems([
            "Normal (0.5\" / 12.7 mm)",
            "Narrow (0.25\" / 6.35 mm)",
            "None / Borderless (0.0\")",
            "Custom Margin"
        ])
        self.combo_margins.currentIndexChanged.connect(self.onMarginChanged)
        margin_layout.addWidget(self.combo_margins)

        self.spin_custom_margin = QDoubleSpinBox()
        self.spin_custom_margin.setRange(0.0, 3.0)
        self.spin_custom_margin.setValue(0.5)
        self.spin_custom_margin.setSuffix(' "')
        self.spin_custom_margin.setEnabled(False)
        self.spin_custom_margin.valueChanged.connect(self.onCustomMarginSpinChanged)
        margin_layout.addWidget(self.spin_custom_margin)
        tab_page_layout.addWidget(margin_group)

        border_group = QGroupBox("Photo Frame / Border")
        border_layout = QHBoxLayout(border_group)
        border_layout.addWidget(QLabel("Style:"))
        self.combo_border = QComboBox()
        self.combo_border.addItems([
            "None (Clean Photo)",
            "Thin Line Border (1pt)",
            "Medium Frame (2.5pt)",
            "Thick Border (5pt)",
            "White Photo Mat",
            "Classic Black Frame"
        ])
        self.combo_border.currentIndexChanged.connect(self.onBorderChanged)
        border_layout.addWidget(self.combo_border)
        tab_page_layout.addWidget(border_group)

        tab_page_layout.addStretch()
        self.tabs.addTab(tab_page, "📄 Page, Margins & Borders")

        right_layout.addWidget(self.tabs, stretch=1)
        content_splitter.addWidget(right_box)
        content_splitter.setSizes([460, 540])
        main_layout.addWidget(content_splitter, stretch=1)

        # Bottom Action Buttons Bar
        bottom_bar = QHBoxLayout()
        bottom_bar.setSpacing(10)

        self.btn_preview_sys = QPushButton("👁️ System Print Preview")
        self.btn_preview_sys.clicked.connect(self.onLaunchPrintPreview)
        bottom_bar.addWidget(self.btn_preview_sys)

        self.btn_export_pdf = QPushButton("💾 Export to PDF...")
        self.btn_export_pdf.clicked.connect(self.onExportPDF)
        bottom_bar.addWidget(self.btn_export_pdf)

        bottom_bar.addStretch()

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        bottom_bar.addWidget(self.btn_cancel)

        self.btn_print = QPushButton("🖨️ Print Now...")
        self.btn_print.setObjectName("btnPrintSpecial")
        self.btn_print.clicked.connect(self.onExecutePrint)
        bottom_bar.addWidget(self.btn_print)

        main_layout.addLayout(bottom_bar)

    # UI Event Handlers
    def onScalingModeChanged(self):
        if self.rb_fit.isChecked():
            self.options.scale_mode = PrintScalingOptions.FIT_PAGE
        elif self.rb_fill.isChecked():
            self.options.scale_mode = PrintScalingOptions.FILL_PAGE
        elif self.rb_actual.isChecked():
            self.options.scale_mode = PrintScalingOptions.ACTUAL_SIZE
            dpi_txt = self.combo_dpi.currentText()
            if "600" in dpi_txt:
                self.options.dpi_mode = 600
            elif "150" in dpi_txt:
                self.options.dpi_mode = 150
            elif "96" in dpi_txt:
                self.options.dpi_mode = 96
            else:
                self.options.dpi_mode = 300
        elif self.rb_percent.isChecked():
            self.options.scale_mode = PrintScalingOptions.CUSTOM_PERCENT
            self.options.custom_percent = self.spin_percent.value()
        elif self.rb_preset.isChecked():
            self.options.scale_mode = PrintScalingOptions.PRESET_SIZE
            self.options.preset_size = self.combo_presets.currentText()
        elif self.rb_custom_dim.isChecked():
            self.options.scale_mode = PrintScalingOptions.CUSTOM_DIMENSIONS
            self.options.custom_w_in = self.spin_dim_w.value()
            self.options.custom_h_in = self.spin_dim_h.value()
            self.options.lock_aspect = self.chk_lock_aspect.isChecked()

        self.updatePreview()

    def onPercentSpinChanged(self, val):
        self.slider_percent.blockSignals(True)
        self.slider_percent.setValue(int(val))
        self.slider_percent.blockSignals(False)
        self.rb_percent.setChecked(True)
        self.options.custom_percent = val
        self.options.scale_mode = PrintScalingOptions.CUSTOM_PERCENT
        self.updatePreview()

    def onPercentSliderChanged(self, val):
        self.spin_percent.blockSignals(True)
        self.spin_percent.setValue(float(val))
        self.spin_percent.blockSignals(False)
        self.rb_percent.setChecked(True)
        self.options.custom_percent = float(val)
        self.options.scale_mode = PrintScalingOptions.CUSTOM_PERCENT
        self.updatePreview()

    def setQuickPercent(self, pct):
        self.spin_percent.setValue(float(pct))
        self.onPercentSpinChanged(float(pct))

    def onCustomDimChanged(self):
        self.rb_custom_dim.setChecked(True)
        self.options.scale_mode = PrintScalingOptions.CUSTOM_DIMENSIONS
        self.options.custom_w_in = self.spin_dim_w.value()
        self.options.custom_h_in = self.spin_dim_h.value()
        self.options.lock_aspect = self.chk_lock_aspect.isChecked()
        self.updatePreview()

    def setAlignment(self, h, v):
        self.options.align_h = h
        self.options.align_v = v
        for (bh, bv), btn in self.align_buttons.items():
            btn.setChecked(bh == h and bv == v)
        self.updatePreview()

    def onOffsetChanged(self):
        self.options.offset_x_in = self.spin_off_x.value()
        self.options.offset_y_in = self.spin_off_y.value()
        self.updatePreview()

    def resetNudge(self):
        self.spin_off_x.setValue(0.0)
        self.spin_off_y.setValue(0.0)

    def onOrientationChanged(self):
        if self.rb_orient_port.isChecked():
            self.options.orientation = "portrait"
        elif self.rb_orient_land.isChecked():
            self.options.orientation = "landscape"
        else:
            self.options.orientation = "auto"
        self.updatePreview()

    def onMarginChanged(self, index):
        if index == 0:
            self.options.margin_mode = "normal"
            self.spin_custom_margin.setEnabled(False)
        elif index == 1:
            self.options.margin_mode = "narrow"
            self.spin_custom_margin.setEnabled(False)
        elif index == 2:
            self.options.margin_mode = "none"
            self.spin_custom_margin.setEnabled(False)
        else:
            self.options.margin_mode = "custom"
            self.spin_custom_margin.setEnabled(True)
            self.options.custom_margin_in = self.spin_custom_margin.value()
        self.updatePreview()

    def onCustomMarginSpinChanged(self, val):
        self.options.custom_margin_in = val
        self.updatePreview()

    def onBorderChanged(self, index):
        borders = ["none", "thin", "medium", "thick", "mat_white", "mat_black"]
        if index < len(borders):
            self.options.border_style = borders[index]
        self.updatePreview()

    def updatePreview(self):
        self.preview_canvas.updateState(self.pixmap, self.options)
        info = getattr(self.preview_canvas, 'last_render_info', {})
        if info:
            w_in = info.get('draw_w_in', 0.0)
            h_in = info.get('draw_h_in', 0.0)
            w_cm = w_in * 2.54
            h_cm = h_in * 2.54
            scale_pct = info.get('scale_pct', 100.0)
            mode_name = self.options.scale_mode.replace("_", " ").title()
            self.info_badge.setText(
                f"📐 <b>Print Dimensions:</b> {w_in:.2f}\" × {h_in:.2f}\" ({w_cm:.1f} × {h_cm:.1f} cm)  |  "
                f"<b>Scale:</b> {scale_pct:.1f}%  |  <b>Mode:</b> {mode_name}"
            )

    def onExecutePrint(self):
        try:
            if not HAS_PRINT_SUPPORT:
                QMessageBox.warning(self, "Printing Unavailable", "QtPrintSupport is not available.")
                return

            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            self.configurePrinterOrientation(printer)

            print_dialog = QPrintDialog(printer, self)
            print_dialog.setWindowTitle("🖨️ Print Photo - Corey Kiesel")

            if print_dialog.exec() == QDialog.DialogCode.Accepted:
                self.printToTarget(printer)
                self.accept()
        except Exception as e:
            QMessageBox.warning(self, "Print Error", str(e))

    def onLaunchPrintPreview(self):
        try:
            if not HAS_PRINT_SUPPORT:
                QMessageBox.warning(self, "Printing Unavailable", "QtPrintSupport is not available.")
                return

            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            self.configurePrinterOrientation(printer)

            preview = QPrintPreviewDialog(printer, self)
            preview.setWindowTitle("👁️ System Print Preview - Corey Kiesel")
            preview.paintRequested.connect(lambda p: self.printToTarget(p))
            preview.exec()
        except Exception as e:
            QMessageBox.warning(self, "Preview Error", str(e))

    def onExportPDF(self):
        try:
            file_path, _ = QFileDialog.getSaveFileName(self, "Save as PDF", "Photo_Print.pdf", "PDF Documents (*.pdf)")
            if not file_path:
                return

            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(file_path)
            self.configurePrinterOrientation(printer)

            self.printToTarget(printer)
            QMessageBox.information(self, "PDF Saved", f"Successfully exported PDF to:\n{file_path}")
        except Exception as e:
            QMessageBox.warning(self, "PDF Error", str(e))

    def configurePrinterOrientation(self, printer: QPrinter):
        if self.options.orientation == "portrait":
            printer.setPageOrientation(QPageLayout.Orientation.Portrait)
        elif self.options.orientation == "landscape":
            printer.setPageOrientation(QPageLayout.Orientation.Landscape)
        else: # auto
            if self.pixmap.width() > self.pixmap.height():
                printer.setPageOrientation(QPageLayout.Orientation.Landscape)
            else:
                printer.setPageOrientation(QPageLayout.Orientation.Portrait)

    def printToTarget(self, printer: QPrinter):
        painter = QPainter()
        if not painter.begin(printer):
            return
        try:
            dpi = printer.resolution()
            page_rect = printer.pageLayout().paintRectPixels(dpi)
            full_rect = printer.pageLayout().fullRectPixels(dpi)
            renderScaledPhoto(painter, page_rect, full_rect, dpi, self.pixmap, self.options)
        finally:
            if painter.isActive():
                painter.end()


class ModernMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Web Photo Quick Cropper, Saver & Printer - by Corey Kiesel")
        self.resize(1280, 840)
        self.setMinimumSize(960, 600)

        default_dir = os.path.join(os.path.expanduser("~"), "Pictures", "WebCrops")
        os.makedirs(default_dir, exist_ok=True)
        self.save_directory = default_dir
        
        self.history_items = []
        self.last_clipboard_text = ""

        self.thread_pool = QThreadPool.globalInstance()

        self.edge_server = EdgeServerThread(port=59999)
        self.edge_server.imageReceived.connect(self.onEdgeImageReceived)
        self.edge_server.start()

        self.clipboard = QGuiApplication.clipboard()
        self.clipboard.dataChanged.connect(self.onClipboardDataChangedDebounced)
        self.edge_watch_enabled = True
        
        self.clipboard_timer = QTimer(self)
        self.clipboard_timer.setSingleShot(True)
        self.clipboard_timer.timeout.connect(self.processClipboard)

        self.initUI()
        self.applyModernStyle()

        self.print_shortcut = QShortcut(QKeySequence("Ctrl+P"), self)
        self.print_shortcut.activated.connect(self.printSelectedPhoto)

        QTimer.singleShot(100, lambda: self.loadSampleImage("Landscape (800x600)"))

    def closeEvent(self, event):
        try:
            if self.edge_server:
                self.edge_server.stop()
        except Exception:
            pass
        super().closeEvent(event)

    def initUI(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(12, 12, 12, 8)
        main_layout.setSpacing(10)

        top_bar = self.createTopBar()
        main_layout.addWidget(top_bar)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        self.cropper = InteractiveCropper()
        self.cropper.cropCompleted.connect(self.onCropCompleted)
        self.cropper.mouseMovedOnImage.connect(self.onMouseMovedOnImage)
        self.cropper.statusMessage.connect(self.statusBar().showMessage)
        self.cropper.fileOrUrlDropped.connect(self.loadDroppedImage)
        splitter.addWidget(self.cropper)
        
        right_panel = self.createSidePanel()
        splitter.addWidget(right_panel)
        
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([850, 350])
        main_layout.addWidget(splitter)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        port_num = getattr(self.edge_server, 'port', 59999)
        self.edge_status_label = QLabel(f"🟢 Edge Plugin Active (Port {port_num})")
        self.edge_status_label.setStyleSheet("color: #7ee787; font-weight: bold; padding-right: 12px;")
        self.status_bar.addPermanentWidget(self.edge_status_label)

        self.author_label = QLabel("👤 Corey Kiesel")
        self.author_label.setStyleSheet("color: #d2a8ff; font-weight: bold; padding-right: 12px;")
        self.status_bar.addPermanentWidget(self.author_label)

        self.coord_label = QLabel("X: 0, Y: 0")
        self.coord_label.setStyleSheet("color: #8b949e; padding-right: 12px;")
        self.status_bar.addPermanentWidget(self.coord_label)

        self.img_info_label = QLabel("No Image")
        self.img_info_label.setStyleSheet("color: #58a6ff; font-weight: bold; padding-right: 12px;")
        self.status_bar.addPermanentWidget(self.img_info_label)

        self.status_bar.showMessage("Ready. Select crop area, or press '🖨️ Print Selected Photo' (Ctrl+P).")

    def createTopBar(self) -> QWidget:
        container = QFrame()
        container.setObjectName("topBarContainer")
        layout = QHBoxLayout(container)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(8)

        self.btn_option2 = QPushButton("⚡ Edge Plugin / Bookmark")
        self.btn_option2.setStyleSheet("background: linear-gradient(135deg, #1f6feb, #238636); color: white; font-weight: bold; padding: 6px 14px;")
        self.btn_option2.clicked.connect(self.openEdgeSetupDialog)
        self.btn_option2.setToolTip("Setup 1-Click Direct Edge Picture Clicking")
        layout.addWidget(self.btn_option2)

        self.top_print_btn = QPushButton("🖨️ Print Photo")
        self.top_print_btn.setStyleSheet("background-color: #8957e5; color: white; font-weight: bold; padding: 6px 12px;")
        self.top_print_btn.clicked.connect(self.printSelectedPhoto)
        self.top_print_btn.setToolTip("Print selected crop or full photo (Ctrl+P)")
        layout.addWidget(self.top_print_btn)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Paste web image URL or click any picture in Edge...")
        self.url_input.returnPressed.connect(self.fetchImageFromUrl)
        self.url_input.setClearButtonEnabled(True)
        layout.addWidget(self.url_input, stretch=3)

        paste_btn = QPushButton("📋 Paste & Fetch")
        paste_btn.clicked.connect(self.pasteAndFetch)
        paste_btn.setToolTip("Paste URL from clipboard and download photo")
        layout.addWidget(paste_btn)

        self.fetch_btn = QPushButton("⚡ Load Photo")
        self.fetch_btn.setObjectName("primaryButton")
        self.fetch_btn.clicked.connect(self.fetchImageFromUrl)
        layout.addWidget(self.fetch_btn)

        preset_label = QLabel("Sample:")
        preset_label.setStyleSheet("color: #8b949e; margin-left: 6px;")
        layout.addWidget(preset_label)

        self.sample_combo = QComboBox()
        self.sample_combo.addItems([
            "Landscape (800x600)",
            "Nature & Lake (1200x800)",
            "Architecture (1080x720)",
            "Cute Puppy (800x800)",
            "Random HD (1920x1080)"
        ])
        self.sample_combo.currentTextChanged.connect(self.loadSampleImage)
        layout.addWidget(self.sample_combo)

        return container

    def createSidePanel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("sidePanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)

        tab_widget = QTabWidget()
        
        # --- TAB 1: CROPPING, SAVE & PRINT OPTIONS ---
        crop_tab = QWidget()
        crop_tab_layout = QVBoxLayout(crop_tab)
        crop_tab_layout.setContentsMargins(8, 10, 8, 8)
        crop_tab_layout.setSpacing(10)

        # Quick Print Card
        print_box = QFrame()
        print_box.setObjectName("cardBox")
        print_layout = QVBoxLayout(print_box)
        print_layout.setContentsMargins(10, 10, 10, 10)
        print_layout.setSpacing(8)

        print_title = QLabel("🖨️ Print Selected Photo")
        print_title.setStyleSheet("font-weight: bold; color: #d2a8ff; font-size: 13px;")
        print_layout.addWidget(print_title)

        print_desc = QLabel("Print either the cropped selection or full photo directly to your printer or PDF:")
        print_desc.setStyleSheet("color: #8b949e; font-size: 11px;")
        print_desc.setWordWrap(True)
        print_layout.addWidget(print_desc)

        print_btn_row = QHBoxLayout()
        self.btn_print_now = QPushButton("🖨️ Print Now (Ctrl+P)")
        self.btn_print_now.setStyleSheet("background-color: #8957e5; color: white; font-weight: bold; padding: 8px 12px; font-size: 12px;")
        self.btn_print_now.clicked.connect(self.printSelectedPhoto)
        print_btn_row.addWidget(self.btn_print_now, stretch=2)

        self.btn_print_preview = QPushButton("👁️ Preview")
        self.btn_print_preview.setStyleSheet("background-color: #21262d; border: 1px solid #30363d; padding: 8px;")
        self.btn_print_preview.clicked.connect(self.printPreview)
        print_btn_row.addWidget(self.btn_print_preview, stretch=1)
        print_layout.addLayout(print_btn_row)

        crop_tab_layout.addWidget(print_box)

        # Mode Card
        mode_box = QFrame()
        mode_box.setObjectName("cardBox")
        mode_layout = QVBoxLayout(mode_box)
        mode_layout.setContentsMargins(10, 10, 10, 10)
        
        mode_title = QLabel("🎯 Click-to-Crop Mode")
        mode_title.setStyleSheet("font-weight: bold; color: #58a6ff; font-size: 13px;")
        mode_layout.addWidget(mode_title)

        self.btn_group_mode = QButtonGroup(self)
        
        self.rb_click_fixed = QRadioButton("⚡ Instant Click-to-Crop & Save")
        self.rb_click_fixed.setChecked(True)
        self.rb_click_fixed.toggled.connect(self.onModeChanged)
        self.btn_group_mode.addButton(self.rb_click_fixed, 1)
        mode_layout.addWidget(self.rb_click_fixed)

        fixed_size_widget = QWidget()
        fixed_layout = QHBoxLayout(fixed_size_widget)
        fixed_layout.setContentsMargins(18, 2, 0, 4)
        fixed_layout.setSpacing(6)
        
        fixed_layout.addWidget(QLabel("Crop Size:"))
        self.spin_click_w = QSpinBox()
        self.spin_click_w.setRange(20, 4000)
        self.spin_click_w.setValue(300)
        self.spin_click_w.setSuffix(" px")
        self.spin_click_w.valueChanged.connect(self.updateFixedCropDimensions)
        fixed_layout.addWidget(self.spin_click_w)

        fixed_layout.addWidget(QLabel("×"))
        self.spin_click_h = QSpinBox()
        self.spin_click_h.setRange(20, 4000)
        self.spin_click_h.setValue(300)
        self.spin_click_h.setSuffix(" px")
        self.spin_click_h.valueChanged.connect(self.updateFixedCropDimensions)
        fixed_layout.addWidget(self.spin_click_h)

        mode_layout.addWidget(fixed_size_widget)

        self.rb_drag_rect = QRadioButton("📐 Free Rectangle Drag & Resize")
        self.rb_drag_rect.toggled.connect(self.onModeChanged)
        self.btn_group_mode.addButton(self.rb_drag_rect, 0)
        mode_layout.addWidget(self.rb_drag_rect)

        aspect_widget = QWidget()
        aspect_layout = QHBoxLayout(aspect_widget)
        aspect_layout.setContentsMargins(18, 2, 0, 4)
        aspect_layout.addWidget(QLabel("Aspect Ratio:"))
        self.aspect_combo = QComboBox()
        self.aspect_combo.addItems(["Free", "1:1", "4:3", "16:9", "3:2", "9:16", "2:3"])
        self.aspect_combo.currentTextChanged.connect(self.onAspectRatioChanged)
        aspect_layout.addWidget(self.aspect_combo)
        mode_layout.addWidget(aspect_widget)

        self.chk_instant_drag_save = QCheckBox("Save immediately on mouse release")
        self.chk_instant_drag_save.setChecked(False)
        self.chk_instant_drag_save.toggled.connect(self.onInstantDragSaveToggled)
        self.chk_instant_drag_save.setStyleSheet("margin-left: 18px; color: #8b949e;")
        mode_layout.addWidget(self.chk_instant_drag_save)

        self.rb_pan = QRadioButton("✋ Pan / Move Canvas")
        self.rb_pan.toggled.connect(self.onModeChanged)
        self.btn_group_mode.addButton(self.rb_pan, 2)
        mode_layout.addWidget(self.rb_pan)

        crop_tab_layout.addWidget(mode_box)

        # Save Destination Card
        save_box = QFrame()
        save_box.setObjectName("cardBox")
        save_layout = QVBoxLayout(save_box)
        save_layout.setContentsMargins(10, 10, 10, 10)
        save_layout.setSpacing(8)

        save_title = QLabel("💾 Save Destination & Format")
        save_title.setStyleSheet("font-weight: bold; color: #58a6ff; font-size: 13px;")
        save_layout.addWidget(save_title)

        folder_row = QHBoxLayout()
        self.folder_label = QLabel(self.save_directory)
        self.folder_label.setStyleSheet("color: #7ee787; font-family: monospace; font-size: 11px;")
        self.folder_label.setWordWrap(True)
        folder_row.addWidget(self.folder_label, stretch=1)

        browse_btn = QPushButton("📂 Browse...")
        browse_btn.clicked.connect(self.browseSaveDirectory)
        folder_row.addWidget(browse_btn)
        save_layout.addLayout(folder_row)

        open_folder_btn = QPushButton("🔍 Open Saved Folder")
        open_folder_btn.clicked.connect(self.openSavedFolder)
        save_layout.addWidget(open_folder_btn)

        format_row = QHBoxLayout()
        format_row.addWidget(QLabel("Format:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["PNG (*.png)", "JPEG (*.jpg)", "WEBP (*.webp)", "BMP (*.bmp)"])
        format_row.addWidget(self.format_combo)

        format_row.addWidget(QLabel("Quality:"))
        self.quality_spin = QSpinBox()
        self.quality_spin.setRange(10, 100)
        self.quality_spin.setValue(95)
        self.quality_spin.setSuffix("%")
        format_row.addWidget(self.quality_spin)
        save_layout.addLayout(format_row)

        self.chk_copy_clipboard = QCheckBox("📋 Auto-copy cropped image to clipboard")
        self.chk_copy_clipboard.setChecked(True)
        save_layout.addWidget(self.chk_copy_clipboard)

        crop_tab_layout.addWidget(save_box)

        # Actions
        action_box = QFrame()
        action_layout = QVBoxLayout(action_box)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(6)

        self.manual_crop_btn = QPushButton("✂️ Save Selected Crop Area (Enter)")
        self.manual_crop_btn.setObjectName("actionButton")
        self.manual_crop_btn.clicked.connect(self.cropper.executeCrop)
        action_layout.addWidget(self.manual_crop_btn)

        zoom_row = QHBoxLayout()
        btn_fit = QPushButton("🔍 Fit Window")
        btn_fit.clicked.connect(self.cropper.resetZoom)
        zoom_row.addWidget(btn_fit)

        btn_zin = QPushButton("➕ Zoom In")
        btn_zin.clicked.connect(self.cropper.zoomIn)
        zoom_row.addWidget(btn_zin)

        btn_zout = QPushButton("➖ Zoom Out")
        btn_zout.clicked.connect(self.cropper.zoomOut)
        zoom_row.addWidget(btn_zout)
        action_layout.addLayout(zoom_row)

        btn_all = QPushButton("Select Full Photo")
        btn_all.clicked.connect(self.cropper.selectEntireImage)
        action_layout.addWidget(btn_all)

        crop_tab_layout.addWidget(action_box)
        crop_tab_layout.addStretch()

        tab_widget.addTab(crop_tab, "✂️ Crop & Print")

        # --- TAB 2: SAVED CROPS HISTORY ---
        history_tab = QWidget()
        history_layout = QVBoxLayout(history_tab)
        history_layout.setContentsMargins(8, 8, 8, 8)
        history_layout.setSpacing(8)

        hist_header = QHBoxLayout()
        hist_header.addWidget(QLabel("Recent Saved Crops:"))
        
        clear_hist_btn = QPushButton("Clear List")
        clear_hist_btn.clicked.connect(self.clearHistory)
        hist_header.addWidget(clear_hist_btn)
        history_layout.addLayout(hist_header)

        self.history_list = QListWidget()
        self.history_list.setIconSize(QSize(64, 64))
        self.history_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.history_list.customContextMenuRequested.connect(self.onHistoryContextMenu)
        self.history_list.itemDoubleClicked.connect(self.onHistoryItemDoubleClicked)
        history_layout.addWidget(self.history_list)

        hist_hint = QLabel("💡 Double-click to open | Right-click to print directly")
        hist_hint.setStyleSheet("color: #8b949e; font-size: 11px;")
        history_layout.addWidget(hist_hint)

        tab_widget.addTab(history_tab, "🖼️ Saved History")

        layout.addWidget(tab_widget)
        return panel

    def applyModernStyle(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0d1117;
            }
            QWidget {
                color: #c9d1d9;
                font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
                font-size: 12px;
            }
            #topBarContainer, #sidePanel {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 8px;
            }
            #cardBox {
                background-color: #0d1117;
                border: 1px solid #21262d;
                border-radius: 6px;
            }
            QLineEdit, QComboBox, QSpinBox {
                background-color: #0d1117;
                border: 1px solid #30363d;
                border-radius: 5px;
                padding: 6px 10px;
                color: #f0f6fc;
                selection-background-color: #1f6feb;
            }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
                border: 1px solid #58a6ff;
            }
            QPushButton {
                background-color: #21262d;
                border: 1px solid #30363d;
                border-radius: 5px;
                padding: 6px 12px;
                color: #c9d1d9;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #30363d;
                border-color: #8b949e;
                color: #ffffff;
            }
            QPushButton:pressed {
                background-color: #161b22;
            }
            #primaryButton {
                background-color: #238636;
                border: 1px solid #2ea043;
                color: #ffffff;
                font-weight: bold;
                padding: 6px 16px;
            }
            #primaryButton:hover {
                background-color: #2ea043;
            }
            #actionButton {
                background-color: #1f6feb;
                border: 1px solid #388bfd;
                color: #ffffff;
                font-weight: bold;
                padding: 10px;
                font-size: 13px;
                border-radius: 6px;
            }
            #actionButton:hover {
                background-color: #388bfd;
            }
            QTabWidget::pane {
                border: 1px solid #30363d;
                background-color: #161b22;
                border-radius: 6px;
            }
            QTabBar::tab {
                background-color: #0d1117;
                border: 1px solid #30363d;
                padding: 8px 14px;
                margin-right: 4px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
                color: #8b949e;
            }
            QTabBar::tab:selected {
                background-color: #161b22;
                color: #58a6ff;
                border-bottom-color: #161b22;
                font-weight: bold;
            }
            QListWidget {
                background-color: #0d1117;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 4px;
            }
            QListWidget::item {
                padding: 6px;
                border-radius: 4px;
                margin-bottom: 4px;
                background-color: #161b22;
            }
            QListWidget::item:hover {
                background-color: #21262d;
            }
            QListWidget::item:selected {
                background-color: #1f6feb;
                color: #ffffff;
            }
            QRadioButton, QCheckBox {
                spacing: 8px;
            }
            QRadioButton::indicator, QCheckBox::indicator {
                width: 16px;
                height: 16px;
            }
            QStatusBar {
                background-color: #0d1117;
                border-top: 1px solid #21262d;
                color: #8b949e;
            }
            QSplitter::handle {
                background-color: #21262d;
                width: 4px;
            }
        """)

    # ------------------ PRINTING SUPPORT ------------------
    def printSelectedPhoto(self):
        try:
            if not HAS_PRINT_SUPPORT:
                QMessageBox.warning(self, "Printing Unavailable", "QtPrintSupport is not available on this system.")
                return

            pixmap = self.cropper.getSelectedOrFullPixmap()
            if not pixmap or pixmap.isNull():
                QMessageBox.warning(self, "No Photo", "Please load a photo first before printing.")
                return

            dialog = PrintScalingDialog(pixmap, self)
            dialog.exec()
        except Exception as e:
            QMessageBox.warning(self, "Print Error", f"Could not open print studio: {str(e)}")

    def printPreview(self):
        try:
            if not HAS_PRINT_SUPPORT:
                QMessageBox.warning(self, "Printing Unavailable", "QtPrintSupport is not available on this system.")
                return

            pixmap = self.cropper.getSelectedOrFullPixmap()
            if not pixmap or pixmap.isNull():
                QMessageBox.warning(self, "No Photo", "Please load a photo first before previewing.")
                return

            dialog = PrintScalingDialog(pixmap, self)
            dialog.onLaunchPrintPreview()
        except Exception as e:
            QMessageBox.warning(self, "Print Preview Error", f"Could not open print preview: {str(e)}")

    def onHistoryContextMenu(self, point: QPoint):
        try:
            item = self.history_list.itemAt(point)
            if not item:
                return

            filepath = item.data(Qt.ItemDataRole.UserRole)
            menu = QMenu(self)
            
            open_action = menu.addAction("🔍 Open in Default Viewer")
            print_action = menu.addAction("🖨️ Print & Scale this Crop...")
            copy_action = menu.addAction("📋 Copy to Clipboard")
            delete_action = menu.addAction("🗑️ Delete from List")

            action = menu.exec(self.history_list.mapToGlobal(point))
            if action == open_action:
                if filepath and os.path.exists(filepath):
                    open_path(filepath)
            elif action == print_action:
                if filepath and os.path.exists(filepath):
                    pix = QPixmap(filepath)
                    if not pix.isNull() and HAS_PRINT_SUPPORT:
                        dialog = PrintScalingDialog(pix, self)
                        dialog.exec()
            elif action == copy_action:
                if filepath and os.path.exists(filepath):
                    pix = QPixmap(filepath)
                    if not pix.isNull():
                        self.clipboard.setPixmap(pix)
                        self.statusBar().showMessage("Copied to clipboard!", 3000)
            elif action == delete_action:
                row = self.history_list.row(item)
                self.history_list.takeItem(row)
        except Exception:
            pass

    # ------------------ EDGE SETUP & SIGNALS ------------------
    def openEdgeSetupDialog(self):
        dlg = EdgeSetupDialog(self)
        dlg.exec()

    def onToggleEdgeWatch(self, checked: bool):
        self.edge_watch_enabled = checked
        if checked:
            port_num = getattr(self.edge_server, 'port', 59999)
            self.edge_status_label.setText(f"🟢 Edge Plugin Active (Port {port_num})")
            self.edge_status_label.setStyleSheet("color: #7ee787; font-weight: bold; padding-right: 12px;")
        else:
            self.edge_status_label.setText("⚪ Edge Watcher Paused")
            self.edge_status_label.setStyleSheet("color: #8b949e; padding-right: 12px;")

    def onEdgeImageReceived(self, url: str):
        if not self.edge_watch_enabled or not url:
            return
        
        self.url_input.setText(url)
        self.fetchImageFromUrl()

        if self.chk_auto_bring_front.isChecked():
            try:
                self.activateWindow()
                self.raise_()
            except Exception:
                pass

    def onClipboardDataChangedDebounced(self):
        if not self.edge_watch_enabled:
            return
        self.clipboard_timer.start(120)

    def processClipboard(self):
        try:
            if not self.edge_watch_enabled:
                return

            mime = self.clipboard.mimeData()
            if not mime:
                return

            if mime.hasImage():
                img = mime.imageData()
                if isinstance(img, QImage) and not img.isNull():
                    pix = QPixmap.fromImage(img)
                    self.cropper.setPixmap(pix)
                    self.img_info_label.setText(f"{pix.width()} × {pix.height()} px (Clipboard Image)")
                    self.statusBar().showMessage("📥 Photo automatically captured from Microsoft Edge clipboard!", 5000)
                    if self.chk_auto_bring_front.isChecked():
                        self.activateWindow()
                        self.raise_()
                    return

            if mime.hasText():
                text = mime.text().strip()
                if text and text != self.last_clipboard_text:
                    self.last_clipboard_text = text
                    if (text.startswith("http://") or text.startswith("https://") or text.startswith("data:image/")):
                        lower = text.lower()
                        image_extensions = ('.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp', '.svg', 'images.unsplash', 'picsum.photos', 'format=jpg', 'format=png')
                        if any(ext in lower for ext in image_extensions) or text.startswith("data:image/"):
                            self.url_input.setText(text)
                            self.fetchImageFromUrl()
                            if self.chk_auto_bring_front.isChecked():
                                self.activateWindow()
                                self.raise_()
        except Exception:
            pass

    def loadDroppedImage(self, path_or_url: str):
        self.url_input.setText(path_or_url)
        self.fetchImageFromUrl()

    def pasteAndFetch(self):
        try:
            clipboard = QGuiApplication.clipboard()
            text = clipboard.text().strip()
            if text.startswith("http://") or text.startswith("https://") or text.startswith("data:image/"):
                self.url_input.setText(text)
                self.fetchImageFromUrl()
            else:
                self.statusBar().showMessage("Clipboard does not contain a valid web URL.", 4000)
        except Exception:
            pass

    def loadSampleImage(self, sample_name: str):
        sample_urls = {
            "Landscape (800x600)": "https://images.unsplash.com/photo-1506744038136-46273834b3fb?w=1200&q=80",
            "Nature & Lake (1200x800)": "https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?w=1200&q=80",
            "Architecture (1080x720)": "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=1200&q=80",
            "Cute Puppy (800x800)": "https://images.unsplash.com/photo-1543466835-00a7907e9de1?w=1000&q=80",
            "Random HD (1920x1080)": "https://picsum.photos/1920/1080"
        }
        url = sample_urls.get(sample_name, "https://picsum.photos/1200/800")
        self.url_input.setText(url)
        self.fetchImageFromUrl()

    def fetchImageFromUrl(self):
        url = self.url_input.text().strip()
        if not url:
            self.statusBar().showMessage("Please enter an image URL.")
            return

        self.fetch_btn.setEnabled(False)
        self.fetch_btn.setText("⏳ Downloading...")
        self.statusBar().showMessage(f"Fetching photo from {url[:50]}...")

        task = ImageDownloadTask(url)
        task.signals.finished.connect(self.onImageDownloaded)
        task.signals.error.connect(self.onImageDownloadError)
        self.thread_pool.start(task)

    def onImageDownloaded(self, pixmap: QPixmap, url: str, meta: dict):
        self.fetch_btn.setEnabled(True)
        self.fetch_btn.setText("⚡ Load Photo")
        
        self.cropper.setPixmap(pixmap)
        size_kb = meta.get('size_bytes', 0) / 1024.0
        self.img_info_label.setText(f"{meta.get('width', 0)} × {meta.get('height', 0)} px ({size_kb:.1f} KB)")
        self.statusBar().showMessage("Photo loaded! Click/drag to crop, save, or press Ctrl+P to print.", 5000)

    def onImageDownloadError(self, error_msg: str):
        self.fetch_btn.setEnabled(True)
        self.fetch_btn.setText("⚡ Load Photo")
        self.statusBar().showMessage(error_msg, 6000)
        QMessageBox.warning(self, "Download Notice", f"Could not load photo:\n{error_msg}")

    def onModeChanged(self):
        if self.rb_click_fixed.isChecked():
            self.cropper.mode = InteractiveCropper.MODE_CLICK_FIXED
            self.cropper.instant_save_on_click = True
            self.statusBar().showMessage("Instant Click-to-Crop Mode: Click anywhere on the photo to instantly crop & save.")
        elif self.rb_drag_rect.isChecked():
            self.cropper.mode = InteractiveCropper.MODE_DRAG_RECT
            self.statusBar().showMessage("Free Drag Mode: Drag a rectangle over the photo and resize.")
        elif self.rb_pan.isChecked():
            self.cropper.mode = InteractiveCropper.MODE_PAN
            self.statusBar().showMessage("Pan Mode: Click and drag to pan the image.")

    def onAspectRatioChanged(self, text: str):
        self.cropper.aspect_ratio_mode = text
        self.statusBar().showMessage(f"Aspect ratio set to: {text}")

    def onInstantDragSaveToggled(self, checked: bool):
        self.cropper.instant_save_on_drag_release = checked

    def updateFixedCropDimensions(self):
        self.cropper.fixed_crop_width = self.spin_click_w.value()
        self.cropper.fixed_crop_height = self.spin_click_h.value()

    def browseSaveDirectory(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Save Directory", self.save_directory)
        if folder:
            self.save_directory = folder
            self.folder_label.setText(folder)

    def openSavedFolder(self):
        try:
            if os.path.exists(self.save_directory):
                open_path(self.save_directory)
            else:
                QMessageBox.information(self, "Folder", f"Directory does not exist yet: {self.save_directory}")
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

    def onMouseMovedOnImage(self, x: int, y: int):
        self.coord_label.setText(f"X: {x}, Y: {y}")

    def onCropCompleted(self, cropped_pixmap: QPixmap, crop_rect: QRect):
        try:
            format_text = self.format_combo.currentText()
            if "PNG" in format_text:
                ext = "png"
                qt_format = "PNG"
            elif "JPEG" in format_text:
                ext = "jpg"
                qt_format = "JPEG"
            elif "WEBP" in format_text:
                ext = "webp"
                qt_format = "WEBP"
            else:
                ext = "bmp"
                qt_format = "BMP"

            quality = self.quality_spin.value()

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:19]
            filename = f"crop_{crop_rect.width()}x{crop_rect.height()}_{timestamp}.{ext}"
            filepath = os.path.join(self.save_directory, filename)

            success = cropped_pixmap.save(filepath, qt_format, quality)
            if success:
                if self.chk_copy_clipboard.isChecked():
                    self.clipboard.blockSignals(True)
                    self.clipboard.setPixmap(cropped_pixmap)
                    self.clipboard.blockSignals(False)

                self.addHistoryItem(filepath, cropped_pixmap, crop_rect)
                self.statusBar().showMessage(f"✨ Cropped & Saved: {filename} ({crop_rect.width()}×{crop_rect.height()}px)", 6000)
            else:
                self.statusBar().showMessage(f"Failed to save image to {filepath}", 5000)
        except Exception as e:
            self.statusBar().showMessage(f"Save error: {str(e)}", 5000)

    def addHistoryItem(self, filepath: str, pixmap: QPixmap, crop_rect: QRect):
        try:
            thumb = pixmap.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            icon = QIcon(thumb)
            
            filename = os.path.basename(filepath)
            time_str = datetime.now().strftime("%H:%M:%S")
            item_text = f"{filename}\n{crop_rect.width()}×{crop_rect.height()}px • {time_str}"
            
            item = QListWidgetItem(icon, item_text)
            item.setData(Qt.ItemDataRole.UserRole, filepath)
            self.history_list.insertItem(0, item)
            self.history_items.append(filepath)
        except Exception:
            pass

    def onHistoryItemDoubleClicked(self, item: QListWidgetItem):
        try:
            filepath = item.data(Qt.ItemDataRole.UserRole)
            if filepath and os.path.exists(filepath):
                open_path(filepath)
        except Exception:
            pass

    def clearHistory(self):
        self.history_list.clear()
        self.history_items.clear()
        self.statusBar().showMessage("History cleared.")


def exception_hook(exctype, value, traceback):
    print("Unhandled Exception:", exctype, value)
    sys.__excepthook__(exctype, value, traceback)


def main():
    sys.excepthook = exception_hook
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    window = ModernMainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
