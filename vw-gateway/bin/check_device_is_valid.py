from zk import ZK, const
import sys
import logging


conn = None
logging.debug("create ZK instance")
zk = ZK(str('192.168.88.159'), port=4370, timeout=5, password=int(8984), force_udp=False, ommit_ping=True)

try:
    logging.debug("Connect to device")
    conn = zk.connect()  
    attendances = conn.get_attendance()
    users = conn.get_users()
    print(users)
    print(attendances)
except Exception as e:
    logging.error("Fail to get attendences", exc_info=True)
finally:
    if conn:
        conn.disconnect()          