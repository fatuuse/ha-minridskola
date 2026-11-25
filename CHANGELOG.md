# Changelog

## 0.1.0
- Skeleton: config flow (school, credentials, child), coordinator, calendar and sensors.
- Debug: DEBUG logging of requests, response capture, redacted debug dump from options.
- Parsers are stubs until real page samples are available.
- Login flow for ASP.NET site (ViewState, auto-submit hops), start page parser, one account per child.
- Lesson parser for 'Mina bokade lektioner' (weekly recurring lessons, expanded 8 weeks ahead).
- Lesson detail page: lesson period limits the expanded dates; instructor message shown in calendar description and sensor attribute.
- Attendance history page parsed; new sensor 'Last horse' with recent history as attribute.
- Sign out (/Exit_Utloggning.aspx) after every fetch and after config flow validation.
- Button 'Refresh data' to update immediately.
- Dynamic update schedule: idle 24 h, active every 15 min from 1 h before lesson until it ends.
- Cleanup: removed unused constants (PATH_SCHOOLS_TS, PATH_CHILDREN stub).
- Config flow: clarify that personal number or username is accepted.
- Session kept alive during active lesson window to reduce login overhead.
- README: automation examples added.
- parse_schools implementerat utifrån riktig HTML från Init_Ridskolor.aspx; config flow visar nu dropdown med alla anslutna ridskolor.
