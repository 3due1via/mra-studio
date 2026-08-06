import type { ButtonHTMLAttributes } from "react";
import { MraButton } from "../ui";

export function Button(props: ButtonHTMLAttributes<HTMLButtonElement>) {
  const legacyClass = props.className ?? "";
  const tone = legacyClass.includes("danger") ? "danger" : legacyClass.includes("secondary") ? "secondary" : "primary";
  return <MraButton {...props} tone={tone} />;
}
