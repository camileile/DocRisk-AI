"use client";

import Link from "next/link";
import { useEffect, useRef, useState, type FormEvent } from "react";
import {
  CheckCircle2, CircleAlert, FileText, RefreshCw, Upload, X,
} from "lucide-react";
import { useDemo } from "@/components/demo-provider";
import { PageIntro } from "@/components/workspace-parts";
import { BatchBadge } from "@/components/batch-badge";
import {
  ApiRequestError, fetchApiBatch, uploadApiBatch, validateApiUploadFile,
  type ApiBatch, type ApiUploadReceipt,
} from "@/lib/api-client";

const TERMINAL = new Set(["CONCLUIDO", "FALHA_PROCESSAMENTO"]);
const MAX_STATUS_CHECKS = 60;

function ProcessingStatus({ receipt, token, submittedContract, filename }: {
  receipt: ApiUploadReceipt;
  token: string;
  submittedContract: string;
  filename: string;
}) {
  const [batch, setBatch] = useState<ApiBatch | null>(null);
  const [error, setError] = useState("");
  const [finishedChecking, setFinishedChecking] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    let active = true;
    let checkCount = 0;
    let timeout: ReturnType<typeof setTimeout> | undefined;
    let requestController: AbortController | undefined;
    setError("");
    setFinishedChecking(false);

    async function check() {
      if (!active) return;
      requestController = new AbortController();
      try {
        const current = await fetchApiBatch(token, receipt.batch_id, requestController.signal);
        if (!active) return;
        if (current.contract_id !== submittedContract) {
          setError("A API retornou um lote de contrato diferente. Acompanhe o ocorrido com a equipe.");
          setFinishedChecking(true);
          return;
        }
        setBatch(current);
        setError("");
        if (TERMINAL.has(current.status)) {
          setFinishedChecking(true);
          return;
        }
      } catch (reason) {
        if (!active) return;
        setError(reason instanceof Error ? reason.message : "Não foi possível atualizar o status.");
        if (reason instanceof ApiRequestError && reason.status !== null && reason.status < 500) {
          setFinishedChecking(true);
          return;
        }
      }
      checkCount += 1;
      if (checkCount >= MAX_STATUS_CHECKS) {
        setFinishedChecking(true);
        return;
      }
      timeout = setTimeout(() => { void check(); }, 2500);
    }

    void check();
    return () => {
      active = false;
      if (timeout) clearTimeout(timeout);
      requestController?.abort();
    };
  }, [token, receipt.batch_id, submittedContract, refreshKey]);

  const completed = batch?.status === "CONCLUIDO";
  const failed = batch?.status === "FALHA_PROCESSAMENTO";

  return (
    <section className="workspace-card api-upload-result" aria-label="Acompanhamento do envio" aria-live="polite">
      <div className="api-upload-result-heading">
        <CheckCircle2 size={23} aria-hidden="true" />
        <div>
          <strong>Recebimento confirmado — lote #{receipt.batch_id}</strong>
          <p>{filename} · contrato {submittedContract}</p>
        </div>
      </div>
      <div className="api-upload-progress">
        <div>
          <span>Status consultado na API</span>
          {batch ? <BatchBadge status={batch.status} /> : <span className="api-status">Consultando…</span>}
        </div>
        {batch && <small>{batch.tipo_arquivo === "AEJ"
          ? "AEJ estruturado identificado pelo backend; processamento sem IA"
          : `${batch.total_pages} página(s) identificada(s) pelo backend`}</small>}
      </div>
      {completed && (
        <p className="api-upload-notice api-upload-success">
          <CheckCircle2 size={17} /> Processamento documental concluído. Isso não significa conciliação trabalhista concluída.
        </p>
      )}
      {failed && (
        <p className="api-error" role="alert">
          <CircleAlert size={17} /> {batch?.erro || "O processamento foi interrompido. Consulte os registros do lote."}
        </p>
      )}
      {error && <p className="api-error" role="alert">{error}</p>}
      {!finishedChecking && !error && !completed && !failed && (
        <p className="api-status" role="status">Acompanhando a leitura documental automaticamente…</p>
      )}
      {finishedChecking && !completed && !failed && !error && (
        <p className="api-status">O acompanhamento automático foi interrompido após 2 minutos e meio; o processamento pode continuar no backend.</p>
      )}
      <div className="api-upload-result-actions">
        <Link className="button secondary" href="/painel/lotes">Consultar histórico de lotes</Link>
        <button type="button" className="button secondary" onClick={() => setRefreshKey(n => n + 1)} disabled={!finishedChecking}>
          <RefreshCw size={16} /> {finishedChecking ? "Consultar status novamente" : "Atualizando…"}
        </button>
      </div>
    </section>
  );
}

export function ApiUpload() {
  const { apiSession, contract, isDemo } = useDemo();
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [uploaded, setUploaded] = useState<{
    receipt: ApiUploadReceipt; contract: string; filename: string;
  } | null>(null);

  const allowed = Boolean(
    apiSession &&
    (apiSession.user.papel === "OPERADOR_FORN" || apiSession.user.papel === "GESTOR_FORN") &&
    apiSession.contracts.some((item) => item.id === contract),
  );

  if (isDemo) {
    return (
      <>
        <PageIntro
          eyebrow="DEMONSTRAÇÃO · FORNECEDORA"
          title="Envio de documentos."
          description="Esta prévia funciona sem API e mostra somente dados fictícios. Nenhum arquivo é recebido ou processado."
        />
        <section className="workspace-card api-unavailable">
          <h2>Envio desativado nesta demonstração</h2>
          <p>O envio de PDFs e imagens está disponível exclusivamente no ambiente de testes com backend conectado. Para conhecer o fluxo sem enviar dados, explore um lote ilustrativo e suas pendências.</p>
          <Link className="button secondary" href="/painel/lotes">Ver lotes fictícios</Link>
        </section>
      </>
    );
  }

  if (!apiSession || !allowed) {
    return (
      <>
        <PageIntro eyebrow="FORNECEDORA · API DE TESTE" title="Envio reservado à fornecedora."
          description="A API exige um usuário da fornecedora e um contrato autorizado. Esta interface não permite contornar essas permissões." />
        <div className="workspace-card api-unavailable">
          <p>Use um token de operador/gestor da fornecedora e selecione um contrato válido.</p>
          <Link className="button secondary" href="/painel/lotes">Voltar aos lotes</Link>
        </div>
      </>
    );
  }

  const validation = file ? validateApiUploadFile(file) : null;
  const canSubmit = Boolean(file && !validation && confirmed && !busy && !uploaded);

  function pickFile(list: FileList | null) {
    const candidate = list?.[0] ?? null;
    setFile(candidate);
    setConfirmed(false);
    setError(candidate ? validateApiUploadFile(candidate) ?? "" : "");
    setUploaded(null);
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSubmit || !file || !apiSession) return;
    // Verificar autorização imediatamente antes de enviar.
    if (!apiSession.contracts.some(c => c.id === contract)) {
      setError("Contrato não autorizado neste usuário.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const receipt = await uploadApiBatch(apiSession.token, contract, file);
      setUploaded({ receipt, contract, filename: file.name });
      setFile(null);
      setConfirmed(false);
      if (inputRef.current) inputRef.current.value = "";
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Não foi possível confirmar o envio.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <PageIntro
        eyebrow="FORNECEDORA · API F1 + MOTOR F2"
        title="Envio de documentos."
        description="Envie um arquivo sintético para o contrato autorizado. O backend cria um lote real no ambiente local e a F2 processa o documento."
      />
      <div className="upload-layout">
        <section className="workspace-card">
          <div className="card-title">
            <h2>Enviar arquivo ao backend</h2>
            <span>Contrato {contract}</span>
          </div>
          <form onSubmit={(event) => { void submit(event); }} className="api-upload-form">
            <label className="upload-area">
              <Upload size={30} />
              <strong>Selecione um arquivo sintético</strong>
              <span>PDF, imagem ou AEJ · até 20 MB (AEJ até 10 MB)</span>
              <input ref={inputRef} type="file" aria-label="Selecionar arquivo para envio real"
                accept=".pdf,.png,.jpg,.jpeg,.tif,.tiff,.aej,.txt"
                disabled={busy || Boolean(uploaded)}
                onChange={(event) => pickFile(event.target.files)} />
            </label>
            {file && (
              <div className="api-upload-selected">
                <FileText size={20} aria-hidden="true" />
                <div><strong>{file.name}</strong><small>{(file.size / 1024 / 1024).toFixed(2)} MB · contrato {contract}</small></div>
                <button type="button" className="icon-button" aria-label="Remover arquivo selecionado"
                  onClick={() => { setFile(null); setConfirmed(false); setError(""); if (inputRef.current) inputRef.current.value = ""; }}>
                  <X size={17} />
                </button>
              </div>
            )}
            {!uploaded && (
              <>
                <label className="api-upload-confirm">
                  <input type="checkbox" checked={confirmed} disabled={busy || !file || Boolean(validation)}
                    onChange={(event) => setConfirmed(event.target.checked)} />
                  <span>Confirmo que o arquivo é <strong>inteiramente sintético</strong>, não contém dados pessoais reais e deve ser enviado para o contrato {contract} no ambiente local de testes.</span>
                </label>
                <button type="submit" className="button api-upload-button" disabled={!canSubmit}>
                  <Upload size={17} /> {busy ? "Enviando e aguardando confirmação…" : "Enviar arquivo ao backend"}
                </button>
              </>
            )}
            {error && !uploaded && <p className="api-error" role="alert">{error}</p>}
            {busy && <p className="api-status" role="status">Aguarde a confirmação. Não feche esta página durante o envio; o processamento pode ocorrer na mesma requisição.</p>}
          </form>
          {uploaded && (
            <button type="button" className="button secondary api-upload-another" onClick={() => { setUploaded(null); setError(""); }}>
              Preparar outro arquivo
            </button>
          )}
        </section>
        <aside className="workspace-card upload-guidance">
          <span className="eyebrow">ENVIO OPERACIONAL DE TESTE</span>
          <h2>O que acontece agora?</h2>
          <ul>
            <li>Um arquivo gera um lote independente na API.</li>
            <li>O servidor valida o conteúdo, o tamanho, o contrato e a permissão do usuário.</li>
            <li>A F2 registra e classifica páginas; alguns documentos podem seguir para revisão humana.</li>
            <li>AEJ é processado como dado estruturado, sem envio à IA; o original e as linhas de origem são preservados.</li>
            <li>O sistema não valida assinatura P7S. Vínculos sem mapeamento ou cálculos com alertas precisam de conferência da Bernhoeft.</li>
            <li>O status CONCLUÍDO não representa parecer ou conciliação da F3.</li>
          </ul>
          <div className="evidence-note"><CircleAlert size={19} />
            <p>Somente ambiente local e documentos fictícios. Não envie folhas, pontos ou dados pessoais de trabalhadores reais.</p>
          </div>
        </aside>
      </div>
      {uploaded && <ProcessingStatus key={uploaded.receipt.batch_id} token={apiSession.token}
        receipt={uploaded.receipt} submittedContract={uploaded.contract} filename={uploaded.filename} />}
    </>
  );
}
