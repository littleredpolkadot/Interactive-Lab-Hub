import qwiic_proximity
import time

prox = qwiic_proximity.QwiicProximity()
if not prox.connected:
    print("VCNL4040 not detected")
    exit()

prox.begin()
print("VCNL4040 initialized")

while True:
    try:
        print(prox.get_proximity())
        time.sleep(0.5)
    except Exception as e:
        print("Read failed:", e)