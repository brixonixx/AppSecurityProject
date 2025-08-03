models.py
- Added new models Event and FileReference
- Added new database table user_event_association
- Added new attribute to User class: events

events.py
- Added event-related routes

admin.py
- Added event-related admin routes

main.py
- Modified script to use a local DB instead of remote DB
    - Code for remote connection have been commented out
- Added functionality for SSL connections

config.py
- Modified script to use a local DB instead of remote DB
    - Code for remote connection have been commented out

forms.py
- Added new form EventForm

security.py
- Added improved functions
    - alt_secure_filename_custom()
    - alt_sanitize_input()

Misc.
- Added SSL folder for storing encryption data
- Added openssl.conf for ease of generation of self-signed certificate-key pair
