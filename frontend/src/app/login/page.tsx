"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Lock, Mail } from "lucide-react";

import { App, Button, Form, Input, Password } from "@/components/ui";
import { useLogin, useSession } from "@/hooks/useSession";
import { apiErrorMessage } from "@/lib/api";
import { AuthShell } from "@/components/AuthShell";

export default function LoginPage() {
  const { isAuthenticated } = useSession();
  const login = useLogin();
  const { message } = App.useApp();
  const router = useRouter();

  useEffect(() => {
    if (isAuthenticated) router.replace("/dashboard");
  }, [isAuthenticated, router]);

  const onFinish = async (values: { email: string; password: string }) => {
    try {
      await login.mutateAsync(values);
      router.replace("/dashboard");
    } catch (err) {
      message.error(apiErrorMessage(err, "Login failed"));
    }
  };

  return (
    <AuthShell title="Welcome back" subtitle="Sign in to your Vineflow workspace">
      <Form layout="vertical" onFinish={onFinish} requiredMark={false} size="large">
        <Form.Item
          name="email"
          label="Email"
          rules={[{ required: true, type: "email", message: "Enter a valid email" }]}
        >
          <Input prefix={<Mail size={16} />} placeholder="you@company.com" autoComplete="email" />
        </Form.Item>
        <Form.Item
          name="password"
          label="Password"
          rules={[{ required: true, message: "Enter your password" }]}
        >
          <Password
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
