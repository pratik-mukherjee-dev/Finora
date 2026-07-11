(.venv) PS E:\PyCharm\Services\Finora\desktop> npm run tauri dev

> desktop@0.1.0 tauri
> tauri dev

     Running BeforeDevCommand (`npm run dev`)

> desktop@0.1.0 dev
> vite dev

        Warn Waiting for your frontend dev server to start on http://localhost:1420/...

  VITE v6.4.3  ready in 4926 ms

  ➜  Local:   http://localhost:1420/
     Running DevCommand (`cargo  run --no-default-features --color always --`)
        Info Watching E:\PyCharm\Services\Finora\desktop\src-tauri for changes...
   Compiling desktop v0.1.0 (E:\PyCharm\Services\Finora\desktop\src-tauri)
    Finished `dev` profile [unoptimized + debuginfo] target(s) in 1m 42s
     Running `target\debug\desktop.exe`
pg_ctl: another server might be running; trying to start server anyway
waiting for server to start....2026-07-11 21:57:11.071 IST [20152] LOG:  starting PostgreSQL 18.4 on x86_64-windows, compiled by msvc-19.44.35227, 64-bit
2026-07-11 21:57:11.115 IST [20152] LOG:  listening on IPv4 address "127.0.0.1", port 62378
2026-07-11 21:57:11.674 IST [13960] LOG:  database system was interrupted; last known up at 2026-07-10 00:39:27 IST
.........2026-07-11 21:57:21.710 IST [13960] LOG:  syncing data directory (fsync), elapsed time: 10.03 s, current path: ./base/16384/16853
...Traceback (most recent call last):
  File "C:\Users\death\AppData\Local\Temp\onefile_14980_336360_DorKYbyup3w\run_server.py", line 53, in <module>
  File "C:\Users\death\AppData\Local\Temp\onefile_14980_336360_DorKYbyup3w\run_server.py", line 43, in main
  File "C:\Users\death\AppData\Local\Temp\onefile_14980_336360_DorKYbyup3w\django\core\management\__init__.py", line 194, in call_command
  File "C:\Users\death\AppData\Local\Temp\onefile_14980_336360_DorKYbyup3w\django\core\management\base.py", line 459, in execute
  File "C:\Users\death\AppData\Local\Temp\onefile_14980_336360_DorKYbyup3w\django\core\management\base.py", line 107, in wrapper
  File "C:\Users\death\AppData\Local\Temp\onefile_14980_336360_DorKYbyup3w\django\core\management\commands\migrate.py", line 118, in handle
  File "C:\Users\death\AppData\Local\Temp\onefile_14980_336360_DorKYbyup3w\django\db\migrations\executor.py", line 18, in __init__
  File "C:\Users\death\AppData\Local\Temp\onefile_14980_336360_DorKYbyup3w\django\db\migrations\loader.py", line 58, in __init__
  File "C:\Users\death\AppData\Local\Temp\onefile_14980_336360_DorKYbyup3w\django\db\migrations\loader.py", line 229, in build_graph
  File "C:\Users\death\AppData\Local\Temp\onefile_14980_336360_DorKYbyup3w\django\db\migrations\loader.py", line 120, in load_disk
  File "importlib.py", line 88, in import_module
  File "<frozen importlib._bootstrap>", line 1398, in _gcd_import
  File "<frozen importlib._bootstrap>", line 1371, in _find_and_load
  File "<frozen importlib._bootstrap>", line 1342, in _find_and_load_unlocked
  File "<frozen importlib._bootstrap>", line 938, in _load_unlocked
  File "C:\Users\death\AppData\Local\Temp\onefile_14980_336360_DorKYbyup3w\rest_framework_simplejwt\token_blacklist\migrations\0010_fix_migrate_to_bigautofield.py", line 7, in <module rest_framework_simplejwt.token_blacklist.migrations.0010_fix_migrate_to_bigautofield>
  File "C:\Users\death\AppData\Local\Temp\onefile_14980_336360_DorKYbyup3w\pathlib\__init__.py", line 938, in resolve
  File "C:\Users\death\AppData\Local\Temp\onefile_14980_336360_DorKYbyup3w\ntpath.py", line 694, in realpath
FileNotFoundError: [WinError 3] The system cannot find the path specified: 'C:\\Users\\death\\AppData\\Local\\Temp\\onefile_14980_336360_DorKYbyup3w\\rest_framework_simplejwt\\token_blacklist\\migrations\\0010_fix_migrate_to_bigautofield.py'
......2026-07-11 21:57:31.222 IST [13960] LOG:  database system was not properly shut down; automatic recovery in progress
2026-07-11 21:57:31.331 IST [13960] LOG:  redo starts at 0/1EEC220
2026-07-11 21:57:31.331 IST [13960] LOG:  invalid record length at 0/1EEC328: expected at least 24, got 0
2026-07-11 21:57:31.332 IST [13960] LOG:  redo done at 0/1EEC2F0 system usage: CPU: user: 0.00 s, system: 0.00 s, elapsed: 0.00 s
2026-07-11 21:57:31.367 IST [13196] LOG:  checkpoint starting: end-of-recovery immediate wait
2026-07-11 21:57:31.421 IST [13196] LOG:  checkpoint complete: wrote 0 buffers (0.0%), wrote 3 SLRU buffers; 0 WAL file(s) added, 0 removed, 0 recycled; write=0.008 s, sync=0.008 s, total=0.073 s; sync files=2, longest=0.006 s, average=0.004 s; distance=0 kB, estimate=0 kB; lsn=0/1EEC328, redo lsn=0/1EEC328
2026-07-11 21:57:31.465 IST [20152] LOG:  database system is ready to accept connections
 done
server started


on screen we can see:
Couldn’t reach the backend
Backend did not become ready within 30s (attempts=74). with a retry button 