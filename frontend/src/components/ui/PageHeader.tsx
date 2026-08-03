"use client";

import { ArrowLeft } from "lucide-react";
import { Button, Typography } from "antd";

export function PageHeader({
  title,
  description,
  actions,
  onBack,
}: {
  title: string;
  description?: React.ReactNode;
  actions?: React.ReactNode;
  onBack?: () => void;
}) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div className="flex items-start gap-1">
        {onBack && (
          <Button
            type="text"
            aria-label="Go back"
            className="-ml-2 mt-1 text-gray-500"
            icon={<ArrowLeft size={18} />}
            onClick={onBack}
          />
        )}
        <div>
          <Typography.Title level={3} className="!mb-0">
            {title}
          </Typography.Title>
          {description && (
            <Typography.Text type="secondary" className="mt-1 block">
              {description}
            </Typography.Text>
          )}
        </div>
      </div>
      {actions && <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto">{actions}</div>}
    </div>
  );
}
