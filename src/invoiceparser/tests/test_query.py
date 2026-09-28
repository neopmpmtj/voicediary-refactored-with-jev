import pytest

from src.invoiceparser.prompt import PROCESSED_LABEL_NAME, invoice_search_query

pytestmark = pytest.mark.unit


def test_invoice_query_uses_trigger_words_and_excludes_processed_label():
    query = invoice_search_query()
    assert "subject:invoice" in query
    assert "subject:fatura" in query
    assert "subject:recibo" in query
    assert f"-label:{PROCESSED_LABEL_NAME}" in query
    assert PROCESSED_LABEL_NAME == "Facturas/Processadas"
