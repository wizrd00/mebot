#!/usr/bin/python3

from _config import *
from _types import *
from playwright.sync_api import sync_playwright, Page
import sys
import os
import time
import random
import json

driver = sync_playwright().start()
browser = driver.chromium.launch(headless = False if OPEN_BROWSER_WINDOW else True)
context = browser.new_context(
	locale = BROWSER_LOCALE,
	color_scheme = BROWSER_THEME,
	strict_selectors = True
)
main_page = context.new_page()
course_page = None
file = open(SCHEDULE_JSON_FILE_PATH)
schedule = json.load(file)
file.close()

def get_today_name() -> str :
	os.environ["TZ"] = TIMEZONE_NAME
	time.tzset()
	return time.strftime("%A")

def clear_cookies() -> None :
	context.clear_cookies()

def goto_login_page_action(args : dict, event : Event) -> None :
	Logger.log(LogType.TRACE, "Goto login page")
	main_page.goto(args["url"], timeout = args["timeout"])
	main_page.wait_for_load_state()
	return

def login_operation_action(args : dict, event : Event) -> None :
	Logger.log(LogType.TRACE, "Logging")
	main_page.fill("input[id='username']", args["username"])
	main_page.fill("input[id='password']", args["password"])
	main_page.get_by_role("button", name = "ورود به سایت").click()
	main_page.wait_for_load_state()
	return

def goto_preview_course_page_action(args : dict, event : Event) -> None :
	Logger.log(LogType.TRACE, f"Goto {str(event)} course preview page")
	main_page.goto(event.url, timeout = args["timeout"])
	main_page.wait_for_load_state()
	return

def participate_course_action(args : dict, event : Event) -> None :
	Logger.log(LogType.TRACE, f"Participating in course {str(event)}")
	with main_page.expect_popup(timeout = args["timeout"]) as popup_info :
		main_page.get_by_role("link", name = "پیوستن به جلسه").click(timeout = args["timeout"])
	Logger.log(LogType.TRACE, "The course has started")
	course_page = popup_info.value
	course_page.wait_for_load_state()
	bigbluebutton_page.get_by_role("button", name = "بستن").click()
	course_page.wait_for_load_state()
	bigbluebutton_page.get_by_role("button", name = "بستن").click()
	return

def wait_course_finish_action(args : dict) -> None :
	Logger.log(LogType.TRACE, "Wait for the course to end")
	with course_page.expect_event("close", timeout = 0) :
		pass
	return

def main() -> None :
	username = sys.argv[1]
	password = sys.argv[2]
	even_or_odd = sys.argv[3]
	today = get_today_name()
	events = [Event(event["name"], event["start"], event["end"], event["url"]) for event in schedule["even_weeks" if (even_or_odd == "even") else "odd_weeks"][today]]
	web_actions = [
		WebAction("goto_login_page", Action({"url" : LOGIN_PAGE_URL, "timeout" : LOGIN_PAGE_TIMEOUT}, goto_login_page_action)),
		WebAction("login_operation", Action({"username" : username, "password" : password}, login_operation_action)),
		WebAction("goto_preview_course_page", Action({"timeout" : PREVIEW_COURSE_PAGE_TIMEOUT}, goto_preview_course_page_action)),
		WebAction("participate_course", Action({"timeout" : POPUP_COURSE_PAGE_TIMEOUT}, participate_course_action)),
		WebAction("wait_course_finish", Action({}, wait_course_finish_action))
	]
	Logger.log(LogType.TRACE, "Start running the scheduler")
	scheduler = Scheduler(events, web_actions, clear_cookies)
	try :
		scheduler.run()
	except KeyboardInterrupt :
		sys.exit()
	else :
		context.close()
		browser.close()
	return

if __name__ == "__main__" :
	if (len(sys.argv) > 3) :
		main()
	else :
		raise TypeError("The mebot needs username, password and evenness or oddness")
