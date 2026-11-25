# Min Ridskola (Home Assistant)

Follow riding lessons published on https://ww2.minridskola.se.

**Status: skeleton.** Parsers are stubs; nothing is verified against the live site or a running Home Assistant.

## Provides
- Calendar `Lessons` per child
- Button `Refresh data` (update now)
- Sensors: `Next lesson`, `Upcoming lessons`, `Last horse` (from attendance history)

## Update schedule
Idle: once a day. Active: every 15 minutes starting 1 hour before a lesson until the lesson ends. Use the Refresh button to force an immediate update.

## Setup
Settings > Devices & services > Add integration > Min Ridskola: choose school, enter username and password, choose child.

## Debug
Add to `configuration.yaml`:

```yaml
logger:
  logs:
    custom_components.minridskola: debug
```

Options > Create debug dump writes redacted raw responses to `<config>/minridskola_debug/`. Review before sharing. Turn on "Capture responses" in Options > Settings to also see captures in diagnostics.

## Notes
- Login uses the child's personal number; one config entry per child.
- Lessons page /XenoWebb/Lektioner/Lekt_Start.aspx lists weekly recurring lessons (weekday + time, no dates). They are expanded 8 weeks ahead, limited to the lesson period from the detail page (Lekt_VisaLektion0.aspx). The instructor's message is shown as event description. Per-date cancellations (Lekt_VisaLektion2.aspx) and breaks are not handled yet; a message like 'week 49: no riding lessons' is shown but not applied automatically.

## Open questions
- Is there a JSON/XML API behind the site, or must HTML be scraped?
- How is the school selected (form field, subdomain, path, cookie)?
- Login form fields, CSRF token, session cookie.
- Where are children and lessons listed.

## Automation examples

### Notify when the next lesson is tomorrow
```yaml
automation:
  - alias: "Påminnelse om morgondagens ridlektion"
    trigger:
      - platform: time
        at: "18:00:00"
    condition:
      - condition: template
        value_template: >
          {% set t = states('sensor.ester_next_lesson') %}
          {{ t != 'unavailable' and (as_datetime(t).date() - now().date()).days == 1 }}
    action:
      - action: notify.mobile_app_your_phone
        data:
          title: "🐴 Ridlektion imorgon"
          message: >
            Ridlektion kl {{ as_datetime(states('sensor.ester_next_lesson')) | as_local | strftime('%H:%M') }}
            {% if state_attr('sensor.ester_next_lesson', 'location') %}
            i {{ state_attr('sensor.ester_next_lesson', 'location') }}
            {% endif %}
```

### Notify when the instructor leaves a new message
```yaml
automation:
  - alias: "Meddelande från ridläraren"
    trigger:
      - platform: state
        entity_id: sensor.ester_next_lesson
        attribute: message
    condition:
      - condition: template
        value_template: "{{ trigger.to_state.attributes.message not in ('', none) }}"
    action:
      - action: notify.mobile_app_your_phone
        data:
          title: "📢 Nytt meddelande från ridläraren"
          message: "{{ state_attr('sensor.ester_next_lesson', 'message') }}"
```

### Notify when a new horse shows up in the history (horse changed)
```yaml
automation:
  - alias: "Ny häst i historiken"
    trigger:
      - platform: state
        entity_id: sensor.ester_last_horse
    condition:
      - condition: template
        value_template: >
          {{ trigger.from_state.state not in ('unavailable','unknown','')
             and trigger.to_state.state != trigger.from_state.state }}
    action:
      - action: notify.mobile_app_your_phone
        data:
          title: "🐎 Ny häst"
          message: "Ester red {{ trigger.to_state.state }} (tidigare {{ trigger.from_state.state }})"
```

### Force refresh and log result (useful for debugging)
```yaml
script:
  refresh_minridskola:
    alias: "Uppdatera Min Ridskola nu"
    sequence:
      - action: button.press
        target:
          entity_id: button.ester_refresh_data
```
