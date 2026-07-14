interface SkeletonProps {
  variant?: 'text' | 'card' | 'circle';
  width?: string | number;
  height?: string | number;
  count?: number;
}

export function Skeleton({ variant = 'text', width, height, count = 1 }: SkeletonProps) {
  const items = Array.from({ length: count }, (_, index) => index);
  const style = {
    width: width ?? (variant === 'circle' ? 36 : '100%'),
    height: height ?? (variant === 'circle' ? 36 : undefined),
    borderRadius: variant === 'circle' ? '50%' : undefined,
  };
  const className = `skeleton ${variant === 'card' ? 'skeleton-card' : variant === 'text' ? 'skeleton-text' : ''}`.trim();

  return (
    <div aria-hidden="true">
      {items.map((item) => (
        <div key={item} className={className} style={style} />
      ))}
    </div>
  );
}
