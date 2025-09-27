print("Start CartratBot")

from config import BOT_TOKEN

from db import get_all_brands, get_models_by_brand, get_model_details, get_connection, get_user, add_user, update_user_state
from db import update_user_car, delete_user_car, get_car, get_class_description
from db import get_all_fuel_types, get_fuel_type_id, get_other_expense_types, get_other_expense_type_id, add_refuel, add_other_expense, get_price_for_fuel, get_fuel_name_by_id, get_other_expense_type_name_by_id, get_full_expense_history

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

import telebot
from telebot import types
from telebot.handler_backends import State, StatesGroup     # FSM
from telebot.types import ReplyKeyboardRemove               # Удаление клавиатуры
from telebot.storage import StateMemoryStorage              # Память состояний

state_storage = StateMemoryStorage()
bot = telebot.TeleBot(BOT_TOKEN, state_storage=state_storage)
# Состояния - для запуска после перезагурзаки бота (чтобы пользователь был на том же пункте)
State.DEFAULT_STATE = 'Default'
# Определяем состояние для FSM
class CarStates(StatesGroup):
    WaitingStart = State() # Состояние "start"
    WaitingForMycar = State() # Состояние "🏎️ Моя машина"
    WaitingForBrandSearch = State() # Состояние "🔍 Поиск марки"
    WaitingChangingTheCar = State() # Состояние "⚠️ Сменить авто"
    WaitingDeleteACar = State() # Состояние "❌ Удалить авто"
    WaitingForExpenses = State() # Состояние "⛽ Расходы"
    ChoosingFuelType = State() # Состояние "➕ Заправка->Выбор топлива"
    ChoosingOtherExpenseType = State() # Состояние "➕ Прочий расход->Выбор типа расхода"
    EnteringLiters = State() # Состояние "➕ Заправка->Ввод литров"
    EnteringDate = State() # Состояние "➕ Заправка->Ввод даты"
    # Прочие расходы
    EnteringOtherExpenseSum = State() # Состояние "➕ Прочий расход->Ввод суммы"
    EnteringOtherExpenseDate = State() # Состояние "➕ Прочий расход->Ввод даты"
    EnteringOtherExpenseComment = State() # Состояние "➕ Прочий расход->Ввод комментария"


@bot.message_handler(commands=['help'])
def send_help(message):
    help_text = (
        "Это CartratBot – бот для учёта расходов на автомобиль.\n\n"
        "Вот что я умею:\n"
        "- Выбор автомобиля\n"
        "- Учёт расходов на автомобиль\n"
        "- Напоминания о ТО и других событиях\n\n"
        "Чтобы начать, используйте команду /car для выбора автомобиля."
    )
    bot.send_message(message.chat.id, help_text, parse_mode='HTML')
# Здесь надо доработать смотреть на наличие авто в базе данных и если оно есть то показывать его. 
# С клавиатурой "Мой авто" "Расходы"
# Если пользователь выберет "Моя машина" показать ему его авто и предложить "удалить" или "сменить"
# Если пользователь выберет "Расходы" то показать ему список расходов по авто и предложить добавить новый расход

@bot.message_handler(commands=['start'])
@bot.message_handler(state=CarStates.WaitingStart)
def send_welcome(message):
    # Удаляем состояние, если оно есть
    try:
        state = bot.get_state(message.from_user.id, message.chat.id)
        if state and state != State.DEFAULT_STATE:
            bot.delete_state(message.from_user.id, message.chat.id)
    except Exception as e:
        print(f"[WARNING] Не удалось удалить состояние: {e}")

    bot.set_state(message.from_user.id, CarStates.WaitingStart, message.chat.id)
    update_user_state(message.from_user.id, bot.get_state(message.from_user.id, message.chat.id))

    # Устанавливаем команды бота
    bot.set_my_commands([
        types.BotCommand("/start", "Разбудить бота"),
    ])

    user_id = message.from_user.id
    # Проверяем, есть ли пользователь в базе данных
    result = get_user(user_id)
    print(f"[DEBUG] Результат поиска авто: {result}")

    if result:
       text = (
            "И снова привет! Вы уже выбрали автомобиль?\n"
       )
    else:
         text = (
             "Привет! Это CartratBot – бот для учёта расходов на автомобиль.\n"
             "Нажмите /car для выбора автомобиля или /help для справки."
         )
         state = bot.get_state(message.from_user.id, message.chat.id)
         add_user(user_id, state) # Добавляем пользователя в базу данных, если его там нет
  
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton(text="🏎️ Моя машина"))
    bot.send_message(message.chat.id, text, parse_mode='HTML', reply_markup=markup)

# Кнопка "Моя машина" в меню, чтобы лишний раз не писать пользователю.
# Невозможно сделать из за ограничений Tlegram API (Telegram API не принимает " " как допустимый text. Он считает это пустым сообщением, а они запрещены.)

# Если пользоватль входит во вкладку "Моя машина", то проверяем есть ли оно и отображаем (при этом добавля кнопки сравнения и кнопки назад)
# Или говорим ему выбрать авто посредствам вызова клавиши "🔍 Поиск марки"
@bot.message_handler(commands=['car'])
@bot.message_handler(func=lambda message: message.text == "🏎️ Моя машина")
@bot.message_handler(state=CarStates.WaitingForMycar)
def car(message):
    # Устанавливаем состояние вкладки "Моя машина"
    bot.set_state(message.from_user.id, CarStates.WaitingForMycar, message.chat.id)
    update_user_state(message.from_user.id, bot.get_state(message.from_user.id, message.chat.id))
    # Для отладки
    print(f"[DEBUG] Установлено состояние WaitingForMycar для {message.from_user.id}")
    # Смотрим есть ли авто у пользователя в базе данных
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    user_id = message.from_user.id
    user_details = get_user(user_id) # Смотрим id машины присвоен ли?
    print(f"[DEBUG] Результат поиска авто: {user_details}")
    car_id = user_details[1] # id авто
    car_nickname = user_details[2]
    if car_id != None:
        car_details = get_car(car_id)
        if car_details != None:
         brand_name, model_name, year_from, year_to, car_class = car_details
        class_description = get_class_description(car_class) # Получаем описание класса автомобиля
        # Формируем сообщение
        if car_nickname:
            title_line = f"🚗 Ваш автомобиль: <b>{brand_name} {model_name}</b> (\"{car_nickname}\")"
        else:
            title_line = f"🚗 Ваш автомобиль: <b>{brand_name} {model_name}</b>"

        text = (
            f"{title_line}\n"
            f"Годы выпуска: {year_from}–{year_to}\n"
            f"Класс: {car_class} ({class_description[0]})"
        )
        
        markup.add(types.KeyboardButton(text="⛽ Расходы"))
        markup.add(types.KeyboardButton(text="⚠️ Сменить авто"))
        markup.add(types.KeyboardButton(text="❌ Удалить авто"))

    else:
        text = "У вас нет выбранного автомобиля. Пожалуйста, выберите автомобиль через поиск."
        markup.add(types.KeyboardButton(text="🔍 Поиск марки"))

    bot.send_message(message.chat.id, text, parse_mode='HTML', reply_markup=markup)


############################################
# Работа над сменой авто

pending_reset = set()  # chat_id пользователей, подтвердивших сброс (пока пользователь не выберет новый авто он будет находиться в этом списке)
# При нажатии на сменить авто, удаляем прошлое и перемещаем в функию status_car_search
@bot.message_handler(func=lambda message: message.text == "⚠️ Сменить авто")
def change_car(message):
    # Устанавливаем состояние вкладки "Моя машина"
    bot.set_state(message.from_user.id, CarStates.WaitingChangingTheCar, message.chat.id)
    update_user_state(message.from_user.id, bot.get_state(message.from_user.id, message.chat.id))
    # Для отладки
    print(f"[DEBUG] Установлено состояние WaitingChangingTheCar для {message.from_user.id}")
    # Нужна проверка и предупреждение о смене автомобиля 
    warning_text = (
        "❗ У вас уже выбран автомобиль.\n"
        "Если вы смените авто, все связанные с ним расходы и история будут удалены.\n\n"
        "Вы уверены, что хотите продолжить?"
    )
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton(text="✅ Подтвердить смену авто"))
    markup.add(types.KeyboardButton(text="❌ Отмена"))
    bot.send_message(message.chat.id, warning_text, reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "✅ Подтвердить смену авто")
def confirm_change_car(message):
    # Возврат к предыдущему состоянию
    bot.set_state(message.from_user.id, CarStates.WaitingForMycar, message.chat.id)
    update_user_state(message.from_user.id, bot.get_state(message.from_user.id, message.chat.id))
    print(f"[DEBUG] Пользователь {message.from_user.id} вернулся к состоянию WaitingForMycar")
    # Удаляем авто из базы данных
    delete_user_car(message.from_user.id)
    markup = types.ReplyKeyboardRemove()
    bot.send_message(message.chat.id, "Данные прошлой машины были удалены 🫡", reply_markup=markup)
    pending_reset.add(message.from_user.id) # Добавляем id пользователья в список подтверждённых на сброс (моего авто)
    # Удаляем состояние
    bot.delete_state(message.from_user.id, message.chat.id)
    return status_car_search(message)

@bot.message_handler(func=lambda message: message.text == "❌ Отмена")
def cancel_change_car(message):
    # Возврат к предыдущему состоянию
    bot.set_state(message.from_user.id, CarStates.WaitingForMycar, message.chat.id)
    update_user_state(message.from_user.id, bot.get_state(message.from_user.id, message.chat.id))
    print(f"[DEBUG] Пользователь {message.from_user.id} вернулся к состоянию WaitingForMycar")
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton(text="🏎️ Моя машина"))
    bot.send_message(message.chat.id, "Изменения отклонены 🎉", reply_markup=markup)
    # Удаляем состояние
    bot.delete_state(message.from_user.id, message.chat.id)
    return 

############################################
# Работа над удалением авто

# При удалении авто просто удаляем и перемещаем НОВУЮ ФУНКИЮ КОТОРАЯ БУДЕТ ВЫЫОДИТЬ ТОЛЬКО КНОПКУ МОЯ МАШИНА БЕЗ НАДПИСЕЙ 
@bot.message_handler(func=lambda message: message.text == "❌ Удалить авто")
def delete_a_car(message):
        # Устанавливаем состояние вкладки "Моя машина"
    bot.set_state(message.from_user.id, CarStates.WaitingDeleteACar, message.chat.id)
    update_user_state(message.from_user.id, bot.get_state(message.from_user.id, message.chat.id))
    # Для отладки
    print(f"[DEBUG] Установлено состояние WaitingChangingTheCar для {message.from_user.id}")
    # Нужна проверка и предупреждение о смене автомобиля 
    warning_text = (
        "❗ У вас уже выбран автомобиль.\n"
        "Если вы смените или удалите авто, все связанные с ним расходы и история будут удалены.\n\n"
        "Вы уверены, что хотите продолжить?"
    )
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton(text="✅ Подтвердить удаление"))
    markup.add(types.KeyboardButton(text="❌ Отмена"))
    bot.send_message(message.chat.id, warning_text, reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "✅ Подтвердить удаление")
def confirm_change_car(message):
    # Возврат к предыдущему состоянию
    bot.set_state(message.from_user.id, CarStates.WaitingForMycar, message.chat.id)
    update_user_state(message.from_user.id, bot.get_state(message.from_user.id, message.chat.id))
    print(f"[DEBUG] Пользователь {message.from_user.id} вернулся к состоянию WaitingForMycar")
    # Удаляем авто из базы данных
    delete_user_car(message.from_user.id)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton(text="🏎️ Моя машина"))
    bot.send_message(message.chat.id, "Данные прошлой машины были удалены 🫡", reply_markup=markup)
    # Удаляем состояние
    bot.delete_state(message.from_user.id, message.chat.id)
    return

############################################
# Работа над добавлением авто


@bot.message_handler(func=lambda message: message.text == "🔍 Поиск марки")
def status_car_search(message):
    # Устанавливаем состояние вкладки "Поиска марки"
    bot.set_state(message.from_user.id, CarStates.WaitingForBrandSearch, message.chat.id)
    update_user_state(message.from_user.id, bot.get_state(message.from_user.id, message.chat.id))
    # Для отладки
    print(f"[DEBUG] Установлено состояние WaitingForBrandSearch для {message.from_user.id}")
    # Смотрим есть ли авто у пользователя в базе данных, если есть предлагаем сменить и откатывает в состояние "Моя машина"
    user_details = get_user(message.from_user.id) # Смотрим id машины есть ли?
    model_name = user_details[1]
    if model_name != None and message.from_user.id not in pending_reset:
        bot.send_message(message.chat.id,
                     "У вас уже выбран автомобиль. Чтобы сменить его, нажмите кнопку '⚠️ Сменить авто' в меню.")
        return car(message)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton(text="🔙 Назад"))
    msg = bot.send_message(message.chat.id, "Введите название марки или первые буквы:", reply_markup=markup)
    # Передаём управление функции поиска марки
    bot.register_next_step_handler(msg, process_brand_search)
def process_brand_search(message):

    if message.text == "🔙 Назад":
        # Возврат к предыдущему состоянию
        bot.set_state(message.from_user.id, CarStates.WaitingForMycar, message.chat.id)
        update_user_state(message.from_user.id, bot.get_state(message.from_user.id, message.chat.id))
        print(f"[DEBUG] Пользователь {message.from_user.id} вернулся к состоянию WaitingForMycar")
        update_user_state(message.from_user.id, bot.get_state(message.from_user.id, message.chat.id))
        return car(message)
    
    search_text = message.text.lower()
    all_brands = get_all_brands()
    matching_brands = [brand for brand in all_brands if brand.lower().startswith(search_text)] # Поиск совпадений по первой букве и вывод только нужных кнопок

    if matching_brands:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        brand_buttons = [types.KeyboardButton(text=brand) for brand in matching_brands]
        markup.add(*brand_buttons)
        markup.add(types.KeyboardButton(text="🔙 Назад"))
        
        msg = bot.send_message(message.chat.id, f"Найдено {len(matching_brands)} марок. Выберите одну:", reply_markup=markup)
        bot.register_next_step_handler(msg, process_brand_selection)

    else:
        markup = types.ReplyKeyboardRemove()
        bot.send_message(message.chat.id, "Марки не найдены.", reply_markup=markup)
        return car(message)
# Словарь для временного хранения выбора бренда
user_car_selection = {}
user_selected_brand = {}
def process_brand_selection(message):

    if message.text == "🔙 Назад":
        # Возврат к предыдущему состоянию
        bot.set_state(message.from_user.id, CarStates.WaitingForMycar, message.chat.id)
        update_user_state(message.from_user.id, bot.get_state(message.from_user.id, message.chat.id))
        print(f"[DEBUG] Пользователь {message.from_user.id} вернулся к состоянию WaitingForMycar")
        return car(message)

    brand = message.text.strip()
    user_selected_brand[message.chat.id] = brand
    models = get_models_by_brand(brand)

    if models:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        for model in models:
            markup.add(types.KeyboardButton(text=model))
        markup.add(types.KeyboardButton(text="🔙 Назад"))
        msg = bot.send_message(message.chat.id, f"Выберите модель для марки {brand}:", reply_markup=markup)
        bot.register_next_step_handler(msg, process_model_selection)
    else:
        bot.send_message(message.chat.id, f"Для марки {brand} не найдено моделей.")
        return car(message)

def process_model_selection(message):

    if message.text == "🔙 Назад":
        # Возврат к предыдущему состоянию
        bot.set_state(message.from_user.id, CarStates.WaitingForMycar, message.chat.id)
        update_user_state(message.from_user.id, bot.get_state(message.from_user.id, message.chat.id))
        print(f"[DEBUG] Пользователь {message.from_user.id} вернулся к состоянию WaitingForMycar")
        return car(message)

    user_id = message.from_user.id
    brand = user_selected_brand[user_id]
    model = message.text.strip()
    
    details = get_model_details(brand, model)
    if details:
        car_id = details[0]
        user_car_selection[user_id] = (car_id, brand, model)
        # Сохраняем выбор в базу данных
        #update_user_car(user_id, car_id)

        #удаляем id пользователья из списка подтверждённых на сброс (моего авто)
        if user_id in pending_reset:
            pending_reset.remove(message.chat.id)

        #return car(message)
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton(text="Пропустить"))
        msg = bot.send_message(message.chat.id, f"Введите кличку для машины или нажмите 'Пропустить':", reply_markup=markup)
        bot.register_next_step_handler(msg, choices_car_name)
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton(text="🏎️ Моя машина"))
        bot.send_message(message.chat.id, "Модель не найдена. Попробуйте ещё раз.", reply_markup=markup)

def choices_car_name(message):
    user_id = message.from_user.id
    car_id = user_car_selection[message.from_user.id][0]
    if message.text == "Пропустить":
        # Возврат к предыдущему состоянию
        update_user_car(user_id, car_id)
        bot.set_state(message.from_user.id, CarStates.WaitingForMycar, message.chat.id)
        update_user_state(message.from_user.id, bot.get_state(message.from_user.id, message.chat.id))
        print(f"[DEBUG] Пользователь {message.from_user.id} вернулся к состоянию WaitingForMycar")
        return car(message)

    # Сохраняем выбор в базу данных с кличкой
    update_user_car(user_id, car_id, message.text.strip())
    return car(message)

############################################
# Работа над расходами авто

@bot.message_handler(func=lambda msg: msg.text == "⛽ Расходы")
def handle_expense_menu(message):
    bot.set_state(message.from_user.id, CarStates.WaitingForExpenses, message.chat.id)
    update_user_state(message.from_user.id, bot.get_state(message.from_user.id, message.chat.id))
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("➕ Заправка", "➕ Прочий расход", "📈 История", "🔙 Назад")
    bot.send_message(message.chat.id, "Выберите действие:", reply_markup=markup)

@bot.message_handler(func=lambda msg: msg.text == "🔙 Назад")
def handle_back_to_mycar(message):
    # Возврат к предыдущему состоянию
    bot.set_state(message.from_user.id, CarStates.WaitingForMycar, message.chat.id)
    update_user_state(message.from_user.id, bot.get_state(message.from_user.id, message.chat.id))
    print(f"[DEBUG] Пользователь {message.from_user.id} вернулся к состоянию WaitingForMycar")
    return car(message)

############################################
# Работа над расходами авто (Заправка)

@bot.message_handler(func=lambda msg: msg.text == "➕ Заправка")
def start_refuel(message):
    fuels = get_all_fuel_types()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(*fuels)
    markup.add("🔙 Назад")

    msg = bot.send_message(message.chat.id, "Выберите тип топлива:", reply_markup=markup)
    bot.set_state(message.from_user.id, CarStates.ChoosingFuelType, message.chat.id)
    update_user_state(message.from_user.id, bot.get_state(message.from_user.id, message.chat.id))
    bot.register_next_step_handler(msg, process_fuel_type_selection)

def process_fuel_type_selection(message):
    if message.text == "🔙 Назад":
        bot.delete_state(message.from_user.id, message.chat.id)
        return handle_expense_menu(message)

    fuel_type_id = get_fuel_type_id(message.text)
    if not fuel_type_id:
        bot.send_message(message.chat.id, "❌ Тип топлива не найден. Попробуйте снова.")
        return start_refuel(message)

    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['fuel_type_id'] = fuel_type_id

    bot.set_state(message.from_user.id, CarStates.EnteringLiters, message.chat.id)
    update_user_state(message.from_user.id, bot.get_state(message.from_user.id, message.chat.id))
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🔙 Назад")
    msg = bot.send_message(message.chat.id, "Сколько литров вы заправили?", reply_markup=markup)
    bot.register_next_step_handler(msg, process_liters_input)

def process_liters_input(message):
    if message.text == "🔙 Назад":
        return start_refuel(message)

    try:
        liters = float(message.text.strip())
        if liters <= 0:
            raise ValueError("Литры должны быть положительным числом.")

        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            data['liters'] = liters

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("📅 Сегодня", "✍ Ввести вручную", "🔙 Назад")

        bot.set_state(message.from_user.id, CarStates.EnteringDate, message.chat.id)
        update_user_state(message.from_user.id, bot.get_state(message.from_user.id, message.chat.id))
        msg = bot.send_message(message.chat.id, "Когда была заправка?", reply_markup=markup)
        bot.register_next_step_handler(msg, process_date_input)

    except ValueError:
        bot.send_message(message.chat.id, "❌ Введите число литров, например: 42.5")

def process_date_input(message):
    if message.text == "🔙 Назад":
        return process_fuel_type_selection(message)

    from datetime import datetime, date

    if message.text == "📅 Сегодня":
        refuel_date = date.today().isoformat()
    elif message.text == "✍ Ввести вручную":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("🔙 Назад")
        msg = bot.send_message(message.chat.id, "Введите дату в формате ГГГГ-ММ-ДД:", reply_markup=markup)
        bot.register_next_step_handler(msg, process_manual_date_input)
        return
    else:
        try:
            datetime.strptime(message.text.strip(), "%Y-%m-%d")
            refuel_date = message.text.strip()
        except Exception:
            bot.send_message(message.chat.id, "❌ Неверный формат. Введите дату: 2025-04-30")
            return

    return finalize_refuel(message, refuel_date)

def process_manual_date_input(message):
    if message.text == "🔙 Назад":
        return process_liters_input(message)

    from datetime import datetime
    try:
        refuel_date = message.text.strip()
        datetime.strptime(refuel_date, "%Y-%m-%d")
        return finalize_refuel(message, refuel_date)
    except Exception:
        bot.send_message(message.chat.id, "❌ Неверный формат. Введите как 2025-04-30")

def finalize_refuel(message, refuel_date):
    try:
        user_id = message.from_user.id
        with bot.retrieve_data(user_id, message.chat.id) as data:
            fuel_type_id = data['fuel_type_id']
            liters = data['liters']

        price_per_liter = get_price_for_fuel(fuel_type_id, refuel_date)
        if price_per_liter is None:
            bot.send_message(message.chat.id, "❌ Нет цены на топливо для этой даты.")
            return handle_expense_menu(message)

        total = round(liters * price_per_liter, 2)
        fuel_name = get_fuel_name_by_id(fuel_type_id)
        add_refuel(user_id, fuel_type_id, refuel_date, liters, total)
        bot.send_message(
            message.chat.id,
            f"✅ Заправка сохранена:\n"
            f"Топливо ID: {fuel_name}\n"
            f"Объём: {liters} л\n"
            f"Цена: {price_per_liter}₽/л\n"
            f"Итого: {total}₽\n"
            f"Дата: {refuel_date}"
        )
        bot.delete_state(user_id, message.chat.id)
        return handle_expense_menu(message)

    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка при сохранении: {e}")
        bot.delete_state(user_id, message.chat.id)
        return handle_expense_menu(message)

############################################
# Работа над расходами авто (Прочий расход)

@bot.message_handler(func=lambda msg: msg.text == "➕ Прочий расход")
def start_other_expense(message):
    types_list = get_other_expense_types()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for t in types_list:
        markup.add(t)
    markup.add("🔙 Назад")

    msg = bot.send_message(message.chat.id, "Выберите тип расхода:", reply_markup=markup)
    bot.set_state(message.from_user.id, CarStates.ChoosingOtherExpenseType, message.chat.id)
    update_user_state(message.from_user.id, bot.get_state(message.from_user.id, message.chat.id))
    bot.register_next_step_handler(msg, process_other_expense_type_selection)


def process_other_expense_type_selection(message):
    if message.text == "🔙 Назад":
        bot.delete_state(message.from_user.id, message.chat.id)
        return handle_expense_menu(message)

    type_id = get_other_expense_type_id(message.text)
    if not type_id:
        bot.send_message(message.chat.id, "❌ Тип расхода не найден. Попробуйте снова.")
        return start_other_expense(message)

    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['other_expense_type_id'] = type_id

    bot.set_state(message.from_user.id, CarStates.EnteringOtherExpenseSum, message.chat.id)
    update_user_state(message.from_user.id, bot.get_state(message.from_user.id, message.chat.id))
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🔙 Назад")
    msg = bot.send_message(message.chat.id, "Введите сумму расхода:", reply_markup=markup)
    bot.register_next_step_handler(msg, process_other_expense_sum)


def process_other_expense_sum(message):
    if message.text == "🔙 Назад":
        return start_other_expense(message)

    try:
        amount = float(message.text.strip())
        if amount <= 0:
            raise ValueError

        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            data['amount'] = amount

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("📅 Сегодня", "✍ Ввести вручную", "🔙 Назад")
        bot.set_state(message.from_user.id, CarStates.EnteringOtherExpenseDate, message.chat.id)
        update_user_state(message.from_user.id, bot.get_state(message.from_user.id, message.chat.id))
        msg = bot.send_message(message.chat.id, "Когда был расход?", reply_markup=markup)
        bot.register_next_step_handler(msg, process_other_expense_date)

    except ValueError:
        bot.send_message(message.chat.id, "❌ Введите положительное число, например: 350")


def process_other_expense_date(message):
    if message.text == "🔙 Назад":
        return process_other_expense_sum(message)

    from datetime import datetime, date
    if message.text == "📅 Сегодня":
        expense_date = date.today().isoformat()
    elif message.text == "✍ Ввести вручную":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("🔙 Назад")
        msg = bot.send_message(message.chat.id, "Введите дату в формате ГГГГ-ММ-ДД:", reply_markup=markup)
        bot.register_next_step_handler(msg, process_manual_other_expense_date)
        return
    else:
        try:
            datetime.strptime(message.text.strip(), "%Y-%m-%d")
            expense_date = message.text.strip()
        except:
            bot.send_message(message.chat.id, "❌ Неверный формат. Введите дату: 2025-04-30")
            return

    ask_other_expense_comment(message, expense_date)


def process_manual_other_expense_date(message):
    if message.text == "🔙 Назад":
        return process_other_expense_sum(message)

    from datetime import datetime
    try:
        expense_date = message.text.strip()
        datetime.strptime(expense_date, "%Y-%m-%d")
        return ask_other_expense_comment(message, expense_date)
    except:
        bot.send_message(message.chat.id, "❌ Неверный формат. Введите как 2025-04-30")


def ask_other_expense_comment(message, expense_date):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['expense_date'] = expense_date

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Без комментария", "🔙 Назад")
    bot.set_state(message.from_user.id, CarStates.EnteringOtherExpenseComment, message.chat.id)
    update_user_state(message.from_user.id, bot.get_state(message.from_user.id, message.chat.id))
    msg = bot.send_message(message.chat.id, "Введите комментарий к расходу:", reply_markup=markup)
    bot.register_next_step_handler(msg, finalize_other_expense)


def finalize_other_expense(message):
    if message.text == "🔙 Назад":
        return process_other_expense_sum(message)

    comment = message.text.strip() if message.text != "Без комментария" else ""

    try:
        user_id = message.from_user.id
        with bot.retrieve_data(user_id, message.chat.id) as data:
            type_id = data['other_expense_type_id']
            amount = data['amount']
            expense_date = data['expense_date']

        add_other_expense(user_id, type_id, expense_date, amount, comment)
        type_name = get_other_expense_type_name_by_id(type_id)  # Функция для получения имени по id

        bot.send_message(
            message.chat.id,
            f"✅ Расход сохранён:\n"
            f"Тип: {type_name}\n"
            f"Сумма: {amount}₽\n"
            f"Дата: {expense_date}\n"
            f"Комментарий: {comment or '—'}"
        )
        bot.delete_state(user_id, message.chat.id)
        return handle_expense_menu(message)

    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка при сохранении: {e}")
        bot.delete_state(user_id, message.chat.id)
        return handle_expense_menu(message)

############################################
# Работа над расходами авто (История расходов)

@bot.message_handler(func=lambda msg: msg.text == "📈 История")
def show_history(message):
    user_id = message.from_user.id
    rows = get_full_expense_history(user_id)

    if not rows:
        bot.send_message(message.chat.id, "🚫 У вас пока нет записей о расходах.")
        return

    total_sum = 0.0
    lines = ["📊 История расходов:\n"]

    for row in rows:
        expense_type, date, fuel_name, liters, total, other_name, amount, comment = row

        if expense_type == 'refuel':
            lines.append(f"⛽ {date}: {fuel_name} — {liters} л, {total}₽")
            total_sum += float(total)
        elif expense_type == 'other':
            entry = f"📌 {date}: {other_name} — {amount}₽"
            if comment:
                entry += f" ({comment})"
            lines.append(entry)
            total_sum += float(amount or 0)
        else:
            lines.append(f"❓ {date}: неизвестный расход")

    lines.append(f"\n💰 Всего потрачено: {round(total_sum, 2)}₽")
    text = "\n".join(lines)
    bot.send_message(message.chat.id, text)


bot.infinity_polling()
