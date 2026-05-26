/* ===========================================================
   THIMI TECH — Three.js interactive globes
   - Hero globe: dotted earth with Nepal pin, draggable
   - CTA orb: smaller decorative wireframe sphere
   =========================================================== */

(() => {
  if (typeof THREE === 'undefined') {
    console.warn('Three.js not loaded');
    return;
  }

  /* ============== HERO GLOBE ============== */
  const heroMount = document.getElementById('globe');
  if (heroMount) {
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 100);
    camera.position.z = 3.4;

    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setClearColor(0x000000, 0);
    const setSize = () => {
      const w = heroMount.clientWidth;
      const h = heroMount.clientHeight;
      renderer.setSize(w, h, false);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    };
    heroMount.appendChild(renderer.domElement);
    setSize();
    window.addEventListener('resize', setSize);

    const globe = new THREE.Group();
    scene.add(globe);

    const R = 1;

    /* Faint wireframe icosahedron base */
    const wireGeo = new THREE.IcosahedronGeometry(R * 0.985, 3);
    const wireMat = new THREE.MeshBasicMaterial({
      color: 0x15140f, wireframe: true,
      transparent: true, opacity: 0.06,
    });
    globe.add(new THREE.Mesh(wireGeo, wireMat));

    /* Solid sub-sphere (occludes back dots subtly) */
    const innerGeo = new THREE.SphereGeometry(R * 0.965, 64, 64);
    const innerMat = new THREE.MeshBasicMaterial({ color: 0xf4f1ea, transparent: true, opacity: 1 });
    globe.add(new THREE.Mesh(innerGeo, innerMat));

    /* Fibonacci dot sphere */
    const N = 2400;
    const positions = new Float32Array(N * 3);
    for (let i = 0; i < N; i++) {
      const y = 1 - (i / (N - 1)) * 2;
      const radius = Math.sqrt(1 - y * y);
      const theta = Math.PI * (1 + Math.sqrt(5)) * i;
      positions[i*3]   = R * Math.cos(theta) * radius;
      positions[i*3+1] = R * y;
      positions[i*3+2] = R * Math.sin(theta) * radius;
    }
    const dotGeo = new THREE.BufferGeometry();
    dotGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));

    /* Custom dot shader so back dots fade */
    const dotMat = new THREE.ShaderMaterial({
      transparent: true,
      depthWrite: false,
      uniforms: {
        uColor: { value: new THREE.Color(0x15140f) },
        uSize:  { value: 3.2 * Math.min(window.devicePixelRatio, 2) },
      },
      vertexShader: `
        uniform float uSize;
        varying float vFade;
        void main(){
          vec4 mv = modelViewMatrix * vec4(position, 1.0);
          gl_Position = projectionMatrix * mv;
          gl_PointSize = uSize;
          // dot facing camera? compute normal in view space
          vec3 vNormal = normalize(normalMatrix * normalize(position));
          vFade = clamp(vNormal.z, 0.0, 1.0);
        }
      `,
      fragmentShader: `
        precision mediump float;
        uniform vec3 uColor;
        varying float vFade;
        void main(){
          vec2 c = gl_PointCoord - 0.5;
          float d = length(c);
          if (d > 0.5) discard;
          float a = smoothstep(0.5, 0.35, d);
          gl_FragColor = vec4(uColor, a * (0.15 + vFade * 0.75));
        }
      `
    });
    const points = new THREE.Points(dotGeo, dotMat);
    globe.add(points);

    /* Nepal pin */
    const lat = 28.0;
    const lon = 84.0;
    const latRad = lat * Math.PI / 180;
    const lonRad = lon * Math.PI / 180;
    const pinPos = new THREE.Vector3(
      R * Math.cos(latRad) * Math.cos(lonRad),
      R * Math.sin(latRad),
      R * Math.cos(latRad) * Math.sin(lonRad)
    );
    const pinGroup = new THREE.Group();
    pinGroup.position.copy(pinPos);
    pinGroup.lookAt(pinPos.clone().multiplyScalar(2));

    const pinDot = new THREE.Mesh(
      new THREE.SphereGeometry(0.018, 16, 16),
      new THREE.MeshBasicMaterial({ color: 0xc77b2c })
    );
    pinGroup.add(pinDot);
    const ring1 = new THREE.Mesh(
      new THREE.RingGeometry(0.025, 0.035, 32),
      new THREE.MeshBasicMaterial({ color: 0xc77b2c, transparent: true, opacity: 0.85, side: THREE.DoubleSide })
    );
    pinGroup.add(ring1);
    const pulse = new THREE.Mesh(
      new THREE.RingGeometry(0.025, 0.032, 32),
      new THREE.MeshBasicMaterial({ color: 0xc77b2c, transparent: true, opacity: 0.6, side: THREE.DoubleSide })
    );
    pinGroup.add(pulse);
    /* Pin stalk going outward */
    const stalk = new THREE.Mesh(
      new THREE.CylinderGeometry(0.002, 0.002, 0.08, 8),
      new THREE.MeshBasicMaterial({ color: 0xc77b2c })
    );
    stalk.position.z = 0.04;
    stalk.rotation.x = Math.PI / 2;
    pinGroup.add(stalk);
    const stalkCap = new THREE.Mesh(
      new THREE.SphereGeometry(0.012, 12, 12),
      new THREE.MeshBasicMaterial({ color: 0xc77b2c })
    );
    stalkCap.position.z = 0.08;
    pinGroup.add(stalkCap);

    globe.add(pinGroup);

    /* Initial rotation: Nepal toward camera, slightly tilted */
    globe.rotation.x = -0.35;
    globe.rotation.y = -lonRad - Math.PI / 2;

    /* Interaction state */
    let target = { rx: globe.rotation.x, ry: globe.rotation.y };
    let cur = { rx: target.rx, ry: target.ry };
    let isDragging = false;
    let lastPt = { x: 0, y: 0 };
    let autoSpin = true;
    let idleTimer = null;

    const startDrag = (clientX, clientY) => {
      isDragging = true;
      autoSpin = false;
      lastPt.x = clientX; lastPt.y = clientY;
      clearTimeout(idleTimer);
    };
    const moveDrag = (clientX, clientY) => {
      if (!isDragging) return;
      const dx = clientX - lastPt.x;
      const dy = clientY - lastPt.y;
      target.ry += dx * 0.005;
      target.rx += dy * 0.005;
      target.rx = Math.max(-1.0, Math.min(1.0, target.rx));
      lastPt.x = clientX; lastPt.y = clientY;
    };
    const endDrag = () => {
      if (!isDragging) return;
      isDragging = false;
      clearTimeout(idleTimer);
      idleTimer = setTimeout(() => { autoSpin = true; }, 2400);
    };

    const cv = renderer.domElement;
    cv.addEventListener('mousedown', e => { e.preventDefault(); startDrag(e.clientX, e.clientY); });
    window.addEventListener('mousemove', e => moveDrag(e.clientX, e.clientY));
    window.addEventListener('mouseup', endDrag);
    cv.addEventListener('touchstart', e => { startDrag(e.touches[0].clientX, e.touches[0].clientY); }, { passive: true });
    window.addEventListener('touchmove', e => moveDrag(e.touches[0].clientX, e.touches[0].clientY), { passive: true });
    window.addEventListener('touchend', endDrag);

    let t = 0;
    const animate = () => {
      requestAnimationFrame(animate);
      t += 0.016;
      if (autoSpin) target.ry += 0.0018;
      cur.rx += (target.rx - cur.rx) * 0.08;
      cur.ry += (target.ry - cur.ry) * 0.08;
      globe.rotation.x = cur.rx;
      globe.rotation.y = cur.ry;

      const ps = 1 + (Math.sin(t * 3.0) * 0.5 + 0.5) * 2.4;
      pulse.scale.setScalar(ps);
      pulse.material.opacity = Math.max(0, 0.55 - (ps - 1) * 0.22);

      renderer.render(scene, camera);
    };
    animate();
  }

  /* ============== CTA ORB (decorative wireframe) ============== */
  const ctaMount = document.getElementById('cta-orb');
  if (ctaMount) {
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(40, 1, 0.1, 100);
    camera.position.z = 3.6;

    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setClearColor(0x000000, 0);
    const setSize = () => {
      const w = ctaMount.clientWidth;
      const h = ctaMount.clientHeight;
      renderer.setSize(w, h, false);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    };
    ctaMount.appendChild(renderer.domElement);
    setSize();
    window.addEventListener('resize', setSize);

    const group = new THREE.Group();
    scene.add(group);

    /* Outer wireframe sphere */
    const outerGeo = new THREE.IcosahedronGeometry(1.1, 2);
    const outerMat = new THREE.MeshBasicMaterial({
      color: 0xf4f1ea, wireframe: true,
      transparent: true, opacity: 0.35,
    });
    group.add(new THREE.Mesh(outerGeo, outerMat));

    /* Inner solid */
    const innerGeo = new THREE.IcosahedronGeometry(0.85, 3);
    const innerMat = new THREE.MeshStandardMaterial({
      color: 0xc77b2c,
      roughness: 0.35,
      metalness: 0.1,
      flatShading: true,
    });
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
    const ringMat = new THREE.PointsMaterial({
      color: 0xf4f1ea, size: 0.04, transparent: true, opacity: 0.9,
    });
    const ring = new THREE.Points(ringGeo, ringMat);
    ring.rotation.x = Math.PI / 2.6;
    group.add(ring);

    /* Lights */
    scene.add(new THREE.AmbientLight(0xffffff, 0.4));
    const dl = new THREE.DirectionalLight(0xffe6c2, 0.9);
    dl.position.set(2, 3, 2);
    scene.add(dl);
    const dl2 = new THREE.DirectionalLight(0xf4f1ea, 0.4);
    dl2.position.set(-2, -1, 1);
    scene.add(dl2);

    let mx = 0, my = 0;
    ctaMount.addEventListener('mousemove', e => {
      const r = ctaMount.getBoundingClientRect();
      mx = ((e.clientX - r.left) / r.width - 0.5) * 2;
      my = ((e.clientY - r.top) / r.height - 0.5) * 2;
    });
    ctaMount.addEventListener('mouseleave', () => { mx = 0; my = 0; });

    let t = 0;
    let curRx = 0, curRy = 0;
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
  }
})();


/* =================== SCROLL CHOREOGRAPHY =================== */
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
})();
