import logManager
import socket
from zeroconf import IPVersion, ServiceInfo, Zeroconf
from functions.core import hueMdnsHostname, hueMdnsServiceName

logging = logManager.logger.get_logger(__name__)

def mdnsServiceInfo(ip, port, modelid, bridgeid):
    """Build the Hue discovery record before registering it on mDNS."""
    if modelid == "BSB003":
        service_name = hueMdnsServiceName(bridgeid)
        host_name = hueMdnsHostname(bridgeid)
    else:
        # Preserve the established Classic advertisement unchanged.
        service_name = "DIYHue-" + bridgeid
        host_name = "DIYHue-" + bridgeid + ".local."
    return ServiceInfo(
        "_hue._tcp.local.",
        service_name + "._hue._tcp.local.",
        addresses=[socket.inet_aton(ip)],
        port=port,
        properties={
            "modelid": modelid,
            "bridgeid": bridgeid,
        },
        server=host_name,
    )


def mdnsListener(ip, port, modelid, bridgeid):
    logging.info('<MDNS> listener started')
    ip_version = IPVersion.V4Only
    zeroconf = Zeroconf(ip_version=ip_version)
    info = mdnsServiceInfo(ip, port, modelid, bridgeid)
    zeroconf.register_service(info) 
