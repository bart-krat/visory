from playwright.sync_api import sync_playwright

def run_test():
    with sync_playwright() as p:
        # Launch Chromium (headless=False so you can see it working)
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        # 1. Navigate to the app
        page.goto("http://localhost:5173/")

        # 2. Click "Let AI Get to Know You"
        start_button_selector = "#root > div > div:nth-child(2) > div:nth-child(2) > div > div > div:nth-child(2) > button:nth-child(1) > div:nth-child(2) > div:nth-child(1)"
        page.wait_for_selector(start_button_selector)
        page.click(start_button_selector)

        # 3. Answer the 10 questions
        questions_answers = [
            "Family", "Growth", "Time management", "Yes", "Good",
            "Daily", "Focus", "Reading", "Moderate", "Nature"
        ]
        
        input_selector = "#root > div > div:nth-child(2) > div:nth-child(2) > div > div > div > div:nth-child(3) > input"
        send_button_text = "button:has-text('Send')"

        for answer in questions_answers:
            page.wait_for_selector(input_selector)
            page.fill(input_selector, answer)
            page.click(send_button_text)
            # Short sleep to allow the next question to load if needed
            page.wait_for_timeout(500) 

        # 4. Press "Plan Your Day"
        plan_day_button = "button:has-text('Plan Your Day')"
        page.wait_for_selector(plan_day_button)
        page.click(plan_day_button)

        # 5. Insert tasks into the chat box
        task_input_selector = "input[placeholder='Type your tasks...']"
        task_send_button = "#root > div > div:nth-child(2) > div:nth-child(2) > div > div > div > div:nth-child(3) > button"
        
        page.wait_for_selector(task_input_selector)
        page.fill(task_input_selector, "gym, beach, work, kids, read, movies, run")
        page.click(task_send_button)

        # 6. Click Continue Button
        continue_button = "#root > div > div:nth-child(2) > div:nth-child(2) > div > div > div > div:nth-child(2) > div:nth-child(4) > button"
        page.wait_for_selector(continue_button)
        page.click(continue_button)

        # 7. Write "gym before work which is after kids"
        final_input_selector = "#root > div > div:nth-child(2) > div:nth-child(2) > div > div > div > div:nth-child(3) > div:nth-child(2) > div:nth-child(2) > input[type=text]"
        page.wait_for_selector(final_input_selector)
        page.fill(final_input_selector, "gym before work which is after kids")

        # 8. Click Optimize
        optimize_button = "#root > div > div:nth-child(2) > div:nth-child(2) > div > div > div > div:nth-child(3) > div:nth-child(4) > button"
        page.wait_for_selector(optimize_button)
        page.click(optimize_button)

        # Keep browser open for a few seconds to see result
        page.wait_for_timeout(5000)
        browser.close()

if __name__ == "__main__":
    run_test()