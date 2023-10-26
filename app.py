from datetime import datetime
import time
import requests
import json
import random 
import pymysql
import os


def connect_db(host, user, pwd, dbname, port):
    try:
        db = pymysql.connect(
            host = host,
            user = user,
            passwd = pwd,
            database = dbname,
            port = int(port)
        )
        # print("連線成功")
        return db
    except Exception as e:
        print('連線資料庫失敗: {}'.format(str(e)))
    return None


if __name__ == '__main__':

    url = "https://www.twfood.cc/api/FarmTradeSumMonths" # 台灣當季蔬果API網址
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36'
    }

    params = { # Request傳送的參數
        "filter": {
            "order": "endDay asc",
            "where":{
                "itemCode": "LB1", # 基本上只要改這個作物代號就好
                "startDay": { # 從哪個時間點開始抓取
                    "gte":"2020/01/01"
                }
            }
        }
    }

    db = connect_db(
        host='127.0.0.1',
        user='root',
        pwd='Ru,6e.4vu4wj/3',
        dbname='greenhouse',
        port=3306,
    ) # 資料庫連線

    if( not db ):
        print("資料庫連線發生問題")
        

    # products = [ # 農產品列表
    #     { "code": "LB1", "name": "小白菜" },
    #     # { "code": "LC1", "name": "不結球白菜類" }, # 包心白菜-包白
    #     # { "code": "LA1", "name": "甘藍" },
    # ]
    product_path = os.path.join( os.getcwd(), 'json', 'products.json' )
    
    with open(product_path, 'r', encoding="utf8") as json_file: # 讀取 JSON檔案
        products = json.load(json_file) # regions變數為所有要抓取鄉鎮資訊

    for product in products:
        params['filter']["where"]["itemCode"] = product["code"] # 修改查詢的農產品Code
        
        # 抓取近兩個月的資料(由於其資料都是隔日才更新，因此會有跨月的情況)
        now = datetime.now()
        month_start = datetime(now.year, now.month - 1, 1) # month - 1
        params['filter']["where"]["startDay"]["gte"] = month_start.strftime("%Y/%m/%d") # 修改查詢的時間點

        new_params = { 'filter': '' } # 新增一個新的 params(主要用於Request傳送)
        new_params['filter'] = json.dumps(params['filter']) # 將 Dict轉成字串(由於其params過去的值須為字串)
        response = requests.get(url, headers=headers, params=new_params)   # 通過requests獲取資訊

        veg_code = product["code"] # 作物代號
        name = product["name"] # 作物名稱

        print( f'【{ veg_code }】 { name }' )
        if(response.status_code == 200):
            # print(response.url)
            text = response.text
            datas = json.loads(text)
            for data in datas:
                year = data["year"]
                month = data["month"]
                weight = data["kg"]
                price = data["avgPrice"]
                endDay = data["endDay"]

                print(data)
                
                cursor = db.cursor()
                # 找尋資料庫有無資料
                sql = f"""SELECT * FROM vegetable_market WHERE `veg_code` = '{ veg_code }' and `year` = '{year}' and `month` = '{month}'"""
                cursor.execute(sql)
                result = cursor.fetchone() # 找不到時會回傳 "None"
                if( result ):
                    
                    with db.cursor() as cursor: # 資料處理好後，進行資料庫新增動作
                        updateCommand = "UPDATE `vegetable_market`  SET `weight` = %s, `price` = %s, `endDay` = %s WHERE `veg_code` = %s and `year` = %s AND `month` = %s;"
                        cursor.execute(updateCommand, ( weight, price, data['endDay'], veg_code, year, month ))
                    #儲存變更
                    db.commit()

                    print(f"【{year}-{month}】更新成功 (time: {endDay})")
                else:
                    with db.cursor() as cursor: # 資料處理好後，進行資料庫新增動作
                        insertCommand = "INSERT INTO `vegetable_market` (`weight`, `price`, `month`, `year`, `endDay`, `veg_code`) VALUES (%s, %s, %s, %s, %s, %s)"
                        cursor.execute(insertCommand, ( weight, price, month, year, data['endDay'], veg_code ))
                    #儲存變更
                    db.commit()
                    print(f"【{year}-{month}】新增成功 (time: {endDay})")
            
            print("---------------------------------\n")

        time.sleep(random.randint(1, 3)) # 美抓一筆Delay時間 1~3秒(不要沒設，不然會被鎖IP)
    

    
