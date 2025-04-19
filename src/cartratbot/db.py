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

def get_models_by_brand(brand_name):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT m.name 
        FROM models m
        JOIN brands b ON m.brand_id = b.id
        WHERE b.name = %s
        ORDER BY m.name;
    """, (brand_name,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [row[0] for row in rows]

def get_model_details(brand_name, model_name):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT b.name, m.name, m.year_from, m.year_to, m.class, c.description
        FROM models m
        JOIN brands b ON m.brand_id = b.id
        LEFT JOIN car_classes c ON m.class = c.code
        WHERE b.name = %s AND m.name = %s;
    """, (brand_name, model_name))
    result = cur.fetchone() # Получает ОДНУ строку из результата запроса.
    cur.close()
    conn.close()
    return result
