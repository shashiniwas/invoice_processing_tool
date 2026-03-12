from __future__ import annotations

import json
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path

import requests
from django.conf import settings


class AIInvoiceProcessor:
    """Extract invoice metadata from different invoice file types."""

    SUPPORTED_TEXT_EXTENSIONS = {'.txt', '.csv', '.json', '.xml', '.html', '.htm'}

    def extract(self, file_path: str) -> dict:
        text, tables = self._extract_text(file_path)

        if not text.strip() and not tables:
            return self._empty_result('No readable text found in invoice. For scanned PDFs/images, OCR is required.')

        combined_content = self._build_llm_content(text, tables)

        mistral_data = self._extract_with_mistral(combined_content)
        if mistral_data:
            return self._normalize_result(mistral_data, source_text=combined_content)

        rule_data = self._extract_with_rules(combined_content)
        if tables and not rule_data.get('line_items'):
            rule_data['line_items'] = tables
        return self._normalize_result(rule_data, source_text=combined_content)

    def _extract_text(self, file_path: str) -> tuple[str, list[dict]]:
        path = Path(file_path)
        ext = path.suffix.lower()

        if ext in self.SUPPORTED_TEXT_EXTENSIONS:
            return path.read_text(encoding='utf-8', errors='ignore'), []

        if ext == '.pdf':
            text, tables = self._extract_from_digital_pdf_with_pdfplumber(path)
            if self._is_likely_scanned_pdf(text):
                scanned_text, scanned_tables = self._extract_from_scanned_pdf_with_docling(path)
                if scanned_text.strip() or scanned_tables:
                    return scanned_text, scanned_tables
            return text, tables

        # fallback for unknown types: attempt text decode
        return path.read_text(encoding='utf-8', errors='ignore'), []

    def _extract_from_digital_pdf_with_pdfplumber(self, path: Path) -> tuple[str, list[dict]]:
        try:
            import pdfplumber
        except ImportError:
            return '', []

        text_chunks = []
        tables: list[dict] = []

        try:
            with pdfplumber.open(str(path)) as pdf:
                for page_index, page in enumerate(pdf.pages, start=1):
                    page_text = page.extract_text() or ''
                    if page_text:
                        text_chunks.append(page_text)

                    for table in page.extract_tables() or []:
                        normalized_rows = []
                        for row in table:
                            normalized_rows.append([(cell or '').strip() for cell in row])
                        if normalized_rows:
                            tables.append({'page': page_index, 'rows': normalized_rows})
        except Exception:
            return '', []

        return '\n'.join(text_chunks), tables

    def _extract_from_scanned_pdf_with_docling(self, path: Path) -> tuple[str, list[dict]]:
        try:
            from docling.document_converter import DocumentConverter
        except ImportError:
            return '', []

        try:
            converter = DocumentConverter()
            result = converter.convert(str(path))
            document = result.document
        except Exception:
            return '', []

        text = ''
        tables: list[dict] = []

        try:
            text = document.export_to_markdown() or ''
        except Exception:
            text = ''

        # Best-effort table extraction for docling result shapes
        extracted_tables = getattr(document, 'tables', None)
        if extracted_tables:
            for idx, table in enumerate(extracted_tables, start=1):
                rows = []
                data = getattr(table, 'data', None)
                if data and isinstance(data, list):
                    for row in data:
                        if isinstance(row, list):
                            rows.append([str(cell).strip() for cell in row])
                if rows:
                    tables.append({'page': idx, 'rows': rows})

        return text, tables

    def _extract_with_mistral(self, content: str) -> dict:
        api_key = getattr(settings, 'MISTRAL_API_KEY', '')
        if not api_key:
            return {}

        model = getattr(settings, 'MISTRAL_MODEL', 'mistral-small-latest')
        prompt = (
            'Extract invoice data from this content. Return valid JSON with keys: '
            'vendor_name, invoice_number, invoice_date, due_date, currency, total_amount, '
            'tax_amount, invoice_type, line_items.'
        )

        try:
            response = requests.post(
                'https://api.mistral.ai/v1/chat/completions',
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json',
                },
                json={
                    'model': model,
                    'temperature': 0,
                    'messages': [
                        {'role': 'system', 'content': 'You are an invoice extraction assistant.'},
                        {'role': 'user', 'content': f'{prompt}\n\nINVOICE_CONTENT:\n{content[:24000]}'},
                    ],
                    'response_format': {'type': 'json_object'},
                },
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
            message = payload['choices'][0]['message']['content']
            return json.loads(message)
        except Exception:
            return {}

    def _extract_with_rules(self, content: str) -> dict:
        def capture(pattern: str) -> str:
            match = re.search(pattern, content, flags=re.IGNORECASE)
            return match.group(1).strip() if match else ''

        total = self._parse_amount(
            capture(r'(?:grand\s*total|total\s*amount|amount\s*due|total)\s*[:\-]?\s*([$€£]?\s*[\d,.]+)')
        )
        tax = self._parse_amount(capture(r'(?:tax|vat|gst)\s*[:\-]?\s*([$€£]?\s*[\d,.]+)'))

        return {
            'vendor_name': capture(r'(?:vendor|supplier|from|bill\s*from)\s*[:\-]?\s*([^\n]+)'),
            'invoice_number': capture(r'invoice\s*(?:number|#|no\.?|id)?\s*[:\-]?\s*([A-Za-z0-9\-/]+)'),
            'invoice_date': capture(r'invoice\s*date\s*[:\-]?\s*([\d\-/\.]+)'),
            'due_date': capture(r'due\s*date\s*[:\-]?\s*([\d\-/\.]+)'),
            'currency': self._detect_currency(content),
            'total_amount': str(total) if total is not None else None,
            'tax_amount': str(tax) if tax is not None else None,
            'invoice_type': capture(r'(?:type|category)\s*[:\-]?\s*([^\n]+)') or 'general',
            'line_items': [],
        }

    def _build_llm_content(self, text: str, tables: list[dict]) -> str:
        content = text or ''
        if tables:
            table_lines = ['\n\nEXTRACTED_TABLES:']
            for table in tables:
                table_lines.append(f"Page {table.get('page', '?')}")
                for row in table.get('rows', []):
                    table_lines.append(' | '.join(row))
            content += '\n'.join(table_lines)
        return content

    def _is_likely_scanned_pdf(self, text: str) -> bool:
        return len((text or '').strip()) < 20

    def _detect_currency(self, content: str) -> str:
        explicit = re.search(r'currency\s*[:\-]?\s*([A-Z]{3})', content, flags=re.IGNORECASE)
        if explicit:
            return explicit.group(1).upper()

        symbol_map = {'$': 'USD', '€': 'EUR', '£': 'GBP'}
        for symbol, code in symbol_map.items():
            if symbol in content:
                return code

        return 'USD'

    def _parse_amount(self, raw: str) -> Decimal | None:
        if not raw:
            return None
        cleaned = raw.replace(',', '').replace('$', '').replace('€', '').replace('£', '').strip()
        try:
            return Decimal(cleaned)
        except (InvalidOperation, ValueError):
            return None

    def _empty_result(self, reason: str) -> dict:
        return {
            'vendor_name': '',
            'invoice_number': '',
            'invoice_date': '',
            'due_date': '',
            'currency': 'USD',
            'total_amount': None,
            'tax_amount': None,
            'invoice_type': 'general',
            'line_items': [],
            'warnings': [reason],
        }

    def _normalize_result(self, data: dict, source_text: str) -> dict:
        normalized = {
            'vendor_name': data.get('vendor_name', '') or '',
            'invoice_number': data.get('invoice_number', '') or '',
            'invoice_date': data.get('invoice_date', '') or '',
            'due_date': data.get('due_date', '') or '',
            'currency': (data.get('currency') or 'USD').upper(),
            'total_amount': data.get('total_amount'),
            'tax_amount': data.get('tax_amount'),
            'invoice_type': data.get('invoice_type', 'general') or 'general',
            'line_items': data.get('line_items', []) or [],
        }
        if data.get('warnings'):
            normalized['warnings'] = data['warnings']
        normalized['text_preview'] = source_text[:800]
        return normalized
