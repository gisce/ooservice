OpenObject Service
==================

Access to OpenObject API without XML-RPC and a similiar API from ERPPeek.

.. code-block: python

    from ooservice import OpenERPService, PoolWrapper
    service = OpenERPService()
    uid = service.login(user, password)
    c = PoolWrapper(service.pool, service.db_name, uid)

    partner_obj = c.model('res.partner')
    partner_ids = partner_obj.search([])
