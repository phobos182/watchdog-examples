#!/usr/bin/env python
# 2012 - Jeremy Carroll
import os


class NetworkInterface():
    """NetworkInterface object."""
    def __init__(self, path="/sys/class/net"):
        """Get interface statistics from /proc."""
        # Get list of network interfaces
        self.path = path
        # Get a list of all interfaces
        try:
            self.interfaces = os.listdir(self.path)
            # Get stats for all interfaces
            for i in self.interfaces:
                self._get_stats(i)
        except Exception:
            pass


    def _get_stats(self, interface):
        """Create object attributes based on file contents in /proc."""
        stats = ["speed", "duplex", "address", "operstate", "mtu"]
        # Create object attribute for each path if found
        for s in stats:
            attr = "%s_%s" % (interface, s)
            try:
                setattr(self, attr, self._get_file_head("%s/%s/%s" % (self.path, interface, s)))
            except Exception:
                pass


    def _get_file_head(self, path):
        """Open a file, return it's contents."""
        result = []
        try:
            f = open(path, "r")
            result = f.readlines()
        except Exception, e:
            result = None
        finally:
            f.close()
        # Only return the first result chomped
        return result[0].rstrip()


if __name__ == "__main__":
    iface = NetworkInterface()
    for i in iface.interfaces:
        # Skip localhost
        if 'lo' in i:
            continue
        # If an interface is up and active, check link speed
        if getattr(iface, "%s_operstate" % (i)) == "up":
            if getattr(iface, "%s_speed" % (i)) != "1000":
                raise Exception("Interface %s network speed is not 1000" % (i))
            else:
                print "Interface %s is OK" % (i)
