import type { BotContract } from "../lib/contracts";
import { switchBotAction } from "../actions";

export default function BotScopeSwitcher({ bots, selectedBotId, redirectTo }: { bots: BotContract[]; selectedBotId?: string | null; redirectTo: string; }) {
  if (!bots.length) return null;
  return (
    <form action={switchBotAction} className="flex flex-wrap items-center gap-2">
      <input type="hidden" name="redirect_to" value={redirectTo} />
      <select name="bot_id" defaultValue={selectedBotId || ""} className="field-input min-w-[220px] py-2" aria-label="Seleccionar bot">
        <option value="">Seleccionar bot</option>
        {bots.map((bot) => <option key={String(bot.id)} value={String(bot.id)}>{String(bot.name || bot.id)}</option>)}
      </select>
      <button type="submit" className="secondary-btn">Cambiar bot</button>
    </form>
  );
}
