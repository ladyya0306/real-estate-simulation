import streamlit as st
import sqlite3
import pandas as pd
import json
import ast
import plotly.express as px

# 设置页面配置
st.set_page_config(
    page_title="Oasis 房产交易看板",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 数据库路径
DB_PATH = "./real_estate_stage2.db"

@st.cache_data(ttl=5) # 5秒缓存刷新，模拟实时
def load_data():
    if not os.path.exists(DB_PATH):
        return None, None, None
        
    conn = sqlite3.connect(DB_PATH)
    
    # 读取 Trace (核心行为)
    try:
        # 兼容列名
        cols = pd.read_sql("PRAGMA table_info(trace)", conn)['name'].tolist()
        action_col = 'action' if 'action' in cols else 'action_type'
        
        df_trace = pd.read_sql(f"SELECT user_id, {action_col} as action, info, created_at FROM trace ORDER BY created_at DESC", conn)
        
        # 处理 JSON info
        def parse_info(row):
            if not isinstance(row, str):
                return row
            try:
                # 1. Try standard JSON
                return json.loads(row)
            except:
                try:
                    # 2. Try AST for Python-style dicts
                    return ast.literal_eval(row)
                except:
                    try:
                        # 3. Last resort: dirty replace (only if above failed)
                        return json.loads(row.replace("'", '"'))
                    except:
                        return {}
        
        df_trace['info_dict'] = df_trace['info'].apply(parse_info)
        df_trace['info_dict'] = df_trace['info'].apply(parse_info)
        
        # 读取用户表映射名称
        try:
            df_users = pd.read_sql("SELECT user_id, user_name FROM user", conn)
            user_map = dict(zip(df_users['user_id'], df_users['user_name']))
            
            # 映射用户名，如果找不到则显示 ID
            df_trace['user_name'] = df_trace['user_id'].map(user_map)
            df_trace['user_name'] = df_trace['user_name'].fillna(df_trace['user_id'].astype(str))
            
            # 为 0 号用户特殊处理（如果是系统/卖家）
            # 注意：数据库中 0 号用户可能已有名字，这里只作为兜底
            mask_0 = df_trace['user_id'] == 0
            if mask_0.any():
                # 如果映射后仍为空，才赋予默认值
                df_trace.loc[mask_0 & df_trace['user_name'].isna(), 'user_name'] = "卖家老王"
                
        except Exception as e:
            print(f"读取用户表失败: {e}")
            # 降级方案
            df_trace['user_name'] = df_trace['user_id'].apply(lambda x: "卖家老王" if x == 0 else f"用户 {x}")
    except Exception as e:
        df_trace = pd.DataFrame()
        st.error(f"读取 Trace 失败: {e}")

    # 读取房源 Post
    try:
        df_post = pd.read_sql("SELECT * FROM post ORDER BY created_at DESC", conn)
    except:
        df_post = pd.DataFrame()

    # 读取评论 Comment (Offer详情)
    try:
        df_comment = pd.read_sql("SELECT * FROM comment ORDER BY created_at DESC", conn)
    except:
        df_comment = pd.DataFrame()

    conn.close()
    return df_trace, df_post, df_comment

import os

# --- UI 渲染 ---
st.title("🏠 Oasis 房产仿真交易中心")

# 加载数据
df_trace, df_post, df_comment = load_data()

if df_trace is None:
    st.warning("🚧 数据库尚未生成，请先运行仿真脚本！")
    st.info("运行命令: `python real_estate_demo_v2.py`")
else:
    # --- 顶栏指标 ---
    col1, col2, col3, col4 = st.columns(4)
    
    # 计算指标
    total_listings = len(df_trace[df_trace['action'] == 'list_property'])
    total_offers = len(df_trace[df_trace['action'] == 'make_offer'])
    total_deals = len(df_trace[df_trace['action'] == 'accept_offer'])
    last_active = df_trace.iloc[0]['created_at'] if not df_trace.empty else "N/A"

    col1.metric("📋 挂牌房源", total_listings, "+1")
    col2.metric("💰 收到报价", total_offers, delta_color="normal")
    col3.metric("🤝 达成成交", total_deals, delta_color="inverse") # 绿色
    col4.metric("🕒最后活动", last_active.split(" ")[1] if " " in last_active else last_active)

    # --- 主体内容 ---
    tab1, tab2 = st.tabs(["📊 动态看板", "🗃️ 数据明细"])
    
    with tab1:
        c1, c2 = st.columns([1, 1.5])
        
        with c1:
            st.subheader("📋 最新房源 (Listings)")
            if not df_post.empty:
                for _, row in df_post.iterrows():
                    with st.container(border=True):
                        st.markdown(f"**🏡 房源 #{row['post_id']}**")
                        st.text(row['content'])
                        st.caption(f"发布时间: {row['created_at']}")
            else:
                st.info("暂无房源")

            st.divider()
            st.subheader("💰 报价记录 (Offers)")
            # 筛选 make_offer 的 trace
            offers = df_trace[df_trace['action'] == 'make_offer']
            if not offers.empty:
                for _, row in offers.iterrows():
                    info = row['info_dict']
                    st.success(f"**{row['user_name']}** 出价: **{info.get('price')} 万**")
                    st.markdown(f"> 💬 {info.get('message')}")
                    st.caption(f"Offer ID: {info.get('offer_id')} | {row['created_at']}")
            else:
                st.info("暂无报价")

        with c2:
            st.subheader("⚡ 实时交易动态 (Live Feed)")
            
            for index, row in df_trace.iterrows():
                action = row['action']
                user = row['user_name']
                time = row['created_at']
                info = row['info_dict']
                
                if action == 'list_property':
                    st.info(f"🏡 **{user}** 刚刚挂牌了一套房产！\n\n内容: {info.get('content')}")
                elif action == 'make_offer':
                    st.warning(f"💰 **{user}** 发起了一笔报价！\n\n金额: **{info.get('price')}万**")
                elif action == 'accept_offer':
                    st.balloons() # 庆祝特效
                    st.success(f"🤝 **{user}** 接受了报价！交易达成！🎉\n\n状态: {info.get('status')}")
                elif action == 'search_property':
                    st.markdown(f"🔍 *{user} 正在搜索: {info.get('query')}*")
                elif action == 'refresh':
                    st.caption(f"🔄 {user} 刷新了页面")
                else:
                    st.write(f"[{time}] {user}: {action}")

    with tab2:
        st.subheader("数据库原始记录")
        st.dataframe(df_trace)

    # 自动刷新按钮
    if st.button("🔄 刷新数据"):
        st.rerun()
