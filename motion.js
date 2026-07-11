/* ===========================================================
   THIMI TECH — motion.js
   Scroll-anchored choreography built on GSAP + ScrollTrigger + Lenis.
   Replaces scroll.js. Degrades gracefully without the CDN libs,
   and respects prefers-reduced-motion throughout.
   =========================================================== */

window.ThimiViz = window.ThimiViz || { hidden: new Set() };

(() => {
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const hasGSAP = typeof gsap !== 'undefined' && typeof ScrollTrigger !== 'undefined';
  if (!hasGSAP) document.documentElement.classList.add('no-motion');

  /* ---------- Motion tokens ---------- */
  const EASE = {
    out: 'power3.out',
    io: 'power2.inOut',
    overshoot: 'back.out(1.6)',
    soft: 'sine.out',
  };
  const DUR = { fast: 0.35, base: 0.7, slow: 1.1, cinematic: 1.6 };

  if (hasGSAP) gsap.registerPlugin(ScrollTrigger);

  /* ============================================================
     LENIS — buttery smooth scroll, synced to GSAP's ticker
     ============================================================ */
  let lenis = null;
  if (hasGSAP && !reduced && typeof Lenis !== 'undefined') {
    lenis = new Lenis({ duration: 1.05, smoothWheel: true, syncTouch: false });
    lenis.on('scroll', ScrollTrigger.update);
    gsap.ticker.add((time) => lenis.raf(time * 1000));
    gsap.ticker.lagSmoothing(0);
  }

  /* ============================================================
     PERF — pause offscreen / backgrounded 3D scenes
     ============================================================ */
  (() => {
    const vizIds = ['globe', 'controller3d', 'bucket3d'];
    vizIds.forEach((id) => {
      const el = document.getElementById(id);
      if (!el || !('IntersectionObserver' in window)) return;
      const io = new IntersectionObserver(
        (entries) => {
          entries.forEach((en) => {
            if (en.isIntersecting) window.ThimiViz.hidden.delete(id);
            else window.ThimiViz.hidden.add(id);
          });
        },
        { threshold: 0.01 }
      );
      io.observe(el);
    });
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) vizIds.forEach((id) => window.ThimiViz.hidden.add(id));
      else vizIds.forEach((id) => window.ThimiViz.hidden.delete(id));
    });
  })();

  /* ============================================================
     LOADER — tracks real page load + a graceful minimum hold,
     then hands off directly into the hero entrance timeline
     ============================================================ */
  const loader = document.querySelector('.loader');
  const bar = document.querySelector('.loader-bar');
  const num = document.querySelector('.loader-mark .num');
  const runHeroEntrance = () => {
    if (!hasGSAP) return;
    const words = document.querySelectorAll('.hero-title .word');
    const tl = gsap.timeline({ defaults: { ease: EASE.out } });
    tl.set(words, { yPercent: 110 })
      .set('.eyebrow, .hero-meta, .hero-sub, .hero-actions, .hero-foot', { opacity: 0 })
      .set('.hero-globe-wrap', { opacity: 0, scale: 0.92 })
      .to('.hero-meta', { opacity: 1, duration: DUR.base }, 0)
      .to('.eyebrow', { opacity: 1, duration: DUR.base }, 0.1)
      .to(words, { yPercent: 0, duration: DUR.slow, stagger: 0.09 }, 0.16)
      .to('.hero-sub', { opacity: 1, duration: DUR.base }, 0.55)
      .to('.hero-actions', { opacity: 1, duration: DUR.base }, 0.68)
      .to('.hero-globe-wrap', { opacity: 1, scale: 1, duration: DUR.cinematic, ease: EASE.overshoot }, 0.35)
      .to('.hero-foot', { opacity: 1, duration: DUR.base }, 0.9);
  };

  if (loader) {
    let p = 0;
    let loaded = false;
    const minHoldMs = 900;
    const startedAt = performance.now();
    const setPct = (val) => {
      p = Math.min(100, val);
      if (bar) bar.style.setProperty('--p', (p / 100).toFixed(3));
      if (num) num.textContent = String(Math.floor(p)).padStart(3, '0');
    };
    const finish = () => {
      const elapsed = performance.now() - startedAt;
      const wait = Math.max(0, minHoldMs - elapsed);
      setTimeout(() => {
        setPct(100);
        setTimeout(() => {
          loader.classList.add('done');
          runHeroEntrance();
        }, 220);
      }, wait);
    };
    /* Simulated-but-bounded progress until the real load event lands */
    const tick = () => {
      if (loaded) return;
      setPct(p + Math.random() * 10 + 4);
      if (p < 92) setTimeout(tick, 90);
    };
    tick();
    window.addEventListener('load', () => { loaded = true; finish(); });
    /* Safety net if load never fires cleanly */
    setTimeout(() => { if (!loaded) { loaded = true; finish(); } }, 4500);
  } else {
    runHeroEntrance();
  }

  /* ============================================================
     NAV — scrolled state + active-section underline
     ============================================================ */
  (() => {
    const nav = document.querySelector('.nav');
    const links = document.querySelectorAll('.nav-center a');
    if (!nav) return;

    const onScroll = () => {
      if (window.scrollY > 30) nav.classList.add('scrolled');
      else nav.classList.remove('scrolled');
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();

    if (!links.length || !('IntersectionObserver' in window)) return;
    const center = document.querySelector('.nav-center');
    let pill = center && center.querySelector('.nav-active-pill');
    if (center && !pill) {
      pill = document.createElement('span');
      pill.className = 'nav-active-pill';
      center.appendChild(pill);
    }
    const movePill = (link) => {
      if (!pill || !link) return;
      links.forEach((l) => l.classList.toggle('active', l === link));
      const cr = center.getBoundingClientRect();
      const lr = link.getBoundingClientRect();
      const x = lr.left - cr.left;
      if (hasGSAP) {
        gsap.to(pill, { x, width: lr.width, duration: DUR.fast, ease: EASE.io, opacity: 1 });
      } else {
        pill.style.transform = `translateX(${x}px)`;
        pill.style.width = lr.width + 'px';
        pill.style.opacity = 1;
      }
    };
    const sections = Array.from(links)
      .map((l) => document.querySelector(l.getAttribute('href')))
      .filter(Boolean);
    const sectionIO = new IntersectionObserver(
      (entries) => {
        entries.forEach((en) => {
          if (!en.isIntersecting) return;
          const id = '#' + en.target.id;
          const link = document.querySelector(`.nav-center a[href="${id}"]`);
          if (link) movePill(link);
        });
      },
      { rootMargin: '-45% 0px -45% 0px' }
    );
    sections.forEach((s) => sectionIO.observe(s));
  })();

  /* ---------- Clock ---------- */
  const clock = document.getElementById('clock');
  if (clock) {
    const fmt = () => {
      try {
        const d = new Date();
        const opts = { hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Kathmandu', hour12: false };
        clock.textContent = d.toLocaleTimeString('en-GB', opts) + ' Kathmandu';
      } catch (e) { clock.textContent = ''; }
    };
    fmt();
    setInterval(fmt, 30 * 1000);
  }

  /* ---------- Reveal on intersect (unchanged, still cheap) ---------- */
  const io = new IntersectionObserver(
    (entries) => {
      entries.forEach((en) => {
        if (en.isIntersecting) {
          en.target.classList.add('in');
          io.unobserve(en.target);
        }
      });
    },
    { threshold: 0.15, rootMargin: '0px 0px -8% 0px' }
  );
  document.querySelectorAll('.reveal-up').forEach((el) => io.observe(el));

  if (!hasGSAP) return; /* everything below needs GSAP/ScrollTrigger */

  /* ============================================================
     HERO — scroll-scrubbed exit: globe drifts & scales, title
     splits apart as the page moves into the flicker section
     ============================================================ */
  if (!reduced) {
    const hero = document.querySelector('.hero');
    if (hero) {
      gsap.timeline({
        scrollTrigger: { trigger: hero, start: 'top top', end: 'bottom top', scrub: 0.6 },
      })
        .to('.hero-globe-wrap', { yPercent: -18, scale: 1.12, opacity: 0.35, ease: 'none' }, 0)
        .to('.hero-title .word', { yPercent: -60, opacity: 0, stagger: 0.04, ease: 'none' }, 0)
        .to('.hero-sub, .hero-actions, .hero-meta', { opacity: 0, y: -20, ease: 'none' }, 0);
    }
  }

  /* ---------- Magnetic buttons ---------- */
  (() => {
    if (reduced || matchMedia('(hover: none)').matches) return;
    const targets = document.querySelectorAll('.hero-actions .btn-primary, .hero-actions .btn-ghost, .nav-cta');
    targets.forEach((el) => {
      const strength = 0.35;
      el.addEventListener('mousemove', (e) => {
        const r = el.getBoundingClientRect();
        const x = (e.clientX - r.left - r.width / 2) * strength;
        const y = (e.clientY - r.top - r.height / 2) * strength;
        gsap.to(el, { x, y, duration: 0.4, ease: EASE.out });
      });
      el.addEventListener('mouseleave', () => {
        gsap.to(el, { x: 0, y: 0, duration: 0.5, ease: 'elastic.out(1, 0.4)' });
      });
    });
  })();

  /* ============================================================
     SERVICES RAIL — pin + scrub + snap, card-by-card choreography
     ============================================================ */
  (() => {
    const rail = document.querySelector('.services-rail');
    const track = document.querySelector('.services-track');
    const progBar = document.querySelector('.services-head .bar');
    const progNow = document.querySelector('.services-head .now');
    const cards = gsap.utils.toArray('.service-card');
    if (!rail || !track || !cards.length) return;

    const getMaxX = () => {
      const pad = parseInt(getComputedStyle(document.documentElement).getPropertyValue('--pad-x')) || 32;
      return track.scrollWidth - window.innerWidth + pad * 2;
    };

    const cardParts = cards.map((card) => ({
      art: card.querySelector('.service-art'),
      rest: [card.querySelector('h3'), card.querySelector('.more')].filter(Boolean),
    }));

    let st;
    const build = () => {
      if (window.innerWidth < 880) {
        gsap.set(track, { x: 0 });
        gsap.set(cardParts.map((c) => c.art), { clearProps: 'all' });
        gsap.set(cardParts.flatMap((c) => c.rest), { clearProps: 'all' });
        if (st) st.kill();
        return;
      }
      const maxX = getMaxX();
      const skewTo = gsap.quickTo(track, 'skewX', { duration: 0.5, ease: EASE.out });
      let skewIdle;
      st = ScrollTrigger.create({
        trigger: rail,
        start: 'top top',
        end: 'bottom bottom',
        scrub: reduced ? false : 0.8,
        snap: reduced ? undefined : 1 / (cards.length - 1),
        onUpdate: (self) => {
          const pct = self.progress;
          gsap.set(track, { x: -pct * maxX });
          if (!reduced) {
            skewTo(gsap.utils.clamp(-6, 6, self.getVelocity() / -300));
            clearTimeout(skewIdle);
            skewIdle = setTimeout(() => skewTo(0), 80);
          }
          if (progBar) progBar.style.setProperty('--p', pct.toFixed(3));
          if (progNow) {
            const idx = Math.min(cards.length, Math.floor(pct * cards.length) + 1);
            progNow.textContent = String(idx).padStart(2, '0');
          }
          if (!reduced) {
            const focus = pct * (cards.length - 1);
            cardParts.forEach((c, i) => {
              const t = gsap.utils.clamp(0, 1, 1 - Math.abs(focus - i));
              if (c.art) gsap.set(c.art, { opacity: gsap.utils.mapRange(0, 1, 0.35, 1, t), scale: gsap.utils.mapRange(0, 1, 0.9, 1, t), y: gsap.utils.mapRange(0, 1, 16, 0, t) });
              gsap.set(c.rest, { opacity: gsap.utils.mapRange(0, 1, 0.4, 1, t) });
            });
          }
        },
      });
    };
    build();
    window.addEventListener('resize', () => {
      if (st) st.kill();
      build();
      ScrollTrigger.refresh();
    });
  })();

  /* ============================================================
     FLICKER — scramble fires on entry instead of a bare timer,
     pauses entirely while offscreen
     ============================================================ */
  (() => {
    const section = document.querySelector('.flicker');
    const flick = document.querySelector('.flicker-text');
    if (!section || !flick) return;
    const phrases = ['Reality, into Vision', 'Vision, into Reality'];
    const charset = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ#@$%&*/\\-+=<>?:;,.';
    let idx = 0;
    let active = false;
    let loopHandle = null;

    const scramble = (target, duration = 600) => {
      const start = performance.now();
      const orig = target;
      const step = (now) => {
        const t = Math.min(1, (now - start) / duration);
        const revealLen = Math.floor(orig.length * t);
        let out = '';
        for (let i = 0; i < orig.length; i++) {
          if (orig[i] === ' ' || orig[i] === ',') { out += orig[i]; continue; }
          out += i < revealLen ? orig[i] : charset[Math.floor(Math.random() * charset.length)];
        }
        flick.textContent = out;
        flick.setAttribute('data-text', out);
        if (t < 1) requestAnimationFrame(step);
        else { flick.textContent = orig; flick.setAttribute('data-text', orig); }
      };
      requestAnimationFrame(step);
    };

    const jitter = () => {
      if (!active) return;
      if (Math.random() < 0.55) {
        flick.style.setProperty('--jx', (Math.random() - 0.5) * 18 + 'px');
        flick.style.setProperty('--jy', (Math.random() - 0.5) * 8 + 'px');
      } else {
        flick.style.setProperty('--jx', '0px');
        flick.style.setProperty('--jy', '0px');
      }
      loopHandle = setTimeout(jitter, 120 + Math.random() * 300);
    };

    let swapInterval = null;
    ScrollTrigger.create({
      trigger: section,
      start: 'top bottom',
      end: 'bottom top',
      onEnter: () => { if (!active) { active = true; scramble(phrases[idx]); jitter(); swapInterval = setInterval(() => { idx = 1 - idx; scramble(phrases[idx]); }, 3800); } },
      onEnterBack: () => { if (!active) { active = true; jitter(); swapInterval = setInterval(() => { idx = 1 - idx; scramble(phrases[idx]); }, 3800); } },
      onLeave: () => { active = false; clearTimeout(loopHandle); clearInterval(swapInterval); },
      onLeaveBack: () => { active = false; clearTimeout(loopHandle); clearInterval(swapInterval); },
    });
  })();

  /* ============================================================
     PROJECTS — internal image parallax + cursor-follow "View" pill
     ============================================================ */
  (() => {
    const projects = document.querySelectorAll('.project');
    if (!projects.length) return;

    projects.forEach((p) => {
      const img = p.querySelector('.thumb img');
      if (img && !reduced) {
        gsap.set(img, { scale: 1.14 });
        gsap.to(img, {
          yPercent: 8,
          ease: 'none',
          scrollTrigger: { trigger: p, start: 'top bottom', end: 'bottom top', scrub: 0.6 },
        });
      }

      if (matchMedia('(hover: none)').matches) return;
      const pill = document.createElement('span');
      pill.className = 'view-pill';
      pill.textContent = 'View ↗';
      p.querySelector('.thumb').appendChild(pill);
      gsap.set(pill, { xPercent: -50, yPercent: -50, scale: 0.7 });
      p.addEventListener('mousemove', (e) => {
        const r = p.getBoundingClientRect();
        gsap.to(pill, { x: e.clientX - r.left, y: e.clientY - r.top, duration: 0.5, ease: EASE.out });
      });
      p.addEventListener('mouseenter', () => gsap.to(pill, { opacity: 1, scale: 1, duration: 0.3 }));
      p.addEventListener('mouseleave', () => gsap.to(pill, { opacity: 0, scale: 0.7, duration: 0.3 }));
    });
  })();

  /* ============================================================
     MISSION — tile stagger rise + gem line-icon draw-in
     ============================================================ */
  (() => {
    const tiles = gsap.utils.toArray('.mission-tile');
    if (!tiles.length || reduced) return;
    tiles.forEach((tile) => {
      const paths = tile.querySelectorAll('.gem path');
      paths.forEach((p) => {
        const len = p.getTotalLength ? p.getTotalLength() : 0;
        if (!len) return;
        gsap.set(p, { strokeDasharray: len, strokeDashoffset: len });
        gsap.to(p, {
          strokeDashoffset: 0, duration: 1.1, ease: EASE.io,
          scrollTrigger: { trigger: tile, start: 'top 82%', toggleActions: 'play none none reverse' },
        });
      });
    });
  })();

  /* ============================================================
     TEAM — mouse tilt on hover
     ============================================================ */
  (() => {
    if (reduced || matchMedia('(hover: none)').matches) return;
    document.querySelectorAll('.team-card').forEach((card) => {
      card.addEventListener('mousemove', (e) => {
        const r = card.getBoundingClientRect();
        const rx = ((e.clientY - r.top) / r.height - 0.5) * -8;
        const ry = ((e.clientX - r.left) / r.width - 0.5) * 8;
        gsap.to(card, { rotateX: rx, rotateY: ry, duration: 0.4, ease: EASE.out, transformPerspective: 800 });
      });
      card.addEventListener('mouseleave', () => {
        gsap.to(card, { rotateX: 0, rotateY: 0, duration: 0.6, ease: EASE.out });
      });
    });
  })();

  /* ============================================================
     HIRING — 3D tilt on the job ticket
     ============================================================ */
  (() => {
    if (reduced || matchMedia('(hover: none)').matches) return;
    const card = document.querySelector('.hiring-card');
    const art = document.querySelector('.hiring-art');
    if (!card || !art) return;
    card.addEventListener('mousemove', (e) => {
      const r = card.getBoundingClientRect();
      const rx = ((e.clientY - r.top) / r.height - 0.5) * -10;
      const ry = ((e.clientX - r.left) / r.width - 0.5) * 10;
      gsap.to(art, { rotateX: rx, rotateY: ry, duration: 0.5, ease: EASE.out, transformPerspective: 900 });
    });
    card.addEventListener('mouseleave', () => {
      gsap.to(art, { rotateX: 0, rotateY: 0, duration: 0.7, ease: EASE.out });
    });
  })();

  /* ============================================================
     CTA / IDEA BUCKET — entrance choreography
     ============================================================ */
  (() => {
    const cta = document.querySelector('.cta');
    if (!cta || reduced) return;
    gsap.from('.cta-head > *', {
      opacity: 0, y: 26, duration: 0.8, stagger: 0.1, ease: EASE.out,
      scrollTrigger: { trigger: '.cta-head', start: 'top 80%' },
    });
    gsap.from('.whiteboard', {
      opacity: 0, x: -30, duration: 0.9, ease: EASE.out,
      scrollTrigger: { trigger: '.idea-stage', start: 'top 78%' },
    });
    gsap.from('.bucket-wrap', {
      opacity: 0, x: 30, duration: 0.9, ease: EASE.out,
      scrollTrigger: { trigger: '.idea-stage', start: 'top 78%' },
    });
  })();

  /* ============================================================
     FOOTER — rises in as a closing note; CTA settles behind it
     ============================================================ */
  (() => {
    const footer = document.querySelector('.footer');
    const cta = document.querySelector('.cta');
    if (!footer || reduced) return;
    gsap.from(footer, {
      opacity: 0, y: 48, duration: 1, ease: EASE.out,
      scrollTrigger: { trigger: footer, start: 'top 92%' },
    });
    if (cta) {
      gsap.to(cta, {
        scale: 0.97, filter: 'brightness(0.85)', ease: 'none',
        scrollTrigger: { trigger: footer, start: 'top bottom', end: 'top 60%', scrub: 0.6 },
      });
    }
  })();

  ScrollTrigger.refresh();
})();
