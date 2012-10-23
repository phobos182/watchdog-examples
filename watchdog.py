#!/usr/bin/env python
# 2012 - Jeremy Carroll
# WatchDog testing
# Read from a file. If "ok" in file, then healthy.
# Else failed. Test extending DSL with a Tiered remediation
# script to take multiple actions based on failure count.
# State is stored in the rule object as a hack, investigating
# other methods
from watchdog import *
from networkinterface import *



class InterfaceSpeed(Rule):
    """Rule to check to ensure that active linkes are 1000/full."""
    def __init__(self, timeout=Time.s(10), freq=Time.m(60), fail=(), success=()):
        Rule.__init__(self, freq, fail, success)
        self.failcount = []


    def run(self):
        f = open("/tmp/testfile", "r")
        a = f.readlines()
        f.close()
        if "ok" in a[0].rstrip():
            print 'Healthy'
            return Success(None)
        else:
            return Failure("File: %s" % (a))


class Tier(Action):
    """Triggers an action if there are > N errors, and < Y errors
        within a time lapse. Useful for tiering conditions."""
    def __init__(self, actions, description="undef", errors=5, unmonitor=10, during=30 * 1000):
        Action.__init__(self)
        if not (type(actions) in (tuple, list)):
            actions = tuple([actions])
        self.actions = actions
        self.description = description
        self.errors = errors
        self.unmonitor = unmonitor
        self.during = during
        self.errorValues = []
        self.errorStartTime = 0


    def run(self, monitor, service, rule, runner):
        """When the number of errors is reached within the period, the given
        actions are triggered."""
        if not rule.failcount:
            self.errorStartTime = now()
        if rule.lastRun not in rule.failcount:
            rule.failcount.append(rule.lastRun)
        elapsed_time = now() - self.errorStartTime
        print "\nEval: %s :: Min: %s, Max: %s, Iteration: %s, Elapsed: %s, During: %s" % (self.description, self.errors, self.unmonitor, len(rule.failcount), elapsed_time, self.during)
        if len(rule.failcount) >= self.errors and len(rule.failcount) <= self.unmonitor and elapsed_time <= self.during:
            print "\n    Executing: %s, Iteration: %x" % (self.description, len(rule.failcount))
            for action in self.actions:
                action.run(monitor, service, rule, runner)


class ResetTier(Action):
    """Resets failure counter for tier on success."""
    def __init__(self):
        Action.__init__(self)


    def run(self, monitor, service, rule, runner):
        """Reset counter."""
        try:
            rule.failcount = []
        except Exception:
            pass


Monitor (
    Service(
        name    = "network-health",
        monitor = (
            InterfaceSpeed(
                freq=Time.s(10),
                fail=[
                    Tier(
                        errors=1,
                        description="Restart Interface",
                        unmonitor=2,
                        during=Time.s(300),
                        actions=[
                            Run("touch /tmp/remedy")
                        ]
                    ),
                    Tier(
                        description="Stop prescriptions",
                        errors=3,
                        unmonitor=3,
                        during=Time.s(300),
                        actions=[
                            Run("touch /tmp/remedy_last")
                        ]
                    )
                ],
                success=[ResetTier()],
            )
        )
    )
).run()
