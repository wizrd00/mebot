from playwright.sync_api import Page
from playwright._impl._errors import Error, TimeoutError, is_target_closed_error
from enum import Enum
import time

class Status(Enum) :
	SUCCESS = 0
	FAILURE = 1
	TIMEOUT = 2
	TARGET_CLOSE = 3


class LogType(Enum) :
	TRACE = 0
	EVENT = 1
	ERROR = 2


class Logger :
	@staticmethod
	def log(log_type : LogType, log_msg : str) -> None :
		match (log_type) :
			case LogType.TRACE :
				label = "[\x1b[33m+\x1b[0m]"
			case LogType.EVENT :
				label = "[\x1b[32m*\x1b[0m]"
			case LogType.ERROR :
				label = "[\x1b[31m!\x1b[0m]"
		print(f"{label} {log_msg}")
		return


class Event :
	def __init__(self, name : str, start : str, end : str, url : str) :
		self.name = name
		self.start = start
		self.end = end
		self.url = url

	def __str__(self) -> str :
		return f"{self.name}: {self.start} -> {self.end}"

	def passed(self) -> bool :
		"is the event passed or not"
		now = time.strftime("%H:%M")
		return (now >= self.end)

	def remained_time(self) -> int :
		"calculate remained time in second until event passes"
		now = time.strftime("%H:%M")
		end_hour, end_minute = self.end.split(":")
		now_hour, now_minute = now.split(":")
		end_in_second = ((int(end_hour) * 60) + int(end_minute)) * 60
		now_in_second = ((int(now_hour) * 60) + int(now_minute)) * 60
		return (end_in_second - now_in_second)


class Action :
	def __init__(self, args : dict, func : callable) :
		self.args = args
		self.func = func

	def act(self, event : Event) -> None :
		self.func(self.args, event)
		return


class WebAction :
	def __init__(self, name : str, action : Action) :
		self.name = name
		self.action = action
		self.error_message = str()

	def act(self, event : Event) -> Status:
		try :
			self.action.act(event)
		except Error as err :
			self.error_message = str(err)
			return (Status.TARGET_CLOSE if is_target_closed_error(err) else Status.FAILURE)
		except TimeoutError as err :
			self.error_message = str(err)
			return Status.TIMEOUT
		else :
			return Status.SUCCESS


class Scheduler :
	def __init__(self, events : list[Event], actions : WebAction, delete_cookies : callable) :
		self.events = events
		self.actions = actions
		self.delete_cookies = delete_cookies

	def act(self, event : Event) -> Status :
		for action in self.actions :
			match (action.act(event)) :
				case Status.SUCCESS :
					Logger.log(LogType.EVENT, f"WebAction \"{action.name}\" -> SUCCESS")
				case Status.FAILURE :
					Logger.log(LogType.EVENT, f"WebAction \"{action.name}\" -> FAILURE : {action.error_message}")
					return Status.FAILURE
				case Status.TIMEOUT :
					Logger.log(LogType.EVENT, f"WebAction \"{action.name}\" -> TIMEOUT : {action.error_message}")
					return Status.FAILUER
				case Status.TARGET_CLOSE :
					Logger.log(LogType.EVENT, f"WebAction \"{action.name}\" -> TARGET_CLOSE: {action.error_message}")
					return Status.FAILURE
		return Status.SUCCESS

	def run(self) -> None :
		for event in self.events :
			if (event.passed()) :
				Logger.log(LogType.EVENT, f"The event {str(event)} passed")
				continue
			while (not event.passed()) :
				Logger.log(LogType.TRACE, f"Accomplishing the {str(event)} event...")
				if (self.act(event) == Status.SUCCESS) :
					break
				else :
					Logger.log(LogType.ERROR, f"Failed to accomplish the {str(event)} event; try again if it hasn't passed yet...")
					Logger.log(LogType.TRACE, "Clear cookies...")
					self.delete_cookies()
