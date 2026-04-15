import { redirect } from "next/navigation";
export default function StatusRedirectPage() { redirect("/operations?view=observability"); }
