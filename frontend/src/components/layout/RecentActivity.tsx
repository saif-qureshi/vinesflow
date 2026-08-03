"use client";

import { useState } from "react";
import { Avatar, Empty, Popover, Spin } from "antd";
import { History } from "lucide-react";

import { Button } from "@/components/ui";
import { useActivities } from "@/hooks/useActivities";
import { timeAgo } from "@/lib/format";
import type { Activity } from "@/types";

const ICON = 18;

function actorName(a: Activity) {
  return a.actor?.full_name || a.actor?.email || "System";
}

function Row({ a }: { a: Activity }) {
  return (
    <div className="flex gap-3 px-3 py-2 hover:bg-gray-50">
      <Avatar size={28} src={a.actor?.avatar_url ?? undefined} className="shrink-0">
        {actorName(a).charAt(0).toUpperCase()}
      </Avatar>
      <div className="min-w-0 flex-1">
        <div className="text-sm">
          <span className="font-medium">{actorName(a)}</span>{" "}
          <span className="text-gray-500">
            {a.action} {a.entity_type}
          </span>
        </div>
        <div className="truncate text-xs text-gray-500">
          {a.summary} · {timeAgo(a.created_at)}
        </div>
      </div>
    </div>
  );
}

export function RecentActivity({ label }: { label?: string }) {
  const [open, setOpen] = useState(false);
  const { data, isLoading, refetch } = useActivities();
  const items = data?.pages.flatMap((p) => p.items) ?? [];

  const content = (
    <div className="w-80">
      <div className="border-b border-gray-100 px-3 py-2 text-sm font-semibold">Recent activity</div>
      <div className="max-h-96 overflow-y-auto">
        {isLoading ? (
          <div className="flex justify-center py-8">
            <Spin />
          </div>
        ) : items.length ? (
          items.map((a) => <Row key={a.id} a={a} />)
        ) : (
          <div className="py-4">
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="No recent activity yet" />
          </div>
        )}
      </div>
    </div>
  );

  return (
    <Popover
      trigger="click"
      placement="bottomLeft"
      open={open}
      onOpenChange={(o) => {
        setOpen(o);
        if (o) refetch();
      }}
      styles={{ content: { padding: 0 } }}
      content={content}
    >
      <Button
        block={Boolean(label)}
        className={label ? "!justify-start" : undefined}
        type="text"
        icon={<History size={ICON} />}
      >
        {label}
      </Button>
    </Popover>
  );
}
