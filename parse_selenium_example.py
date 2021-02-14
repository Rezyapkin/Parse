from selenium import webdriver
from selenium.webdriver.common.keys import Keys

if __name__ == '__main__':
    browser = webdriver.Firefox()
    url = 'https://habr.com/ru/'
    browser.get(url)
    print(1)
