"use client";

import { useEffect, useState } from "react";

import { App, Avatar, Button, Form, Input, Password, PageHeader } from "@/components/ui";
import { Uploader } from "@/components/ui/Uploader";
import { useSession } from "@/hooks/useSession";
import { useUpdateProfile } from "@/hooks/useOrg";
import { apiErrorMessage } from "@/lib/api";
import { brand } from "@/theme/tokens";
import type { UploadedFile } from "@/types";

export default function AccountPage() {
  const { user } = useSession();
  const { message } = App.useApp();
  const updateProfile = useUpdateProfile();
  const [form] = Form.useForm();
  const avatarKey = user?.avatar_key ?? "";
  const [avatar, setAvatar] = useState<UploadedFile[]>([]);
  const [syncedKey, setSyncedKey] = useState<string | null>(null);
  if (syncedKey !== avatarKey) {
    setSyncedKey(avatarKey);
    setAvatar(
      user?.avatar_key && user.avatar_url
        ? [{ storage_key: user.avatar_key, url: user.avatar_url }]
        : [],
    );
  }

  useEffect(() => {
    form.setFieldsValue({ full_name: user?.full_name });
  }, [user, form]);

  const save = async (values: { full_name?: string; password?: string }) => {
    try {
      await updateProfile.mutateAsync({
        full_name: values.full_name,
        avatar_key: avatar[0]?.storage_key ?? "",
        ...(values.password ? { password: values.password } : {}),
      });
      message.success("Profile updated");
      form.setFieldValue("password", undefined);
    } catch (err) {
      message.error(apiErrorMessage(err));
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader title="Profile" description="Your personal account details" />

      <Form form={form} layout="vertical" onFinish={save} className="max-w-lg">
        <Form.Item label="Avatar">
          <div className="flex items-center gap-4">
            <Avatar size={64} src={avatar[0]?.url || undefined} style={{ backgroundColor: brand.primary }}>
              {(user?.full_name ?? user?.email ?? "?").charAt(0).toUpperCase()}
            </Avatar>
            <Uploader
              value={avatar}
              onChange={setAvatar}
              maxCount={1}
              accept="image/*"
              maxSizeMB={5}
              drag={false}
            />
          </div>
        </Form.Item>
        <Form.Item label="Email">
          <Input value={user?.email} disabled />
        </Form.Item>
        <Form.Item name="full_name" label="Full name">
          <Input />
        </Form.Item>
        <Form.Item
          name="password"
          label="New password"
          rules={[{ min: 8, message: "At least 8 characters" }]}
        >
          <Password placeholder="Leave blank to keep current" autoComplete="new-password" />
        </Form.Item>
        <Button type="primary" htmlType="submit" loading={updateProfile.isPending}>
          Save
        </Button>
      </Form>
    </div>
  );
}
