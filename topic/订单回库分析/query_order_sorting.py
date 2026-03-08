#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量查询订单对应的盒菜分拣信息。

关联逻辑（参考 Dashboard 128 Card 1513）：
1. 通过 commodity_expiration_time + point_id + save_container_id + save_shelf_id
   匹配 inventory_device_shelf_bak.tally_times，取最早出现该过期日的快照日
   作为上架日期；若 bak 无记录（当天补货当天卖完），回退用下单当天
2. central_kitchen_car_task：point_id + task_type=4 + 上架日当天
   + finish_shelve < 下单时间 → 取最早 batch_no
3. sorting_tasks：batch_no + point_id → 分拣/上架时间、车牌、op_name
"""
import sys
sys.path.insert(0, '/Users/admin/Code/MyCode/kuhe/topic/订单回库分析')

from query_order_callback import metabase_query
import pandas as pd

orders_raw = """
176838948523054106
176836507915119006
176839276230732101
176839221926413636
176840810038409873
176836247763317642
176844888389897790
176853715613577925
176856460645765024
176862202748807530
176862639601508584
176865469564941348
176830260915215046
176844660264220118
176887268714963498
176905228483517343
176905071962923676
176750494026001150
176913995240070498
176933853556950063
176960127282528769
176967918035318121
176968741152447331
176979100104683514
177026173814432875
177029456344001530
177030933943206680
177034577619975513
177028343250834247
177044978152398190
177065851926977047
177107850624007861
177120699724569516
177125874499056773
177139224421974942
177141376124399990
177145637738598267
177025923595330216
177138387859466223
177172353157193100
177182612271833789
177183452859607233
177183904942731054
177184799598375210
177181190891864300
177190841411034461
177182560569724712
177191007311300298
177189800276832055
177199079955569838
177200866938369102
177201762917213081
177204157124697616
177199083530638822
177207368415857454
177208922008818474
177207881920576912
177211631089971915
177211130485171815
177212231981095440
177215154026041413
177218660430722225
177212636571259170
177229464450275314
177236783143831352
177240489401005615
177243165804046136
177244464934862230
177242600438176887
177253429306025133
177199499781960576
177254397825292285
"""

# 去重
order_list = sorted(set(line.strip() for line in orders_raw.strip().split('\n') if line.strip()))
print(f"去重后共 {len(order_list)} 个订单，开始分批查询...\n")

BATCH_SIZE = 15
all_results = []

for i in range(0, len(order_list), BATCH_SIZE):
    batch = order_list[i:i + BATCH_SIZE]
    in_clause = ",".join(f"'{o}'" for o in batch)
    batch_num = i // BATCH_SIZE + 1
    total_batches = (len(order_list) + BATCH_SIZE - 1) // BATCH_SIZE
    print(f"  查询第 {batch_num}/{total_batches} 批（{len(batch)} 个订单）...", end='', flush=True)

    sql = f"""
        SELECT
            op.order_no,
            op.commodity_id,
            op.commodity_name,
            op.commodity_expiration_time,
            o.point_id,
            p.point_name,
            op.save_container_id,
            op.save_shelf_id,
            o.create_time AS order_time,
            sd.shelving_date,
            cct.batch_no,
            cct.finish_shelve,
            cct.op_name AS car_task_op_name,
            st.car_number,
            CASE
                WHEN st.car_number IS NULL OR st.car_number = '' THEN 0
                WHEN st.car_number LIKE '虚%' THEN 1
                ELSE 2
            END AS car_type,
            st.sorting_start_time,
            st.sorting_end_time,
            st.shelving_finish_time,
            st.op_name AS sorting_op_name
        FROM order_product op
        JOIN commodity c
            ON c.id = op.commodity_id
            AND c.commodity_type = 1
        JOIN `order` o
            ON o.order_no = op.order_no
        JOIN point p ON p.id = o.point_id
        -- 第1步：确定上架日期（每个 order_no+commodity_id+货架位置 只取一行）
        --   优先：tally_times 包含商品过期日的最早一天（= 该批次第一次出现在货架上的日期）
        --   回退：下单当天（商品当天补货当天卖完，bak 无记录）
        JOIN (
            SELECT
                op2.order_no,
                op2.commodity_id,
                op2.save_container_id,
                op2.save_shelf_id,
                op2.commodity_expiration_time,
                COALESCE(
                    (SELECT MIN(bak.day)
                     FROM inventory_device_shelf_bak bak
                     WHERE bak.point_id      = o2.point_id
                       AND bak.cabinet_id   = op2.save_container_id
                       AND bak.shelf_id     = op2.save_shelf_id
                       AND bak.commodity_id = op2.commodity_id
                       AND bak.tally_times LIKE CONCAT('%', op2.commodity_expiration_time, '%')
                       AND bak.day <= DATE(o2.create_time)
                    ),
                    DATE(o2.create_time)
                ) AS shelving_date
            FROM order_product op2
            JOIN commodity c2 ON c2.id = op2.commodity_id AND c2.commodity_type = 1
            JOIN `order` o2   ON o2.order_no = op2.order_no
            WHERE op2.order_no IN ({in_clause})
            GROUP BY op2.order_no, op2.commodity_id, op2.save_container_id, op2.save_shelf_id,
                     op2.commodity_expiration_time, o2.point_id, o2.create_time
        ) sd ON sd.order_no = op.order_no
            AND sd.commodity_id = op.commodity_id
            AND sd.save_container_id = op.save_container_id
            AND sd.save_shelf_id = op.save_shelf_id
        -- 第2步：上架日当天 task_type=4、已完成且早于下单时间的最早配送任务
        LEFT JOIN central_kitchen_car_task cct
            ON  cct.point_id          = o.point_id
            AND cct.task_type         = 4
            AND DATE(cct.create_time) = sd.shelving_date
            AND cct.finish_shelve     > '2000-01-01'
            AND cct.finish_shelve     < o.create_time
            AND cct.batch_no = (
                SELECT MIN(c2.batch_no)
                FROM central_kitchen_car_task c2
                WHERE c2.point_id          = o.point_id
                  AND c2.task_type         = 4
                  AND DATE(c2.create_time) = sd.shelving_date
                  AND c2.finish_shelve     > '2000-01-01'
                  AND c2.finish_shelve     < o.create_time
            )
        -- 第3步：通过 batch_no 关联分拣任务
        LEFT JOIN sorting_tasks st
            ON  st.batch_no = cct.batch_no
            AND st.point_id = o.point_id
        WHERE op.order_no IN ({in_clause})
        ORDER BY o.create_time, op.order_no, op.commodity_id
    """

    batch_results = metabase_query(sql, timeout=90)
    print(f" 返回 {len(batch_results)} 条")
    all_results.extend(batch_results)

print()

df = pd.DataFrame(all_results)

if df.empty:
    print("未查询到任何匹配的分拣记录")
    sys.exit(0)

total = len(df)
matched = df[df['batch_no'].notna()].shape[0]
print(f"共 {total} 条记录，其中 {matched} 条匹配到配送/分拣记录，{total - matched} 条未匹配\n")

pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', 40)

try:
    print(df.to_markdown(index=False))
except ImportError:
    print(df.to_string(index=False))

# 保存 CSV
output_path = '/Users/admin/Code/MyCode/kuhe/topic/订单回库分析/order_sorting_result.csv'
df.to_csv(output_path, index=False, encoding='utf-8-sig')
print(f"\n完整结果已保存至: {output_path}")
