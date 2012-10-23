#!/usr/bin/env python
from watchdog import *
from networkinterface import *


class InterfaceSpeed(Rule):
    """Rule to check to ensure that active linkes are 1000/full."""
    def __init__(self, timeout=Time.s(10), freq=Time.m(1), fail=(), success=(), speed="1000", duplex="full"):
        Rule.__init__(self, freq, fail, success)
        # State about the rules failure count, and start of error.
        # This will help in our Tiered policy to keep track of the 
        # current status of the failure.
        self.failcount = []
        self.speed = speed
        self.duplex = duplex


    def run(self):
        iface = NetworkInterface()
        for i in iface.interfaces:
            if 'lo' in i:
                continue
            ifspeed = getattr(iface, "%s_speed" % (i))
            ifduplex = getattr(iface, "%s_duplex" % (i))
            ifup = getattr(iface, "%s_operstate" % (i))
            if ifup == "up":
                if ifspeed != self.speed or ifduplex != self.duplex:
                    return Failure("Interface %s test failed. Speed: %s, Duplex: %s" % (ifspeed, ifduplex))
                Logger.Info("Interface %s - Speed: %s, Duplex: %s" % (i, ifspeed, ifduplex))
        return Success(None)


class Tier(Action):
    """Triggers an action if there are > N errors, and < Y errors
        within a time lapse. Useful for tiering conditions."""
    def __init__(self, actions, description="undef", errors=5, unmonitor=10):
        Action.__init__(self)
        if not (type(actions) in (tuple, list)):
            actions = tuple([actions])
        self.actions = actions
        self.description = description
        self.errors = errors
        self.unmonitor = unmonitor


    def run(self, monitor, service, rule, runner):
        """When the number of errors is reached within the period, the given
        actions are triggered."""
        # De-duplcate error counts due to multiple threads.
        # Add lastRun (epoch) to list, exists in array - skip it.
        if rule.lastRun not in rule.failcount:
            rule.failcount.append(rule.lastRun)
        Logger.Debug("Eval: %s :: Min: %s, Max: %s, Iteration: %s" % (self.description, self.errors, self.unmonitor, len(rule.failcount)))
        if len(rule.failcount) >= self.errors and len(rule.failcount) <= self.unmonitor:
            Logger.Debug("Executing: %s, Iteration: %x" % (self.description, len(rule.failcount)))
            for action in self.actions:
                action.run(monitor, service, rule, runner)


class ResetTier(Action):
    """Resets failure counter for tier on success."""
    def __init__(self):
        Action.__init__(self)


    def run(self, monitor, service, rule, runner):
        """Reset failure counter."""
        try:
            rule.failcount = []
        except Exception:
            pass


Monitor (
    Service(
        name    = "network-health",
        monitor = (
            InterfaceSpeed(
                freq=Time.m(1),
                fail=[
                    Tier(
                        description="Restart Interface",
                        errors=1,
                        unmonitor=3,
                        actions=[
                            Run("/etc/init.d/networking restart")
                        ]
                    ),
                    Tier(
                        description="Send fix API call",
                        errors=4,
                        unmonitor=4,
                        actions=[
                            Run("echo Could not remedy network interface - $(date +%s) > /var/log/watchdog.err")
                        ]
                    )
                ],
                success=[ResetTier()],
            )
        )
    )
).run()
