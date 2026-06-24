export function Thumb({ src, round, alt }: { src?: string | null; round?: boolean; alt?: string }) {
  const cls = round ? "thumb round" : "thumb";
  if (!src) return <div className={`${cls} thumb-empty`} aria-hidden />;
  return <img className={cls} src={src} alt={alt ?? ""} loading="lazy" />;
}
