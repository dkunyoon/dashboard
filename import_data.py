import pandas as pd
import numpy as np

str_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRfNroFE_THBtcNXvqGmIjAznHFN7d7J_oaBaUWbuGwCnpifPfAcDWDZJcgRsJ13efcmQu1LcNeXCmq/pub?output=xlsx"

df = pd.read_excel(str_url, sheet_name="Market_Data", index_col="DATE")

df.columns.tolist()


