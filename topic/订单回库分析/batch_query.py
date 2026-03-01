#!/usr/bin/env python3
"""批量查询订单回库情况，复用 query_order_callback.py 的逻辑"""
import sys
sys.path.insert(0, '/Users/admin/Code/MyCode/kuhe/topic/订单回库分析')

from query_order_callback import metabase_query
import pandas as pd

orders_raw = """
176913995240070498
176913995240070498
176960127282528769
176968741152447331
176979100104683514
177017907552124303
177029456344001530
177030933943206680
177034577619975513
177028343250834247
177028343250834247
177044978152398190
177061711158592456
177065851926977047
177080397108271265
176657174900890775
177087217040835405
177094925743614960
177094862211373915
177105975279250475
177107850624007861
177101085112843753
177120699724569516
177125874499056773
177125874499056773
177133368222141880
177139224421974942
177141376124399990
177141376124399990
177141376124399990
177141376124399990
177141376124399990
177141376124399990
177145637738598267
177145637738598267
176718476815503072
177025923595330216
177160426741157655
177138387859466223
177172755078282985
177172353157193100
177182612271833789
177183452859607233
177184799598375210
177184799598375210
177181190891864300
177181190891864300
177182560569724712
177191007311300298
177195234322102670
177195234322102670
177189800276832055
177199079955569838
177199079955569838
177199888268330174
177200866938369102
177200866938369102
177201762917213081
177203266632552050
177204157124697616
177204157124697616
177203260204413650
177203260204413650
177199083530638822
177199083530638822
177195632148313517
177207368415857454
177203410728396104
177208922008818474
177208922008818474
177208922008818474
177208922008818474
177211631089971915
177211130485171815
177212231981095440
177215154026041413
177218543323905923
177212636571259170
177229464450275314
177212231981095440
"""

# 去重
order_list = sorted(set(line.strip() for line in orders_raw.strip().split('\n') if line.strip()))
print(f"去重后共 {len(order_list)} 个订单，开始查询...\n")

# 拼接 IN 子句
in_clause = ",".join(f"'{o}'" for o in order_list)

sql = f"""
    SELECT
        op.order_no,
        op.commodity_id,
        op.commodity_name,
        o.point_id,
        p.point_name,
        op.save_shelf_id,
        op.create_time AS order_time,
        CASE WHEN COUNT(DISTINCT ca.id) > 0 THEN 'Y' ELSE 'N' END AS is_callback,
        COUNT(DISTINCT ca.id) AS callback_count,
        MIN(ca.callback_time) AS earliest_callback,
        MAX(ca.callback_time) AS latest_callback,
        GROUP_CONCAT(DISTINCT ca.from_picking_no ORDER BY ca.from_picking_no) AS from_picking_nos
    FROM order_product op
    JOIN commodity c
        ON c.id = op.commodity_id
    JOIN `order` o
        ON o.order_no = op.order_no
    JOIN point p
        ON p.id = o.point_id
    LEFT JOIN central_kitchen_commodity_again ca
        ON ca.next_point_id = o.point_id
        AND ca.next_shelf_id = op.save_shelf_id
        AND ca.commodity_id = op.commodity_id
        AND ca.callback_time >= DATE_SUB(op.create_time, INTERVAL 7 DAY)
        AND ca.callback_time <= op.create_time
    WHERE op.order_no IN ({in_clause})
      AND c.commodity_type = 1
    GROUP BY
        op.order_no, op.commodity_id, op.commodity_name,
        o.point_id, p.point_name, op.save_shelf_id, op.create_time
    ORDER BY op.order_no, op.commodity_id
"""

results = metabase_query(sql)
df = pd.DataFrame(results)

if df.empty:
    print("未查询到任何盒菜商品")
    sys.exit(0)

total = len(df)
callback_df = df[df['is_callback'] == 'Y']
callback_count = len(callback_df)

print(f"共查询到 {total} 条盒菜记录，其中 {callback_count} 条存在回库记录\n")

# 只输出命中的
if callback_df.empty:
    print("所有订单盒菜均无回库记录")
else:
    print(f"=== 命中回库的记录（{callback_count} 条）===\n")
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    pd.set_option('display.max_colwidth', 40)
    try:
        print(callback_df.to_markdown(index=False))
    except ImportError:
        print(callback_df.to_string(index=False))

# 保存完整结果到 CSV
output_path = '/Users/admin/Code/MyCode/kuhe/topic/订单回库分析/batch_callback_result.csv'
df.to_csv(output_path, index=False, encoding='utf-8-sig')
print(f"\n完整结果已保存至: {output_path}")
