###全版本 现运行
# ------------------- Python 标准库 -------------------
import os
import glob
import json
import csv
import pathlib
# import time
from datetime import date, time, datetime, timedelta
from time import sleep

# ------------------- 第三方库 -------------------
import streamlit as st
import pandas as pd
import numpy as np
from PIL import Image
import plotly.express as px
import matplotlib.pyplot as plt
from matplotlib import dates as mdates
from streamlit_autorefresh import st_autorefresh


from pathlib import Path

from light_agent import calc_photoperiod

# ------------------- 文件路径 -------------------
CONFIG_PLC_FILE = "configPLC.json"
CONFIG_485_FILE = "config485.json"
LOG_DIR = Path("./Log")
IMAGE_DIR = "./Image"

# ------------------- 页面配置 -------------------
st.set_page_config(layout='wide')

# ------------------- CSS 样式 -------------------
st.markdown("""
<style>
body { font-size: 22px !important; }
.stButton>button { font-size: 30px !important; }
.stSelectbox>div>div>select { font-size: 18px !important; }
.stTextInput>div>div>input { font-size: 18px !important; }
.stNumberInput>div>div>input { font-size: 18px !important; }
.stCheckbox>label>div { font-size: 18px !important; }
</style>
""", unsafe_allow_html=True)


AUTO_CONFIG_DIR = pathlib.Path(__file__).with_name("config")  # ./config/
LED_KEYS = [
    "top_led", "mid_led", "bot_led",
    "top_led2", "top_led3", "bot_led2", "bot_led3",
    "under_led1", "under_led2", "under_led3", "under_led4"
]

# ------------------- 数据可视化 -------------------


def load_recent_data(days=3):
    all_data = []
    today = date.today()
    # today = date(2025, 11, 12)
    start_date = today - timedelta(days=days - 1)

    for i in range(days):
        d = start_date + timedelta(days=i)
        file_path = LOG_DIR / f"log{d.strftime('%Y-%m-%d')}.csv"
        if os.path.exists(file_path):
            df = pd.read_csv(file_path)

            # 🔹 清理列名异常符号
            df.columns = df.columns.str.strip()
            df.columns = df.columns.str.replace(r'[\r\n]+', '', regex=True)
            df = df.loc[:, df.columns != '']       # 去掉空列
            df = df.dropna(axis=1, how='all')      # 去掉全空列

            # 🔹 解析时间与数值
            df['DateTime'] = pd.to_datetime(df['DateTime'], errors='coerce')
            for col in ["Temperature", "Humidity", "CO2", "pH", "EC"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

            df.set_index('DateTime', inplace=True)
            df.replace(-1, np.nan, inplace=True)
            all_data.append(df)



    if all_data:
        df_all = pd.concat(all_data).sort_index()
        return df_all[df_all.index >= datetime.now() - timedelta(days=days)]
        # return df_all
    return pd.DataFrame()





# 前面的 load_recent_data() 保持不变
def data_visualization_tab():
    st.title("传感器数据可视化")
    days_option = st.radio("选择时间范围", [1, 3, 7], horizontal=True,
                          format_func=lambda x: f"最近{x}天")
    df = load_recent_data(days_option)
    if df.empty:
        st.warning("未找到对应数据")
        return

    # ---------- 一行 4 小图 ----------
    fig, axes = plt.subplots(1, 4, figsize=(15, 3), sharex=True)

    infos = [
        ("Temperature", [0, 50]),
        ("Humidity",    [0, 100]),
        ("CO2",         [0, 2000]),
    ]
    for ax, (col_name, y_range) in zip(axes[:3], infos):
        if col_name in df.columns:
            ax.plot(df.index, df[col_name], color='tab:blue')
            ax.set_ylim(y_range)
        ax.set_title(f"{col_name} Trend")
        ax.set_ylabel(col_name)

    # ---------- 第 4 图：pH / EC 双轴 ----------
    ax4 = axes[3]
    cols = [c for c in ["pH", "EC"] if c in df.columns]
    for col in cols:
        ax4.plot(df.index, df[col], label=col)
    ax4.set_title("pH & EC Trend")
    ax4.set_ylabel("pH / EC")
    ax4.legend()

    # ---------- 统一 X 轴刻度 ----------
    if days_option == 1:
        # 最近 1 天：只显示小时，不标日期
        locator = mdates.HourLocator(interval=3)
        formatter = mdates.DateFormatter("%H")
    else:
        # 3/7 天：只显示日期，不标时间
        locator = mdates.DayLocator(interval=1)
        formatter = mdates.DateFormatter("%m-%d")

    for ax in axes:
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(formatter)
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)
    st.markdown("---")
    st.header("📷 相机拍摄画面")

    CAMERA_IDS = [0, 2, 4]
    IMAGE_BASE_DIR = "./Image"
    VALID_EXTS = ("*.jpg", "*.jpeg", "*.png")

    def get_latest_image(camera_id: int):
        folder_path = os.path.join(IMAGE_BASE_DIR, str(camera_id))
        if not os.path.isdir(folder_path):
            return None

        files = []
        for ext in VALID_EXTS:
            files.extend(glob.glob(os.path.join(folder_path, f"img_dst_{camera_id}_*{ext}")))

        if not files:
            return None

        def extract_time_from_name(path):
            name = os.path.basename(path)
            try:
                base = os.path.splitext(name)[0]
                parts = base.split("_")
                time_part = parts[-2] + "_" + parts[-1] if len(parts) >= 2 else parts[-1]
                return datetime.strptime(time_part, "%Y-%m-%d_%H-%M-%S")
            except Exception:
                return datetime.min

        files.sort(key=extract_time_from_name, reverse=True)
        return files[0]

    cols = st.columns(len(CAMERA_IDS))
    for idx, cam_id in enumerate(CAMERA_IDS):
        with cols[idx]:
            st.subheader(f"相机 {cam_id}")
            latest = get_latest_image(cam_id)
            if latest:
                try:
                    with Image.open(latest) as img:
                        st.image(img, caption=os.path.basename(latest))
                except Exception as e:
                    st.error(f"无法打开图片：{e}")
            else:
                st.info("暂无图片")

# ------------------- 配置文件读写 -------------------
def load_config(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_config(config, file_path):
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


# --- 初始化文件修改时间 --- #
if "plc_mtime" not in st.session_state:
    st.session_state.plc_mtime = os.path.getmtime(CONFIG_PLC_FILE) if os.path.exists(CONFIG_PLC_FILE) else 0
if "rs485_mtime" not in st.session_state:
    st.session_state.rs485_mtime = os.path.getmtime(CONFIG_485_FILE) if os.path.exists(CONFIG_485_FILE) else 0

# # --- 检查文件更新并自动刷新 --- #
# def check_for_config_update():
#     plc_mtime = os.path.getmtime(CONFIG_PLC_FILE) if os.path.exists(CONFIG_PLC_FILE) else 0
#     rs485_mtime = os.path.getmtime(CONFIG_485_FILE) if os.path.exists(CONFIG_485_FILE) else 0

#     if plc_mtime != st.session_state.plc_mtime or rs485_mtime != st.session_state.rs485_mtime:
#         st.session_state.plc_mtime = plc_mtime
#         st.session_state.rs485_mtime = rs485_mtime
#         st.toast("检测到配置文件更新，页面即将刷新 🔄", icon="🔁")
#         sleep(0.5)
#         st.experimental_rerun()



# ------------------- LED 统一渲染函数 -------------------
def load_auto_schedule(today: date | None = None):
    today = today or date.today()
    auto_file = AUTO_CONFIG_DIR / f"config{today}.json"

    if not auto_file.exists():
        return {}

    data = json.loads(auto_file.read_text(encoding="utf-8"))
    schedule = {}
    for key in LED_KEYS:
        if key not in data:
            continue
        try:
            start = int(data[key]["start"].split(":")[0])
            stop = int(data[key]["stop"].split(":")[0])
            schedule[key] = (start, stop)
        except Exception:
            continue
    return schedule
def led_control_block(led_key: str, conf: dict, prefix: str):
    st.subheader(f"{led_key.upper()} 控制")
    led_conf = conf.get(led_key, {"mode":"manual","enable":False,"start_hour":20,"stop_hour":0})

    # 单选框选择模式
    mode = st.radio("模式", ["auto", "manual"], index=0 if led_conf.get("mode")=="auto" else 1,
                    key=f"{prefix}_{led_key}_mode")
    
    if mode == "auto":
        auto_schedule = load_auto_schedule()
        if led_key in auto_schedule:
            start, stop = auto_schedule[led_key]
            stop_display = 24 if stop == 0 else stop
            st.info(f"AI 自动模式 —— 今日开启：{start}:00，关闭：{stop_display}:00")
        else:
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


# ------------------- 读取csv，计算光照时间 -------------------
def get_today_led_schedule() -> tuple[int,int]:
    csv_path = AUTO_CONFIG_DIR / "daily_light.csv"
    if not csv_path.exists():
        return 20,20

    today = date.today().day
    with csv_path.open(newline='',encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
        if today > len(rows):
            return 20,20
        light_hours = float(rows[today-1]["light_hours"])

    start = 20
    end_dt = datetime.combine(date.today(), time(start)) + timedelta(hours=light_hours)
    stop = end_dt.hour
    return start,stop

# ------------------- 控制页面 -------------------
def relays_tab():
    # 检查是否有配置更新（来自别的设备）
    # check_for_config_update()

    config_plc = load_config(CONFIG_PLC_FILE)
    config_485 = load_config(CONFIG_485_FILE)

    st.header("PLC设备控制")
    uv_enable = st.checkbox(
        "UV开关",
        value=config_plc.get("uv", {}).get("enable", False),
        key="uv_enable"
    )
    uv_start = st.number_input(
        "UV开启时间(小时)", 0, 23,
        value=config_plc.get("uv", {}).get("start_hour", 3),
        key="uv_start"
    )
    uv_stop = st.number_input(
        "UV关闭时间(小时)", 0, 23,
        value=config_plc.get("uv", {}).get("stop_hour", 6),
        key="uv_stop"
    )
    config_plc["uv"] = {"enable": uv_enable, "start_hour": uv_start, "stop_hour": uv_stop}

    pump_enable = st.checkbox(
        "水泵开关",
        value=config_plc.get("water_pump", {}).get("enable", False),
        key="pump_enable"
    )
    pump_interval = st.number_input(
        "水泵间隔(分钟)", 1, 999,
        value=config_plc.get("water_pump", {}).get("interval_minutes", 20),
        key="pump_interval"
    )
    pump_duration = st.number_input(
        "水泵持续时间(秒)", 1, 9999,
        value=config_plc.get("water_pump", {}).get("duration_seconds", 60),
        key="pump_duration"
    )
    config_plc["water_pump"] = {
        "enable": pump_enable,
        "interval_minutes": pump_interval,
        "duration_seconds": pump_duration
    }

    spray_enable = st.checkbox(
        "洒水开关",
        value=config_plc.get("water_spray", {}).get("enable", False),
        key="spray_enable"
    )
    spray_interval = st.number_input(
        "洒水间隔(分钟)", 1, 999,
        value=config_plc.get("water_spray", {}).get("interval_minutes", 30),
        key="spray_interval"
    )
    spray_duration = st.number_input(
        "洒水持续时间(秒)", 1, 9999,
        value=config_plc.get("water_spray", {}).get("duration_seconds", 600),
        key="spray_duration"
    )
    config_plc["water_spray"] = {
        "enable": spray_enable,
        "interval_minutes": spray_interval,
        "duration_seconds": spray_duration
    }

    for led in ["top_led", "mid_led", "bot_led"]:
        led_control_block(led, config_plc, "plc")
    save_config(config_plc, CONFIG_PLC_FILE)

    st.header("485设备控制")
    for led in ["top_led2","top_led3","bot_led2","bot_led3","under_led1",
                "under_led2","under_led3","under_led4"]:
        led_control_block(led, config_485, "rs485")
    save_config(config_485, CONFIG_485_FILE)


# -------------------- AI光周期配置模块 --------------------
def ai_photoperiod_tab():
    st.header("AI光周期配置")
    with st.form(key="ai_photo_form"):
        days = st.number_input("栽培天数", min_value=1, value=50, step=1)
        h_min = st.number_input("最小光周期(h)", min_value=0, max_value=24, value=4, step=1)
        h_max = st.number_input("最大光周期(h)", min_value=0, max_value=24, value=9, step=1)
        h_ave = st.number_input("平均光周期(h)", min_value=0, max_value=24, value=8, step=1)
        submitted = st.form_submit_button("确认")

    if submitted:
        calc = calc_photoperiod(days,h_min,h_max,h_ave)
        csv_path = AUTO_CONFIG_DIR / "daily_light.csv"
        csv_path.parent.mkdir(exist_ok=True,parents=True)
        with csv_path.open("w", newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["day","light_hours"])
            writer.writerows(enumerate(calc["daily_schedule"],1))

        base_date = date.today()
        start_min = 20*60
        for day_i, hrs in enumerate(calc["daily_schedule"],1):
            duration_min = int(hrs*60)
            stop_min = (start_min+duration_min)%(24*60)
            stop_hour, stop_min = divmod(stop_min,60)
            day_conf = {k:{"start":"20:00","stop":f"{stop_hour:02d}:{stop_min:02d}"} for k in LED_KEYS}
            (AUTO_CONFIG_DIR/f"config{base_date+timedelta(days=day_i-1)}.json").write_text(json.dumps(day_conf,ensure_ascii=False,indent=2))
        st.success(f"已自动配置光周期！")

# ------------------- 主函数 -------------------
def main():
    st.title("室墨司源控制面板")

    refresh_interval = 30
    st_autorefresh(interval=refresh_interval * 1000)  # 注意转换成毫秒

    # —— 日期刷新逻辑 —— #
    if 'current_date' not in st.session_state:
        st.session_state.current_date = date.today()

    today = date.today()
    if today != st.session_state.current_date:
        st.session_state.current_date = today
        st.experimental_rerun()
    # —— 逻辑结束 —— #

    tab1, tab2, tab3 = st.tabs(["数据","控制","智能体"])
    with tab1:
        data_visualization_tab()
    with tab2:
        relays_tab()
    with tab3:
        ai_photoperiod_tab()

if __name__=="__main__":
    main()
