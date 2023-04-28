# -*- coding: utf-8 -*-
#
#  Pax2Weather Converter
#
#  Coded by oerlgrey
#  Based on teamBlue image source code
#
#  This code is licensed under the Creative Commons 
#  Attribution-NonCommercial-ShareAlike 3.0 Unported 
#  License. To view a copy of this license, visit
#  http://creativecommons.org/licenses/by-nc-sa/3.0/ 
#  or send a letter to Creative Commons, 559 Nathan 
#  Abbott Way, Stanford, California 94305, USA.
#
#  If you think this license infringes any rights,
#  please contact me at ochzoetna@gmail.com

from __future__ import absolute_import
from __future__ import print_function
from Components.Converter.Converter import Converter
from Components.Element import cached
from Components.config import config
from enigma import eTimer
import requests, json
from time import strftime, gmtime
from datetime import datetime
from Components.Converter.Poll import Poll
from Plugins.Extensions.PaxWeather import ping

WEATHER_DATA = None
WEATHER_LOAD = True

class Pax2Weather(Poll, Converter, object):
	def __init__(self, type):
		_type = type
		Poll.__init__(self)
		Converter.__init__(self, type)
		self.poll_interval = 60000
		self.poll_enabled = True
		_type = _type.split(',')
		self.day_value = _type[0]
		self.type = _type[1]
		self.timer = eTimer()
		self.timer.callback.append(self.reset)
		self.timer.callback.append(self.get_Data)
		self.data = None
		self.zerolist = [0] * 24
		self.nalist = ["na"] * 24
		self.get_Data()

	@cached
	def getText(self):
		global WEATHER_DATA

		self.data = WEATHER_DATA
		day = self.day_value.split('_')[1]
		if self.type == "DayTemp":
			return self.getDayTemp()
		elif self.type == 'MinTemp':
			return self.getMinTemp(int(day))
		elif self.type == 'MaxTemp':
			return self.getMaxTemp(int(day))
		elif self.type == "MeteoFont":
			return self.getMeteoFont(int(day))
		else:
			return ""

	text = property(getText)

	def reset(self):
		global WEATHER_LOAD

		WEATHER_LOAD = True
		self.timer.stop()

	def get_Data(self):
		global WEATHER_DATA
		global WEATHER_LOAD

		if WEATHER_LOAD:
			try:
				r = ping.doOne("8.8.8.8", 1.5)
				if r != None and r <= 1.5:
					print("[PaxWeather]: download from URL")
					timezones = {"-06": "America/Anchorage", "-05": "America/Los_Angeles", "-04": "America/Denver", "-03": "America/Chicago", "-02": "America/New_York", "-01": "America/Sao_Paulo", "+00": "Europe/London", "+01": "Europe/Berlin", "+02": "Europe/Moscow", "+03": "Africa/Cairo", "+04": "Asia/Bangkok", "+05": "Asia/Singapore", "+06": "Asia/Tokyo", "+07": "Australia/Sydney", "+08": "Pacific/Auckland"}
					currzone = timezones.get(strftime("%z", gmtime())[:3], "Europe/Berlin")
					url = 'https://api.open-meteo.com/v1/forecast?longitude=%s&latitude=%s&hourly=temperature_2m,relativehumidity_2m,apparent_temperature,weathercode,windspeed_10m,winddirection_10m,precipitation_probability&daily=sunrise,sunset,weathercode,precipitation_probability_max,temperature_2m_max,temperature_2m_min&timezone=%s&windspeed_unit=kmh&temperature_unit=celsius' % (str(config.plugins.PaxWeather.longitude.value), str(config.plugins.PaxWeather.latitude.value), currzone)
					res = requests.get(url, timeout=3)
					self.data = res.json()
					WEATHER_DATA = self.data
					WEATHER_LOAD = False
			except:
				pass
			timeout = max(15, int(config.plugins.PaxWeather.refreshInterval.value)) * 1000.0 * 60.0
			self.timer.start(int(timeout), True)
		else:
			self.data = WEATHER_DATA

	def getDayTemp(self):
		try:
			if self.data.get("hourly", None) is not None and self.data.get("daily", None) is not None:
				isotime = datetime.now().strftime("%FT%H:00")
				current = self.data.get("hourly", {})
				for idx, time in enumerate(current.get("time", [])):
					if isotime in time:
						value = "%.0f" % current.get("temperature_2m", self.zerolist)[idx]
						return str(value) + "°C"
		except:
			return ""

	def getMinTemp(self, day):
		try:
			if self.data.get("hourly", None) is not None and self.data.get("daily", None) is not None:
				forecast = self.data["daily"]
				if day in range(6):
					value = "%.0f" % forecast.get("temperature_2m_min", self.zerolist)[day]
					return str(value) + '°C'
		except:
			return ""

	def getMaxTemp(self, day):
		try:
			if self.data.get("hourly", None) is not None and self.data.get("daily", None) is not None:
				forecast = self.data["daily"]
				if day in range(6):
					value = "%.0f" % forecast.get("temperature_2m_max", self.zerolist)[day]
					return str(value) + '°C'
		except:
			return ""

	def getMeteoFont(self, day):
		try:
			if self.data.get("hourly", None) is not None and self.data.get("daily", None) is not None:
				if day == 0:
					isotime = datetime.now().strftime("%FT%H:00")
					current = self.data.get("hourly", {})
					for idx, time in enumerate(current.get("time", [])):
						if isotime in time:
							value = int(current.get("weathercode", self.nalist)[idx])
							font = self.setMeteoFont(value)
							return str(font)
				else:
					forecast = self.data["daily"]
					if day in range(6):
						value = int(forecast.get("weathercode", self.zerolist)[day])
						font = self.setMeteoFont(value)
						return str(font)
		except:
			return ""

	def setMeteoFont(self, value):
		if value == 0:
			return "B" # sun
		elif value in (1, 2):
			return "H" # sun + cloud
		elif value == 3:
			return "Y" # clouds
		elif value in (45, 48):
			return "M" # fog
		elif value in (95, 96, 99):
			return "P" # thunderstorm
		elif value in (51, 61, 80):
			return "Q" # slight rain
		elif value in (53, 55, 63, 65, 81, 82):
			return "R" # rain
		elif value in (71, 85):
			return "U" # slight snow
		elif value in (73, 75, 86):
			return "W" # snow
		elif value in (56, 57, 66, 67, 77):
			return "X" # sleet
		else:
			return "(" # compass
