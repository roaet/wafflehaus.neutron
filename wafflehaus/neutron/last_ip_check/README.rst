=============
Last IP Check
=============

The Last IP Check filter will prevent a user from detaching the last fixed_ip
from their instance. Such a situation may leave an instance unreachable.

Configuration
~~~~~~~~~~~~~

::

    [filter:last_ip_check]
    paste.filter_factory = wafflehaus.neutron.last_ip_check.last_ip_check:filter_factory
    enabled = true

Use Case
~~~~~~~~

Neutron by default will not prevent a user from detaching the last fixed_ip
from their instance. In some situations this may prevent further access. As a 
quality of life for the user this will prevent them from shooting themselves
in the foot.
