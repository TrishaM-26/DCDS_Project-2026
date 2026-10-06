from db.mysql_conn import run_query

rows = run_query("SELECT COUNT(*) AS total FROM donors", fetch=True)

if rows:
    print(f"Connected to MySQL. Donors in database: {rows[0]['total']}")
else:
    print("MySQL test failed - see the error printed above")