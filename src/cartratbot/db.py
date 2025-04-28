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

# Поиск машины по марке и модели (выводит в начале уникальный id) нужно для поиска при добавлении по марке и модели
def get_model_details(brand_name, model_name):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT m.id, b.name, m.name, m.year_from, m.year_to, m.class, c.description
        FROM models m
        JOIN brands b ON m.brand_id = b.id
        LEFT JOIN car_classes c ON m.class = c.code
        WHERE b.name = %s AND m.name = %s;
    """, (brand_name, model_name))
    result = cur.fetchone() # Получает ОДНУ строку из результата запроса.
    cur.close()
    conn.close()
    return result

def get_car(car_id):
    conn = get_connection()
    cur = conn.cursor()
    try:
        # Запрос для получения данных о машине, используя таблицы models и brands
        cur.execute("""
            SELECT b.name AS brand_name, m.name AS model_name, m.year_from, m.year_to, m.class
            FROM models m
            JOIN brands b ON m.brand_id = b.id
            WHERE m.id = %s;
        """, (car_id,))
        result = cur.fetchone()
        if result:
            brand_name, model_name, year_from, year_to, car_class = result
            return brand_name, model_name, year_from, year_to, car_class
        else:
            return None
    except Exception as e:
        print(f"[ERROR] Ошибка при получении данных о машине: {e}")
        return None
    finally:
        cur.close()
        conn.close()


# Обновление состояния пользователя в базе данных
def update_user_state(user_id, state):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE users
        SET state = %s
        WHERE id = %s;
    """, (state, user_id))
    conn.commit()

    cur.close()
    conn.close()


# Поиск человека по user_id
def get_user(user_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, car_id, car_nickname, state
        FROM users
        WHERE id = %s;
    """, (user_id,))
    result = cur.fetchone()

    cur.close()
    conn.close()
    return result

def get_class_description(car_class):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT description
        FROM car_classes
        WHERE code = %s;
    """, (car_class,))
    result = cur.fetchone()

    cur.close()
    conn.close()
    return result

def add_user(user_id, state): # Состояние state отправлять строку а не типа State
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO users (id, car_id, car_nickname, state)
        VALUES (%s, NULL, NULL, %s)
    """, (user_id, state))
    conn.commit()

    cur.close()
    conn.close()


    # Функция удаления авто
def delete_user_car(user_id):
    conn = get_connection()
    cur = conn.cursor()
    try:
        # Обновляем запись пользователя, сбрасывая данные о машине в начальные значения
        cur.execute("""
            UPDATE users
            SET car_id = NULL,
                car_nickname = NULL
            WHERE id = %s
        """, (user_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"[ERROR] Ошибка при удалении автомобиля пользователя: {e}")
        conn.rollback()
        return False
    finally:
        cur.close()
        conn.close()


def update_user_car(user_id, car_id):
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        # Проверяем, существует ли car_id в таблице models
        cur.execute("""
            SELECT id FROM models
            WHERE id = %s
        """, (car_id,))
        
        car_result = cur.fetchone()
        
        if not car_result:
            print("[ERROR] Машина с таким car_id не существует.")
            return False  # Возвращаем False, если машина не найдена
        
        # Обновляем запись о пользователе, присваиваем car_id
        cur.execute("""
            UPDATE users
            SET car_id = %s, state = 'Default'
            WHERE id = %s
        """, (car_id, user_id))
        
        conn.commit()
        return True
        
    except Exception as e:
        print(f"[ERROR] Ошибка при обновлении машины пользователя: {e}")
        conn.rollback()
        return False
        
    finally:
        cur.close()
        conn.close()