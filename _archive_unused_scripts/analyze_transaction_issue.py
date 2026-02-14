"""深度分析交易成交率低的问题 - 修正版"""
import sqlite3

import pandas as pd

db_path = 'results/run_20260208_201643/simulation.db'
conn = sqlite3.connect(db_path)

print("=" * 80)
print("数据库结构分析")
print("=" * 80)

# 1. 查看所有表
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print(f"\n数据库包含的表: {[t[0] for t in tables]}\n")

# 2. 分析agents财务状况
print("=" * 80)
print("AGENTS 财务状况分析")
print("=" * 80)
agents_df = pd.read_sql_query("SELECT * FROM agents_finance", conn)
print(f"\n总agent数: {len(agents_df)}")
print("\nCash统计:")
print(agents_df['cash'].describe())
print("\n现金分布:")
print(f"  > 1000万: {(agents_df['cash'] > 10000000).sum()}人")
print(f"  500-1000万: {((agents_df['cash'] >= 5000000) & (agents_df['cash'] <= 10000000)).sum()}人")
print(f"  100-500万: {((agents_df['cash'] >= 1000000) & (agents_df['cash'] < 5000000)).sum()}人")
print(f"  < 100万: {(agents_df['cash'] < 1000000).sum()}人")

# 3. 分析active_participants
print("\n" + "=" * 80)
print("ACTIVE PARTICIPANTS 分析")
print("=" * 80)
active_df = pd.read_sql_query("SELECT * FROM active_participants", conn)
print(f"\n总激活参与者: {len(active_df)}")
print("角色分布:")
print(active_df['role'].value_counts())

# 4. 分析properties
print("\n" + "=" * 80)
print("PROPERTIES 分析")
print("=" * 80)

# 先看看两个表都有什么字段
props_market = pd.read_sql_query("SELECT * FROM properties_market LIMIT 1", conn)
print(f"\nproperties_market字段: {props_market.columns.tolist()}")

props_static = pd.read_sql_query("SELECT * FROM properties_static LIMIT 1", conn)
print(f"properties_static字段: {props_static.columns.tolist()}")

# 读取properties数据
props_market_full = pd.read_sql_query("SELECT * FROM properties_market", conn)
props_static_full = pd.read_sql_query("SELECT * FROM properties_static", conn)

# 合并
props_df = pd.merge(props_static_full, props_market_full, on='property_id', how='inner')
print(f"\n总房产数: {len(props_df)}")
print("\n状态分布:")
print(props_df['status'].value_counts())

# 检查价格字段
if 'current_valuation' in props_df.columns:
    price_col = 'current_valuation'
elif 'initial_value' in props_df.columns:
    price_col = 'initial_value'
else:
    print("警告：找不到价格字段！")
    print(f"可用字段: {props_df.columns.tolist()}")
    price_col = None

if price_col:
    print(f"\n使用价格字段: {price_col}")
    for_sale = props_df[props_df['status'] == 'for_sale']
    print("\nFor Sale房产价格统计:")
    print(for_sale[price_col].describe())
    print("\n价格分布:")
    print(f"  > 500万: {(for_sale[price_col] > 5000000).sum()}套")
    print(f"  300-500万: {((for_sale[price_col] >= 3000000) & (for_sale[price_col] <= 5000000)).sum()}套")
    print(f"  150-300万: {((for_sale[price_col] >= 1500000) & (for_sale[price_col] < 3000000)).sum()}套")
    print(f"  < 150万: {(for_sale[price_col] < 1500000).sum()}套")

    print("\nFor Sale房产zone分布:")
    print(for_sale['zone'].value_counts())

    # 检查owner_id
    print("\nFor Sale房产owner_id情况:")
    print(f"  有owner_id: {for_sale['owner_id'].notna().sum()}套")
    print(f"  无owner_id (NULL/NaN): {for_sale['owner_id'].isna().sum()}套")

    # 检查owner_id是否为空字符串或0
    if for_sale['owner_id'].notna().sum() > 0:
        non_null_owners = for_sale[for_sale['owner_id'].notna()]['owner_id']
        print(f"  owner_id样本: {non_null_owners.head(10).tolist()}")

# 5. 分析transactions
print("\n" + "=" * 80)
print("TRANSACTIONS 分析")
print("=" * 80)
trans_df = pd.read_sql_query("SELECT * FROM transactions", conn)
print(f"\n总交易数: {len(trans_df)}")
if len(trans_df) > 0:
    print("\n成功的交易详情:")
    print(trans_df[['buyer_id', 'seller_id', 'property_id', 'final_price', 'month']])

    # 查看这笔交易的详细信息
    buyer_id = trans_df.iloc[0]['buyer_id']
    seller_id = trans_df.iloc[0]['seller_id']
    property_id = trans_df.iloc[0]['property_id']

    print(f"\n成功交易的买家(ID:{buyer_id})信息:")
    buyer_finance = pd.read_sql_query(f"SELECT * FROM agents_finance WHERE agent_id = {buyer_id}", conn)
    print(buyer_finance)

    print(f"\n成功交易的卖家(ID:{seller_id})信息:")
    seller_finance = pd.read_sql_query(f"SELECT * FROM agents_finance WHERE agent_id = {seller_id}", conn)
    print(seller_finance)

    print(f"\n成功交易的房产(ID:{property_id})信息:")
    prop = props_df[props_df['property_id'] == property_id]
    print(prop.T)  # 转置显示更清楚

# 6. 分析negotiations
print("\n" + "=" * 80)
print("NEGOTIATIONS 分析")
print("=" * 80)
neg_df = pd.read_sql_query("SELECT * FROM negotiations", conn)
print(f"\n总谈判记录数: {len(neg_df)}")
if len(neg_df) > 0:
    print(f"\nnegotiations表字段: {neg_df.columns.tolist()}")
    print("\n谈判成功/失败分布:")
    print(neg_df['success'].value_counts())

    # 分析失败原因
    failed = neg_df[neg_df['success'] == 0]
    print(f"\n失败的谈判数: {len(failed)}")
    if 'reason' in neg_df.columns:
        print("\n失败原因分布:")
        print(failed['reason'].value_counts())

    # 查看一些失败的谈判详情
    print("\n前10条失败谈判的详情:")
    if 'final_price' in neg_df.columns:
        print(failed[['buyer_id', 'seller_id', 'property_id', 'final_price', 'success', 'reason']].head(10))

# 7. 交叉分析：buyer能力 vs 房价
print("\n" + "=" * 80)
print("交叉分析：买家购买力 vs 房产价格")
print("=" * 80)

# 找出所有BUYER
buyers_df = active_df[active_df['role'] == 'BUYER']
print(f"\n买家数量: {len(buyers_df)}")

# 获取买家的财务信息
if len(buyers_df) > 0:
    buyer_ids = buyers_df['agent_id'].tolist()
    placeholders = ','.join(['?' for _ in buyer_ids])
    buyers_finance = pd.read_sql_query(
        f"SELECT * FROM agents_finance WHERE agent_id IN ({placeholders})",
        conn,
        params=buyer_ids
    )

    print("\n买家现金统计:")
    print(buyers_finance['cash'].describe())

    # 计算买家的最大购买力（假设首付30%，可贷款70%）
    # 最大购买力 = cash / 0.3
    buyers_finance['max_affordability'] = buyers_finance['cash'] / 0.3
    print("\n买家最大购买力统计（按30%首付计算）:")
    print(buyers_finance['max_affordability'].describe())

    if price_col:
        # 对比：有多少买家能买得起最便宜的房子
        min_price = for_sale[price_col].min()
        max_price = for_sale[price_col].max()
        median_price = for_sale[price_col].median()

        print("\n房产价格范围:")
        print(f"  最低价: {min_price:,.0f}")
        print(f"  中位数: {median_price:,.0f}")
        print(f"  最高价: {max_price:,.0f}")

        print("\n买家购买力匹配分析:")
        print(f"  能买得起最便宜房子的买家: {(buyers_finance['max_affordability'] >= min_price).sum()}人")
        print(f"  能买得起中位数价格房子的买家: {(buyers_finance['max_affordability'] >= median_price).sum()}人")
        print(f"  能买得起最贵房子的买家: {(buyers_finance['max_affordability'] >= max_price).sum()}人")

# 8. 检查agents_preference表
print("\n" + "=" * 80)
print("买家偏好 vs 房产zone匹配分析")
print("=" * 80)

# 查看表是否存在
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='agents_preference'")
if cursor.fetchone():
    pref_df = pd.read_sql_query("SELECT * FROM agents_preference", conn)
    print(f"\nagents_preference表字段: {pref_df.columns.tolist()}")
    print("\n买家偏好zone分布:")
    buyer_prefs = pref_df[pref_df['agent_id'].isin(buyers_df['agent_id'])]

    if 'preferred_zone' in pref_df.columns:
        print(buyer_prefs['preferred_zone'].value_counts())

        print("\nFor Sale房产zone分布:")
        print(for_sale['zone'].value_counts())

        # Zone匹配分析
        print("\nZone匹配可能性:")
        for zone in for_sale['zone'].unique():
            buyers_want_this_zone = buyer_prefs[buyer_prefs['preferred_zone'] == zone]
            houses_in_this_zone = for_sale[for_sale['zone'] == zone]
            print(f"  {zone}: {len(buyers_want_this_zone)}个买家想要, {len(houses_in_this_zone)}套房在售")
    else:
        print("警告：agents_preference表中没有preferred_zone字段")
        print(f"可用字段: {pref_df.columns.tolist()}")
else:
    print("警告：数据库中没有agents_preference表")

# 9. 深入分析：随机抽取几个买家，看看为什么买不了房
print("\n" + "=" * 80)
print("深入案例分析：随机抽取3个买家")
print("=" * 80)

if len(buyers_finance) > 0:
    sample_buyers = buyers_finance.sample(min(3, len(buyers_finance)))

    for idx, buyer_row in sample_buyers.iterrows():
        buyer_id = buyer_row['agent_id']
        buyer_cash = buyer_row['cash']
        buyer_max_afford = buyer_row['max_affordability']

        print(f"\n【买家 #{buyer_id}】")
        print(f"  现金: {buyer_cash:,.0f}")
        print(f"  最大购买力(30%首付): {buyer_max_afford:,.0f}")

        # 查看这个买家的谈判记录
        buyer_negs = neg_df[neg_df['buyer_id'] == buyer_id]
        print(f"  参与谈判次数: {len(buyer_negs)}")
        if len(buyer_negs) > 0:
            print("  谈判结果:")
            print(buyer_negs['success'].value_counts().to_dict())
            if 'reason' in buyer_negs.columns:
                print("  失败原因:")
                print(buyer_negs[buyer_negs['success'] == 0]['reason'].value_counts())

conn.close()
print("\n" + "=" * 80)
print("分析完成")
print("=" * 80)
