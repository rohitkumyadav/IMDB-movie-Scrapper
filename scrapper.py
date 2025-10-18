import time
import random
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

def get_product_info(product_id):
    url = f"https://www.newegg.com/p/pl?d={product_id.replace(' ', '+')}"

    options = uc.ChromeOptions()
    
    # --- DEBUGGING STEP 1: Comment out headless mode to see the browser ---
    # By running with a visible window, we can see if we're stuck on a CAPTCHA.
    # options.add_argument('--headless=new') 
    
    options.add_argument("start-maximized")
    
    driver = uc.Chrome(options=options, use_subprocess=True)

    try:
        print("Fetching page (browser window will open)...")
        driver.get(url)
        time.sleep(random.uniform(2, 4))

        try:
            cookie_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[text()='Accept All']"))
            )
            cookie_button.click()
            print("Cookie banner accepted.")
            time.sleep(random.uniform(1, 2))
        except (TimeoutException, NoSuchElementException):
            print("No cookie banner found or already accepted.")
            pass
        
        product_name = "Name not found"
        product_price = "Price not found"

        # Try search page logic
        try:
            print("Trying to find product in a search list...")
            wait = WebDriverWait(driver, 25)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.item-cells-wrap")))
            product_card = driver.find_element(By.CSS_SELECTOR, "div.item-cell")
            
            name_tag = product_card.find_element(By.CSS_SELECTOR, "a.item-title")
            product_name = name_tag.text

            price_dollar = product_card.find_element(By.CSS_SELECTOR, "li.price-current strong").text
            price_sup = product_card.find_element(By.CSS_SELECTOR, "li.price-current sup").text
            product_price = f"${price_dollar}{price_sup}"

        # Try direct product page logic
        except TimeoutException:
            print("Not a search list. Checking for a direct product page...")
            wait = WebDriverWait(driver, 25)
            name_tag = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "h1.product-title")))
            product_name = name_tag.text

            try:
                price_dollar = driver.find_element(By.CSS_SELECTOR, "li.price-current strong").text
                price_sup = driver.find_element(By.CSS_SELECTOR, "li.price-current sup").text
                product_price = f"${price_dollar}{price_sup}"
            except Exception:
                pass
        
        return {
            "Search Term": product_id,
            "Name": product_name,
            "Price": product_price
        }
    
    except TimeoutException:
        print(f"Error: Timed out waiting for page elements. Saving screenshot for review.")
        
        # --- DEBUGGING STEP 2: Save a screenshot on failure ---
        # This will show us exactly what the browser was seeing when it failed.
        driver.save_screenshot('debug_screenshot.png')
        print("Screenshot saved as 'debug_screenshot.png'")
        
        return {"Search Term": product_id, "Error": "Product not found or page was blocked."}
        
    finally:
        driver.quit()

if __name__ == "__main__":
    search_term = input("Enter a product name or ID to search on Newegg: ").strip()
    if search_term:
        details = get_product_info(search_term)
        print("\n--- Scraped Details ---")
        if details:
            for k, v in details.items():
                print(f"{k}: {v}")
    else:
        print("Please enter a valid search term.")