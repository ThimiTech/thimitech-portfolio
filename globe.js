/* ===========================================================
   THIMI TECH — globe.js
   Interactive Earth with satellite + PS5 Gamepad API support
   =========================================================== */

(() => {
  if (typeof THREE === 'undefined') {
    console.warn('Three.js not loaded');
    return;
  }

  const heroMount = document.getElementById('globe');
  if (!heroMount) return;

  /* ============== Scene setup ============== */
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 100);
  camera.position.z = 3.4;

  const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setClearColor(0x000000, 0);
  if (THREE.SRGBColorSpace) renderer.outputColorSpace = THREE.SRGBColorSpace;

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

  /* ============== Lights ============== */
  scene.add(new THREE.AmbientLight(0xffffff, 0.35));
  const sun = new THREE.DirectionalLight(0xfff1d8, 1.6);
  sun.position.set(5, 3, 5);
  scene.add(sun);
  const fill = new THREE.DirectionalLight(0x8aa8ff, 0.25);
  fill.position.set(-3, -1, -2);
  scene.add(fill);

  /* ============== Earth ============== */
  const earthGroup = new THREE.Group();
  scene.add(earthGroup);

  const R = 1;
  const loader = new THREE.TextureLoader();
  loader.crossOrigin = 'anonymous';

  const earthGeo = new THREE.SphereGeometry(R, 96, 96);
  const earthMat = new THREE.MeshPhongMaterial({
    color: 0xffffff,
    specular: 0x222233,
    shininess: 14,
  });
  const earth = new THREE.Mesh(earthGeo, earthMat);
  earthGroup.add(earth);

  /* Try to load real textures. Fallback gracefully. */
  const textureCandidates = [
    'https://unpkg.com/three-globe@2.27.2/example/img/earth-blue-marble.jpg',
    'https://cdn.jsdelivr.net/npm/three-globe@2.27.2/example/img/earth-blue-marble.jpg',
  ];
  const bumpCandidates = [
    'https://unpkg.com/three-globe@2.27.2/example/img/earth-topology.png',
    'https://cdn.jsdelivr.net/npm/three-globe@2.27.2/example/img/earth-topology.png',
  ];
  const tryLoad = (urls, onLoad) => {
    let i = 0;
    const next = () => {
      if (i >= urls.length) return;
      loader.load(urls[i], onLoad, undefined, () => { i++; next(); });
    };
    next();
  };
  tryLoad(textureCandidates, (tex) => {
    if (THREE.SRGBColorSpace) tex.colorSpace = THREE.SRGBColorSpace;
    tex.anisotropy = renderer.capabilities.getMaxAnisotropy ? renderer.capabilities.getMaxAnisotropy() : 4;
    earthMat.map = tex;
    earthMat.needsUpdate = true;
  });
  tryLoad(bumpCandidates, (tex) => {
    earthMat.bumpMap = tex;
    earthMat.bumpScale = 0.015;
    earthMat.needsUpdate = true;
  });

  /* Atmosphere — soft glow */
  const atmoGeo = new THREE.SphereGeometry(R * 1.06, 64, 64);
  const atmoMat = new THREE.ShaderMaterial({
    transparent: true,
    side: THREE.BackSide,
    blending: THREE.AdditiveBlending,
    uniforms: {
      uColor: { value: new THREE.Color(0x6fb2ff) },
    },
    vertexShader: `
      varying vec3 vNormal;
      void main(){
        vNormal = normalize(normalMatrix * normal);
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `,
    fragmentShader: `
      uniform vec3 uColor;
      varying vec3 vNormal;
      void main(){
        float i = pow(0.62 - dot(vNormal, vec3(0.0, 0.0, 1.0)), 2.4);
        gl_FragColor = vec4(uColor, 1.0) * i * 0.9;
      }
    `,
  });
  scene.add(new THREE.Mesh(atmoGeo, atmoMat));

  /* Nepal pin */
  const NEPAL_LAT = 28.0;
  const NEPAL_LON = 84.0;
  const llToVec = (lat, lon, r = R) => {
    const phi = (90 - lat) * Math.PI / 180;
    const theta = (lon + 180) * Math.PI / 180;
    return new THREE.Vector3(
      -r * Math.sin(phi) * Math.cos(theta),
       r * Math.cos(phi),
       r * Math.sin(phi) * Math.sin(theta)
    );
  };
  const pinPos = llToVec(NEPAL_LAT, NEPAL_LON, R);
  const pinGroup = new THREE.Group();
  pinGroup.position.copy(pinPos);
  pinGroup.lookAt(pinPos.clone().multiplyScalar(2));

  const pinDot = new THREE.Mesh(
    new THREE.SphereGeometry(0.014, 16, 16),
    new THREE.MeshBasicMaterial({ color: 0xff7a18 })
  );
  pinGroup.add(pinDot);
  const ring1 = new THREE.Mesh(
    new THREE.RingGeometry(0.02, 0.028, 32),
    new THREE.MeshBasicMaterial({ color: 0xff7a18, transparent: true, opacity: 0.9, side: THREE.DoubleSide })
  );
  pinGroup.add(ring1);
  const pulse = new THREE.Mesh(
    new THREE.RingGeometry(0.02, 0.026, 32),
    new THREE.MeshBasicMaterial({ color: 0xff7a18, transparent: true, opacity: 0.7, side: THREE.DoubleSide })
  );
  pinGroup.add(pulse);
  const stalk = new THREE.Mesh(
    new THREE.CylinderGeometry(0.002, 0.002, 0.07, 8),
    new THREE.MeshBasicMaterial({ color: 0xff7a18 })
  );
  stalk.rotation.x = Math.PI / 2;
  stalk.position.z = 0.035;
  pinGroup.add(stalk);
  const stalkCap = new THREE.Mesh(
    new THREE.SphereGeometry(0.012, 12, 12),
    new THREE.MeshBasicMaterial({ color: 0xff7a18 })
  );
  stalkCap.position.z = 0.075;
  pinGroup.add(stalkCap);
  earthGroup.add(pinGroup);

  /* ============== Satellite ============== */
  const satellite = new THREE.Group();
  scene.add(satellite);

  const matMetal = new THREE.MeshStandardMaterial({ color: 0xdcdcdc, metalness: 0.85, roughness: 0.3 });
  const matGold  = new THREE.MeshStandardMaterial({ color: 0xd49a3d, metalness: 0.9,  roughness: 0.25 });
  const matPanel = new THREE.MeshStandardMaterial({ color: 0x1a3a8c, metalness: 0.6, roughness: 0.4, emissive: 0x0a1d4a, emissiveIntensity: 0.5 });

  /* Body */
  const body = new THREE.Mesh(new THREE.BoxGeometry(0.05, 0.05, 0.08), matMetal);
  satellite.add(body);
  const bodyWrap = new THREE.Mesh(new THREE.BoxGeometry(0.055, 0.025, 0.085), matGold);
  satellite.add(bodyWrap);
  /* Solar panels */
  const panelGeo = new THREE.BoxGeometry(0.16, 0.005, 0.06);
  const panelL = new THREE.Mesh(panelGeo, matPanel);
  panelL.position.x = -0.12;
  satellite.add(panelL);
  const panelR = new THREE.Mesh(panelGeo, matPanel);
  panelR.position.x = 0.12;
  satellite.add(panelR);
  /* Panel struts */
  const strutGeo = new THREE.CylinderGeometry(0.003, 0.003, 0.08, 6);
  const strut1 = new THREE.Mesh(strutGeo, matMetal);
  strut1.rotation.z = Math.PI / 2;
  strut1.position.x = -0.06;
  satellite.add(strut1);
  const strut2 = new THREE.Mesh(strutGeo, matMetal);
  strut2.rotation.z = Math.PI / 2;
  strut2.position.x = 0.06;
  satellite.add(strut2);
  /* Antenna dish */
  const dish = new THREE.Mesh(
    new THREE.ConeGeometry(0.02, 0.025, 16, 1, true),
    new THREE.MeshStandardMaterial({ color: 0xeeeeee, metalness: 0.6, roughness: 0.4, side: THREE.DoubleSide })
  );
  dish.position.z = 0.06;
  dish.rotation.x = -Math.PI / 2;
  satellite.add(dish);
  /* Beacon light */
  const beacon = new THREE.Mesh(
    new THREE.SphereGeometry(0.008, 12, 12),
    new THREE.MeshBasicMaterial({ color: 0xff3344 })
  );
  beacon.position.set(0, 0.03, 0);
  satellite.add(beacon);

  /* Orbital ring (visual trail) */
  const orbitRadius = 1.45;
  const orbitGeo = new THREE.TorusGeometry(orbitRadius, 0.001, 8, 128);
  const orbitMat = new THREE.MeshBasicMaterial({ color: 0xff7a18, transparent: true, opacity: 0.2 });
  const orbitLine = new THREE.Mesh(orbitGeo, orbitMat);
  scene.add(orbitLine);

  /* ============== Interaction state ============== */
  let target = { rx: -0.35, ry: -((NEPAL_LON) * Math.PI / 180) - Math.PI / 2, zoom: 3.4 };
  let cur = { rx: target.rx, ry: target.ry, zoom: target.zoom };
  earthGroup.rotation.x = target.rx;
  earthGroup.rotation.y = target.ry;

  const Z_MIN = 1.8;
  const Z_MAX = 5.5;

  let isDragging = false;
  let lastPt = { x: 0, y: 0 };
  let autoSpin = true;
  let idleTimer = null;

  const setIdleTimer = () => {
    clearTimeout(idleTimer);
    idleTimer = setTimeout(() => { autoSpin = true; }, 2600);
  };

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
    target.rx = Math.max(-1.1, Math.min(1.1, target.rx));
    lastPt.x = clientX; lastPt.y = clientY;
  };
  const endDrag = () => {
    if (!isDragging) return;
    isDragging = false;
    setIdleTimer();
  };

  const cv = renderer.domElement;
  cv.addEventListener('mousedown', e => { e.preventDefault(); startDrag(e.clientX, e.clientY); });
  window.addEventListener('mousemove', e => moveDrag(e.clientX, e.clientY));
  window.addEventListener('mouseup', endDrag);
  cv.addEventListener('touchstart', e => { startDrag(e.touches[0].clientX, e.touches[0].clientY); }, { passive: true });
  window.addEventListener('touchmove', e => moveDrag(e.touches[0].clientX, e.touches[0].clientY), { passive: true });
  window.addEventListener('touchend', endDrag);

  /* Wheel zoom */
  heroMount.addEventListener('wheel', (e) => {
    e.preventDefault();
    target.zoom += e.deltaY * 0.0028;
    target.zoom = Math.max(Z_MIN, Math.min(Z_MAX, target.zoom));
    autoSpin = false; setIdleTimer();
  }, { passive: false });

  /* Zoom buttons */
  const zoomIn  = document.getElementById('zoom-in');
  const zoomOut = document.getElementById('zoom-out');
  const zoomReset = document.getElementById('zoom-reset');
  if (zoomIn)  zoomIn.addEventListener('click', () => { target.zoom = Math.max(Z_MIN, target.zoom - 0.4); });
  if (zoomOut) zoomOut.addEventListener('click', () => { target.zoom = Math.min(Z_MAX, target.zoom + 0.4); });
  if (zoomReset) zoomReset.addEventListener('click', () => {
    target.zoom = 3.4;
    target.rx = -0.35;
    target.ry = -((NEPAL_LON) * Math.PI / 180) - Math.PI / 2;
  });

  /* ============== Satellite state ============== */
  let satAngle = 0;            // around Y
  let satIncline = 0.45;       // tilt of orbit plane (rad)
  let satSpeed = 0.006;
  let satSpeedBoost = 0;       // decays each frame, set by external API
  let satOrbitTilt = 0.35;     // orbit plane rotation

  /* ============== Gamepad / PS5 ============== */
  const psShell = document.getElementById('ps5');
  const psStatus = document.getElementById('ps5-status');
  let gpConnected = false;

  const deadzone = (v, t = 0.12) => Math.abs(v) < t ? 0 : v;

  /* Highlight buttons on the SVG controller */
  const setBtn = (id, on) => {
    const el = document.getElementById('ps5-' + id);
    if (el) el.classList.toggle('on', !!on);
  };
  /* Move stick visuals */
  const moveStick = (id, x, y) => {
    const el = document.getElementById('ps5-' + id);
    if (!el) return;
    const tx = (x || 0) * 6;
    const ty = (y || 0) * 6;
    el.style.transform = `translate(${tx}px, ${ty}px)`;
  };

  window.addEventListener('gamepadconnected', (e) => {
    gpConnected = true;
    document.body.classList.add('gp-on');
    if (psShell) psShell.classList.add('connected');
    if (psStatus) psStatus.textContent = 'Controller connected · DualSense detected';
  });
  window.addEventListener('gamepaddisconnected', () => {
    gpConnected = false;
    document.body.classList.remove('gp-on');
    if (psShell) psShell.classList.remove('connected');
    if (psStatus) psStatus.textContent = 'Connect a PS5 controller to fly the satellite';
  });

  const readGamepad = () => {
    const pads = navigator.getGamepads ? navigator.getGamepads() : [];
    let gp = null;
    for (const p of pads) { if (p) { gp = p; break; } }
    if (!gp) return;

    const lx = deadzone(gp.axes[0] || 0);
    const ly = deadzone(gp.axes[1] || 0);
    const rx = deadzone(gp.axes[2] || 0);
    const ry = deadzone(gp.axes[3] || 0);
    const l2 = (gp.buttons[6] && gp.buttons[6].value) || 0;
    const r2 = (gp.buttons[7] && gp.buttons[7].value) || 0;

    /* Satellite control: left stick */
    satSpeed = 0.006 + lx * 0.04;
    satIncline += ly * 0.012;
    satIncline = Math.max(-Math.PI / 2.2, Math.min(Math.PI / 2.2, satIncline));

    /* Globe rotation: right stick */
    if (rx !== 0 || ry !== 0) {
      target.ry += rx * 0.025;
      target.rx += ry * 0.018;
      target.rx = Math.max(-1.1, Math.min(1.1, target.rx));
      autoSpin = false;
      setIdleTimer();
    }

    /* Zoom: L2 in, R2 out */
    if (l2 > 0.05 || r2 > 0.05) {
      target.zoom += (r2 - l2) * 0.04;
      target.zoom = Math.max(Z_MIN, Math.min(Z_MAX, target.zoom));
    }

    /* Sync visual controller */
    moveStick('lstick', lx, ly);
    moveStick('rstick', rx, ry);
    /* PS5 button mapping (Chrome standard): 0=X, 1=Circle, 2=Square, 3=Triangle, 4=L1, 5=R1, 6=L2, 7=R2, 8=Share, 9=Options, 10=L3, 11=R3, 12=Up, 13=Down, 14=Left, 15=Right */
    const namesByIdx = ['cross','circle','square','triangle','l1','r1','l2','r2','share','options','l3','r3','up','down','left','right'];
    for (let i = 0; i < namesByIdx.length; i++) {
      const b = gp.buttons[i];
      setBtn(namesByIdx[i], b && b.pressed);
    }
    /* Triangle: snap back to Nepal */
    if (gp.buttons[3] && gp.buttons[3].pressed) {
      target.rx = -0.35;
      target.ry = -((NEPAL_LON) * Math.PI / 180) - Math.PI / 2;
      target.zoom = 3.4;
    }
    /* X: speed boost */
    if (gp.buttons[0] && gp.buttons[0].pressed) {
      satSpeed = 0.06;
    }
  };

  /* ============== Render loop ============== */
  let t = 0;
  const animate = () => {
    requestAnimationFrame(animate);
    t += 0.016;

    readGamepad();

    if (autoSpin) target.ry += 0.0014;

    cur.rx += (target.rx - cur.rx) * 0.08;
    cur.ry += (target.ry - cur.ry) * 0.08;
    cur.zoom += (target.zoom - cur.zoom) * 0.08;
    earthGroup.rotation.x = cur.rx;
    earthGroup.rotation.y = cur.ry;
    camera.position.z = cur.zoom;

    /* Pin pulse */
    const ps = 1 + (Math.sin(t * 3) * 0.5 + 0.5) * 2.6;
    pulse.scale.setScalar(ps);
    pulse.material.opacity = Math.max(0, 0.65 - (ps - 1) * 0.22);

    /* Satellite orbit */
    satAngle += satSpeed + satSpeedBoost;
    satSpeedBoost *= 0.94;
    const cosI = Math.cos(satIncline);
    const sinI = Math.sin(satIncline);
    const cosT = Math.cos(satOrbitTilt);
    const sinT = Math.sin(satOrbitTilt);
    const r = orbitRadius;
    let sx = r * Math.cos(satAngle);
    let sy = r * sinI * Math.sin(satAngle);
    let sz = r * cosI * Math.sin(satAngle);
    /* Apply orbit plane tilt around X axis */
    const ty = sy * cosT - sz * sinT;
    const tz = sy * sinT + sz * cosT;
    satellite.position.set(sx, ty, tz);
    satellite.lookAt(0, 0, 0);
    satellite.rotateY(Math.PI);
    satellite.rotateZ(t * 0.4);

    /* Orbit ring follows satellite plane */
    orbitLine.rotation.x = satOrbitTilt;
    orbitLine.rotation.y = 0;
    orbitLine.rotation.z = satIncline;

    /* Beacon blink */
    beacon.material.color.setRGB(
      Math.sin(t * 6) > 0 ? 1.0 : 0.2,
      0.2, 0.25
    );

    renderer.render(scene, camera);
  };
  animate();

  /* ============== External control API ============== */
  window.ThimiGlobe = {
    zoomIn:  () => { target.zoom = Math.max(Z_MIN, target.zoom - 0.4); autoSpin = false; setIdleTimer(); },
    zoomOut: () => { target.zoom = Math.min(Z_MAX, target.zoom + 0.4); autoSpin = false; setIdleTimer(); },
    zoomBy:  (dz) => { target.zoom = Math.max(Z_MIN, Math.min(Z_MAX, target.zoom + dz)); autoSpin = false; setIdleTimer(); },
    rotateBy:(dx, dy) => {
      target.ry += dx;
      target.rx += dy;
      target.rx = Math.max(-1.1, Math.min(1.1, target.rx));
      autoSpin = false; setIdleTimer();
    },
    reset: () => {
      target.zoom = 3.4;
      target.rx = -0.35;
      target.ry = -((NEPAL_LON) * Math.PI / 180) - Math.PI / 2;
    },
    satBoost: () => { satSpeedBoost = 0.08; },
    satTiltUp: () => { satIncline = Math.min(Math.PI/2.2, satIncline + 0.06); },
    satTiltDown: () => { satIncline = Math.max(-Math.PI/2.2, satIncline - 0.06); },
    toggleAutoSpin:  () => { autoSpin = !autoSpin; },
    toggleSatellite: () => { satellite.visible = !satellite.visible; orbitLine.visible = !orbitLine.visible; },
  };
})();
