import { api, ApiError } from "./api";
import type { Batch } from "./api-contracts";

export type ApiUploadReceipt = {
  batch_id: number;
  status: "RECEBIDO";
};

// A API F1 aceita um arquivo por lote, em multipart/form-data.
// Não definir Content-Type manualmente: o navegador precisa inserir o boundary.
export const MAX_API_UPLOAD_BYTES = 20 * 1024 * 1024;
export const API_UPLOAD_EXTENSIONS = [".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".aej", ".txt"] as const;

export function validateApiUploadFile(file: File): string | null {
  const name = file.name.toLocaleLowerCase("en-US");
  if (!API_UPLOAD_EXTENSIONS.some((ext) => name.endsWith(ext))) {
    return "Formato não aceito: envie PDF, PNG, JPEG, TIFF ou AEJ.";
  }
  const limite = name.endsWith(".aej") || name.endsWith(".txt") ? 10 * 1024 * 1024 : MAX_API_UPLOAD_BYTES;
  if (!file.size || file.size > limite) {
    return name.endsWith(".aej") || name.endsWith(".txt")
      ? "O AEJ deve ter conteúdo e no máximo 10 MB."
      : "O arquivo deve ter conteúdo e no máximo 20 MB neste ambiente de testes.";
  }
  return null;
}

export function fetchApiBatch(token: string, id: number, signal?: AbortSignal): Promise<Batch> {
  if (!Number.isSafeInteger(id) || id <= 0) throw new ApiError(0, "Identificador de lote inválido.", "validation");
  return api<Batch>(`/api/batches/${id}`, { expectedToken: token, signal });
}

export async function uploadApiBatch(
  token: string, contractId: string, file: File, signal?: AbortSignal,
): Promise<ApiUploadReceipt> {
  const validation = validateApiUploadFile(file);
  if (validation || !contractId.trim())
    throw new ApiError(0, validation ?? "Selecione um contrato autorizado.", "validation");
  const data = new FormData();
  data.set("contract_id", contractId);
  data.set("file", file, file.name);
  // Sem retentativa automática: o servidor pode ter recebido um envio sem confirmação.
  const receipt = await api<unknown>("/api/supplier/batches", {
    method: "POST", body: data, expectedToken: token, signal, timeoutMs: 120000,
  });
  if (!receipt || typeof receipt !== "object" || !("batch_id" in receipt) ||
      !Number.isSafeInteger(receipt.batch_id) || (receipt.batch_id as number) <= 0 ||
      !("status" in receipt) || receipt.status !== "RECEBIDO") {
    throw new ApiError(0, "Resposta de recebimento inválida. Consulte a lista de lotes antes de reenviar.", "invalid_response");
  }
  return receipt as ApiUploadReceipt;
}
