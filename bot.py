import asyncio
import logging
import re
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import (
    Message, CallbackQuery, 
    InlineKeyboardMarkup, InlineKeyboardButton, 
    InputFile
)
from aiogram.filters import CommandStart, Command
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# ================= НАСТРОЙКИ =================
BOT_TOKEN = "8860296167:AAGFjtPRi5uMUNr6VV1yDVsEdtxS37fevEY"
ADMIN_CHAT_ID = -1004492034556

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

# ================= ПУТЬ К ФОТО =================
PHOTO_PATH = "bot_files/"

CATEGORY_IMAGES = {
    "hot": PHOTO_PATH + "hot_food.jpg",
    "fry": PHOTO_PATH + "fried_food.jpg",
    "grill": PHOTO_PATH + "grill.jpg",
    "drinks": PHOTO_PATH + "drinks.jpg"
}

BANNERS = {
    "menu": PHOTO_PATH + "menu_banner.jpg",
    "menu_categories": PHOTO_PATH + "menu_categories_banner.jpg",
    "popular": PHOTO_PATH + "popular_banner.jpg",
    "chicken": PHOTO_PATH + "chicken_banner.jpg",
    "banquet": PHOTO_PATH + "banquet_banner.jpg"
}

# ================= УПРАВЛЕНИЕ СООБЩЕНИЯМИ =================
user_messages = {}

async def clear_history(user_id, keep_message_id=None):
    if user_id in user_messages:
        for msg_id in user_messages[user_id]:
            if keep_message_id and msg_id == keep_message_id:
                continue
            try:
                await bot.delete_message(user_id, msg_id)
            except:
                pass
        user_messages[user_id] = []

async def add_user_message(message: Message):
    user_id = message.from_user.id
    if user_id not in user_messages:
        user_messages[user_id] = []
    user_messages[user_id].append(message.message_id)
    if len(user_messages[user_id]) > 10:
        user_messages[user_id] = user_messages[user_id][-10:]

async def delete_all_user_messages(user_id):
    if user_id in user_messages:
        for msg_id in user_messages[user_id]:
            try:
                await bot.delete_message(user_id, msg_id)
            except:
                pass
        user_messages[user_id] = []

# ================= ДАННЫЕ МЕНЮ =================
MENU_ITEMS = {}
CURRENT_ID = 1

def register_items():
    global CURRENT_ID
    for cat_id, cat in MENU_ITEMS_CATEGORIES.items():
        for name, price in cat['items'].items():
            MENU_ITEMS[CURRENT_ID] = {'name': name, 'price': price, 'category': cat_id}
            CURRENT_ID += 1

MENU_ITEMS_CATEGORIES = {
    "hot": {
        "name": "🌯 Горячие блюда",
        "emoji": "🌯",
        "items": {
            "Шаурма классическая": 350,
            "Шаурма с сыром": 380,
            "Пита с курицей": 350,
            "Тако мексиканское": 350,
            "Буррито": 300,
            "Пицца 23 см (Пепперони)": 400,
            "Пицца 23 см (Маргарита)": 380,
            "Чикен бургер": 250
        }
    },
    "fry": {
        "name": "🍟 Фриптюрное меню",
        "emoji": "🍟",
        "items": {
            "Картофель фри (150гр)": 170,
            "Картофель фри (200гр)": 220,
            "Крылья (3шт)": 190,
            "Крылья (6шт)": 350,
            "Наггетсы (7шт)": 180,
            "Стрипсы (5шт)": 200,
            "Луковые кольца (10шт)": 170,
            "Сырные палочки (6шт)": 190
        }
    },
    "grill": {
        "name": "🔥 Курица Гриль",
        "emoji": "🔥",
        "items": {
            "Курица Гриль (целая, ~1.1 кг)": 1000,
            "Курица с картошкой и грибами (2+ кг)": 1200,
            "Свиные ребра (2+ кг)": 1300,
            "Куриное филе гриль (300гр)": 350,
            "Куриные бедра (4шт)": 400
        }
    },
    "drinks": {
        "name": "🥤 Коктейли",
        "emoji": "🥤",
        "items": {
            "Молочный коктейль (Шоколад)": 180,
            "Молочный коктейль (Ваниль)": 180,
            "Молочный коктейль (Клубника)": 180,
            "Молочный коктейль (Карамель)": 190,
            "Лимонад домашний": 150,
            "Морс ягодный": 120
        }
    }
}

register_items()

BANQUET_MENU = {
    "price_per_person": 1500,
    "min_persons": 5,
    "delivery": "Бесплатная",
    "items": [
        "Канапе (2 шт)",
        "Брускетты (2 шт)",
        "Куриное бедро (1 шт)",
        "Блинчик с рыбой (1 шт)",
        "Картошка (150 г)",
        "Шампиньоны (1 шт)"
    ]
}

# ================= СОСТОЯНИЯ =================
user_states = {}
carts = {}
banquet_orders = {}

# ================= ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =================

def get_cart_total(user_id):
    cart = carts.get(user_id, {})
    total = 0
    for item_id, data in cart.items():
        if item_id in ['address', 'phone']:
            continue
        if isinstance(data, list) and len(data) == 2:
            total += data[0] * data[1]
    return total

def format_cart(user_id):
    cart = carts.get(user_id, {})
    if not cart:
        return "🛒 Ваша корзина пуста!"
    
    text = "<b>🛒 Ваш заказ:</b>\n\n"
    total = 0
    
    for item_id, data in cart.items():
        if item_id in ['address', 'phone']:
            continue
        if isinstance(data, list) and len(data) == 2:
            price, qty = data
            item_info = MENU_ITEMS.get(item_id, {})
            item_name = item_info.get('name', 'Неизвестно')
            total += price * qty
            text += f"• <i>{qty} x {price}₽ = {price * qty}₽</i> — {item_name}\n"
    
    text += f"\n💰 <b>Итого: {total}₽</b>"
    
    if 'address' in cart:
        text += f"\n\n📍 Адрес доставки: {cart['address']}"
    if 'phone' in cart:
        text += f"\n📞 Телефон: {cart['phone']}"
    
    return text

def validate_phone(phone):
    phone = re.sub(r'[\s\-()]', '', phone)
    if re.match(r'^(\+7|8|7)?\d{10}$', phone):
        return True
    return False

def validate_address(address):
    return len(address.strip()) >= 5

# ================= ФУНКЦИИ КЛАВИАТУР =================
def get_main_keyboard():
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⭐ Популярное", callback_data="popular"),
                InlineKeyboardButton(text="📖 Наше меню", callback_data="menu")
            ],
            [
                InlineKeyboardButton(text="🥂 Фуршетное меню", callback_data="banquet"),
                InlineKeyboardButton(text="🐔 Забронировать курицу", callback_data="book_chicken")
            ],
            [
                InlineKeyboardButton(text="🕒 График работы", callback_data="schedule"),
                InlineKeyboardButton(text="📞 Контакты", callback_data="contacts")
            ],
            [
                InlineKeyboardButton(text="🛒 Моя корзина", callback_data="cart")
            ]
        ]
    )
    return kb

def get_cancel_keyboard():
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Отмена", callback_data="cancel")]
        ]
    )
    return kb

def get_cart_keyboard(user_id):
    cart = carts.get(user_id, {})
    kb = InlineKeyboardMarkup(inline_keyboard=[])

    for item_id, data in cart.items():
        if item_id in ['address', 'phone']:
            continue
        if isinstance(data, list) and len(data) == 2:
            price, qty = data
            item_info = MENU_ITEMS.get(item_id, {})
            item_name = item_info.get('name', 'Неизвестно')
            
            btn_name = item_name if len(item_name) <= 40 else item_name[:37] + "..."
            
            btn_minus = InlineKeyboardButton(text="➖", callback_data=f"dec_{item_id}")
            btn_center = InlineKeyboardButton(text=f"{btn_name}", callback_data="noop")
            btn_plus = InlineKeyboardButton(text="➕", callback_data=f"inc_{item_id}")
            
            kb.inline_keyboard.append([btn_minus, btn_center, btn_plus])
    
    kb.inline_keyboard.append([
        InlineKeyboardButton(text="✅ Оформить заказ", callback_data="checkout"),
        InlineKeyboardButton(text="🗑 Очистить", callback_data="clear")
    ])
    kb.inline_keyboard.append([
        InlineKeyboardButton(text="🔙 В меню", callback_data="menu"),
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="back")
    ])
    
    return kb

# ================= ФУНКЦИЯ ОТПРАВКИ С ФОТО =================
async def send_with_photo(chat_id, text, image_path, reply_markup=None):
    try:
        if image_path and os.path.exists(image_path):
            photo = InputFile(image_path)
            return await bot.send_photo(
                chat_id=chat_id,
                photo=photo,
                caption=text,
                reply_markup=reply_markup
            )
    except Exception as e:
        logger.error(f"Ошибка отправки фото: {e}")
    
    return await bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=reply_markup
    )

# ================= ОБРАБОТЧИКИ КОМАНД =================

@dp.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    
    await delete_all_user_messages(user_id)
    
    if user_id not in carts:
        carts[user_id] = {}
    if user_id not in user_states:
        user_states[user_id] = 'main'
    
    await add_user_message(message)
    
    sent_msg = await send_with_photo(
        chat_id=user_id,
        text=(
            "🔥 <b>ГРИЛЬ БАР</b> 🔥\n\n"
            "🌟 <i>Добро пожаловать!</i>\n\n"
            "🍗 <b>Свежая курица на углях</b>\n"
            "🥙 <b>Вкусные шаурмы</b>\n"
            "🍕 <b>Горячая пицца</b>\n\n"
            "✨ <i>Более 50 блюд!</i>\n"
            "⚡ <i>Готовим быстро</i>\n\n"
            "👇 Выберите пункт меню:"
        ),
        image_path=BANNERS["menu"],
        reply_markup=get_main_keyboard()
    )
    await add_user_message(sent_msg)

@dp.message(Command("help"))
async def cmd_help(message: Message):
    await cmd_start(message)

# ================= ОБРАБОТКА CALLBACK'ОВ =================

@dp.callback_query(F.data == "back")
async def back_main(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_states[user_id] = 'main'
    
    await delete_all_user_messages(user_id)
    
    sent_msg = await send_with_photo(
        chat_id=user_id,
        text="🏠 <b>Главное меню</b>",
        image_path=BANNERS["menu"],
        reply_markup=get_main_keyboard()
    )
    await add_user_message(sent_msg)
    
    try:
        await callback.message.delete()
    except:
        pass

@dp.callback_query(F.data == "cancel")
async def cancel_input(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    if user_id in banquet_orders:
        del banquet_orders[user_id]
    
    if 'address' in carts.get(user_id, {}):
        del carts[user_id]['address']
    if 'phone' in carts.get(user_id, {}):
        del carts[user_id]['phone']
    
    user_states[user_id] = 'main'
    
    await delete_all_user_messages(user_id)
    
    sent_msg = await send_with_photo(
        chat_id=user_id,
        text="❌ Ввод отменен.\n\n🏠 <b>Главное меню</b>",
        image_path=BANNERS["menu"],
        reply_markup=get_main_keyboard()
    )
    await add_user_message(sent_msg)
    
    try:
        await callback.message.delete()
    except:
        pass

@dp.callback_query(F.data == "menu")
async def show_menu(callback: CallbackQuery):
    user_states[callback.from_user.id] = 'menu'
    
    await delete_all_user_messages(callback.from_user.id)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for cat_id, cat in MENU_ITEMS_CATEGORIES.items():
        kb.inline_keyboard.append([
            InlineKeyboardButton(text=f"{cat['emoji']} {cat['name']}", callback_data=f"cat_{cat_id}")
        ])
    
    kb.inline_keyboard.append([
        InlineKeyboardButton(text="🛒 Моя корзина", callback_data="cart"),
        InlineKeyboardButton(text="🔙 Назад", callback_data="back")
    ])
    
    sent_msg = await send_with_photo(
        chat_id=callback.from_user.id,
        text="📖 <b>Наше меню</b>\n\nВыберите категорию:",
        image_path=BANNERS["menu_categories"],
        reply_markup=kb
    )
    await add_user_message(sent_msg)
    
    try:
        await callback.message.delete()
    except:
        pass

@dp.callback_query(F.data.startswith("cat_"))
async def show_category(callback: CallbackQuery):
    cat_id = callback.data.split('_')[1]
    cat = MENU_ITEMS_CATEGORIES.get(cat_id)
    
    if not cat:
        await callback.answer("⚠️ Категория не найдена!")
        return
    
    user_states[callback.from_user.id] = f'category_{cat_id}'
    
    await delete_all_user_messages(callback.from_user.id)
    
    items_text = []
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    
    for item_id, info in MENU_ITEMS.items():
        if info['category'] == cat_id:
            items_text.append(f"• <b>{info['name']}</b> — <i>{info['price']}₽</i>")
            kb.inline_keyboard.append([
                InlineKeyboardButton(text=f"➕ {info['name']} ({info['price']}₽)", callback_data=f"add_{item_id}")
            ])
    
    kb.inline_keyboard.append([
        InlineKeyboardButton(text="🔙 Назад к категориям", callback_data="menu"),
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="back")
    ])
    
    caption = f"{cat['emoji']} <b>{cat['name']}</b>\n\n" + "\n".join(items_text)
    
    photo_path = CATEGORY_IMAGES.get(cat_id)
    sent_msg = await send_with_photo(
        chat_id=callback.from_user.id,
        text=caption,
        image_path=photo_path,
        reply_markup=kb
    )
    await add_user_message(sent_msg)
    
    try:
        await callback.message.delete()
    except:
        pass

@dp.callback_query(F.data == "popular")
async def show_popular(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_states[user_id] = 'popular'
    
    await delete_all_user_messages(user_id)
    
    popular_items = ["Шаурма классическая", "Пицца 23 см (Пепперони)", "Курица Гриль", "Картофель фри (200гр)", "Молочный коктейль (Шоколад)"]
    
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for item_name in popular_items:
        for item_id, info in MENU_ITEMS.items():
            if info['name'] == item_name:
                kb.inline_keyboard.append([
                    InlineKeyboardButton(text=f"⭐ {info['name']} ({info['price']}₽)", callback_data=f"add_{item_id}")
                ])
    
    kb.inline_keyboard.append([
        InlineKeyboardButton(text="🔙 Назад", callback_data="back"),
        InlineKeyboardButton(text="📖 В меню", callback_data="menu")
    ])
    
    sent_msg = await send_with_photo(
        chat_id=user_id,
        text="⭐ <b>Популярные блюда</b>\n\n🔥 <i>Выбор наших гостей!</i>",
        image_path=BANNERS["popular"],
        reply_markup=kb
    )
    await add_user_message(sent_msg)
    
    try:
        await callback.message.delete()
    except:
        pass

@dp.callback_query(F.data.startswith("add_"))
async def add_to_cart(callback: CallbackQuery):
    user_id = callback.from_user.id
    item_id = int(callback.data.split('_')[1])
    
    item_info = MENU_ITEMS.get(item_id)
    if not item_info:
        await callback.answer("⚠️ Товар не найден!", show_alert=True)
        return
    
    price = item_info['price']
    item_name = item_info['name']
    
    if user_id not in carts:
        carts[user_id] = {}
    
    if item_id in carts[user_id]:
        carts[user_id][item_id][1] += 1
        action = "обновлено"
    else:
        carts[user_id][item_id] = [price, 1]
        action = "добавлен"
    
    total_items = sum(qty for item_id, (price, qty) in carts[user_id].items() if isinstance(carts[user_id][item_id], list))
    total_sum = get_cart_total(user_id)
    
    await callback.answer(f"✅ {item_name} {action}!\n\n🛒 Товаров: {total_items} | 💰 Сумма: {total_sum}₽")

@dp.callback_query(F.data == "cart")
async def show_cart(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_states[user_id] = 'cart'
    
    await delete_all_user_messages(user_id)
    
    cart = carts.get(user_id, {})
    has_items = any(isinstance(data, list) for data in cart.values())
    
    if not has_items:
        sent_msg = await send_with_photo(
            chat_id=user_id,
            text="🛒 <b>Корзина пуста</b>\n\nДобавьте что-нибудь из меню!",
            image_path=BANNERS["menu"],
            reply_markup=get_main_keyboard()
        )
        await add_user_message(sent_msg)
    else:
        text = format_cart(user_id)
        sent_msg = await bot.send_message(
            chat_id=user_id,
            text=text,
            reply_markup=get_cart_keyboard(user_id)
        )
        await add_user_message(sent_msg)
    
    try:
        await callback.message.delete()
    except:
        pass

@dp.callback_query(F.data.startswith("inc_") or F.data.startswith("dec_"))
async def change_quantity(callback: CallbackQuery):
    user_id = callback.from_user.id
    action, item_id_str = callback.data.split('_', 1)
    item_id = int(item_id_str)
    
    if user_id not in carts or item_id not in carts[user_id]:
        await callback.answer("⚠️ Товар не найден!", show_alert=True)
        return
    
    price, qty = carts[user_id][item_id]
    
    if action == 'inc':
        carts[user_id][item_id][1] += 1
    elif action == 'dec':
        if qty > 1:
            carts[user_id][item_id][1] -= 1
        else:
            del carts[user_id][item_id]
    
    has_items = any(isinstance(data, list) for data in carts[user_id].values())
    
    if not has_items:
        try:
            await callback.message.edit_text(
                "🛒 <b>Корзина пуста</b>",
                reply_markup=get_main_keyboard()
            )
        except:
            sent_msg = await callback.message.answer(
                "🛒 <b>Корзина пуста</b>",
                reply_markup=get_main_keyboard()
            )
            await add_user_message(sent_msg)
            try:
                await callback.message.delete()
            except:
                pass
    else:
        text = format_cart(user_id)
        kb = get_cart_keyboard(user_id)
        
        try:
            await callback.message.edit_text(text, reply_markup=kb)
        except:
            sent_msg = await callback.message.answer(text, reply_markup=kb)
            await add_user_message(sent_msg)
            try:
                await callback.message.delete()
            except:
                pass

@dp.callback_query(F.data == "clear")
async def clear_cart(callback: CallbackQuery):
    user_id = callback.from_user.id
    carts[user_id] = {}
    user_states[user_id] = 'main'
    
    try:
        await callback.message.edit_text(
            "🗑 <b>Корзина очищена!</b>\n\n🏠 Главное меню",
            reply_markup=get_main_keyboard()
        )
    except:
        sent_msg = await callback.message.answer(
            "🗑 <b>Корзина очищена!</b>\n\n🏠 Главное меню",
            reply_markup=get_main_keyboard()
        )
        await add_user_message(sent_msg)
        try:
            await callback.message.delete()
        except:
            pass

@dp.callback_query(F.data == "checkout")
async def checkout(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_states[user_id] = 'checkout'
    
    await clear_history(user_id, keep_message_id=callback.message.message_id)
    
    cart = carts.get(user_id, {})
    has_items = any(isinstance(data, list) for data in cart.values())
    
    if not has_items:
        await callback.answer("⚠️ Корзина пуста!", show_alert=True)
        return
    
    total = get_cart_total(user_id)
    
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🏠 Доставка", callback_data="del"),
                InlineKeyboardButton(text="🏃 Самовывоз", callback_data="pick")
            ],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="cart")]
        ]
    )
    
    try:
        await callback.message.edit_text(
            f"<b>📋 Оформление заказа</b>\n\n"
            f"💰 <b>Сумма заказа: {total}₽</b>\n\n"
            f"Выберите способ получения:",
            reply_markup=kb
        )
    except:
        sent_msg = await callback.message.answer(
            f"<b>📋 Оформление заказа</b>\n\n"
            f"💰 <b>Сумма заказа: {total}₽</b>\n\n"
            f"Выберите способ получения:",
            reply_markup=kb
        )
        await add_user_message(sent_msg)
        try:
            await callback.message.delete()
        except:
            pass

@dp.callback_query(F.data == "pick")
async def pickup(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_states[user_id] = 'waiting_phone'
    
    try:
        await callback.message.edit_text(
            "🏃 <b>Самовывоз</b>\n\n"
            "📍 Адрес: 3-й квартал, 16, 305502, пос. Маршала Жукова, Курский район, Курская область\n\n"
            "📞 Пожалуйста, введите ваш номер телефона:",
            reply_markup=get_cancel_keyboard()
        )
    except:
        sent_msg = await callback.message.answer(
            "🏃 <b>Самовывоз</b>\n\n"
            "📍 Адрес: 3-й квартал, 16, 305502, пос. Маршала Жукова, Курский район, Курская область\n\n"
            "📞 Пожалуйста, введите ваш номер телефона:",
            reply_markup=get_cancel_keyboard()
        )
        await add_user_message(sent_msg)
        try:
            await callback.message.delete()
        except:
            pass

@dp.callback_query(F.data == "del")
async def delivery(callback: CallbackQuery):
    user_id = callback.from_user.id
    total = get_cart_total(user_id)
    
    if total < 1500:
        await callback.answer(
            f"⚠️ Минимальная сумма для доставки: 1500₽\nВаша сумма: {total}₽\n\nДобавьте товаров или выберите самовывоз!",
            show_alert=True
        )
        return
    
    user_states[user_id] = 'waiting_address'
    
    try:
        await callback.message.edit_text(
            "🏠 <b>Доставка</b>\n\n"
            "🚚 Доставка в течение 60-90 минут\n"
            "💰 Бесплатная доставка при заказе от 2000₽\n\n"
            "📍 Пожалуйста, введите ваш адрес:",
            reply_markup=get_cancel_keyboard()
        )
    except:
        sent_msg = await callback.message.answer(
            "🏠 <b>Доставка</b>\n\n"
            "🚚 Доставка в течение 60-90 минут\n"
            "💰 Бесплатная доставка при заказе от 2000₽\n\n"
            "📍 Пожалуйста, введите ваш адрес:",
            reply_markup=get_cancel_keyboard()
        )
        await add_user_message(sent_msg)
        try:
            await callback.message.delete()
        except:
            pass

# ================= ДОП. РАЗДЕЛЫ =================

@dp.callback_query(F.data == "banquet")
async def banquet_menu(callback: CallbackQuery):
    await delete_all_user_messages(callback.from_user.id)
    
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📋 Подробное описание", callback_data="show_banquet")],
            [InlineKeyboardButton(text="🎯 Заказать фуршет", callback_data="order_banquet")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
        ]
    )
    
    sent_msg = await send_with_photo(
        chat_id=callback.from_user.id,
        text=(
            f"🥂 <b>Фуршетное меню</b>\n\n"
            f"💰 <b>Цена:</b> {BANQUET_MENU['price_per_person']}₽/чел\n"
            f"👥 <b>Минимальный заказ:</b> {BANQUET_MENU['min_persons']} персон\n"
            f"🚚 <b>Доставка:</b> {BANQUET_MENU['delivery']}\n\nИдеально для корпоративов и праздников!"
        ),
        image_path=BANNERS["banquet"],
        reply_markup=kb
    )
    await add_user_message(sent_msg)
    
    try:
        await callback.message.delete()
    except:
        pass

@dp.callback_query(F.data == "show_banquet")
async def show_banquet_details(callback: CallbackQuery):
    items_text = "\n".join([f"• {item}" for item in BANQUET_MENU['items']])
    
    await delete_all_user_messages(callback.from_user.id)
    
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎯 Заказать фуршет", callback_data="order_banquet")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="banquet")]
        ]
    )
    
    sent_msg = await send_with_photo(
        chat_id=callback.from_user.id,
        text=(
            f"🥂 <b>Состав фуршета (на 1 персону):</b>\n\n{items_text}\n\n"
            f"💰 <b>Итого: {BANQUET_MENU['price_per_person']}₽/чел</b>\n"
            f"👥 Минимальный заказ: {BANQUET_MENU['min_persons']} персон"
        ),
        image_path=BANNERS["banquet"],
        reply_markup=kb
    )
    await add_user_message(sent_msg)
    
    try:
        await callback.message.delete()
    except:
        pass

@dp.callback_query(F.data == "order_banquet")
async def order_banquet(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    banquet_orders[user_id] = {}
    user_states[user_id] = 'banquet_persons'
    
    await delete_all_user_messages(user_id)
    
    sent_msg = await callback.message.answer(
        "🎯 <b>Бронирование фуршета</b>\n\n📝 Введите количество персон (от 5):\n<i>Например: 10</i>",
        reply_markup=get_cancel_keyboard()
    )
    await add_user_message(sent_msg)
    
    try:
        await callback.message.delete()
    except:
        pass

@dp.callback_query(F.data == "book_chicken")
async def book_chicken(callback: CallbackQuery):
    await delete_all_user_messages(callback.from_user.id)
    
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📅 Забронировать к 18:00", callback_data="book_18")],
            [InlineKeyboardButton(text="💬 Написать менеджеру", callback_data="contact_manager")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
        ]
    )
    
    sent_msg = await send_with_photo(
        chat_id=callback.from_user.id,
        text=(
            "🐔 <b>Курица Гриль</b>\n\n"
            "⭐ <b>Хит продаж!</b>\n\n"
            "📏 Вес: ~1.1 кг\n"
            "💰 Цена: 1000₽\n"
            "🔥 Готовим на углях\n\nЗабронируйте свою курочку прямо сейчас!"
        ),
        image_path=BANNERS["chicken"],
        reply_markup=kb
    )
    await add_user_message(sent_msg)
    
    try:
        await callback.message.delete()
    except:
        pass

@dp.callback_query(F.data == "book_18")
async def book_18(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_states[user_id] = 'waiting_phone_chicken'
    
    await delete_all_user_messages(user_id)
    
    sent_msg = await callback.message.answer(
        "📅 <b>Бронирование курицы к 18:00</b>\n\n"
        "🐔 Курица Гриль ~1.1 кг — <b>1000₽</b>\n\n"
        "📞 Введите ваш номер телефона для подтверждения:",
        reply_markup=get_cancel_keyboard()
    )
    await add_user_message(sent_msg)
    
    try:
        await callback.message.delete()
    except:
        pass

@dp.callback_query(F.data == "contact_manager")
async def contact_manager(callback: CallbackQuery):
    await delete_all_user_messages(callback.from_user.id)
    
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="book_chicken")]
        ]
    )
    
    sent_msg = await callback.message.answer(
        "📞 <b>Свяжитесь с нами:</b>\n\nТелефон: +7 (900) 000-00-00\nTelegram: @grill_bar_manager\n\nМы на связи с 10:00 до 20:00!",
        reply_markup=kb
    )
    await add_user_message(sent_msg)
    
    try:
        await callback.message.delete()
    except:
        pass

@dp.callback_query(F.data == "schedule")
async def schedule(callback: CallbackQuery):
    await delete_all_user_messages(callback.from_user.id)
    
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
        ]
    )
    
    sent_msg = await callback.message.answer(
        "🕒 <b>График работы:</b>\n\n"
        "Пн - Пт: <b>10:00 - 20:00</b>\n"
        "Сб: 🚫 <b>Выходной</b>\n"
        "Вс: 🚫 <b>Выходной</b>\n\n"
        "🍗 Заказы на гриль принимаем до 19:00",
        reply_markup=kb
    )
    await add_user_message(sent_msg)
    
    try:
        await callback.message.delete()
    except:
        pass

@dp.callback_query(F.data == "contacts")
async def contacts(callback: CallbackQuery):
    await delete_all_user_messages(callback.from_user.id)
    
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📍 Показать на карте", callback_data="show_location"),
                InlineKeyboardButton(text="📞 Позвонить", callback_data="call_phone")
            ],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
        ]
    )
    
    sent_msg = await callback.message.answer(
        "📞 <b>Наши контакты:</b>\n\n"
        "📍 <b>Адрес:</b> 3-й квартал, 16, 305502, пос. Маршала Жукова, Курский район, Курская область\n"
        "📱 <b>Телефон:</b> +7 (900) 000-00-00\n"
        "💬 <b>Telegram:</b> @grill_bar\n"
        "📧 <b>Email:</b> info@grillbar.ru\n\n"
        "⏰ <b>Режим работы:</b> Пн-Пт 10:00-20:00",
        reply_markup=kb
    )
    await add_user_message(sent_msg)
    
    try:
        await callback.message.delete()
    except:
        pass

@dp.callback_query(F.data == "show_location")
async def show_location(callback: CallbackQuery):
    await callback.message.answer_location(latitude=51.7180, longitude=36.1870, reply_markup=get_main_keyboard())
    await callback.answer("📍 Мы находимся здесь!")

@dp.callback_query(F.data == "call_phone")
async def call_phone(callback: CallbackQuery):
    await callback.answer("📞 Наш телефон: +7 (900) 000-00-00")

@dp.callback_query(F.data == "noop")
async def noop(callback: CallbackQuery):
    await callback.answer()

# ================= ГЛАВНЫЙ ОБРАБОТЧИК ТЕКСТОВЫХ СООБЩЕНИЙ =================
@dp.message(F.text)
async def process_user_input(message: Message):
    user_id = message.from_user.id
    text = message.text.strip()
    
    await clear_history(user_id, keep_message_id=message.message_id)
    await add_user_message(message)
    
    state = user_states.get(user_id, 'main')

    # ---- ВВОД АДРЕСА ----
    if state == 'waiting_address':
        if not validate_address(text):
            sent_msg = await message.answer("⚠️ <b>Некорректный адрес!</b>\n\nВведите адрес более подробно:\n<i>Пример: г. Москва, ул. Ленина, д. 10, кв. 25</i>")
            await add_user_message(sent_msg)
            return
        
        carts[user_id]['address'] = text
        user_states[user_id] = 'waiting_phone'
        
        sent_msg = await message.answer("✅ Адрес принят!\n\n📞 Теперь введите ваш номер телефона:", reply_markup=get_cancel_keyboard())
        await add_user_message(sent_msg)
        return

    # ---- ВВОД ТЕЛЕФОНА (для заказа) ----
    if state == 'waiting_phone':
        if not validate_phone(text):
            sent_msg = await message.answer("⚠️ <b>Некорректный номер телефона!</b>\n\nВведите номер в формате:\n<i>+7 (999) 123-45-67 или 89991234567</i>")
            await add_user_message(sent_msg)
            return
        
        carts[user_id]['phone'] = text
        await send_order_to_admin(user_id)
        
        user_states[user_id] = 'main'
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🏠 В главное меню", callback_data="back")]
            ]
        )
        
        await delete_all_user_messages(user_id)
        
        sent_msg = await message.answer(
            "🎉 <b>ЗАКАЗ ПРИНЯТ!</b>\n\n"
            "📞 С вами свяжется наша кухня для уточнения деталей доставки.\n\n"
            "💳 Оплата при получении: наличными или картой\n\n"
            "Спасибо за заказ!",
            reply_markup=kb
        )
        await add_user_message(sent_msg)
        
        carts[user_id] = {}
        return

    # ---- ВВОД ТЕЛЕФОНА (для брони курицы) ----
    if state == 'waiting_phone_chicken':
        if not validate_phone(text):
            sent_msg = await message.answer("⚠️ <b>Некорректный номер!</b>\n<i>Пример: +7 (999) 123-45-67</i>")
            await add_user_message(sent_msg)
            return

        order_text = (
            "🐔 <b>БРОНЬ КУРИЦЫ ГРИЛЬ!</b>\n\n"
            f"👤 Клиент: {message.from_user.first_name}\n"
            f"📞 Телефон: {text}\n"
            f"⏰ Время: к 18:00\n"
            f"💰 Цена: 1000₽\n\n"
            f"📱 Для связи: @{message.from_user.username}"
        )
        
        await bot.send_message(ADMIN_CHAT_ID, order_text)
        
        user_states[user_id] = 'main'
        await delete_all_user_messages(user_id)
        
        sent_msg = await message.answer("✅ <b>Курица забронирована на 18:00!</b>\n\n🐔 Мы уже начали готовить вашу курочку!\n📞 Ожидайте звонка для подтверждения.\n\n🏠 Главное меню:", reply_markup=get_main_keyboard())
        await add_user_message(sent_msg)
        return

    # ---- ЗАКАЗ ФУРШЕТА ----
    if state == 'banquet_persons':
        try:
            persons = int(text)
            if persons < BANQUET_MENU['min_persons']:
                sent_msg = await message.answer(f"⚠️ <b>Минимальное количество: {BANQUET_MENU['min_persons']} персон!</b>\nВведите число от {BANQUET_MENU['min_persons']}:")
                await add_user_message(sent_msg)
                return
            
            banquet_orders[user_id]['persons'] = persons
            user_states[user_id] = 'banquet_name'
            
            sent_msg = await message.answer("👤 Введите ваше имя:", reply_markup=get_cancel_keyboard())
            await add_user_message(sent_msg)
            return
        except ValueError:
            sent_msg = await message.answer("⚠️ <b>Пожалуйста, введите число!</b>\n<i>Например: 10</i>")
            await add_user_message(sent_msg)
            return

    if state == 'banquet_name':
        banquet_orders[user_id]['name'] = text
        user_states[user_id] = 'banquet_phone'
        
        sent_msg = await message.answer("📞 Введите ваш номер телефона:", reply_markup=get_cancel_keyboard())
        await add_user_message(sent_msg)
        return

    if state == 'banquet_phone':
        if not validate_phone(text):
            sent_msg = await message.answer("⚠️ <b>Некорректный номер телефона!</b>\n\nВведите номер в формате:\n<i>+7 (999) 123-45-67 или 89991234567</i>")
            await add_user_message(sent_msg)
            return
        
        banquet_orders[user_id]['phone'] = text
        user_states[user_id] = 'banquet_address'
        
        sent_msg = await message.answer("📍 Введите адрес доставки:", reply_markup=get_cancel_keyboard())
        await add_user_message(sent_msg)
        return

    if state == 'banquet_address':
        if not validate_address(text):
            sent_msg = await message.answer("⚠️ <b>Некорректный адрес!</b>\n\nВведите адрес более подробно:\n<i>Пример: г. Москва, ул. Ленина, д. 10, кв. 25</i>")
            await add_user_message(sent_msg)
            return
        
        banquet_orders[user_id]['address'] = text
        
        order_data = banquet_orders[user_id]
        persons = order_data['persons']
        total = persons * BANQUET_MENU['price_per_person']
        
        order_text = (
            "🥂 <b>ЗАКАЗ ФУРШЕТА!</b>\n\n"
            f"👤 <b>Имя:</b> {order_data['name']}\n"
            f"📞 <b>Телефон:</b> {order_data['phone']}\n"
            f"📍 <b>Адрес:</b> {order_data['address']}\n"
            f"👥 <b>Количество персон:</b> {persons}\n"
            f"💰 <b>Итого:</b> {total}₽\n\n"
            f"📱 <b>Telegram:</b> @{message.from_user.username}"
        )
        
        try:
            await bot.send_message(ADMIN_CHAT_ID, order_text)
        except Exception as e:
            logger.error(f"Ошибка при отправке фуршета: {e}")
        
        user_states[user_id] = 'main'
        del banquet_orders[user_id]
        
        await delete_all_user_messages(user_id)
        
        sent_msg = await message.answer(
            f"✅ <b>Фуршет забронирован!</b>\n\n"
            f"👥 Персон: {persons}\n"
            f"💰 Сумма: {total}₽\n\n"
            f"📞 С вами свяжется наша команда для уточнения деталей!",
            reply_markup=get_main_keyboard()
        )
        await add_user_message(sent_msg)
        return

    sent_msg = await message.answer("👋 Выберите пункт в меню:", reply_markup=get_main_keyboard())
    await add_user_message(sent_msg)

async def send_order_to_admin(user_id):
    cart = carts.get(user_id, {})
    user = await bot.get_chat(user_id)
    
    total = 0
    order_text = "🛒 <b>НОВЫЙ ЗАКАЗ!</b>\n\n"
    order_text += f"👤 <b>Клиент:</b> {user.first_name}\n"
    if user.last_name:
        order_text += f"   {user.last_name}\n"
    order_text += f"📞 <b>Телефон:</b> {cart.get('phone', 'Не указан')}\n"
    
    if 'address' in cart:
        order_text += f"📍 <b>Адрес:</b> {cart['address']}\n"
        order_text += "🚚 <b>Тип:</b> Доставка\n"
    else:
        order_text += "🏃 <b>Тип:</b> Самовывоз\n"
    
    order_text += "\n<b>— Состав заказа —</b>\n"
    
    for item_id, data in cart.items():
        if item_id in ['address', 'phone']:
            continue
        if isinstance(data, list) and len(data) == 2:
            price, qty = data
            item_info = MENU_ITEMS.get(item_id, {})
            item_name = item_info.get('name', 'Неизвестно')
            
            item_total = price * qty
            total += item_total
            order_text += f"• {item_name} x {qty} = <b>{item_total}₽</b>\n"
    
    order_text += f"\n💰 <b>ИТОГО: {total}₽</b>\n"
    order_text += f"🕒 <b>Время заказа:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    
    try:
        await bot.send_message(ADMIN_CHAT_ID, order_text)
    except Exception as e:
        logger.error(f"Ошибка при отправке заказа: {e}")

# ================= ОБРАБОТКА ОШИБОК =================
@dp.errors()
async def error_handler(update: types.Update, exception: Exception):
    logger.error(f"Ошибка: {exception}")
    
    try:
        user_id = None
        if update and update.message:
            user_id = update.message.from_user.id
            first_name = update.message.from_user.first_name
        elif update and update.callback_query:
            user_id = update.callback_query.from_user.id
            first_name = update.callback_query.from_user.first_name
        else:
            first_name = "Неизвестно"
        
        await bot.send_message(
            ADMIN_CHAT_ID,
            f"❌ <b>Произошла ошибка!</b>\n\nОшибка: {exception}\n"
            f"Пользователь ID: {user_id}\nИмя: {first_name}\n"
            f"Время: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )
        
        if user_id:
            try:
                await bot.send_message(
                    user_id,
                    "⚠️ <b>Произошла ошибка.</b>\nПопробуйте еще раз или напишите в поддержку: @grill_bar_support",
                    reply_markup=get_main_keyboard()
                )
            except:
                pass
    except Exception as e:
        logger.error(f"Не удалось обработать ошибку: {e}")
    
    return True

# ================= ЗАПУСК =================
async def main():
    print("🤖 Бот Гриль Бар запущен!")
    print("👨‍💼 Ожидание сообщений...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
