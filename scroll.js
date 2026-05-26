/* ===========================================================
   THIMI TECH — scroll.js (UI choreography + CTA orb + flicker)
   =========================================================== */

/* ============== CTA decorative orb ============== */
(() => {
  if (typeof THREE === 'undefined') return;
  const mount = document.getElementById('cta-orb');
  if (!mount) return;

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(40, 1, 0.1, 100);
  camera.position.z = 3.6;

  const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setClearColor(0x000000, 0);
  const setSize = () => {
    const w = mount.clientWidth;
    const h = mount.clientHeight;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  };
  mount.appendChild(renderer.domElement);
  setSize();
  window.addEventListener('resize', setSize);

  const group = new THREE.Group();
  scene.add(group);

  const outerGeo = new THREE.IcosahedronGeometry(1.1, 2);
  const outerMat = new THREE.MeshBasicMaterial({ color: 0xf4f1ea, wireframe: true, transparent: true, opacity: 0.35 });
  group.add(new THREE.Mesh(outerGeo, outerMat));

  const innerGeo = new THREE.IcosahedronGeometry(0.85, 3);
  const innerMat = new THREE.MeshStandardMaterial({ color: 0xc77b2c, roughness: 0.35, metalness: 0.1, flatShading: true });
  const inner = new THREE.Mesh(innerGeo, innerMat);
  group.add(inner);

  /* Dot ring */
  const ringDots = 80;
  const ringGeo = new THREE.BufferGeometry();
  const rp = new Float32Array(ringDots * 3);
  for (let i = 0; i < ringDots; i++) {
    const a = (i / ringDots) * Math.PI * 2;
    rp[i*3]   = Math.cos(a) * 1.35;
    rp[i*3+1] = 0;
    rp[i*3+2] = Math.sin(a) * 1.35;
  }
  ringGeo.setAttribute('position', new THREE.BufferAttribute(rp, 3));
  const ringMat = new THREE.PointsMaterial({ color: 0xf4f1ea, size: 0.04, transparent: true, opacity: 0.9 });
  const ring = new THREE.Points(ringGeo, ringMat);
  ring.rotation.x = Math.PI / 2.6;
  group.add(ring);

  scene.add(new THREE.AmbientLight(0xffffff, 0.4));
  const dl = new THREE.DirectionalLight(0xffe6c2, 0.9);
  dl.position.set(2, 3, 2);
  scene.add(dl);
  const dl2 = new THREE.DirectionalLight(0xf4f1ea, 0.4);
  dl2.position.set(-2, -1, 1);
  scene.add(dl2);

  let mx = 0, my = 0;
  mount.addEventListener('mousemove', e => {
    const r = mount.getBoundingClientRect();
    mx = ((e.clientX - r.left) / r.width - 0.5) * 2;
    my = ((e.clientY - r.top) / r.height - 0.5) * 2;
  });
  mount.addEventListener('mouseleave', () => { mx = 0; my = 0; });

  let t = 0, curRx = 0, curRy = 0;
  const animate = () => {
    requestAnimationFrame(animate);
    t += 0.01;
    const targetRy = mx * 0.6 + t * 0.3;
    const targetRx = -my * 0.4 + Math.sin(t * 0.5) * 0.1;
    curRx += (targetRx - curRx) * 0.05;
    curRy += (targetRy - curRy) * 0.05;
    group.rotation.x = curRx;
    group.rotation.y = curRy;
    inner.rotation.y -= 0.003;
    ring.rotation.z += 0.004;
    renderer.render(scene, camera);
  };
  animate();
})();


/* ============== UI choreography ============== */
(() => {
  /* ---------- LOADER ---------- */
  const loader = document.querySelector('.loader');
  const bar = document.querySelector('.loader-bar');
  const num = document.querySelector('.loader-mark .num');
  let p = 0;
  const tick = () => {
    p += Math.random() * 9 + 3;
    if (p > 100) p = 100;
    if (bar) bar.style.setProperty('--p', (p / 100).toFixed(3));
    if (num) num.textContent = String(Math.floor(p)).padStart(3, '0');
    if (p < 100) setTimeout(tick, 70);
    else setTimeout(() => loader && loader.classList.add('done'), 280);
  };
  tick();

  /* ---------- NAV scrolled state ---------- */
  const nav = document.querySelector('.nav');
  window.addEventListener('scroll', () => {
    if (!nav) return;
    if (window.scrollY > 30) nav.classList.add('scrolled');
    else nav.classList.remove('scrolled');
  }, { passive: true });

  /* ---------- Clock in hero meta ---------- */
  const clock = document.getElementById('clock');
  if (clock) {
    const fmt = () => {
      try {
        const d = new Date();
        const opts = { hour:'2-digit', minute:'2-digit', timeZone:'Asia/Kathmandu', hour12: false };
        clock.textContent = d.toLocaleTimeString('en-GB', opts) + ' Kathmandu';
      } catch(e) { clock.textContent = ''; }
    };
    fmt();
    setInterval(fmt, 30 * 1000);
  }

  /* ---------- Reveal on intersect ---------- */
  const io = new IntersectionObserver((entries) => {
    entries.forEach(en => {
      if (en.isIntersecting) {
        en.target.classList.add('in');
        io.unobserve(en.target);
      }
    });
  }, { threshold: 0.15, rootMargin: '0px 0px -8% 0px' });
  document.querySelectorAll('.reveal-up').forEach(el => io.observe(el));

  /* ---------- Horizontal pinned services ---------- */
  const rail = document.querySelector('.services-rail');
  const track = document.querySelector('.services-track');
  const progBar = document.querySelector('.services-head .bar');
  const progNow = document.querySelector('.services-head .now');
  const cards = document.querySelectorAll('.service-card');

  const updateRail = () => {
    if (!rail || !track) return;
    if (window.innerWidth < 880) {
      track.style.transform = '';
      return;
    }
    const r = rail.getBoundingClientRect();
    const railH = rail.offsetHeight;
    const winH = window.innerHeight;
    const scrollable = railH - winH;
    const scrolled = Math.min(Math.max(-r.top, 0), scrollable);
    const pct = scrollable > 0 ? scrolled / scrollable : 0;
    const pad = parseInt(getComputedStyle(document.documentElement).getPropertyValue('--pad-x')) || 32;
    const maxX = track.scrollWidth - window.innerWidth + pad * 2;
    track.style.transform = `translateX(${-pct * maxX}px)`;
    if (progBar) progBar.style.setProperty('--p', pct.toFixed(3));
    if (progNow) {
      const idx = Math.min(cards.length, Math.floor(pct * cards.length) + 1);
      progNow.textContent = String(idx).padStart(2, '0');
    }
  };
  window.addEventListener('scroll', updateRail, { passive: true });
  window.addEventListener('resize', updateRail);
  updateRail();

  /* ---------- FLICKER TEXT ---------- */
  const flick = document.querySelector('.flicker-text');
  if (flick) {
    const phrases = ['Reality, into Vision', 'Vision, into Reality'];
    const charset = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ#@$%&*/\\-+=<>?:;,.';
    let idx = 0;

    const scramble = (target, duration = 600) => {
      const start = performance.now();
      const orig = target;
      const step = (now) => {
        const t = Math.min(1, (now - start) / duration);
        const revealLen = Math.floor(orig.length * t);
        let out = '';
        for (let i = 0; i < orig.length; i++) {
          if (orig[i] === ' ' || orig[i] === ',') { out += orig[i]; continue; }
          if (i < revealLen) out += orig[i];
          else out += charset[Math.floor(Math.random() * charset.length)];
        }
        flick.textContent = out;
        flick.setAttribute('data-text', out);
        if (t < 1) requestAnimationFrame(step);
        else {
          flick.textContent = orig;
          flick.setAttribute('data-text', orig);
        }
      };
      requestAnimationFrame(step);
    };

    /* Random position jitter */
    const jitter = () => {
      if (Math.random() < 0.55) {
        const x = (Math.random() - 0.5) * 18;
        const y = (Math.random() - 0.5) * 8;
        flick.style.setProperty('--jx', x + 'px');
        flick.style.setProperty('--jy', y + 'px');
      } else {
        flick.style.setProperty('--jx', '0px');
        flick.style.setProperty('--jy', '0px');
      }
      setTimeout(jitter, 120 + Math.random() * 300);
    };
    jitter();

    /* Swap phrase every 3.8s with scramble */
    setInterval(() => {
      idx = 1 - idx;
      scramble(phrases[idx]);
    }, 3800);
  }

  /* ---------- PARALLAX of hero text on scroll ---------- */
  const heroText = document.querySelector('.hero-text');
  if (heroText) {
    window.addEventListener('scroll', () => {
      const y = window.scrollY;
      if (y < window.innerHeight) {
        heroText.style.transform = `translateY(${y * 0.15}px)`;
        heroText.style.opacity = Math.max(0, 1 - y / (window.innerHeight * 0.7));
      }
    }, { passive: true });
  }
})();
