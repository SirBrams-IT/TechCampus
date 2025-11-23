/* sb-toast.js
   Full-featured SBToast module (namespaced). Put in static/js/ and include as module:
   <script type="module" src="{% static 'js/sb-toast.js' %}"></script>
   It also attaches window.SBToast for non-module usage.
*/

const SBToast = (function () {
  /* ---------- Defaults ---------- */
  const DEFAULTS = {
    position: 'bottom-right', // bottom-right, bottom-left, top-right, top-left, top-center, bottom-center, center (overlay)
    duration: 4200,
    max: 4,
    pauseOnHover: true,
    queueMode: true,         // show one at a time if many
    groupDuplicates: true,   // combine identical messages and show counter
    showNetwork: true,
    autoTheme: true,         // uses prefers-color-scheme
    playSound: true,
    icons: {
      success: '✓',
      info: 'ℹ',
      warning: '⚠',
      error: '✕',
      offline: '🔌',
      online: '📶'
    },
    messages: {
      offline: "You're offline — changes will be saved locally",
      online: "Back online"
    },
    sounds: {
      success: { type: 'tone', freq: 880, duration: 90 },
      error: { type: 'tone', freq: 260, duration: 180 },
      info:  { type: 'tone', freq: 660, duration: 90 },
      offline:{ type: 'tone', freq: 220, duration: 120 },
      online: { type: 'tone', freq: 660, duration: 120 }
    }
  };

  /* ---------- State ---------- */
  let cfg = { ...DEFAULTS };
  let root = null;
  let queue = [];            // pending toasts when queueMode
  let showing = [];          // currently displayed toasts (DOM nodes)
  let grouped = new Map();   // message => {count, node}
  let ariaLive = null;

  /* ---------- UTIL ---------- */
  function mk(tag = 'div', props = {}) {
    const el = document.createElement(tag);
    Object.entries(props).forEach(([k, v]) => {
      if (k === 'cls') el.className = v;
      else if (k === 'html') el.innerHTML = v;
      else if (k === 'text') el.textContent = v;
      else el.setAttribute(k, v);
    });
    return el;
  }

  function ensureRoot() {
    if (root) return root;
    // root wrapper holds position containers lazily
    root = mk('div', { cls: 'sb-toast-root', id: 'sb-toast-root' });
    document.body.appendChild(root);
    // aria-live region for screen readers
    ariaLive = mk('div', { cls: 'sb-visually-hidden', 'aria-live': 'polite', 'aria-atomic': 'true' });
    root.appendChild(ariaLive);
    return root;
  }

  function getPosContainer(pos) {
    ensureRoot();
    const cls = `sb-pos-${pos.replace(/_/g,'-')}`;
    let el = root.querySelector(`.${cls}`);
    if (!el) {
      el = mk('div', { cls: cls });
      root.appendChild(el);
    }
    return el;
  }

  function playTone({freq = 440, duration = 120, type = 'sine'}) {
    try {
      const a = new (window.AudioContext || window.webkitAudioContext)();
      const o = a.createOscillator();
      const g = a.createGain();
      o.type = type;
      o.frequency.value = freq;
      o.connect(g);
      g.connect(a.destination);
      g.gain.value = 0.0001;
      o.start();
      // ramp up quickly
      g.gain.exponentialRampToValueAtTime(0.08, a.currentTime + 0.01);
      // ramp down
      g.gain.exponentialRampToValueAtTime(0.0001, a.currentTime + duration/1000);
      setTimeout(() => { try { o.stop(); a.close(); } catch(e){} }, duration + 50);
    } catch (e) { /* ignore audio errors */ }
  }

  /* ---------- Create Toast DOM ---------- */
  function createToastElement(message, type, opts = {}) {
    const toast = mk('div', { cls: `sb-toast sb-toast-${type}` });
    const icon = mk('div', { cls: 'sb-toast-icon', text: cfg.icons[type] || cfg.icons.info });
    const msg  = mk('div', { cls: 'sb-toast-msg', text: message });

    // count bubble for grouped messages
    const count = mk('div', { cls: 'sb-toast-count', text: '' });
    count.style.display = 'none';

    const close = mk('button', { cls: 'sb-toast-close', html: '✕', 'aria-label': 'Dismiss' });

    const progress = mk('div', { cls: 'sb-toast-progress' });
    const pbar = mk('i');
    progress.appendChild(pbar);

    toast.appendChild(icon);
    toast.appendChild(msg);
    toast.appendChild(count);
    toast.appendChild(close);
    toast.appendChild(progress);

    // center style when position center or options.center true
    if (opts.center) toast.classList.add('sb-toast-center');

    return { toast, close, pbar, count };
  }

  /* ---------- Show / Queue Management ---------- */
  function _showImmediate(message, type = 'info', options = {}) {
    ensureRoot();
    const pos = (options.position || cfg.position) || 'bottom-right';
    const isCenter = pos === 'center' || options.center;
    const container = isCenter ? (function(){
      let c = root.querySelector('.sb-center-overlay');
      if (!c) { c = mk('div', { cls: 'sb-center-overlay' }); root.appendChild(c); }
      return c;
    })() : getPosContainer(pos);

    // limit max (if not center overlay)
    if (!isCenter) {
      while (container.children.length >= cfg.max) {
        const oldest = container.children[0];
        if (oldest) oldest.remove();
      }
    }

    // grouping duplicates
    if (cfg.groupDuplicates && type !== 'center') {
      const key = `${type}::${message}`;
      if (grouped.has(key)) {
        const meta = grouped.get(key);
        meta.count++;
        meta.node.querySelector('.sb-toast-count').textContent = `x${meta.count}`;
        meta.node.querySelector('.sb-toast-count').style.display = '';
        // reset progress (visual)
        const p = meta.node.querySelector('.sb-toast-progress > i');
        p.style.transition = `transform ${options.duration ?? cfg.duration}ms linear`;
        p.style.transform = 'scaleX(0)';
        return { dismiss: () => { /* grouped dismiss no-op or decrease count? */ } };
      }
    }

    const { toast, close, pbar, count } = createToastElement(message, type, { center: isCenter });
    container.appendChild(toast);
    // small accessibility text
    ariaLive.textContent = message;

    // show animation
    requestAnimationFrame(() => toast.classList.add('sb-toast--show'));

    // progress bar animation
    const dur = (options.duration === 0) ? 0 : (options.duration ?? cfg.duration);
    if (dur > 0) {
      pbar.style.transition = `transform ${dur}ms linear`;
      requestAnimationFrame(()=> requestAnimationFrame(()=> { pbar.style.transform = 'scaleX(0)'; }));
    } else {
      // persistent: keep full bar
      pbar.style.transform = 'scaleX(1)';
      pbar.style.transition = '';
    }

    // store grouped mapping
    let key;
    if (cfg.groupDuplicates && type !== 'center') {
      key = `${type}::${message}`;
      grouped.set(key, { count: 1, node: toast });
      const bubble = toast.querySelector('.sb-toast-count');
      bubble.textContent = '';
      bubble.style.display = 'none';
    }

    // sound
    if (cfg.playSound && cfg.sounds && cfg.sounds[type]) {
      const s = cfg.sounds[type];
      if (s.type === 'tone') playTone(s);
    }

    showing.push(toast);

    // dismissal
    let tId = null;
    function dismissNow() {
      if (!toast || toast.dataset.removing) return;
      toast.dataset.removing = '1';
      toast.classList.remove('sb-toast--show');
      toast.classList.add('sb-toast--hide');
      setTimeout(() => {
        try { toast.remove(); } catch(e) {}
        // cleanup grouped map if existed
        if (key) grouped.delete(key);
        showing = showing.filter(n => n !== toast);
        // when queueMode on, pop next
        if (cfg.queueMode) processQueue();
      }, 210);
    }

    // auto dismiss if duration > 0
    if (dur > 0) tId = setTimeout(dismissNow, dur);

    // pause/resume on hover
    if (cfg.pauseOnHover && dur > 0) {
      toast.addEventListener('mouseenter', () => {
        if (tId) clearTimeout(tId);
        // freeze bar
        const cs = getComputedStyle(pbar);
        pbar.style.transition = '';
        // keep computed transform
        pbar.style.transform = cs.transform;
      });
      toast.addEventListener('mouseleave', () => {
        // compute approximate remaining via transform matrix if present
        let remaining = dur;
        try {
          const mat = getComputedStyle(pbar).transform;
          if (mat && mat !== 'none') {
            // matrix(a, b, c, d, tx, ty) => a is scaleX approx
            const vals = mat.match(/matrix\((.+)\)/)[1].split(',').map(s=>parseFloat(s));
            const scaleX = vals[0];
            remaining = Math.max(0, dur * scaleX);
          }
        } catch (e) { remaining = dur; }
        pbar.style.transition = `transform ${remaining}ms linear`;
        requestAnimationFrame(()=> pbar.style.transform = 'scaleX(0)');
        tId = setTimeout(dismissNow, remaining);
      });
    }

    // close button
    close.addEventListener('click', () => {
      if (tId) clearTimeout(tId);
      dismissNow();
    });

    return {
      dismiss: dismissNow,
      element: toast
    };
  }

  function processQueue() {
    if (!cfg.queueMode) return;
    if (showing.length > 0) return; // wait until no showing
    if (queue.length === 0) return;
    const job = queue.shift();
    _showImmediate(job.message, job.type, job.options);
  }

  function show(message, type = 'info', options = {}) {
    // normalize type for network messages
    if (type === 'offline' || type === 'online') {
      // allow network types
    }
    // center special semantics
    if (cfg.queueMode) {
      // if queueMode and something showing -> push to queue
      if (showing.length > 0) {
        queue.push({ message, type, options });
        return { queued: true, cancel: () => { queue = queue.filter(j => j.message !== message); } };
      } else {
        return _showImmediate(message, type, options);
      }
    } else {
      // group duplicates check: if grouped and exist, handle in immediate
      return _showImmediate(message, type, options);
    }
  }

  /* ---------- Public API ---------- */
  function init(options = {}) {
    cfg = { ...cfg, ...options };
    ensureRoot();

    // network detection
    if (cfg.showNetwork && typeof window !== 'undefined') {
      if (!navigator.onLine) {
        show(cfg.messages.offline, 'offline', { duration: 0 });
      }
      window.addEventListener('offline', () => {
        show(cfg.messages.offline, 'offline', { duration: 0 });
      });
      window.addEventListener('online', () => {
        // remove offline toasts
        document.querySelectorAll('.sb-toast-offline').forEach(n => n.remove());
        show(cfg.messages.online, 'online', { duration: 2800 });
      });
    }

    // auto theme watch
    if (cfg.autoTheme && window.matchMedia) {
      const mq = window.matchMedia('(prefers-color-scheme: dark)');
      // you could toggle classes if needed; CSS uses gradients so auto ok
      mq.addEventListener && mq.addEventListener('change', () => { /* no-op for now */ });
    }

    // expose simple helper on window for convenience
    if (typeof window !== 'undefined') {
      window.SBToast = window.SBToast || SB;
    }

    return SB; // return api
  }

  function sessionExpired(options = {}) {
    const cfgOpt = { position: 'center', duration: options.duration ?? 0, center: true };
    const res = _showImmediate(options.message ?? 'Session expired — please sign in again.', 'error', cfgOpt);
    // add action button to center element
    const el = res.element || null;
    if (el) {
      // make an actions container
      const actions = mk('div', { cls: 'sb-toast-actions' });
      actions.style.marginLeft = '8px';
      actions.style.display = 'flex';
      actions.style.gap = '8px';
      const relogin = mk('button', { html: options.buttonText ?? 'Sign in', cls: 'sb-toast-center-btn' });
      relogin.style.padding = '.5rem .9rem';
      relogin.style.borderRadius = '8px';
      relogin.style.border = '0';
      relogin.style.cursor = 'pointer';
      relogin.addEventListener('click', () => {
        if (typeof options.onAction === 'function') options.onAction();
        res.dismiss();
      });
      actions.appendChild(relogin);
      el.appendChild(actions);
    }
    return res;
  }

  /* ---------- Small convenience wrapper 'SB' to export ---------- */
  const SB = {
    init: init,
    show: show,
    sessionExpired: sessionExpired,
    config: (o)=> { cfg = { ...cfg, ...o }; return cfg; },
    _internal: { grouped, queue, showing } // useful for debugging
  };

  // Auto-init on DOMContentLoaded (with defaults) to ensure root present (but don't override user config)
  if (typeof document !== 'undefined') {
    document.addEventListener('DOMContentLoaded', () => { ensureRoot(); });
  }

  return SB;
})();

/* UMD-style attach */
if (typeof window !== 'undefined') {
  window.SBToast = window.SBToast || SBToast;
}

/* Export for ES module usage */
export default SBToast;
