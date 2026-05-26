/* ===========================================================
   THIMI TECH — bucket3d.js
   3D bucket that collects user-submitted "idea cards".
   Cards come from the whiteboard canvas or the text input.
   =========================================================== */

(() => {
  if (typeof THREE === 'undefined') return;
  const mount = document.getElementById('bucket3d');
  if (!mount) return;

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(40, 1, 0.1, 100);
  /* Top-down view, slightly angled so we see into the bucket */
  camera.position.set(0, 3.6, 1.3);
  camera.lookAt(0, 0.4, 0);

  const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setClearColor(0x000000, 0);
  if (THREE.SRGBColorSpace) renderer.outputColorSpace = THREE.SRGBColorSpace;
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

  /* Lights */
  scene.add(new THREE.AmbientLight(0xffffff, 0.45));
  const key = new THREE.DirectionalLight(0xfff1d8, 1.0);
  key.position.set(2, 5, 3);
  scene.add(key);
  const fill = new THREE.DirectionalLight(0xc77b2c, 0.35);
  fill.position.set(-3, 1, 2);
  scene.add(fill);

  /* ============== Bucket geometry (lathe) ============== */
  const profile = [
    new THREE.Vector2(0.0,  0.0),    // center bottom
    new THREE.Vector2(0.62, 0.0),    // outer bottom
    new THREE.Vector2(0.66, 0.04),
    new THREE.Vector2(1.0,  1.25),   // outer top
    new THREE.Vector2(1.06, 1.27),   // rim outer
    new THREE.Vector2(1.02, 1.27),   // rim inner
    new THREE.Vector2(0.96, 1.23),
    new THREE.Vector2(0.62, 0.04),
    new THREE.Vector2(0.58, 0.04),
  ];
  const bucketGeo = new THREE.LatheGeometry(profile, 80);
  const bucketMat = new THREE.MeshPhongMaterial({
    color: 0xece6d7,
    shininess: 40,
    specular: 0x444444,
    side: THREE.DoubleSide,
    flatShading: false,
  });
  const bucket = new THREE.Mesh(bucketGeo, bucketMat);
  scene.add(bucket);

  /* Wireframe overlay */
  const bucketWireMat = new THREE.MeshBasicMaterial({
    color: 0x15140f, wireframe: true, transparent: true, opacity: 0.18,
  });
  scene.add(new THREE.Mesh(bucketGeo, bucketWireMat));

  /* Handle (a torus segment) */
  const handleGroup = new THREE.Group();
  const handleGeo = new THREE.TorusGeometry(0.5, 0.025, 8, 32, Math.PI);
  const handleMat = new THREE.MeshPhongMaterial({ color: 0x15140f, shininess: 80 });
  const handleL = new THREE.Mesh(handleGeo, handleMat);
  handleL.rotation.z = Math.PI;
  handleL.rotation.y = Math.PI / 2;
  handleL.position.set(0, 1.32, 0);
  handleL.scale.set(2.05, 1.2, 1);
  handleGroup.add(handleL);
  scene.add(handleGroup);

  /* Soft glow ring inside the bucket */
  const glowGeo = new THREE.CircleGeometry(0.6, 32);
  const glowMat = new THREE.MeshBasicMaterial({
    color: 0xc77b2c, transparent: true, opacity: 0.35, side: THREE.DoubleSide
  });
  const glow = new THREE.Mesh(glowGeo, glowMat);
  glow.rotation.x = -Math.PI / 2;
  glow.position.y = 0.05;
  scene.add(glow);

  /* Ground shadow plane */
  const shadowGeo = new THREE.CircleGeometry(1.4, 48);
  const shadowMat = new THREE.MeshBasicMaterial({ color: 0x15140f, transparent: true, opacity: 0.08 });
  const shadowM = new THREE.Mesh(shadowGeo, shadowMat);
  shadowM.rotation.x = -Math.PI / 2;
  shadowM.position.y = -0.001;
  scene.add(shadowM);

  /* ============== Ideas in the bucket (crumpled paper balls) ============== */
  const ideas = []; // each { mesh, settledY, jitterPhase, settledX, settledZ }

  /* Build a crumpled-paper ball geometry with the canvas as texture */
  const buildCrumpledBall = (texture, size = 0.16) => {
    const geo = new THREE.IcosahedronGeometry(size, 2);
    const pos = geo.attributes.position;
    /* Displace each vertex slightly to look crumpled */
    for (let i = 0; i < pos.count; i++) {
      const x = pos.getX(i), y = pos.getY(i), z = pos.getZ(i);
      const nx = x + (Math.random() - 0.5) * size * 0.35;
      const ny = y + (Math.random() - 0.5) * size * 0.35;
      const nz = z + (Math.random() - 0.5) * size * 0.35;
      pos.setXYZ(i, nx, ny, nz);
    }
    pos.needsUpdate = true;
    geo.computeVertexNormals();
    const mat = new THREE.MeshStandardMaterial({
      map: texture,
      color: 0xffffff,
      roughness: 0.95,
      metalness: 0.0,
      flatShading: true,
    });
    return new THREE.Mesh(geo, mat);
  };

  /* Drop a new idea ball */
  const STORAGE_KEY = 'thimitech.bucket.v2';
  let count = 0;
  const countEl = document.getElementById('bucket-count');
  const setCount = (n) => {
    count = n;
    if (countEl) countEl.textContent = String(n).padStart(2, '0');
  };
  setCount(0);

  const addIdeaBall = (texture, settle = true) => {
    const size = 0.13 + Math.random() * 0.04;
    const ball = buildCrumpledBall(texture, size);
    /* Random landing position inside bucket (clustered at center) */
    const r = Math.random() * 0.55;
    const a = Math.random() * Math.PI * 2;
    const settledX = Math.cos(a) * r;
    const settledZ = Math.sin(a) * r;
    /* Stack vertically as more come in */
    const layer = Math.floor(ideas.length / 6);
    const stackY = size * 0.95 + layer * size * 0.8 + Math.random() * 0.02;
    if (settle) {
      ball.position.set(settledX, stackY, settledZ);
      ball.rotation.set(
        Math.random() * Math.PI,
        Math.random() * Math.PI * 2,
        Math.random() * Math.PI
      );
    } else {
      ball.position.set(0, 3.5, 0);
    }
    scene.add(ball);
    ideas.push({
      mesh: ball,
      settledX, settledZ, settledY: stackY,
      jitterPhase: Math.random() * Math.PI * 2,
      size,
    });
    setCount(ideas.length);
    return ball;
  };

  /* Animate a 3D ball falling into the bucket with bounce */
  const dropBall = (texture) => {
    const ball = addIdeaBall(texture, false);
    const idea = ideas[ideas.length - 1];
    const startY = 2.8;
    const endY = idea.settledY;
    const startX = (Math.random() - 0.5) * 0.3;
    const startZ = (Math.random() - 0.5) * 0.3;
    const endX = idea.settledX;
    const endZ = idea.settledZ;
    const fallDur = 700;
    const startRot = {
      x: Math.random() * Math.PI,
      y: Math.random() * Math.PI * 2,
      z: Math.random() * Math.PI,
    };
    const spin = {
      x: 0.15 + Math.random() * 0.2,
      y: 0.12 + Math.random() * 0.18,
      z: 0.1 + Math.random() * 0.15,
    };
    const start = performance.now();
    const tick = (now) => {
      const t = Math.min(1, (now - start) / fallDur);
      /* Fall with quadratic (gravity-like) ease */
      const ease = t * t;
      ball.position.x = startX + (endX - startX) * t;
      ball.position.z = startZ + (endZ - startZ) * t;
      ball.position.y = startY + (endY - startY) * ease;
      ball.rotation.x = startRot.x + spin.x * t * 10;
      ball.rotation.y = startRot.y + spin.y * t * 10;
      ball.rotation.z = startRot.z + spin.z * t * 10;
      if (t < 1) {
        requestAnimationFrame(tick);
      } else {
        /* Bounce */
        const bounceStart = performance.now();
        const bounceTick = (now2) => {
          const bt = Math.min(1, (now2 - bounceStart) / 280);
          const lift = Math.sin(bt * Math.PI) * 0.08;
          ball.position.y = endY + lift;
          if (bt < 1) requestAnimationFrame(bounceTick);
          else ball.position.y = endY;
        };
        requestAnimationFrame(bounceTick);
      }
    };
    requestAnimationFrame(tick);

    /* Visual feedback on glow */
    glow.material.opacity = 0.9;
    setTimeout(() => { glow.material.opacity = 0.35; }, 800);

    /* Persist count */
    try {
      const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
      stored.count = (stored.count || 0) + 1;
      stored.lastAt = Date.now();
      localStorage.setItem(STORAGE_KEY, JSON.stringify(stored));
    } catch (e) {}
  };

  /* Restore prior count from localStorage — pre-fill as crumpled balls */
  const restore = () => {
    try {
      const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
      const n = Math.min(stored.count || 0, 18);
      if (!n) return;
      const cv = document.createElement('canvas');
      cv.width = 256; cv.height = 180;
      const ctx = cv.getContext('2d');
      ctx.fillStyle = '#f4f1ea';
      ctx.fillRect(0, 0, cv.width, cv.height);
      ctx.fillStyle = '#15140f';
      ctx.font = 'italic 22px Instrument Serif, Times New Roman, serif';
      ctx.fillText('Idea no.', 16, 30);
      ctx.strokeStyle = '#c77b2c';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(16, 90); ctx.lineTo(180, 90);
      ctx.stroke();
      const tex = new THREE.CanvasTexture(cv);
      if (THREE.SRGBColorSpace) tex.colorSpace = THREE.SRGBColorSpace;
      for (let i = 0; i < n; i++) {
        addIdeaBall(tex, true);
      }
      setCount(n);
    } catch (e) {}
  };
  restore();

  /* ============== Crumple-and-fly animation ============== */
  const crumpleAndDrop = (sourceCanvas) => {
    const dataURL = sourceCanvas.toDataURL('image/png');

    /* Get start position (whiteboard pane) and end position (bucket center) */
    const startEl = document.querySelector('.wb-pane:not([hidden])');
    const endEl = document.getElementById('bucket3d');
    if (!startEl || !endEl) {
      /* fallback: just spawn the ball */
      const tex = new THREE.CanvasTexture(sourceCanvas);
      if (THREE.SRGBColorSpace) tex.colorSpace = THREE.SRGBColorSpace;
      dropBall(tex);
      return;
    }
    const sR = startEl.getBoundingClientRect();
    const eR = endEl.getBoundingClientRect();
    const cx = eR.left + eR.width / 2;
    const cy = eR.top + eR.height / 2;

    /* Build ghost element */
    const ghost = document.createElement('div');
    ghost.className = 'crumple-ghost';
    ghost.style.left = sR.left + 'px';
    ghost.style.top = sR.top + 'px';
    ghost.style.width = sR.width + 'px';
    ghost.style.height = sR.height + 'px';
    ghost.style.backgroundImage = `url(${dataURL})`;

    /* Compute translation needed (from CSS top-left of ghost to bucket center) */
    const dx = cx - (sR.left + sR.width / 2);
    const dy = cy - (sR.top + sR.height / 2);
    ghost.style.setProperty('--tx', dx + 'px');
    ghost.style.setProperty('--ty', dy + 'px');
    document.body.appendChild(ghost);

    /* Trigger animation next frame */
    requestAnimationFrame(() => {
      ghost.classList.add('go');
    });

    /* Hand off to 3D scene partway through */
    setTimeout(() => {
      const tex = new THREE.CanvasTexture(sourceCanvas);
      if (THREE.SRGBColorSpace) tex.colorSpace = THREE.SRGBColorSpace;
      dropBall(tex);
    }, 850);

    /* Remove ghost after the full animation */
    setTimeout(() => {
      ghost.remove();
    }, 1200);
  };

  /* ============== Whiteboard wiring ============== */
  const wbCanvas = document.getElementById('wb-canvas');
  const wbText = document.getElementById('wb-text');
  const submitBtn = document.getElementById('wb-submit');
  const clearBtn = document.getElementById('wb-clear');
  const tabs = document.querySelectorAll('.wb-tab');
  const panes = document.querySelectorAll('.wb-pane');
  const colorBtns = document.querySelectorAll('.wb-color');

  let activeMode = 'draw';
  let strokeColor = '#15140f';
  let isDrawing = false;
  let lastX = 0, lastY = 0;
  let strokes = 0;
  let ctx;

  const setupCanvas = () => {
    if (!wbCanvas) return;
    const r = wbCanvas.getBoundingClientRect();
    const dpr = Math.min(window.devicePixelRatio, 2);
    wbCanvas.width = r.width * dpr;
    wbCanvas.height = r.height * dpr;
    ctx = wbCanvas.getContext('2d');
    ctx.scale(dpr, dpr);
    /* Subtle grid background */
    ctx.fillStyle = '#fbf8f1';
    ctx.fillRect(0, 0, r.width, r.height);
    ctx.strokeStyle = 'rgba(21,20,15,0.06)';
    ctx.lineWidth = 1;
    for (let x = 0; x < r.width; x += 24) {
      ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, r.height); ctx.stroke();
    }
    for (let y = 0; y < r.height; y += 24) {
      ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(r.width, y); ctx.stroke();
    }
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    strokes = 0;
  };
  if (wbCanvas) setupCanvas();
  window.addEventListener('resize', () => { if (wbCanvas) setupCanvas(); });

  const startStroke = (x, y) => {
    isDrawing = true;
    lastX = x; lastY = y;
  };
  const drawTo = (x, y) => {
    if (!isDrawing || !ctx) return;
    ctx.strokeStyle = strokeColor;
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(lastX, lastY);
    ctx.lineTo(x, y);
    ctx.stroke();
    lastX = x; lastY = y;
    strokes++;
  };
  const endStroke = () => { isDrawing = false; };

  if (wbCanvas) {
    const px = (e) => {
      const r = wbCanvas.getBoundingClientRect();
      const cx = e.touches ? e.touches[0].clientX : e.clientX;
      const cy = e.touches ? e.touches[0].clientY : e.clientY;
      return { x: cx - r.left, y: cy - r.top };
    };
    wbCanvas.addEventListener('mousedown', e => { const p = px(e); startStroke(p.x, p.y); });
    wbCanvas.addEventListener('mousemove', e => { const p = px(e); drawTo(p.x, p.y); });
    window.addEventListener('mouseup', endStroke);
    wbCanvas.addEventListener('touchstart', e => { e.preventDefault(); const p = px(e); startStroke(p.x, p.y); }, { passive: false });
    wbCanvas.addEventListener('touchmove', e => { e.preventDefault(); const p = px(e); drawTo(p.x, p.y); }, { passive: false });
    window.addEventListener('touchend', endStroke);
  }

  /* Tabs */
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const mode = tab.dataset.tab;
      activeMode = mode;
      tabs.forEach(t => t.classList.toggle('active', t === tab));
      panes.forEach(p => {
        if (p.classList.contains('wb-' + mode)) p.removeAttribute('hidden');
        else p.setAttribute('hidden', '');
      });
    });
  });

  /* Color picker */
  colorBtns.forEach(b => {
    b.addEventListener('click', () => {
      strokeColor = b.dataset.color;
      colorBtns.forEach(c => c.classList.toggle('active', c === b));
    });
  });

  /* Clear */
  if (clearBtn) clearBtn.addEventListener('click', () => {
    if (activeMode === 'draw') { setupCanvas(); }
    else if (wbText) { wbText.value = ''; }
  });

  /* Submit */
  const renderTextToCanvas = (text) => {
    const cv = document.createElement('canvas');
    cv.width = 512; cv.height = 360;
    const ctx2 = cv.getContext('2d');
    ctx2.fillStyle = '#fbf8f1';
    ctx2.fillRect(0, 0, cv.width, cv.height);
    /* small grid */
    ctx2.strokeStyle = 'rgba(21,20,15,0.05)';
    ctx2.lineWidth = 1;
    for (let y = 0; y < cv.height; y += 30) {
      ctx2.beginPath(); ctx2.moveTo(0, y); ctx2.lineTo(cv.width, y); ctx2.stroke();
    }
    /* idea no */
    ctx2.fillStyle = '#15140f';
    ctx2.font = 'italic 28px Instrument Serif, Times New Roman, serif';
    ctx2.fillText('Idea no. ' + (count + 1), 24, 50);
    /* text body */
    ctx2.font = '18px Inter, sans-serif';
    ctx2.fillStyle = '#15140f';
    const words = (text || '(blank)').split(/\s+/);
    let line = '';
    let y = 90;
    const maxW = cv.width - 48;
    for (let i = 0; i < words.length; i++) {
      const test = line + words[i] + ' ';
      if (ctx2.measureText(test).width > maxW) {
        ctx2.fillText(line, 24, y);
        line = words[i] + ' ';
        y += 26;
        if (y > cv.height - 40) break;
      } else line = test;
    }
    ctx2.fillText(line, 24, y);
    /* accent stripe */
    ctx2.fillStyle = '#c77b2c';
    ctx2.fillRect(0, cv.height - 8, cv.width, 8);
    return cv;
  };

  const flashSubmit = () => {
    if (!submitBtn) return;
    submitBtn.classList.add('sent');
    const orig = submitBtn.innerHTML;
    submitBtn.innerHTML = '<span>Dropped ✓</span><span class="ico">↓</span>';
    setTimeout(() => {
      submitBtn.classList.remove('sent');
      submitBtn.innerHTML = orig;
    }, 1600);
  };

  if (submitBtn) {
    submitBtn.addEventListener('click', () => {
      let cv;
      if (activeMode === 'draw') {
        if (!wbCanvas) return;
        if (strokes < 2) {
          cv = renderTextToCanvas('(sketch)');
        } else {
          cv = document.createElement('canvas');
          cv.width = wbCanvas.width;
          cv.height = wbCanvas.height;
          const c2 = cv.getContext('2d');
          c2.drawImage(wbCanvas, 0, 0);
          /* accent stripe */
          c2.fillStyle = '#c77b2c';
          c2.fillRect(0, cv.height - 8, cv.width, 8);
          c2.fillStyle = '#15140f';
          c2.font = '14px JetBrains Mono, monospace';
          c2.fillText('IDEA NO. ' + String(count + 1).padStart(2, '0'), 12, 22);
        }
      } else {
        cv = renderTextToCanvas((wbText && wbText.value) || '');
      }
      crumpleAndDrop(cv);
      flashSubmit();
      /* Clear board after submit */
      setTimeout(() => {
        if (activeMode === 'draw') setupCanvas();
        else if (wbText) wbText.value = '';
      }, 600);
    });
  }

  /* ============== Render loop ============== */
  let t = 0;
  let targetRotY = 0;
  let curRotY = 0;

  mount.addEventListener('mousemove', (e) => {
    const r = mount.getBoundingClientRect();
    const nx = ((e.clientX - r.left) / r.width - 0.5) * 2;
    targetRotY = nx * 0.3;
  });
  mount.addEventListener('mouseleave', () => { targetRotY = 0; });

  const animate = () => {
    requestAnimationFrame(animate);
    t += 0.016;
    curRotY += (targetRotY - curRotY) * 0.05;
    scene.rotation.y = curRotY + Math.sin(t * 0.3) * 0.02;
    /* Glow throb */
    glow.material.opacity = 0.32 + Math.sin(t * 1.6) * 0.08;
    /* Idea balls jiggle subtly */
    ideas.forEach(i => {
      i.mesh.position.y = i.settledY + Math.sin(t * 1.4 + i.jitterPhase) * 0.003;
    });
    renderer.render(scene, camera);
  };
  animate();
})();
