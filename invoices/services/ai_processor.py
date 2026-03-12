from __future__ import annotations

import json
import re
from decimal import Decimal
from pathlib import Path

from django.conf import settings


class AIInvoiceProcessor:
    """Extract invoice metadata from any invoice layout using AI with regex fallback."""

    def extract(self, file_path: str) -> dict:
        text = Path(file_path).read_text(encoding='utf-8', errors='ignore')
        if settings.OPENAI_API_KEY:
            ai_data = self._extract_with_openai(text)
            if ai_data:
                return ai_data
        return self._extract_with_rules(text)

    def _extract_with_openai(self, content: str) -> dict:
        try:
            from openai import OpenAI
        except ImportError:
            return {}

        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        prompt = (
            'Extract invoice data from this text. '
            'Return valid compact JSON with keys: vendor_name, invoice_number, invoice_date, '
            'due_date, currency, total_amount, tax_amount, invoice_type, line_items.'
        )
        response = client.responses.create(
            model='gpt-4.1-mini',
            input=[
                {'role': 'system', 'content': 'You are an invoice extraction assistant.'},
                {'role': 'user', 'content': f'{prompt}\n\nINVOICE_TEXT:\n{content[:20000]}'},
            ],
            temperature=0,
        )
        try:
            return json.loads(response.output_text)
        except (json.JSONDecodeError, AttributeError):
            return {}

    def _extract_with_rules(self, content: str) -> dict:
        def capture(pattern: str) -> str:
            match = re.search(pattern, content, flags=re.IGNORECASE)
            return match.group(1).strip() if match else ''

        total = capture(r'total\s*[:\-]?\s*([\d,.]+)')
        tax = capture(r'(?:tax|vat)\s*[:\-]?\s*([\d,.]+)')

        return {
            'vendor_name': capture(r'(?:vendor|supplier)\s*[:\-]?\s*([^\n]+)'),
            'invoice_number': capture(r'invoice\s*(?:number|#)?\s*[:\-]?\s*([A-Za-z0-9\-/]+)'),
            'invoice_date': capture(r'invoice\s*date\s*[:\-]?\s*([\d\-/]+)'),
            'due_date': capture(r'due\s*date\s*[:\-]?\s*([\d\-/]+)'),
            'currency': capture(r'currency\s*[:\-]?\s*([A-Z]{3})') or 'USD',
            'total_amount': str(Decimal(total.replace(',', ''))) if total else None,
            'tax_amount': str(Decimal(tax.replace(',', ''))) if tax else None,
            'invoice_type': capture(r'(?:type|category)\s*[:\-]?\s*([^\n]+)') or 'general',
            'line_items': [],
        }
