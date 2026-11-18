"use client";

import { useEffect, useState } from "react";

export function useViewport() {
  const [width, setWidth] = useState(1280);

  useEffect(() => {
    const update = () => setWidth(window.innerWidth);
    update();
    window.addEventListener("resize", update);
    return () => window.removeEventListener("resize", update);
  }, []);

  return {
    width,
    isMobile: width < 760,
    isDesktop: width >= 1100,
  };
}
