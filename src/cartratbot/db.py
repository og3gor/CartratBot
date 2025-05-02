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
        # Удаление расходов при удалении авто теперь реализует тригер в БД
        # # Получаем все id расходов пользователя
        # cur.execute("SELECT id FROM expenses WHERE user_id = %s", (user_id,))
        # expense_ids = [row[0] for row in cur.fetchall()]

        # if expense_ids:
        #     # Удаляем связанные записи из refuels и other_expenses
        #     cur.execute("DELETE FROM refuels WHERE expense_id = ANY(%s)", (expense_ids,))
        #     cur.execute("DELETE FROM other_expenses WHERE expense_id = ANY(%s)", (expense_ids,))

        #     # Удаляем из expenses
        #     cur.execute("DELETE FROM expenses WHERE id = ANY(%s)", (expense_ids,))

        # Обнуляем информацию о машине у пользователя
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


def update_user_car(user_id, car_id, car_nickname=None):
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

        # Обновляем запись пользователя, присваиваем car_id и кличку (если указана)
        cur.execute("""
            UPDATE users
            SET car_id = %s,
                car_nickname = %s,
                state = 'Default'
            WHERE id = %s
        """, (car_id, car_nickname, user_id))
        
        conn.commit()
        return True

    except Exception as e:
        print(f"[ERROR] Ошибка при обновлении машины пользователя: {e}")
        conn.rollback()
        return False

    finally:
        cur.close()
        conn.close()

# Работа с расходами на авто

# Получить список всех видов топлива
def get_all_fuel_types():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT name FROM fuel_types")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [r[0] for r in rows]

# Получить ID топлива по названию
def get_fuel_type_id(name):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM fuel_types WHERE name = %s", (name,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row[0] if row else None

# Получить список типов прочих расходов
def get_other_expense_types():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT name FROM other_expense_types")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [r[0] for r in rows]

# Получить ID типа прочего расхода
def get_other_expense_type_id(name):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM other_expense_types WHERE name = %s", (name,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row[0] if row else None

# Добавить заправку
def add_refuel(user_id, fuel_type_id, date, liters, price_total, comment=None):
    conn = get_connection()
    cur = conn.cursor()
    try:
        # Получаем type_id для 'refuel'
        cur.execute("SELECT id FROM expense_types WHERE name = 'refuel'")
        type_id = cur.fetchone()[0]

        # Добавляем запись в expenses
        cur.execute("""
            INSERT INTO expenses (user_id, expense_date, type_id)
            VALUES (%s, %s, %s)
            RETURNING id
        """, (user_id, date, type_id))
        expense_id = cur.fetchone()[0]

        # Добавляем запись в refuels
        cur.execute("""
            INSERT INTO refuels (expense_id, fuel_type_id, liters, price_total, comment)
            VALUES (%s, %s, %s, %s, %s)
        """, (expense_id, fuel_type_id, liters, price_total, comment))

        conn.commit()
    finally:
        cur.close()
        conn.close()

# Добавить другой расход
def add_other_expense(user_id, other_type_id, date, amount, comment=None):
    conn = get_connection()
    cur = conn.cursor()
    try:
        # Получаем type_id для 'other'
        cur.execute("SELECT id FROM expense_types WHERE name = 'other'")
        type_id = cur.fetchone()[0]

        # Добавляем в expenses
        cur.execute("""
            INSERT INTO expenses (user_id, expense_date, type_id)
            VALUES (%s, %s, %s)
            RETURNING id
        """, (user_id, date, type_id))
        expense_id = cur.fetchone()[0]

        # Добавляем в other_expenses
        cur.execute("""
            INSERT INTO other_expenses (expense_id, type_id, amount, comment)
            VALUES (%s, %s, %s, %s)
        """, (expense_id, other_type_id, amount, comment))

        conn.commit()
    finally:
        cur.close()
        conn.close()

def get_price_for_fuel(fuel_type_id, date):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT price_per_liter
        FROM fuel_prices
        WHERE fuel_type_id = %s AND price_date <= %s  -- выбираем цену на дату или раньше
        ORDER BY price_date DESC
        LIMIT 1
    """, (fuel_type_id, date))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return float(row[0]) if row else None

def get_fuel_name_by_id(fuel_type_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT name
        FROM fuel_types
        WHERE id = %s;
    """, (fuel_type_id,))
    result = cur.fetchone()

    cur.close()
    conn.close()
    return result[0]

def get_other_expense_type_name_by_id(type_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT name FROM other_expense_types WHERE id = %s;", (type_id,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result[0] if result else "Неизвестно"


def get_full_expense_history(user_id):
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 
                et.name AS expense_type,
                e.expense_date,
                ft.name AS fuel_name,
                r.liters,
                r.price_total,
                oet.name AS other_name,
                o.amount,
                COALESCE(r.comment, o.comment) AS comment
            FROM expenses e
            JOIN expense_types et ON e.type_id = et.id
            LEFT JOIN refuels r ON r.expense_id = e.id
            LEFT JOIN fuel_types ft ON r.fuel_type_id = ft.id
            LEFT JOIN other_expenses o ON o.expense_id = e.id
            LEFT JOIN other_expense_types oet ON o.type_id = oet.id
            WHERE e.user_id = %s
            ORDER BY e.expense_date DESC
        """, (user_id,))
        return cur.fetchall()