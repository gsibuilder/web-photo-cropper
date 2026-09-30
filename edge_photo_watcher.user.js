// ==UserScript==
// @name         Qt6 Photo Cropper - Edge Auto Clicker
// @namespace    http://tampermonkey.net/
// @version      1.0
// @description  Automatically sends clicked photos in Edge to Qt6 Desktop Cropper & Saver
// @author       Corey Kiesel
// @match        *://*/*
// @grant        none
// @run-at       document-idle
// ==/UserScript==

(function() {
    'use strict';
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

    document.addEventListener('click', function(e) {
        const target = e.target;
        let imgEl = (target.tagName === 'IMG' || target.getAttribute('role') === 'img') ? target : (target.querySelector && target.querySelector('img')) ? target.querySelector('img') : null;
        if (!imgEl) {
            const bg = window.getComputedStyle(target).backgroundImage;
            if (bg && bg !== 'none' && bg.startsWith('url(')) imgEl = target;
        }
        if (!imgEl) return;

        const src = getBestSrc(imgEl);
        if (!src || src.startsWith('javascript:')) return;

        imgEl.style.transition = 'outline 0.2s, transform 0.2s';
        imgEl.style.outline = '4px solid #00ff66';
        imgEl.style.transform = 'scale(0.98)';
        setTimeout(() => { imgEl.style.outline = ''; imgEl.style.transform = ''; }, 600);

        fetch(`${SERVER_URL}/load?url=${encodeURIComponent(src)}`).catch(() => {});
    }, true);
})();
