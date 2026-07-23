import {goto} from "$app/navigation";

export type CommandId = string;

export interface Command {
    id: CommandId;
    label: string;
    icon?: string;
    shortcut?: string;
    keychord?: string;
    module?: boolean;
    minMode?: "single" | "multi";
    run: () => void;
}

export const modules: Command[] = [
    {
        id: "home",
        label: "Home",
        icon: "⌂",
        shortcut: "Alt+1",
        keychord: "alt+1",
        module: true,
        run: () => goto("/app")
    },
    {
        id: "sale",
        label: "Sale",
        icon: "＄",
        shortcut: "Alt+2",
        keychord: "alt+2",
        module: true,
        run: () => goto("/app/sale")
    },
    {
        id: "purchase",
        label: "Purchase",
        icon: "▤",
        shortcut: "Alt+3",
        keychord: "alt+3",
        module: true,
        run: () => goto("/app/purchase")
    },
    {
        id: "payment",
        label: "Payment",
        icon: "↗",
        shortcut: "Alt+4",
        keychord: "alt+4",
        module: true,
        run: () => goto("/app/payment")
    },
    {
        id: "received",
        label: "Received",
        icon: "↙",
        shortcut: "Alt+5",
        keychord: "alt+5",
        module: true,
        run: () => goto("/app/received")
    },
    {
        id: "stock",
        label: "Stock",
        icon: "▦",
        shortcut: "Alt+6",
        keychord: "alt+6",
        module: true,
        run: () => goto("/app/stock")
    },
    {
        id: "parties",
        label: "Parties",
        icon: "☰",
        shortcut: "Alt+7",
        keychord: "alt+7",
        module: true,
        run: () => goto("/app/parties")
    },
    {
        id: "items",
        label: "Items",
        icon: "◈",
        shortcut: "Alt+8",
        keychord: "alt+8",
        module: true,
        run: () => goto("/app/items")
    },
    {
        id: "reports",
        label: "Reports",
        icon: "▥",
        shortcut: "Alt+9",
        keychord: "alt+9",
        module: true,
        run: () => goto("/app/reports")
    },
    {
        id: "settings",
        label: "Settings",
        icon: "⚙",
        shortcut: "Alt+0",
        keychord: "alt+0",
        module: true,
        run: () => goto("/app/settings")
    },
];

export function activeModuleId(pathname: string): CommandId {
    if (pathname.startsWith("/app/sale")) return "sale";
    if (pathname.startsWith("/app/purchase")) return "purchase";
    if (pathname.startsWith("/app/payment")) return "payment";
    if (pathname.startsWith("/app/received")) return "received";
    if (pathname.startsWith("/app/stock")) return "stock";
    if (pathname.startsWith("/app/parties")) return "parties";
    if (pathname.startsWith("/app/items")) return "items";
    if (pathname.startsWith("/app/reports")) return "reports";
    if (pathname.startsWith("/app/settings")) return "settings";
    return "home";
}
