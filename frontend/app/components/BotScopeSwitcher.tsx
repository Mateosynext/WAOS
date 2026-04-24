import type { BotContract } from "@/app/lib/contracts/bots";
import { switchBotAction } from "@/app/actions/selection";

export default function BotScopeSwitcher({
  bots,
  selectedBotId,
  redirectTo,
  compact = false,
}: {
  bots: BotContract[];
  selectedBotId?: string | null;
  redirectTo: string;
  compact?: boolean;
}) {
  if (!bots.length) return null;
  return (
    <form action={switchBotAction} className="flex flex-wrap items-center gap-2">
      <input type="hidden" name="redirect_to" value={redirectTo} />
      <select name="bot_id" defaultValue={selectedBotId || ""} className="field-input min-w-[220px] py-2" aria-label="Seleccionar asistente operativo">
        <option value="">Seleccionar asistente operativo</option>
        {bots.map((bot) => <option key={String(bot.id)} value={String(bot.id)}>{String(bot.name || bot.id)}</option>)}
      </select>
      <button type="submit" className="secondary-btn">{compact ? "Cambiar asistente" : "Cambiar asistente operativo"}</button>
    </form>
  );
}
