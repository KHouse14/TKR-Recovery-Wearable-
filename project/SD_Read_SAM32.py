import board
import busio
import digitalio
import storage
import adafruit_sdcard

# Set up the sd card as a spi device
cs = digitalio.DigitalInOut(board.xSDCS)
spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
# Connect to the card and mount the filesystem.
sdcard = adafruit_sdcard.SDCard(spi, cs)
vfs = storage.VfsFat(sdcard)
storage.mount(vfs, "/sd")

# open the file with read, change the string to meet your needs
fp = open("/sd/data.txt", "r")

# print the whole thing
print(fp.read())