"""ocr_fallback.py — OCR fallback para PDFs vetoriais sem texto extraível.

Usado quando pdfplumber/pymupdf retornam zero (ou quase zero) chars de uma
página. Renderiza cada página em PNG via PyMuPDF e roda Tesseract com
idioma português. O resultado é cacheado por (path, mtime) para evitar
OCR redundante quando pipeline e parser pedem o texto separadamente.

Sessão 20 — primeira inserção: extrato Banco Inter gerado por
"Microsoft Print To PDF" (vetorial puro).
"""
from __future__ import annotations

import io
import os
import time
from typing import Optional

# Imports lazy: se Tesseract não estiver instalado, módulo carrega mas
# `extrair_texto_via_ocr` retorna '' e não quebra o pipeline.
try:
    import fitz  # type: ignore
    import pytesseract  # type: ignore
    from PIL import Image  # type: ignore
    _DEPS_OK = True
except ImportError:
    _DEPS_OK = False


_OCR_DPI = 200
_OCR_LANG = 'por'
_CACHE: dict[str, tuple[float, str]] = {}


def _aspas_e_ruido(texto: str) -> str:
    """Normaliza ruído típico de OCR: aspas tipográficas, espaços extras."""
    return (texto
            .replace('“', '"').replace('”', '"')
            .replace('‘', "'").replace('’', "'")
            .replace(' ', ' '))


def normalizar_texto_ocr(texto: str) -> str:
    """API pública para outros módulos aplicarem o mesmo saneamento."""
    return _aspas_e_ruido(texto)


def extrair_texto_via_ocr(pdf_path: str,
                          senha: Optional[str] = None,
                          dpi: int = _OCR_DPI) -> str:
    """Renderiza páginas e aplica Tesseract. Retorna texto concatenado.

    Usa cache por (path, mtime). Retorna '' se Tesseract/PyMuPDF ausentes
    ou se OCR falhar.
    """
    if not _DEPS_OK:
        return ''
    try:
        mtime = os.path.getmtime(pdf_path)
    except OSError:
        return ''
    cached = _CACHE.get(pdf_path)
    if cached and cached[0] == mtime:
        return cached[1]

    t0 = time.time()
    paginas: list[str] = []
    try:
        doc = fitz.open(pdf_path)
        if senha:
            doc.authenticate(senha)
        for page in doc:
            pix = page.get_pixmap(dpi=dpi)
            img = Image.open(io.BytesIO(pix.tobytes('png')))
            txt = pytesseract.image_to_string(img, lang=_OCR_LANG)
            paginas.append(txt)
        doc.close()
    except Exception as e:
        print(f'[OCR-FALLBACK] erro arquivo={os.path.basename(pdf_path)} '
              f'erro={str(e)[:80]!r}')
        return ''

    texto = _aspas_e_ruido('\n'.join(paginas))
    elapsed = time.time() - t0
    print(f'[OCR-FALLBACK] arquivo={os.path.basename(pdf_path)} '
          f'paginas={len(paginas)} chars={len(texto)} tempo={elapsed:.2f}s')
    _CACHE[pdf_path] = (mtime, texto)
    return texto


def tesseract_disponivel() -> bool:
    """True se pytesseract + Tesseract binário estão acessíveis."""
    if not _DEPS_OK:
        return False
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False
