"use client";

import { MouseEvent, ReactNode } from "react";

type Props = { children: ReactNode; className?: string; message: string };

export default function ConfirmSubmitButton({ children, className = "secondary-btn", message }: Props) {
  return <button className={className} type="submit" onClick={(event: MouseEvent<HTMLButtonElement>) => { if (!window.confirm(message)) event.preventDefault(); }}>{children}</button>;
}
