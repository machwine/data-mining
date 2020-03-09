import csv

import time

import fp_growth
import geohash



import sys


def log(*args):
    show_log = True
    if show_log:
        for arg in args:
            print(arg, end=" ")
        print()


def add_dict(d, key, value):
    if key in d:
        d[key].append(value)
    else:
        d[key] = [value]


dis_threshold = 400

user_start_end_dict = {}  # { 用户: [ [初始地，目的地], [], []... ], ... }
user_start_dict = {}  # { 用户: [ [初始地], [], []... ], ... }
user_end_dict = {}  # { 用户: [ [目的地], [], []... ], ... }
start_end_dict = {}  # { 初始地: [ [目的地], [], []... ], ... }

dataset24 = []

train_num = 0
test_num = 0

print('开始读取数据')

with open('train.csv') as f:
    reader = csv.reader(f)

    for line in reader:

        if reader.line_num % 80000 == 0:
            print("%.2f" % (reader.line_num / 3090000 * 100), "%")

        if reader.line_num == 1:
            continue

        t = time.strptime(line[4], "%Y-%m-%d %H:%M:%S")

        if t[2] == 24:
            test_num += 1
            dataset24.append(line)
        else:
            train_num += 1
            add_dict(user_start_end_dict, line[1], [line[5], line[6]])
            add_dict(user_start_dict, line[1], [line[5]])
            add_dict(user_end_dict, line[1], [line[6]])
            add_dict(start_end_dict, line[5], [line[6]])

print('load finished', 'train set:', train_num, 'test set:', test_num)

print("开始测试...")

pre_num = 0  # 参与预测的数量
invalid_num = 0  # 无效用户
right_num = 0  # 预测正确的数量
des_num = 0  # 预测目的地总数

for i, line in enumerate(dataset24):
    if i % 10000 == 0:
        print("%.2f" % (i / 128000 * 100), "%")

    username, ori, des = line[1], line[5], line[6]

    log("\n\n测试", i)
    log(username, ori, des)

    fp_user_start_end = []
    fp_user_start = []
    fp_user_end = []
    fp_start_end = []

    if username not in user_start_end_dict and ori not in start_end_dict:
        invalid_num += 1
        continue

    pre_num += 1

    if username in user_start_end_dict:
        log("user_start_end_dict[username]", user_start_end_dict[username])
        log("user_start_dict[username]", user_start_dict[username])
        log("user_end_dict[username]", user_end_dict[username])

        fp_user_start_end = fp_growth.generate(user_start_end_dict[username], 1, 2)

        user_start_list = []
        user_end_list = []

        for j, val in enumerate(user_start_dict[username]):
            user_start_list.extend([[item] for item in geohash.expand(val[0])])

        for j, val in enumerate(user_end_dict[username]):
            user_end_list.extend([[item] for item in geohash.expand(val[0])])

        log("user_start_list", user_start_list)
        log("user_end_list", user_end_list)
        fp_user_start = fp_growth.generate(user_start_list, 2, 0)
        fp_user_end = fp_growth.generate(user_end_list, 2, 0)

    if ori in start_end_dict:
        log("start_end_dict[ori]", start_end_dict[ori])

        # start_end_list = []
        # for j, val in enumerate(start_end_dict[ori]):
        #     start_end_list.extend([[item] for item in geohash.expand(val[0])])

        fp_start_end = fp_growth.generate(start_end_dict[ori], 3, 0)

    log("fp_user_start_end", fp_user_start_end)
    log("fp_user_start:", fp_user_start)
    log("fp_user_end:", fp_user_end)
    log("fp_start_end", fp_start_end)

    result_tmp = set()

    # 对于[[初始地]], [[目的地]]这样的频繁项集，直接添加到结果里
    for j, item in enumerate(fp_user_start):
        result_tmp.add(list(item)[0])
    for j, item in enumerate(fp_user_end):
        result_tmp.add(list(item)[0])
    for j, item in enumerate(fp_start_end):
        result_tmp.add(list(item)[0])

    # 遍历[[初始地，目的地]]频繁项集，把处在出发地周围的一个作为起始地点，而远的作为预测结果.
    log("遍历[[初始地，目的地]]频繁项集")
    for j, item in enumerate(fp_user_start_end):
        item_list = list(item)
        log(item_list[0], item_list[1])

        dis1 = geohash.get_distance_geohash(item_list[0], ori)
        dis2 = geohash.get_distance_geohash(item_list[1], ori)
        log("dis1:", dis1, "dis2", dis2)

        if dis1 > dis_threshold and dis2 > dis_threshold:
            continue
        else:
            log("将判断出的目的地加入结果")
            if dis1 > dis2:
                result_tmp.update(geohash.expand(item_list[0]))
            else:
                result_tmp.update(geohash.expand(item_list[1]))

    # 判断结果：如果结果中有实际目的地，则认为预测成功
    log("Result: ", result_tmp)
    # result = set()
    # for value in result_tmp:
    #     result.update(geohash.expand(value))
    # log("Result expanded:", result)
    des_num += len(result_tmp)
    for r in result_tmp:
        if des in geohash.expand(r):
            right_num += 1
            log("接受")
            break

    log("----------------------------------------------------------")

print("预测总数", pre_num)
print("无效个数", invalid_num)
print("召回率", right_num / pre_num)
print("平均目的地个数", des_num / pre_num)
