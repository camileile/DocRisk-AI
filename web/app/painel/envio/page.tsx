"use client";
import { useRef, useState } from "react";
import { Upload, FileText, X, Check, CircleAlert } from "lucide-react";
import { useDemo } from "@/components/demo-provider";
import { PageIntro } from "@/components/workspace-parts";
const accepted = ["pdf", "png", "jpg", "jpeg", "aej"];
export default function UploadPreview() {
  const { role, contract, competence } = useDemo();
  const [files, setFiles] = useState<{ name: string; size: number }[]>([]);
  const [error, setError] = useState("");
  const [checked, setChecked] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  if (role !== "OPERADOR_FORN")
    return (
      <>
        <PageIntro
          eyebrow="FORNECEDORA"
          title="Envio de documentos."
          description="Na demonstração, esta etapa pertence ao perfil da fornecedora."
        />
        <div className="workspace-card">
          <p>
            Troque para a perspectiva de operador da fornecedora na página de
            acesso para explorar a prévia.
          </p>
        </div>
      </>
    );
  function select(list: FileList | null) {
    setChecked(false);
    if (!list) return;
    const selection = Array.from(list);
    if (selection.length > 10) {
      setError("Selecione até 10 arquivos de exemplo por vez.");
      return;
    }
    if (
      selection.some(
        (file) =>
          !accepted.includes(file.name.split(".").pop()?.toLowerCase() ?? ""),
      )
    ) {
      setError("Formato não aceito. Use PDF, PNG, JPG, JPEG ou AEJ.");
      return;
    }
    if (
      selection.some((file) => file.size === 0 || file.size > 20 * 1024 * 1024)
    ) {
      setError(
        "Cada arquivo deve ter conteúdo e no máximo 20 MB nesta prévia.",
      );
      return;
    }
    setFiles(selection.map(({ name, size }) => ({ name, size })));
    setError("");
  }
  return (
    <>
      <PageIntro
        eyebrow="FORNECEDORA · PRÉVIA DE ENVIO"
        title="Tudo começa com os documentos."
        description="Explore a preparação do lote. Nesta etapa, nenhum arquivo é enviado, lido ou processado."
      />
      <div className="upload-layout">
        <section className="workspace-card">
          <div className="card-title">
            <h2>Prepare um lote de exemplo</h2>
            <span>
              {contract} · {competence}
            </span>
          </div>
          <label className="upload-area">
            <Upload size={30} />
            <strong>Selecione arquivos sintéticos</strong>
            <span>PDF, imagens ou AEJ · até 10 arquivos de 20 MB</span>
            <input
              ref={input}
              type="file"
              accept=".pdf,.png,.jpg,.jpeg,.aej"
              multiple
              aria-label="Selecionar arquivos sintéticos"
              onChange={(e) => select(e.target.files)}
            />
          </label>
          {error && (
            <p role="alert" className="upload-error">
              {error}
            </p>
          )}
          {files.length > 0 && (
            <>
              <div className="upload-file-list">
                {files.map((file, index) => (
                  <div key={`${file.name}-${index}`}>
                    <FileText size={20} />
                    <span>
                      <strong>{file.name}</strong>
                      <small>
                        {file.size < 1024 * 1024
                          ? `${Math.ceil(file.size / 1024)} KB`
                          : `${(file.size / 1024 / 1024).toFixed(1)} MB`}
                      </small>
                    </span>
                    <button
                      className="icon-button"
                      aria-label={`Remover ${file.name}`}
                      onClick={() => {
                        setFiles(files.filter((_, i) => i !== index));
                        setChecked(false);
                        if (input.current) input.current.value = "";
                      }}
                    >
                      <X size={17} />
                    </button>
                  </div>
                ))}
              </div>
              <button className="button" onClick={() => setChecked(true)}>
                Conferir seleção <Check size={17} />
              </button>
            </>
          )}
          {checked && (
            <div className="inline-info" role="status">
              <Check size={18} />
              <p>
                {files.length} arquivo(s) selecionado(s). A prévia foi
                conferida; nenhum lote foi criado. Envio, leitura e
                classificação dependem da integração com a API.
              </p>
            </div>
          )}
        </section>
        <aside className="workspace-card upload-guidance">
          <span className="eyebrow">ANTES DE CONTINUAR</span>
          <h2>Um lote bem preparado.</h2>
          <ul>
            <li>Use somente arquivos sintéticos neste protótipo.</li>
            <li>Confira se todas as páginas estão presentes e legíveis.</li>
            <li>O AEJ segue o fluxo de dados estruturados de jornada.</li>
            <li>
              O contrato e a competência selecionados indicam o contexto de
              navegação, sem substituir a validação documental.
            </li>
          </ul>
          <div className="evidence-note">
            <CircleAlert size={19} />
            <p>
              Esta é uma prévia de interface. As verificações de segurança e
              conteúdo serão realizadas pelo backend na integração.
            </p>
          </div>
        </aside>
      </div>
    </>
  );
}
