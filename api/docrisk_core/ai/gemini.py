"""Leitor principal: Gemini Flash com visão. Dono: FRENTE 2.

Uma chamada por página -> JSON no formato de contracts.AnalisePagina.
SDK: google-genai (`from google import genai`).

Aceite:
- temperature=0 e response_mime_type="application/json"
- limitador de requisições por minuto (config.GEMINI_RPM)
- nova tentativa com espera crescente em 429 / 503 / RESOURCE_EXHAUSTED
- resposta validada por AnalisePagina.model_validate (normaliza tipos/números)
- envia SÓ a imagem (OCR real); a camada de texto do PDF não vai ao modelo
- só dados sintéticos: o plano gratuito pode usar o conteúdo enviado
"""
from __future__ import annotations

from ..contracts import AnalisePagina

PROMPT = """Você analisa UMA página digitalizada de um lote de documentos trabalhistas (dados fictícios).
Responda SOMENTE um objeto JSON com as chaves:
- "texto": transcrição integral da página (OCR)
- "tipo": um de ESPELHO_PONTO, HOLERITE, COMPROVANTE_PAGAMENTO, CONTRATO, DOCUMENTO_IDENTIFICACAO, NOTA_FISCAL, OUTRO, DESCONHECIDO
- "inicio_documento": true se a página parece a primeira de um documento (título, cabeçalho, "Página 1")
- "pagina_x", "pagina_de": números de "Página X de Y" impressos na página, ou null
- "trabalhador_id": matrícula/ID do trabalhador (ex.: T001) ou null
- "trabalhador_nome": nome impresso ou null
- "competencia": "MM/AAAA" ou null
- "legivel": false se o conteúdo essencial estiver ilegível
- "qualidade": 0 a 1, legibilidade da página
- "confianca_tipo": 0 a 1
- "campos": {"horas_extras_h", "horas_extras_valor", "valor_liquido", "valor_pago", "data_pagamento"}
Regras: não invente; use null quando o dado não estiver na página. Horas extras em HORAS vão em
horas_extras_h; em REAIS vão em horas_extras_valor; nunca converta uma na outra.
Na dúvida sobre o tipo, use DESCONHECIDO."""


class GeminiProvider:
    nome = "gemini"

    def __init__(self) -> None:
        raise NotImplementedError("Frente 2: GeminiProvider.__init__ (cliente + limitador)")

    def analisar(self, png: bytes, texto_camada: str | None) -> AnalisePagina:
        raise NotImplementedError("Frente 2: GeminiProvider.analisar")
