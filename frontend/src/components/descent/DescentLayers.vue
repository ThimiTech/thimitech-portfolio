<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { canAnimate, gsap } from './motion'

/** Services, ordered the way a platform is actually built: from the imagery up to the decision. */
const layers = [
  { tag: 'Imagery', title: 'Remote Sensing & Earth Observation', text: 'Satellite imagery and remote sensing to monitor environmental change, assess land use and support evidence-based planning at district and national scale.' },
  { tag: 'Spatial data', title: 'WebGIS Development & Geospatial Solutions', text: 'Layers, imagery and field records become one map your team can search, filter and act on.' },
  { tag: 'Field capture', title: 'Mobile Application Development', text: 'From field data collection to offline mapping, apps that keep working where the signal does not.' },
  { tag: 'Application', title: 'Custom Software & Web Application Development', text: 'Secure, scalable software: the data model, the API and the interface your staff open every day.' },
  { tag: 'Insight', title: 'Data Analytics & Business Intelligence', text: 'Dashboards and reporting that people actually open, and trust enough to decide with.' },
  { tag: 'Decision', title: 'Real-World Problem Solving & Digital Innovation', text: 'We start from the decision you need to make, not from the tool.' },
]

const root = ref<HTMLElement | null>(null)
const active = ref(0)
let ctx: gsap.Context | undefined

onMounted(() => {
  if (!canAnimate || !root.value) return
  ctx = gsap.context(() => {
    gsap
      .timeline({
        scrollTrigger: {
          trigger: root.value,
          start: 'top top',
          end: '+=280%',
          pin: true,
          scrub: true,
          refreshPriority: 2,
          onUpdate: (self) => (active.value = Math.min(layers.length - 1, Math.floor(self.progress * layers.length))),
        },
      })
      // The stack fans open first, then stays open while each layer takes its turn.
      .fromTo('.iso', { '--gap': '7px' }, { '--gap': '58px', ease: 'power2.out', duration: 1 })
      .to({}, { duration: 5 })
  }, root.value)
})
onBeforeUnmount(() => ctx?.revert())
</script>

<template>
  <section id="services" ref="root" class="layers" :class="{ 'is-static': !canAnimate }" aria-labelledby="services-title">
    <div class="wrap grid">
      <div class="stage" aria-hidden="true">
        <div class="iso">
          <div v-for="(l, i) in layers" :key="l.tag" class="plate" :class="[`p${i}`, { on: active === i }]" :style="{ '--i': i }">
            <span>{{ l.tag }}</span>
          </div>
        </div>
      </div>

      <div class="side">
        <p class="kicker">Altitude 600 m · what we build</p>
        <h2 id="services-title">Every platform is a stack of layers.</h2>
        <ol>
          <li v-for="(l, i) in layers" :key="l.tag" :class="{ on: active === i }">
            <span class="num">L{{ i + 1 }}</span>
            <div>
              <h3>{{ l.title }}</h3>
              <div class="more"><p>{{ l.text }}</p></div>
            </div>
          </li>
        </ol>
      </div>
    </div>
  </section>
</template>

<style scoped>
.layers {
  display: flex;
  min-height: 100svh;
  align-items: center;
  overflow: hidden;
  padding-block: 88px 40px;
}
.grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1.05fr);
  align-items: center;
  gap: clamp(24px, 5vw, 88px);
}

/* Isometric stack: the plates share one footprint and are pushed apart along Z. */
.stage {
  display: grid;
  height: min(68svh, 620px);
  place-items: end center;
  padding-bottom: 6svh;
}
.iso {
  --gap: 58px;
  --size: clamp(190px, 21vw, 300px);
  position: relative;
  width: var(--size);
  height: var(--size);
  transform: rotateX(58deg) rotateZ(-45deg);
  transform-style: preserve-3d;
}
.plate {
  position: absolute;
  inset: 0;
  transform: translateZ(calc(var(--gap) * var(--i)));
  border: 1px solid rgb(242 239 232 / 0.3);
  background-color: rgb(12 16 20 / 0.82);
  opacity: 0.4;
  transition: opacity 0.35s ease, border-color 0.35s ease, box-shadow 0.35s ease;
}
.plate span {
  position: absolute;
  bottom: 8px;
  left: 10px;
  font: 400 10px/1 var(--font-mono);
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--fg);
}
.plate.on {
  border-color: var(--signal);
  box-shadow: 0 0 0 1px var(--signal), 0 0 46px rgb(255 90 31 / 0.3);
  opacity: 1;
}
.is-static .plate {
  opacity: 0.85;
}
/* One drawn texture per layer */
.p0 {
  background-image: radial-gradient(circle at 28% 34%, rgb(242 239 232 / 0.28), transparent 34%), radial-gradient(circle at 72% 66%, rgb(242 239 232 / 0.2), transparent 30%), radial-gradient(circle at 64% 22%, rgb(242 239 232 / 0.12), transparent 22%);
}
.p1 {
  background-image: linear-gradient(rgb(242 239 232 / 0.22) 1px, transparent 1px), linear-gradient(90deg, rgb(242 239 232 / 0.22) 1px, transparent 1px);
  background-size: 12.5% 12.5%;
}
.p2 {
  background-image: radial-gradient(rgb(242 239 232 / 0.6) 1.6px, transparent 2px);
  background-size: 14% 14%;
}
.p3 {
  background-image: repeating-linear-gradient(45deg, rgb(242 239 232 / 0.2) 0 1px, transparent 1px 14px);
}
.p4 {
  background-image: linear-gradient(0deg, rgb(242 239 232 / 0.4) 38%, transparent 38%), linear-gradient(0deg, rgb(242 239 232 / 0.4) 72%, transparent 72%), linear-gradient(0deg, rgb(242 239 232 / 0.4) 54%, transparent 54%), linear-gradient(0deg, rgb(242 239 232 / 0.4) 88%, transparent 88%);
  background-repeat: no-repeat;
  background-position: 16% 82%, 38% 82%, 60% 82%, 82% 82%;
  background-size: 12% 64%;
}
.p5 {
  background-image: radial-gradient(circle, var(--signal) 0 5%, transparent 5.5%), repeating-radial-gradient(circle, transparent 0 11%, rgb(242 239 232 / 0.3) 11% 11.6%);
}

h2 {
  margin: 16px 0 clamp(20px, 3svh, 36px);
}
ol {
  margin: 0;
  padding: 0;
  list-style: none;
}
li {
  display: grid;
  grid-template-columns: 44px 1fr;
  padding-block: clamp(9px, 1.5svh, 15px);
  border-top: 1px solid var(--line);
  color: var(--dim);
  transition: color 0.3s ease;
}
li.on,
.is-static li {
  color: var(--fg);
}
.num {
  padding-top: 5px;
  font: 400 11px/1 var(--font-mono);
  letter-spacing: 0.12em;
}
li.on .num {
  color: var(--signal);
}
h3 {
  margin: 0;
  font-size: clamp(17px, 1.55vw, 23px);
  font-weight: 500;
  line-height: 1.25;
  letter-spacing: -0.02em;
}
/* 0fr → 1fr animates the open height without measuring it */
.more {
  display: grid;
  grid-template-rows: 0fr;
  transition: grid-template-rows 0.4s ease;
}
.more p {
  min-height: 0;
  margin: 0;
  overflow: hidden;
  font-size: 15.5px;
  line-height: 1.55;
  color: var(--dim);
}
li.on .more,
.is-static .more {
  grid-template-rows: 1fr;
}
li.on .more p,
.is-static .more p {
  padding-top: 6px;
}

.is-static {
  min-height: 0;
  padding-block: 96px;
}

@media (max-width: 860px) {
  .grid {
    grid-template-columns: minmax(0, 1fr);
    gap: 0;
  }
  .stage {
    height: 34svh;
    padding-bottom: 2svh;
  }
  .iso {
    --size: 132px;
  }
  .layers:not(.is-static) .iso {
    scale: 0.8;
  }
  .more p {
    font-size: 14px;
  }
}
</style>
