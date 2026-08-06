"use client";

import { App, Button, Card, Form, Password, Typography } from "@/components/ui";
import { useUpdateProfile } from "@/hooks/useOrg";
import { apiErrorMessage } from "@/lib/api";

interface FormValues {
  password: string;
  confirm: string;
}

export default function AccountSecurityPage() {
  const { message } = App.useApp();
  const updateProfile = useUpdateProfile();
  const [form] = Form.useForm<FormValues>();

  const save = async (values: FormValues) => {
    try {
      await updateProfile.mutateAsync({ password: values.password });
      message.success("Password changed. Your other sessions have been signed out.");
      form.resetFields();
    } catch (err) {
      message.error(apiErrorMessage(err));
    }
  };

  return (
    <Card title="Security" className="border-gray-100">
      <Form form={form} layout="vertical" onFinish={save} className="max-w-lg">
        <Form.Item
          name="password"
          label="New password"
          rules={[
            { required: true, message: "Enter a new password" },
            { min: 8, message: "At least 8 characters" },
          ]}
        >
          <Password autoComplete="new-password" />
        </Form.Item>
        <Form.Item
          name="confirm"
          label="Confirm new password"
          dependencies={["password"]}
          rules={[
            { required: true, message: "Repeat the new password" },
            ({ getFieldValue }) => ({
              validator: (_, value) =>
                !value || getFieldValue("password") === value
                  ? Promise.resolve()
                  : Promise.reject(new Error("The passwords do not match")),
            }),
          ]}
        >
          <Password autoComplete="new-password" />
        </Form.Item>
        <Typography.Paragraph type="secondary" className="!text-xs">
          Changing your password signs out every other device.
        </Typography.Paragraph>
        <Button type="primary" htmlType="submit" loading={updateProfile.isPending}>
          Change password
        </Button>
      </Form>
    </Card>
  );
}
