print("Start CartratBot")

from config import BOT_TOKEN

from db import get_all_brands, get_models_by_brand, get_model_details, get_connection

import telebot
from telebot import types

bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    # Устанавливаем доступные команды в интерфейсе Telegram
    bot.set_my_commands([
        types.BotCommand("/start", "Start the bot"),
        types.BotCommand("/help", "Get help"),
        types.BotCommand("/car", "My car"),
    ])
    # Убираем предыдущие кнопки
    remove_keyboard = types.ReplyKeyboardRemove()
    bot.send_message(message.chat.id, 
                     "Привет, это бот для подсчета денег, потраченных на автомобиль, как если бы это были топливо, штрафы и страховка.\nВыбери команду помощи (\\help) для получения более подробной информации или же просто начни пользоваться😁\n\n",
                     reply_markup=remove_keyboard)
    

def update_user_car(user_id, brand_name, model_name, year_from, year_to, car_class):
    conn = get_connection()
    cur = conn.cursor()

    # Проверяем, существует ли пользователь в базе данных
    cur.execute("""
        SELECT user_id FROM users_cars WHERE user_id = %s;
    """, (user_id,))
    result = cur.fetchone()

    if result:
        # Если пользователь существует, обновляем его данные
        cur.execute("""
            UPDATE users_cars
            SET selected_car_brand = %s, selected_car_model = %s, selected_car_year_from = %s, 
                selected_car_year_to = %s, selected_car_class = %s
            WHERE user_id = %s;
        """, (brand_name, model_name, year_from, year_to, car_class, user_id))
    else:
        # Если пользователя нет, добавляем новый
        cur.execute("""
            INSERT INTO users_cars (user_id, selected_car_brand, selected_car_model, 
                                    selected_car_year_from, selected_car_year_to, selected_car_class)
            VALUES (%s, %s, %s, %s, %s, %s);
        """, (user_id, brand_name, model_name, year_from, year_to, car_class))

    conn.commit()
    cur.close()
    conn.close()

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
    

@bot.message_handler(commands=["car"])
def car(message):
    # Показываем кнопку поиска
    brands = get_all_brands()  # Получаем все марки автомобилей
    markup = types.ReplyKeyboardMarkup()
    markup.add(types.KeyboardButton(text="🔍 Поиск марки"))
    markup.add(types.KeyboardButton(text="Мой авто"))
    user_id = message.from_user.id
    car_details = get_user_car(user_id)
    if car_details:
        markup.add(types.KeyboardButton(text="⚠️ Сменить авто"))
    
    bot.send_message(message.chat.id, "Воспользуйтесь поиском или выберите 'Мой авто'", reply_markup=markup)


@bot.message_handler(func=lambda message: message.text == "⚠️ Сменить авто")
def confirm_car_reset(message):
    warning_text = (
        "❗ У вас уже выбран автомобиль.\n"
        "Если вы смените авто, все связанные с ним расходы и история будут удалены.\n\n"
        "Вы уверены, что хотите продолжить?"
    )
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton(text="✅ Подтвердить смену авто"))
    markup.add(types.KeyboardButton(text="❌ Отмена"))
    bot.send_message(message.chat.id, warning_text, reply_markup=markup)

pending_reset = set()  # chat_id'ы пользователей, подтвердивших сброс (пока пользователь не выберет новый авто он будет находиться в этом списке)

@bot.message_handler(func=lambda message: message.text == "✅ Подтвердить смену авто")
def approve_reset(message):
    user_id = message.from_user.id
    pending_reset.add(user_id)

    # Очистка базы (если нужно — добавим удаление расходов)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM users_cars WHERE user_id = %s", (user_id,))
    # cur.execute("DELETE FROM car_expenses WHERE user_id = %s", (user_id,))  # если есть
    conn.commit()
    cur.close()
    conn.close()

    bot.send_message(message.chat.id, "Вы можете выбрать новый автомобиль. Воспользуйтесь поиском:")
    search_brand(message)  # Переводим пользователя в выбор марки

@bot.message_handler(func=lambda message: message.text == "Мой авто")
def my_car(message):
    user_id = message.from_user.id
    car_details = get_user_car(user_id)

    if car_details:
        brand_name, model_name, year_from, year_to, car_class = car_details
        text = f"🚗 Ваш автомобиль: <b>{brand_name} {model_name}</b>\n" \
               f"Годы выпуска: {year_from}–{year_to}\n" \
               f"Класс: {car_class}"
    else:
        text = "У вас нет выбранного автомобиля. Пожалуйста, выберите автомобиль через поиск."

    bot.send_message(message.chat.id, text, parse_mode='HTML')

@bot.message_handler(func=lambda message: message.text == "🔍 Поиск марки")
def search_brand(message):
    msg = bot.send_message(message.chat.id, "Введите название марки или первые буквы:")
    bot.register_next_step_handler(msg, process_brand_search)

def process_brand_search(message):
    search_text = message.text.lower()
    all_brands = get_all_brands()
    matching_brands = [brand for brand in all_brands if brand.lower().startswith(search_text)]

    if matching_brands:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        brand_buttons = [types.KeyboardButton(text=brand) for brand in matching_brands[:10]]
        markup.add(*brand_buttons)
        markup.add(types.KeyboardButton(text="🔍 Поиск марки"), types.KeyboardButton(text="◀️ Назад в меню"))
        
        msg = bot.send_message(message.chat.id, f"Найдено {len(matching_brands)} марок. Выберите одну:", reply_markup=markup)

        # Вот это ключевой момент:
        bot.register_next_step_handler(msg, process_brand_selection)

    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton(text="🔍 Поиск марки"), types.KeyboardButton(text="◀️ Назад в меню"))
        
        bot.send_message(message.chat.id, "Марки не найдены. Попробуйте другой запрос:", reply_markup=markup)

# Словарь для временного хранения выбора бренда
user_selected_brand = {}

def process_brand_selection(message):
    brand = message.text.strip()
    user_selected_brand[message.chat.id] = brand
    models = get_models_by_brand(brand)

    if models:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        for model in models:
            markup.add(types.KeyboardButton(text=model))
        msg = bot.send_message(message.chat.id, f"Выберите модель для марки {brand}:", reply_markup=markup)
        bot.register_next_step_handler(msg, process_model_selection)
    else:
        bot.send_message(message.chat.id, f"Для марки {brand} не найдено моделей.")

def process_model_selection(message):
    model = message.text.strip()
    user_id = message.from_user.id
    brand = user_selected_brand.get(message.chat.id)

    if not brand:
        bot.send_message(message.chat.id, "Произошла ошибка. Начните сначала.")
        return
    
    if get_user_car(user_id) and user_id not in pending_reset:
        bot.send_message(message.chat.id,
                     "У вас уже выбран автомобиль. Чтобы сменить его, нажмите кнопку '⚠️ Сменить авто' в меню.")
        return

    details = get_model_details(brand, model)
    if details:
        brand_name, model_name, year_from, year_to, car_class, class_description = details

        # Сохраняем выбор в базу данных
        update_user_car(user_id, brand_name, model_name, year_from, year_to, car_class)

        #удаляем id пользователья из списка подтверждённых на сброс (моего авто)
        if user_id in pending_reset:
            pending_reset.remove(user_id)

        text = f"🚗 <b>{brand_name} {model_name}</b>\n" \
               f"Годы выпуска: {year_from}–{year_to}\n" \
               f"Класс: {car_class} ({class_description})"
        bot.send_message(message.chat.id, text, parse_mode='HTML')
    else:
        bot.send_message(message.chat.id, "Модель не найдена. Попробуйте ещё раз.")

# Функция сохранения авто в базу данных
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

bot.infinity_polling()


