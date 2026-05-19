"use client";

import { useRef, useEffect } from "react";

interface Props {
  /** Força tema claro (true) ou escuro (false). Omitir = auto-detecta via html.light */
  light?: boolean;
}

export default function GlobeBackground({ light }: Props) {
  const canvasRef  = useRef<HTMLCanvasElement>(null);
  const lightRef   = useRef<boolean>(light ?? false);

  // Mantém lightRef sincronizado com a prop
  useEffect(() => {
    if (light !== undefined) lightRef.current = light;
  }, [light]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animId: number;
    let t = 0;

    // Se nenhuma prop foi passada, detecta pelo html.light e observa mudanças
    if (light === undefined) {
      lightRef.current = document.documentElement.classList.contains("light");
      const obs = new MutationObserver(() => {
        lightRef.current = document.documentElement.classList.contains("light");
      });
      obs.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });
      // cleanup no return abaixo captura obs
      const cleanup = () => obs.disconnect();
      canvas.dataset.obsCleanup = "1";
      (canvas as unknown as { _obsCleanup: () => void })._obsCleanup = cleanup;
    }

    function resize() {
      if (!canvas) return;
      canvas.width  = canvas.offsetWidth;
      canvas.height = canvas.offsetHeight;
    }
    resize();
    window.addEventListener("resize", resize);

    const nodes = Array.from({ length: 28 }, () => ({
      theta: Math.random() * Math.PI,
      phi:   Math.random() * Math.PI * 2,
      speed: (Math.random() - 0.5) * 0.004,
    }));

    function project(x: number, y: number, z: number, rotY: number) {
      const rx  = x * Math.cos(rotY) + z * Math.sin(rotY);
      const rz  = -x * Math.sin(rotY) + z * Math.cos(rotY);
      const til = 0.28;
      const ry2 = y  * Math.cos(til) - rz * Math.sin(til);
      const rz2 = y  * Math.sin(til) + rz * Math.cos(til);
      const fov   = 2.2;
      const scale = fov / (fov + rz2 * 0.25);
      if (!canvas) return { sx: 0, sy: 0, z: rz2, alpha: 0.5 };
      const R  = Math.min(canvas.width, canvas.height) * 0.38;
      const cx = canvas.width  * 0.50;
      const cy = canvas.height * 0.46;
      return { sx: cx + R * rx * scale, sy: cy + R * ry2 * scale, z: rz2, alpha: Math.max(0, (rz2 + 1) / 2) };
    }

    function draw() {
      if (!canvas || !ctx) return;
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      const isLight = lightRef.current;
      const rotY  = t * 0.10;
      // Modo claro: azul marinho mais escuro, opacidade aumentada para contraste sobre branco
      const col   = isLight ? "30,58,138" : "140,160,255";  // blue-900 no claro
      const baseA = isLight ? 0.55 : 0.22;                   // bem mais visível no fundo branco
      const R     = Math.min(canvas.width, canvas.height) * 0.38;

      // Paralelos
      for (let lat = -60; lat <= 60; lat += 30) {
        const theta = ((90 - lat) * Math.PI) / 180;
        const yc = Math.cos(theta), rc = Math.sin(theta);
        ctx.beginPath();
        let first = true;
        for (let lon = 0; lon <= 362; lon += 3) {
          const phi = (lon * Math.PI) / 180;
          const p = project(rc * Math.cos(phi), yc, rc * Math.sin(phi), rotY);
          first ? ctx.moveTo(p.sx, p.sy) : ctx.lineTo(p.sx, p.sy);
          first = false;
        }
        ctx.strokeStyle = `rgba(${col},${baseA * 0.55})`;
        ctx.lineWidth   = 0.6;
        ctx.stroke();
      }

      // Meridianos
      for (let lon = 0; lon < 360; lon += 30) {
        const phi = (lon * Math.PI) / 180;
        ctx.beginPath();
        let first = true;
        for (let lat = -90; lat <= 90; lat += 2) {
          const theta = ((90 - lat) * Math.PI) / 180;
          const p = project(Math.sin(theta) * Math.cos(phi), Math.cos(theta), Math.sin(theta) * Math.sin(phi), rotY);
          first ? ctx.moveTo(p.sx, p.sy) : ctx.lineTo(p.sx, p.sy);
          first = false;
        }
        ctx.strokeStyle = `rgba(${col},${baseA * 0.55})`;
        ctx.lineWidth   = 0.6;
        ctx.stroke();
      }

      // Equador destaque
      ctx.beginPath();
      let firstEq = true;
      for (let lon = 0; lon <= 362; lon += 2) {
        const phi = (lon * Math.PI) / 180;
        const p   = project(Math.cos(phi), 0, Math.sin(phi), rotY);
        firstEq ? ctx.moveTo(p.sx, p.sy) : ctx.lineTo(p.sx, p.sy);
        firstEq = false;
      }
      ctx.strokeStyle = `rgba(${col},${baseA * 0.9})`;
      ctx.lineWidth   = 1;
      ctx.stroke();

      // Atualiza nós
      nodes.forEach(n => { n.phi += n.speed; });
      const pts = nodes.map(n => {
        const x = Math.sin(n.theta) * Math.cos(n.phi);
        const y = Math.cos(n.theta);
        const z = Math.sin(n.theta) * Math.sin(n.phi);
        return project(x, y, z, rotY);
      });

      // Conexões
      for (let i = 0; i < pts.length; i++) {
        for (let j = i + 1; j < pts.length; j++) {
          const d = Math.hypot(pts[i].sx - pts[j].sx, pts[i].sy - pts[j].sy);
          if (d < R * 0.42) {
            const a = (1 - d / (R * 0.42)) * baseA * ((pts[i].alpha + pts[j].alpha) / 2);
            ctx.beginPath();
            ctx.moveTo(pts[i].sx, pts[i].sy);
            ctx.lineTo(pts[j].sx, pts[j].sy);
            ctx.strokeStyle = `rgba(${col},${a})`;
            ctx.lineWidth   = 0.5;
            ctx.stroke();
          }
        }
      }

      // Pontos
      pts.forEach(p => {
        ctx.beginPath();
        ctx.arc(p.sx, p.sy, 1.4 + p.alpha * 1.6, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${col},${baseA * 1.8 * p.alpha})`;
        ctx.fill();
      });

      t += 0.016;
      animId = requestAnimationFrame(draw);
    }

    draw();

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener("resize", resize);
      const c = canvas as unknown as { _obsCleanup?: () => void };
      c._obsCleanup?.();
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // roda uma vez — lightRef é lido dinamicamente a cada frame

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 w-full h-full pointer-events-none"
      style={{ zIndex: 0 }}
      aria-hidden="true"
    />
  );
}
