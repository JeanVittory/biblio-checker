export function BackgroundGrid() {
  return (
    <div
      className="pointer-events-none fixed inset-0 -z-10"
      style={{
        backgroundImage: `linear-gradient(var(--border-color) 1px, transparent 1px),
                          linear-gradient(90deg, var(--border-color) 1px, transparent 1px)`,
        backgroundSize: "60px 60px",
        maskImage: "linear-gradient(to bottom, rgba(0,0,0,0.15) 0%, transparent 70%)",
        WebkitMaskImage: "linear-gradient(to bottom, rgba(0,0,0,0.15) 0%, transparent 70%)",
      }}
    />
  );
}
