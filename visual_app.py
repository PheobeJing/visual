#######################
# Import libraries
import streamlit as st
import pandas as pd
import altair as alt
import plotly.express as px
import os
import json
from datetime import date, time, datetime, timedelta
from streamlit_autorefresh import st_autorefresh
import numpy as np
from photoperiod_tool import run_light_cycle
import pandas as pd
import io
from dotenv import load_dotenv, find_dotenv

from pathlib import Path

load_dotenv(find_dotenv()) 


#######################
# 文件路径
CONFIG_PLC_FILE = "configPLC.json"
CONFIG_485_FILE = "config485.json"
LOG_DIR = Path("./Log")
IMAGE_DIR = "./Image"

def load_config(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_config(config, file_path):
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

#######################

# Page configuration
st.set_page_config(
    page_title="US Population Dashboard",
    page_icon="🏂",
    layout="wide",
    initial_sidebar_state="expanded")

alt.themes.enable("dark")

#######################
# CSS styling
st.markdown("""
<style>

[data-testid="block-container"] {
    padding-left: 2rem;
    padding-right: 2rem;
    padding-top: 1rem;
    padding-bottom: 0rem;
    margin-bottom: -7rem;
}

[data-testid="stVerticalBlock"] {
    padding-left: 0rem;
    padding-right: 0rem;
}

[data-testid="stMetric"] {
    background-color: #393939;
    text-align: center;
    padding: 15px 0;
}

[data-testid="stMetricLabel"] {
  display: flex;
  justify-content: center;
  align-items: center;
}

[data-testid="stMetricDeltaIcon-Up"] {
    position: relative;
    left: 38%;
    -webkit-transform: translateX(-50%);
    -ms-transform: translateX(-50%);
    transform: translateX(-50%);
}

[data-testid="stMetricDeltaIcon-Down"] {
    position: relative;
    left: 38%;
    -webkit-transform: translateX(-50%);
    -ms-transform: translateX(-50%);
    transform: translateX(-50%);
}

</style>
""", unsafe_allow_html=True)


#######################
# Load data
df_reshaped = pd.read_csv('data/us-population-2010-2019-reshaped.csv')




def led_control_block(led_key: str, conf: dict, prefix: str):
    st.subheader(f"{led_key.upper()} 控制")
    led_conf = conf.get(led_key, {"mode":"manual","enable":False,"start_hour":20,"stop_hour":0})

    # 单选框选择模式
    mode = st.radio("模式", ["auto", "manual"], index=0 if led_conf.get("mode")=="auto" else 1,
                    key=f"{prefix}_{led_key}_mode")
    
    if mode == "auto":
        # auto_schedule = load_auto_schedule()
        # if led_key in auto_schedule:
        #     start, stop = auto_schedule[led_key]
        #     stop_display = 24 if stop == 0 else stop
        #     st.info(f"AI 自动模式 —— 今日开启：{start}:00，关闭：{stop_display}:00")
        # else:
            st.warning("自动配置未找到，切换到手动模式")
            mode = "manual"

    if mode == "manual":
        enable = st.checkbox("开关", value=led_conf.get("enable", False), key=f"{prefix}_{led_key}_enable")
        start = st.number_input("开启时间(小时)", 0, 23, value=led_conf.get("start_hour", 20), key=f"{prefix}_{led_key}_start")
        stop = st.number_input("关闭时间(小时)", 0, 23, value=led_conf.get("stop_hour", 8), key=f"{prefix}_{led_key}_stop")
    else:
        enable = True  # auto 默认开启

    # 保存配置
    conf[led_key] = {"mode": mode, "enable": enable, "start_hour": start, "stop_hour": stop}



#######################
# Sidebar
with st.sidebar:

    st.title('🏂 US Population Dashboard')
    
    year_list = list(df_reshaped.year.unique())[::-1]
    
    selected_year = st.selectbox('Select a year', year_list)
    df_selected_year = df_reshaped[df_reshaped.year == selected_year]
    df_selected_year_sorted = df_selected_year.sort_values(by="population", ascending=False)

    color_theme_list = ['blues', 'cividis', 'greens', 'inferno', 'magma', 'plasma', 'reds', 'rainbow', 'turbo', 'viridis']
    selected_color_theme = st.selectbox('Select a color theme', color_theme_list)


    st.header("设备控制")

    # 加载配置
    config_plc = load_config(CONFIG_PLC_FILE)
    config_485 = load_config(CONFIG_485_FILE)

    # 初始化 PLC 设备默认值
    device_config_plc = {
        "uv": config_plc.get("uv", {"enable": False, "start_hour": 3, "stop_hour": 6}),
        "water_pump": config_plc.get("water_pump", {"enable": False, "interval_minutes": 20, "duration_seconds": 60}),
        "water_spray": config_plc.get("water_spray", {"enable": False, "interval_minutes": 30, "duration_seconds": 600}),
        "top_led": config_plc.get("top_led", {"mode": "auto", "enable": True, "start_hour": 20, "stop_hour": 0}),
        "mid_led": config_plc.get("mid_led", {"mode": "auto", "enable": True, "start_hour": 20, "stop_hour": 0}),
        "bot_led": config_plc.get("bot_led", {"mode": "auto", "enable": True, "start_hour": 20, "stop_hour": 0})
    }

    # PLC 控制
    with st.expander("UV 灯", expanded=False):
        device_config_plc["uv"]["enable"] = st.checkbox("开启 UV 灯", value=device_config_plc["uv"]["enable"], key="uv_enable")
        device_config_plc["uv"]["start_hour"] = st.slider("开始时间", 0, 23, device_config_plc["uv"]["start_hour"], key="uv_start")
        device_config_plc["uv"]["stop_hour"] = st.slider("结束时间", 0, 23, device_config_plc["uv"]["stop_hour"], key="uv_stop")

    with st.expander("水泵", expanded=False):
        device_config_plc["water_pump"]["enable"] = st.checkbox("开启水泵", value=device_config_plc["water_pump"]["enable"], key="pump_enable")
        device_config_plc["water_pump"]["interval_minutes"] = st.slider("间隔 (分钟)", 1, 120, device_config_plc["water_pump"]["interval_minutes"], key="pump_interval")
        device_config_plc["water_pump"]["duration_seconds"] = st.slider("持续时间 (秒)", 1, 300, device_config_plc["water_pump"]["duration_seconds"], key="pump_duration")

    with st.expander("喷雾", expanded=False):
        device_config_plc["water_spray"]["enable"] = st.checkbox("开启喷雾", value=device_config_plc["water_spray"]["enable"], key="spray_enable")
        device_config_plc["water_spray"]["interval_minutes"] = st.slider("间隔 (分钟)", 1, 120, device_config_plc["water_spray"]["interval_minutes"], key="spray_interval")
        device_config_plc["water_spray"]["duration_seconds"] = st.slider("持续时间 (秒)", 1, 300, device_config_plc["water_spray"]["duration_seconds"], key="spray_duration")

    with st.expander("LED 灯", expanded=False):
        for led in ["top_led", "mid_led", "bot_led"]:
            st.subheader(f"{led.replace('_',' ').title()}")
            device_config_plc[led]["enable"] = st.checkbox("开启", value=device_config_plc[led]["enable"], key=f"{led}_enable")
            device_config_plc[led]["mode"] = st.selectbox("模式", ["auto","manual"], index=0 if device_config_plc[led]["mode"]=="auto" else 1, key=f"{led}_mode")
            device_config_plc[led]["start_hour"] = st.slider("开始时间", 0, 23, device_config_plc[led]["start_hour"], key=f"{led}_start")
            device_config_plc[led]["stop_hour"] = st.slider("结束时间", 0, 23, device_config_plc[led]["stop_hour"], key=f"{led}_stop")

    # 保存 PLC 配置
    save_config(device_config_plc, CONFIG_PLC_FILE)

    # 485 LED 控制
    device_config_485 = config_485
    with st.expander("485 LED 灯", expanded=False):
        for led in ["top_led2","top_led3","bot_led2","bot_led3","under_led1","under_led2","under_led3","under_led4"]:
            st.subheader(f"{led.replace('_',' ').title()}")
            device_config_485[led]["enable"] = st.checkbox("开启", value=device_config_485.get(led, {}).get("enable", True), key=f"{led}_enable")
            device_config_485[led]["mode"] = st.selectbox("模式", ["auto","manual"], index=0 if device_config_485.get(led, {}).get("mode","auto")=="auto" else 1, key=f"{led}_mode")
            device_config_485[led]["start_hour"] = st.slider("开始时间", 0, 23, device_config_485.get(led, {}).get("start_hour", 20), key=f"{led}_start")
            device_config_485[led]["stop_hour"] = st.slider("结束时间", 0, 23, device_config_485.get(led, {}).get("stop_hour", 0), key=f"{led}_stop")

    # 保存 485 配置
    save_config(device_config_485, CONFIG_485_FILE)



#######################
# Plots

# Heatmap
def make_heatmap(input_df, input_y, input_x, input_color, input_color_theme):
    heatmap = alt.Chart(input_df).mark_rect().encode(
            y=alt.Y(f'{input_y}:O', axis=alt.Axis(title="Year", titleFontSize=18, titlePadding=15, titleFontWeight=900, labelAngle=0)),
            x=alt.X(f'{input_x}:O', axis=alt.Axis(title="", titleFontSize=18, titlePadding=15, titleFontWeight=900)),
            color=alt.Color(f'max({input_color}):Q',
                             legend=None,
                             scale=alt.Scale(scheme=input_color_theme)),
            stroke=alt.value('black'),
            strokeWidth=alt.value(0.25),
        ).properties(width=900
        ).configure_axis(
        labelFontSize=12,
        titleFontSize=12
        ) 
    # height=300
    return heatmap

# Choropleth map
def show_image(image_path):
    """
    image_path: 图片文件路径，比如 'images/us_population_2023.png'
    """
    st.image(image_path, caption="US Population Map", use_column_width=True)

REFRESH_INTERVAL = 6000          # 秒

# ---------- 1. 自动刷新 ----------
st_autorefresh(interval=REFRESH_INTERVAL * 1000, key="auto")
# ---------- 2. 取最近 N 天数据 ----------
@st.cache_data(ttl=REFRESH_INTERVAL)
def load_recent_data(days=3):
    all_data = []
    today = date(2025, 11, 12)               # 调试用固定日期
    start_date = today - timedelta(days=days-1)
    for i in range(days):
        d = start_date + timedelta(days=i)
        file_path = LOG_DIR / f"log{d.strftime('%Y-%m-%d')}.csv"
        if file_path.exists():
            df = pd.read_csv(file_path)
            # 清理
            df.columns = df.columns.str.strip().str.replace(r'[\r\n]+', '', regex=True)
            df = df.loc[:, df.columns != '']
            df = df.dropna(axis=1, how='all')
            df['DateTime'] = pd.to_datetime(df['DateTime'], errors='coerce')
            for col in ["Temperature", "Humidity", "CO2", "pH", "EC"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            df.set_index('DateTime', inplace=True)
            df.replace(-1, np.nan, inplace=True)
            all_data.append(df)
    if all_data:
        return pd.concat(all_data).sort_index()
    return pd.DataFrame()

df_all = load_recent_data(3)
if df_all.empty:
    st.warning("暂无数据")
    st.stop()

# ---------- 3. 取最新一行 ----------
latest = df_all.tail(1).iloc[0]


# ---------- 3. 单行流动进度条 ----------
def slim_flow(label, val, v_min, v_max, color_list):
    ratio = max(0, min(1, (val - v_min)/(v_max - v_min)))
    pct   = f"{ratio*100:.1f}%"
    # 把颜色列表拼成 200% 宽度的渐变，用来滚动
    gradient = ",".join(color_list)
    html = f"""
    <style>
    @keyframes flow-{label} {{
        0%   {{ background-position:  100% 0; }}
        100% {{ background-position:    0% 0; }}
    }}
    .bar-{label} {{
        height: 4px;
        width: {ratio*100:.2f}%;
        background: linear-gradient(90deg, {gradient});
        background-size: 200% 100%;
        animation: flow-{label} 2.5s linear infinite;
        border-radius: 2px;
    }}
    </style>
    <div style="display:flex;align-items:center;margin-bottom:8px;">
        <span style="width:60px;font-size:13px;">{label}</span>
        <span style="width:50px;font-size:12px;color:#666;">{val:.1f}</span>
        <div style="flex:1;background:#f1f1f1;height:4px;border-radius:2px;">
            <div class="bar-{label}"></div>
        </div>
        <span style="width:40px;font-size:12px;color:#666;text-align:right;">{pct}</span>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)




# Donut chart
def make_donut(input_response, input_text, input_color):
  if input_color == 'blue':
      chart_color = ['#29b5e8', '#155F7A']
  if input_color == 'green':
      chart_color = ['#27AE60', '#12783D']
  if input_color == 'orange':
      chart_color = ['#F39C12', '#875A12']
  if input_color == 'red':
      chart_color = ['#E74C3C', '#781F16']
    
  source = pd.DataFrame({
      "Topic": ['', input_text],
      "% value": [100-input_response, input_response]
  })
  source_bg = pd.DataFrame({
      "Topic": ['', input_text],
      "% value": [100, 0]
  })
    
  plot = alt.Chart(source).mark_arc(innerRadius=45, cornerRadius=25).encode(
      theta="% value",
      color= alt.Color("Topic:N",
                      scale=alt.Scale(
                          #domain=['A', 'B'],
                          domain=[input_text, ''],
                          # range=['#29b5e8', '#155F7A']),  # 31333F
                          range=chart_color),
                      legend=None),
  ).properties(width=130, height=130)
    
  text = plot.mark_text(align='center', color="#29b5e8", font="Lato", fontSize=32, fontWeight=700, fontStyle="italic").encode(text=alt.value(f'{input_response} %'))
  plot_bg = alt.Chart(source_bg).mark_arc(innerRadius=45, cornerRadius=20).encode(
      theta="% value",
      color= alt.Color("Topic:N",
                      scale=alt.Scale(
                          # domain=['A', 'B'],
                          domain=[input_text, ''],
                          range=chart_color),  # 31333F
                      legend=None),
  ).properties(width=130, height=130)
  return plot_bg + plot + text

# Convert population to text 
def format_number(num):
    if num > 1000000:
        if not num % 1000000:
            return f'{num // 1000000} M'
        return f'{round(num / 1000000, 1)} M'
    return f'{num // 1000} K'

# Calculation year-over-year population migrations
def calculate_population_difference(input_df, input_year):
  selected_year_data = input_df[input_df['year'] == input_year].reset_index()
  previous_year_data = input_df[input_df['year'] == input_year - 1].reset_index()
  selected_year_data['population_difference'] = selected_year_data.population.sub(previous_year_data.population, fill_value=0)
  return pd.concat([selected_year_data.states, selected_year_data.id, selected_year_data.population, selected_year_data.population_difference], axis=1).sort_values(by="population_difference", ascending=False)


#######################
# Dashboard Main Panel
col = st.columns((1.5, 4.5, 2), gap='medium')

with col[0]:
    st.markdown('#### Gains/Losses')

    df_population_difference_sorted = calculate_population_difference(df_reshaped, selected_year)

    if selected_year > 2010:
        first_state_name = df_population_difference_sorted.states.iloc[0]
        first_state_population = format_number(df_population_difference_sorted.population.iloc[0])
        first_state_delta = format_number(df_population_difference_sorted.population_difference.iloc[0])
    else:
        first_state_name = '-'
        first_state_population = '-'
        first_state_delta = ''
    st.metric(label=first_state_name, value=first_state_population, delta=first_state_delta)

    if selected_year > 2010:
        last_state_name = df_population_difference_sorted.states.iloc[-1]
        last_state_population = format_number(df_population_difference_sorted.population.iloc[-1])   
        last_state_delta = format_number(df_population_difference_sorted.population_difference.iloc[-1])   
    else:
        last_state_name = '-'
        last_state_population = '-'
        last_state_delta = ''
    st.metric(label=last_state_name, value=last_state_population, delta=last_state_delta)

    
    st.markdown('#### States Migration')

    if selected_year > 2010:
        # Filter states with population difference > 50000
        # df_greater_50000 = df_population_difference_sorted[df_population_difference_sorted.population_difference_absolute > 50000]
        df_greater_50000 = df_population_difference_sorted[df_population_difference_sorted.population_difference > 50000]
        df_less_50000 = df_population_difference_sorted[df_population_difference_sorted.population_difference < -50000]
        
        # % of States with population difference > 50000
        states_migration_greater = round((len(df_greater_50000)/df_population_difference_sorted.states.nunique())*100)
        states_migration_less = round((len(df_less_50000)/df_population_difference_sorted.states.nunique())*100)
        donut_chart_greater = make_donut(states_migration_greater, 'Inbound Migration', 'green')
        donut_chart_less = make_donut(states_migration_less, 'Outbound Migration', 'red')
    else:
        states_migration_greater = 0
        states_migration_less = 0
        donut_chart_greater = make_donut(states_migration_greater, 'Inbound Migration', 'green')
        donut_chart_less = make_donut(states_migration_less, 'Outbound Migration', 'red')

    migrations_col = st.columns((0.2, 1, 0.2))
    with migrations_col[1]:
        st.write('Inbound')
        st.altair_chart(donut_chart_greater)
        st.write('Outbound')
        st.altair_chart(donut_chart_less)

with col[1]:
    st.markdown('#### Total Population')
    
    # 显示静态地图图片
    st.image("sample.jpg", caption="US Population Map", use_column_width=True)

    st.markdown('#### ⚙️ 光周期参数设置')
    
    with st.form("light_params_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("##### 基础参数")
            days = st.number_input("栽培总天数", min_value=1, max_value=365, value=30, help="整个生长周期的总天数")
            h_ave = st.number_input("平均光照时长 (h)", min_value=0.0, max_value=24.0, value=14.0, step=0.5, help="目标平均每日光照时间")
        
        with col2:
            st.markdown("##### 光照范围")
            h_min = st.number_input("最短光照 (h)", min_value=0.0, max_value=24.0, value=12.0, step=0.5, help="允许的最短每日光照时间")
            h_max = st.number_input("最长光照 (h)", min_value=0.0, max_value=24.0, value=18.0, step=0.5, help="允许的最长每日光照时间")
        
        submitted = st.form_submit_button("🚀 生成AI光周期策略", use_container_width=True)
    
    if submitted:
        if not (0 <= h_min <= h_ave <= h_max <= 24):
            st.error("❌ 参数错误：必须满足 0 ≤ 最短光照 ≤ 平均光照 ≤ 最长光照 ≤ 24")
        else:
            with st.spinner("🤖 AI正在为您生成最优光周期策略..."):
                answer_md = run_light_cycle(days, h_min, h_max, h_ave)
            
            st.markdown("#### 📋 AI生成的光周期策略")
            st.markdown(answer_md)
            
            # Excel 下载功能
            lines = answer_md.splitlines()
            table_start = None
            for i, line in enumerate(lines):
                if "| 天数" in line or "| Day" in line:
                    table_start = i
                    break
            
            if table_start:
                try:
                    # 解析Markdown表格
                    table_lines = lines[table_start:]
                    clean_lines = []
                    for line in table_lines:
                        if line.strip() and '|---' not in line:
                            clean_lines.append(line)
                    
                    if clean_lines:
                        df = pd.read_csv(io.StringIO("\n".join(clean_lines)), sep="|", skipinitialspace=True)
                        df = df.dropna(axis=1, how="all").iloc[1:].reset_index(drop=True)
                        
                        # 清理列名
                        df.columns = [col.strip() for col in df.columns]
                        
                        excel = io.BytesIO()
                        with pd.ExcelWriter(excel, engine="openpyxl") as writer:
                            df.to_excel(writer, index=False, sheet_name="光周期计划")
                            
                            # 添加摘要工作表
                            summary_data = {
                                '参数': ['总天数', '最短光照', '最长光照', '平均光照', '植物类型', '光照强度'],
                                '数值': [days, f'{h_min}h', f'{h_max}h', f'{h_ave}h', plant_type, light_intensity]
                            }
                            pd.DataFrame(summary_data).to_excel(writer, index=False, sheet_name="参数摘要")
                        
                        excel.seek(0)
                        
                        st.download_button(
                            label="📥 下载Excel详细计划表",
                            data=excel,
                            file_name=f"光周期计划_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
                except Exception as e:
                    st.warning(f"⚠️ 表格解析遇到问题，但策略已生成完成。错误详情: {str(e)}")

    



    

with col[2]:
    st.markdown(f"**实时监测**  `{latest.name.strftime('%Y-%m-%d %H:%M:%S')}`")
    slim_flow("温度", latest["Temperature"], 0, 50, ["#ff4b4b","#ffa500","#ffff00","#ff4b4b"])
    slim_flow("湿度", latest["Humidity"],   0, 100, ["#00b4ff","#4bff7a","#00b4ff"])
    slim_flow("CO₂",  latest["CO2"],       0, 1000, ["#70a1ff","#ff6b6b","#70a1ff"])

    st.markdown("---")
    days_option = st.radio(
        "选择时间范围",
        [1, 3, 7],
        horizontal=True,
        format_func=lambda x: f"最近{x}天"
    )

    df = load_recent_data(days_option)
    if df.empty:
        st.warning("未找到对应数据")
        st.stop()

    # -------------- pH & EC 折线 --------------
    cols = [c for c in ["pH", "EC"] if c in df.columns]
    if cols:
        st.line_chart(df[cols], height=280)
    else:
        st.info("暂无 pH / EC 数据")
    
    with st.expander('About', expanded=True):
        st.write('''
            - Data: [U.S. Census Bureau](https://www.census.gov/data/datasets/time-series/demo/popest/2010s-state-total.html).
            - :orange[**Gains/Losses**]: states with high inbound/ outbound migration for selected year
            - :orange[**States Migration**]: percentage of states with annual inbound/ outbound migration > 50,000
            ''')
    
st.set_page_config(page_title="AI 光周期助手", page_icon="🌱")

