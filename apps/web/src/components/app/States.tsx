import type { ReactNode } from "react";
import { Button, Card, Status } from "@/components/ui";

/** Shown while a request is in flight. */
export function Loading({ label = "Loading" }: { label?: string }) {
  return (
    <div role="status" aria-live="polite" className="py-6">
      <Status status="pending" label={label} />
    </div>
  );
}

/** A failed request, with the reason from the API and a way to try again. */
export function ErrorState({
  title = "This could not be loaded",
  message,
  onRetry,
  problems = [],
}: {
  title?: string;
  message: string;
  onRetry?: () => void;
  problems?: string[];
}) {
  return (
    <div role="alert" className="flex flex-col items-start gap-3 border border-fail bg-fail-bg/40 px-5 py-4">
      <Status status="fail" label={title} />
      <p className="type-body text-ink">{message}</p>
      {problems.length ? (
        <ul className="flex list-disc flex-col gap-1 pl-5 type-small text-ink-2">
          {problems.map((p) => (
            <li key={p}>{p}</li>
          ))}
        </ul>
      ) : null}
      {onRetry ? (
        <Button variant="secondary" onClick={onRetry}>
          Try again
        </Button>
      ) : null}
    </div>
  );
}

/** Nothing to show yet, and what to do about it. */
export function Empty({ title, children, action }: { title: string; children?: ReactNode; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-start gap-2 border border-dashed border-rule bg-paper px-5 py-6">
      <p className="type-body-medium text-ink">{title}</p>
      {children ? <p className="type-small text-ink-2">{children}</p> : null}
      {action}
    </div>
  );
}

/** A Card whose body follows a request: loading, error, empty or the content. */
export function DataCard<T>({
  eyebrow,
  title,
  tag,
  state,
  isEmpty,
  empty,
  children,
  className,
}: {
  eyebrow?: string;
  title: string;
  tag?: ReactNode;
  state: { data?: T; error?: string; loading: boolean; reload: () => void };
  isEmpty?: (data: T) => boolean;
  empty?: ReactNode;
  children: (data: T) => ReactNode;
  className?: string;
}) {
  let body: ReactNode;
  if (state.error) body = <div className="pt-3"><ErrorState message={state.error} onRetry={state.reload} /></div>;
  else if (state.data === undefined) body = <Loading />;
  else if (isEmpty?.(state.data)) body = <div className="pt-3">{empty}</div>;
  else body = children(state.data);
  return (
    <Card eyebrow={eyebrow} title={title} tag={state.data !== undefined ? tag : undefined} className={className}>
      {body}
    </Card>
  );
}
