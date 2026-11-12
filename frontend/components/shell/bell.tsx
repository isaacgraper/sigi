"use client";

import { Bell as BellIcon, CheckCheck } from "lucide-react";
import { useRouter } from "next/navigation";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { formatDate } from "@/lib/format";
import { BELL_EMPTY, BELL_LABEL, BELL_MAX_COUNT, BELL_PATH, MARK_ALL } from "@/lib/notificacoes/constants";
import type { AvisoPage } from "@/lib/notificacoes/types";
import { apiFetch } from "@/lib/session";
import { useRead } from "@/lib/use-read";
import { cn } from "@/lib/utils";

/**
 * The ATA notices in the header (SPEC-0008 AC-0008-04, -05): how many this
 * member has not read, the newest of them, and each opening its ATA. Every
 * perfil sees the same notices; what one reads is theirs alone.
 */
export function Bell() {
  const router = useRouter();
  const read = useRead<AvisoPage>(BELL_PATH);
  const unread = read.data?.nao_lidas ?? 0;
  const count = unread > BELL_MAX_COUNT ? `${BELL_MAX_COUNT}+` : String(unread);

  const markAll = async () => {
    await apiFetch("/api/v1/notificacoes/lidas", { method: "POST" });
    read.reload();
  };

  return (
    <DropdownMenu onOpenChange={(open) => open && read.reload()}>
      <DropdownMenuTrigger
        data-testid="bell"
        className="relative flex size-9 items-center justify-center rounded-md hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        aria-label={unread ? `${BELL_LABEL}, ${unread} não lidos` : BELL_LABEL}
      >
        <BellIcon aria-hidden className="size-5" />
        {unread > 0 && (
          <span
            data-testid="bell-count"
            aria-hidden
            className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-primary px-1 text-[10px] leading-none text-primary-foreground tabular-nums"
          >
            {count}
          </span>
        )}
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-80 max-w-[calc(100vw-2rem)]">
        <DropdownMenuLabel className="flex items-center justify-between font-normal">
          <span className="text-sm text-foreground">{BELL_LABEL}</span>
        </DropdownMenuLabel>
        {unread > 0 && (
          <DropdownMenuItem onSelect={() => void markAll()}>
            <CheckCheck aria-hidden />
            {MARK_ALL}
          </DropdownMenuItem>
        )}
        <DropdownMenuSeparator />
        {(read.data?.items.length ?? 0) === 0 && (
          <p className="px-2 py-3 text-sm font-light text-muted-foreground">{BELL_EMPTY}</p>
        )}
        {/* Focusable, so a keyboard can scroll a long list too (axe scrollable-region-focusable). */}
        <div role="group" aria-label={BELL_LABEL} tabIndex={0} className="max-h-96 overflow-y-auto focus-visible:outline-none">
          {read.data?.items.map((aviso) => (
            <DropdownMenuItem
              key={aviso.id}
              data-testid="aviso"
              data-motivo={aviso.motivo}
              data-lida={aviso.lida}
              className="items-start"
              onSelect={() => {
                if (!aviso.lida) void apiFetch(`/api/v1/notificacoes/${aviso.id}/lida`, { method: "POST" }).then(read.reload);
                router.push(`/atas/${aviso.ata_id}`);
              }}
            >
              <span
                aria-hidden
                className={cn("mt-1.5 size-1.5 shrink-0 rounded-full", aviso.lida ? "bg-transparent" : "bg-attention")}
              />
              <span className="min-w-0">
                <span className={cn("block truncate text-sm", aviso.lida && "text-muted-foreground")}>
                  ATA {aviso.ata_number}
                </span>
                <span className="block text-xs font-light text-muted-foreground">
                  {aviso.motivo_rotulo} · {formatDate(aviso.criada_em)}
                  {!aviso.lida && <span className="sr-only"> (não lido)</span>}
                </span>
              </span>
            </DropdownMenuItem>
          ))}
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
