// Screen-side helper: registers this screen's shell contributions (title,
// actions, panel tabs, shortcuts) and auto-disposes on unmount.
import {onMount} from "svelte";
import {useShell, type ScreenRegistration} from "./shellContext.svelte";

export function registerScreen(build: () => ScreenRegistration) {
    const shell = useShell();
    onMount(() => {
        const dispose = shell.register(build());
        return dispose;
    });
    return shell;
}
