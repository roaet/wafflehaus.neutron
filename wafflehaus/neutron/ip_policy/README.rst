=================
Default IP Policy
=================

The default IP policy filter is a way for a deployment to ensure that subnets
created by users conform to a minimal IPAM policy.

Configuration
~~~~~~~~~~~~~

::

    [filter:default_policy]
    paste.filter_factory = wafflehaus.neutron.ip_policy.create_default:filter_factory
    enabled = true
    
Currently this filter does not support configuration of the IP policy that is
generated but support will soon be added.

Use Case
~~~~~~~~

This filter is useful if your deployment uses a portion of the created subnets
for gateway, network, and/or broadcast. This is also helpful if your
deployment uses some of a created subnet for internal use.
