"use client";
/* Envio real de lote: componente da integração F1 (confirmação de arquivo fictício,
 * POST /api/supplier/batches e acompanhamento do processamento F2). */
import { ApiUpload } from "@/components/api-upload";

export default function UploadPage() {
  return <ApiUpload />;
}
