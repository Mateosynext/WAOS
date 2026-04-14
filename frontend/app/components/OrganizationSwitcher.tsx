"use client";
import { useEffect, useRef } from "react";
export default function OrganizationSwitcher({ organizations, selectedId, redirectTo, action }: { organizations: Array<{ id: string; name: string }>; selectedId?: string | null; redirectTo: string; action: (formData: FormData) => void | Promise<void> }) {
  const formRef = useRef<HTMLFormElement | null>(null);
  useEffect(() => {
    const form = formRef.current; if (!form) return;
    const select = form.querySelector("select[name='organization_id']") as HTMLSelectElement | null; if (!select) return;
    const handler = () => form.requestSubmit(); select.addEventListener("change", handler); return () => select.removeEventListener("change", handler);
  }, []);
  return <form ref={formRef} action={action}><input type="hidden" name="redirect_to" value={redirectTo} /><select name="organization_id" defaultValue={selectedId || ""} className="field-input min-w-[240px] py-2" aria-label="Seleccionar organización"><option value="">Selecciona una organización</option>{organizations.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></form>;
}
