import pysony
import six

search = pysony.ControlPoint()  # Capitalized 'ControlPoint'
cameras = search.discover(5)    # Wait 5 seconds to discover cameras

print("Available cameras: %s" % cameras)
print("")

for x in cameras:
    print("Checking Camera: %s" % x)
    camera = pysony.SonyAPI(x)  # Corrected from 'QX addr=x' to just 'x'
    mode = camera.getAvailableApiList()
    print(mode)
    print("")