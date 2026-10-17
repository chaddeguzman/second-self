// [BACKGROUND:ORBIT] Project a slowly turning 3D sky; own all work only while enabled.
(() => {
  "use strict";
  const modules = (window.IntroModules ||= {});
  modules.createOrbitStarfield = ({ root = document, random = Math.random } = {}) => {
    const turnDuration = 720000 / (1.3 * 1.2);
    const frameInterval = 1000 / 30;
    let canvas = null;
    let context = null;
    let motion = null;
    let frame = null;
    let redrawNeeded = false;
    let disposed = false;
    let stars = [];
    let width = 0;
    let height = 0;
    let focal = 0;
    let angle = 0;
    let motionTime = 0;
    let lastTime = 0;
    let lastPaint = 0;

    function prepareSky() {
      redrawNeeded = false;
      width = Math.max(1, window.innerWidth);
      height = Math.max(1, window.innerHeight);
      focal = width * 0.65;
      const resolution = Math.min(window.devicePixelRatio || 1, 1.25, 2560 / Math.max(width, height));
      canvas.width = Math.floor(width * resolution);
      canvas.height = Math.floor(height * resolution);
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      context.setTransform(canvas.width / width, 0, 0, canvas.height / height, 0, 0);
      const halfFov = Math.atan(width / (2 * focal));
      const verticalSpan = height / focal * 0.9;
      const visibleCount = width <= 760 ? 220 : 600;
      const count = Math.min(6000, Math.ceil(visibleCount * 1.8 * Math.PI / Math.sin(halfFov)));
      stars = Array.from({ length: count }, (_, i) => {
        const direction = i / count * Math.PI * 2;
        const distance = 1.2 + random() * 3;
        const y = (random() * 2 - 1) * verticalSpan * distance;
        const kind = random();
        const radius = kind < 0.65 ? 0.45 + random() * 0.45
          : kind < 0.93 ? 0.9 + random() * 0.45
          : kind < 0.985 ? 1.4 + random() * 0.65 : 2.2 + random() * 1.8;
        const opacity = 0.12 + random() * (kind < 0.985 ? 0.3 : 0.14);
        const shape = kind < 0.985 ? null : Array.from({ length: 6 }, (_, corner) => {
          const turn = corner * Math.PI / 3;
          const length = 0.65 + random() * 0.35;
          return [Math.cos(turn) * length, Math.sin(turn) * length];
        });
        return {
          x: Math.sin(direction) * distance, y, z: Math.cos(direction) * distance,
          radius, shape,
          // Seven in thirty: 40% more than one in six, spread around the sky.
          twinkle: !shape && (i * 7) % 30 < 7
            ? { period: 6000 + random() * 5000, phase: random() * Math.PI * 2 } : null,
          color: `rgba(${shape ? "170, 180, 198" : "235, 240, 250"}, ${opacity})`,
        };
      });
    }

    function paint() {
      context.clearRect(0, 0, width, height);
      const cosine = Math.cos(angle);
      const sine = Math.sin(angle);
      for (const star of stars) {
        // Turn around the vertical axis: in the first-person view stars sweep left.
        const x = star.x * cosine - star.z * sine;
        const z = star.z * cosine + star.x * sine;
        if (z <= 0.1) continue;
        const px = width / 2 + focal * x / z;
        const py = height / 2 + focal * star.y / z;
        if (px < -10 || px > width + 10 || py < -10 || py > height + 10) continue;
        const radius = star.radius * Math.min(1.8, Math.max(0.65, 1.8 / z));
        context.fillStyle = star.color;
        context.globalAlpha = star.twinkle && !motion.matches
          ? 0.78 + 0.22 * Math.sin(motionTime * Math.PI * 2 / star.twinkle.period + star.twinkle.phase)
          : 1;
        context.beginPath();
        if (!star.shape) {
          context.arc(px, py, radius, 0, Math.PI * 2);
        } else {
          star.shape.forEach(([sx, sy], index) => {
            if (index === 0) context.moveTo(px + sx * radius, py + sy * radius);
            else context.lineTo(px + sx * radius, py + sy * radius);
          });
          context.closePath();
        }
        context.fill();
      }
      context.globalAlpha = 1;
    }

    function schedule() {
      if (canvas && !document.hidden && frame === null && (redrawNeeded || !motion.matches)) {
        frame = requestAnimationFrame(tick);
      }
    }

    function tick(now) {
      frame = null;
      if (!canvas || document.hidden) return;
      if (!motion.matches) {
        const elapsed = now - lastTime;
        angle = (angle + elapsed * Math.PI * 2 / turnDuration) % (Math.PI * 2);
        motionTime += elapsed;
      }
      lastTime = now;
      const resized = redrawNeeded;
      if (resized) prepareSky();
      if (resized || now - lastPaint >= frameInterval - 0.1) {
        paint();
        lastPaint = now;
      }
      schedule();
    }

    function syncMotion() {
      if (frame !== null) cancelAnimationFrame(frame);
      frame = null;
      lastTime = performance.now();
      schedule();
    }

    function resize() {
      if (!canvas) return;
      redrawNeeded = true;
      schedule();
    }

    function turnOff() {
      if (frame !== null) cancelAnimationFrame(frame);
      frame = null;
      redrawNeeded = false;
      window.removeEventListener("resize", resize);
      document.removeEventListener("visibilitychange", syncMotion);
      motion?.removeEventListener("change", syncMotion);
      motion = null;
      if (canvas) {
        canvas.remove();
        canvas.width = canvas.height = 0;
      }
      stars = [];
      context = null;
      canvas = null;
      angle = 0;
      motionTime = 0;
      return false;
    }

    return {
      toggle() {
        if (disposed) return false;
        if (canvas) return turnOff();
        const sky = root.querySelector(".starfield");
        if (!sky) return false;
        canvas = document.createElement("canvas");
        context = canvas.getContext?.("2d");
        if (!context) return turnOff();
        canvas.className = "orbit-starfield";
        canvas.setAttribute("aria-hidden", "true");
        sky.append(canvas);
        motion = window.matchMedia("(prefers-reduced-motion: reduce)");
        window.addEventListener("resize", resize);
        document.addEventListener("visibilitychange", syncMotion);
        motion.addEventListener("change", syncMotion);
        prepareSky();
        paint();
        lastPaint = performance.now();
        syncMotion();
        return true;
      },
      dispose() { disposed = true; turnOff(); },
    };
  };
})();
