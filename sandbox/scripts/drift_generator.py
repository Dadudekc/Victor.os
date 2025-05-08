import datetime
import random
import pytz

# Define timezones
local_tz = pytz.timezone('America/New_York') # Example local timezone
utc_tz = pytz.utc

# Timestamp formats to generate
formats = [
    # Format                        # Description                       # Example Generator
    ("naive_local",                 "Naive datetime assumed local",     lambda now: now.replace(tzinfo=None)),
    ("naive_utc",                   "Naive datetime assumed UTC",       lambda now: now.astimezone(utc_tz).replace(tzinfo=None)),
    ("iso_utc_Z",                   "Correct ISO 8601 UTC",             lambda now: now.astimezone(utc_tz).isoformat(timespec='milliseconds').replace('+00:00', 'Z')),
    ("iso_offset",                  "Correct ISO 8601 with offset",     lambda now: now.isoformat(timespec='milliseconds')),
    ("rfc_3339",                    "RFC 3339 format",                  lambda now: now.astimezone(utc_tz).isoformat(sep='T', timespec='milliseconds').replace('+00:00', 'Z')), # Close enough for demo
    ("malformed_iso_space",         "ISO with space instead of T",      lambda now: now.astimezone(utc_tz).isoformat(timespec='milliseconds').replace('T', ' ').replace('+00:00', 'Z')),
    ("malformed_iso_no_T_no_Z",     "ISOish without T or Z/offset",   lambda now: now.astimezone(utc_tz).isoformat(timespec='milliseconds').replace('T', ' ').replace('+00:00', '')[:-1]), # Remove Z approx
    ("unix_timestamp_secs",         "Unix timestamp (seconds)",         lambda now: str(int(now.timestamp()))),
    ("unix_timestamp_ms",           "Unix timestamp (milliseconds)",    lambda now: str(int(now.timestamp() * 1000))),
    ("human_readable",              "Ambiguous human format",           lambda now: now.strftime("%m/%d/%Y %I:%M:%S %p")),
]

print("Generating 10 synthetic log entries with inconsistent timestamps...")

base_time = datetime.datetime.now(local_tz)

for i in range(10):
    # Slightly vary time for each entry
    current_time = base_time + datetime.timedelta(seconds=random.randint(-60, 60), milliseconds=random.randint(-500, 500))

    # Pick a random format generator
    fmt_name, _, generator = random.choice(formats)

    timestamp_str = generator(current_time)

    # Simulate a log line structure
    log_line = f"EventID={1000+i},Timestamp={timestamp_str},Source=Node{random.randint(1,5)},Severity=INFO,Message=Synthetic event {i+1} using format '{fmt_name}'"
    print(log_line)

print("Log generation complete.") 