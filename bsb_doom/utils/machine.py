import uuid
import platform
import hashlib

def get_machine_id():
    """Generate a unique machine ID that works on all devices."""
    try:
        # Try to get MAC address
        mac = uuid.getnode()
        if (mac >> 40) % 2:  # random MAC, fallback to UUID
            mac = str(uuid.uuid4())
        else:
            mac = str(mac)
    except:
        mac = str(uuid.uuid4())

    host = platform.node()
    # Combine MAC and hostname, hash for consistent length
    unique = f"{mac}-{host}"
    return hashlib.sha256(unique.encode()).hexdigest()[:16]
