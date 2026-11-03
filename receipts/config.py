import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROJECT = os.getenv('GOOGLE_CLOUD_PROJECT', 'ieor-4570-f26-ap4839')
MODEL = os.getenv('GEMINI_MODEL', 'gemini-3.5-flash-lite')
USER_AGENT = os.getenv('SEC_USER_AGENT', 'TheReceipts Academic Research ap4839@columbia.edu')
# Curated starting points; ticker lookup also supports the full SEC directory.
INDUSTRIES = {
    'Automakers': ['TSLA', 'GM', 'F'],
    'Semiconductors': ['NVDA', 'AMD', 'INTC'],
    'Cloud platforms': ['MSFT', 'AMZN', 'GOOGL'],
}
COMPANIES = {
    'TSLA': ('Tesla', 1318605), 'GM': ('General Motors', 1467858),
    'F': ('Ford', 37996), 'NVDA': ('NVIDIA', 1045810),
    'AMD': ('AMD', 2488), 'INTC': ('Intel', 50863),
    'MSFT': ('Microsoft', 789019), 'AMZN': ('Amazon', 1018724),
    'GOOGL': ('Alphabet', 1652044),
}
METRICS = {
    'revenue': ['Revenues', 'RevenueFromContractWithCustomerExcludingAssessedTax', 'SalesRevenueNet', 'SalesRevenueGoodsNet'],
    'net_income': ['NetIncomeLoss', 'ProfitLoss'],
    'operating_income': ['OperatingIncomeLoss'],
    'operating_cash_flow': ['NetCashProvidedByUsedInOperatingActivities'],
    'capex': ['PaymentsToAcquirePropertyPlantAndEquipment'],
}
