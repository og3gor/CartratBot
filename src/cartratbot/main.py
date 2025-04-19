print("Start CartratBot")

from config import BOT_TOKEN

from db import get_all_brands

import telebot
from telebot import types

bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
        bot.reply_to(message, "Hi, this is a bot for calculating the money spent on a car, as if it were fuel, fines and insurance")

# @bot.message_handler(func=lambda message: True)
# def echo_all(message):
# 	bot.reply_to(message, message.text)

@bot.message_handler(commands=["car"])
def car(message):
    # Показываем первые 10 самых популярных брендов + кнопку поиска
    brands = get_all_brands()
    popular_brands = brands[:10]  # Можно реализовать логику популярных брендов
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    brand_buttons = [types.KeyboardButton(text=brand) for brand in popular_brands]
    markup.add(*brand_buttons)
    markup.add(types.KeyboardButton(text="🔍 Поиск марки"))
    
    bot.send_message(message.chat.id, "Выберите марку автомобиля или воспользуйтесь поиском:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "🔍 Поиск марки")
def search_brand(message):
    msg = bot.send_message(message.chat.id, "Введите название марки или первые буквы:")
    bot.register_next_step_handler(msg, process_brand_search)

def process_brand_search(message):
    search_text = message.text.lower()
    all_brands = get_all_brands()
    
    # Ищем бренды, начинающиеся с введенного текста
    matching_brands = [brand for brand in all_brands if brand.lower().startswith(search_text)]
    
    if matching_brands:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        brand_buttons = [types.KeyboardButton(text=brand) for brand in matching_brands[:10]]
        markup.add(*brand_buttons)
        markup.add(types.KeyboardButton(text="🔍 Поиск марки"), types.KeyboardButton(text="◀️ Назад к популярным"))
        
        bot.send_message(message.chat.id, f"Найдено {len(matching_brands)} марок:", reply_markup=markup)
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton(text="🔍 Поиск марки"), types.KeyboardButton(text="◀️ Назад к популярным"))
        
        bot.send_message(message.chat.id, "Марки не найдены. Попробуйте другой запрос:", reply_markup=markup)
bot.infinity_polling()


