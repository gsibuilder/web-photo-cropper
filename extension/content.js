// Microsoft Edge / Chrome Companion Content Script
// Automatically connects to Qt6 Cropper on http://127.0.0.1:59999
// Enhanced for Ancestry.com, FamilySearch, IIIF, Canvas & Deep-Zoom Tiled Document Viewers

(function() {
  let isEnabled = true;
  const SERVER_URL = 'http://127.0.0.1:59999';

  function getCanvasData(canvas) {
    if (!canvas || typeof canvas.toDataURL !== 'function') return '';
    try {
      return canvas.toDataURL('image/jpeg', 0.95);
    } catch (e) {
      try {
        return canvas.toDataURL('image/png');
      } catch (e2) {
        return '';
      }
    }
  }

  function compositeTiledContainer(container) {
    try {
      const tiles = container.querySelectorAll('img, canvas');
      if (!tiles || tiles.length === 0) return '';
      if (tiles.length === 1 && tiles[0].tagName === 'CANVAS') {
        return getCanvasData(tiles[0]);
      }

      const rect = container.getBoundingClientRect();
      if (rect.width <= 10 || rect.height <= 10) return '';

      const offCanvas = document.createElement('canvas');
      offCanvas.width = Math.min(4000, Math.round(rect.width * (window.devicePixelRatio || 1)));
      offCanvas.height = Math.min(4000, Math.round(rect.height * (window.devicePixelRatio || 1)));
      const ctx = offCanvas.getContext('2d');
      if (!ctx) return '';

      const scaleX = offCanvas.width / rect.width;
      const scaleY = offCanvas.height / rect.height;

      let drawnCount = 0;
      tiles.forEach(tile => {
        const tRect = tile.getBoundingClientRect();
        const dx = (tRect.left - rect.left) * scaleX;
        const dy = (tRect.top - rect.top) * scaleY;
        const dw = tRect.width * scaleX;
        const dh = tRect.height * scaleY;

        if (tile.tagName === 'IMG' && tile.complete && tile.naturalWidth > 0) {
          ctx.drawImage(tile, dx, dy, dw, dh);
          drawnCount++;
        } else if (tile.tagName === 'CANVAS') {
          ctx.drawImage(tile, dx, dy, dw, dh);
          drawnCount++;
        }
      });

      if (drawnCount > 0) {
        return offCanvas.toDataURL('image/jpeg', 0.92);
      }
    } catch (err) {
      console.log('[Qt6 Cropper] Tiled composition notice:', err);
    }
    return '';
  }

  function getAncestryViewerImage() {
    // 1. Check for visible high-res canvas in Ancestry / OpenSeaDragon viewer
    const canvases = document.querySelectorAll('.image-viewer canvas, .openseadragon-canvas canvas, #imageViewer canvas, [data-testid*="imageViewer"] canvas, canvas');
    for (let c of canvases) {
      if (c.width > 200 && c.height > 200) {
        const data = getCanvasData(c);
        if (data && data.length > 500) return data;
      }
    }

    // 2. Check for deep-zoom container tiles
    const viewerContainers = document.querySelectorAll('.openseadragon-container, .image-viewer-container, #image-viewer-container, .viewport, [data-testid*="imageViewer"]');
    for (let vc of viewerContainers) {
      const comp = compositeTiledContainer(vc);
      if (comp && comp.length > 500) return comp;
    }

    // 3. Check for Ancestry download / full image links in DOM
    const dlLink = document.querySelector('a[data-testid*="download"], a[href*="mediaui-image-service"], a[href*="download"], [data-full-image-url], [data-image-url]');
    if (dlLink) {
      const href = dlLink.getAttribute('href') || dlLink.getAttribute('data-full-image-url') || dlLink.getAttribute('data-image-url');
      if (href && !href.startsWith('javascript:')) return href;
    }

    return '';
  }

  function getBestSrc(el) {
    if (!el) return '';

    // Canvas element support (Ancestry / FamilySearch / WebGL viewers)
    if (el.tagName === 'CANVAS') {
      const cData = getCanvasData(el);
      if (cData) return cData;
    }

    // Check if clicked inside a canvas container or deep-zoom viewer
    const closestCanvas = el.closest ? el.closest('canvas, .openseadragon-container, .image-viewer-container, #imageViewer, [data-testid*="imageViewer"]') : null;
    if (closestCanvas) {
      if (closestCanvas.tagName === 'CANVAS') {
        const cData = getCanvasData(closestCanvas);
        if (cData) return cData;
      } else {
        const comp = compositeTiledContainer(closestCanvas);
        if (comp) return comp;
      }
    }

    // Standard IMG tags
    if (el.tagName === 'IMG') {
      if (el.currentSrc) return el.currentSrc;
      if (el.src) return el.src;
      if (el.getAttribute('data-src')) return el.getAttribute('data-src');
      if (el.getAttribute('data-original')) return el.getAttribute('data-original');
      if (el.getAttribute('data-zoom-src')) return el.getAttribute('data-zoom-src');
      if (el.getAttribute('data-highres')) return el.getAttribute('data-highres');
      if (el.srcset) {
        const parts = el.srcset.split(',');
        const best = parts[parts.length - 1].trim().split(' ')[0];
        if (best) return best;
      }
    }
    
    // Check parent picture tag
    if (el.parentElement && el.parentElement.tagName === 'PICTURE') {
      const source = el.parentElement.querySelector('source');
      if (source && source.srcset) {
        const parts = source.srcset.split(',');
        return parts[parts.length - 1].trim().split(' ')[0];
      }
    }

    // Check computed background-image
    const bg = window.getComputedStyle(el).backgroundImage;
    if (bg && bg !== 'none' && bg.startsWith('url(')) {
      return bg.slice(4, -1).replace(/["']/g, '');
    }

    // Check SVG image
    if (el.tagName === 'image' || el.tagName === 'IMAGE') {
      const href = el.getAttribute('href') || el.getAttribute('xlink:href');
      if (href) return href;
    }

    // Check if on Ancestry or deep zoom site
    if (window.location.hostname.includes('ancestry.') || window.location.hostname.includes('familysearch.')) {
      const ancImg = getAncestryViewerImage();
      if (ancImg) return ancImg;
    }
    
    return '';
  }

  function sendToCropper(src, visualElement) {
    if (!src) return;

    if (visualElement) {
      visualElement.style.transition = 'outline 0.2s, transform 0.2s';
      visualElement.style.outline = '4px solid #00ff66';
      visualElement.style.transform = 'scale(0.99)';
      setTimeout(() => {
        visualElement.style.outline = '';
        visualElement.style.transform = '';
      }, 700);
    }

    showToast('⏳ Sending document to Qt6 Cropper...');

    // Use POST for large payloads (like canvas base64 data URLs)
    fetch(`${SERVER_URL}/load`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ url: src })
    })
    .then(res => res.json())
    .then(data => {
      showToast('✨ Record sent to Qt6 Cropper!');
    })
    .catch(err => {
      // Fallback GET for normal URLs
      if (src.length < 1800) {
        fetch(`${SERVER_URL}/load?url=${encodeURIComponent(src)}`)
          .then(r => r.json())
          .then(() => showToast('✨ Record sent to Qt6 Cropper!'))
          .catch(() => showToast('⚠️ Make sure Qt6 Cropper app is running.'));
      } else {
        showToast('⚠️ Cropper app server not responding on port 59999.');
      }
    });
  }

  function handleImageClick(e) {
    if (!isEnabled) return;
    
    const target = e.target;
    // Don't intercept clicks on our own floating quick button or toast
    if (target.id === '__qt_ancestry_crop_btn' || target.closest('#__qt_ancestry_crop_btn') || target.id === '__qt_crop_toast') {
      return;
    }

    let imgEl = null;

    if (target.tagName === 'IMG' || target.tagName === 'CANVAS' || target.getAttribute('role') === 'img') {
      imgEl = target;
    } else if (target.querySelector && (target.querySelector('img') || target.querySelector('canvas'))) {
      imgEl = target.querySelector('img') || target.querySelector('canvas');
    } else if (target.closest && target.closest('.image-viewer, .openseadragon-container, #imageViewer, [data-testid*="imageViewer"]')) {
      imgEl = target.closest('.image-viewer, .openseadragon-container, #imageViewer, [data-testid*="imageViewer"]');
    } else {
      const bg = window.getComputedStyle(target).backgroundImage;
      if (bg && bg !== 'none' && bg.startsWith('url(')) {
        imgEl = target;
      }
    }

    if (!imgEl) return;

    const src = getBestSrc(imgEl);
    if (!src || src.startsWith('javascript:')) return;

    sendToCropper(src, imgEl);
  }

  function showToast(msg) {
    const existing = document.getElementById('__qt_crop_toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.id = '__qt_crop_toast';
    toast.innerText = msg;
    toast.style = 'position:fixed;bottom:24px;right:24px;z-index:99999999;background:#1f6feb;color:#ffffff;padding:12px 20px;border-radius:8px;font-family:Segoe UI, sans-serif;box-shadow:0 6px 20px rgba(0,0,0,0.5);font-size:13px;font-weight:bold;transition:opacity 0.3s;pointer-events:none;';
    document.body.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      setTimeout(() => toast.remove(), 300);
    }, 2600);
  }

  // Inject sleek floating quick button for Ancestry & Document Viewers
  function injectFloatingButton() {
    if (document.getElementById('__qt_ancestry_crop_btn')) return;
    const isAncestryOrViewer = window.location.hostname.includes('ancestry.') || 
                               window.location.hostname.includes('familysearch.') || 
                               window.location.href.includes('imageviewer') ||
                               document.querySelector('.image-viewer, .openseadragon-container, #imageViewer, canvas');
    
    if (!isAncestryOrViewer) return;

    const btn = document.createElement('button');
    btn.id = '__qt_ancestry_crop_btn';
    btn.innerHTML = '✂️ <b>Send Record to Cropper</b>';
    btn.style = 'position:fixed;bottom:28px;left:24px;z-index:9999999;background:linear-gradient(135deg, #1f6feb, #238636);color:#ffffff;border:none;padding:12px 18px;border-radius:24px;font-family:Segoe UI, sans-serif;font-size:13px;font-weight:600;box-shadow:0 6px 24px rgba(0,0,0,0.4);cursor:pointer;display:flex;align-items:center;gap:8px;transition:transform 0.2s, box-shadow 0.2s;';
    
    btn.addEventListener('mouseenter', () => {
      btn.style.transform = 'scale(1.05)';
      btn.style.boxShadow = '0 8px 28px rgba(31,111,235,0.6)';
    });
    btn.addEventListener('mouseleave', () => {
      btn.style.transform = 'scale(1)';
      btn.style.boxShadow = '0 6px 24px rgba(0,0,0,0.4)';
    });

    btn.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      const src = getAncestryViewerImage() || getBestSrc(document.querySelector('canvas, .openseadragon-container, #imageViewer, img'));
      if (src) {
        sendToCropper(src, btn);
      } else {
        showToast('⚠️ No document canvas/image detected on this page.');
      }
    });

    document.body.appendChild(btn);
  }

  // Attach global click event in capture phase
  document.addEventListener('click', handleImageClick, true);

  // Initialize button injection
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', injectFloatingButton);
  } else {
    injectFloatingButton();
  }
  setInterval(injectFloatingButton, 3000);

  console.log('[Qt6 Cropper] Edge/Chrome Watcher Plugin Active with Ancestry & Canvas Support.');
})();
