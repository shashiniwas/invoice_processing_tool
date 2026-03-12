from __future__ import annotations

import requests
from django.conf import settings


class ERPSyncService:
    def build_payload(self, extracted_data: dict) -> dict:
        return {
            'vendor': extracted_data.get('vendor_name'),
            'invoice_no': extracted_data.get('invoice_number'),
            'invoice_date': extracted_data.get('invoice_date'),
            'due_date': extracted_data.get('due_date'),
            'currency': extracted_data.get('currency'),
            'total': extracted_data.get('total_amount'),
            'tax': extracted_data.get('tax_amount'),
            'document_type': extracted_data.get('invoice_type'),
            'line_items': extracted_data.get('line_items', []),
        }

    def send(self, payload: dict) -> dict:
        if settings.ERP_PROVIDER == 'mock':
            return {'status': 'accepted', 'provider': 'mock', 'payload': payload}

        response = requests.post(settings.ERP_ENDPOINT, json=payload, timeout=20)
        response.raise_for_status()
        return response.json()
