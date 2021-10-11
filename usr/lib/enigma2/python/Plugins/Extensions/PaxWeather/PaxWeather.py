# -*- coding: utf-8 -*-
#
#  PaxWeather Plugin for teamBlue-image
#
#  Coded/Modified/Adapted by örlgrey
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
from Components.config import config, configfile, ConfigYesNo, ConfigSubsection, getConfigListEntry, ConfigSelection, ConfigNumber, ConfigText, ConfigInteger, ConfigClock, ConfigSlider, ConfigBoolean
from Components.ConfigList import ConfigListScreen
from Components.Sources.StaticText import StaticText
from Components.Label import Label
from Components.Language import language
import gettext
import time
import os
import requests
from enigma import eTimer
from Tools.Directories import fileExists, resolveFilename, SCOPE_LANGUAGE, SCOPE_PLUGINS
from shutil import move, copyfile
from lxml import etree
from xml.etree.cElementTree import fromstring

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
				("location", _("Enter location manually")),
				("weatherplugin", _("WeatherPlugin"))
				])
				
config.plugins.PaxWeather.refreshInterval = ConfigSelection(default="0", choices=[
				("0", _("0")),
				("120", _("120"))
				])

SearchResultList = []
config.plugins.PaxWeather.list = ConfigSelection(default="", choices=SearchResultList)

config.plugins.PaxWeather.cityname = ConfigText(default="")
config.plugins.PaxWeather.gmcode = ConfigText(default="")

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
			"yellow": self.checkCode,
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

		self.actCity = ""
		self.InternetAvailable = self.getInternetAvailable()

	def mylist(self):
		self.timer.start(100, True)

	def updateMylist(self):
		list = []
		list.append(getConfigListEntry(_("PaxWeather"), config.plugins.PaxWeather.activate, _("Activate or deactivate the weather widget.")))
		if config.plugins.PaxWeather.activate.value == "weather-on":
			list.append(getConfigListEntry(_("Search option"), config.plugins.PaxWeather.searchby, _("Choose from different options to enter your settings.\nPress the yellow button to search for the weather code.")))
			if config.plugins.PaxWeather.searchby.value == "location":
				list.append(getConfigListEntry(_("Location "), config.plugins.PaxWeather.cityname, _("Enter your location.\nPress OK to use the virtual keyboard.\nPress the yellow button to search for the weather code.")))

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
		if option.value == "auto-ip" or option.value == "location" or option == config.plugins.PaxWeather.cityname:
			self["key_yellow"].text = _("Search Code")
		elif option.value == "weatherplugin":
			self["key_yellow"].text = _("WeatherPlugin")
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

	def getCityByIP(self):
		try:
			res_city = requests.get('http://ip-api.com/json/?lang=de&fields=status,city', timeout=1)
			data_city = res_city.json()
			if data_city['status'] == 'success':
				return str(data_city['city'])
		except:
			self.session.open(MessageBox, _('No valid location found.'), MessageBox.TYPE_INFO, timeout=10)

	def checkCode(self):
		if self.InternetAvailable and config.plugins.PaxWeather.activate.value == "weather-on":
			option = self["config"].getCurrent()[1]
			if option.value == "auto-ip":
				cityip = self.getCityByIP()
				iplist = []
				try:
					res_gc = requests.get('http://weather.service.msn.com/find.aspx?src=windows&outputview=search&weasearchstr=%s&culture=de-DE' % str(cityip), timeout=1)
					data_gc = fromstring(res_gc.text)

					for weather in data_gc.findall("./weather"):
						ipcity = weather.get('weatherlocationname').encode("utf-8", 'ignore')
						code = weather.get('weatherlocationcode').split('wc:')[1]
						iplist.append((ipcity, code))

					def CodeCallBack(callback):
						callback = callback and callback[1]
						if callback:
							config.plugins.PaxWeather.gmcode.value = str(callback)
							config.plugins.PaxWeather.gmcode.save()
							self.session.open(MessageBox, _("Weather-Code found:\n") + str(config.plugins.PaxWeather.gmcode.value), MessageBox.TYPE_INFO, timeout=10)
					self.session.openWithCallback(CodeCallBack, ChoiceBox, title=_("Choose your location:"), list=iplist)

				except:
					self.session.open(MessageBox, _('No valid location found.'), MessageBox.TYPE_INFO, timeout=10)

			if option.value == "location" or option == config.plugins.PaxWeather.cityname:
				citylist = []
				try:
					res_gc = requests.get('http://weather.service.msn.com/find.aspx?src=windows&outputview=search&weasearchstr=%s&culture=de-DE' % str(config.plugins.PaxWeather.cityname.value), timeout=1)
					data_gc = fromstring(res_gc.text)

					for weather in data_gc.findall("./weather"):
						city = weather.get('weatherlocationname').encode("utf-8", 'ignore')
						code = weather.get('weatherlocationcode').split('wc:')[1]
						citylist.append((city, code))

					def LocationCallBack(callback):
						callback = callback and callback[1]
						if callback:
							config.plugins.PaxWeather.gmcode.value = str(callback)
							config.plugins.PaxWeather.gmcode.save()
							self.session.open(MessageBox, _("Weather-Code found:\n") + str(config.plugins.PaxWeather.gmcode.value), MessageBox.TYPE_INFO, timeout=10)
					self.session.openWithCallback(LocationCallBack, ChoiceBox, title=_("Choose your location:"), list=citylist)

				except:
					self.session.open(MessageBox, _('No valid Weather-Code found.'), MessageBox.TYPE_INFO, timeout=10)

			if option.value == "weatherplugin":
				if self.InternetAvailable:
					try:
						check_installed = os.popen("opkg list-installed enigma2-plugin-systemplugins-weathercomponenthandler | cut -d ' ' -f1").read()
						if "enigma2-plugin-systemplugins-weathercomponenthandler" in str(check_installed):
							from Plugins.Extensions.WeatherPlugin.setup import MSNWeatherPluginEntriesListConfigScreen
							self.session.open(MSNWeatherPluginEntriesListConfigScreen)
						else:
							self.askInstall()
					except:
						self.askInstall()
				else:
					self.session.open(MessageBox, _("Your box needs an internet connection to display the weather widget.\nPlease solve the problem."), MessageBox.TYPE_INFO, timeout=10)
					config.plugins.PaxWeather.activate.value = "weather-off"
					self.mylist()

	def VirtualKeyBoardCallBack(self, callback):
		try:
			if callback:
				self["config"].getCurrent()[1].value = callback
			else:
				pass
		except:
			pass

	def OK(self):
		option = self["config"].getCurrent()[1]

		if option == config.plugins.PaxWeather.cityname:
			text = self["config"].getCurrent()[1].value
			title = _("Enter your location:")
			self.session.openWithCallback(self.VirtualKeyBoardCallBack, VirtualKeyBoard, title=title, text=text)
			config.plugins.PaxWeather.cityname.save()

	def askInstall(self):
		askInstall = self.session.openWithCallback(self.doInstall, MessageBox, _("Systemplugin \"weathercomponenthandler\" is not installed.\nDo you want to install the plugin now?"), MessageBox.TYPE_YESNO)
		askInstall.setTitle(_("Restart GUI"))

	def doInstall(self, answer):
		if answer is True:
			os.system('opkg update')
			os.system("opkg install enigma2-plugin-systemplugins-weathercomponenthandler")
			check_installed = os.popen("opkg list-installed enigma2-plugin-systemplugins-weathercomponenthandler | cut -d ' ' -f1").read()
			if "enigma2-plugin-systemplugins-weathercomponenthandler" in str(check_installed):
				self.session.open(MessageBox, _("Systemplugin \"weathercomponenthandler\" was installed successfully."), MessageBox.TYPE_INFO, timeout=10)
				self.mylist()
			else:
				self.session.open(MessageBox, _("Systemplugin \"weathercomponenthandler\" could not be installed."), MessageBox.TYPE_INFO, timeout=10)
				config.plugins.PaxWeather.activate.value = "weather-off"
				self.mylist()
		else:
			config.plugins.PaxWeather.activate.value = "weather-off"
			self.mylist()

	def reboot(self):
		restartbox = self.session.openWithCallback(self.restartGUI, MessageBox, _("Do you really want to reboot now?"), MessageBox.TYPE_YESNO)
		restartbox.setTitle(_("Restart GUI"))

	def save(self):
		for x in self["config"].list:
			if len(x) > 1:
				x[1].save()
			else:
				pass

		self.skinSearchAndReplace = []

		if config.plugins.PaxWeather.activate.value == "weather-on":
			if self.InternetAvailable:
				if config.plugins.PaxWeather.searchby.value == "weatherplugin":
					check_installed = os.popen("opkg list-installed enigma2-plugin-systemplugins-weathercomponenthandler | cut -d ' ' -f1").read()
					if "enigma2-plugin-systemplugins-weathercomponenthandler" in str(check_installed):
						self.skinSearchAndReplace.append(['<!-- <panel name="PANEL_WEATHER_WIDGET_OFF"/> -->', '<panel name="PANEL_WEATHER_WIDGET"/>'])
						self.skinSearchAndReplace.append(['<panel name="PANEL_WEATHER_WIDGET2"/>', '<panel name="PANEL_WEATHER_WIDGET"/>'])
						self.appendSkinFile(self.xmlfile)
						self.generateSkin()
					else:
						self.session.open(MessageBox, _("Systemplugin \"weathercomponenthandler\" is not installed.\nPlease check your settings."), MessageBox.TYPE_INFO, timeout=10)
						config.plugins.PaxWeather.activate.value = "weather-off"
						self.mylist()
				else:
					self.skinSearchAndReplace.append(['<!-- <panel name="PANEL_WEATHER_WIDGET_OFF"/> -->', '<panel name="PANEL_WEATHER_WIDGET2"/>'])
					self.skinSearchAndReplace.append(['<panel name="PANEL_WEATHER_WIDGET"/>', '<panel name="PANEL_WEATHER_WIDGET2"/>'])
					self.appendSkinFile(self.xmlfile)
					self.generateSkin()
			else:
				self.session.open(MessageBox, _("Your box needs an internet connection to display the weather widget.\nPlease solve the problem."), MessageBox.TYPE_INFO, timeout=10)
				config.plugins.PaxWeather.activate.value = "weather-off"
				self.mylist()
		else:
			self.skinSearchAndReplace.append(['<panel name="PANEL_WEATHER_WIDGET2"/>', '<!-- <panel name="PANEL_WEATHER_WIDGET_OFF"/> -->'])
			self.skinSearchAndReplace.append(['<panel name="PANEL_WEATHER_WIDGET"/>', '<!-- <panel name="PANEL_WEATHER_WIDGET_OFF"/> -->'])
			self.appendSkinFile(self.xmlfile)
			self.generateSkin()

		if config.plugins.PaxWeather.activate.value == "weather-on" and self.InternetAvailable and not config.plugins.PaxWeather.searchby.value == "weatherplugin":
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
		restartbox.setTitle(_("Restart GUI"))

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
		askExit.setTitle(_("Exit"))

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
