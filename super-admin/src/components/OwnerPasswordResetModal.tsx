"use client";

import { App, Button, Form, Input, Modal } from "antd";
import { KeyRound, WandSparkles } from "lucide-react";

import { useUpdateOrganizationOwnerPassword } from "@/hooks/useSuperAdmin";
import { apiErrorMessage } from "@/lib/api";

interface PasswordValues {
  password: string;
  confirm_password: string;
}

interface OwnerPasswordResetModalProps {
  organizationId: number;
  organizationName: string;
  ownerEmail: string;
  open: boolean;
  onClose: () => void;
}

function generateTemporaryPassword(): string {
  const characters = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#$%";
  const random = new Uint32Array(16);
  crypto.getRandomValues(random);
  return Array.from(random, (value) => characters[value % characters.length]).join("");
}

export function OwnerPasswordResetModal({
  organizationId,
  organizationName,
  ownerEmail,
  open,
  onClose,
}: OwnerPasswordResetModalProps) {
  const [form] = Form.useForm<PasswordValues>();
  const updatePassword = useUpdateOrganizationOwnerPassword(organizationId);
  const { message } = App.useApp();

  const submit = async (values: PasswordValues) => {
    try {
      await updatePassword.mutateAsync(values.password);
      message.success("Owner password updated and existing sessions revoked");
      form.resetFields();
      onClose();
    } catch (error) {
      message.error(apiErrorMessage(error, "Could not update owner password"));
    }
  };

  const generate = () => {
    const password = generateTemporaryPassword();
    form.setFieldsValue({ password, confirm_password: password });
  };

  return (
    <Modal
      open={open}
      title={
        <div className="flex items-center gap-2">
          <KeyRound size={18} /> Reset owner password
        </div>
      }
      footer={null}
      onCancel={onClose}
      afterClose={() => form.resetFields()}
      destroyOnHidden
    >
      <div className="mb-5 rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm">
        <div className="font-medium text-slate-900">{organizationName}</div>
        <div className="mt-1 text-slate-500">{ownerEmail}</div>
      </div>
      <Form<PasswordValues>
        form={form}
        layout="vertical"
        requiredMark={false}
        onFinish={(values) => void submit(values)}
      >
        <Form.Item
          name="password"
          label="New temporary password"
          rules={[{ required: true, min: 8, message: "Use at least 8 characters" }]}
        >
          <Input.Password autoComplete="new-password" />
        </Form.Item>
        <Button
          type="dashed"
          icon={<WandSparkles size={16} />}
          onClick={generate}
          className="!mb-5"
        >
          Generate secure password
        </Button>
        <Form.Item
          name="confirm_password"
          label="Confirm password"
          dependencies={["password"]}
          rules={[
            { required: true, message: "Confirm the password" },
            ({ getFieldValue }) => ({
              validator(_, value) {
                return !value || getFieldValue("password") === value
                  ? Promise.resolve()
                  : Promise.reject(new Error("Passwords do not match"));
              },
            }),
          ]}
        >
          <Input.Password autoComplete="new-password" />
        </Form.Item>
        <div className="mb-5 text-xs leading-relaxed text-slate-500">
          Resetting the password revokes the owner&apos;s existing sign-in sessions. Share the new
          password through a secure channel.
        </div>
        <div className="flex justify-end gap-2">
          <Button onClick={onClose} disabled={updatePassword.isPending}>
            Cancel
          </Button>
          <Button type="primary" htmlType="submit" loading={updatePassword.isPending}>
            Update password
          </Button>
        </div>
      </Form>
    </Modal>
  );
}
