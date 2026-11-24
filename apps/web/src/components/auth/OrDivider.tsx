export function OrDivider() {
  return (
    <div className="flex w-full items-center gap-3" role="separator" aria-label="or">
      <span aria-hidden className="h-px flex-1 bg-rule" />
      <span aria-hidden className="type-caption text-muted">
        or
      </span>
      <span aria-hidden className="h-px flex-1 bg-rule" />
    </div>
  );
}
