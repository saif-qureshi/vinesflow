export interface Media {
  id: number;
  storage_key: string;
  url: string;
  filename: string | null;
  content_type: string | null;
  size: number | null;
  sort_order: number;
}

export interface MediaInput {
  storage_key: string;
  filename?: string | null;
  content_type?: string | null;
  size?: number | null;
  sort_order?: number;
}

export interface UploadedFile {
  storage_key: string;
  url: string;
}
