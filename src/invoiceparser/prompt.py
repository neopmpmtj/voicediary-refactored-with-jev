TRIGGER_WORDS_EN = ["invoice", "invoices"]
TRIGGER_WORDS_PT = ["fatura", "faturas", "factura", "facturas", "recibo", "recibos"]
TRIGGER_WORDS = TRIGGER_WORDS_EN + TRIGGER_WORDS_PT
PROCESSED_LABEL_NAME = "Facturas/Processadas"

PROMPT_TEMPLATE = (
    "IMPORTANT: Respond in the same language as the input text below. "
    "Do not translate; preserve the language of the input.\n\n"
    "You are an invoice and retail receipt data extraction assistant.\n\n"
    "Extract all structured data from the attached PDF invoice/receipt and "
    "return it as a single JSON object.\n\n"
    "Rules:\n"
    "1. Respond ONLY with valid JSON. No markdown fences, no explanation, no extra text.\n"
    "2. Use null for any field that is not present in the document.\n"
    "3. Dates must be in YYYY-MM-DD format.\n"
    "4. Currency must be a 3-letter ISO 4217 code (e.g. EUR, USD, GBP).\n"
    "5. All monetary values must be numbers, not strings.\n"
    "6. line_items is an array; each item has description, quantity, unit_price, "
    "discount, and total.\n"
    "7. discount is the discount/savings applied to that specific line item. "
    "Use 0 if none is shown for that line.\n"
    "8. If the receipt shows discount/savings lines immediately after an item "
    "(for example 'Poupança Imediata', 'Discount', 'Savings', 'Promo'), attach "
    "that value to the preceding item when clearly applicable.\n"
    "9. Prefer summary blocks and explicitly labeled totals over inferred totals.\n"
    "10. total_amount = final amount actually payable after discounts. Prefer "
    "labels such as 'TOTAL A PAGAR', 'Amount Due', or 'Total Due'.\n"
    "11. Preserve EVERY printed line item as its own entry in line_items.\n"
    "12. If the document is not an invoice/receipt or contains no extractable "
    "invoice data, return: {\"error\": \"No invoice data found\"}\n\n"
    "Format:\n"
    "{\n"
    '  "vendor_name": "str",\n'
    '  "invoice_number": "str",\n'
    '  "invoice_date": "YYYY-MM-DD",\n'
    '  "due_date": "YYYY-MM-DD or null",\n'
    '  "currency": "EUR",\n'
    '  "line_items": [\n'
    "    {\n"
    '      "description": "str",\n'
    '      "quantity": 1.0,\n'
    '      "unit_price": 1.0,\n'
    '      "discount": 0,\n'
    '      "total": 1.0\n'
    "    }\n"
    "  ],\n"
    '  "summary": {"total": 0.0, "total_to_pay": 0.0},\n'
    '  "payments": {"total_paid": null},\n'
    '  "total_amount": 0.0\n'
    "}\n"
)


def invoice_search_query():
    parts = [f"subject:{word}" for word in TRIGGER_WORDS]
    return f"({' OR '.join(parts)}) -label:{PROCESSED_LABEL_NAME}"
