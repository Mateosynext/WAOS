export type ValidationErrors = Record<string, string>;

export function isEmail(value: string) { return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim()); }

export function validateLogin(values: { email?: string; password?: string; otp_code?: string; challenge_id?: string | null }) {
  const errors: ValidationErrors = {};
  const email = String(values.email || "").trim();
  const password = String(values.password || "");
  const otpCode = String(values.otp_code || "").trim();
  const challengeId = String(values.challenge_id || "").trim();
  if (!email) errors.email = "Ingresa tu correo.";
  else if (!isEmail(email)) errors.email = "Usa un correo válido.";
  if (!password) errors.password = "Ingresa tu contraseña.";
  else if (password.length < 8) errors.password = "Usa al menos 8 caracteres.";
  if (challengeId) {
    if (!otpCode) errors.otp_code = "Ingresa el código MFA.";
    else if (!/^\d{6}$/.test(otpCode)) errors.otp_code = "El código MFA debe tener 6 dígitos.";
  }
  return errors;
}

export function validateSecret(values: { key_name?: string; secret_value?: string; scope?: string; bot_id?: string }) {
  const errors: ValidationErrors = {};
  const keyName = String(values.key_name || "").trim();
  const secretValue = String(values.secret_value || "").trim();
  const scope = String(values.scope || "tenant").trim();
  if (!keyName) errors.key_name = "Escribe un nombre claro para la clave.";
  else if (!/^[a-zA-Z0-9._-]{3,80}$/.test(keyName)) errors.key_name = "Usa 3 a 80 caracteres: letras, números, punto, guion o guion bajo.";
  if (!secretValue) errors.secret_value = "Ingresa el valor del secreto.";
  else if (secretValue.length < 8) errors.secret_value = "Usa un valor de al menos 8 caracteres.";
  if (!["tenant", "bot"].includes(scope)) errors.scope = "Selecciona un alcance válido.";
  if (scope === "bot" && !String(values.bot_id || "").trim()) errors.bot_id = "Selecciona un bot para alcance por bot.";
  return errors;
}

export function validateBotDraft(values: { name?: string; objective?: string; tone?: string }) {
  const errors: ValidationErrors = {};
  const name = String(values.name || "").trim();
  const objective = String(values.objective || "").trim();
  const tone = String(values.tone || "").trim();
  if (!name) errors.name = "Ponle nombre al bot.";
  if (!objective) errors.objective = "Define el objetivo principal del bot.";
  if (!tone) errors.tone = "Define el tono antes de probar.";
  return errors;
}

export function validateIntegrationConnection(values: { provider?: string; channel?: string; credential?: string }) {
  const errors: ValidationErrors = {};
  if (!String(values.provider || "").trim()) errors.provider = "Selecciona un proveedor.";
  if (!String(values.channel || "").trim()) errors.channel = "Selecciona un canal.";
  if (!String(values.credential || "").trim()) errors.credential = "Agrega la credencial o token principal.";
  return errors;
}
