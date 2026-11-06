"use client";
import { useEffect, useRef, useState } from "react";
import { ChevronLeft, ChevronRight, RotateCw, ZoomIn, ZoomOut } from "lucide-react";
import { apiBlob, type PageRef } from "@/lib/api";
import { useApi } from "@/lib/use-api";

export function DocumentViewer({ documentId, pages, selectedPageId, onPageChange }: {
  documentId: number; pages: PageRef[]; selectedPageId?: number; onPageChange?: (id: number) => void;
}) {
  const [localPageId, setLocalPageId] = useState(pages[0]?.page_id);
  const index = Math.max(0, pages.findIndex(p => p.page_id === (selectedPageId ?? localPageId)));
  const current = pages[index];
  const [zoom, setZoom] = useState(100);
  const [rotation, setRotation] = useState(0);
  const text = useApi<{ texto: string }>(current ? `/api/documents/${documentId}/pages/${current.page_id}` : null);
  function change(id: number) { setLocalPageId(id); onPageChange?.(id); }
  if (!current) return <p className="muted">Documento sem páginas de imagem.</p>;
  return (
    <section className="workspace-card document-viewer" aria-label="Visualizador do documento">
      <div className="document-viewer-toolbar">
        <button type="button" className="icon-button" aria-label="Página anterior" disabled={index === 0} onClick={() => change(pages[index - 1].page_id)}><ChevronLeft size={18} /></button>
        <label>Página <select aria-label="Página do documento" value={current.page_id} onChange={event => change(Number(event.target.value))}>
          {pages.map((page, i) => <option key={page.page_id} value={page.page_id}>{i + 1} de {pages.length} · lote p. {page.ordem}</option>)}
        </select></label>
        <button type="button" className="icon-button" aria-label="Próxima página" disabled={index === pages.length - 1} onClick={() => change(pages[index + 1].page_id)}><ChevronRight size={18} /></button>
        <button type="button" className="icon-button" aria-label="Diminuir zoom" disabled={zoom <= 50} onClick={() => setZoom(value => Math.max(50, value - 25))}><ZoomOut size={18} /></button>
        <output aria-label="Zoom atual">{zoom}%</output>
        <button type="button" className="icon-button" aria-label="Aumentar zoom" disabled={zoom >= 300} onClick={() => setZoom(value => Math.min(300, value + 25))}><ZoomIn size={18} /></button>
        <button type="button" className="button secondary" onClick={() => setRotation(value => (value + 90) % 360)} aria-label="Girar página 90 graus"><RotateCw size={16} /> {rotation}°</button>
        <button type="button" className="button secondary" onClick={() => { setZoom(100); setRotation(0); }}>Restaurar visualização</button>
      </div>
      <p className="muted" role="status">Página {index + 1} de {pages.length} · página {current.ordem} do lote</p>
      <PageCanvas key={current.page_id} page={current} zoom={zoom} rotation={rotation} />
      <details key={`text-${current.page_id}`} className="document-viewer-text">
        <summary>Texto lido (OCR) desta página</summary>
        {text.loading ? <p role="status">Carregando texto…</p> : text.error ? <p role="alert">{text.error} <button type="button" onClick={() => void text.reload()}>Tentar novamente</button></p>
          : <pre className="ocr-text">{text.data?.texto || "Nenhum texto lido nesta página."}</pre>}
      </details>
    </section>
  );
}

function PageCanvas({ page, zoom, rotation }: { page: PageRef; zoom: number; rotation: number }) {
  const viewport = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(640);
  const [size, setSize] = useState({ width: 595, height: 842 });
  const [url, setUrl] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const element = viewport.current;
    if (!element) return;
    const observer = new ResizeObserver(() => setWidth(Math.max(160, Math.min(800, element.clientWidth - 24))));
    observer.observe(element);
    return () => observer.disconnect();
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    let objectUrl: string | null = null;
    setError(""); setUrl(null);
    apiBlob(`/api/pages/${page.page_id}/image`, { signal: controller.signal }).then(blob => {
      if (controller.signal.aborted) return;
      objectUrl = URL.createObjectURL(blob); setUrl(objectUrl);
    }).catch(reason => { if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : "Imagem indisponível."); });
    return () => { controller.abort(); if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [page.page_id, attempt]);
  const rotated = rotation % 180 !== 0;
  const fitWidth = rotated ? width * size.width / size.height : width;
  const imageWidth = fitWidth * zoom / 100;
  const imageHeight = imageWidth * size.height / size.width;
  return (
    <div ref={viewport} className="document-viewer-viewport" tabIndex={0} role="region" aria-label="Imagem ampliada; use as setas para rolar">
      {error ? <p role="alert">{error} <button type="button" onClick={() => setAttempt(value => value + 1)}>Tentar novamente</button></p> : !url ? <p role="status">Carregando página…</p> : (
        <div className="document-viewer-canvas" style={{ width: rotated ? imageHeight : imageWidth, height: rotated ? imageWidth : imageHeight }}>
          <img src={url} alt={`Página ${page.ordem} do lote`} onLoad={event => setSize({ width: event.currentTarget.naturalWidth, height: event.currentTarget.naturalHeight })}
            style={{ width: imageWidth, height: imageHeight, transform: `translate(-50%, -50%) rotate(${rotation}deg)` }} />
        </div>
      )}
    </div>
  );
}
