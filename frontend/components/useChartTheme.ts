"use client";
import { useState, useEffect } from "react";

/**
 * Hook reutilizável para cores de gráficos recharts compatíveis com dark/light mode.
 * Uso: const ct = useChartTheme(); então passe ct.gridStroke, ct.tooltipStyle, etc.
 */
export function useChartTheme() {
  const [isLight, setIsLight] = useState(false);

  useEffect(() => {
    const check = () => setIsLight(document.documentElement.classList.contains("light"));
    check();
    const obs = new MutationObserver(check);
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });
    return () => obs.disconnect();
  }, []);

  return {
    isLight,
    gridStroke: isLight ? "#E2E8F0" : "#334155",
    tickFill: isLight ? "#475569" : "#94a3b8",
    axisStroke: isLight ? "#CBD5E1" : "#475569",
    lineStroke: isLight ? "#1E4976" : "#3b6ea5",
    tooltipStyle: {
      backgroundColor: isLight ? "#FFFFFF" : "#1e293b",
      border: `1px solid ${isLight ? "#E2E8F0" : "#475569"}`,
      borderRadius: 10,
      boxShadow: isLight ? "0 4px 12px rgba(0,0,0,0.08)" : "0 4px 16px rgba(0,0,0,0.3)",
      padding: "10px 14px",
    },
    tooltipLabelStyle: {
      color: isLight ? "#64748b" : "#94a3b8",
      fontSize: 11,
      fontWeight: 500,
    },
    tooltipItemStyle: {
      color: isLight ? "#475569" : "#e2e8f0",
      fontSize: 12,
    },
  };
}
