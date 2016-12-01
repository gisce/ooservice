OpenObject Service
==================

Access to OpenObject API without XML-RPC and a similiar API from ERPPeek.

To configure the service you can use environment vars:

.. code-block:: sh

    export OPENERP_ROOT_PATH="path/to/server/bin"
    export OPENERP_ADDONS_PATH="$OPENERP_ROOT_PATH/addons"
    export OPENERP_DB_HOST="localhost"
    export OPENERP_DB_PORT="5432"
    export OPENERP_DB_USER="db_user"
    export OPENERP_DB_PASSWORD="db_password"
    export OPENERP_DB_NAME="test_1480577710"
    export PYTHONPATH="$OPENERP_ROOT_PATH:$OPENERP_ADDONS_PATH"

Then you can open an Ipython and start using PoolWrapper API

.. code-block:: python

    from ooservice import OpenERPService, PoolWrapper
    service = OpenERPService()
    uid = service.login(user, password)
    c = PoolWrapper(service.pool, service.db_name, uid)

    partner_obj = c.model('res.partner')
    partner_ids = partner_obj.search([])
