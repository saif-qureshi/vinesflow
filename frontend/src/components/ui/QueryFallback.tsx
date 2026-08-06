"use client";

import type { ReactNode } from "react";
import { Result, Spin } from "antd";

import { Button } from "@/components/ui";
import { apiErrorMessage } from "@/lib/api";

/** Kept as plain functions rather than a wrapper component so the caller's own
 *  `if (!data)` guard still narrows the type after them. */

export function errorState(error: unknown, onRetry?: () => void): ReactNode {
  return (
    <Result
      status="warning"
      title="This could not be loaded"
      subTitle={apiErrorMessage(error)}
      extra={onRetry ? <Button onClick={onRetry}>Try again</Button> : undefined}
    />
  );
}

export function loadingState(): ReactNode {
  return (
    <div className="flex min-h-[40vh] items-center justify-center">
      <Spin size="large" />
    </div>
  );
}

export function notFoundState(title = "Not found"): ReactNode {
  return (
    <Result
      status="404"
      title={title}
      subTitle="It may have been deleted, or you may not have access to it."
    />
  );
}
