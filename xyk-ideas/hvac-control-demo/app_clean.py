"""
HVAC Control Strategy Dynamic Visualization Dashboard - NO JAVASCRIPT VERSION
动态HVAC控制策略可视化看板 - 纯服务器端音效版
"""

import dash
from dash import dcc, html, Input, Output, State, no_update
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import numpy as np
import json
from hvac_simulator import HVACControlSimulator, ActionType, DeviceType
from audio_generator import generate_action_sound

# 样式规范 - 符合CLAUDE.md
COLORS = [
    'rgba(72,121,128,0.7)',   # 深蓝绿 - primary scientific color
    'rgba(216,81,23,0.7)',    # 橙色 - accent/warning
    'rgba(4,115,192,0.7)',    # 蓝色 - data/results
    'rgba(179,53,56,0.7)',    # 红色 - critical/baseline
    'rgba(104,57,132,0.7)',   # 紫色 - secondary data
    'rgba(36,113,158,0.7)',   # 深蓝 - comparison
    'rgba(125,193,191,0.7)',  # 青绿 - positive results
    'rgba(216,132,142,0.7)'   # 粉色 - supplementary
]

# 动作颜色映射
ACTION_COLORS = {
    # ASHP
    'ASHP制冷模式': 'rgba(4,115,192,0.3)',
    'ASHP制热模式': 'rgba(216,81,23,0.3)',
    'ASHP除湿模式': 'rgba(125,193,191,0.3)',
    'ASHP设定温度上升': 'rgba(216,132,142,0.3)',
    'ASHP设定温度下降': 'rgba(72,121,128,0.3)',
    'ASHP风速上升': 'rgba(104,57,132,0.2)',
    'ASHP风速下降': 'rgba(36,113,158,0.2)',
    # ERV
    'ERV风速上升': 'rgba(125,193,191,0.2)',
    'ERV风速下降': 'rgba(104,57,132,0.2)',
}

INSTANT_ACTION_COLOR = 'rgba(0,0,0,0.5)'  # 瞬时动作竖线颜色

FONT_FAMILY = "Microsoft YaHei, Arial, sans-serif"

# 全局变量
simulator = HVACControlSimulator(timestep_minutes=5)

# 初始化Dash应用
app = dash.Dash(__name__)
app.title = "HVAC控制策略动态监控"


def create_combined_figure(history, actions, window_start=0, window_end=90):
    """创建温湿度和能耗电费的组合图表 - 共享X轴"""
    if not history:
        # 返回空图表但有提示
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.12,
            subplot_titles=("温湿度监控 - 等待初始化", "能耗电费监控 - 等待初始化"),
            specs=[[{"secondary_y": True}], [{"secondary_y": True}]]
        )
        fig.update_layout(height=1100, plot_bgcolor='rgba(255,255,255,1)')
        return fig

    # 获取显示窗口的数据
    display_history = history[window_start:window_end]

    if not display_history:
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.12,
            subplot_titles=("温湿度监控 - 无数据", "能耗电费监控 - 无数据"),
            specs=[[{"secondary_y": True}], [{"secondary_y": True}]]
        )
        fig.update_layout(height=1100)
        return fig

    # 提取数据
    timestamps = [s.timestamp for s in display_history]
    temperatures = [s.temperature for s in display_history]
    humidities = [s.humidity for s in display_history]
    total_powers = [s.total_power for s in display_history]
    costs = [s.cost for s in display_history]
    cumulative_cost = np.cumsum(costs)

    # 生成预测数据（从最后一个点向前延伸到未来）
    # 预测线应该从当前时间点延伸到未来5个时间步
    timestep_minutes = 5
    if len(display_history) >= 1:
        last_state = display_history[-1]
        last_ts = last_state.timestamp

        # 预测时间戳（当前时间 + 5个未来时间步）
        pred_timestamps = [last_ts + timedelta(minutes=timestep_minutes * i) for i in range(6)]

        # 预测值从当前实际值开始，延伸到未来预测值
        temp_preds = [last_state.temperature]
        hum_preds = [last_state.humidity]
        power_preds = [last_state.total_power]
        cost_preds = [cumulative_cost[-1] if len(cumulative_cost) > 0 else 0]

        # 使用线性趋势生成预测
        if len(display_history) >= 3:
            # 温度趋势
            recent_temps = [s.temperature for s in display_history[-3:]]
            temp_trend = np.mean(np.diff(recent_temps))
            # 湿度趋势
            recent_hums = [s.humidity for s in display_history[-3:]]
            hum_trend = np.mean(np.diff(recent_hums))
            # 功率趋势
            recent_powers = [s.total_power for s in display_history[-3:]]
            power_trend = np.mean(np.diff(recent_powers))
            # 累计电费趋势
            if len(cumulative_cost) >= 3:
                cost_trend = np.mean(np.diff(cumulative_cost[-3:]))
            else:
                cost_trend = costs[-1] if costs else 0
        else:
            temp_trend = 0
            hum_trend = 0
            power_trend = 0
            cost_trend = costs[-1] if costs else 0

        # 生成5步预测
        for i in range(1, 6):
            temp_preds.append(np.clip(last_state.temperature + temp_trend * i, 18.0, 28.0))
            hum_preds.append(np.clip(last_state.humidity + hum_trend * i, 40.0, 80.0))
            power_preds.append(max(0, last_state.total_power + power_trend * i))
            cost_preds.append(max(0, cost_preds[0] + cost_trend * i))
    else:
        pred_timestamps = timestamps
        temp_preds = temperatures
        hum_preds = humidities
        power_preds = total_powers
        cost_preds = list(cumulative_cost)

    # 创建组合图表
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        subplot_titles=(
            '温湿度 (上) | 能耗电费 (下)',
            ''
        ),
        specs=[[{"secondary_y": True}], [{"secondary_y": True}]]
    )

    # ========== 第一行：温湿度图表 ==========
    # 实测温度
    fig.add_trace(
        go.Scatter(
            x=timestamps, y=temperatures, name="实测温度",
            mode='lines', line=dict(color=COLORS[3], width=3),
            legendgroup='temp', showlegend=True
        ),
        row=1, col=1, secondary_y=False
    )

    # 预测温度（延伸到未来）
    fig.add_trace(
        go.Scatter(
            x=pred_timestamps, y=temp_preds, name="预测温度",
            mode='lines', line=dict(color=COLORS[3], width=2, dash='dash'),
            opacity=0.6, legendgroup='temp', showlegend=True
        ),
        row=1, col=1, secondary_y=False
    )

    # 实测湿度
    fig.add_trace(
        go.Scatter(
            x=timestamps, y=humidities, name="实测湿度",
            mode='lines', line=dict(color=COLORS[0], width=3),
            legendgroup='hum', showlegend=True
        ),
        row=1, col=1, secondary_y=True
    )

    # 预测湿度（延伸到未来）
    fig.add_trace(
        go.Scatter(
            x=pred_timestamps, y=hum_preds, name="预测湿度",
            mode='lines', line=dict(color=COLORS[0], width=2, dash='dash'),
            opacity=0.6, legendgroup='hum', showlegend=True
        ),
        row=1, col=1, secondary_y=True
    )

    # ========== 第二行：能耗电费图表 ==========
    # 总功率
    fig.add_trace(
        go.Scatter(
            x=timestamps, y=total_powers, name="实测功率",
            mode='lines', line=dict(color=COLORS[1], width=3),
            fill='tozeroy', fillcolor='rgba(216,81,23,0.2)',
            legendgroup='power', showlegend=True
        ),
        row=2, col=1, secondary_y=False
    )

    # 预测功率（延伸到未来）
    fig.add_trace(
        go.Scatter(
            x=pred_timestamps, y=power_preds, name="预测功率",
            mode='lines', line=dict(color=COLORS[1], width=2, dash='dash'),
            opacity=0.6, legendgroup='power', showlegend=True
        ),
        row=2, col=1, secondary_y=False
    )

    # 累计电费
    fig.add_trace(
        go.Scatter(
            x=timestamps, y=cumulative_cost, name="实测电费",
            mode='lines', line=dict(color=COLORS[4], width=3),
            legendgroup='cost', showlegend=True
        ),
        row=2, col=1, secondary_y=True
    )

    # 预测电费（延伸到未来）
    fig.add_trace(
        go.Scatter(
            x=pred_timestamps, y=cost_preds, name="预测电费",
            mode='lines', line=dict(color=COLORS[4], width=2, dash='dash'),
            opacity=0.6, legendgroup='cost', showlegend=True
        ),
        row=2, col=1, secondary_y=True
    )

    # ========== 添加动作序列标注（在两个图表上） ==========
    # 性能优化：只显示时间窗口内的动作，限制最大数量
    if timestamps and actions:
        time_start = timestamps[0]
        time_end = timestamps[-1]

        # 筛选时间窗口内的动作
        window_actions = [a for a in actions if time_start <= a.timestamp <= time_end]

        # 限制最大动作数量以提高性能
        max_actions = 30
        if len(window_actions) > max_actions:
            window_actions = window_actions[-max_actions:]

        for action in window_actions:
            try:
                if action.is_instant:
                    # 瞬时动作 - 竖线（在两个图表上都显示）
                    fig.add_vline(
                        x=action.timestamp, row=1, col=1,
                        line_width=2, line_dash="solid", line_color=INSTANT_ACTION_COLOR
                    )
                    fig.add_vline(
                        x=action.timestamp, row=2, col=1,
                        line_width=2, line_dash="solid", line_color=INSTANT_ACTION_COLOR
                    )
                else:
                    # 持续动作 - 覆盖区域（在两个图表上都显示）
                    action_name = action.action.value
                    color = ACTION_COLORS.get(action_name, 'rgba(200,200,200,0.2)')
                    end_time = action.timestamp + timedelta(minutes=action.duration)
                    # 温湿度图
                    fig.add_vrect(
                        x0=action.timestamp, x1=min(end_time, time_end),
                        fillcolor=color, layer="below", line_width=0, row=1, col=1
                    )
                    # 能耗电费图
                    fig.add_vrect(
                        x0=action.timestamp, x1=min(end_time, time_end),
                        fillcolor=color, layer="below", line_width=0, row=2, col=1
                    )
            except Exception as e:
                continue

    # ========== 标注峰谷电价时段（仅在能耗图） ==========
    if timestamps:
        current_hour = timestamps[0].hour
        segment_start = timestamps[0]

        for i, ts in enumerate(timestamps):
            if ts.hour != current_hour or i == len(timestamps) - 1:
                segment_end = ts if i == len(timestamps) - 1 else timestamps[i-1]
                if 8 <= current_hour < 22:
                    fig.add_vrect(
                        x0=segment_start, x1=segment_end,
                        fillcolor='rgba(255,200,200,0.15)', layer="below",
                        line_width=0, row=2, col=1
                    )
                segment_start = ts
                current_hour = ts.hour

    # ========== 布局设置 ==========
    fig.update_layout(
        height=900, width=1100,
        margin=dict(t=80, b=100, l=100, r=50),
        plot_bgcolor='rgba(255,255,255,1)',
        paper_bgcolor='rgba(255,255,255,1)',
        font=dict(family=FONT_FAMILY, size=18),
        hovermode='x unified',
        legend=dict(orientation="h", yanchor="top", y=-0.08, xanchor="center", x=0.5, font=dict(size=14)),
        showlegend=True
    )

    # 更新子图标题字体大小
    for annotation in fig['layout']['annotations']:
        if annotation['text']:  # 只更新非空标题
            annotation['font'] = dict(size=24, color='#2E2E2E', family=FONT_FAMILY)

    # ========== Y轴设置 ==========
    # 温度轴（第一行左侧）
    fig.update_yaxes(
        title_text="温度 (°C)", title_font=dict(size=27, color='#2E2E2E'),
        showline=True, linewidth=2, linecolor='#000000', mirror=True,
        ticks='outside', tickwidth=2, tickcolor='#000000',
        showgrid=True, gridwidth=1, gridcolor='rgba(0,0,0,0.1)',
        row=1, col=1, secondary_y=False
    )

    # 湿度轴（第一行右侧）
    fig.update_yaxes(
        title_text="湿度 (%)", title_font=dict(size=27, color='#2E2E2E'),
        showline=True, linewidth=2, linecolor='#000000', mirror=True,
        ticks='outside', tickwidth=2, tickcolor='#000000', showgrid=False,
        row=1, col=1, secondary_y=True
    )

    # 功率轴（第二行左侧）
    fig.update_yaxes(
        title_text="功率 (kW)", title_font=dict(size=27, color='#2E2E2E'),
        showline=True, linewidth=2, linecolor='#000000', mirror=True,
        ticks='outside', tickwidth=2, tickcolor='#000000',
        showgrid=True, gridwidth=1, gridcolor='rgba(0,0,0,0.1)',
        row=2, col=1, secondary_y=False
    )

    # 电费轴（第二行右侧）
    fig.update_yaxes(
        title_text="累计电费 (元)", title_font=dict(size=27, color='#2E2E2E'),
        showline=True, linewidth=2, linecolor='#000000', mirror=True,
        ticks='outside', tickwidth=2, tickcolor='#000000', showgrid=False,
        row=2, col=1, secondary_y=True
    )

    # ========== X轴设置 ==========
    fig.update_xaxes(
        title_text="时间", title_font=dict(size=27, color='#2E2E2E'),
        showline=True, linewidth=2, linecolor='#000000', mirror=True,
        ticks='outside', tickwidth=2, tickcolor='#000000',
        showgrid=True, gridwidth=1, gridcolor='rgba(0,0,0,0.1)',
        row=2, col=1
    )

    return fig


# 应用布局
app.layout = html.Div([
    # 标题
    html.H1(
        "HVAC控制策略动态监控看板",
        style={
            'textAlign': 'center',
            'color': '#2E2E2E',
            'fontFamily': FONT_FAMILY,
            'padding': '15px',
            'fontSize': '36px',
            'margin': '0'
        }
    ),

    # 状态面板
    html.Div([
        html.Div([
            html.H3("实行策略", style={'margin': '0', 'fontSize': '18px'}),
            html.P(id='strategy-display', style={'fontSize': '22px', 'fontWeight': 'bold', 'margin': '5px 0'})
        ], style={'flex': '1', 'textAlign': 'center', 'padding': '12px', 'backgroundColor': '#f0f8ff', 'borderRadius': '6px', 'margin': '3px'}),

        html.Div([
            html.H3("当前状况", style={'margin': '0', 'fontSize': '18px'}),
            html.P(id='status-display', style={'fontSize': '22px', 'fontWeight': 'bold', 'margin': '5px 0'})
        ], style={'flex': '1', 'textAlign': 'center', 'padding': '12px', 'backgroundColor': '#f0fff0', 'borderRadius': '6px', 'margin': '3px'}),

        html.Div([
            html.H3("舒适度评分", style={'margin': '0', 'fontSize': '18px'}),
            html.P(id='comfort-display', style={'fontSize': '22px', 'fontWeight': 'bold', 'margin': '5px 0'})
        ], style={'flex': '1', 'textAlign': 'center', 'padding': '12px', 'backgroundColor': '#fff8f0', 'borderRadius': '6px', 'margin': '3px'}),
    ], style={'display': 'flex', 'justifyContent': 'space-around', 'margin': '10px 20px'}),

    # 播放控制
    html.Div([
        html.Button('▶️ 播放', id='play-button', n_clicks=0, style={'margin': '3px', 'padding': '10px 20px', 'fontSize': '18px'}),
        html.Button('⏸️ 暂停', id='pause-button', n_clicks=0, style={'margin': '3px', 'padding': '10px 20px', 'fontSize': '18px'}),
        html.Button('🔄 重置', id='reset-button', n_clicks=0, style={'margin': '3px', 'padding': '10px 20px', 'fontSize': '18px'}),
        html.Button('🔊 音效', id='mute-button', n_clicks=0, style={'margin': '3px', 'padding': '10px 20px', 'fontSize': '18px', 'backgroundColor': '#4CAF50', 'color': 'white', 'border': 'none', 'borderRadius': '4px'}),
        html.Label('播放速度:', style={'margin': '3px 3px 3px 15px', 'fontSize': '18px'}),
        dcc.Dropdown(
            id='speed-dropdown',
            options=[
                {'label': '0.5x', 'value': 0.5},
                {'label': '1x', 'value': 1},
                {'label': '2x', 'value': 2},
                {'label': '5x', 'value': 5},
            ],
            value=1,
            style={'width': '100px', 'display': 'inline-block', 'margin': '3px', 'fontSize': '16px'}
        ),
        html.Span(id='time-display', style={'margin': '3px 15px', 'fontSize': '18px', 'fontWeight': 'bold'})
    ], style={'textAlign': 'center', 'margin': '10px'}),

    # 主内容区域：左边图表 + 右边日志
    html.Div([
        # 左侧：组合图表
        html.Div([
            dcc.Graph(id='combined-graph', style={'margin': '0'})
        ], style={'width': '68%', 'display': 'inline-block', 'verticalAlign': 'top'}),

        # 右侧：动作序列日志
        html.Div([
            html.H3("控制动作日志", style={
                'textAlign': 'center', 'margin': '10px 0',
                'fontSize': '20px', 'color': '#2E2E2E',
                'borderBottom': '2px solid #2E2E2E', 'paddingBottom': '5px'
            }),
            html.Div(id='action-log', style={
                'height': '820px', 'overflowY': 'auto',
                'backgroundColor': '#f8f8f8', 'padding': '10px',
                'borderRadius': '5px', 'fontFamily': 'Consolas, monospace',
                'fontSize': '13px', 'lineHeight': '1.6'
            })
        ], style={
            'width': '30%', 'display': 'inline-block',
            'verticalAlign': 'top', 'padding': '0 10px',
            'marginLeft': '10px'
        })
    ], style={'margin': '10px 20px'}),

    # 定时器 - 每2秒更新一次
    dcc.Interval(
        id='interval-component',
        interval=2000,  # 2秒
        n_intervals=0,
        disabled=True  # 初始禁用
    ),

    # 音频元素 - 服务器端生成音效，不依赖JavaScript
    html.Audio(
        id='action-audio',
        controls=False,  # 隐藏控制栏
        preload='none',  # 不预加载
        autoplay=True,   # 自动播放
        style={'display': 'none'}  # 隐藏元素
    ),

    # 存储数据
    dcc.Store(id='simulation-data', data={'current_step': 0, 'is_playing': False, 'initialized': False}),
    dcc.Store(id='audio-state', data={'muted': False}),
    dcc.Store(id='last-action', data=None),
])


# 使用clientside callback直接修改JavaScript变量
app.clientside_callback(
    """
    function(n_clicks, audio_state) {
        if (!audio_state) {
            audio_state = {muted: false};
        }

        audio_state.muted = !audio_state.muted;
        window.hvacAudioEnabled = !audio_state.muted;

        let buttonText, buttonStyle;
        if (audio_state.muted) {
            buttonText = '🔇 静音';
            buttonStyle = {
                margin: '3px', padding: '10px 20px', fontSize: '18px',
                backgroundColor: '#f44336', color: 'white', border: 'none', borderRadius: '4px'
            };
        } else {
            buttonText = '🔊 音效';
            buttonStyle = {
                margin: '3px', padding: '10px 20px', fontSize: '18px',
                backgroundColor: '#4CAF50', color: 'white', border: 'none', borderRadius: '4px'
            };
        }

        return [audio_state, buttonText, buttonStyle];
    }
    """,
    [Output('audio-state', 'data'),
     Output('mute-button', 'children'),
     Output('mute-button', 'style')],
    [Input('mute-button', 'n_clicks')],
    [State('audio-state', 'data')],
    prevent_initial_call=True
)


# 使用Python callback更新音频元素，播放音效
@app.callback(
    [Output('action-audio', 'src'),
     Output('action-audio', 'n_clicks')],  # 触发播放
    Input('last-action', 'data'),
    prevent_initial_call=True
)
def trigger_audio(last_action_data):
    """触发音效播放 - 生成音频data URL并返回给audio元素"""
    try:
        print(f"[Python Debug] trigger_audio called with: {last_action_data}")

        # 检查输入是否有效
        if last_action_data is None:
            print("[Python Debug] last_action_data is None")
            return dash.no_update, dash.no_update

        # 检查是否为字典类型
        if not isinstance(last_action_data, dict):
            print(f"[Python Debug] last_action_data is not dict: {type(last_action_data)}")
            return dash.no_update, dash.no_update

        # 安全地获取action_name
        action_name = last_action_data.get('action_name')
        if not action_name:
            print("[Python Debug] action_name is empty")
            return dash.no_update, dash.no_update

        # 生成音频data URL
        audio_url = generate_action_sound(action_name)
        if not audio_url:
            print(f"[Python Debug] Failed to generate audio for: {action_name}")
            return dash.no_update, dash.no_update

        print(f"[Python Debug] Generated audio URL for {action_name}: {audio_url[:50]}...")

        # 返回音频URL和一个随机值来触发播放
        # 使用当前时间戳作为n_clicks的值，确保每次都不同从而触发播放
        return audio_url, datetime.now().timestamp()
    except Exception as e:
        print(f"Error in trigger_audio callback: {e}")
        import traceback
        traceback.print_exc()
        return dash.no_update, dash.no_update


@app.callback(
    [Output('interval-component', 'disabled'),
     Output('simulation-data', 'data')],
    [Input('play-button', 'n_clicks'),
     Input('pause-button', 'n_clicks'),
     Input('reset-button', 'n_clicks'),
     Input('speed-dropdown', 'value')],
    [State('simulation-data', 'data')],
    prevent_initial_call=True
)
def control_playback(play_clicks, pause_clicks, reset_clicks, speed, data):
    """控制播放/暂停/重置"""
    global simulator

    ctx = dash.callback_context
    if not ctx.triggered:
        return True, data

    button_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if button_id == 'play-button':
        data['is_playing'] = True
        return False, data
    elif button_id == 'pause-button':
        data['is_playing'] = False
        return True, data
    elif button_id == 'reset-button':
        simulator.reset()
        data['current_step'] = 0
        data['is_playing'] = False
        data['initialized'] = False
        return True, data
    elif button_id == 'speed-dropdown':
        # 速度变化不影响播放状态
        return not data.get('is_playing', False), data

    return True, data


@app.callback(
    Output('last-action', 'data'),
    [Input('interval-component', 'n_intervals')],
    [State('last-action', 'data')],
    prevent_initial_call=True
)
def detect_new_action(n, last_action):
    """检测新动作并返回用于触发音效"""
    global simulator

    try:
        if not simulator.actions:
            return dash.no_update

        current_action = simulator.actions[-1]
        action_data = {
            'action_name': current_action.action.value,
            'timestamp': current_action.timestamp.isoformat(),
            'device': current_action.device.value
        }

        # 检查是否为新动作
        if last_action is None or last_action.get('timestamp') != action_data['timestamp']:
            return action_data

        return dash.no_update
    except Exception as e:
        print(f"Error in detect_new_action: {e}")
        return dash.no_update


@app.callback(
    [Output('combined-graph', 'figure'),
     Output('strategy-display', 'children'),
     Output('status-display', 'children'),
     Output('comfort-display', 'children'),
     Output('time-display', 'children'),
     Output('action-log', 'children'),
     Output('simulation-data', 'data', allow_duplicate=True)],
    [Input('interval-component', 'n_intervals')],  # 只监听interval，避免循环依赖
    [State('simulation-data', 'data')],  # 使用State而不是Input，避免循环触发
    prevent_initial_call='initial_duplicate'  # 允许初始调用但支持重复输出
)
def update_graphs(n, data):
    """更新图表、状态显示和动作日志"""
    global simulator

    try:
        # 确保data是字典
        if data is None:
            data = {'current_step': 0, 'is_playing': False, 'initialized': False}

        # 初始化检查
        if not data.get('initialized', False):
            # 第一次加载，初始化数据
            if not simulator.history:
                simulator.simulate(num_steps=10)
            data['initialized'] = True
            data['current_step'] = simulator.current_step

        # 执行模拟步进（只在播放时）
        if data.get('is_playing', False):
            simulator.step()
            data['current_step'] = simulator.current_step

        # 获取历史数据
        history = simulator.history
        actions = simulator.actions

        # 计算显示窗口（最近90个时间步）
        window_size = 90
        total_steps = len(history)
        window_end = total_steps
        window_start = max(0, window_end - window_size)

        # 创建组合图表
        combined_fig = create_combined_figure(history, actions, window_start, window_end)

        # 获取当前状态
        current_state = history[-1] if history else None

        if current_state:
            strategy = current_state.strategy
            status = current_state.status
            comfort = f"{current_state.comfort_score:.1f} 分"
            time_str = current_state.timestamp.strftime('%Y-%m-%d %H:%M:%S')

            # 状态颜色
            if status == "正常":
                status_color = "green"
            elif status == "预警":
                status_color = "orange"
            else:
                status_color = "red"

            status_display = html.Span(status, style={'color': status_color, 'fontSize': '22px'})
        else:
            strategy = "初始化中"
            status_display = html.Span("未知", style={'color': 'gray', 'fontSize': '22px'})
            comfort = "-- 分"
            time_str = "--"

        # 生成动作日志（显示最近30条）
        if actions:
            recent_actions = actions[-30:]
            log_entries = []
            for action in reversed(recent_actions):
                time_label = action.timestamp.strftime('%H:%M:%S')
                device_label = action.device.value
                action_label = action.action.value

                # 根据动作类型设置样式
                if action.is_instant:
                    style = {'color': '#d32f2f', 'fontWeight': 'bold'}
                    duration_text = "[瞬时]"
                else:
                    style = {'color': '#1976d2'}
                    duration_text = f"[{action.duration:.0f}min]"

                log_entries.append(
                    html.Div([
                        html.Span(f"{time_label} ", style={'color': '#666', 'fontWeight': 'bold'}),
                        html.Span(f"{device_label} ", style={'color': '#2e7d32', 'fontWeight': 'bold'}),
                        html.Span(f"{action_label} ", style=style),
                        html.Span(duration_text, style={'color': '#999', 'fontSize': '11px'})
                    ], style={'marginBottom': '5px', 'paddingBottom': '5px', 'borderBottom': '1px solid #e0e0e0'})
                )
            action_log_content = log_entries
        else:
            action_log_content = html.Div("等待动作序列...", style={'color': '#999', 'textAlign': 'center', 'marginTop': '20px'})

        return (
            combined_fig,
            strategy,
            status_display,
            comfort,
            f"当前时间: {time_str}",
            action_log_content,
            data  # 返回更新后的data
        )
    except Exception as e:
        print(f"Error in update_graphs: {e}")
        import traceback
        traceback.print_exc()
        # 返回默认值以避免应用崩溃
        empty_fig = go.Figure()
        empty_fig.add_annotation(text="数据加载错误", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        return (
            empty_fig,
            "错误",
            html.Span("错误", style={'color': 'red', 'fontSize': '22px'}),
            "-- 分",
            "错误",
            html.Div("数据加载错误", style={'color': 'red', 'textAlign': 'center'}),
            data if data else {'current_step': 0, 'is_playing': False, 'initialized': False}
        )


if __name__ == '__main__':
    print("启动HVAC控制策略动态监控看板（纯服务器端音效版）...")
    print("请在浏览器中访问: http://127.0.0.1:8050/")
    print("\n特性:")
    print("  - 温湿度和能耗电费图表共享X轴")
    print("  - 所有字体放大1.5倍")
    print("  - 更积极的自适应控制策略")
    print("  - 更多控制动作类型")
    print("  - 纯服务器端音效系统（不依赖JavaScript）")
    app.run(debug=True, host='127.0.0.1', port=8050)
