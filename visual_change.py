
import streamlit as st
import plotly.graph_objects as go

st.set_page_config(page_title="绿色能源与未来农业中心", layout="wide")

# -----------------------------
# 页面炫酷风格 CSS
# -----------------------------
st.markdown("""
<style>
body {
    background: linear-gradient(120deg, #0b1f1c, #001a1a);
    color: #00ffcc;
    font-family: 'Orbitron', sans-serif;
}
h1, h2, h3 {
    color: #00ffcc;
    text-shadow: 0 0 5px #00ffcc;
}
.stButton>button {
    background: linear-gradient(90deg, #00ffcc, #00b3b3);
    color: #0b1f1c;
    border-radius: 12px;
    box-shadow: 0 0 10px #00ffcc;
}
.stSlider>div>div>input {
    accent-color: #00ffcc;
}
.stMetric>div>div {
    background-color: rgba(0, 255, 204, 0.1);
    border-radius: 10px;
    padding: 10px;
}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# 页面三列布局
# -----------------------------
col_left, col_center, col_right = st.columns([1, 3, 1])

# -----------------------------
# 左列：气象监测
# -----------------------------
with col_left:
    st.header("气象监测")
    st.metric("温度", "16°C")
    st.metric("湿度", "86%")
    st.metric("光照", "450 W/m²")
    st.metric("风速", "3级")
    st.metric("CO2", "1 ppm")

# -----------------------------
# 中间列：监控图片 + 仪表盘
# -----------------------------
with col_center:
    # 缩小图片
    st.image("sample.jpg", caption="主监控画面", width=400)  # 原来是600，改成400

    # 仪表盘放在一个容器里，更紧凑
    with st.container():
        col3, col4, col5, col6, col7 = st.columns(5)
        indicators = [
            ("温度", 23, "°C"),
            ("湿度", 62, "%"),
            ("CO2浓度", 671, "ppm"),
            ("pH值", 7.2, ""),
            ("电导率", 1442, "S/m")
        ]
        for col, (name, value, unit) in zip([col3, col4, col5, col6, col7], indicators):
            fig = go.Figure(go.Indicator(
                mode="gauge+number+delta",
                value=value,
                delta={'reference': 50, 'increasing': {'color': "lime"}, 'decreasing': {'color': "red"}},
                title={'text': name, 'font': {'size': 18, 'color':'#00ffcc'}},
                gauge={
                    'axis': {'range': [0, 100], 'tickcolor':'#00ffcc'},
                    'bar': {'color': "#00ffcc"},
                    'bgcolor': "#001a1a",
                    'borderwidth': 2,
                    'bordercolor': "cyan",
                    'steps': [
                        {'range': [0, 50], 'color': '#003333'},
                        {'range': [50, 100], 'color': '#006666'}
                    ],
                }
            ))
            col.plotly_chart(fig, use_container_width=True)
# -----------------------------
# 右列：设备控制
# -----------------------------
with col_right:
    st.header("设备控制")

    # 初始化设备配置
    device_config = {
        "uv": {"enable": True, "start_hour": 3, "stop_hour": 6},
        "water_pump": {"enable": True, "interval_minutes": 30, "duration_seconds": 60},
        "water_spray": {"enable": False, "interval_minutes": 999, "duration_seconds": 1},
        "top_led": {"mode": "auto", "enable": True, "start_hour": 20, "stop_hour": 0},
        "mid_led": {"mode": "auto", "enable": True, "start_hour": 20, "stop_hour": 0},
        "bot_led": {"mode": "auto", "enable": True, "start_hour": 20, "stop_hour": 0}
    }

    # UV 控制
    with st.expander("UV 灯", expanded=True):
        device_config["uv"]["enable"] = st.checkbox("开启 UV 灯", value=device_config["uv"]["enable"], key="uv_enable")
        device_config["uv"]["start_hour"] = st.slider("开始时间", 0, 23, device_config["uv"]["start_hour"], key="uv_start")
        device_config["uv"]["stop_hour"] = st.slider("结束时间", 0, 23, device_config["uv"]["stop_hour"], key="uv_stop")

    # 水泵控制
    with st.expander("水泵", expanded=True):
        device_config["water_pump"]["enable"] = st.checkbox("开启水泵", value=device_config["water_pump"]["enable"], key="pump_enable")
        device_config["water_pump"]["interval_minutes"] = st.slider("间隔 (分钟)", 1, 120, device_config["water_pump"]["interval_minutes"], key="pump_interval")
        device_config["water_pump"]["duration_seconds"] = st.slider("持续时间 (秒)", 1, 300, device_config["water_pump"]["duration_seconds"], key="pump_duration")

    # 喷雾控制
    with st.expander("喷雾", expanded=False):
        device_config["water_spray"]["enable"] = st.checkbox("开启喷雾", value=device_config["water_spray"]["enable"], key="spray_enable")
        device_config["water_spray"]["interval_minutes"] = st.slider("间隔 (分钟)", 1, 120, device_config["water_spray"]["interval_minutes"], key="spray_interval")
        device_config["water_spray"]["duration_seconds"] = st.slider("持续时间 (秒)", 1, 300, device_config["water_spray"]["duration_seconds"], key="spray_duration")

    # LED 灯控制
    with st.expander("LED 灯", expanded=True):
        for led in ["top_led", "mid_led", "bot_led"]:
            st.subheader(f"{led.replace('_', ' ').title()}")
            device_config[led]["enable"] = st.checkbox("开启", value=device_config[led]["enable"], key=f"{led}_enable")
            device_config[led]["mode"] = st.selectbox("模式", ["auto", "manual"], index=0 if device_config[led]["mode"]=="auto" else 1, key=f"{led}_mode")
            device_config[led]["start_hour"] = st.slider("开始时间", 0, 23, device_config[led]["start_hour"], key=f"{led}_start")
            device_config[led]["stop_hour"] = st.slider("结束时间", 0, 23, device_config[led]["stop_hour"], key=f"{led}_stop")

