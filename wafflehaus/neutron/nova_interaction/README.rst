=======================
Nova Interaction Filter
=======================

For some requests in Neutron, we would like to see the changes made reflect on the
targeted VMs in Nova as well. To do this, this filter will make a synchronous call
back to Nova requesting the VM to be updated.

Configuration
~~~~~~~~~~~~~

::

    [filter:nova_interaction]
    paste.filter_factory = wafflehaus.neutron.nova_interaction:filter_factory
    enabled = true
    nova_url = https://nova.ohthree.com
    nova_port = 8774
    nova_verify_ssl = false
    neutron_url = http://neutron.ohthree.com
    neutron_port = 80
    neutron_verify_ssl = false
    neutron_resources = POST PUT DELETE /ports, POST PUT DELETE /ip_addresses


Use Case
~~~~~~~~

In this example, POSTs/PUTs/DELETESs to /ports and /ip_addresses will trigger a
call to Nova using the new admin-virtual-interfaces resource.
