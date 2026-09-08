/* Hero video background — explore branch.
   Reveals the background video only once it is genuinely playing. If autoplay
   is blocked or the file fails to load, the wrapper stays transparent and the
   hero keeps its original JPG. */
(function () {
  'use strict';

  var wrap = document.querySelector('.hero-video-bg');
  var video = wrap && wrap.querySelector('video');
  if (!video) return;

  // Match the stylesheet's opt-outs; don't fetch a file we never show.
  if (window.matchMedia('(max-width: 767px), (prefers-reduced-motion: reduce)').matches) {
    video.removeAttribute('autoplay');
    video.removeAttribute('src');
    return;
  }

  video.addEventListener('playing', function () {
    wrap.classList.add('is-playing');
  }, { once: true });

  // Safari and Chrome both need muted set before play() to allow autoplay.
  var p = video.play();
  if (p && typeof p.catch === 'function') p.catch(function () { /* keep the JPG */ });
})();
