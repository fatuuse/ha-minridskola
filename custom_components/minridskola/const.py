"""Constants for Min Ridskola."""
from __future__ import annotations

import logging

DOMAIN = "minridskola"
LOGGER = logging.getLogger(__package__)

BASE_URL = "https://ww2.minridskola.se"

CONF_SCHOOL_ID = "school_id"
CONF_SCHOOL_NAME = "school_name"
CONF_CHILD_ID = "child_id"
CONF_CHILD_NAME = "child_name"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_DEBUG = "debug"

# Update schedule: once a day, but every 15 min from 1 h before a lesson until it ends.
IDLE_INTERVAL_HOURS = 24
ACTIVE_INTERVAL_MINUTES = 15
ACTIVE_LEAD_MINUTES = 60

DEBUG_DIR = "minridskola_debug"
DEBUG_BUFFER_SIZE = 20

SCHOOLS_BASE_URL = "https://www.minridskola.se"  # skolval ligger här, ww2 redirectar till Default.aspx
PATH_SCHOOLS = "/Init_Ridskolor.aspx"
PATH_LOGIN_PAGE = "/Default3.aspx"  # ?LicNr=<school id>
PATH_LOGIN_POST = "/Init_LoggaIn.aspx"
PATH_LOGOUT = "/Exit_Utloggning.aspx"
PATH_START = "/XenoWebb/Main_Start.aspx"
PATH_LESSON_DETAIL = "/XenoWebb/Lektioner/Lekt_VisaLektion0.aspx"  # ?KNummerPlats=<raw id>
PATH_HISTORY = "/XenoWebb/Lektioner/Lekt_VisaLektion3.aspx"  # session-bound: open detail page first
PATH_LESSONS = "/XenoWebb/Lektioner/Lekt_Start.aspx"
LOGIN_FIELD_USER = "ctl00$ContentPlaceHolder1$txbUserName"
LOGIN_FIELD_PASS = "ctl00$ContentPlaceHolder1$txbUserPasswd"
LOGIN_FIELD_SUBMIT = "ctl00$ContentPlaceHolder1$butSubmit"
