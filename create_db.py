# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
import sqlite3
import os

db_path = 'data/combined/fin_data.db'
if os.path.exists(db_path):
    os.remove(db_path)

conn = sqlite3.connect(db_path)

# Create tables
conn.execute('''
    CREATE TABLE IF NOT EXISTS stock_price (
        code    TEXT,
        date    TEXT,
        open    REAL,
        close   REAL,
        high    REAL,
        low     REAL,
        volume  REAL,
        amount  REAL,
        log_return REAL,
        is_extreme INTEGER,
        hs300_close REAL,
        zz500_close REAL,
        cpi_yoy REAL,
        m2_yoy REAL
    )
''')

conn.execute('''
    CREATE TABLE IF NOT EXISTS macro_data (
        date      TEXT,
        indicator TEXT,
        value     REAL,
        PRIMARY KEY (date, indicator)
    )
''')

conn.execute('''
    CREATE TABLE IF NOT EXISTS stock_info (
        code     TEXT PRIMARY KEY,
        name     TEXT,
        industry TEXT
    )
''')
conn.commit()

# Insert stock data
df = pd.read_csv('data/combined/combined_data.csv', index_col=0)
db_insert = df.copy()
db_insert['date'] = db_insert.index.astype(str)
db_insert['is_extreme'] = db_insert['is_extreme'].astype(int)
db_insert['code'] = db_insert['code'].astype(str)

col_map = {
    '\u5f00\u76d8\u4ef7': 'open',  # 开盘价
    '\u6536\u76d8\u4ef7': 'close',  # 收盘价
    '\u6700\u9ad8\u4ef7': 'high',  # 最高价
    '\u6700\u4f4e\u4ef7': 'low',   # 最低价
    '\u6210\u4ea4\u91cf': 'volume',  # 成交量
    '\u6210\u4ea4\u989d': 'amount'   # 成交额
}
db_insert = db_insert.rename(columns=col_map)

insert_cols = ['code', 'date', 'open', 'close', 'high', 'low', 'volume', 'amount',
               'log_return', 'is_extreme', 'hs300_close', 'zz500_close', 'cpi_yoy', 'm2_yoy']
available_cols = [c for c in insert_cols if c in db_insert.columns]
db_insert_final = db_insert[available_cols]

print(f'Inserting {len(db_insert_final)} rows into stock_price')
db_insert_final.to_sql('stock_price', conn, if_exists='append', index=False)
print('stock_price inserted!')

# Insert stock info
stock_info_data = [
    ('601398', '工商银行', '银行'), ('000001', '平安银行', '银行'),
    ('000625', '长安汽车', '汽车'), ('600104', '上汽集团', '汽车'),
    ('000002', '万科A', '房地产'), ('600048', '保利发展', '房地产'),
    ('000858', '五粮液', '白酒'), ('600519', '贵州茅台', '白酒'),
    ('601857', '中国石油', '能源'), ('600028', '中国石化', '能源'),
]
for row in stock_info_data:
    conn.execute('INSERT OR REPLACE INTO stock_info VALUES (?, ?, ?)', row)
conn.commit()
print('stock_info inserted!')

# Insert macro data
cpi = pd.read_csv('data/macro/macro_cpi.csv')
cpi['date'] = pd.to_datetime(cpi['date'])
for _, row in cpi.iterrows():
    ym = row['date'].strftime('%Y-%m')
    val = row['cpi_yoy']
    if pd.notna(val):
        conn.execute('INSERT OR REPLACE INTO macro_data VALUES (?, ?, ?)',
                     (ym, 'cpi', float(val)))

m2 = pd.read_csv('data/macro/macro_m2.csv')
m2['date'] = pd.to_datetime(m2['date'])
for _, row in m2.iterrows():
    ym = row['date'].strftime('%Y-%m')
    val = float(row['m2_yoy']) if not pd.isna(row['m2_yoy']) else None
    if val is not None:
        conn.execute('INSERT OR REPLACE INTO macro_data VALUES (?, ?, ?)',
                     (ym, 'm2', val))

conn.commit()
print('macro_data inserted!')

# Test queries
query = """
SELECT p.date, p.code, p.close, m.value AS cpi
FROM stock_price p
LEFT JOIN macro_data m
       ON substr(p.date, 1, 7) = substr(m.date, 1, 7)
      AND m.indicator = 'cpi'
LIMIT 5
"""
print('\n=== JOIN Test ===')
print(pd.read_sql_query(query, conn))

conn.close()
print('\nDatabase created successfully!')
