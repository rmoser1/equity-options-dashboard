"""Stock information fields exported for dashboard controls and tables."""

FIELDS_BY_CATEGORY = {
  "company_profile": [
    "longName",
    "country",
    "sector",
    "industry",
    "fullTimeEmployees",
    "longBusinessSummary",
  ],
  "market_data": [
    "ask",
    "volume",
    "averageDailyVolume3Month",
    "averageDailyVolume10Day",
    "dayHigh",
    "dayLow",
    "fiftyTwoWeekRange",
    "52WeekChange",
    "twoHundredDayAverageChangePercent",
    "beta"
  ],
  "valuation": [
    "marketCap",
    "enterpriseValue",
    "nonDilutedMarket",
    "trailingPE",
    "forwardPE",
    "priceToBook",
    "priceToSalesTrailing12Months",
    "pegRatio",
    "enterpriseToEbitda",
    "enterpriseToRevenue"
  ],
  "financial_performance": [
    "totalRevenue",
    "revenueGrowth",
    "revenuePerShare",
    "earningsGrowth",
    "earningsQuarterlyGrowth",
    "ebitda",
    "ebitdaMargins",
    "grossProfits",
    "grossMargins",
    "operatingMargins",
    "profitMargins",
    "netIncomeToCommon",
    "epsTrailingTwelveMonths",
    "epsCurrentYear",
    "epsForward",
    "trailingEps",
    "returnOnAssets",
    "returnOnEquity"
  ],
  "balance_sheet_cash_flow": [
    "totalCash",
    "totalCashPerShare",
    "totalDebt",
    "freeCashflow",
    "operatingCashflow",
    "currentRatio",
    "debtToEquity",
    "bookValue"
  ],
  "dividends_corporate_events": [
    "dividendYield",
    "dividendRate",
    "payoutRatio",
    "fiveYearAvgDividendYield",
    "lastDividendDate",
    "lastDividendValue",
    "lastFiscalYearEnd",
    "mostRecentQuarter",
    "nextFiscalYearEnd",
    "lastSplitDate",
    "lastSplitFactor"
  ],
  "ownership_structure": [
    "sharesOutstanding",
    "impliedSharesOutstanding",
    "floatShares",
    "heldPercentInsiders",
    "heldPercentInstitutions",
    "sharesShort",
    "sharesShortPriorMonth",
    "shortPercentOfFloat",
    "shortRatio"
  ],
  "etf_fund_metrics": [
    "netAssets",
    "netExpenseRatio",
    "threeYearAverageReturn",
    "trailingThreeMonthNavReturns"
  ],
}

FIELDS_NUMERIC = [
  "ask",
  "volume",
  "averageDailyVolume3Month",
  "averageDailyVolume10Day",
  "dayHigh",
  "dayLow",
  "52WeekChange",
  "twoHundredDayAverageChangePercent",
  "beta",
  "marketCap",
  "enterpriseValue",
  "nonDilutedMarket",
  "trailingPE",
  "forwardPE",
  "priceToBook",
  "priceToSalesTrailing12Months",
  "pegRatio",
  "enterpriseToEbitda",
  "enterpriseToRevenue",
  "totalRevenue",
  "revenueGrowth",
  "revenuePerShare",
  "earningsGrowth",
  "earningsQuarterlyGrowth",
  "ebitda",
  "ebitdaMargins",
  "grossProfits",
  "grossMargins",
  "operatingMargins",
  "profitMargins",
  "netIncomeToCommon",
  "epsTrailingTwelveMonths",
  "epsCurrentYear",
  "epsForward",
  "trailingEps",
  "returnOnAssets",
  "returnOnEquity",
  "totalCash",
  "totalCashPerShare",
  "totalDebt",
  "freeCashflow",
  "operatingCashflow",
  "currentRatio",
  "debtToEquity",
  "bookValue",
  "dividendYield",
  "dividendRate",
  "payoutRatio",
  "fiveYearAvgDividendYield",
  "lastDividendValue",
  "sharesOutstanding",
  "impliedSharesOutstanding",
  "floatShares",
  "heldPercentInsiders",
  "heldPercentInstitutions",
  "sharesShort",
  "sharesShortPriorMonth",
  "shortPercentOfFloat",
  "shortRatio",
  "netAssets",
  "netExpenseRatio",
  "threeYearAverageReturn",
  "trailingThreeMonthNavReturns",
  "fullTimeEmployees"
]

FIELDS_STRING = [
  "longName",
  "country",
  "sector",
  "industry",
  "longBusinessSummary",
  "fiftyTwoWeekRange",
  "lastSplitFactor",
]

FIELDS_DATE = [
  "lastFiscalYearEnd",
  "mostRecentQuarter",
  "nextFiscalYearEnd",
  "lastDividendDate",
  "lastSplitDate"
]

INFO_ITEM_NAMES = [
  item_name
  for item_names in FIELDS_BY_CATEGORY.values()
  for item_name in item_names
]

DIVIDEND_YIELD_NAMES = ["dividendYield", "Dividend Yield"]
