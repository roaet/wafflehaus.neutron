=======================
Pagination Filter
=======================

Workaround for https://bugs.launchpad.net/neutron/+bug/1483873

Configuration
~~~~~~~~~~~~~

::

    [filter:pagination]
    paste.filter_factory = wafflehaus.neutron.pagination.pagination:filter_factory
    enabled = true
    pagination_url = https://neutron.ohthree.com:7575


Use Case
~~~~~~~~

When there is a proxy in front of the neutron server, requests with pagination may get localhost instead of a real host.

The above config will replace the following json:

{
  "networks": [ . ],
  "networks_links": [
    {
      "href": "http://localhost:9696/v2.0/networks?limit=1&marker=f05255b4-a958-4db1-953a-0f552d190470",
      "rel": "next"
    },
    {
      "href": "http://localhost:9696/v2.0/networks?limit=1&marker=f05255b4-a958-4db1-953a-0f552d190470&page_reverse=True",
      "rel": "previous"
    }
  ]
}

with:

{
  "networks": [ . ],
  "networks_links": [
    {
      "href": "https://neutron.ohthree.com:7575/v2.0/networks?limit=1&marker=f05255b4-a958-4db1-953a-0f552d190470",
      "rel": "next"
    },
    {
      "href": "https://neutron.ohthree.com:7575/v2.0/networks?limit=1&marker=f05255b4-a958-4db1-953a-0f552d190470&page_reverse=True",
      "rel": "previous"
    }
  ]
}
