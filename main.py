import asyncio
import logging
import threading
import pandas as pd
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import dash
from dash import Input, Output, dcc, html, dash_table
import plotly.express as px
import plotly.graph_objects as go
from os import getenv

from dotenv import load_dotenv

# ================== КОНФИГУРАЦИЯ ==================
load_dotenv()
API_TOKEN = getenv('TOKEN')
DASH_PORT = 8050
DASHBOARD_URL = "http://127.0.0.1:8050"  

# ================== ХРАНИЛИЩЕ ТОВАРОВ ==================
products_db = []
sales_history = []

# ================== TELEGRAM BOT ==================
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# ================== DASH DASHBOARD ==================
app = dash.Dash(__name__)
app.title = "Аналитика товаров - Retail Management"

styles = {
    'header': {
        'backgroundColor': '#2c3e50',
        'color': 'white',
        'padding': '20px',
        'textAlign': 'center',
        'borderRadius': '10px',
        'marginBottom': '20px'
    },
    'card': {
        'backgroundColor': '#f8f9fa',
        'padding': '15px',
        'borderRadius': '10px',
        'boxShadow': '0 2px 4px rgba(0,0,0,0.1)',
        'marginBottom': '20px'
    }
}

# Макет дашборда
app.layout = html.Div(style={'margin': '20px', 'fontFamily': 'Arial, sans-serif'}, children=[
    html.Div(style=styles['header'], children=[
        html.H1("📊 Аналитика управления товарами"),
        html.P("Данные из Telegram-бота в реальном времени"),
        html.P(f"Товаров в базе: {len(products_db)}", id='live-counter')
    ]),
    
    # Индикаторы
    html.Div([
        html.Div(id='total-products-indicator', style={
            'backgroundColor': '#ffffff',
            'padding': '15px',
            'borderRadius': '8px',
            'textAlign': 'center',
            'boxShadow': '0 1px 3px rgba(0,0,0,0.1)',
            'width': '24%',
            'display': 'inline-block',
            'marginRight': '1%'
        }),
        html.Div(id='total-value-indicator', style={
            'backgroundColor': '#ffffff',
            'padding': '15px',
            'borderRadius': '8px',
            'textAlign': 'center',
            'boxShadow': '0 1px 3px rgba(0,0,0,0.1)',
            'width': '24%',
            'display': 'inline-block',
            'marginRight': '1%'
        }),
        html.Div(id='low-stock-indicator', style={
            'backgroundColor': '#ffffff',
            'padding': '15px',
            'borderRadius': '8px',
            'textAlign': 'center',
            'boxShadow': '0 1px 3px rgba(0,0,0,0.1)',
            'width': '24%',
            'display': 'inline-block',
            'marginRight': '1%'
        }),
        html.Div(id='expiring-soon-indicator', style={
            'backgroundColor': '#ffffff',
            'padding': '15px',
            'borderRadius': '8px',
            'textAlign': 'center',
            'boxShadow': '0 1px 3px rgba(0,0,0,0.1)',
            'width': '24%',
            'display': 'inline-block'
        }),
    ]),
    
    # Графики
    html.Div([
        html.Div([
            dcc.Graph(id='stock-level-chart'),
        ], style={'width': '49%', 'display': 'inline-block', 'marginRight': '1%'}),
        
        html.Div([
            dcc.Graph(id='category-distribution'),
        ], style={'width': '49%', 'display': 'inline-block'}),
    ]),
    
    # Таблица товаров
    html.Div(style=styles['card'], children=[
        html.H3("📋 Текущие товарные остатки"),
        dash_table.DataTable(
            id='products-table',
            page_size=10,
            style_table={'overflowX': 'auto'},
            style_cell={'textAlign': 'left', 'padding': '10px'},
            style_header={
                'backgroundColor': '#2c3e50',
                'color': 'white',
                'fontWeight': 'bold'
            },
        )
    ]),
    
    # Обновление данных
    dcc.Interval(
        id='interval-component',
        interval=5000,  # Обновление каждые 5 секунд
        n_intervals=0
    )
])

@app.callback(
    [Output('products-table', 'data'),
     Output('products-table', 'columns'),
     Output('total-products-indicator', 'children'),
     Output('total-value-indicator', 'children'),
     Output('low-stock-indicator', 'children'),
     Output('expiring-soon-indicator', 'children'),
     Output('stock-level-chart', 'figure'),
     Output('category-distribution', 'figure'),
     Output('live-counter', 'children')],
    [Input('interval-component', 'n_intervals')]
)
def update_dashboard(n):
    """Обновление дашборда данными из бота"""
    
    # Создаем DataFrame из данных бота
    df = pd.DataFrame(products_db)
    
    if len(df) == 0:
        empty_df = pd.DataFrame([{'sku': 'Нет данных', 'name': 'Нет данных', 'quantity': 0}])
        return (
            empty_df.to_dict('records'),
            [{"name": i, "id": i} for i in empty_df.columns],
            [html.H4("Всего товаров"), html.H2("0")],
            [html.H4("Общая стоимость"), html.H2("0 руб")],
            [html.H4("Низкий запас"), html.H2("0")],
            [html.H4("Срок годности"), html.H2("0")],
            go.Figure(),
            go.Figure(),
            f"Товаров в базе: 0"
        )
    
    # Расчет показателей
    total_products = len(df)
    total_value = (df['quantity'] * df['price']).sum()
    low_stock = len(df[df['quantity'] < 5])
    
  
    now = datetime.now()
    expiring_soon = 0
    for product in products_db:
        if 'expiry' in product:
            try:
                expiry_date = datetime.strptime(product['expiry'], '%Y-%m-%d')
                days_left = (expiry_date - now).days
                if 0 <= days_left <= 30:
                    expiring_soon += 1
            except:
                pass
    
   
    table_data = df.to_dict('records')
    table_columns = [{"name": i, "id": i} for i in ['name', 'sku', 'quantity', 'price', 'status', 'manager']]
    
   
    total_products_indicator = [
        html.H4("Всего товаров", style={'color': '#3498db'}),
        html.H2(str(total_products), style={'color': '#3498db', 'margin': '10px 0'}),
        html.P(f"{len(df)} позиций")
    ]
    
    total_value_indicator = [
        html.H4("Общая стоимость", style={'color': '#27ae60'}),
        html.H2(f"{total_value:,.0f} руб", style={'color': '#27ae60', 'margin': '10px 0'}),
        html.P("Стоимость запасов")
    ]
    
    low_stock_indicator = [
        html.H4("Низкий запас", style={'color': '#e74c3c'}),
        html.H2(str(low_stock), style={'color': '#e74c3c', 'margin': '10px 0'}),
        html.P("менее 5 шт.")
    ]
    
    expiring_soon_indicator = [
        html.H4("Скоро истечет", style={'color': '#f39c12'}),
        html.H2(str(expiring_soon), style={'color': '#f39c12', 'margin': '10px 0'}),
        html.P("в течение 30 дней")
    ]
    

    stock_fig = go.Figure()
    stock_fig.add_trace(go.Bar(
        x=df['name'][:10],  
        y=df['quantity'][:10],
        name='Количество',
        marker_color='#3498db'
    ))
    stock_fig.update_layout(
        title='Уровень запасов (ТОП-10)',
        xaxis_title='Товар',
        yaxis_title='Количество, шт.'
    )
    
    
    if 'category' not in df.columns:
        categories = ['Электроника', 'Одежда', 'Продукты', 'Бытовая техника', 'Мебель']
        df['category'] = [categories[i % len(categories)] for i in range(len(df))]
    
    category_fig = px.pie(
        df,
        names='category',
        title='Распределение по категориям',
        hole=0.4
    )
    
    return (
        table_data,
        table_columns,
        total_products_indicator,
        total_value_indicator,
        low_stock_indicator,
        expiring_soon_indicator,
        stock_fig,
        category_fig,
        f"Товаров в базе: {len(products_db)}"
    )

def run_dashboard():
    """Запуск дашборда в отдельном потоке"""
    app.run(debug=False, port=DASH_PORT, host='127.0.0.1')


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "🤖 <b>Бот управления товарами с аналитикой</b>\n\n"
        "<b>📊 Основные команды:</b>\n"
        "/add Название, SKU, Кол-во, Цена, Срок - Добавить товар\n"
        "/list - Показать остатки\n"
        "/info SKU - Детали о товаре\n"
        "/update SKU, Поле, Значение - Обновить\n"
        "/delete SKU, Кол-во - Списать\n"
        "/status SKU, Статус - Изменить статус\n"
        "/manager SKU, ФИО - Назначить ответственного\n\n"
        "<b>📈 Аналитика и отчеты:</b>\n"
        "/dashboard - Запустить аналитику\n"
        "/sell SKU, Кол-во, Цена - Продажа товара\n"
        "/help - Справка",
        parse_mode='HTML'
    )

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "📚 <b>Справка по использованию бота</b>\n\n"
        "<b>Форматы команд:</b>\n"
        "• /add Название, SKU, Количество, Цена, Срок годности\n"
        "  Пример: /add Кофеварка, SKU-001, 10, 15000, 2025-12-31\n\n"
        "• /update SKU, Поле, Новое значение\n"
        "  Пример: /update SKU-001, количество, 15\n\n"
        "• /delete SKU, Количество\n"
        "  Пример: /delete SKU-001, 2\n\n"
        "• /status SKU, Статус\n"
        "  Пример: /status SKU-001, В резерве\n\n"
        "<b>Доступные статусы:</b> В наличии, Нет в наличии, В резерве, Списано",
        parse_mode='HTML'
    )

@dp.message(Command("add"))
async def cmd_add(message: types.Message):
    """Добавление товара с автоматическим обновлением дашборда"""
    try:
        text = message.text.replace('/add', '').strip()
        if not text:
            await message.answer("❌ <b>Неверный формат</b>\nИспользуйте: /add Название, SKU, Количество, Цена, Срок годности\nПример: /add Кофеварка, SKU-001, 10, 15000, 2025-12-31", parse_mode='HTML')
            return
        
        args = [arg.strip() for arg in text.split(',')]
        if len(args) < 5:
            await message.answer("❌ <b>Недостаточно параметров</b>\nНужно 5 параметров: Название, SKU, Количество, Цена, Срок годности", parse_mode='HTML')
            return
        
        name, sku, quantity, price, expiry = args[0], args[1], args[2], args[3], args[4]
        
        try:
            quantity = int(quantity)
            price = float(price)
        except ValueError:
            await message.answer("❌ <b>Ошибка данных</b>\nКоличество должно быть целым числом, цена - числом", parse_mode='HTML')
            return
        
       
        for p in products_db:
            if p['sku'] == sku:
                p['quantity'] += quantity
                await message.answer(
                    f"✅ <b>Товар обновлен</b>\n"
                    f"Артикул: {sku}\n"
                    f"Новое количество: {p['quantity']} шт.\n"
                    f"Общая стоимость: {p['quantity'] * p['price']:,.0f} руб",
                    parse_mode='HTML'
                )
                return
        
      
        category = "Другое"
        if any(word in name.lower() for word in ['телефон', 'ноутбук', 'планшет']):
            category = "Электроника"
        elif any(word in name.lower() for word in ['кофе', 'чай', 'молоко']):
            category = "Продукты"
        elif any(word in name.lower() for word in ['футболка', 'джинсы', 'куртка']):
            category = "Одежда"
        
        product = {
            'name': name,
            'sku': sku,
            'quantity': quantity,
            'price': price,
            'expiry': expiry,
            'status': 'В наличии',
            'manager': 'Не назначен',
            'category': category,
            'added_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        products_db.append(product)
        
        await message.answer(
            f"✅ <b>Товар добавлен</b>\n"
            f"Название: {name}\n"
            f"Артикул: {sku}\n"
            f"Количество: {quantity} шт.\n"
            f"Цена: {price} руб\n"
            f"Срок годности: {expiry}\n"
            f"Категория: {category}\n\n"
            f"<i>Дашборд обновлен автоматически</i>",
            parse_mode='HTML'
        )
    except Exception as e:
        await message.answer(f"❌ <b>Ошибка:</b> {str(e)}", parse_mode='HTML')

@dp.message(Command("list"))
async def cmd_list(message: types.Message):
    """Просмотр остатков с информацией из дашборда"""
    if not products_db:
        await message.answer("📦 <b>Склад пуст</b>\nДобавьте товары командой /add", parse_mode='HTML')
        return
    
   
    total_value = sum(p['quantity'] * p['price'] for p in products_db)
    total_items = sum(p['quantity'] for p in products_db)
    
    response = f"📊 <b>Остатки товаров</b>\n\n"
    response += f"Всего позиций: {len(products_db)}\n"
    response += f"Общее количество: {total_items} шт.\n"
    response += f"Стоимость запасов: {total_value:,.0f} руб\n\n"
    response += "<b>ТОП-5 товаров:</b>\n"
    
   
    sorted_products = sorted(products_db, key=lambda x: x['quantity'], reverse=True)[:5]
    
    for i, product in enumerate(sorted_products, 1):
        response += f"{i}. {product['name']} ({product['sku']}): {product['quantity']} шт.\n"
    
    if len(products_db) > 5:
        response += f"\n... и еще {len(products_db) - 5} позиций\n"
    
    response += f"\n<i>Полный список доступен в дашборде: /dashboard</i>"
    
    await message.answer(response, parse_mode='HTML')

@dp.message(Command("info"))
async def cmd_info(message: types.Message):
    """Детальная информация о товаре"""
    try:
        text = message.text.replace('/info', '').strip()
        if not text:
            await message.answer("❌ Укажите артикул: /info SKU", parse_mode='HTML')
            return
        
        sku = text.strip()
        
        for product in products_db:
            if product['sku'] == sku:
                total_value = product['quantity'] * product['price']
                
                await message.answer(
                    f"📋 <b>Детальная информация</b>\n\n"
                    f"<b>Название:</b> {product['name']}\n"
                    f"<b>Артикул:</b> {product['sku']}\n"
                    f"<b>Количество:</b> {product['quantity']} шт.\n"
                    f"<b>Цена за шт.:</b> {product['price']} руб\n"
                    f"<b>Общая стоимость:</b> {total_value:,.0f} руб\n"
                    f"<b>Статус:</b> {product['status']}\n"
                    f"<b>Срок годности:</b> {product['expiry']}\n"
                    f"<b>Ответственный:</b> {product['manager']}\n"
                    f"<b>Категория:</b> {product['category']}\n"
                    f"<b>Добавлен:</b> {product['added_at']}",
                    parse_mode='HTML'
                )
                return
        
        await message.answer(f"❌ Товар с артикулом <b>{sku}</b> не найден", parse_mode='HTML')
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}", parse_mode='HTML')

@dp.message(Command("update"))
async def cmd_update(message: types.Message):
    """Обновление информации о товаре"""
    try:
        text = message.text.replace('/update', '').strip()
        if not text:
            await message.answer("❌ <b>Неверный формат</b>\nИспользуйте: /update SKU, Поле, Значение\nПример: /update SKU-001, количество, 15", parse_mode='HTML')
            return
        
        args = [arg.strip() for arg in text.split(',')]
        if len(args) < 3:
            await message.answer("❌ <b>Недостаточно параметров</b>\nНужно 3 параметра: SKU, Поле, Значение", parse_mode='HTML')
            return
        
        sku, field, value = args[0], args[1].lower(), args[2]
        
        for product in products_db:
            if product['sku'] == sku:
                old_value = product.get(field, 'не установлено')
                
                
                if field == 'количество':
                    try:
                        value = int(value)
                    except ValueError:
                        await message.answer("❌ Количество должно быть целым числом", parse_mode='HTML')
                        return
                elif field == 'цена':
                    try:
                        value = float(value)
                    except ValueError:
                        await message.answer("❌ Цена должна быть числом", parse_mode='HTML')
                        return
                
                product[field] = value
                
                await message.answer(
                    f"✅ <b>Данные обновлены</b>\n"
                    f"Товар: {product['name']} ({sku})\n"
                    f"Поле: {field}\n"
                    f"Старое значение: {old_value}\n"
                    f"Новое значение: {value}",
                    parse_mode='HTML'
                )
                return
        
        await message.answer(f"❌ Товар с артикулом <b>{sku}</b> не найден", parse_mode='HTML')
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}", parse_mode='HTML')

@dp.message(Command("delete"))
async def cmd_delete(message: types.Message):
    """Списание товара"""
    try:
        text = message.text.replace('/delete', '').strip()
        if not text:
            await message.answer("❌ <b>Неверный формат</b>\nИспользуйте: /delete SKU, Количество\nПример: /delete SKU-001, 2", parse_mode='HTML')
            return
        
        args = [arg.strip() for arg in text.split(',')]
        if len(args) < 2:
            await message.answer("❌ <b>Недостаточно параметров</b>\nНужно 2 параметра: SKU, Количество", parse_mode='HTML')
            return
        
        sku, quantity = args[0], args[1]
        
        try:
            quantity = int(quantity)
        except ValueError:
            await message.answer("❌ Количество должно быть целым числом", parse_mode='HTML')
            return
        
        for product in products_db:
            if product['sku'] == sku:
                if product['quantity'] >= quantity:
                    product['quantity'] -= quantity
                    
                  
                    if product['quantity'] == 0:
                        product['status'] = 'Нет в наличии'
                        status_msg = " (товар закончился)"
                    else:
                        status_msg = ""
                    
                    await message.answer(
                        f"✅ <b>Товар списан</b>\n"
                        f"Название: {product['name']}\n"
                        f"Артикул: {sku}\n"
                        f"Списано: {quantity} шт.\n"
                        f"Осталось: {product['quantity']} шт.{status_msg}\n\n"
                        f"<i>Дашборд обновлен автоматически</i>",
                        parse_mode='HTML'
                    )
                    return
                else:
                    await message.answer(f"❌ <b>Недостаточно товара</b>\nДоступно: {product['quantity']} шт.\nТребуется: {quantity} шт.", parse_mode='HTML')
                    return
        
        await message.answer(f"❌ Товар с артикулом <b>{sku}</b> не найден", parse_mode='HTML')
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}", parse_mode='HTML')

@dp.message(Command("status"))
async def cmd_status(message: types.Message):
    """Изменение статуса товара"""
    try:
        text = message.text.replace('/status', '').strip()
        if not text:
            await message.answer("❌ <b>Неверный формат</b>\nИспользуйте: /status SKU, Статус\nПример: /status SKU-001, В резерве", parse_mode='HTML')
            return
        
        args = [arg.strip() for arg in text.split(',')]
        if len(args) < 2:
            await message.answer("❌ <b>Недостаточно параметров</b>\nНужно 2 параметра: SKU, Статус", parse_mode='HTML')
            return
        
        sku, new_status = args[0], args[1]
        
        valid_statuses = ['В наличии', 'Нет в наличии', 'В резерве', 'Списано', 'На проверке']
        
        if new_status not in valid_statuses:
            await message.answer(f"❌ <b>Неверный статус</b>\nДопустимые статусы: {', '.join(valid_statuses)}", parse_mode='HTML')
            return
        
        for product in products_db:
            if product['sku'] == sku:
                old_status = product['status']
                product['status'] = new_status
                
                await message.answer(
                    f"✅ <b>Статус изменен</b>\n"
                    f"Товар: {product['name']} ({sku})\n"
                    f"Старый статус: {old_status}\n"
                    f"Новый статус: {new_status}",
                    parse_mode='HTML'
                )
                return
        
        await message.answer(f"❌ Товар с артикулом <b>{sku}</b> не найден", parse_mode='HTML')
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}", parse_mode='HTML')

@dp.message(Command("manager"))
async def cmd_manager(message: types.Message):
    """Назначение ответственного за товар"""
    try:
        text = message.text.replace('/manager', '').strip()
        if not text:
            await message.answer("❌ <b>Неверный формат</b>\nИспользуйте: /manager SKU, ФИО\nПример: /manager SKU-001, Иванов И.И.", parse_mode='HTML')
            return
        
        args = [arg.strip() for arg in text.split(',')]
        if len(args) < 2:
            await message.answer("❌ <b>Недостаточно параметров</b>\nНужно 2 параметра: SKU, ФИО", parse_mode='HTML')
            return
        
        sku, manager = args[0], args[1]
        
        for product in products_db:
            if product['sku'] == sku:
                old_manager = product['manager']
                product['manager'] = manager
                
                await message.answer(
                    f"✅ <b>Ответственный назначен</b>\n"
                    f"Товар: {product['name']} ({sku})\n"
                    f"Прежний ответственный: {old_manager}\n"
                    f"Новый ответственный: {manager}",
                    parse_mode='HTML'
                )
                return
        
        await message.answer(f"❌ Товар с артикулом <b>{sku}</b> не найден", parse_mode='HTML')
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}", parse_mode='HTML')

@dp.message(Command("dashboard"))
async def cmd_dashboard(message: types.Message):
    """Запуск и отправка ссылки на дашборд"""
    
    total_items = len(products_db)
    total_value = sum(p['quantity'] * p['price'] for p in products_db) if products_db else 0
    active_items = sum(1 for p in products_db if p['status'] == 'В наличии')
    
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Обновить дашборд", callback_data="refresh_dashboard")],
            [InlineKeyboardButton(text="📋 Быстрый отчет", callback_data="quick_report")]
        ]
    )
    
    await message.answer(
        f"📈 <b>Аналитический дашборд</b>\n\n"
        f"<b>📊 Текущие показатели:</b>\n"
        f"• Товаров: {total_items}\n"
        f"• Стоимость запасов: {total_value:,.0f} руб\n"
        f"• Активных: {active_items}\n"
        f"• В резерве: {sum(1 for p in products_db if p['status'] == 'В резерве')}\n\n"
        f"<b>🌐 Дашборд доступен по адресу:</b>\n"
        f"http://127.0.0.1:{DASH_PORT}\n\n"
        f"<i>Дашборд обновляется автоматически каждые 5 секунд</i>",
        reply_markup=keyboard,
        parse_mode='HTML'
    )

@dp.message(Command("sell"))
async def cmd_sell(message: types.Message):
    """Регистрация продажи с обновлением дашборда"""
    try:
        text = message.text.replace('/sell', '').strip()
        if not text:
            await message.answer("❌ <b>Неверный формат</b>\nИспользуйте: /sell SKU, Количество, Цена продажи\nПример: /sell SKU-001, 1, 18000", parse_mode='HTML')
            return
        
        args = [arg.strip() for arg in text.split(',')]
        if len(args) < 3:
            await message.answer("❌ <b>Недостаточно параметров</b>\nНужно 3 параметра: SKU, Количество, Цена продажи", parse_mode='HTML')
            return
        
        sku, quantity, price = args[0], args[1], args[2]
        
        try:
            quantity = int(quantity)
            price = float(price)
        except ValueError:
            await message.answer("❌ <b>Ошибка данных</b>\nКоличество должно быть целым числом, цена - числом", parse_mode='HTML')
            return
        
        
        for product in products_db:
            if product['sku'] == sku:
                if product['quantity'] >= quantity:
                    product['quantity'] -= quantity
                    sale_total = quantity * price
                    
                   
                    sale = {
                        'sku': sku,
                        'name': product['name'],
                        'quantity': quantity,
                        'price': price,
                        'total': sale_total,
                        'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'profit': sale_total - (quantity * product['price'])
                    }
                    sales_history.append(sale)
                    
                
                    if product['quantity'] == 0:
                        product['status'] = 'Нет в наличии'
                        status_msg = " (товар закончился)"
                    else:
                        status_msg = ""
                    
                    profit = sale_total - (quantity * product['price'])
                    profit_percent = (profit / (quantity * product['price'])) * 100 if (quantity * product['price']) > 0 else 0
                    
                    await message.answer(
                        f"💰 <b>Продажа зарегистрирована</b>\n\n"
                        f"<b>Товар:</b> {product['name']}\n"
                        f"<b>Артикул:</b> {sku}\n"
                        f"<b>Продано:</b> {quantity} шт.\n"
                        f"<b>Цена закупки:</b> {product['price']} руб/шт.\n"
                        f"<b>Цена продажи:</b> {price} руб/шт.\n"
                        f"<b>Выручка:</b> {sale_total:,.0f} руб\n"
                        f"<b>Прибыль:</b> {profit:,.0f} руб ({profit_percent:.1f}%)\n"
                        f"<b>Осталось:</b> {product['quantity']} шт.{status_msg}\n\n"
                        f"<i>Дашборд обновлен</i>",
                        parse_mode='HTML'
                    )
                    return
                else:
                    await message.answer(f"❌ <b>Недостаточно товара</b>\nДоступно: {product['quantity']} шт.\nТребуется: {quantity} шт.", parse_mode='HTML')
                    return
        
        await message.answer(f"❌ Товар с артикулом <b>{sku}</b> не найден", parse_mode='HTML')
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}", parse_mode='HTML')

@dp.message(Command("report"))
async def cmd_report(message: types.Message):
    """Быстрый отчет для отправки в чат"""
    if not products_db:
        await message.answer("📭 <b>Нет данных для отчета</b>\nДобавьте товары командой /add", parse_mode='HTML')
        return
    
    total_items = len(products_db)
    total_quantity = sum(p['quantity'] for p in products_db)
    total_value = sum(p['quantity'] * p['price'] for p in products_db)
    low_stock = sum(1 for p in products_db if p['quantity'] < 5)
    out_of_stock = sum(1 for p in products_db if p['status'] == 'Нет в наличии')
    
    top_by_quantity = sorted(products_db, key=lambda x: x['quantity'], reverse=True)[:5]
    
    top_by_value = sorted(products_db, key=lambda x: x['quantity'] * x['price'], reverse=True)[:5]
    
    total_sales = len(sales_history)
    total_revenue = sum(s['total'] for s in sales_history)
    total_profit = sum(s['profit'] for s in sales_history)
    
    report = f"📋 <b>ЭКСПРЕСС-ОТЧЕТ</b>\n\n"
    report += f"<b>📊 Общая статистика:</b>\n"
    report += f"• Всего позиций: {total_items}\n"
    report += f"• Общее количество: {total_quantity} шт.\n"
    report += f"• Стоимость запасов: {total_value:,.0f} руб\n"
    report += f"• Низкий запас (<5 шт.): {low_stock}\n"
    report += f"• Нет в наличии: {out_of_stock}\n\n"
    
    if total_sales > 0:
        report += f"<b>💰 Продажи:</b>\n"
        report += f"• Всего продаж: {total_sales}\n"
        report += f"• Общая выручка: {total_revenue:,.0f} руб\n"
        report += f"• Общая прибыль: {total_profit:,.0f} руб\n\n"
    
    report += f"<b>🏆 ТОП-5 по количеству:</b>\n"
    for i, item in enumerate(top_by_quantity, 1):
        report += f"{i}. {item['name']}: {item['quantity']} шт.\n"
    
    report += f"\n<strong>💎 ТОП-5 по стоимости:</strong>\n"
    for i, item in enumerate(top_by_value, 1):
        item_value = item['quantity'] * item['price']
        report += f"{i}. {item['name']}: {item_value:,.0f} руб\n"
    
    await message.answer(report, parse_mode='HTML')

@dp.callback_query(F.data == "refresh_dashboard")
async def refresh_dashboard(callback: types.CallbackQuery):
    """Обновление дашборда"""
    await callback.answer("✅ Дашборд обновляется автоматически каждые 5 секунд")

@dp.callback_query(F.data == "quick_report")
async def quick_report(callback: types.CallbackQuery):
    """Быстрый отчет по callback"""
    if not products_db:
        await callback.answer("Нет данных для отчета")
        return
    
    total_items = len(products_db)
    total_value = sum(p['quantity'] * p['price'] for p in products_db)
    
    await callback.message.answer(
        f"📊 <b>Быстрый отчет</b>\n\n"
        f"Всего товаров: {total_items}\n"
        f"Общая стоимость: {total_value:,.0f} руб\n"
        f"Активных: {sum(1 for p in products_db if p['status'] == 'В наличии')}\n"
        f"В резерве: {sum(1 for p in products_db if p['status'] == 'В резерве')}",
        parse_mode='HTML'
    )
    await callback.answer()

async def main():
    """Запуск бота и дашборда"""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    dash_thread = threading.Thread(target=run_dashboard, daemon=True)
    dash_thread.start()
    
    print(f"🚀 Дашборд запущен: http://127.0.0.1:{DASH_PORT}")
    print("🤖 Бот запускается...")
    print("📋 Используйте команду /start для получения списка команд")
    print("📊 Для просмотра аналитики откройте в браузере: http://127.0.0.1:8050")
    
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Программа завершена пользователем")