import React, { useState, useEffect, useRef, useCallback } from "react";
import { Sparkles, Terminal } from "lucide-react";

// Cute cybernetic easter egg voice-lines spoken by the Chrono Companion
const VOICE_LINES = [
  "SLA response thresholds: nominal.",
  "Autoencoder anomaly suppression: online.",
  "No timeline drifts detected.",
  "Telemetry stream verified. I am watching.",
  "FastAPI connection speed: optimal.",
  "Redis cache layer status: fully primed.",
  "Chronoshield at maximum power.",
  "Ready to shield your infrastructure."
];

export const Companion: React.FC = () => {
  const [status, setStatus] = useState<string>("SYSTEMS NOMINAL");
  const [bubbleText, setBubbleText] = useState<string | null>(null);
  const bubbleTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const leftEyeRef = useRef<SVGGElement | null>(null);
  const rightEyeRef = useRef<SVGGElement | null>(null);
  const leftPupilRef = useRef<SVGCircleElement | null>(null);
  const rightPupilRef = useRef<SVGCircleElement | null>(null);
  const shakeIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      const calculateOffset = (eyeElement: SVGGElement | null) => {
        if (!eyeElement) return { x: 0, y: 0 };
        const rect = eyeElement.getBoundingClientRect();
        
        // Find center of the eye in viewport coords
        const eyeCenterX = rect.left + rect.width / 2;
        const eyeCenterY = rect.top + rect.height / 2;
        
        const dx = e.clientX - eyeCenterX;
        const dy = e.clientY - eyeCenterY;
        const angle = Math.atan2(dy, dx);
        
        // Dynamic pupil limit tracking factor
        const maxDistance = 3.5; 
        const distance = Math.min(maxDistance, Math.hypot(dx, dy) / 25);
        
        return {
          x: Math.cos(angle) * distance,
          y: Math.sin(angle) * distance
        };
      };

      const leftOffset = calculateOffset(leftEyeRef.current);
      const rightOffset = calculateOffset(rightEyeRef.current);

      if (leftPupilRef.current) {
        leftPupilRef.current.style.transform = `translate(${leftOffset.x}px, ${leftOffset.y}px)`;
      }
      if (rightPupilRef.current) {
        rightPupilRef.current.style.transform = `translate(${rightOffset.x}px, ${rightOffset.y}px)`;
      }
    };

    window.addEventListener("mousemove", handleMouseMove);
    return () => window.removeEventListener("mousemove", handleMouseMove);
  }, []);

  const handleClick = useCallback(() => {
    // Pick a voice line
    const randomIndex = Math.floor(Math.random() * VOICE_LINES.length);
    const selectedLine = VOICE_LINES[randomIndex];
    
    setBubbleText(selectedLine);
    setStatus("SYNC ACTIVE");

    // Perform a cute pupil vibration effect on click
    if (leftPupilRef.current && rightPupilRef.current) {
      leftPupilRef.current.style.transition = "transform 0.05s ease-in-out";
      rightPupilRef.current.style.transition = "transform 0.05s ease-in-out";
      
      let shakeCount = 0;
      if (shakeIntervalRef.current) clearInterval(shakeIntervalRef.current);
      shakeIntervalRef.current = setInterval(() => {
        const sx = (Math.random() - 0.5) * 6;
        const sy = (Math.random() - 0.5) * 6;
        if (leftPupilRef.current) leftPupilRef.current.style.transform = `translate(${sx}px, ${sy}px)`;
        if (rightPupilRef.current) rightPupilRef.current.style.transform = `translate(${sx}px, ${sy}px)`;
        
        shakeCount++;
        if (shakeCount >= 8) {
          clearInterval(shakeIntervalRef.current!);
          shakeIntervalRef.current = null;
          if (leftPupilRef.current) leftPupilRef.current.style.transform = "translate(0px, 0px)";
          if (rightPupilRef.current) rightPupilRef.current.style.transform = "translate(0px, 0px)";
        }
      }, 50);
    }

    // Clear and set new bubble timeout
    if (bubbleTimeoutRef.current) clearTimeout(bubbleTimeoutRef.current);
    bubbleTimeoutRef.current = setTimeout(() => {
      setBubbleText(null);
      setStatus("SYSTEMS NOMINAL");
    }, 4500);
  }, []);

  useEffect(() => {
    return () => {
      if (bubbleTimeoutRef.current) clearTimeout(bubbleTimeoutRef.current);
      if (shakeIntervalRef.current) clearInterval(shakeIntervalRef.current);
    };
  }, []);

  return (
    <div 
      className="companion-card" 
      onClick={handleClick}
      style={{
        margin: "1.25rem 0.75rem",
        padding: "1rem 0.85rem",
        background: "rgba(30, 41, 59, 0.15)",
        border: "1px solid var(--border-card, rgba(255, 255, 255, 0.08))",
        borderRadius: "12px",
        backdropFilter: "blur(16px)",
        WebkitBackdropFilter: "blur(16px)",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: "0.5rem",
        cursor: "pointer",
        transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
        position: "relative",
        overflow: "visible",
        userSelect: "none"
      }}
    >
      {/* Speech Bubble / Tooltip */}
      {bubbleText && (
        <div 
          style={{
            position: "absolute",
            bottom: "105%",
            left: "50%",
            transform: "translateX(-50%)",
            background: "rgba(15, 23, 42, 0.95)",
            border: "1px solid var(--accent-cyan, #00e5ff)",
            color: "var(--text-primary)",
            padding: "0.5rem 0.75rem",
            borderRadius: "8px",
            fontSize: "0.75rem",
            width: "160px",
            textAlign: "center",
            boxShadow: "0 4px 15px rgba(0, 0, 0, 0.4), 0 0 10px rgba(0, 229, 255, 0.15)",
            zIndex: 100,
            pointerEvents: "none",
            animation: "bubbleFadeIn 0.2s cubic-bezier(0.16, 1, 0.3, 1)"
          }}
        >
          <div style={{ fontWeight: 600, color: "var(--accent-cyan)", fontSize: "0.7rem", marginBottom: "0.2rem", display: "flex", alignItems: "center", justifyContent: "center", gap: "0.25rem" }}>
            <Terminal size={10} />
            CHRONO_MASCOT
          </div>
          {bubbleText}
          <div 
            style={{
              position: "absolute",
              top: "100%",
              left: "50%",
              transform: "translateX(-50%)",
              width: "0",
              height: "0",
              borderLeft: "6px solid transparent",
              borderRight: "6px solid transparent",
              borderTop: "6px solid rgba(15, 23, 42, 0.95)",
              zIndex: 101
            }}
          />
          <div 
            style={{
              position: "absolute",
              top: "100%",
              left: "50%",
              transform: "translateX(-50%)",
              width: "0",
              height: "0",
              borderLeft: "7px solid transparent",
              borderRight: "7px solid transparent",
              borderTop: "7px solid var(--accent-cyan, #00e5ff)",
              zIndex: 99
            }}
          />
        </div>
      )}

      {/* Cybernetic Mascot Head Base SVG */}
      <div 
        className="companion-avatar"
        style={{
          animation: "companionLevitate 3s ease-in-out infinite",
          display: "flex",
          justifyContent: "center",
          alignItems: "center"
        }}
      >
        <svg 
          viewBox="0 0 100 100" 
          width="75" 
          height="75" 
          style={{ 
            filter: "drop-shadow(0 0 8px rgba(0, 229, 255, 0.35))"
          }}
        >
          {/* Ambient Glowing Aura */}
          <circle cx="50" cy="50" r="46" fill="none" stroke="rgba(0, 229, 255, 0.12)" strokeWidth="1" />
          <circle cx="50" cy="50" r="42" fill="none" stroke="rgba(0, 229, 255, 0.04)" strokeWidth="1" strokeDasharray="3 2" />

          {/* Android Neck Joint */}
          <path d="M43 78 L43 88 C43 89.5, 57 89.5, 57 88 L57 78 Z" fill="rgba(30, 41, 59, 0.95)" stroke="rgba(255, 255, 255, 0.05)" strokeWidth="0.75" />
          <path d="M46 82 L54 82" stroke="rgba(0, 229, 255, 0.4)" strokeWidth="1.5" strokeLinecap="round" />

          {/* Sleek Cybernetic Helmet Shape */}
          <path 
            d="M24 45 C24 23, 76 23, 76 45 C76 60, 69 76, 50 76 C31 76, 24 60, 24 45 Z" 
            fill="url(#mascotHelmetGrad)" 
            stroke="rgba(255, 255, 255, 0.06)" 
            strokeWidth="1" 
          />

          {/* Dark Mirror Visor Shield */}
          <path 
            d="M30 42 C30 35, 70 35, 70 42 C70 51, 65 54, 50 54 C35 54, 30 51, 30 42 Z" 
            fill="#090d16" 
            stroke="rgba(0, 229, 255, 0.2)" 
            strokeWidth="0.75" 
          />

          {/* Left Eye Socket & Tracking Pupil */}
          <g ref={leftEyeRef}>
            <ellipse cx="41" cy="45" rx="5.5" ry="5.5" fill="rgba(0, 229, 255, 0.08)" />
            <circle 
              ref={leftPupilRef} 
              cx="41" 
              cy="45" 
              r="2.2" 
              fill="var(--accent-cyan, #00e5ff)" 
              style={{ transformOrigin: "41px 45px" }}
            />
          </g>

          {/* Right Eye Socket & Tracking Pupil */}
          <g ref={rightEyeRef}>
            <ellipse cx="59" cy="45" rx="5.5" ry="5.5" fill="rgba(0, 229, 255, 0.08)" />
            <circle 
              ref={rightPupilRef} 
              cx="59" 
              cy="45" 
              r="2.2" 
              fill="var(--accent-cyan, #00e5ff)" 
              style={{ transformOrigin: "59px 45px" }}
            />
          </g>

          {/* AI Chip Node Core Indicator */}
          <path d="M48 24 L52 24 L50 30 Z" fill="rgba(168, 85, 247, 0.85)" style={{ filter: "drop-shadow(0 0 3px rgba(168, 85, 247, 0.6))" }} />
          <line x1="50" y1="30" x2="50" y2="33" stroke="rgba(168, 85, 247, 0.4)" strokeWidth="0.75" />

          {/* Visor Glare / Curved Metallic Highlights */}
          <path d="M33 40 C37 37.5, 45 37.5, 48 39" stroke="rgba(255, 255, 255, 0.12)" strokeWidth="0.75" strokeLinecap="round" fill="none" />
          <path d="M50 71 C58 71, 63 67, 65 64" stroke="rgba(0, 229, 255, 0.15)" strokeWidth="1" strokeLinecap="round" fill="none" />

          {/* Gradients */}
          <defs>
            <linearGradient id="mascotHelmetGrad" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="rgba(30, 41, 59, 0.95)" />
              <stop offset="60%" stopColor="rgba(15, 23, 42, 0.98)" />
              <stop offset="100%" stopColor="rgba(8, 12, 24, 0.99)" />
            </linearGradient>
          </defs>
        </svg>
      </div>

      {/* Companion Details Labels */}
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "0.15rem" }}>
        <span 
          style={{ 
            fontSize: "0.72rem", 
            fontWeight: 700, 
            letterSpacing: "0.05em",
            color: "var(--text-primary)",
            display: "flex",
            alignItems: "center",
            gap: "0.25rem"
          }}
        >
          <span>CHRONO BOT</span>
          <Sparkles size={10} color="var(--accent-cyan)" />
        </span>

        {/* Pulse Heartbeat / Sync Activity tag */}
        <div style={{ display: "flex", alignItems: "center", gap: "0.3rem" }}>
          <span 
            className="pulse-indicator" 
            style={{
              width: "5px",
              height: "5px",
              background: status === "SYNC ACTIVE" ? "var(--accent-purple, #a855f7)" : "var(--accent-cyan, #00e5ff)",
              borderRadius: "50%",
              display: "inline-block",
              boxShadow: status === "SYNC ACTIVE" 
                ? "0 0 6px var(--accent-purple, #a855f7)" 
                : "0 0 6px var(--accent-cyan, #00e5ff)"
            }}
          />
          <span 
            style={{ 
              fontSize: "0.6rem", 
              fontWeight: 600, 
              color: status === "SYNC ACTIVE" ? "var(--accent-purple, #a855f7)" : "var(--text-muted)",
              letterSpacing: "0.05em",
              textTransform: "uppercase",
              fontFamily: "var(--font-mono)"
            }}
          >
            {status}
          </span>
        </div>
      </div>

    </div>
  );
};
