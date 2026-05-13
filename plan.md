# Implementation Plan

## Goal
Support multiple Webhook (WebSocket push) configurations directly from the frontend page.

## Proposed Changes

1. **`core/notifier.py`**
   - Update `check_webhook_configured()` to check if any non-empty lines exist.
   - Update `send_webhook_notification()` and `send_new_dynamic_notification()` to read all non-empty lines from `webhook_config.txt`.
   - Loop through all URLs and perform a POST request for each.

2. **`web_server.py`**
   - Add new API endpoints to manage webhooks:
     - `GET /api/webhooks`: Return a list of current webhook URLs.
     - `POST /api/webhooks`: Accept a JSON payload with a list of URLs and write them to `webhook_config.txt`, separated by newlines.

3. **`templates/index.html`**
   - Add a new "通知设置" (Notification Settings) sidebar menu item.
   - Create a new section (`#section-notifications`) to display a list of configured webhooks.
   - Include an input field and button to add new webhook URLs.
   - Add buttons to delete existing webhook URLs.
   - Add frontend JavaScript functions to integrate with the new APIs (`loadWebhooks`, `addWebhook`, `deleteWebhook`).

## Verification
- Can add and delete multiple webhooks in the new UI.
- `webhook_config.txt` contains multiple lines.
- The `notifier.py` correctly sends requests to all configured webhooks without errors if one fails.
