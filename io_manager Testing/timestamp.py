import time
from datetime import datetime, timezone

# Method 1: Unix Timestamp (Float seconds since Epoch)
unix_timestamp = time.time()
print(f"Unix Timestamp: {unix_timestamp}")

# Method 2: Integer Unix Timestamp
int_timestamp = int(time.time())
print(f"Integer Unix Timestamp: {int_timestamp}")

# Method 3: Millisecond Timestamp
ms_timestamp = int(time.time() * 1000)
print(f"Millisecond Timestamp: {ms_timestamp}")

# Method 4: Human-Readable Local Timestamp
local_format = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
print(f"Formatted Local Time: {local_format}")

# Method 5: Human-Readable UTC Timestamp (ISO 8601)
utc_format = datetime.now(timezone.utc).isoformat()
print(f"Formatted UTC Time: {utc_format}")

timestamp = datetime.now().isoformat(timespec="seconds")
print(f"Auto-captured Timestamp: {timestamp}")