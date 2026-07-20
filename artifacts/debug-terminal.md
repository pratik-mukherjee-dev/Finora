
(.venv) E:\PyCharm\Services\Finora\backend>python manage.py makemigrations
E:\PyCharm\Services\Finora\.venv\Lib\site-packages\django\core\management\commands\makemigrations.py:160: RuntimeWarning: Got an error checking a consistent migration history performed for database connection 'default': connection timeout expired
  warnings.warn(
Migrations for 'accounts':
  apps\accounts\migrations\0002_settlementmode.py
    + Create model SettlementMode
Migrations for 'vouchers':
  apps\vouchers\migrations\0003_payment_mode_received_mode.py
    + Add field mode to payment
    + Add field mode to received

(.venv) E:\PyCharm\Services\Finora\backend>
                                                                          
(.venv) E:\PyCharm\Services\Finora\backend>python manage.py migrate       
Traceback (most recent call last):
  File "E:\PyCharm\Services\Finora\.venv\Lib\site-packages\django\db\backends\base\base.py", line 278, in ensure_connection
    self.connect()
    ~~~~~~~~~~~~^^
  File "E:\PyCharm\Services\Finora\.venv\Lib\site-packages\django\utils\asyncio.py", line 26, in inner
    return func(*args, **kwargs)
  File "E:\PyCharm\Services\Finora\.venv\Lib\site-packages\django\db\backends\base\base.py", line 255, in connect
    self.connection = self.get_new_connection(conn_params)
                      ~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^
  File "E:\PyCharm\Services\Finora\.venv\Lib\site-packages\django\utils\asyncio.py", line 26, in inner
    return func(*args, **kwargs)
  File "E:\PyCharm\Services\Finora\.venv\Lib\site-packages\django\db\backends\postgresql\base.py", line 332, in get_new_connection
    connection = self.Database.connect(**conn_params)
  File "E:\PyCharm\Services\Finora\.venv\Lib\site-packages\psycopg\connection.py", line 122, in connect
    raise last_ex.with_traceback(None)
psycopg.errors.ConnectionTimeout: connection timeout expired

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "E:\PyCharm\Services\Finora\backend\manage.py", line 21, in <module>
    main()
    ~~~~^^
  File "E:\PyCharm\Services\Finora\backend\manage.py", line 17, in main
    execute_from_command_line(sys.argv)
    ~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^
  File "E:\PyCharm\Services\Finora\.venv\Lib\site-packages\django\core\management\__init__.py", line 442, in execute_from_command_line
    utility.execute()
    ~~~~~~~~~~~~~~~^^
  File "E:\PyCharm\Services\Finora\.venv\Lib\site-packages\django\core\management\__init__.py", line 436, in execute
    self.fetch_command(subcommand).run_from_argv(self.argv)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^
  File "E:\PyCharm\Services\Finora\.venv\Lib\site-packages\django\core\management\base.py", line 413, in run_from_argv
    self.execute(*args, **cmd_options)
    ~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^
  File "E:\PyCharm\Services\Finora\.venv\Lib\site-packages\django\core\management\base.py", line 459, in execute
    output = self.handle(*args, **options)
  File "E:\PyCharm\Services\Finora\.venv\Lib\site-packages\django\core\management\base.py", line 107, in wrapper
    res = handle_func(*args, **kwargs)
  File "E:\PyCharm\Services\Finora\.venv\Lib\site-packages\django\core\management\commands\migrate.py", line 118, in handle
    executor = MigrationExecutor(connection, self.migration_progress_callback)
  File "E:\PyCharm\Services\Finora\.venv\Lib\site-packages\django\db\migrations\executor.py", line 18, in __init__
    self.loader = MigrationLoader(self.connection)
                  ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
  File "E:\PyCharm\Services\Finora\.venv\Lib\site-packages\django\db\migrations\loader.py", line 58, in __init__
    self.build_graph()
    ~~~~~~~~~~~~~~~~^^
  File "E:\PyCharm\Services\Finora\.venv\Lib\site-packages\django\db\migrations\loader.py", line 235, in build_graph
    self.applied_migrations = recorder.applied_migrations()
                              ~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "E:\PyCharm\Services\Finora\.venv\Lib\site-packages\django\db\migrations\recorder.py", line 89, in applied_migrations
    if self.has_table():
       ~~~~~~~~~~~~~~^^
  File "E:\PyCharm\Services\Finora\.venv\Lib\site-packages\django\db\migrations\recorder.py", line 63, in has_table
    with self.connection.cursor() as cursor:
         ~~~~~~~~~~~~~~~~~~~~~~^^
  File "E:\PyCharm\Services\Finora\.venv\Lib\site-packages\django\utils\asyncio.py", line 26, in inner
    return func(*args, **kwargs)
  File "E:\PyCharm\Services\Finora\.venv\Lib\site-packages\django\db\backends\base\base.py", line 319, in cursor
    return self._cursor()
           ~~~~~~~~~~~~^^
  File "E:\PyCharm\Services\Finora\.venv\Lib\site-packages\django\db\backends\base\base.py", line 295, in _cursor
    self.ensure_connection()
    ~~~~~~~~~~~~~~~~~~~~~~^^
  File "E:\PyCharm\Services\Finora\.venv\Lib\site-packages\django\utils\asyncio.py", line 26, in inner
    return func(*args, **kwargs)
  File "E:\PyCharm\Services\Finora\.venv\Lib\site-packages\django\db\backends\base\base.py", line 277, in ensure_connection
    with self.wrap_database_errors:
         ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "E:\PyCharm\Services\Finora\.venv\Lib\site-packages\django\db\utils.py", line 91, in __exit__
    raise dj_exc_value.with_traceback(traceback) from exc_value
  File "E:\PyCharm\Services\Finora\.venv\Lib\site-packages\django\db\backends\base\base.py", line 278, in ensure_connection
    self.connect()
    ~~~~~~~~~~~~^^
  File "E:\PyCharm\Services\Finora\.venv\Lib\site-packages\django\utils\asyncio.py", line 26, in inner
    return func(*args, **kwargs)
  File "E:\PyCharm\Services\Finora\.venv\Lib\site-packages\django\db\backends\base\base.py", line 255, in connect
    self.connection = self.get_new_connection(conn_params)
                      ~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^
  File "E:\PyCharm\Services\Finora\.venv\Lib\site-packages\django\utils\asyncio.py", line 26, in inner
    return func(*args, **kwargs)
  File "E:\PyCharm\Services\Finora\.venv\Lib\site-packages\django\db\backends\postgresql\base.py", line 332, in get_new_connection
    connection = self.Database.connect(**conn_params)
  File "E:\PyCharm\Services\Finora\.venv\Lib\site-packages\psycopg\connection.py", line 122, in connect
    raise last_ex.with_traceback(None)
django.db.utils.OperationalError: connection timeout expired

(.venv) E:\PyCharm\Services\Finora\backend>