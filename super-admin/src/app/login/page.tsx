"use client";

import { useEffect } from "react";
import { App, Button, Form, Input } from "antd";
import { Lock, Mail } from "lucide-react";
import { useRouter } from "next/navigation";

import { AuthShell } from "@/components/AuthShell";
import { useAdminLogin, useSuperAdmin } from "@/hooks/useSuperAdmin";
import { apiErrorMessage } from "@/lib/api";

export default function LoginPage() {
  const login = useAdminLogin();
  const { data: admin } = useSuperAdmin();
  const { message } = App.useApp();
  const router = useRouter();

  useEffect(() => {
    if (admin) router.replace("/dashboard");
  }, [admin, router]);

  const onFinish = async (values: { email: string; password: string }) => {
    try {
      await login.mutateAsync(values);
      router.replace("/dashboard");
    } catch (error) {
      message.error(apiErrorMessage(error, "Sign in failed"));
    }
  };

  return (
    <AuthShell>
      <Form layout="vertical" onFinish={onFinish} requiredMark={false} size="large">
        <Form.Item
          name="email"
          label="Email"
          rules={[{ required: true, type: "email", message: "Enter a valid email" }]}
        >
          <Input prefix={<Mail size={16} />} placeholder="admin@vinesflow.com" autoComplete="email" />
        </Form.Item>
        <Form.Item
          name="password"
          label="Password"
          rules={[{ required: true, message: "Enter your password" }]}
        >
          <Input.Password
            prefix={<Lock size={16} />}
            placeholder="••••••••"
            autoComplete="current-password"
          />
        </Form.Item>
        <Button type="primary" htmlType="submit" block loading={login.isPending}>
          Sign in
        </Button>
      </Form>
    </AuthShell>
  );
}
