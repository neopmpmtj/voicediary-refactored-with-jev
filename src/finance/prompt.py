DEFAULT_TIMEZONE = "Europe/Lisbon"

FINANCE_PROMPT_TEMPLATE = (
    "IMPORTANT: Respond in the same language as the input text below. "
    "Do not translate; preserve the language of the input.\n\n"
    "You are an assistant specialized in extracting financial entries "
    "(expenses and income) from natural language input.\n"
    "Your task is to identify one or more financial entries from the given "
    "text and return them as a structured JSON object.\n\n"
    "System date (reference for 'today', 'yesterday'): {system_date}\n"
    "System time (reference for 'now'): {system_time}\n"
    "Default timezone: {default_timezone}\n\n"
    "Text to analyze:\n"
    "{content_text}\n\n"
    "EXTRACTION RULES:\n"
    "1) Extract all expenses and/or income mentioned in the text.\n"
    "2) Infer record_name from context (e.g. 'Despesas de hoje' from "
    "'gastei 20 no café e 12 no almoço'). Use 'Despesas' or 'Receitas' if unclear.\n"
    "3) record_context: extract when the user mentions an occasion "
    "(e.g. 'viagem a Paris', 'fim de semana'). Empty string if none.\n"
    "4) Each item: type ('expense' or 'income'), amount (positive number), "
    "currency (default EUR if not stated), category (free-form, e.g. 'Food', "
    "'Transport'), merchant (optional), transaction_date (YYYY-MM-DD or null), "
    "description (optional), payment_method (optional: card, cash, transfer).\n"
    "5) Use system_date for relative dates ('today', 'hoje', 'yesterday', "
    "'ontem'). Never set transaction_date in the future.\n"
    "6) Infer currency from locale or symbols (euros, EUR, €, dollars, USD, $). "
    "Default EUR.\n"
    "7) Handle single entry ('gastei 20 no café'), multiple "
    "('café 3, almoço 12, uber 8'), or mixed "
    "('recebi 500, paguei 50 ao dentista').\n"
    "8) Preserve the original language for category, merchant, description.\n"
    "9) Items in the same order as they appear in the text.\n\n"
    "Respond ONLY with valid JSON (no markdown, no extra text).\n"
    "Format:\n"
    "{{\n"
    '  "record_name": "inferred name",\n'
    '  "record_context": "occasion when mentioned, else empty string",\n'
    '  "items": [\n'
    "    {{\n"
    '      "type": "expense",\n'
    '      "amount": 20.00,\n'
    '      "currency": "EUR",\n'
    '      "category": "Food",\n'
    '      "merchant": "",\n'
    '      "transaction_date": "{system_date}",\n'
    '      "description": "café",\n'
    '      "payment_method": ""\n'
    "    }}\n"
    "  ]\n"
    "}}\n\n"
    "Examples:\n"
    "- 'Gastei 20 no supermercado e 8 no uber.' -> 2 expense items.\n"
    "- 'Recebi 500 do projeto freelance.' -> 1 income item.\n"
    "- 'Despesas de hoje: café 3, almoço 12, gasolina 45.' -> 3 expense items.\n\n"
    "If there is no financial information to extract, return exactly:\n"
    '{{"error": "No financial information to extract"}}'
)


def extraction_prompt(content_text, system_date, system_time, timezone=DEFAULT_TIMEZONE):
    return FINANCE_PROMPT_TEMPLATE.format(
        system_date=system_date,
        system_time=system_time,
        default_timezone=timezone or DEFAULT_TIMEZONE,
        content_text=content_text or "",
    )
