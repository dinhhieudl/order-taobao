import sqlite3
c = sqlite3.connect('data/cache.db')
c.row_factory = sqlite3.Row
r = c.execute("SELECT customer_name, SUM(remaining) as debt FROM orders WHERE customer_name_ascii LIKE '%vy%' OR customer_name LIKE '%Vỹ%' GROUP BY customer_phone").fetchall()
for row in r:
    print(dict(row))
