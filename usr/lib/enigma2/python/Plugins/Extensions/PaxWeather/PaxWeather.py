# -*- coding: utf-8 -*-
#
#  PaxWeather Plugin for teamBlue-image
#
#  Coded/Modified/Adapted by oerlgrey
#  Based on teamBlue image source code
#  Thankfully inspired by MyMetrix by iMaxxx
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
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Screens.Standby import TryQuitMainloop
from Components.ActionMap import ActionMap
from Components.config import config, configfile, ConfigSubsection, getConfigListEntry, ConfigSelection, ConfigText
from Components.ConfigList import ConfigListScreen
from Components.Sources.StaticText import StaticText
from Components.Label import Label
from Components.Language import language
import gettext, time, os, requests
from enigma import eTimer
from Tools.Directories import fileExists, resolveFilename, SCOPE_LANGUAGE, SCOPE_PLUGINS
from shutil import move, copyfile

python3 = False
try:
	import six
	if six.PY2:
		python3 = False
	else:
		python3 = True
except ImportError:
	python3 = False

lang = language.getLanguage()
os.environ["LANGUAGE"] = lang[:2]
gettext.bindtextdomain("enigma2", resolveFilename(SCOPE_LANGUAGE))
gettext.textdomain("enigma2")
gettext.bindtextdomain("PaxWeather", "%s%s" % (resolveFilename(SCOPE_PLUGINS), "Extensions/PaxWeather/locale/"))

def _(txt):
	t = gettext.dgettext("PaxWeather", txt)
	if t == txt:
		t = gettext.gettext(txt)
	return t

def translateBlock(block):
	for x in TranslationHelper:
		if block.__contains__(x[0]):
			block = block.replace(x[0], x[1])
	return block

config.plugins.PaxWeather = ConfigSubsection()
config.plugins.PaxWeather.activate = ConfigSelection(default="weather-off", choices=[
				("weather-off", _("off")),
				("weather-on", _("on"))
				])

config.plugins.PaxWeather.searchby = ConfigSelection(default="auto-ip", choices=[
				("auto-ip", _("IP")),
				("location", _("Enter location manually"))
				])

config.plugins.PaxWeather.refreshInterval = ConfigSelection(default="0", choices=[
				("0", _("0")),
				("120", _("120"))
				])

config.plugins.PaxWeather.cityname = ConfigText(default="")
config.plugins.PaxWeather.latitude = ConfigText(default="")
config.plugins.PaxWeather.longitude = ConfigText(default="")

class PaxWeather(ConfigListScreen, Screen):
	skin = """
			<screen name="PaxWeather" position="0,0" size="1280,720" flags="wfNoBorder" backgroundColor="#ff002b57">
				<widget source="global.CurrentTime" render="Label" position="227,3" size="100,45" font="Regular; 32" backgroundColor="#10000000" transparent="1" zPosition="1" halign="center">
					<convert type="ClockToText">Default</convert>
				</widget>
				<ePixmap position="0,0" size="940,53" pixmap="/usr/share/enigma2/GigabluePaxV2/construct/menu-top.png" alphatest="blend" zPosition="-2"/>
				<ePixmap position="0,265" size="1280,242" pixmap="/usr/share/enigma2/GigabluePaxV2/construct/menu-band.png" alphatest="blend" zPosition="-2"/>
				<widget source="Title" render="Label" position="369,0" size="540,46" font="SetrixHD; 35" backgroundColor="#10000000" transparent="1"/>
				<widget name="config" position="492,86" size="700,150" itemHeight="30" scrollbarMode="showOnDemand" enableWrapAround="1" backgroundColor="#10000000" transparent="1"/>
				<eLabel position="476,70" zPosition="-1" size="735,585" backgroundColor="#10000000"/>
				<widget source="help" render="Label" position="492,380" size="700,310" backgroundColor="#10000000" transparent="1" zPosition="1" foregroundColor="#00fcc000" font="Regular; 20" halign="center" valign="center"/>
				<widget source="key_red" render="Label" position="500,685" size="180,26" zPosition="2" font="Regular; 20" halign="left" backgroundColor="#10000000" transparent="1"/>
				<widget source="key_green" render="Label" position="700,685" size="180,26" zPosition="2" font="Regular; 20" halign="left" backgroundColor="#10000000" transparent="1"/>
				<widget source="key_yellow" render="Label" position="900,685" size="215,26" zPosition="2" font="Regular; 20" halign="left" backgroundColor="#10000000" transparent="1"/>
				<ePixmap pixmap="/usr/share/enigma2/GigabluePaxV2/construct/plugins/teamblue.png" position="149,284" size="200,200" alphatest="blend"/>
				<ePixmap pixmap="/usr/share/enigma2/GigabluePaxV2/buttons/key_red.png" position="475,680" size="30,40" alphatest="blend"/>
				<ePixmap pixmap="/usr/share/enigma2/GigabluePaxV2/buttons/key_green.png" position="675,680" size="30,40" alphatest="blend"/>
				<ePixmap pixmap="/usr/share/enigma2/GigabluePaxV2/buttons/key_yellow.png" position="875,680" size="30,40" alphatest="blend"/>
				<ePixmap position="1103,680" size="94,40" pixmap="/usr/share/enigma2/GigabluePaxV2/buttons/ok.png" alphatest="blend" zPosition="1"/>
				<ePixmap position="1183,680" size="94,40" pixmap="/usr/share/enigma2/GigabluePaxV2/buttons/buttonbar_exit.png" alphatest="blend" zPosition="1"/>
				<ePixmap position="475,680" size="900,40" pixmap="/usr/share/enigma2/GigabluePaxV2/construct/general/button-back.png" zPosition="-2" alphatest="blend"/>
			</screen>
			"""

	def __init__(self, session, args=None):
		self.skin_lines = []
		Screen.__init__(self, session)
		self.session = session
		copyfile("/usr/share/enigma2/GigabluePaxV2/skin.xml", "/usr/lib/enigma2/python/Plugins/Extensions/PaxWeather/skin.xml")
		self.xmlfile = "/usr/lib/enigma2/python/Plugins/Extensions/PaxWeather/skin.xml"
		self.skinfile = "/usr/share/enigma2/GigabluePaxV2/skin.xml"
		self.skinfile_tmp = self.skinfile + ".tmp"

		list = []
		ConfigListScreen.__init__(self, list)

		self["actions"] = ActionMap(["OkCancelActions", "DirectionActions", "ColorActions", "InputActions"],
		{
			"up": self.keyUp,
			"down": self.keyDown,
			"left": self.keyLeft,
			"right": self.keyRight,
			"red": self.exit,
			"green": self.save,
			"yellow": self.getWeatherData,
			"cancel": self.exit,
			"ok": self.OK,
		}, -2)

		self["key_red"] = StaticText(_("Exit"))
		self["key_green"] = StaticText(_("Save"))
		self["key_yellow"] = StaticText()
		self["Title"] = StaticText(_("PaxWeather-Settings"))
		self["help"] = StaticText()

		self.timer = eTimer()
		self.timer.callback.append(self.updateMylist)
		self.onLayoutFinish.append(self.updateMylist)

		self.InternetAvailable = self.getInternetAvailable()

	def mylist(self):
		self.timer.start(100, True)

	def updateMylist(self):
		list = []
		list.append(getConfigListEntry(_("PaxWeather"), config.plugins.PaxWeather.activate, _("Activate or deactivate the weather widget.")))
		if config.plugins.PaxWeather.activate.value == "weather-on":
			list.append(getConfigListEntry(_("Search option"), config.plugins.PaxWeather.searchby, _("Choose from different options to enter your settings.\nThen press the yellow button to search for the coordinates.")))
			if config.plugins.PaxWeather.searchby.value == "location":
				list.append(getConfigListEntry(_("Location "), config.plugins.PaxWeather.cityname, _("Enter your location.\nPress OK to use the virtual keyboard.\nThen press the yellow button to search for the coordinates.")))

		self["config"].list = list
		self["config"].l.setList(list)
		self.updateHelp()
		self.showYellowText()

	def updateHelp(self):
		cur = self["config"].getCurrent()
		if cur:
			self["help"].text = cur[2]

	def showYellowText(self):
		option = self["config"].getCurrent()[1]
		if option in (config.plugins.PaxWeather.searchby, config.plugins.PaxWeather.cityname):
			self["key_yellow"].text = _("Find coordinates")
		else:
			self["key_yellow"].text = ""

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.mylist()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.mylist()

	def keyDown(self):
		self["config"].instance.moveSelection(self["config"].instance.moveDown)
		self.mylist()

	def keyUp(self):
		self["config"].instance.moveSelection(self["config"].instance.moveUp)
		self.mylist()

	def getWeatherData(self):
		if self.InternetAvailable and config.plugins.PaxWeather.activate.value == "weather-on":
			option = self["config"].getCurrent()[1]
			if option.value == "auto-ip" or (option.value == "location" and config.plugins.PaxWeather.cityname.value in ("", " ")) or (option == config.plugins.PaxWeather.cityname and config.plugins.PaxWeather.cityname.value in ("", " ")):
				self.getCityByIP(False)
			elif (option.value == "location" and not config.plugins.PaxWeather.cityname.value in ("", " ")) or (option == config.plugins.PaxWeather.cityname and not config.plugins.PaxWeather.cityname.value in ("", " ")):
				try:
					res = requests.request('get', 'http://dev.virtualearth.net/REST/v1/Locations/' + str(config.plugins.PaxWeather.cityname.value) + '?&key=Amdqp42KR1c0kHZjTSFXtovl5Y-YridPCqZFguFnvFk6TbW-ITF8jdINSt0jqUQ2', timeout=3)
					data = res.json()
					reslist = []
					for idx, locations in enumerate(data['resourceSets'][0]['resources']):
						city = data['resourceSets'][0]['resources'][int(idx)]['address']['locality']
						region = data['resourceSets'][0]['resources'][int(idx)]['address']['countryRegion']
						lat = data['resourceSets'][0]['resources'][int(idx)]['geocodePoints'][0]['coordinates'][0]
						lon = data['resourceSets'][0]['resources'][int(idx)]['geocodePoints'][0]['coordinates'][1]
						reslist.append((city + " / " + region, lat, lon))
					if len(reslist) > 0:
						self.session.openWithCallback(self.LocationCallBack, ChoiceBox, list=reslist)
					else:
						self.getCityByIP(True)
				except:
					self.getCityByIP(True)

	def LocationCallBack(self, callback):
		if callback:
			config.plugins.PaxWeather.latitude.value = str(callback[1])
			config.plugins.PaxWeather.latitude.save()
			config.plugins.PaxWeather.longitude.value = str(callback[2])
			config.plugins.PaxWeather.longitude.save()
			self.session.open(MessageBox, _("Location found:") + "\n" + str(callback[0]) + "\n\n" + _("latitude: ") + str(callback[1]) + "\n" + _("longitude: ") + str(callback[2]), MessageBox.TYPE_INFO, timeout=8)

	def getCityByIP(self, failed):
		city = ""
		lat = ""
		lon = ""

		try:
			res_city = requests.get('http://ip-api.com/json/?lang=de&fields=status,city,lat,lon,country', timeout=2)
			data = res_city.json()
			if data['status'] == 'success':
				city = data['city']
				region = data['country']
				lat = data['lat']
				lon = data['lon']
				if failed:
					config.plugins.PaxWeather.cityname.value = ""
					config.plugins.PaxWeather.cityname.save()
					self.session.open(MessageBox, _("No valid location found.") + "\n" + _("Fallback to IP.") + "\n\n" + _("Location found:") + "\n" + str(city) + " / " + str(region) + "\n\n" + _("latitude: ") + str(lat) + "\n" + _("longitude: ") + str(lon), MessageBox.TYPE_INFO, timeout=10)
				else:
					self.session.open(MessageBox, _("Location found:") + "\n" + str(city) + " / " + str(region) + "\n\n" + _("latitude: ") + str(lat) + "\n" + _("longitude: ") + str(lon), MessageBox.TYPE_INFO, timeout=8)
		except:
			pass

		config.plugins.PaxWeather.latitude.value = str(lat)
		config.plugins.PaxWeather.latitude.save()
		config.plugins.PaxWeather.longitude.value = str(lon)
		config.plugins.PaxWeather.longitude.save()

	def OK(self):
		option = self["config"].getCurrent()[1]

		if option == config.plugins.PaxWeather.cityname:
			text = self["config"].getCurrent()[1].value
			title = _("Enter your location:")
			self.session.openWithCallback(self.VirtualKeyBoardCallBack, VirtualKeyBoard, title=title, text=text)
			config.plugins.PaxWeather.cityname.save()

	def VirtualKeyBoardCallBack(self, callback):
		try:
			if callback:
				self["config"].getCurrent()[1].value = callback
		except:
			pass

	def save(self):
		for x in self["config"].list:
			if len(x) > 1:
				x[1].save()
			else:
				pass

		self.skinSearchAndReplace = []

		if config.plugins.PaxWeather.activate.value == "weather-on":
			if self.InternetAvailable:
				self.skinSearchAndReplace.append(['<!-- <panel name="PANEL_WEATHER_WIDGET_OFF"/> -->', '<panel name="PANEL_WEATHER_WIDGET"/>'])
				self.appendSkinFile(self.xmlfile)
				self.generateSkin()
			else:
				self.session.open(MessageBox, _("Your box needs an internet connection to display the weather widget.\nPlease solve the problem."), MessageBox.TYPE_INFO, timeout=10)
				config.plugins.PaxWeather.activate.value = "weather-off"
				self.mylist()
		else:
			self.skinSearchAndReplace.append(['<panel name="PANEL_WEATHER_WIDGET"/>', '<!-- <panel name="PANEL_WEATHER_WIDGET_OFF"/> -->'])
			self.appendSkinFile(self.xmlfile)
			self.generateSkin()

		if self.InternetAvailable and config.plugins.PaxWeather.activate.value == "weather-on":
			config.plugins.PaxWeather.refreshInterval.value = "120"
			config.plugins.PaxWeather.refreshInterval.save()
		else:
			config.plugins.PaxWeather.refreshInterval.value = "0"
			config.plugins.PaxWeather.refreshInterval.save()

	def generateSkin(self):
		xFile = open(self.skinfile_tmp, "w")
		for xx in self.skin_lines:
			xFile.writelines(xx)
		xFile.close()
		move(self.skinfile_tmp, self.skinfile)
		self.restart()

	def restart(self):
		configfile.save()
		restartbox = self.session.openWithCallback(self.restartGUI, MessageBox, _("GUI needs a restart to apply the settings.\nDo you want to Restart the GUI now?"), MessageBox.TYPE_YESNO)
		restartbox.setTitle(_("Restart GUI?"))

	def appendSkinFile(self, appendFileName):
		"""
		add skin file to main skin content

		appendFileName:
		 xml skin-part to add
		"""

		skFile = open(appendFileName, "r")
		file_lines = skFile.readlines()
		skFile.close()

		tmpSearchAndReplace = []
		tmpSearchAndReplace = self.skinSearchAndReplace

		for skinLine in file_lines:
			for item in tmpSearchAndReplace:
				skinLine = skinLine.replace(item[0], item[1])
			self.skin_lines.append(skinLine)

	def restartGUI(self, answer):
		if answer is True:
			configfile.save()
			self.session.open(TryQuitMainloop, 3)
		else:
			self.close()

	def exit(self):
		askExit = self.session.openWithCallback(self.doExit, MessageBox, _("Do you really want to exit without saving?"), MessageBox.TYPE_YESNO)
		askExit.setTitle(_("Exit?"))

	def doExit(self, answer):
		if answer is True:
			for x in self["config"].list:
				if len(x) > 1:
						x[1].cancel()
				else:
						pass
			self.close()
		else:
			self.mylist()

	def getInternetAvailable(self):
		from . import ping
		r = ping.doOne("8.8.8.8", 1.5)
		if r != None and r <= 1.5:
			return True
		else:
			return False
