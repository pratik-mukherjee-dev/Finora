(.venv) PS E:\PyCharm\Services\Finora\desktop> npm run tauri dev

> desktop@0.1.0 tauri
> tauri dev

     Running BeforeDevCommand (`npm run dev`)

> desktop@0.1.0 dev
> vite dev


  VITE v6.4.3  ready in 1845 ms

  ➜  Local:   http://localhost:1420/
     Running DevCommand (`cargo  run --no-default-features --color always --`)
        Info Watching E:\PyCharm\Services\Finora\desktop\src-tauri for changes...
    Finished `dev` profile [unoptimized + debuginfo] target(s) in 1.24s
     Running `target\debug\desktop.exe`
waiting for server to start....2026-07-17 19:58:54.410 IST [13928] LOG:  starting PostgreSQL 18.4 on x86_64-windows, compiled by msvc-19.44.35227, 64-bit
2026-07-17 19:58:54.425 IST [13928] LOG:  listening on IPv4 address "127.0.0.1", port 62903
2026-07-17 19:58:54.849 IST [27380] LOG:  database system was shut down at 2026-07-17 19:57:51 IST
2026-07-17 19:58:55.048 IST [13928] LOG:  database system is ready to accept connections
 done
server started
Finora backend ready on 127.0.0.1:62904
WARNING:django.request:Unauthorized: /api/accounts/auth/me/
C:\Users\death\AppData\Local\Temp\onefile_27096_897512_d21WFWjlEGQ\jwt\api_jwt.py:368: InsecureKeyLengthWarning: The HMAC key is 22 bytes long, which is below the minimum recommended length of 32 bytes for SHA256. See RFC 7518 Section 3.2.
C:\Users\death\AppData\Local\Temp\onefile_27096_897512_d21WFWjlEGQ\jwt\api_jwt.py:147: InsecureKeyLengthWarning: The HMAC key is 22 bytes long, which is below the minimum recommended length of 32 bytes for SHA256. See RFC 7518 Section 3.2.
7:59:12 PM [vite-plugin-svelte] src/lib/components/shell/CommandPalette.svelte:59:8 Elements with the 'dialog' interactive role must have a tabindex value
https://svelte.dev/e/a11y_interactive_supports_focus
7:59:13 PM [vite-plugin-svelte] src/lib/components/shell/CommandPalette.svelte:59:8 Visible, non-interactive element `<div>` with a click event must be accompanied by a keyboard event handler. Consider whether an interactive element such as `<button type="button">` or `<a>` might be more appropriate
https://svelte.dev/e/a11y_click_events_have_key_events
7:59:13 PM [vite-plugin-svelte] src/lib/components/shell/CommandPalette.svelte:68:20 Non-interactive element `<li>` should not be assigned mouse or keyboard event listeners
https://svelte.dev/e/a11y_no_noninteractive_element_interactions
