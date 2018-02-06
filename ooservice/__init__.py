import re
import os
import logging
import time

from osconf import config_from_environment


def camel2dot(name):
    """
    Converts a model name from _ to .

    :param name: Module name
    :return: Module name converted
    """
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1.\2', name)
    return re.sub('([a-z])([A-Z0-9])', r'\1.\2', s1).lower()


class OpenERPService(object):
    """
    OpenERP Service
    """

    def __init__(self, **kwargs):
        """
        Creates a new OpenERP service.

        :param kwargs: keyword arguments passed to the config
        """
        if 'LOGGER_NAME' in kwargs:
            self.logger = logging.getLogger(kwargs['LOGGER_NAME'])
        else:
            self.logger = logging.getLogger('OpenERPService')

        import sys
        sys.argv = [sys.argv[0]]
        config = config_from_environment('OPENERP', [], **kwargs)
        import netsvc
        logging.disable(logging.CRITICAL)
        import tools
        for key, value in config.iteritems():
            tools.config[key] = value
        if hasattr(tools.config, 'parse'):
            tools.config.parse()
        tools.config.parse()
        from tools import config as default_config
        for key, value in config.iteritems():
            default_config[key] = value
        # Disable cron
        default_config['cron'] = False
        self.config = default_config
        import pooler
        import workflow
        self.pooler = pooler
        self.db = None
        self.pool = None
        self.DEFAULT_USER = 1
        if 'db_name' in config:
            self.db_name = config['db_name']
        try:
            from netsvc import Agent
            Agent.quit()
        except ImportError:
            pass

    def create_database(self, template=True):
        """
        Creates a new database.

        :param template: use a template (name must be `base`) (default True)
        """
        db_name = 'test_' + str(int(time.time()))
        import sql_db
        conn = sql_db.db_connect('postgres')
        cursor = conn.cursor()
        try:
            self.logger.info('Creating database %s', db_name)
            cursor.autocommit(True)
            if template:
                cursor.execute('CREATE DATABASE {} WITH TEMPLATE base'.format(
                    db_name
                ))
            else:
                cursor.execute('CREATE DATABASE {}'.format(db_name))
            return db_name
        finally:
            cursor.close()
            sql_db.close_db('postgres')

    def drop_database(self):
        """
        Drop database from `self.db_name`

        :return: None
        """

        import sql_db
        sql_db.close_db(self.db_name)
        conn = sql_db.db_connect('template1')
        cursor = conn.cursor()
        try:
            self.logger.info('Droping database %s', self.db_name)
            cursor.autocommit(True)
            cursor.execute('DROP DATABASE ' + self.db_name)
        finally:
            cursor.close()

    def install_module(self, module):
        """Installs a module

        :param module: Module to install
        """
        self.logger.info('Installing module %s', module)
        import pooler

        module_obj = self.pool.get('ir.module.module')
        with Transaction().start(self.config['db_name']) as txn:
            module_obj.update_list(txn.cursor, txn.user)
            module_ids = module_obj.search(
                txn.cursor, self.DEFAULT_USER,
                [('name', '=', module)],
            )
            assert module_ids, "Module %s not found" % module
            module_obj.button_install(txn.cursor, self.DEFAULT_USER, module_ids)
            pool = pooler.get_pool(txn.cursor.dbname)
            mod_obj = pool.get('ir.module.module')
            ids = mod_obj.search(txn.cursor, txn.user, [
                ('state', 'in', ['to upgrade', 'to remove', 'to install'])
            ])
            print 'ids:{}'.format(ids)
            unmet_packages = []
            mod_dep_obj = pool.get('ir.module.module.dependency')
            for mod in mod_obj.browse(txn.cursor, txn.user, ids):
                deps = mod_dep_obj.search(txn.cursor, txn.user, [
                    ('module_id', '=', mod.id)
                ])
                for dep_mod in mod_dep_obj.browse(txn.cursor, txn.user, deps):
                    if dep_mod.state in ('unknown', 'uninstalled'):
                        unmet_packages.append(dep_mod.name)
            mod_obj.download(txn.cursor, txn.user, ids)
            txn.cursor.commit()
        self.db, self.pool = pooler.restart_pool(
            self.config['db_name'], update_module=True
        )

    @property
    def db_name(self):
        """
        Database name
        :return: Name of the database as str
        """

        return self.config['db_name']

    @db_name.setter
    def db_name(self, value):
        """
        Sets ths name of the database
        :param value: Name of the database
        :return: None
        """

        self.config['db_name'] = value
        self.db, self.pool = self.pooler.get_db_and_pool(self.db_name)
        # TODO: Patch ir.cron

    def login(self, user, password):
        """
        Logs into the database

        :param user: OpenERP User
        :param password: OpenERP Password
        :return: OpenERP Connection
        """
        if not self.db_name:
            raise Exception('Database not ready')
        import netsvc
        common = netsvc.SERVICES['common']
        res = common.login(self.db_name, user, password, 'localservice')
        return res

    def shutdown(self):
        """
        Closes all the OpenERP Service database connections

        :return: None
        """

        if self.db_name:
            import sql_db
            sql_db.close_db(self.db_name)

    def __del__(self):
        """
        Class destructor

        :return: None
        """

        self.shutdown()


class Transaction(object):
    """
    OpenERP Transaction
    """

    def __init__(self):
        """
        Creates a Transaction
        """

        self.database = None
        self.service = None
        self.pool = None
        self.cursor = None
        self.user = None
        self.context = None

    def start(self, database_name, user=1, context=None):
        """
        Starts a Transaction

        :param database_name: Name of the database as a str
        :param user: User for the transaction
        :param context: Context for the Transaction
        :return: Transaction context
        """

        self._assert_stopped()
        self.service = OpenERPService(db_name=database_name)
        self.pool = self.service.pool
        self.cursor = self.service.db.cursor()
        self.user = user
        self.context = context if context is not None else self.get_context()
        return self

    def stop(self):
        """
        End the transaction

        :return: None
        """

        self.cursor.close()
        self.service = None
        self.cursor = None
        self.user = None
        self.context = None
        self.database = None
        self.pool = None

    def get_context(self):
        """
        Loads the context of the current user

        :return: Context object
        """

        assert self.user is not None

        user_obj = self.pool.get('res.users')
        return user_obj.context_get(self.cursor, self.user)

    def __enter__(self):
        """
        Enter to the context

        :return: Context
        """
        return self

    def __exit__(self, type, value, traceback):
        """
        Exits the context stoping the transaction

        :param type:
        :param value:
        :param traceback:
        :return: None
        """
        self.stop()

    def _assert_stopped(self):
        """
        Assert that there is no active transaction

        :return: None
        """

        assert self.service is None
        assert self.database is None
        assert self.cursor is None
        assert self.pool is None
        assert self.user is None
        assert self.context is None


class PoolWrapper(object):
    """
    Pool wrapper class
    """
    def __init__(self, pool, dbname, uid):
        """
        Pool Wrapper constructor

        :param pool:
        :param dbname: Database name
        :param uid: User identifier
        """

        self.pool = pool
        self.dbname = dbname
        self.uid = uid
        self.ppid = os.getpid()
        self.fork = False

    def __getattr__(self, name):
        """
        Gets the value of a property

        :param name: property name
        :return: Returns the value of a property
        """

        if not self.fork and (os.getpid() != self.ppid):
            import sql_db
            sql_db.close_db(self.dbname)
            service = OpenERPService()
            service.pooler.pool_dic.pop(self.dbname, None)
            service.db_name = self.dbname
            self.pool = service.pool
            self.fork = True
        name = camel2dot(name)
        return self.model(name)

    def model(self, name):
        """
        Gets the model

        :param name: Name of the model
        :return: Model object
        """

        return ModelWrapper(self.pool.get(name), self.dbname, self.uid)

    @property
    def models(self):
        """
        Gets the list of OpenERP models
        :return: List of OpenERP models
        """
        return self.pool.obj_pool.keys()


class ModelWrapper(object):
    """
    Model wrapper class
    """
    def __init__(self, model, dbname, uid):
        """
        Creates a model wrapper

        :param model: Name of the model
        :param dbname: Database Name
        :param uid: User id
        """

        self.model = model
        self.dbname = dbname
        self.uid = uid
        self.txn = Transaction().start(self.dbname, user=self.uid)
        self.txn.cursor.autocommit(True)

    def __getattr__(self, item):
        base = getattr(self.model, item)
        if callable(base):
            def wrapper(*args):
                newargs = (self.txn.cursor, self.txn.user) + args
                res = base(*newargs)
                return res
            return wrapper
        else:
            return base

    def __del__(self):
        """
        Model destructor

        :return: None
        """
        if self.txn.cursor:
            self.txn.stop()
