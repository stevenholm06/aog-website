/* Hero video background — explore branch.
   Reveals the background iframe only once YouTube reports it is playing.
   If the API never loads, autoplay is blocked, or the network is down, the
   wrapper stays at opacity 0 and the hero keeps its original JPG. */
(function () {
  'use strict';

  var wrap = document.querySelector('.hero-video-bg');
  var iframe = wrap && wrap.querySelector('iframe');
  if (!iframe) return;

  // Respect the same opt-outs the stylesheet uses; don't boot a player we hide.
  if (window.matchMedia('(max-width: 767px), (prefers-reduced-motion: reduce)').matches) return;

  function start() {
    if (!window.YT || !window.YT.Player) return;
    new window.YT.Player(iframe, {
      events: {
        onStateChange: function (e) {
          if (e.data === window.YT.PlayerState.PLAYING) {
            wrap.classList.add('is-playing');
          }
        }
      }
    });
  }

  // bricks.min.js also loads the IFrame API and may own this global, so chain
  // rather than overwrite it.
  var prev = window.onYouTubeIframeAPIReady;
  window.onYouTubeIframeAPIReady = function () {
    if (typeof prev === 'function') prev();
    start();
  };

  // The API may already be ready by the time this runs.
  if (window.YT && window.YT.Player) start();
})();
