from homeassistant.const import Platform


DOMAIN = "epson_labelworks"
PLATFORMS = [Platform.TEXT]

CONF_TRANSPORT = "transport"
CONF_USB_DEVICE = "usb_device"
CONF_USB_VENDOR_ID = "usb_vendor_id"
CONF_USB_PRODUCT_ID = "usb_product_id"
CONF_USB_INTERFACE = "usb_interface"
CONF_USB_BUS = "usb_bus"
CONF_USB_ADDRESS = "usb_address"
CONF_USB_SERIAL_NUMBER = "usb_serial_number"
CONF_SERIAL_PORT = "serial_port"
CONF_SERIAL_BAUDRATE = "serial_baudrate"

DEFAULT_USB_INTERFACE = 0
DEFAULT_SERIAL_BAUDRATE = 115200

TRANSPORT_USB = "usb"
TRANSPORT_BLUETOOTH = "bluetooth"
