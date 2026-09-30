// Microsoft Edge Companion Content Script
// Automatically connects to Qt6 Cropper on http://127.0.0.1:59999

(function() {
  let isEnabled = true;
  const SERVER_URL = 'http://127.0.0.1:59999';

  function getBestSrc(el) {
    if (!el) return '';
    if (el.tagName === 'IMG') {
      if (el.currentSrc) return el.currentSrc;
      if (el.src) return el.src;
      if (el.getAttribute('data-src')) return el.getAttribute('data-src');
      if (el.getAttribute('data-original')) return el.getAttribute('data-original');
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
    
    return '';
  }

  function handleImageClick(e) {
    if (!isEnabled) return;
    
    // Find closest image or container
    const target = e.target;
    let imgEl = null;

    if (target.tagName === 'IMG' || target.getAttribute('role') === 'img') {
      imgEl = target;
    } else if (target.querySelector && target.querySelector('img')) {
      imgEl = target.querySelector('img');
    } else {
      const bg = window.getComputedStyle(target).backgroundImage;
      if (bg && bg !== 'none' && bg.startsWith('url(')) {
        imgEl = target;
      }
    }

    if (!imgEl) return;

    const src = getBestSrc(imgEl);
    if (!src || src.startsWith('javascript:')) return;

    // Visual feedback
    imgEl.style.transition = 'outline 0.2s, transform 0.2s';
    imgEl.style.outline = '4px solid #00ff66';
    imgEl.style.transform = 'scale(0.98)';
    setTimeout(() => {
      imgEl.style.outline = '';
      imgEl.style.transform = '';
    }, 600);

    // Send to desktop Qt6 app
    fetch(`${SERVER_URL}/load?url=${encodeURIComponent(src)}`, {
      method: 'GET',
      mode: 'cors'
    })
    .then(res => res.json())
    .then(data => {
      showToast('✨ Photo sent to Qt6 Cropper!');
    })
    .catch(err => {
      console.log('Cropper app server not responding on port 59999.');
    });
  }

  function showToast(msg) {
    const existing = document.getElementById('__qt_crop_toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.id = '__qt_crop_toast';
    toast.innerText = msg;
    toast.style = 'position:fixed;bottom:24px;right:24px;z-index:99999999;background:#1f6feb;color:#ffffff;padding:12px 20px;border-radius:8px;font-family:sans-serif;box-shadow:0 6px 20px rgba(0,0,0,0.5);font-size:13px;font-weight:bold;transition:opacity 0.3s;pointer-events:none;';
    document.body.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      setTimeout(() => toast.remove(), 300);
    }, 2500);
  }

  // Attach global click event in capture phase
  document.addEventListener('click', handleImageClick, true);

  // Mark page ready
  console.log('[Qt6 Cropper] Edge Watcher Plugin Active.');
})();
