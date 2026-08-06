"use client";

import { useState } from "react";
import { App, Upload } from "antd";
import type { UploadFile, UploadProps } from "antd";
import { UploadCloud } from "lucide-react";

import { api, apiErrorMessage } from "@/lib/api";
import type { UploadedFile } from "@/types";

interface UploaderProps {
  value?: UploadedFile[];
  onChange?: (files: UploadedFile[]) => void;
  maxCount?: number;
  accept?: string;
  maxSizeMB?: number;
  listType?: UploadProps["listType"];
  drag?: boolean;
}

function toFileList(files: UploadedFile[]): UploadFile[] {
  return files.map((file, i) => ({
    uid: `existing-${i}-${file.storage_key}`,
    name: file.storage_key.split("/").pop() || `file-${i + 1}`,
    status: "done",
    url: file.url,
    response: file,
  }));
}

function toUploaded(file: UploadFile): UploadedFile | null {
  const uploaded = file.response as UploadedFile | undefined;
  return uploaded?.storage_key ? { storage_key: uploaded.storage_key, url: uploaded.url } : null;
}

export function Uploader({
  value = [],
  onChange,
  maxCount = 8,
  accept = "image/*",
  maxSizeMB = 5,
  listType = "picture-card",
  drag = true,
}: UploaderProps) {
  const { message } = App.useApp();
  const [fileList, setFileList] = useState<UploadFile[]>(() => toFileList(value));

  const valueKey = value.map((f) => f.storage_key).join("|");
  const [syncedKey, setSyncedKey] = useState(valueKey);
  if (syncedKey !== valueKey) {
    setSyncedKey(valueKey);
    setFileList((prev) => [...toFileList(value), ...prev.filter((f) => f.status === "uploading")]);
  }

  const beforeUpload = (file: File) => {
    if (accept.includes("image") && !file.type.startsWith("image/")) {
      message.error("Only image files are allowed");
      return Upload.LIST_IGNORE;
    }
    if (file.size > maxSizeMB * 1024 * 1024) {
      message.error(`Each file must be under ${maxSizeMB}MB`);
      return Upload.LIST_IGNORE;
    }
    if (fileList.length >= maxCount) {
      message.error(`Up to ${maxCount} files`);
      return Upload.LIST_IGNORE;
    }
    return true;
  };

  const customRequest: UploadProps["customRequest"] = async ({ file, onSuccess, onError }) => {
    const form = new FormData();
    form.append("file", file as File);
    try {
      const res = await api.post("/media/upload", form);
      onSuccess?.(res.data);
    } catch (err) {
      message.error(apiErrorMessage(err, "Upload failed"));
      onError?.(err as Error);
    }
  };

  const handleChange: UploadProps["onChange"] = ({ fileList: next }) => {
    setFileList(next);
    const uploaded = next
      .filter((f) => f.status === "done")
      .map(toUploaded)
      .filter((f): f is UploadedFile => !!f);
    onChange?.(uploaded);
  };

  const onPreview = (file: UploadFile) => {
    const url = toUploaded(file)?.url ?? file.url;
    if (url) window.open(url, "_blank");
  };

  const shared = {
    accept,
    listType,
    fileList,
    multiple: true,
    maxCount,
    beforeUpload,
    customRequest,
    onChange: handleChange,
    onPreview,
  } satisfies UploadProps;

  if (drag) {
    return (
      <div className="[&_.ant-upload-list]:mt-3">
        <Upload.Dragger {...shared}>
          <p className="ant-upload-drag-icon flex justify-center">
            <UploadCloud size={28} className="text-gray-400" />
          </p>
          <p className="ant-upload-text">Drag files here or click to upload</p>
          <p className="ant-upload-hint !text-xs">
            {accept} · up to {maxSizeMB}MB · max {maxCount} files
          </p>
        </Upload.Dragger>
      </div>
    );
  }

  return (
    <Upload {...shared}>
      {fileList.length < maxCount && (
        <div>
          <UploadCloud size={20} className="mx-auto text-gray-400" />
          <div className="mt-1 text-xs">Upload</div>
        </div>
      )}
    </Upload>
  );
}
