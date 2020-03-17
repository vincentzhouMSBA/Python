#通过爬取携程网页上上海飞往深圳的近期价格，通过聚类的方式对所有价格进行聚类分析，从而找出“超低”价格实现不间断检测，并将结果通过IFTTT网站发送到用户手机，实现App功能


import sys
import pandas as pd
import numpy as np
import requests
from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
import schedule
import time

def check_flights():
    url = "https://flights.ctrip.com/itinerary/oneway/sha-szx?date=2020-05-29"
    driver = webdriver.PhantomJS()
    dcap = dict(DesiredCapabilities.PHANTOMJS)
    dcap["phantomjs.page.settings.userAgent"] =("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.130 Safari/537.36")
    driver = webdriver.PhantomJS(desired_capabilities=dcap, service_args=['--ignore-ssl-errors=true'])
    driver.get(url)
    wait = WebDriverWait(driver, 20)

    s = BeautifulSoup(driver.page_source, "lxml")

    best_price_tags = s.findAll('span','base_price02') 

    # check if scrape worked - alert if it fails and shutdown
    if len(best_price_tags) < 4:
        print('Failed to Load Page Data')
        requests.post('https://maker.ifttt.com/trigger/flight_detected/with/key/ilBUoPJsssp0IvMmdTCSZ-3QLeGqaP7TDA2TjF8JItE',data={ "value1" : "script", "value2" : "failed", "value3" : ""})
        sys.exit(0)
    else:
        print('Successfully Loaded Page Data')

    best_prices = []
    for tag in best_price_tags:
        best_prices.append(int(tag.text.replace('¥','')))
    best_prices.sort()
    
    best_price = best_prices[0]

    price = pd.DataFrame(best_prices, columns=['price'])
    px = [x for x in price['price']]
    ff = pd.DataFrame(px, columns=['price']).reset_index()

    # begin the clustering
    X = StandardScaler().fit_transform(ff)
    db = DBSCAN(eps=.5, min_samples=1).fit(X)

    labels = db.labels_
    clusters = len(set(labels))

    pf = pd.concat([ff,pd.DataFrame(db.labels_,columns=['cluster'])], axis=1)
    rf = pf.groupby('cluster')['price'].agg(['min','count']).sort_values('min', ascending=True)

    # set up our rules
    # must have more than one cluster
    # cluster min must be equal to lowest price fare
    # cluster size must be less than 10th percentile
    # cluster must be $100 less the next lowest-priced cluster
    if clusters > 1 and ff['price'].min() == rf.iloc[0]['min']:
#     and rf.iloc[0]['count'] < rf['count'].quantile(.10):
        #price = s.find('span','base_price02').text
        price =  rf.iloc[0]['min']
        r = requests.post('https://maker.ifttt.com/trigger/flight_detected/with/key/ilBUoPJsssp0IvMmdTCSZ-3QLeGqaP7TDA2TjF8JItE',\
         data={ "value1" : "LowPriceFromSHtoSZ", "value2" : price, "value3" : "Buy it!" })
    else:
        print('no alert triggered')

# set up the scheduler to run our code every 60 min
schedule.every(0).minutes.do(check_flights)

while 1:
    schedule.run_pending()
    time.sleep(1)



