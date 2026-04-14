import crypto from 'node:crypto';
const BASE32_ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
export function base32Decode(input: string): Buffer {
  const normalized = input.toUpperCase().replace(/=+$/g, '');
  let bits = '';
  for (const char of normalized) {
    const idx = BASE32_ALPHABET.indexOf(char);
    if (idx === -1) continue;
    bits += idx.toString(2).padStart(5, '0');
  }
  const bytes: number[] = [];
  for (let i = 0; i + 8 <= bits.length; i += 8) bytes.push(Number.parseInt(bits.slice(i, i + 8), 2));
  return Buffer.from(bytes);
}
export function parseOtpSecret(provisioningUri: string): string {
  const uri = new URL(provisioningUri);
  return uri.searchParams.get('secret') || '';
}
export function totpFromSecret(secret: string, timeMs = Date.now()): string {
  const counter = Math.floor(timeMs / 30_000);
  const buffer = Buffer.alloc(8);
  buffer.writeBigUInt64BE(BigInt(counter));
  const hmac = crypto.createHmac('sha1', base32Decode(secret)).update(buffer).digest();
  const offset = hmac[hmac.length - 1] & 0x0f;
  const code = ((hmac[offset] & 0x7f) << 24) | ((hmac[offset + 1] & 0xff) << 16) | ((hmac[offset + 2] & 0xff) << 8) | (hmac[offset + 3] & 0xff);
  return String(code % 1_000_000).padStart(6, '0');
}
