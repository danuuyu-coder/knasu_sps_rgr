import dash
from dash import dcc, html, dash_table, Input, Output, State, callback
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import base64
import io

# Инициализация приложения Dash
app = dash.Dash(__name__)
app.title = "Процесс менеджмента товаров для розничной торговли"

# Стили
styles = {
    'container': {
        'margin': '20px',
        'fontFamily': 'Arial, sans-serif'
    },
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
    },
    'indicator': {
        'backgroundColor': '#ffffff',
        'padding': '15px',
        'borderRadius': '8px',
        'textAlign': 'center',
        'boxShadow': '0 1px 3px rgba(0,0,0,0.1)'
    }
}

# Макет приложения
app.layout = html.Div(style=styles['container'], children=[
    html.Div(style=styles['header'], children=[
        html.H1("📊 Процесс менеджмента товаров для розничной торговли"),
        html.P("Интерактивная панель анализа финансовых показателей розничной торговли")
    ]),
    
    # Загрузка файла
    html.Div(style=styles['card'], children=[
        html.H3("📁 Загрузка данных"),
        dcc.Upload(
            id='upload-data',
            children=html.Div([
                'Перетащите или ',
                html.A('выберите CSV файл')
            ]),
            style={
                'width': '100%',
                'height': '60px',
                'lineHeight': '60px',
                'borderWidth': '1px',
                'borderStyle': 'dashed',
                'borderRadius': '5px',
                'textAlign': 'center',
                'margin': '10px 0'
            },
            multiple=False
        ),
        html.Div(id='output-data-upload'),
    ]),
    
    # Фильтры и управление
    html.Div(style=styles['card'], children=[
        html.H3("🔍 Фильтры и настройки"),
        html.Div([
            html.Div([
                html.Label("Период анализа:"),
                dcc.Dropdown(
                    id='period-filter',
                    options=[
                        {'label': 'Месяц', 'value': 'month'},
                        {'label': 'Квартал', 'value': 'quarter'},
                        {'label': 'Год', 'value': 'year'}
                    ],
                    value='month',
                    clearable=False
                ),
            ], style={'width': '24%', 'display': 'inline-block', 'marginRight': '1%'}),
            
            html.Div([
                html.Label("Категория:"),
                dcc.Dropdown(
                    id='category-filter',
                    multi=True,
                    placeholder="Все категории"
                ),
            ], style={'width': '24%', 'display': 'inline-block', 'marginRight': '1%'}),
            
            html.Div([
                html.Label("Диапазон дат:"),
                dcc.DatePickerRange(
                    id='date-range',
                    start_date=datetime(2024, 1, 1),
                    end_date=datetime(2024, 12, 31),
                    display_format='YYYY-MM-DD'
                ),
            ], style={'width': '24%', 'display': 'inline-block', 'marginRight': '1%'}),
            
            html.Div([
                html.Label("Тип графика:"),
                dcc.Dropdown(
                    id='chart-type',
                    options=[
                        {'label': 'Линейный', 'value': 'line'},
                        {'label': 'Столбчатый', 'value': 'bar'}
                    ],
                    value='line',
                    clearable=False
                ),
            ], style={'width': '24%', 'display': 'inline-block'}),
        ]),
    ]),
    
    # Индикаторы (полоски состояния)
    html.Div([
        html.Div([
            html.Div(id='total-revenue-indicator', style=styles['indicator']),
        ], style={'width': '19%', 'display': 'inline-block', 'marginRight': '1%'}),
        
        html.Div([
            html.Div(id='total-expenses-indicator', style=styles['indicator']),
        ], style={'width': '19%', 'display': 'inline-block', 'marginRight': '1%'}),
        
        html.Div([
            html.Div(id='total-profit-indicator', style=styles['indicator']),
        ], style={'width': '19%', 'display': 'inline-block', 'marginRight': '1%'}),
        
        html.Div([
            html.Div(id='profit-margin-indicator', style=styles['indicator']),
        ], style={'width': '19%', 'display': 'inline-block', 'marginRight': '1%'}),
        
        html.Div([
            html.Div(id='avg-monthly-growth', style=styles['indicator']),
        ], style={'width': '19%', 'display': 'inline-block'}),
    ]),
    
    # Прогресс-бары для индикаторов
    html.Div(style=styles['card'], children=[
        html.H4("📈 Прогресс по целям"),
        html.Div([
            html.Div([
                html.Label("Выручка:"),
                dcc.Slider(
                    id='revenue-progress',
                    min=0,
                    max=1000000,
                    value=0,
                    marks={0: '0', 500000: '500K', 1000000: '1M'},
                    disabled=True
                ),
            ], style={'marginBottom': '15px'}),
            
            html.Div([
                html.Label("Прибыль:"),
                dcc.Slider(
                    id='profit-progress',
                    min=0,
                    max=300000,
                    value=0,
                    marks={0: '0', 150000: '150K', 300000: '300K'},
                    disabled=True
                ),
            ], style={'marginBottom': '15px'}),
            
            html.Div([
                html.Label("Маржа прибыли:"),
                dcc.Slider(
                    id='margin-progress',
                    min=0,
                    max=50,
                    value=0,
                    marks={0: '0%', 25: '25%', 50: '50%'},
                    disabled=True
                ),
            ]),
        ]),
    ]),
    
    # Основные графики - первый ряд
    html.Div([
        html.Div([
            dcc.Graph(id='time-series-chart'),
        ], style={'width': '49%', 'display': 'inline-block', 'marginRight': '1%'}),
        
        html.Div([
            dcc.Graph(id='expenses-pie-chart'),
        ], style={'width': '49%', 'display': 'inline-block'}),
    ]),
    
    # Второй ряд графиков
    html.Div([
        html.Div([
            dcc.Graph(id='profit-histogram'),
        ], style={'width': '49%', 'display': 'inline-block', 'marginRight': '1%'}),
        
        html.Div([
            dcc.Graph(id='correlation-scatter'),
        ], style={'width': '49%', 'display': 'inline-block'}),
    ]),
    
    # Таблица с финансовыми показателями
    html.Div(style=styles['card'], children=[
        html.H3("📋 Детальные финансовые показатели"),
        dash_table.DataTable(
            id='financial-table',
            page_size=10,
            style_table={'overflowX': 'auto'},
            style_cell={
                'textAlign': 'left',
                'padding': '10px',
                'minWidth': '100px'
            },
            style_header={
                'backgroundColor': '#2c3e50',
                'color': 'white',
                'fontWeight': 'bold'
            },
            style_data_conditional=[
                {
                    'if': {'column_id': 'profit', 'filter_query': '{profit} < 0'},
                    'backgroundColor': '#ffcccc',
                    'color': 'black'
                },
                {
                    'if': {'column_id': 'profit', 'filter_query': '{profit} >= 0'},
                    'backgroundColor': '#ccffcc',
                    'color': 'black'
                }
            ]
        )
    ]),
])

# Функция для парсинга загруженного файла
def parse_contents(contents, filename):
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    
    try:
        if 'csv' in filename:
            df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
            # Преобразуем дату если нужно
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
        else:
            return html.Div(['Пожалуйста, загрузите файл в формате CSV'])
    except Exception as e:
        print(e)
        return html.Div(['Ошибка при обработке файла'])
    
    return df

# Колбэки
@app.callback(
    [Output('output-data-upload', 'children'),
     Output('category-filter', 'options'),
     Output('time-series-chart', 'figure'),
     Output('expenses-pie-chart', 'figure'),
     Output('profit-histogram', 'figure'),
     Output('correlation-scatter', 'figure'),
     Output('financial-table', 'data'),
     Output('financial-table', 'columns'),
     Output('total-revenue-indicator', 'children'),
     Output('total-expenses-indicator', 'children'),
     Output('total-profit-indicator', 'children'),
     Output('profit-margin-indicator', 'children'),
     Output('avg-monthly-growth', 'children'),
     Output('revenue-progress', 'value'),
     Output('profit-progress', 'value'),
     Output('margin-progress', 'value')],
    [Input('upload-data', 'contents'),
     Input('period-filter', 'value'),
     Input('category-filter', 'value'),
     Input('date-range', 'start_date'),
     Input('date-range', 'end_date'),
     Input('chart-type', 'value')],
    [State('upload-data', 'filename')]
)
def update_dashboard(contents, period, selected_categories, start_date, end_date, chart_type, filename):
    ctx = dash.callback_context
    
    # Если данные не загружены, используем демо-данные
    if contents is None:
        # Создаем демо-данные
        dates = pd.date_range(start='2024-01-01', end='2024-12-01', freq='MS')
        categories = ['Электроника', 'Одежда и обувь', 'Бытовая техника', 'Мебель', 'Красота и здоровье', 'Продукты', 'Игрушки']
        
        demo_data = []
        for date in dates:
            for category in categories:
                revenue = np.random.randint(3000, 20000)
                expenses = revenue * np.random.uniform(0.6, 0.8)
                profit = revenue - expenses
                demo_data.append({
                    'date': date,
                    'category': category,
                    'revenue': revenue,
                    'expenses': expenses,
                    'profit': profit,
                    'month': date.strftime('%B'),
                    'quarter': f'Q{(date.month-1)//3 + 1}',
                    'year': date.year
                })
        
        df = pd.DataFrame(demo_data)
        upload_message = html.Div([
            html.H5("Используются демо-данные"),
            html.P("Загрузите CSV файл для работы с реальными данными")
        ])
    else:
        df = parse_contents(contents, filename)
        if isinstance(df, html.Div):
            return df, [], {}, {}, {}, {}, [], [], [], [], [], [], [], 0, 0, 0
        upload_message = html.Div([
            html.H5(f"Файл '{filename}' успешно загружен"),
            html.P(f"Загружено {len(df)} записей")
        ])
    
    # Применяем фильтры дат
    if start_date and end_date:
        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date)
        df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
    
    # Применяем фильтры категорий
    filtered_df = df.copy()
    if selected_categories and len(selected_categories) > 0:
        filtered_df = filtered_df[filtered_df['category'].isin(selected_categories)]
    
    # Обновляем опции фильтров
    category_options = [{'label': cat, 'value': cat} for cat in df['category'].unique()]
    
    # Агрегируем данные по выбранному периоду
    if period == 'month':
        period_col = 'month'
        group_cols = ['month', 'year']
    elif period == 'quarter':
        period_col = 'quarter'
        group_cols = ['quarter', 'year']
    else:  # year
        period_col = 'year'
        group_cols = ['year']
    
    # Создаем агрегированные данные для графиков
    aggregated = filtered_df.groupby(group_cols).agg({
        'revenue': 'sum',
        'expenses': 'sum',
        'profit': 'sum'
    }).reset_index()
    
    # 1. График временного ряда (доходы и расходы)
    if chart_type == 'line':
        time_series_fig = go.Figure()
        time_series_fig.add_trace(go.Scatter(
            x=aggregated[period_col],
            y=aggregated['revenue'],
            mode='lines+markers',
            name='Доходы',
            line=dict(color='#27ae60', width=3)
        ))
        time_series_fig.add_trace(go.Scatter(
            x=aggregated[period_col],
            y=aggregated['expenses'],
            mode='lines+markers',
            name='Расходы',
            line=dict(color='#e74c3c', width=3)
        ))
    else:  # bar chart
        time_series_fig = go.Figure()
        time_series_fig.add_trace(go.Bar(
            x=aggregated[period_col],
            y=aggregated['revenue'],
            name='Доходы',
            marker_color='#27ae60'
        ))
        time_series_fig.add_trace(go.Bar(
            x=aggregated[period_col],
            y=aggregated['expenses'],
            name='Расходы',
            marker_color='#e74c3c'
        ))
    
    time_series_fig.update_layout(
        title='Динамика доходов и расходов',
        xaxis_title='Период',
        yaxis_title='Сумма ($)',
        hovermode='x unified'
    )
    
    # 2. Круговая диаграмма структуры расходов
    expenses_by_category = filtered_df.groupby('category')['expenses'].sum().reset_index()
    expenses_pie_fig = px.pie(
        expenses_by_category,
        values='expenses',
        names='category',
        title='Структура расходов по категориям',
        hole=0.4
    )
    expenses_pie_fig.update_traces(textposition='inside', textinfo='percent+label')
    
    # 3. Гистограмма распределения прибыли
    profit_hist_fig = px.histogram(
        filtered_df,
        x='profit',
        nbins=20,
        title='Распределение прибыли',
        labels={'profit': 'Прибыль ($)'},
        color_discrete_sequence=['#3498db']
    )
    profit_hist_fig.update_layout(
        xaxis_title='Прибыль ($)',
        yaxis_title='Количество записей'
    )
    
    # 4. График рассеяния: корреляция прибыли и других параметров
    scatter_fig = px.scatter(
        filtered_df,
        x='revenue',
        y='profit',
        size='expenses',
        color='category',
        hover_name='category',
        title='Корреляция: Доходы vs Прибыль',
        labels={'revenue': 'Доходы ($)', 'profit': 'Прибыль ($)'},
        size_max=20
    )
    scatter_fig.update_traces(marker=dict(opacity=0.7))
    
    # 5. Таблица с финансовыми показателями
    table_data = filtered_df.to_dict('records')
    table_columns = [{"name": i, "id": i} for i in filtered_df.columns if i in ['date', 'category', 'revenue', 'expenses', 'profit']]
    
    # 6. Индикаторы (KPI)
    total_revenue = filtered_df['revenue'].sum()
    total_expenses = filtered_df['expenses'].sum()
    total_profit = filtered_df['profit'].sum()
    profit_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0
    
    # Расчет среднемесячного роста
    monthly_growth = 0
    if len(aggregated) > 1:
        monthly_revenue = aggregated['revenue'].pct_change().mean() * 100
        monthly_growth = monthly_revenue
    
    # Создаем индикаторы
    revenue_indicator = [
        html.H4("Общая выручка", style={'color': '#27ae60'}),
        html.H2(f"${total_revenue:,.0f}", style={'color': '#27ae60', 'margin': '10px 0'}),
        html.P(f"{len(filtered_df)} транзакций")
    ]
    
    expenses_indicator = [
        html.H4("Общие расходы", style={'color': '#e74c3c'}),
        html.H2(f"${total_expenses:,.0f}", style={'color': '#e74c3c', 'margin': '10px 0'}),
        html.P(f"{len(filtered_df)} транзакций")
    ]
    
    profit_indicator = [
        html.H4("Общая прибыль", style={'color': '#3498db'}),
        html.H2(f"${total_profit:,.0f}", style={'color': '#3498db', 'margin': '10px 0'}),
        html.P("Чистая прибыль")
    ]
    
    margin_indicator = [
        html.H4("Маржа прибыли", style={'color': '#9b59b6'}),
        html.H2(f"{profit_margin:.1f}%", style={'color': '#9b59b6', 'margin': '10px 0'}),
        html.P("Рентабельность")
    ]
    
    growth_indicator = [
        html.H4("Средний рост", style={'color': '#f39c12'}),
        html.H2(f"{monthly_growth:+.1f}%", style={'color': '#f39c12', 'margin': '10px 0'}),
        html.P("в месяц")
    ]
    
    # Прогресс-бары (нормализованные значения)
    revenue_progress = min(int((total_revenue / 1000000) * 100), 100)
    profit_progress = min(int((total_profit / 300000) * 100), 100)
    margin_progress = min(int((profit_margin / 50) * 100), 100)
    
    return (
        upload_message,
        category_options,
        time_series_fig,
        expenses_pie_fig,
        profit_hist_fig,
        scatter_fig,
        table_data,
        table_columns,
        revenue_indicator,
        expenses_indicator,
        profit_indicator,
        margin_indicator,
        growth_indicator,
        revenue_progress,
        profit_progress,
        margin_progress
    )

if __name__ == '__main__':
    import numpy as np
    app.run(debug=True, port=8050)