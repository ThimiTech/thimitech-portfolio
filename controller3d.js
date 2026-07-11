/* ===========================================================
   THIMI TECH — controller3d.js
   3D DualSense-style controller with clickable buttons.
   Each button calls into window.ThimiGlobe (exposed by globe.js).
   =========================================================== */

(() => {
  if (typeof THREE === 'undefined') return;
  const mount = document.getElementById('controller3d');
  if (!mount) return;

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(35, 1, 0.1, 100);
  camera.position.set(0, -1.3, 4.6);
  camera.lookAt(0, -0.35, 0);

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

  /* Lights */
  scene.add(new THREE.AmbientLight(0xffffff, 0.55));
  const key = new THREE.DirectionalLight(0xfff1d8, 1.2);
  key.position.set(2, 4, 4);
  scene.add(key);
  const rim = new THREE.DirectionalLight(0xc77b2c, 0.45);
  rim.position.set(-3, -1, 2);
  scene.add(rim);
  const fill = new THREE.DirectionalLight(0xffffff, 0.3);
  fill.position.set(0, -3, 2);
  scene.add(fill);

  /* ============== Materials ============== */
  const matBody    = new THREE.MeshPhongMaterial({ color: 0xece6d7, shininess: 60, specular: 0x444444 });
  const matAccent  = new THREE.MeshPhongMaterial({ color: 0x15140f, shininess: 40 });
  const matPad     = new THREE.MeshPhongMaterial({ color: 0xb8b0a0, shininess: 30 });
  const matStick   = new THREE.MeshPhongMaterial({ color: 0x15140f, shininess: 80, specular: 0x666666 });
  const matStickTop = new THREE.MeshPhongMaterial({ color: 0xc77b2c, shininess: 80 });
  const matBtnLight = new THREE.MeshPhongMaterial({ color: 0xf6f1e3, shininess: 50, specular: 0x333333 });

  /* ============== Body silhouette (extruded) ============== */
  const s = new THREE.Shape();
  s.moveTo(-1.7, 0.55);
  s.quadraticCurveTo(-1.0, 0.75, 0.0, 0.7);
  s.quadraticCurveTo(1.0, 0.75, 1.7, 0.55);
  s.quadraticCurveTo(2.05, 0.0, 1.55, -0.3);
  s.lineTo(1.05, -0.3);
  s.quadraticCurveTo(1.4, -1.0, 1.0, -1.25);
  s.quadraticCurveTo(0.4, -1.25, 0.25, -0.35);
  s.lineTo(-0.25, -0.35);
  s.quadraticCurveTo(-0.4, -1.25, -1.0, -1.25);
  s.quadraticCurveTo(-1.4, -1.0, -1.05, -0.3);
  s.lineTo(-1.55, -0.3);
  s.quadraticCurveTo(-2.05, 0.0, -1.7, 0.55);

  const bodyGeo = new THREE.ExtrudeGeometry(s, {
    depth: 0.42,
    bevelEnabled: true,
    bevelThickness: 0.06,
    bevelSize: 0.06,
    bevelSegments: 8,
    curveSegments: 32,
  });
  const body = new THREE.Mesh(bodyGeo, matBody);
  body.position.z = -0.21;
  scene.add(body);

  /* Top face plane reference (for placing items at z + small offset) */
  const FACE_Z = body.position.z + 0.42 + 0.06; // depth + bevel
  /* But after centering, our face is at z = 0.21 + 0.06 = 0.27 ish */
  const Z_TOP = 0.27;

  /* ============== Touchpad ============== */
  const padGeo = new THREE.BoxGeometry(1.0, 0.5, 0.04);
  const padCorners = new THREE.EdgesGeometry(padGeo);
  const touchpad = new THREE.Mesh(padGeo, matPad);
  touchpad.position.set(0, 0.2, Z_TOP);
  scene.add(touchpad);

  /* Light bar — thin emissive strip below touchpad */
  const lightBarMat = new THREE.MeshBasicMaterial({ color: 0xc77b2c });
  const lightBarGeo = new THREE.BoxGeometry(0.7, 0.04, 0.02);
  const lightBarFront = new THREE.Mesh(lightBarGeo, lightBarMat);
  lightBarFront.position.set(0, -0.08, Z_TOP - 0.02);
  scene.add(lightBarFront);

  /* ============== Buttons registry ============== */
  const buttons = [];
  const heldButtons = new Set();

  /* Helper to build a button */
  function makeButton({ geom, mat, pos, rot, id, glyph, tap, hold }) {
    const m = mat.clone();
    const mesh = new THREE.Mesh(geom, m);
    mesh.position.set(pos.x, pos.y, pos.z);
    if (rot) mesh.rotation.set(rot.x || 0, rot.y || 0, rot.z || 0);
    mesh.userData = { id, glyph, tap, hold, baseZ: pos.z, mat: m, originalHex: m.color.getHex() };
    scene.add(mesh);
    buttons.push(mesh);
    return mesh;
  }

  /* ============== D-PAD ============== */
  const dpadCenter = { x: -1.15, y: -0.15 };
  const dpadGeo = new THREE.BoxGeometry(0.28, 0.12, 0.08);
  const dpadGeoV = new THREE.BoxGeometry(0.12, 0.28, 0.08);
  makeButton({
    geom: dpadGeoV, mat: matAccent,
    pos: { x: dpadCenter.x, y: dpadCenter.y + 0.18, z: Z_TOP },
    id: 'up', glyph: '▲',
    hold: () => window.ThimiGlobe && window.ThimiGlobe.rotateBy(0, 0.012),
  });
  makeButton({
    geom: dpadGeoV, mat: matAccent,
    pos: { x: dpadCenter.x, y: dpadCenter.y - 0.18, z: Z_TOP },
    id: 'down', glyph: '▼',
    hold: () => window.ThimiGlobe && window.ThimiGlobe.rotateBy(0, -0.012),
  });
  makeButton({
    geom: dpadGeo, mat: matAccent,
    pos: { x: dpadCenter.x - 0.18, y: dpadCenter.y, z: Z_TOP },
    id: 'left', glyph: '◀',
    hold: () => window.ThimiGlobe && window.ThimiGlobe.rotateBy(-0.018, 0),
  });
  makeButton({
    geom: dpadGeo, mat: matAccent,
    pos: { x: dpadCenter.x + 0.18, y: dpadCenter.y, z: Z_TOP },
    id: 'right', glyph: '▶',
    hold: () => window.ThimiGlobe && window.ThimiGlobe.rotateBy(0.018, 0),
  });

  /* ============== Action buttons ============== */
  const actCenter = { x: 1.15, y: -0.15 };
  const actGeo = new THREE.CylinderGeometry(0.13, 0.13, 0.08, 24);
  /* Buttons need to face up (rotate around X) */
  const actRot = { x: Math.PI / 2 };

  /* Triangle (top) - reset view */
  const triangle = makeButton({
    geom: actGeo, mat: matBtnLight,
    pos: { x: actCenter.x, y: actCenter.y + 0.22, z: Z_TOP - 0.04 },
    rot: actRot,
    id: 'triangle', glyph: '△',
    tap: () => window.ThimiGlobe && window.ThimiGlobe.reset(),
  });
  /* Circle (right) - toggle auto-spin */
  const circle = makeButton({
    geom: actGeo, mat: matBtnLight,
    pos: { x: actCenter.x + 0.22, y: actCenter.y, z: Z_TOP - 0.04 },
    rot: actRot,
    id: 'circle', glyph: '○',
    tap: () => window.ThimiGlobe && window.ThimiGlobe.toggleAutoSpin(),
  });
  /* Cross (bottom) - satellite boost */
  const cross = makeButton({
    geom: actGeo, mat: matBtnLight,
    pos: { x: actCenter.x, y: actCenter.y - 0.22, z: Z_TOP - 0.04 },
    rot: actRot,
    id: 'cross', glyph: '✕',
    tap: () => window.ThimiGlobe && window.ThimiGlobe.satBoost(),
  });
  /* Square (left) - toggle satellite */
  const square = makeButton({
    geom: actGeo, mat: matBtnLight,
    pos: { x: actCenter.x - 0.22, y: actCenter.y, z: Z_TOP - 0.04 },
    rot: actRot,
    id: 'square', glyph: '□',
    tap: () => window.ThimiGlobe && window.ThimiGlobe.toggleSatellite(),
  });

  /* Glyphs on action buttons — small extruded shapes */
  function addGlyph(shape, x, y, z, color = 0x666666) {
    const geo = new THREE.ExtrudeGeometry(shape, { depth: 0.005, bevelEnabled: false });
    const mat = new THREE.MeshBasicMaterial({ color });
    const m = new THREE.Mesh(geo, mat);
    m.position.set(x, y, z);
    scene.add(m);
    return m;
  }
  /* △ */
  const triShape = new THREE.Shape();
  triShape.moveTo(0, 0.06);
  triShape.lineTo(0.055, -0.03);
  triShape.lineTo(-0.055, -0.03);
  triShape.lineTo(0, 0.06);
  addGlyph(triShape, actCenter.x, actCenter.y + 0.22, Z_TOP + 0.005, 0x6f5a3a);
  /* ○ */
  const circShape = new THREE.Shape();
  circShape.absarc(0, 0, 0.055, 0, Math.PI * 2);
  const circHole = new THREE.Path();
  circHole.absarc(0, 0, 0.035, 0, Math.PI * 2);
  circShape.holes.push(circHole);
  addGlyph(circShape, actCenter.x + 0.22, actCenter.y, Z_TOP + 0.005, 0x6f5a3a);
  /* □ */
  const sqShape = new THREE.Shape();
  sqShape.moveTo(-0.05, -0.05); sqShape.lineTo(0.05, -0.05); sqShape.lineTo(0.05, 0.05); sqShape.lineTo(-0.05, 0.05); sqShape.lineTo(-0.05, -0.05);
  const sqHole = new THREE.Path();
  sqHole.moveTo(-0.035, -0.035); sqHole.lineTo(0.035, -0.035); sqHole.lineTo(0.035, 0.035); sqHole.lineTo(-0.035, 0.035); sqHole.lineTo(-0.035, -0.035);
  sqShape.holes.push(sqHole);
  addGlyph(sqShape, actCenter.x - 0.22, actCenter.y, Z_TOP + 0.005, 0x6f5a3a);
  /* ✕ */
  const xShape1 = new THREE.Shape();
  xShape1.moveTo(-0.055, -0.045);
  xShape1.lineTo(-0.04, -0.06);
  xShape1.lineTo(0.055, 0.035);
  xShape1.lineTo(0.04, 0.05);
  xShape1.lineTo(-0.055, -0.045);
  addGlyph(xShape1, actCenter.x, actCenter.y - 0.22, Z_TOP + 0.005, 0x6f5a3a);
  const xShape2 = new THREE.Shape();
  xShape2.moveTo(0.055, -0.045);
  xShape2.lineTo(0.04, -0.06);
  xShape2.lineTo(-0.055, 0.035);
  xShape2.lineTo(-0.04, 0.05);
  xShape2.lineTo(0.055, -0.045);
  addGlyph(xShape2, actCenter.x, actCenter.y - 0.22, Z_TOP + 0.005, 0x6f5a3a);

  /* ============== Sticks ============== */
  function buildStick(x, y, id, holdFn) {
    const wellGeo = new THREE.CylinderGeometry(0.22, 0.22, 0.04, 32);
    const wellMat = matAccent.clone();
    const well = new THREE.Mesh(wellGeo, wellMat);
    well.position.set(x, y, Z_TOP - 0.04);
    well.rotation.x = Math.PI / 2;
    scene.add(well);

    const stickGeo = new THREE.CylinderGeometry(0.13, 0.16, 0.16, 32);
    const stick = new THREE.Mesh(stickGeo, matStick.clone());
    stick.position.set(x, y, Z_TOP + 0.04);
    stick.rotation.x = Math.PI / 2;
    scene.add(stick);

    const capGeo = new THREE.CylinderGeometry(0.135, 0.135, 0.05, 32);
    const cap = new THREE.Mesh(capGeo, matStickTop.clone());
    cap.position.set(x, y, Z_TOP + 0.1);
    cap.rotation.x = Math.PI / 2;
    cap.userData = { id, tap: holdFn, baseZ: cap.position.z, mat: cap.material, originalHex: cap.material.color.getHex() };
    scene.add(cap);
    buttons.push(cap);

    return { well, stick, cap };
  }
  const lstick = buildStick(-0.55, -0.55, 'lstick',
    () => window.ThimiGlobe && window.ThimiGlobe.satBoost()
  );
  const rstick = buildStick(0.55, -0.55, 'rstick',
    () => window.ThimiGlobe && window.ThimiGlobe.toggleAutoSpin()
  );

  /* ============== Shoulder buttons (L1/R1) ============== */
  const shoulderGeo = new THREE.BoxGeometry(0.45, 0.12, 0.18);
  makeButton({
    geom: shoulderGeo, mat: matBody,
    pos: { x: -1.4, y: 0.7, z: 0.0 },
    id: 'l1', glyph: 'L1',
    hold: () => window.ThimiGlobe && window.ThimiGlobe.zoomBy(0.02),
  });
  makeButton({
    geom: shoulderGeo, mat: matBody,
    pos: { x: 1.4, y: 0.7, z: 0.0 },
    id: 'r1', glyph: 'R1',
    hold: () => window.ThimiGlobe && window.ThimiGlobe.zoomBy(-0.02),
  });
  /* L2/R2 (triggers — angled boxes behind L1/R1) */
  const triggerGeo = new THREE.BoxGeometry(0.4, 0.18, 0.14);
  makeButton({
    geom: triggerGeo, mat: matBody,
    pos: { x: -1.4, y: 0.82, z: -0.16 },
    rot: { x: 0.4 },
    id: 'l2', glyph: 'L2',
    hold: () => window.ThimiGlobe && window.ThimiGlobe.zoomBy(0.05),
  });
  makeButton({
    geom: triggerGeo, mat: matBody,
    pos: { x: 1.4, y: 0.82, z: -0.16 },
    rot: { x: 0.4 },
    id: 'r2', glyph: 'R2',
    hold: () => window.ThimiGlobe && window.ThimiGlobe.zoomBy(-0.05),
  });

  /* ============== Share / Options ============== */
  const smallBtnGeo = new THREE.BoxGeometry(0.12, 0.05, 0.04);
  makeButton({
    geom: smallBtnGeo, mat: matAccent,
    pos: { x: -0.7, y: 0.45, z: Z_TOP - 0.02 },
    id: 'share', glyph: 'Share',
    tap: () => window.ThimiGlobe && window.ThimiGlobe.satTiltDown(),
  });
  makeButton({
    geom: smallBtnGeo, mat: matAccent,
    pos: { x: 0.7, y: 0.45, z: Z_TOP - 0.02 },
    id: 'options', glyph: 'Options',
    tap: () => window.ThimiGlobe && window.ThimiGlobe.satTiltUp(),
  });

  /* ============== Raycaster interaction ============== */
  const raycaster = new THREE.Raycaster();
  const mouseV = new THREE.Vector2();
  let hoverBtn = null;
  let activeBtn = null;

  const pressVisual = (btn) => {
    btn.position.z = btn.userData.baseZ - 0.05;
    btn.userData.mat.color.setHex(0xc77b2c);
    btn.userData.mat.emissive = new THREE.Color(0x331a00);
    btn.userData.mat.emissiveIntensity = 0.5;
  };
  const releaseVisual = (btn) => {
    btn.position.z = btn.userData.baseZ;
    btn.userData.mat.color.setHex(btn.userData.originalHex);
    if (btn.userData.mat.emissive) {
      btn.userData.mat.emissive = new THREE.Color(0x000000);
      btn.userData.mat.emissiveIntensity = 0;
    }
  };

  const pickButton = (clientX, clientY) => {
    const r = renderer.domElement.getBoundingClientRect();
    mouseV.x = ((clientX - r.left) / r.width) * 2 - 1;
    mouseV.y = -((clientY - r.top) / r.height) * 2 + 1;
    raycaster.setFromCamera(mouseV, camera);
    const hits = raycaster.intersectObjects(buttons, false);
    return hits.length ? hits[0].object : null;
  };

  const onPointerDown = (clientX, clientY) => {
    const btn = pickButton(clientX, clientY);
    if (!btn) return;
    activeBtn = btn;
    pressVisual(btn);
    if (btn.userData.tap) btn.userData.tap();
    if (btn.userData.hold) heldButtons.add(btn);
  };
  const onPointerUp = () => {
    if (activeBtn) releaseVisual(activeBtn);
    activeBtn = null;
    heldButtons.forEach(releaseVisual);
    heldButtons.clear();
  };
  const onPointerMove = (clientX, clientY) => {
    const btn = pickButton(clientX, clientY);
    if (btn !== hoverBtn) {
      hoverBtn = btn;
      renderer.domElement.style.cursor = btn ? 'pointer' : 'grab';
    }
  };

  const cv = renderer.domElement;
  cv.style.cursor = 'grab';
  cv.addEventListener('mousedown', e => { e.preventDefault(); onPointerDown(e.clientX, e.clientY); });
  window.addEventListener('mouseup', onPointerUp);
  cv.addEventListener('mousemove', e => onPointerMove(e.clientX, e.clientY));
  cv.addEventListener('touchstart', e => { onPointerDown(e.touches[0].clientX, e.touches[0].clientY); }, { passive: true });
  window.addEventListener('touchend', onPointerUp);

  /* ============== Subtle idle motion ============== */
  let t = 0;
  const group = new THREE.Group();
  /* Re-parent all scene children to a group for tilting */
  /* Easier: rotate everything via scene.rotation */
  let targetRotY = 0;
  let curRotY = 0;
  cv.addEventListener('mousemove', (e) => {
    const r = cv.getBoundingClientRect();
    const nx = ((e.clientX - r.left) / r.width - 0.5) * 2;
    targetRotY = nx * 0.18;
  });
  cv.addEventListener('mouseleave', () => { targetRotY = 0; });

  /* Hint glow on hover */
  const animate = () => {
    requestAnimationFrame(animate);
    if (window.ThimiViz && window.ThimiViz.hidden.has('controller3d')) return;
    t += 0.016;

    /* Subtle breathing */
    const breath = Math.sin(t * 1.2) * 0.015;
    scene.rotation.x = -0.05 + breath;
    curRotY += (targetRotY - curRotY) * 0.06;
    scene.rotation.y = curRotY + Math.sin(t * 0.4) * 0.02;

    /* Held buttons trigger continuous action */
    heldButtons.forEach(btn => {
      if (btn.userData.hold) btn.userData.hold();
    });

    /* Light bar pulse */
    const lbI = 0.6 + Math.sin(t * 2.2) * 0.4;
    lightBarFront.material.color.setRGB(0.78 * lbI, 0.48 * lbI, 0.17 * lbI);

    renderer.render(scene, camera);
  };
  animate();
})();
