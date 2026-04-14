import { redirect } from "next/navigation";

export function redirectLegacyRoute(): never {
  return redirect("/");
}
