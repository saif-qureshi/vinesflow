"use client";

import { useState } from "react";
import { App, Upload } from "antd";
import type { UploadFile, UploadProps } from "antd";
import { ImagePlus } from "lucide-react";

import { api, apiErrorMessage } from "@/lib/api";

interface OrganizationLogoUploaderProps {
  organizationId: number;
  value?: string[];
  onChange?: (urls: string[]) => void;
}

function toFileList(urls: string[]): UploadFile[] {
  return urls.map((url, index) => ({
    uid: `existing-${index}-${url}`,
    name: url.split("/").pop() || `logo-${index + 1}`,
    status: "done",
    url,
  }));
}

export function OrganizationLogoUploader({
  organizationId,
  value = [],
  onChange,
}: OrganizationLogoUploaderProps) {
  const { message } = App.useApp();
  const [fileList, setFileList] = useState<UploadFile[]>(() => toFileList(value));
  const valueKey = value.join("|");
  const [syncedKey, setSyncedKey] = useState(valueKey);

  if (syncedKey !== valueKey) {
    setSyncedKey(valueKey);
    setFileList((current) => [
      ...toFileList(value),
      ...current.filter((file) => file.status === "uploading"),
    ]);
  }

  const beforeUpload = (file: File) => {
    if (!file.type.startsWith("image/")) {
      message.error("Only image files are allowed");
      return Upload.LIST_IGNORE;
    }
    if (file.size > 5 * 1024 * 1024) {
      message.error("The logo must be under 5MB");
      return Upload.LIST_IGNORE;
    }
    return true;
  };

  const customRequest: UploadProps["customRequest"] = async ({ file, onSuccess, onError }) => {
    const form = new FormData();
    form.append("file", file as File);
    try {
      const response = await api.post(
        `/super-admin/organizations/${organizationId}/media/upload`,
        form,
      );
      onSuccess?.(response.data);
    } catch (error) {
      message.error(apiErrorMessage(error, "Logo upload failed"));
      onError?.(error as Error);
    }
  };

  const handleChange: UploadProps["onChange"] = ({ fileList: next }) => {
    setFileList(next);
    const urls = next
      .filter((file) => file.status === "done")
      .map((file) => file.url ?? (file.response as { url?: string } | undefined)?.url)
      .filter((url): url is string => Boolean(url));
    onChange?.(urls);
  };

  return (
    <Upload
      accept="image/*"
      listType="picture-card"
      fileList={fileList}
      maxCount={1}
      beforeUpload={beforeUpload}
      customRequest={customRequest}
      onChange={handleChange}
      onPreview={(file) => {
        const url = file.url ?? (file.response as { url?: string } | undefined)?.url;
        if (url) window.open(url, "_blank", "noopener,noreferrer");
      }}
    >
      {fileList.length < 1 && (
        <div>
          <ImagePlus size={21} className="mx-auto text-slate-400" />
          <div className="mt-2 text-xs">Upload logo</div>
        </div>
      )}
    </Upload>
  );
}
