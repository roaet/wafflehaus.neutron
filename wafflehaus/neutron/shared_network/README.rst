Shared Network Filters
======================

Trusted Networks Filter
-----------------------

Use Case
~~~~~~~~

Neutron, by default, will return all the shared networks in a deployment. This
is troublesome when tenants have the ability to create their own shared
networks. The trusted networks filter prevents shared networks that are not
configured to appear in GET /v2.0/networks?shared=true lists.

There are times, typically when testing, when one wants to override the trusted
networks. This is done by passing in special headers to the request.

Configuration Options
~~~~~~~~~~~~~~~~~~~~~

**trusted** : a space separated list of network ids that are to be trusted

**testing** : when set to true this filter will function as a noop

Example Configuration
~~~~~~~~~~~~~~~~~~~~~

::

    [filter:trusted_shared_nets]
    paste.filter_factory = wafflehaus.neutron.shared_nets.trusted:filter_factory
    trusted = 00000000-0000-0000-0000-000000000000
              11111111-1111-1111-1111-111111111111 
    enabled = true

Override Options
~~~~~~~~~~~~~~~~

Both are comma separated strings.

**X_NETWORK_WHITELIST** : will allow an untrusted network to show up in a list

**X_NETWORK_BLACKLIST** : will prevent any network from showing up in a list

If a network was present in the whitelist and the blacklist the blacklist will
always take precedence.
