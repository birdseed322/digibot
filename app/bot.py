from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.common.alert import Alert 
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoAlertPresentException, UnexpectedAlertPresentException, TimeoutException,NoSuchElementException
import time
import os
import threading
import requests

VSIP_HEADERS = ['vessel_name', 'agent_name', 'ex_name', 'last_port', 'type', 'next_port', 'flag', 'posn', 'callsign', 'status', 'grt', 'beam', 'loa', 'eta', 'etd', 'dec_arrival', 'dec_departure', 'rep_arrival', 'rep_departure']
MOVEMENT_STATUS_HEADERS = ['date_time', 'from', 'to', 'remarks']

# Retrieving environment variables
LOGIN_URL = os.environ.get('LOGIN_URL') 
USERNAME = os.environ.get('USERNAME')
PASSWORD = os.environ.get('PASSWORD')
VESSEL_NOW_BACKEND_URL = os.environ.get('VESSEL_NOW_BACKEND_URL')

# For boolean values, you might want to convert them to actual boolean types
HEADLESS_MODE = (os.environ.get('HEADLESS_MODE', 'true').lower() == 'true')
DEBUG_MODE = (os.environ.get('DEBUG_MODE', 'false').lower() == 'true')
POST_TO_PRODUCTION = (os.environ.get('POST_TO_PRODUCTION', 'true').lower() == 'true')

if not LOGIN_URL or not USERNAME or not PASSWORD or not VESSEL_NOW_BACKEND_URL:
    raise ValueError("Missing one or more required environment variables.")

def dom_is_loaded(driver):
    return driver.execute_script("return document.readyState") == "complete"

class Bot():
    def __init__(self):
        self.driver = self.initialize_driver()
        self.logged_in = False
        self.waiting_on_otp = False
        self.job_queue = []
        self.login()
        self.init_search_interval()
    
    def initialize_driver(self):
        print("Initiating driver")
        options = Options()
        if HEADLESS_MODE:
            options.add_argument('--headless=new')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
        options.unhandled_prompt_behavior = 'dismiss'
        print(options.unhandled_prompt_behavior)
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        return driver
    
    def init_search_interval(self):
        def clear_array():
            while True:
                time.sleep(30)  # Wait for 30 seconds
                print("SEARCHING NOW")
                self.search()
        thread = threading.Thread(target=clear_array)
        thread.daemon = True  # Ensure the thread will exit when the main program exits
        thread.start()
        
    def check_login_status(self):
        try:
            self.driver.find_element(By.CLASS_NAME, 'logout') # Check for a specific element that only appears when logged in
            self.logged_in = True
            return True
        except NoSuchElementException:
            self.logged_in = False
            return False
    
    def restart(self):
        if not self.waiting_on_otp and self.driver != None:
            print("Restarting")
            self.driver.close()
            self.driver = None
            self.driver = self.initialize_driver()
            self.logged_in = False
            self.job_queue = []
            self.login()
                 
    def add_to_job_queue(self, vessel_name, callsign):
        print("Adding " + vessel_name + " (" + callsign + ")")
        self.job_queue.append((vessel_name, callsign))
        return "Added"
            
    def login(self):
        while True:
            try:
                self.driver.get(LOGIN_URL)
                # Find and fill the username field
                try:
                    print("Finding Digiport login option")
                    login_options = self.driver.find_elements(By.CLASS_NAME, 'pre-login-nav-item')
                except:
                    print("Closing announcement")
                    close_announcement = self.driver.find_element(By.CSS_SELECTOR, '#heading-one > i')
                    close_announcement.click()
                login_options = self.driver.find_elements(By.CLASS_NAME, 'pre-login-nav-item')
                username_pw_login_option = login_options[2]
                username_pw_login_option.click()
                login_input = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "#my-tab-content > form > div > div:nth-child(1) > div > input"))
                )
                pw_input = self.driver.find_element(By.CSS_SELECTOR, '#my-tab-content > form > div > div:nth-child(2) > div > div > input')
                login_input.send_keys(USERNAME)
                pw_input.send_keys(PASSWORD)
                submit_btn = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "#my-tab-content > form > div > div.col-md-12.mt-2 > div > div.col-md-5.col-md-offset-2.col-sm-3 > div > button"))
                )
                submit_btn.click()
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_all_elements_located((By.CLASS_NAME, "otp-input"))
                )
                print("OTP sent")
                self.waiting_on_otp = True
                
                break
            except:
                continue
        
    def handle_otp(self, otp):
        if self.logged_in or not self.waiting_on_otp:
            return
        try:
            # Handle OTP if necessary
            otp_inputs = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_all_elements_located((By.CLASS_NAME, "otp-input"))
                    )
            if DEBUG_MODE:
                otp_code = input("Enter OTP: ")
            else: 
                otp_code = otp
                print("Waiting to pull from email")
                
            otp_indx = 0
            for num in otp_code:
                otp_inputs[otp_indx].send_keys(int(num))
                otp_indx += 1
            submit_otp_btn = self.driver.find_element(By.CSS_SELECTOR, 'body > ngb-modal-window > div > div > msw-otp-conformation-dialog > div > div > div.col-lg-12.d-flex.justify-content-center.pt-4 > button')
            submit_otp_btn.click()
            try:
                print("Trying to find vessel info tab")
                vessel_information_tab = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "step0-tab defaultOpen"))
                )
                time.sleep(2)
                vessel_information_tab = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.ID, "step0-tab defaultOpen"))
                )
                vessel_information_tab.click()
            except:
                print("Trying to find select option")
                nav_tabs = Select(WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#dropdownService > div > div > select"))
                ))
                nav_tabs.select_by_visible_text('VESSEL INFORMATION ')
            vsip_link = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#step0 > div:nth-child(12) > div:nth-child(5) > a"))
            )
            vsip_link.click()
            self.logged_in = True
            self.waiting_on_otp = False
            WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.NAME, 'vsl'))
                )
            print("Successfully handled OTP. Ready to Search.")
        except:
            self.waiting_on_otp = False
    
    def search(self):
        try:
            if self.waiting_on_otp:
                return None
            elif not self.logged_in:
                self.check_login_status()
                if not self.logged_in:
                    print("Not logged in. Logging in now...")
                    self.login()
            vessel_results = []
            if len(self.job_queue) != 0:
                for vessel_name, callsign in self.job_queue:
                    print(f"Searching for: {vessel_name}({callsign})")
                    vessel_name_input = WebDriverWait(self.driver, 10).until(
                            EC.presence_of_element_located((By.NAME, 'vsl'))
                        )
                    vessel_name_input.send_keys(vessel_name)
                    vessel_name_submit_btn = self.driver.find_element(By.NAME,'searchforVSIP')
                    vessel_name_submit_btn.click()
                    original_window = self.driver.current_window_handle
                    WebDriverWait(self.driver,10).until(dom_is_loaded)
                    try:
                        search_result = self.driver.find_element(By.CSS_SELECTOR, 'body > div:nth-child(26) > form > table:nth-child(3) > tbody')
                        search_result = search_result.find_elements(By.TAG_NAME, 'tr')
                        selected = False
                        if len(search_result) > 2:
                            for row in search_result[1:]:
                              current_callsign = row.find_elements(By.TAG_NAME, 'td')[1].find_element(By.TAG_NAME, 'div').text
                              if (current_callsign.lower() == callsign.lower()):
                                row.find_elements(By.TAG_NAME, 'td')[0].click()
                                selected = True
                                break
                        
                        if not selected:
                          raise Exception("Results failed")
                        vsip_confirm = self.driver.find_element(By.NAME, 'vsip')
                        vsip_confirm.click()
                        Alert(self.driver).accept()
                        
                        '''
                        Driver waits for new window to be created. Sometimes UnexpectedAlertPresentException is thrown before new window is created,
                        which prevents new window from creating, therefore exception is added to ignored_exception.
                        '''
                        WebDriverWait(self.driver, 3, poll_frequency=0.1, ignored_exceptions=[UnexpectedAlertPresentException]).until(EC.new_window_is_opened(self.driver.window_handles))
                        # Entering paywall
                        if (len(self.driver.window_handles) > 1):
                            for window_handle in self.driver.window_handles:
                                if window_handle != original_window:
                                    self.driver.switch_to.window(window_handle)
                                    try:
                                        Alert(self.driver).accept()
                                    except:
                                        pass
                                    break
                        else:
                            print("No Windows!")
                                
                        vsip = {}
                        vsip_table = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'body > form > table:nth-child(2) > tbody')))
                        vsip_details = vsip_table.find_elements(By.CLASS_NAME, 'pgeBody6')
                        for indx in range(0, len(vsip_details)):
                            vsip[VSIP_HEADERS[indx]] = vsip_details[indx].text
                        vsip_purpose_table = self.driver.find_element(By.CSS_SELECTOR, 'body > form > table:nth-child(3) > tbody > tr > td.pgeBody6 > table')
                        vsip_purposes = vsip_purpose_table.find_elements(By.TAG_NAME, 'td')
                        purposes = []
                        for purpose in vsip_purposes:
                            if purpose.text.strip() != "":
                                purposes.append(purpose.text)
                        vsip['purposes'] = purposes
                        movement_status = []
                        vsip_movement_status_table = self.driver.find_element(By.CSS_SELECTOR, 'body > form > table:nth-child(7) > tbody')
                        vsip_movement_status = vsip_movement_status_table.find_elements(By.TAG_NAME, 'tr')
                        for vsip_movement_status in vsip_movement_status:
                            if vsip_movement_status.get_attribute('bgcolor') != '#3399CC':
                                    movement = {}
                                    cols = vsip_movement_status.find_elements(By.TAG_NAME, 'td')
                                    for indx in range(1, len(cols)):
                                        movement[MOVEMENT_STATUS_HEADERS[indx - 1]] = cols[indx].text
                                    movement_status.append(movement)
                        vsip['movement_status'] = movement_status
                        self.driver.close()
                        self.driver.switch_to.window(original_window)
                        search_again = self.driver.find_element(By.NAME, 'searchAgain')
                        search_again.click()
                        WebDriverWait(self.driver, 10).until(
                                        EC.presence_of_element_located((By.NAME, 'vsl'))
                                    )
                        vessel_results.append(vsip)
                    except Exception as e:
                        print(e) 
                        back_btn = self.driver.find_element(By.NAME, 'back')
                        back_btn.click()
                        print("No such vessel found")
                        vessel_results.append({
                            "vessel_name": vessel_name
                        })
                        WebDriverWait(self.driver, 10).until(
                                        EC.presence_of_element_located((By.NAME, 'vsl'))
                                    )
                        print("Ready to search again")
                self.job_queue.clear()
                print(vessel_results)
                # Make post request to backend server with the results
                if POST_TO_PRODUCTION:
                    print("Sending results to vessel now backend: " + VESSEL_NOW_BACKEND_URL)
                    vessel_now_res = requests.post(VESSEL_NOW_BACKEND_URL + '/api/vessel-status-in-port/receive', json= {
                        'vsip_results': vessel_results
                    })
                    if vessel_now_res.status_code == 204:
                        print("Successfully Sent results")
                    else:
                        print("Failed to send to VesselNow backend")
                    
                return vessel_results
            else:
                self.driver.refresh()
                return None
        except Exception as e:
            print("Error occured")
            print(e)
            self.restart()
            return None