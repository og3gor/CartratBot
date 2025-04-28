print("Start CartratBot")

from config import BOT_TOKEN

from db import get_all_brands, get_models_by_brand, get_model_details, get_connection, get_user, add_user, update_user_state
from db import update_user_car, delete_user_car, get_car, get_class_description

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
    #brand_name = car_details[0]
    if car_id != None:
        car_details = get_car(car_id)
        if car_details != None:
         brand_name, model_name, year_from, year_to, car_class = car_details
        class_description = get_class_description(car_class) # Получаем описание класса автомобиля
        # Формируем сообщение
        text = (
           f"🚗 Ваш автомобиль: <b>{brand_name} {model_name}</b>\n"
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
    pending_reset.add(user_id) # Добавляем id пользователья в список подтверждённых на сброс (моего авто)
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
    matching_brands = [brand for brand in all_brands if brand.lower().startswith(search_text)]

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

        # Сохраняем выбор в базу данных
        update_user_car(user_id, car_id)

        #удаляем id пользователья из списка подтверждённых на сброс (моего авто)
        if user_id in pending_reset:
            pending_reset.remove(user_id)

        return car(message)
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton(text="🏎️ Моя машина"))
        bot.send_message(message.chat.id, "Модель не найдена. Попробуйте ещё раз.", reply_markup=markup)

bot.infinity_polling()


