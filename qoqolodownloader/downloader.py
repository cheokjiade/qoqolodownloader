import os
import shutil
import time
import logging
import requests
import traceback
from datetime import datetime
from dateutil import parser
from dateutil.parser import ParserError
from selenium import webdriver
from selenium.common import NoSuchElementException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pathvalidate import sanitize_filepath
from jproperties import Properties
import piexif
import piexif.helper

logger = logging.getLogger(__name__)


def load_config(config_path):
    """Load config.properties from the given path. Returns a plain dict."""
    configs = Properties()
    with open(config_path, 'rb') as config_file:
        configs.load(config_file)
    return {key: configs.get(key).data for key in configs}


def save_config(config_path, config):
    """Write config dict back to a .properties file."""
    header = (
        "#note: there is almost no error handling and the script will fail on almost every error.\n"
        "#if your child is check in but not out, that month will fail\n"
        "#will not download videos\n"
        "#assumes all images are jpg, so far this is true for me\n"
        "#depends on xpath to navigate through the website which can break easily\n"
        "\n"
    )
    props = Properties()
    for key, value in config.items():
        props[key] = value
    with open(config_path, 'wb') as f:
        f.write(header.encode('utf-8'))
        props.store(f, strip_meta=False)


def setup_directories(config, base_dir=None):
    """Create output directories. Returns (checkinout_dir, activities_dir).
    If base_dir is None, uses CWD (preserving CLI behavior)."""
    childname = config["childname"]
    year = config["signin_year_to_download"]
    childname_dir = str(childname).replace(" ", "_").lower()

    if base_dir:
        full_checkinout_dir = os.path.join(base_dir, childname_dir, year, "checkinout")
        full_activities_dir = os.path.join(base_dir, childname_dir, year, "activities")
    else:
        full_checkinout_dir = os.path.join(childname_dir, year, "checkinout")
        full_activities_dir = os.path.join(childname_dir, year, "activities")

    if not os.path.exists(full_checkinout_dir):
        os.makedirs(full_checkinout_dir)
    if not os.path.exists(full_activities_dir):
        os.makedirs(full_activities_dir)

    return full_checkinout_dir, full_activities_dir


def create_driver():
    """Launch Chrome WebDriver and return the driver instance."""
    return webdriver.Chrome()


def _default_log(message):
    logger.info(message)
    print(message)


def _sleep(config):
    time.sleep(int(config["default_sleep_time"]))


def download_image(image_url, file_path, selenium_driver, exif_datetime=None, exif_comment=None, log_fn=None):
    if log_fn is None:
        log_fn = _default_log
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
            #exif_dict['0th'][piexif.ImageIFD.ImageDescription] = exif_comment
        exif_bytes = piexif.dump(exif_dict)
        piexif.remove(file_path)
        piexif.insert(exif_bytes, file_path)
    log_fn("Downloaded " + file_path)


def do_login(driver, config, log_fn=None):
    """Navigate to login page, fill credentials, submit, select child if needed."""
    if log_fn is None:
        log_fn = _default_log

    driver.get(config["page_login"])
    _sleep(config)
    #fill up login form
    login_name = driver.find_element(By.NAME, 'name')
    login_name.send_keys(config["username"])
    login_password = driver.find_element(By.NAME, 'password')
    login_password.send_keys(config["password"])
    login_password.submit()
    _sleep(config)

    #to handle flow where there is more than 1 child in pcf
    try:
        child_selector = driver.find_element('id', 'mychild-cnt')
        child_selector.find_element(By.XPATH, "//li[contains(text(),'" + config["childname"] + "')]").click()
    except Exception as e:
        log_fn("Child does not need to be selected")
    _sleep(config)


def download_checkin_photos(driver, config, checkinout_dir, log_fn=None, progress_fn=None, cancel_event=None):
    """Download all check-in/check-out photos for configured months."""
    if log_fn is None:
        log_fn = _default_log

    months = config["signin_months_to_download"].split(',')
    year = config["signin_year_to_download"]
    total_months = len(months)
    photos_downloaded = 0

    for month_idx, month in enumerate(months):
        if cancel_event and cancel_event.is_set():
            return

        driver.get(config["page_checkin"] + month + "-" + year)
        _sleep(config)
        try:
            signin_table = driver.find_element(By.XPATH, config["xpath_signin_table"])
        except NoSuchElementException as e:
            log_fn(f"No sign in/out for the month {month}")
            if progress_fn:
                progress_fn(month_idx + 1, total_months)
            continue
        signin_rows = signin_table.find_elements(By.XPATH, ".//tr")
        #iterate through all the rows of the table
        for signin_row in signin_rows:
            if cancel_event and cancel_event.is_set():
                return
            try:
                signin_row_columns = signin_row.find_elements(By.XPATH, ".//td")
                #find the sign in and out values
                is_signin = is_signout = True
                try:
                    sign_in_date_text = parser.parse(signin_row_columns[1].text)
                except ParserError as e:
                    is_signin = False
                    log_fn(f"Failed to parse signin date time: {e}")
                try:
                    sign_out_date_text = parser.parse(signin_row_columns[4].text)
                except ParserError as e:
                    is_signout = False
                    log_fn(f"Failed to parse signout date time: {e}")
                signin_row.find_element(By.XPATH, ".//button").click()
                _sleep(config)
                #open popup
                photos_elements = driver.find_elements(By.XPATH, "//div[@class='form-group' and .//label[contains(text(), 'Photo')]]")
                if is_signin:
                    photo_src = photos_elements[0].find_element(By.XPATH, './/img').get_attribute("src")
                    download_image(photo_src, os.path.join(checkinout_dir, sanitize_filepath(sign_in_date_text.strftime("%Y-%m-%d_%H%M%S") + "_signin.jpg")), driver, sign_in_date_text, "Check-in on " + sign_in_date_text.strftime("%Y:%m:%d %H:%M:%S"), log_fn)
                    photos_downloaded += 1
                if is_signout:
                    photo_src = photos_elements[1].find_element(By.XPATH, './/img').get_attribute("src")
                    download_image(photo_src, os.path.join(checkinout_dir, sanitize_filepath(sign_out_date_text.strftime("%Y-%m-%d_%H%M%S") + "_signout.jpg")), driver, sign_out_date_text, "Check-out on " + sign_out_date_text.strftime("%Y:%m:%d %H:%M:%S"), log_fn)
                    photos_downloaded += 1
                #close the popup
                driver.find_element(By.XPATH, "//button[text()='×']").click()
                WebDriverWait(driver, 10).until(
                    EC.invisibility_of_element_located((By.XPATH, "//div[contains(@class,'view-signin-modal') and contains(@class,'in')]"))
                )
            except Exception as e:
                log_fn(f"Error processing row: {e}")
                log_fn("Likely there is no sign out photo for 1 of the days. If so ignore this error.")

        if progress_fn:
            progress_fn(month_idx + 1, total_months)

    log_fn(f"Check-in/out download complete. {photos_downloaded} photos downloaded.")


def download_activity_photos(driver, config, activities_dir, log_fn=None, progress_fn=None, cancel_event=None):
    """Download all activity photos."""
    if log_fn is None:
        log_fn = _default_log

    driver.get(config["page_activities"])
    _sleep(config)
    html = driver.find_element(By.TAG_NAME, 'html')
    scroll_times = int(config["activities_scroll_times"])
    log_fn(f"Scrolling down {scroll_times} times to load activities...")
    for i in range(scroll_times):
        if cancel_event and cancel_event.is_set():
            return
        html.send_keys(Keys.END)
        time.sleep(1)

    activity_container = driver.find_element(By.XPATH, "//div[@class='infinite-panel posts-container top-lg clearfix']")
    activity_posts = activity_container.find_elements(By.XPATH, config["xpath_activity_posts"])

    posts_with_images = []
    for activity_post in activity_posts:
        post_images = activity_post.find_elements(By.XPATH, config["xpath_activity_post_images"])
        if len(post_images) > 0:
            posts_with_images.append((activity_post, post_images))

    total_posts = len(posts_with_images)
    log_fn(f"Found {total_posts} activity posts with images.")
    photos_downloaded = 0

    for post_idx, (activity_post, post_images) in enumerate(posts_with_images):
        if cancel_event and cancel_event.is_set():
            return

        post_date = parser.parse(activity_post.find_element(By.XPATH, ".//p[@class='text-muted']").text)
        post_title = activity_post.find_element(By.XPATH, ".//a[@class='view-album post-title']").text
        sanitized_post_title = sanitize_filepath(post_title).strip().replace("  ", " ").replace(" ", "_")[:30]
        post_description = activity_post.find_element(By.XPATH, ".//a[@class='view-album post-title']/following::p[1]").text
        post_images[0].click()
        _sleep(config)
        #parse the album
        album_slides = driver.find_element(By.XPATH, "//div[@class='slides']")
        album_images = album_slides.find_elements(By.XPATH, ".//img[@class='slide-content']")
        #handle case where the album has only 1 photo because it wont have the photo selector
        if len(album_images) == 1:
            count = 0
            for album_image in album_images:
                photo_src = album_image.get_attribute("src")
                download_image(photo_src, os.path.join(activities_dir, post_date.strftime("%Y-%m-%d_%H%M%S") + "_" + sanitized_post_title + "_" + f'{count+1:03}' + ".jpg"), driver, post_date, post_title + ": " + post_description, log_fn)
                count = count + 1
                photos_downloaded += 1
        #if more then 1 photo in album, need to click all the items of the carousel because the photos lazy load
        elif len(album_images) > 1:
            album_images = album_slides.find_elements(By.XPATH, ".//div[@class='slide ' and @data-index]")
            album_images_indicator = driver.find_elements(By.XPATH, "//li[@data-index]")
            count = 0
            for indicator in album_images_indicator:
                album_image = driver.find_elements(By.XPATH, "//div[@class='slide ' and @data-index='" + str(count) + "']/img")
                if len(album_image) == 1:
                    photo_src = album_image[0].get_attribute("src")
                    download_image(photo_src, os.path.join(activities_dir, post_date.strftime("%Y-%m-%d_%H%M%S") + "_" + sanitized_post_title + "_" + f'{count+1:03}' + ".jpg"), driver, post_date, post_title + ": " + post_description, log_fn)
                    photos_downloaded += 1
                count = count + 1
                if count < len(album_images_indicator):
                    driver.find_element(By.XPATH, "//li[@data-index='" + str(count) + "']").click()
                    time.sleep(1)
        #close the photo carousel
        driver.find_element(By.XPATH, config["xpath_photo_carousel_close"]).click()
        _sleep(config)

        if progress_fn:
            progress_fn(post_idx + 1, total_posts)

    log_fn(f"Activities download complete. {photos_downloaded} photos downloaded.")


def run_cli():
    """Full CLI workflow - preserves the original script behavior."""
    config = load_config('config.properties')

    checkinout_dir, activities_dir = setup_directories(config)

    driver = create_driver()
    do_login(driver, config)

    if config.get("download_checkin", "no") == "yes":
        download_checkin_photos(driver, config, checkinout_dir)

    if config.get("download_activities", "no") == "yes":
        download_activity_photos(driver, config, activities_dir)

    #driver.quit()
    os.system('pause')


if __name__ == "__main__":
    run_cli()
