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

# Поиск машины по марке и модели
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

# Поиск модели по user_id
def get_user_car(user_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT selected_car_brand, selected_car_model, selected_car_year_from, 
               selected_car_year_to, selected_car_class
        FROM users_cars
        WHERE user_id = %s;
    """, (user_id,))
    result = cur.fetchone()

    cur.close()
    conn.close()
    return result

# Функция сохранения авто в базу данных
# Если пользователь есть но обновляем данные, если нет - добавляем (хотя он уже с вероятностью 99% есть в базе)
def update_user_car(user_id, brand_name, model_name, year_from, year_to, car_class):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT user_id FROM users_cars WHERE user_id = %s", (user_id,))
    result = cur.fetchone()

    if result:
        cur.execute("""
            UPDATE users_cars
            SET selected_car_brand = %s, selected_car_model = %s,
                selected_car_year_from = %s, selected_car_year_to = %s,
                selected_car_class = %s
            WHERE user_id = %s
        """, (brand_name, model_name, year_from, year_to, car_class, user_id))
    else:
        cur.execute("""
            INSERT INTO users_cars (user_id, selected_car_brand, selected_car_model,
                                    selected_car_year_from, selected_car_year_to,
                                    selected_car_class)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (user_id, brand_name, model_name, year_from, year_to, car_class))

    conn.commit()
    cur.close()
    conn.close()

    # Функция удаления авто
def delete_user_car(user_id):
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("""
        UPDATE users_cars
        SET selected_car_brand = 0,
            selected_car_model = 0,
            selected_car_year_from = 0,
            selected_car_year_to = 0,
            selected_car_class = 0
        WHERE user_id = %s
        """, (user_id,))
    conn.commit()
    conn.close()
