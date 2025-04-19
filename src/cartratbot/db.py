import psycopg2

from config import PASS_DB


def get_connection():
    return psycopg2.connect(
        dbname="cars",
        user="postgres",
        password=PASS_DB,
        host="localhost",
        port=5432
    )

def get_all_brands():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT name FROM brands ORDER BY name;")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [row[0] for row in rows]

