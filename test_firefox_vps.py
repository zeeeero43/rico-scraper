from selenium import webdriver
from selenium.webdriver.firefox.options import Options

options = Options()
options.add_argument('--headless')
options.binary_location = '/usr/bin/firefox-esr'

print('Starting Firefox...')
driver = webdriver.Firefox(options=options)
print('Firefox started!')
driver.get('https://google.com')
print('Title:', driver.title)
driver.quit()
print('Success!')
