import os
import shutil
import time
import requests
from datetime import datetime
from dateutil import parser
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from pathvalidate import sanitize_filepath
from jproperties import Properties
import piexif
import piexif.helper


configs = Properties()
with open('config.properties', 'rb') as config_file:
    configs.load(config_file)

username = configs.get("username").data
password = configs.get("password").data
#child name as displayed in the selector if need to select child (if got more than 1 kid in pcf)
childname = configs.get("childname").data
download_checkin = configs.get("download_checkin").data == 'yes' if True else False
download_activities = configs.get("download_activities").data == 'yes' if True else False
#which months to download separated by comma. e.g. to download Feb & June, use 2,6
signin_months_to_download = configs.get("signin_months_to_download").data

checkinout_dir = "checkinout"
activites_dir = "activities"
if not os.path.exists(checkinout_dir):
    os.makedirs(checkinout_dir)
if not os.path.exists(activites_dir):
    os.makedirs(activites_dir)

def download_image(image_url, file_path, selenium_driver, exif_datetime=None, exif_comment=None):
    headers = {
        "User-Agent":
            "Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.157 Safari/537.36"
    }
    s = requests.session()
    s.headers.update(headers)
    for cookie in selenium_driver.get_cookies():
        c = {cookie['name']: cookie['value']}
        s.cookies.update(c)
    response = s.get(image_url, stream=True)

    if response.status_code == 200:
        with open(file_path, 'wb') as out_file:
            response.raw.decode_content = True
            shutil.copyfileobj(response.raw, out_file)

    if exif_datetime or exif_comment:
        exif_dict = piexif.load(file_path)
        if exif_datetime is not None:
            new_date = exif_datetime.strftime("%Y:%m:%d %H:%M:%S")
            exif_dict['0th'][piexif.ImageIFD.DateTime] = new_date
            exif_dict['Exif'][piexif.ExifIFD.DateTimeOriginal] = new_date
            exif_dict['Exif'][piexif.ExifIFD.DateTimeDigitized] = new_date
        if exif_comment is not None:
            exif_dict['Exif'][piexif.ExifIFD.UserComment] = piexif.helper.UserComment.dump(exif_comment, 'unicode')
        exif_bytes = piexif.dump(exif_dict)
        piexif.remove(file_path)
        piexif.insert(exif_bytes, file_path)
        print("Downloaded " + file_path)



driver = webdriver.Chrome()  # Optional argument, if not specified will search path.
driver.get('https://pcfsparkletots.qoqolo.com/')
time.sleep(1) # Let the user actually see something!
#fill up login form
login_name = driver.find_element('name', 'name')
login_name.send_keys(username)
login_password = driver.find_element('name','password')
login_password.send_keys(password)
login_password.submit()
time.sleep(3) # Let the user actually see something!

#to handle flow where there is more than 1 child in pcf
try:
    child_selector = driver.find_element('id', 'mychild-cnt')
    child_selector.find_element('xpath', "//li[contains(text(),'" + childname + "')]").click()
except Exception as e:
    print("Child does not need to be selected")
    #print(e)
time.sleep(3)

#handle sign in / out photos
if download_checkin:
    for month in signin_months_to_download.split(','):
        driver.get("https://pcfsparkletots.qoqolo.com/cos/o.x?c=/ca4q_pep/check_in&func=recent&selectDate=" + month + "-" + str(datetime.now().year))
        time.sleep(3)
        signin_table = driver.find_element(By.XPATH, "//tbody")
        signin_rows = signin_table.find_elements(By.XPATH, ".//tr")
        #iterate through all the rows of the table
        for signin_row in signin_rows:
            signin_row_columns = signin_row.find_elements(By.XPATH, ".//td")
            #find the sign in and out values
            print(signin_row_columns[1].text)
            sign_in_date_text = parser.parse(signin_row_columns[1].text)
            sign_out_date_text = parser.parse(signin_row_columns[4].text)
            signin_row.find_element(By.XPATH, ".//button").click()
            time.sleep(3)
            #open popup
            photos_elements = driver.find_elements(By.XPATH, "//div[@class='form-group' and .//label[contains(text(), 'Photo')]]")
            photo_src = photos_elements[0].find_element(By.XPATH, './/img').get_attribute("src")
            download_image(photo_src, os.path.join(checkinout_dir, sanitize_filepath(sign_in_date_text.strftime("%Y-%m-%d_%H%M%S") + "_signin.jpg")), driver, sign_in_date_text, "Check-in on " + sign_in_date_text.strftime("%Y:%m:%d %H:%M:%S"))
            photo_src = photos_elements[1].find_element(By.XPATH, './/img').get_attribute("src")
            download_image(photo_src, os.path.join(checkinout_dir, sanitize_filepath(sign_out_date_text.strftime("%Y-%m-%d_%H%M%S") + "_signout.jpg")), driver, sign_out_date_text, "Check-out on " + sign_out_date_text.strftime("%Y:%m:%d %H:%M:%S"))
            #close the popup
            driver.find_element(By.XPATH, "//button[text()='×']").click()
            time.sleep(2)
            #print(signin_row_columns[1].text)

#process activities
if download_activities:
    driver.get('https://pcfsparkletots.qoqolo.com/cos/o.x?c=/ca4q_pep/classspace')
    time.sleep(3)
    html = driver.find_element(By.TAG_NAME, 'html')
    for i in range(7):
        html.send_keys(Keys.END)
        time.sleep(1)
    activity_container = driver.find_element(By.XPATH, "//div[@class='infinite-panel posts-container top-lg clearfix']")
    activity_posts = activity_container.find_elements(By.XPATH, ".//div[@class='panel panel-default infinite-item post ']")
    for activity_post in activity_posts:
        #check if there are images
        post_images = activity_post.find_elements(By.XPATH, ".//a[@class='bi-gallery-item' and @data-type='Image' and @src and @data-index='0']")
        if len(post_images) > 0:
            post_date = parser.parse(activity_post.find_element(By.XPATH, ".//p[@class='text-muted']").text)
            post_title = activity_post.find_element(By.XPATH, ".//a[@class='view-album post-title']").text
            sanitized_post_title = sanitize_filepath(post_title).strip().replace("  ", " ").replace(" ", "_")[:30]
            post_description = activity_post.find_element(By.XPATH, ".//a[@class='view-album post-title']/following::p[1]").text
            post_images[0].click()
            time.sleep(2)
            #parse the album
            album_slides = driver.find_element(By.XPATH, "//div[@class='slides']")
            album_images = album_slides.find_elements(By.XPATH, ".//img[@class='slide-content']")
            #handle case where the album has only 1 photo because it wont have the photo selector
            if len(album_images) == 1:
                count = 0
                for album_image in album_images:
                    photo_src = album_image.get_attribute("src")
                    download_image(photo_src, os.path.join(activites_dir, post_date.strftime("%Y-%m-%d_%H%M%S") + "_" + sanitized_post_title + "_" + f'{count+1:03}' + ".jpg"), driver, post_date, post_title + ": " + post_description)
                    count = count + 1
                driver.find_element(By.XPATH, "//a[@class='close']").click()
                time.sleep(2)
            elif len(album_images) > 1:
                album_images = album_slides.find_elements(By.XPATH, ".//div[@class='slide ' and @data-index]")
                album_images_indicator = driver.find_elements(By.XPATH, "//li[@data-index]")
                count = 0
                for indicator in album_images_indicator:
                    album_image = driver.find_elements(By.XPATH, "//div[@class='slide ' and @data-index='" + str(count) + "']/img")
                    if len(album_image) == 1:
                        photo_src = album_image[0].get_attribute("src")
                        download_image(photo_src, os.path.join(activites_dir, post_date.strftime("%Y-%m-%d_%H%M%S") + "_" + sanitized_post_title + "_" + f'{count+1:03}' + ".jpg"), driver, post_date, post_title + ": " + post_description)
                    count = count + 1
                    if count < len(album_images_indicator):
                        driver.find_element(By.XPATH, "//li[@data-index='" + str(count) + "']").click()
                        time.sleep(1)
                driver.find_element(By.XPATH, "//a[@class='close']").click()
                time.sleep(2)
            time.sleep(2)
#driver.quit()
os.system('pause')