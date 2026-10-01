// ==UserScript==
// @name         Qt6 Photo Cropper - Edge & Chrome Auto Clicker
// @namespace    http://tampermonkey.net/
// @version      2.0
// @description  Automatically sends clicked photos, Ancestry census records, and canvas documents to Qt6 Desktop Cropper
// @author       Corey Kiesel
// @match        *://*/*
// @grant        none
// @run-at       document-idle
// ==/UserScript==

(function() {
    'use strict';
    const SERVER_URL = 'http://127.0.0.1:59999';

    function getCanvasData(canvas) {
        if (!canvas || typeof canvas.toDataURL !== 'function') return '';
        try {
            return canvas.toDataURL('image/jpeg', 0.95);
        } catch (e) {
            try { return canvas.toDataURL('image/png'); } catch (e2) { return ''; }
        }
    }

    function getBestSrc(el) {
        if (!el) return '';
        if (el.tagName === 'CANVAS') {
            const cData = getCanvasData(el);
            if (cData) return cData;
        }

        const closestCanvas = el.closest ? el.closest('canvas, .openseadragon-container, .image-viewer-container, #imageViewer, [data-testid*="imageViewer"]') : null;
        if (closestCanvas) {
            const c = closestCanvas.tagName === 'CANVAS' ? closestCanvas : closestCanvas.querySelector('canvas');
            if (c) {
                const cData = getCanvasData(c);
                if (cData) return cData;
            }
        }

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
        if (el.parentElement && el.parentElement.tagName === 'PICTURE') {
            const source = el.parentElement.querySelector('source');
            if (source && source.srcset) {
                const parts = source.srcset.split(',');
                return parts[parts.length - 1].trim().split(' ')[0];
            }
        }
        const bg = window.getComputedStyle(el).backgroundImage;
        if (bg && bg !== 'none' && bg.startsWith('url(')) {
            return bg.slice(4, -1).replace(/["']/g, '');
        }
        return '';
    }

    function sendToCropper(src, visualElement) {
        if (!src) return;
        if (visualElement) {
            visualElement.style.transition = 'outline 0.2s, transform 0.2s';
            visualElement.style.outline = '4px solid #00ff66';
            visualElement.style.transform = 'scale(0.98)';
            setTimeout(() => { visualElement.style.outline = ''; visualElement.style.transform = ''; }, 600);
        }

        fetch(`${SERVER_URL}/load`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: src })
        }).catch(() => {
            if (src.length < 1800) {
                fetch(`${SERVER_URL}/load?url=${encodeURIComponent(src)}`).catch(() => {});
            }
        });
    }

    document.addEventListener('click', function(e) {
        const target = e.target;
        let imgEl = (target.tagName === 'IMG' || target.tagName === 'CANVAS' || target.getAttribute('role') === 'img') ? target : (target.querySelector && (target.querySelector('img') || target.querySelector('canvas'))) ? (target.querySelector('img') || target.querySelector('canvas')) : null;
        if (!imgEl) {
            const bg = window.getComputedStyle(target).backgroundImage;
            if (bg && bg !== 'none' && bg.startsWith('url(')) imgEl = target;
        }
        if (!imgEl && target.closest) {
            imgEl = target.closest('.image-viewer, .openseadragon-container, #imageViewer, [data-testid*="imageViewer"]');
        }
        if (!imgEl) return;

        const src = getBestSrc(imgEl);
        if (!src || src.startsWith('javascript:')) return;

        sendToCropper(src, imgEl);
    }, true);
})();
